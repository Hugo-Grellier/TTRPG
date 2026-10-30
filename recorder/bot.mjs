// Discord session recorder: joins the table's voice channel when the GM does, records one
// Opus track per human speaker, stops when the channel stays empty, then decodes and runs
// the post-command. Discord wiring only; the logic lives in session.mjs and decode.mjs.
// Capture adapted from LoreForge's discord-receive-timing-probe (probe.mjs).
import { spawn } from 'node:child_process';
import { createWriteStream, existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client, Events, GatewayIntentBits } from 'discord.js';
import { EndBehaviorType, entersState, joinVoiceChannel, VoiceConnectionStatus } from '@discordjs/voice';
import { packetRecord } from './decode.mjs';
import { createSessionDir, dropped, idle, step, trackName, unfinished } from './session.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
if (existsSync(path.join(here, '.env'))) process.loadEnvFile(path.join(here, '.env'));

const log = (...args) => console.log(new Date().toISOString(), ...args);

function readConfig(env) {
  const required = ['RECORDER_DISCORD_TOKEN', 'RECORDER_GUILD_ID', 'RECORDER_VOICE_CHANNEL_ID',
    'RECORDER_TEXT_CHANNEL_ID', 'RECORDER_GM_USER_ID'];
  const missing = required.filter((name) => !env[name]);
  if (missing.length) throw new Error(`Missing environment variable(s): ${missing.join(', ')}`);
  const [token, guildId, voiceId, textId, gmId] = required.map((name) => env[name].trim());
  for (const [name, id] of [['guild', guildId], ['voice channel', voiceId], ['text channel', textId], ['GM user', gmId]]) {
    if (!/^\d{17,20}$/.test(id)) throw new Error(`The ${name} id must be a Discord snowflake (17-20 digits).`);
  }
  const graceSeconds = Number(env.RECORDER_GRACE_SECONDS || 60);
  if (!(graceSeconds >= 0)) throw new Error('RECORDER_GRACE_SECONDS must be a number of seconds.');
  return {
    token, guildId, voiceId, textId, gmId,
    outDir: path.resolve(env.RECORDER_OUTPUT_DIR || path.join(here, 'recordings')),
    postCommand: env.RECORDER_POST_COMMAND || null,
    graceMs: graceSeconds * 1_000,
    notice: env.RECORDER_NOTICE ||
      'Recording started: every voice in this channel is recorded, one track per person, for the session notes. ' +
      'The audio stays on the GM\'s server and is transcribed locally. Leave the channel if you do not agree.',
  };
}

let cfg;
try {
  cfg = readConfig(process.env);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates] });
let state = idle;
let current = null; // the recording in progress
let textChannel;

// --- After a recording: decode, then the post-command, one session at a time. ---

const run = (command, args) => new Promise((resolve, reject) => {
  spawn(command, args, { stdio: 'inherit' })
    .on('error', reject)
    .on('exit', (code, signal) => (code === 0 ? resolve() : reject(new Error(`${command} exited with ${signal ?? code}`))));
});

let queue = Promise.resolve();
function finalize(dir) {
  queue = queue.then(async () => {
    log('decoding', dir);
    // A child process: decoding hours of audio would otherwise block the gateway heartbeat.
    await run(process.execPath, [path.join(here, 'decode.mjs'), dir]);
    const info = JSON.parse(await readFile(path.join(dir, 'info.json'), 'utf8'));
    log('decoded', dir, `${info.tracks.length} track(s)`);
    if (cfg.postCommand && info.tracks.length) {
      log('running post-command for', dir);
      await run('sh', ['-c', cfg.postCommand, 'sh', dir]); // the session dir is $1
      log('post-command done for', dir);
    }
  }).catch((error) => log('ERROR finalizing', dir, error.message));
  return queue;
}

const say = (text) => textChannel.send({ content: text, allowedMentions: { parse: [] } });

// --- Recording ---

