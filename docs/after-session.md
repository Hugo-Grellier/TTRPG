# After a session

Record per speaker, transcribe locally, summarize Foundry, then let an agent
propose the note updates (skill `session-debrief`). Nothing leaves the
machine: no audio or transcript goes to a service.

Everything raw goes to `<campaign>/.cache/sessions/<day>/` (ignored by Git):
a transcript is the players' own words, long and private; only the reviewed
session note and note updates are committed.

## 1. Record

Everyone at the table must agree to be recorded, each session (the players
have agreed in principle; post a notice when recording starts anyway).

- **Craig** (works today): `/join` in the voice channel, download the
  multi-track FLAC zip after the session. Tracks are aligned and named like
  `1-<username>.flac`. The audio sits on Craig's servers until downloaded.
- **LoreForge probe** (`~/dev/personal/LoreForge/experiments/discord-receive-timing-probe`,
  your own bot, nothing hosted by a third party): records raw Opus per
  speaker with RTP timing, up to six hours.
  1. Create a Discord application and bot; intents `Guilds` and
     `GuildVoiceStates`; invite it with View Channel and Connect.
  2. In the probe directory: `pnpm install --frozen-lockfile`; fill its
     ignored `.env` (`LOREFORGE_DISCORD_TEST_BOT_TOKEN`, guild and voice
     channel ids, `LOREFORGE_DISCORD_TEST_PARTICIPANT_IDS` in a fixed order:
     that order gives `speaker-001`, `speaker-002`…). Never commit the token.
  3. `node probe.mjs capture 21600 --notice-posted-and-consented-test`,
     Ctrl-C at the end of the session. It prints the capture directory (under
     `/tmp`: move it before a reboot).
  4. `node decode.mjs <capture>/events.jsonl` writes `decoded/speaker-NNN.wav`,
     all on the capture's timeline.

  Labels are anonymous by design (user ids are never written), so keep the
  participant order fixed and map labels to names with `--names`.

## 2. Transcribe

Once, in the tools checkout (Python 3.14; uv's default 3.15 has no
onnxruntime wheel yet):

```sh
uv venv --python 3.14 tools/.venv
uv pip install --python tools/.venv/bin/python -r tools/requirements.txt faster-whisper==1.2.1
```

Then, from the campaign:

```sh
tools/bin/ttrpg transcribe ~/Downloads/craig-xxxx.zip --day 2026-11-06
tools/bin/ttrpg transcribe /tmp/loreforge-discord-receive-XXXX \
  --names speaker-001=Hugo speaker-002=Alice --day 2026-11-06
```

Each track is decoded with ffmpeg, transcribed on CPU with voice activity
detection (silence skipped), split into remarks at pauses of one second and
merged by time. The language is `campaign.yaml`'s. The default model `small`
is downloaded once from Hugging Face; `--model <dir>` (or
`TTRPG_WHISPER_MODEL`) uses a local copy, e.g. LoreForge's
`models/faster-whisper-small` or a larger model for better French.

## 3. Foundry Flight Recorder

Copy `Data/flight-recorder/` from the Foundry server and import it with `ffr`
(`foundry-observer` repository), then:

```sh
ffr import ./ffr-storage
tools/bin/ttrpg flight latest --db ./data/ffr.db \
  --ffr "node '<foundry-observer>/packages/analysis-cli/ffr.mjs'"
```

This writes `flight.md`: scenes viewed, combats with their combatants and
rounds, checks (actor, item, statistic, outcome, total, DC) and conditions,
each check counted once. The day defaults to the session's start date.

## 4. Debrief

Ask an agent in the campaign to debrief the session (skill `session-debrief`),
with your own notes. Review its changes with `git diff` and commit.

## Toward an automatic recorder

The probe already records what is needed; what it lacks is starting by
itself. The next step, once a bot token and a test server are available: a
small `recorder/` bot (from the probe, without its timing-qualification
modes) that joins when the GM joins the table's voice channel, posts the
recording notice in the text channel, stops when the channel empties, decodes,
and runs `ttrpg transcribe`. It needs an always-on host (the NAS that runs
Foundry is the obvious candidate). Not built yet: it cannot be tested without
Discord, and the probe's RTP timing relies on an internal `@discordjs/voice`
0.19.2 method that must be rechecked on every upgrade.
