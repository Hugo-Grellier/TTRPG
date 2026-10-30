// Decodes a session's raw Opus tracks to time-aligned WAVs and writes info.json.
// Adapted from LoreForge's discord-receive-timing-probe decode.mjs: same RTP placement,
// but packet metadata lives in the track file and output is 16 kHz mono (what
// transcription uses; a third of the size, no 4 GB WAV limit before ~18 h).
//   node decode.mjs <session-dir>
import { createRequire } from 'node:module';
import { mkdir, open, readdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validTrackName } from './session.mjs';

const require = createRequire(import.meta.url);
const OpusScript = require('opusscript');
const rtpRate = 48_000; // Discord's Opus RTP clock
const sampleRate = 16_000;
const channels = 1;
const bytesPerFrame = 2 * channels;
const maxWavBytes = 0xffff_ffff;
const silence = Buffer.alloc(64 * 1024);
const headerBytes = 20;

// One packet in a tracks/<name>.packets file: u32 length, u32 RTP timestamp, u16 RTP sequence,
// u16 source epoch, f64 receive time in ms since recording start (all little-endian), then the Opus bytes.
export function packetRecord({ timestamp, sequence, epoch, atMs }, payload) {
  const header = Buffer.alloc(headerBytes);
  header.writeUInt32LE(payload.length, 0);
  header.writeUInt32LE(timestamp, 4);
  header.writeUInt16LE(sequence, 8);
  header.writeUInt16LE(epoch, 10);
  header.writeDoubleLE(atMs, 12);
  return Buffer.concat([header, payload]);
}

// A crash can cut the last record short: keep what is whole.
export function readPackets(buffer) {
  const packets = [];
  let offset = 0;
  while (offset + headerBytes <= buffer.length) {
    const length = buffer.readUInt32LE(offset);
    const end = offset + headerBytes + length;
    if (end > buffer.length) break;
    packets.push({
      sequence: packets.length + 1,
      rtp_timestamp: buffer.readUInt32LE(offset + 4),
      rtp_sequence: buffer.readUInt16LE(offset + 8),
      source_epoch: buffer.readUInt16LE(offset + 10),
      at_ms: buffer.readDoubleLE(offset + 12),
      payload: buffer.subarray(offset + headerBytes, end),
    });
    offset = end;
  }
  return { packets, truncatedBytes: buffer.length - offset };
}

function makeWavHeader(dataBytes) {
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + dataBytes, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * bytesPerFrame, 28);
  header.writeUInt16LE(bytesPerFrame, 32);
  header.writeUInt16LE(16, 34);
  header.write('data', 36);
  header.writeUInt32LE(dataBytes, 40);
  return header;
}

async function writeAll(handle, buffer, position) {
  let offset = 0;
  while (offset < buffer.length) {
    const { bytesWritten } = await handle.write(buffer, offset, buffer.length - offset, position + offset);
    if (bytesWritten === 0) throw new Error('Could not write decoded audio.');
    offset += bytesWritten;
  }
}

async function writeSilence(handle, startPosition, samples) {
  let bytesRemaining = samples * bytesPerFrame;
  let position = startPosition;
  while (bytesRemaining > 0) {
    const bytes = Math.min(bytesRemaining, silence.length);
    await writeAll(handle, silence.subarray(0, bytes), position);
    position += bytes;
    bytesRemaining -= bytes;
  }
}

export function rtpTimestampDelta(timestamp, originTimestamp) {
  if (!Number.isInteger(timestamp) || timestamp < 0 || timestamp > 0xffff_ffff ||
    !Number.isInteger(originTimestamp) || originTimestamp < 0 || originTimestamp > 0xffff_ffff) {
    throw new Error('Invalid RTP timestamp.');
  }
  const wrappedDelta = (timestamp - originTimestamp + 0x1_0000_0000) % 0x1_0000_0000;
  return wrappedDelta >= 0x8000_0000 ? wrappedDelta - 0x1_0000_0000 : wrappedDelta;
}

