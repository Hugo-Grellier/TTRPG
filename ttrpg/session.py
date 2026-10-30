"""After a session: local transcript of per-speaker tracks and a Flight Recorder summary.

Both are written under .cache/sessions/<day>/ (ignored by Git): raw table talk
is private and long; the session-debrief skill turns it into reviewed notes.
"""

import json
import re
import shlex
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

AUDIO = {".wav", ".flac", ".ogg", ".opus", ".m4a", ".mp3", ".aac"}
INSTALL = """faster-whisper is not installed in the Python that runs ttrpg. Install it in the tools venv (local only, no service):
  uv venv --python 3.14 tools/.venv
  uv pip install --python tools/.venv/bin/python -r tools/requirements.txt faster-whisper==1.2.1
The first run downloads the model (default `small`, ~480 MB) once; pass --model <dir> to use a local copy."""


def tracks(inputs, unpack):
    """Audio files from files, directories and Craig zips; a probe capture directory yields its decoded/ WAVs."""
    found = []
    for item in map(Path, inputs):
        if item.suffix.lower() == ".zip":
            with zipfile.ZipFile(item) as archive:
                archive.extractall(unpack / item.stem)
            item = unpack / item.stem
        if item.is_dir():
            if (item / "decoded").is_dir():
                item = item / "decoded"
            found += sorted(path for path in item.rglob("*") if path.suffix.lower() in AUDIO)
        elif item.is_file():
            found.append(item)
        else:
            raise SystemExit(f"not found: {item}")
    return found


def speaker(path, names):
    """Craig names tracks `1-alice_0.flac`, the probe `speaker-001.wav`; --names maps either form."""
    name = re.sub(r"_\d+$", "", re.sub(r"^\d+-", "", path.stem))
    return names.get(path.stem) or names.get(name) or name


def merge(segments):
    """{speaker: [(start, end, text)]} -> [(start, end, speaker, text)] in time order. Tracks share t=0."""
    return sorted((start, end, who, text) for who, items in segments.items() for start, end, text in items)


def clock(seconds):
    seconds = int(seconds)
    return f"{seconds // 3600}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def whisper(model, language):
    try:
        import numpy
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit(INSTALL)
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is needed to decode the tracks (apt install ffmpeg)")
    loaded = WhisperModel(model, device="cpu", compute_type="int8")

    def run(path):
        # Decode with ffmpeg, as LoreForge does: faster-whisper 1.2.1's own decoder breaks on PyAV >= 16.
        # ponytail: a whole track in memory (~460 MB per 4 h); decode in chunks if that hurts.
        pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                             capture_output=True, check=True).stdout
        samples = numpy.frombuffer(pcm, numpy.int16).astype(numpy.float32) / 32768
        # VAD skips the long silences of a per-speaker track, where Whisper would invent text.
        items, _ = loaded.transcribe(samples, language=language, vad_filter=True, condition_on_previous_text=False, word_timestamps=True)
        return utterances([(word.start, word.end, word.word) for item in items for word in item.words])
    return run


def utterances(words, pause=1.0):
    """Join timed words into lines, splitting at pauses: a Whisper segment can span two remarks
    with another speaker's in between, which would break the merge order."""
    lines = []
    for start, end, word in words:
        if lines and start - lines[-1][1] < pause:
            lines[-1] = (lines[-1][0], end, lines[-1][2] + word)
        else:
            lines.append((start, end, word))
    return [(start, end, text.strip()) for start, end, text in lines if text.strip()]


def transcript(lines, sources, model):
    head = [f"# Transcript\n", f"Model: faster-whisper {model}, local. Tracks: " +
            ", ".join(f"{who} ({path.name})" for who, path in sources) + ".", "Machine transcript: names, numbers and words can be wrong.\n"]
    return "\n".join(head + [f"[{clock(start)}] {who}: {text}" for start, _, who, text in lines]) + "\n"


def flight_events(session, db, ffr):
    types = "session.start,session.stop,scene.summary,combat.start,combat.end,combat.turn,pf2e.check,pf2e.condition"
    command = [*shlex.split(ffr), "timeline", session, "--type", types, "--limit", "1000000", "--json"] + (["--db", db] if db else [])
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(f"{command[0]} not found: put ffr on PATH or pass --ffr 'node <foundry-observer>/packages/analysis-cli/ffr.mjs'")
    if result.returncode:
        raise SystemExit(result.stderr.strip() or f"ffr failed ({result.returncode})")
    return json.loads(result.stdout)


def flight_summary(timeline):
    """Compact Markdown of what Foundry saw: scenes, combats, checks, conditions. Checks seen by author and GM count once."""
    events = timeline["events"]
    # ponytail: no `at` in the key (clients' corrected times can differ); an identical roll seen only by the GM is lost.
    key = lambda event: (event["type"], json.dumps(event.get("data"), sort_keys=True))
    local = {key(event) for event in events if not event.get("observed")}
    events = [event for event in events if not (event.get("observed") and key(event) in local)]
    actor = lambda data: (data.get("actor") or {}).get("name") or "?"
    label = next((event["data"].get("label") for event in events if event["type"] == "session.start"), "")
    end = next((event["at"] for event in events if event["type"] == "session.stop"), "?")
    scenes, combats, checks, conditions = {}, {}, [], []
    for event in events:
        data, at = event.get("data") or {}, event["at"]
        if event["type"] == "scene.summary":
            scenes.setdefault(data.get("scene"), f"- {at} {data.get('name') or data.get('scene')}")
        elif event["type"] == "combat.start":
            combats[data.get("combat")] = {"start": at, "end": "?", "rounds": "?", "names": []}
        elif event["type"] in ("combat.turn", "combat.end"):
            combat = combats.setdefault((event.get("combat") or data.get("combat") or "").split(":")[0],
                                        {"start": "?", "end": "?", "rounds": "?", "names": []})
            if event["type"] == "combat.end":
                combat.update(end=at, rounds=data.get("rounds", "?"))
            elif data.get("actor") and actor(data) not in combat["names"]:  # a turn's end event has no actor
                combat["names"].append(actor(data))
        elif event["type"] == "pf2e.check":
            item = (data.get("item") or {}).get("name")
            total = (data.get("roll") or {}).get("total")
            checks.append(f"- {at} {actor(data)}: {item + ', ' if item else ''}{data.get('statistic') or data.get('ctype')}"
                          f" {data.get('outcome') or ''}{f', {total}' if total is not None else ''}{f' vs DC {data['dc']}' if data.get('dc') else ''}")
        elif event["type"] == "pf2e.condition":
            name = (data.get("item") or {}).get("name") or "?"
            conditions.append(f"- {at} {actor(data)}: {data.get('op') or ''} {name}{f' {data['value']}' if data.get('value') else ''}")
    started = datetime.fromisoformat(timeline["t0"]).astimezone()
    out = [f"# Flight Recorder: {label}\n", f"Started {started:%Y-%m-%d %H:%M}, ended {end}. Times are from the session start.",
           "Only what happened in Foundry: table talk, theatre of the mind and players who declined recording leave no trace.\n",
           "## Scenes\n", *scenes.values(), "", "## Combats\n",
           *(f"- {c['start']} to {c['end']}, {c['rounds']} rounds: {', '.join(c['names'])}" for c in combats.values()), "",
           "## Checks\n", *checks, "", "## Conditions\n", *conditions]
    return "\n".join(out) + "\n", started.date().isoformat()
