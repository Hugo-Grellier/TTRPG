# After a session

Record per speaker, transcribe locally, summarize Foundry, then let an agent
propose the note updates (skill `session-debrief`). Nothing leaves the
machine: no audio or transcript goes to a service.

Transcripts and Flight Recorder summaries are committed in the (private)
campaign repository as raw notes, `sessions/<day>/transcript.md` and
`flight.md` (`tags: [raw]`, `visibility: gm`, never exported to Foundry). The
audio stays outside Git, under `<campaign>/.cache/sessions/audio/`.

Speakers are matched to players by `campaign.yaml` (Discord name, loosely
compared: `.omegadraco`, `_omegadraco` and Craig's `Archivist_AI_1906` all
match their account). Who is present varies by session: the transcript lists
in `present` whoever spoke. Bots are skipped; unknown names are kept and
reported.

```yaml
players:
  .omegadraco: {name: Hugo, role: gm}
  patatecherie: {name: Alice, character: Amiri}
  Archivist AI: {role: bot}
```

## 1. Record

Everyone at the table must agree to be recorded, each session (the players
have agreed in principle; post a notice when recording starts anyway).

- **`recorder/`** (recommended; your own bot, nothing hosted by a third
  party): joins the table's voice channel by itself when the GM joins, posts
  the recording notice, records one track per person, stops when the channel
  has been empty for a minute, decodes, and can start the transcript. Setup
  in [The recorder](#the-recorder) below.
- **Craig** (fallback): `/join` in the voice channel, download the
  multi-track FLAC zip after the session. Tracks are aligned and named like
  `1-<username>.flac`. The audio sits on Craig's servers until downloaded.

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
tools/bin/ttrpg transcribe <recordings>/2026-11-06-2004 --day 2026-11-06
```

A recorder session directory is read through its `decoded/` WAVs, named by
Discord username; `--names alice=Alice` overrides `campaign.yaml` for one run.

Each track is decoded with ffmpeg, transcribed (on the GPU if CTranslate2 finds CUDA 12 and cuDNN 9, else the CPU; `TTRPG_WHISPER_DEVICE=cpu` forces it) with voice activity
detection (silence skipped), split into remarks at pauses of one second and
merged by time. The language is `campaign.yaml`'s; the day comes from
Craig's `info.txt` or the recorder's `info.json`. The default model is
`large-v3-turbo` (downloaded once from Hugging Face; `--model` or
`TTRPG_WHISPER_MODEL` to change it): good French, slow on CPU. Measured on this
machine (16 cores): 15 minutes of speech in under 6 minutes, so a three-hour
session of five players takes several hours: run it overnight.

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

## The recorder

`recorder/` is a small Node bot (`discord.js`, `@discordjs/voice`, built from
the LoreForge receive-timing probe). It needs no command during a session:

- When the GM (`RECORDER_GM_USER_ID`) is in the voice channel, it posts the
  recording notice in the text channel, then joins. If the notice cannot be
  posted it does not record.
- It records every human in the channel, each in their own track named by
  Discord username (bots are ignored), including people who join later.
- When no human has been in the channel for `RECORDER_GRACE_SECONDS` (60), it
  leaves, posts that recording stopped, decodes the tracks and runs
  `RECORDER_POST_COMMAND` if set. If someone disconnects the bot, it stops and
  does not come back until the GM leaves and rejoins.
- If it is stopped or crashes mid-session, the raw tracks stay on disk and
  are decoded at the next start (a new recording starts if the GM is still
  there: two directories for that session).

Each session is a directory under the output volume:

```
<out>/2026-11-06-2004/        start time, local (TZ)
  recording.json              start time, server, channel
  tracks/alice.packets        raw Opus with RTP timing, written as it arrives
  tracks/alice.json           username and display name
  decoded/alice.wav           16 kHz mono, every track starts at t=0
  info.json                   recording.json + tracks and durations; marks the session finished
```

Raw Opus is at most about 30 MB per speaker-hour (less with silence),
decoded WAV 115 MB. The files are
private (0600) to the user that runs the bot.

### Discord application (once)

1. <https://discord.com/developers/applications> > New Application. Under
   **Bot**: Reset Token, copy it into `.env` (never commit it). Leave every
   *Privileged Gateway Intent* off (Presence, Server Members, Message
   Content): the bot only uses `Guilds` and `GuildVoiceStates`. Turn **Public
   Bot** off.
2. **OAuth2 > URL Generator**: scope `bot`; permissions View Channels, Send
   Messages, Connect. Open the URL and add the bot to the server. If the
   channels are private, give the bot's role those three permissions on the
   voice channel and the text channel.
3. In Discord, User Settings > Advanced > Developer Mode on; right-click to
   copy the ids of the server, the voice channel, the text channel (the voice
   channel's own chat works) and the GM.

### Run on the NAS

```sh
cd recorder            # a copy of this directory on the NAS
cp .env.example .env   # fill in the token and the four ids
mkdir recordings       # owned by the uid:gid set in compose.yaml (default 1000:1000)
docker compose up -d --build
docker compose logs -f # "ready as ...", then "recording to ..." when the GM joins
```

`compose.yaml` sets the output to `./recordings` (mounted at `/recordings`)
and `TZ` for directory names. Without Docker: Node 22.12+, `npm ci`, fill
`.env`, `npm start`.

Run the tests with `npm ci --prefix recorder` once, then `make recorder-test`
(Node's test runner, synthetic Opus; no Discord needed).

### Transcribe a recording

The container has only Node: it decodes, but cannot run `ttrpg transcribe`
(Python, ffmpeg, faster-whisper). Either transcribe from your machine over
the NAS share:

```sh
tools/bin/ttrpg transcribe /mnt/nas/recorder/recordings/2026-11-06-2004 --day 2026-11-06
```

or run the bot outside Docker on a machine with the campaign checkout and set
the post-command in `.env` (`$1` is the session directory; single quotes keep
it literal):

```sh
RECORDER_POST_COMMAND='cd ~/dev/personal/Campaign/campaign-kingmaker && tools/bin/ttrpg transcribe "$1" --day "$(basename "$1" | cut -c1-10)"'
```

### Limits

- RTP timing is read in `VoiceReceiver.parsePacket()`, an internal method of
  `@discordjs/voice` 0.19.2 (versions are pinned). After any upgrade, record
  a short test session: if the method changed, the bot logs `packet without
  RTP metadata` and the stop message says audio was not saved.
- Discord changes voice encryption (the DAVE end-to-end protocol, transport
  modes) on its own schedule; an outdated `@discordjs/voice` may fail to
  connect or to decrypt. Packets that fail to decrypt are lost, not garbled.
- Tracks are aligned by the time the first packet of each connection arrived;
  separate speakers share no clock, so expect alignment within tens of
  milliseconds, not samples. Not yet measured on a real session.
- Not verified against Discord at all: written and tested without a bot token.