async function startRecording(guild) {
  // No notice, no recording: the notice is how players know.
  await say(cfg.notice);
  const startedAt = new Date();
  const dir = await createSessionDir(cfg.outDir, startedAt);
  await mkdir(path.join(dir, 'tracks'), { mode: 0o700 });
  const channel = guild.channels.cache.get(cfg.voiceId);
  await writeFile(path.join(dir, 'recording.json'), `${JSON.stringify({
    started_at: startedAt.toISOString(), guild: guild.name, channel: channel?.name ?? cfg.voiceId,
  }, null, 2)}\n`, { mode: 0o600 });

  const connection = joinVoiceChannel({
    channelId: cfg.voiceId, guildId: guild.id, adapterCreator: guild.voiceAdapterCreator,
    selfDeaf: false, selfMute: true,
  });
  const r = { dir, connection, startedAt, t0: null, tracks: new Map(), names: new Set(), subscribed: new Set(), stopping: false };
  current = r;
  log('recording to', dir);

  connection.on('stateChange', (before, after) => log('voice connection', before.status, '->', after.status));
  connection.on('error', (error) => log('ERROR voice connection', error.message));
  connection.on(VoiceConnectionStatus.Disconnected, async () => {
    try { // reconnecting by itself (channel move, region change) or gone for good (kicked)?
      await Promise.race([
        entersState(connection, VoiceConnectionStatus.Signalling, 5_000),
        entersState(connection, VoiceConnectionStatus.Connecting, 5_000),
      ]);
    } catch {
      if (r.stopping) return;
      state = dropped(gmPresent(guild));
      await stopRecording(r, 'disconnected from the voice channel');
    }
  });

  try {
    await entersState(connection, VoiceConnectionStatus.Ready, 30_000);
  } catch (error) {
    await stopRecording(r, 'could not join the voice channel (check the Connect permission)');
    throw error;
  }
  r.t0 = process.hrtime.bigint();
  captureRtp(r);
  connection.receiver.speaking.on('start', (userId) => subscribe(r, guild, userId));
  for (const voiceState of guild.voiceStates.cache.values()) {
    if (voiceState.channelId === cfg.voiceId) subscribe(r, guild, voiceState.id);
  }
}

// @discordjs/voice strips the RTP header before handing out Opus packets, and the decoder needs
// its timestamp to place packets in time. Read it in VoiceReceiver.parsePacket(), an internal
// method of @discordjs/voice 0.19.2: recheck this on every upgrade.
function captureRtp(r) {
  const receiver = r.connection.receiver;
  if (typeof receiver.parsePacket !== 'function') {
    throw new Error('@discordjs/voice has no VoiceReceiver.parsePacket(): the pinned version changed.');
  }
  r.rtp = new WeakMap();
  const parsePacket = receiver.parsePacket;
  receiver.parsePacket = function parsePacketKeepingRtp(buffer, ...rest) {
    const packet = parsePacket.call(this, buffer, ...rest);
    if (packet) {
      r.rtp.set(packet, { sequence: buffer.readUInt16BE(2), timestamp: buffer.readUInt32BE(4), ssrc: buffer.readUInt32BE(8) });
    }
    return packet;
  };
}

async function openTrack(r, guild, userId) {
  const member = guild.members.cache.get(userId) ?? await guild.members.fetch(userId).catch(() => null);
  const user = member?.user ?? await client.users.fetch(userId);
  if (user.bot) return null;
  const name = trackName(user.username, userId, r.names);
  r.names.add(name);
  await writeFile(path.join(r.dir, 'tracks', `${name}.json`), `${JSON.stringify({
    username: user.username, display_name: member?.displayName ?? user.globalName ?? user.username,
  })}\n`, { mode: 0o600 });
  const file = createWriteStream(path.join(r.dir, 'tracks', `${name}.packets`), { flags: 'wx', mode: 0o600 });
  file.on('error', (error) => log('ERROR writing track', name, error.message));
  log('track', name);
  return { name, file, epochs: new Map() };
}

async function subscribe(r, guild, userId) {
  if (r.stopping || r.subscribed.has(userId) || userId === client.user.id) return;
  r.subscribed.add(userId); // bots stay in the set, so they are never looked up again
  try {
    if (!r.tracks.has(userId)) {
      const track = await openTrack(r, guild, userId);
      if (!track) return;
      r.tracks.set(userId, track);
    }
  } catch (error) {
    r.subscribed.delete(userId);
    log('ERROR opening track for a speaker', error.message);
    return;
  }
  if (r.stopping) return;
  const track = r.tracks.get(userId);
  const stream = r.connection.receiver.subscribe(userId, { end: { behavior: EndBehaviorType.Manual } });
  stream.on('data', (packet) => {
    if (r.stopping) return; // the track file is closing
    const rtp = r.rtp.get(packet);
    if (!rtp) {
      if (!r.rtpMissing) log('ERROR packet without RTP metadata: @discordjs/voice internals changed, audio is not saved');
      r.rtpMissing = true;
      return;
    }
    let epoch = track.epochs.get(rtp.ssrc);
    if (epoch === undefined) track.epochs.set(rtp.ssrc, (epoch = track.epochs.size));
    const atMs = Number(process.hrtime.bigint() - r.t0) / 1e6;
    track.file.write(packetRecord({ timestamp: rtp.timestamp, sequence: rtp.sequence, epoch, atMs }, packet));
  });
  stream.on('error', (error) => log('receive stream error for', track.name, error.message));
  // A failed decrypt destroys the stream: subscribe again at the next speaking start.
  stream.on('close', () => r.subscribed.delete(userId));
}