const newDecoder = () => new OpusScript(sampleRate, channels, OpusScript.Application.AUDIO);

function decodePacket(decoder, packet) {
  try {
    return decoder.decode(packet);
  } catch (error) {
    if (error.message === 'Decode error: Invalid packet') return null;
    throw error;
  }
}

// Places each packet by its RTP timestamp, anchored per source epoch (one per SSRC, i.e. per
// reconnect) at the receive time of that epoch's first decodable packet. RTP gaps become
// silence, overlaps are trimmed, invalid Opus frames are dropped and counted.
export async function decodeTrack(packets, outputPath) {
  const packetsByEpoch = new Map();
  for (const packet of packets) {
    const epochPackets = packetsByEpoch.get(packet.source_epoch) ?? [];
    epochPackets.push(packet);
    packetsByEpoch.set(packet.source_epoch, epochPackets);
  }
  const epochOrigins = new Map();
  for (const [sourceEpoch, epochPackets] of packetsByEpoch) {
    const originDecoder = newDecoder();
    try {
      for (const packet of epochPackets) {
        const pcm = decodePacket(originDecoder, packet.payload);
        if (pcm === null) continue;
        if (!Number.isFinite(packet.at_ms) || packet.at_ms < 0) throw new Error('Invalid packet receive time.');
        epochOrigins.set(sourceEpoch, {
          timestamp: packet.rtp_timestamp,
          start_sample: Math.round(packet.at_ms * sampleRate / 1_000) - pcm.length / bytesPerFrame,
        });
        break;
      }
    } finally {
      originDecoder.delete();
    }
  }

  const ordered = packets.filter((packet) => epochOrigins.has(packet.source_epoch)).sort((a, b) => {
    const epochDifference = a.source_epoch - b.source_epoch;
    if (epochDifference !== 0) return epochDifference;
    const originTimestamp = epochOrigins.get(a.source_epoch).timestamp;
    const timestampDifference = rtpTimestampDelta(a.rtp_timestamp, originTimestamp) -
      rtpTimestampDelta(b.rtp_timestamp, originTimestamp);
    return timestampDifference || a.sequence - b.sequence;
  });

  const output = await open(outputPath, 'wx', 0o600);
  let decoder = null;
  let decoderEpoch = null;
  let cursorSamples = 0;
  let insertedSilenceSamples = 0;
  let trimmedOverlapSamples = 0;
  let invalidPackets = packets.length - ordered.length;
  let writtenPackets = 0;

  try {
    await writeAll(output, Buffer.alloc(44), 0);

    for (const packet of ordered) {
      if (packet.source_epoch !== decoderEpoch) {
        decoder?.delete();
        decoder = newDecoder();
        decoderEpoch = packet.source_epoch;
      }

      const pcm = decodePacket(decoder, packet.payload);
      if (pcm === null) {
        invalidPackets += 1;
        continue;
      }
      if (pcm.length % bytesPerFrame !== 0) throw new Error('Opus decoder returned a partial PCM sample.');
      const frameSamples = pcm.length / bytesPerFrame;
      const origin = epochOrigins.get(packet.source_epoch);
      const rawFrameStart = origin.start_sample +
        Math.round(rtpTimestampDelta(packet.rtp_timestamp, origin.timestamp) * sampleRate / rtpRate);
      const trimmedAtStart = Math.min(frameSamples, Math.max(0, -rawFrameStart));
      const frameStart = Math.max(0, rawFrameStart);
      const availableSamples = frameSamples - trimmedAtStart;
      if (availableSamples === 0) continue;

      if (frameStart > cursorSamples) {
        const gapSamples = frameStart - cursorSamples;
        if ((cursorSamples + gapSamples) * bytesPerFrame > maxWavBytes - 36) {
          throw new Error('Decoded track would exceed the WAV size limit.');
        }
        await writeSilence(output, 44 + cursorSamples * bytesPerFrame, gapSamples);
        cursorSamples += gapSamples;
        insertedSilenceSamples += gapSamples;
      }

      const overlapSamples = Math.min(availableSamples, Math.max(0, cursorSamples - frameStart));
      trimmedOverlapSamples += overlapSamples;
      const samplesToWrite = availableSamples - overlapSamples;
      if (samplesToWrite === 0) continue;

      const writeStartSample = frameStart + overlapSamples;
      const writeEndSample = writeStartSample + samplesToWrite;
      if (writeEndSample * bytesPerFrame > maxWavBytes - 36) {
        throw new Error('Decoded track would exceed the WAV size limit.');
      }
      const pcmOffset = (trimmedAtStart + overlapSamples) * bytesPerFrame;
      await writeAll(output, pcm.subarray(pcmOffset), 44 + writeStartSample * bytesPerFrame);
      cursorSamples = Math.max(cursorSamples, writeEndSample);
      writtenPackets += 1;
    }

    await writeAll(output, makeWavHeader(cursorSamples * bytesPerFrame), 0);
  } finally {
    decoder?.delete();
    await output.close();
  }

  return {
    packets: packets.length,
    written_packets: writtenPackets,
    invalid_packets: invalidPackets,
    duration_ms: cursorSamples * 1_000 / sampleRate,
    inserted_silence_ms: insertedSilenceSamples * 1_000 / sampleRate,
    trimmed_overlap_ms: trimmedOverlapSamples * 1_000 / sampleRate,
  };
}

