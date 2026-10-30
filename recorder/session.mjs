// Pure parts of the recorder: when to record, how tracks and sessions are named, what is left to finalize.
import { mkdir, readdir, stat } from 'node:fs/promises';
import path from 'node:path';

export const idle = { recording: false, emptySince: null, held: false };

// One step of the session state machine, called on every voice state change and on a timer.
// Starts when the GM is in the channel; stops once no human has been there for graceMs.
// `held` (set by dropped()) blocks restarting until the GM leaves, so a bot someone
// disconnected on purpose does not jump straight back in.
export function step(state, { gmPresent, humans, now }, graceMs) {
  if (!gmPresent && state.held) state = { ...state, held: false };
  if (!state.recording) {
    if (gmPresent && !state.held) return [{ ...state, recording: true, emptySince: null }, 'start'];
    return [state, null];
  }
  if (humans > 0) return [state.emptySince === null ? state : { ...state, emptySince: null }, null];
  const emptySince = state.emptySince ?? now;
  if (now - emptySince >= graceMs) return [{ ...state, recording: false, emptySince: null }, 'stop'];
  return [{ ...state, emptySince }, null];
}

// The recording ended without the channel emptying (kicked, connection lost, join failed).
export function dropped(gmPresent) {
  return { recording: false, emptySince: null, held: gmPresent };
}

// Track file name from a Discord username (already [a-z0-9._], kept safe for old or odd names).
// `taken` holds names given to other users in this session.
export function trackName(username, userId, taken) {
  let name = String(username ?? '').toLowerCase().replace(/[^a-z0-9._-]+/g, '_')
    .replace(/^[._-]+/, '').slice(0, 32) || 'user';
  if (taken.has(name)) name = `${name}-${String(userId).slice(-6)}`;
  return name;
}

export const validTrackName = (name) => /^[a-z0-9][a-z0-9._-]{0,63}$/.test(name);

const pad = (n) => String(n).padStart(2, '0');

// <YYYY-MM-DD>-<HHMM> in local time (set TZ in the container).
export function sessionName(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}`;
}

// Creates <out>/<name>, or <name>-2, -3… when a session already started that minute.
export async function createSessionDir(outDir, date) {
  const base = path.join(outDir, sessionName(date));
  for (let n = 1; ; n += 1) {
    const dir = n === 1 ? base : `${base}-${n}`;
    try {
      await mkdir(dir, { mode: 0o700 });
      return dir;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
  }
}

// Session directories that were recorded (recording.json) but never finalized (info.json).
export async function unfinished(outDir) {
  const found = [];
  for (const entry of await readdir(outDir, { withFileTypes: true }).catch(() => [])) {
    if (!entry.isDirectory()) continue;
    const dir = path.join(outDir, entry.name);
    const has = (file) => stat(path.join(dir, file)).then(() => true, () => false);
    if (await has('recording.json') && !await has('info.json')) found.push(dir);
  }
  return found.sort();
}