async function stopRecording(r, reason, { decode = true } = {}) {
  if (r.stopping) return;
  r.stopping = true;
  if (current === r) current = null;
  if (r.connection.state.status !== VoiceConnectionStatus.Destroyed) r.connection.destroy();
  await Promise.all([...r.tracks.values()].map(({ file }) => new Promise((resolve) => file.end(resolve))));
  const minutes = Math.round((Date.now() - r.startedAt) / 60_000);
  log('recording stopped:', reason, `${minutes} min, ${r.tracks.size} track(s)`, r.dir);
  await say(`Recording stopped (${reason}): ${minutes} min, ${r.tracks.size} track(s).` +
    (r.rtpMissing ? ' The recorder could not read packet timing: audio was not saved, check the logs.' : ''))
    .catch((error) => log('ERROR posting the stop message', error.message));
  if (decode) finalize(r.dir);
}

// --- When to record ---

const gmPresent = (guild) => guild.voiceStates.cache.get(cfg.gmId)?.channelId === cfg.voiceId;

function evaluate() {
  const guild = client.guilds.cache.get(cfg.guildId);
  if (!guild || !textChannel) return;
  const humans = guild.voiceStates.cache.filter((s) =>
    s.channelId === cfg.voiceId && s.id !== client.user.id && !s.member?.user.bot).size;
  const present = gmPresent(guild);
  let action;
  [state, action] = step(state, { gmPresent: present, humans, now: Date.now() }, cfg.graceMs);
  if (action === 'start') {
    log('GM in the voice channel: starting');
    startRecording(guild).catch((error) => {
      log('ERROR starting the recording:', error.message);
      if (current) stopRecording(current, 'start failed');
      state = dropped(present);
    });
  }
  if (action === 'stop' && current) stopRecording(current, 'the voice channel is empty');
}

client.on(Events.VoiceStateUpdate, (before, after) => {
  if (before.channelId !== cfg.voiceId && after.channelId !== cfg.voiceId) return;
  if (current?.t0 && after.channelId === cfg.voiceId) subscribe(current, after.guild, after.id);
  evaluate();
});
client.on(Events.Error, (error) => log('ERROR gateway', error.message));
async function ready() {
  const voice = await client.channels.fetch(cfg.voiceId);
  if (!voice?.isVoiceBased() || voice.guildId !== cfg.guildId) throw new Error('RECORDER_VOICE_CHANNEL_ID is not a voice channel of RECORDER_GUILD_ID.');
  textChannel = await client.channels.fetch(cfg.textId);
  if (!textChannel?.isTextBased() || textChannel.guildId !== cfg.guildId) throw new Error('RECORDER_TEXT_CHANNEL_ID is not a text channel of RECORDER_GUILD_ID.');
  log(`ready as ${client.user.tag}: watching #${voice.name}, notices in #${textChannel.name}, output ${cfg.outDir}`);
  evaluate();
  setInterval(evaluate, 5_000); // the grace period ends without any Discord event
}
client.once(Events.ClientReady, () => ready().catch((error) => {
  console.error(redact(error.message));
  process.exit(1);
}));

async function shutdown(signal) {
  log('received', signal);
  // Close the track files and leave; the next start decodes this session.
  if (current) await stopRecording(current, 'recorder shutting down', { decode: false });
  client.destroy();
  process.exit(0);
}
process.once('SIGTERM', shutdown);
process.once('SIGINT', shutdown);
process.on('unhandledRejection', (error) => log('ERROR', error?.message ?? error));

const redact = (text) => String(text).replaceAll(cfg.token, '[token]');
try {
  await mkdir(cfg.outDir, { recursive: true, mode: 0o700 });
  for (const dir of await unfinished(cfg.outDir)) {
    log('unfinished session from a previous run:', dir);
    finalize(dir);
  }
  await client.login(cfg.token);
} catch (error) {
  console.error(redact(error.message));
  process.exit(1);
}
