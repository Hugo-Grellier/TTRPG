// Probe decoder tests (LoreForge discord-receive-timing-probe), moved to the in-file packet format,
// plus session-level checks: alignment across tracks, a crash-truncated tail, info.json.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { decodeSession, packetRecord, readPackets, rtpTimestampDelta } from './decode.mjs';

const require = createRequire(import.meta.url);
const OpusScript = require('opusscript');

// 20 ms stereo Opus frames, like Discord sends; `loud` makes a frame audible.
function opusFrames(count, invalid = [], loud = false) {
  const encoder = new OpusScript(48_000, 2, OpusScript.Application.AUDIO);
  const pcm = Buffer.alloc(960 * 2 * 2);
  if (loud) for (let i = 0; i < 960 * 2; i += 1) pcm.writeInt16LE(Math.round(8000 * Math.sin(i / 10)), i * 2);
  const frames = Array.from({ length: count }, (_, i) => invalid.includes(i) ? Buffer.from([0xff]) : encoder.encode(pcm, 960));
  encoder.delete();
  return frames;
}

function trackFile(timestamps, receiveTimes, { invalid = [], epochs = [], loud = false } = {}) {
  const frames = opusFrames(timestamps.length, invalid, loud);
  return Buffer.concat(frames.map((frame, i) => packetRecord({
    timestamp: timestamps[i], sequence: i + 1, epoch: epochs[i] ?? 0, atMs: receiveTimes[i],
  }, frame)));
}

async function withSession(tracks, run) {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'ttrpg-recorder-decode-'));
  try {
    await mkdir(path.join(dir, 'tracks'));
    await writeFile(path.join(dir, 'recording.json'), JSON.stringify({ started_at: '2026-11-06T19:00:00.000Z', channel: 'table' }));
    for (const [name, data] of Object.entries(tracks)) {
      await writeFile(path.join(dir, 'tracks', `${name}.packets`), data);
      await writeFile(path.join(dir, 'tracks', `${name}.json`), JSON.stringify({ username: name }));
    }
    return await run(dir, await decodeSession(dir));
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

const decodeOne = (timestamps, receiveTimes, options) =>
  withSession({ alice: trackFile(timestamps, receiveTimes, options) }, (_dir, info) => info.tracks[0]);

test('calculates forward RTP sample offsets across timestamp wrap', () => {
  assert.equal(rtpTimestampDelta(1_960, 1_000), 960);
  assert.equal(rtpTimestampDelta(944, 0xffff_fff0), 960);
});

test('keeps an earlier out-of-order packet before its RTP origin', () => {
  assert.equal(rtpTimestampDelta(1_000, 1_960), -960);
});

test('rejects RTP timestamps outside the unsigned 32-bit range', () => {
  assert.throws(() => rtpTimestampDelta(-1, 0), /Invalid RTP timestamp/);
  assert.throws(() => rtpTimestampDelta(0, 0x1_0000_0000), /Invalid RTP timestamp/);
});

test('decoder follows RTP timing instead of bursty packet receive times', async () => {
  const track = await decodeOne([1_000, 1_960, 2_920], [20, 55, 57]);
  assert.equal(track.duration_ms, 60);
  assert.equal(track.inserted_silence_ms, 0);
  assert.equal(track.trimmed_overlap_ms, 0);
});

test('decoder restores media order when packets arrive out of order', async () => {
  const track = await decodeOne([1_000, 2_920, 1_960], [20, 80, 55]);
  assert.equal(track.duration_ms, 60);
  assert.equal(track.inserted_silence_ms, 0);
});

test('decoder inserts silence for an RTP timestamp gap', async () => {
  const track = await decodeOne([1_000, 1_960, 3_880], [20, 40, 80]);
  assert.equal(track.duration_ms, 80);
  assert.equal(track.inserted_silence_ms, 20);
});

test('decoder drops invalid packets and anchors each epoch at its first decodable packet', async () => {
  const track = await decodeOne([1_000, 1_960, 2_920, 3_880], [20, 40, 60, 80], { invalid: [0, 2] });
  assert.equal(track.duration_ms, 80);
  assert.equal(track.inserted_silence_ms, 40);
  assert.equal(track.invalid_packets, 2);
});

test('a reconnect (new source epoch) is placed by its own receive time', async () => {
  // Second epoch restarts the RTP clock near 0 but arrives 1 s into the recording.
  const track = await decodeOne([50_000, 50_960, 10, 970], [20, 40, 1_020, 1_040], { epochs: [0, 0, 1, 1] });
  assert.equal(track.duration_ms, 1_040);
});

test('tracks share t=0: a late speaker starts with silence', async () => {
  await withSession({
    alice: trackFile([1_000, 1_960], [20, 40]),
    bob: trackFile([7_000, 7_960], [2_020, 2_040], { loud: true }),
  }, async (dir, info) => {
    assert.deepEqual(info.tracks.map((t) => [t.name, t.username, t.file, t.duration_ms]), [
      ['alice', 'alice', 'decoded/alice.wav', 40],
      ['bob', 'bob', 'decoded/bob.wav', 2_040],
    ]);
    const wav = await readFile(path.join(dir, 'decoded', 'bob.wav'));
    assert.equal(wav.readUInt32LE(24), 16_000);
    assert.equal(wav.readUInt16LE(22), 1);
    const samples = (wav.length - 44) / 2;
    assert.equal(samples, 2.04 * 16_000);
    const peak = (from, to) => Math.max(...Array.from({ length: to - from }, (_, i) => Math.abs(wav.readInt16LE(44 + (from + i) * 2))));
    assert.equal(peak(0, 2.0 * 16_000 - 400), 0); // silent before bob speaks
    assert.ok(peak(2.0 * 16_000, samples) > 1_000); // his frames land at 2.0-2.04 s
    assert.equal(info.started_at, '2026-11-06T19:00:00.000Z');
    assert.equal(info.duration_ms, 2_040);
  });
});

test('a record cut short by a crash is dropped, the rest decoded', async () => {
  const whole = trackFile([1_000, 1_960, 2_920], [20, 40, 60]);
  const cut = whole.subarray(0, whole.length - 3);
  assert.equal(readPackets(cut).packets.length, 2);
  const track = await withSession({ alice: cut }, (_dir, info) => info.tracks[0]);
  assert.equal(track.duration_ms, 40);
  assert.ok(track.truncated_bytes > 0);
});

test('rerunning a session rebuilds decoded/ instead of failing on existing files', async () => {
  await withSession({ alice: trackFile([1_000], [20]) }, async (dir) => {
    const again = await decodeSession(dir);
    assert.equal(again.tracks.length, 1);
  });
});
