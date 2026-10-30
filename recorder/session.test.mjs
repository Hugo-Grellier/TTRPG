import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { createSessionDir, dropped, idle, sessionName, step, trackName, unfinished } from './session.mjs';

const grace = 60_000;

// Feeds observations through step(), returning the actions taken.
function run(observations, state = idle) {
  const actions = [];
  for (const observation of observations) {
    let action;
    [state, action] = step(state, observation, grace);
    if (action) actions.push(action);
  }
  return { state, actions };
}

test('starts when the GM joins, not before', () => {
  assert.deepEqual(run([{ gmPresent: false, humans: 2, now: 0 }]).actions, []);
  assert.deepEqual(run([{ gmPresent: false, humans: 2, now: 0 }, { gmPresent: true, humans: 3, now: 1 }]).actions, ['start']);
});

test('keeps recording while players stay after the GM leaves', () => {
  const { actions, state } = run([
    { gmPresent: true, humans: 3, now: 0 },
    { gmPresent: false, humans: 2, now: 10 },
    { gmPresent: false, humans: 2, now: 999_999 },
  ]);
  assert.deepEqual(actions, ['start']);
  assert.equal(state.recording, true);
});

test('stops only after the channel has been empty for the grace period', () => {
  const start = { gmPresent: true, humans: 1, now: 0 };
  const empty = (now) => ({ gmPresent: false, humans: 0, now });
  assert.deepEqual(run([start, empty(1_000), empty(1_000 + grace - 1)]).actions, ['start']);
  assert.deepEqual(run([start, empty(1_000), empty(1_000 + grace)]).actions, ['start', 'stop']);
});

test('someone rejoining during the grace period cancels the stop', () => {
  const { actions } = run([
    { gmPresent: true, humans: 1, now: 0 },
    { gmPresent: false, humans: 0, now: 1_000 },
    { gmPresent: true, humans: 1, now: 30_000 },
    { gmPresent: false, humans: 0, now: 40_000 },
    { gmPresent: false, humans: 0, now: 40_000 + grace - 1 },
  ]);
  assert.deepEqual(actions, ['start']);
});

test('records again at the next session', () => {
  const { actions } = run([
    { gmPresent: true, humans: 1, now: 0 },
    { gmPresent: false, humans: 0, now: 1 },
    { gmPresent: false, humans: 0, now: 1 + grace },
    { gmPresent: true, humans: 1, now: 2 * grace },
  ]);
  assert.deepEqual(actions, ['start', 'stop', 'start']);
});

test('after a drop with the GM present, waits for the GM to leave and come back', () => {
  let state = dropped(true);
  const { actions } = run([
    { gmPresent: true, humans: 3, now: 0 },
    { gmPresent: false, humans: 2, now: 1 },
    { gmPresent: true, humans: 3, now: 2 },
  ], state);
  assert.deepEqual(actions, ['start']);
  [state] = step(dropped(true), { gmPresent: true, humans: 3, now: 0 }, grace);
  assert.equal(state.recording, false);
});

test('track names are usernames, made safe and unique', () => {
  assert.equal(trackName('alice.b', '1', new Set()), 'alice.b');
  assert.equal(trackName('Old Name#1234', '1', new Set()), 'old_name_1234');
  assert.equal(trackName('../etc', '1', new Set()), 'etc');
  assert.equal(trackName('', '1', new Set()), 'user');
  assert.equal(trackName('alice', '123456789012345678', new Set(['alice'])), 'alice-345678');
});

test('session directories are named by local start minute, never reused', async () => {
  const date = new Date(2026, 10, 6, 9, 5);
  assert.equal(sessionName(date), '2026-11-06-0905');
  const out = await mkdtemp(path.join(os.tmpdir(), 'ttrpg-recorder-session-'));
  try {
    assert.equal(path.basename(await createSessionDir(out, date)), '2026-11-06-0905');
    assert.equal(path.basename(await createSessionDir(out, date)), '2026-11-06-0905-2');
  } finally {
    await rm(out, { recursive: true, force: true });
  }
});

test('unfinished sessions are those with recording.json and no info.json', async () => {
  const out = await mkdtemp(path.join(os.tmpdir(), 'ttrpg-recorder-session-'));
  try {
    for (const [name, files] of [['a', ['recording.json']], ['b', ['recording.json', 'info.json']], ['c', []]]) {
      await mkdir(path.join(out, name));
      for (const file of files) await writeFile(path.join(out, name, file), '{}');
    }
    assert.deepEqual(await unfinished(out), [path.join(out, 'a')]);
    assert.deepEqual(await unfinished(path.join(out, 'missing')), []);
  } finally {
    await rm(out, { recursive: true, force: true });
  }
});