const readJson = async (file, fallback) => JSON.parse(await readFile(file, 'utf8').catch(() => fallback));

// <dir>/recording.json + tracks/<name>.packets (+ <name>.json) -> decoded/<name>.wav + info.json.
// Safe to rerun: decoded/ is rebuilt and info.json, written last, marks the session finished.
export async function decodeSession(dir) {
  const recording = await readJson(path.join(dir, 'recording.json'), '{}');
  const tracksDir = path.join(dir, 'tracks');
  const decodedDir = path.join(dir, 'decoded');
  await rm(decodedDir, { recursive: true, force: true });
  await mkdir(decodedDir, { mode: 0o700 });

  const tracks = [];
  const files = (await readdir(tracksDir).catch(() => [])).filter((file) => file.endsWith('.packets')).sort();
  for (const file of files) {
    const name = file.slice(0, -'.packets'.length);
    if (!validTrackName(name)) throw new Error(`Invalid track name: ${file}`);
    const { packets, truncatedBytes } = readPackets(await readFile(path.join(tracksDir, file)));
    if (packets.length === 0) continue;
    const user = await readJson(path.join(tracksDir, `${name}.json`), '{}');
    const stats = await decodeTrack(packets, path.join(decodedDir, `${name}.wav`));
    tracks.push({ name, ...user, file: `decoded/${name}.wav`, ...stats, truncated_bytes: truncatedBytes });
  }

  const info = {
    ...recording,
    duration_ms: Math.max(0, ...tracks.map((track) => track.duration_ms)),
    sample_rate_hz: sampleRate,
    channels,
    timeline: 'all tracks start at the recording start (t=0)',
    tracks,
  };
  await writeFile(path.join(dir, 'info.json.tmp'), `${JSON.stringify(info, null, 2)}\n`, { mode: 0o600 });
  await rename(path.join(dir, 'info.json.tmp'), path.join(dir, 'info.json'));
  return info;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dir = process.argv[2];
  if (!dir) {
    console.error('Usage: node decode.mjs <session-dir>');
    process.exitCode = 2;
  } else {
    decodeSession(dir)
      .then((info) => console.log(JSON.stringify(info.tracks.map(({ name, duration_ms }) => ({ name, duration_ms })))))
      .catch((error) => {
        console.error(error.message);
        process.exitCode = 1;
      });
  }
}
