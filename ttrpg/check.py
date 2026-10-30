"""Coherence checks for a campaign repository. Run before every commit and in CI."""

import json
import re
from datetime import date as Date

from . import vault
from .vault import SCHEMA, SOURCE, UUID, WIKILINK, MDLINK, fields_for, body_hash

DATE = re.compile(r"(-?\d{1,5})-(\d{2})-(\d{2})")
INDEXED = ("Actor", "Scene", "RollTable", "Item", "Macro", "Playlist")


class Report:
    def __init__(self):
        self.items = []

    def error(self, where, message):
        self.items.append(("error", where, message))

    def warn(self, where, message):
        self.items.append(("warning", where, message))

    @property
    def errors(self):
        return [item for item in self.items if item[0] == "error"]

    def __str__(self):
        return "\n".join(f"{where}: {level}: {message}" for level, where, message in self.items)


def check(root, fix=False):
    campaign = vault.load(root)
    report = Report()
    check_config(campaign, report)
    for note, first in campaign.duplicates:
        report.error(note.rel, f"duplicate id {note.id!r}, also {first.rel}")
    foundry_index = load_foundry_index(campaign)
    for note in campaign.notes.values():
        if note.error:
            report.error(f"{note.rel}:1", note.error)
            continue
        check_fields(campaign, note, report)
        check_body(campaign, note, foundry_index, report)
        check_origin(note, report, fix)
    check_chronology(campaign, report)
    return campaign, report


def check_config(campaign, report):
    config = campaign.config
    if not config:
        report.error("campaign.yaml", "missing or empty")
        return
    for key in ("name", "system", "language"):
        if not config.get(key):
            report.error("campaign.yaml", f"missing {key}")
    for source_id, source in (config.get("sources") or {}).items():
        if not isinstance(source, dict) or not isinstance(source.get("pages"), int):
            report.error("campaign.yaml", f"source {source_id!r} needs an integer pages count")


def load_foundry_index(campaign):
    path = campaign.root / ".foundry" / "index.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def check_fields(campaign, note, report):
    where = f"{note.rel}:1"
    note_type = note.type
    if note_type not in SCHEMA["types"]:
        report.error(where, f"unknown type {note_type!r}")
        return
    specs = fields_for(note_type)
    for name, spec in specs.items():
        if spec.get("required") and note.meta.get(name) in (None, ""):
            report.error(where, f"missing required field {name!r}")
    for name, value in note.meta.items():
        spec = specs.get(name)
        if spec is None:
            report.warn(where, f"unknown field {name!r} for type {note_type}")
            continue
        problem = field_problem(campaign, spec, value)
        if problem:
            report.error(where, f"{name}: {problem}")
    if note_type == "clock" and isinstance(note.get("filled"), int) and isinstance(note.get("segments"), int):
        if not 0 <= note.get("filled") <= note.get("segments"):
            report.error(where, "filled must be between 0 and segments")
    if note_type == "npc" and note.get("died") and note.get("state") != "dead":
        report.error(where, "died is set but state is not dead")


def field_problem(campaign, spec, value):
    kind = spec["kind"]
    if value is None:
        return ""
    if kind == "enum":
        values = spec.get("values") or list(SCHEMA["types"])
        return "" if value in values else f"{value!r} not in {values}"
    if kind == "str":
        return "" if isinstance(value, str) else "must be text"
    if kind == "int":
        return "" if isinstance(value, int) and not isinstance(value, bool) else "must be an integer"
    if kind == "list":
        return "" if isinstance(value, list) else "must be a list"
    if kind == "date":
        return "" if isinstance(value, str) and DATE.fullmatch(value) else "must be a quoted in-game date YYYY-MM-DD"
    if kind == "day":
        return "" if isinstance(value, Date) or (isinstance(value, str) and DATE.fullmatch(value)) else "must be YYYY-MM-DD"
    targets = value if kind == "refs" else [value]
    if kind == "refs" and not isinstance(value, list):
        return "must be a list of note ids"
    for target in targets:
        target_id = strip_link(target)
        other = campaign.notes.get(target_id)
        if other is None:
            return f"unknown note {target_id!r}"
        if spec.get("to") and other.type not in spec["to"]:
            return f"{target_id!r} is a {other.type}, expected {'/'.join(spec['to'])}"
    return ""


def strip_link(value):
    """Accept `id` and `[[id]]` in frontmatter, since Obsidian writes the latter."""
    value = str(value).strip()
    return value[2:-2].split("|")[0] if value.startswith("[[") and value.endswith("]]") else value


def check_body(campaign, note, foundry_index, report):
    sources = campaign.config.get("sources") or {}
    players = note.get("visibility") == "players"
    for match in WIKILINK.finditer(note.body):
        where = f"{note.rel}:{note.line_of(match.start())}"
        embed, target = match[1], match[2].strip()
        if embed and "." in target:
            if target not in campaign.assets:
                report.error(where, f"missing asset {target!r}")
            continue
        other = campaign.notes.get(target)
        if other is None:
            report.error(where, f"broken link [[{target}]]")
        elif players and other.get("visibility") != "players":
            report.error(where, f"players note links GM-only note [[{target}]]")
    for match in MDLINK.finditer(note.body):
        report.error(f"{note.rel}:{note.line_of(match.start())}", f"relative link ({match[1]}): use [[id]] instead")
    for match in SOURCE.finditer(note.body):
        where = f"{note.rel}:{note.line_of(match.start())}"
        source = sources.get(match[1])
        if source is None:
            report.error(where, f"unknown source {match[1]!r} (declare it in campaign.yaml)")
        elif isinstance(source.get("pages"), int) and not 1 <= int(match[2]) <= source["pages"]:
            report.error(where, f"page {match[2]} outside {match[1]} (1-{source['pages']})")
    for match in UUID.finditer(note.body):
        where = f"{note.rel}:{note.line_of(match.start())}"
        uuid = match[1]
        if "JournalEntry" in uuid and not uuid.startswith("Compendium."):
            report.error(where, f"Foundry journal link @UUID[{uuid}]: use [[id]] instead")
        elif foundry_index is not None and uuid.split(".")[0] in INDEXED and ".".join(uuid.split(".")[:2]) not in foundry_index:
            report.error(where, f"unknown Foundry document @UUID[{uuid}]")


def check_origin(note, report, fix):
    if note.get("origin") != "ap" or not note.meta.get("source_hash"):
        return
    if body_hash(note.body) == note.meta["source_hash"]:
        return
    if fix:
        note.meta["origin"] = "modified"
        note.path.write_text(vault.join_frontmatter(note.meta, note.body), encoding="utf-8")
        report.warn(f"{note.rel}:1", "body differs from the imported AP text: origin set to modified")
    else:
        report.error(f"{note.rel}:1", "body differs from the imported AP text: set origin: modified (or run check --fix)")


def check_chronology(campaign, report):
    notes = campaign.notes.values()
    deaths = {note.id: note.get("died") for note in notes if note.type == "npc" and note.get("died")}
    for note in notes:
        if note.type == "event" and isinstance(note.get("date"), str):
            for participant in note.get("participants") or []:
                died = deaths.get(strip_link(participant))
                if died and in_game_key(note.get("date")) > in_game_key(died):
                    report.error(f"{note.rel}:1", f"{strip_link(participant)} died {died}, before this event ({note.get('date')})")
    sessions = sorted((str(note.get("day")), note) for note in notes if note.type == "session" and note.get("ingame"))
    for (_, before), (_, after) in zip(sessions, sessions[1:]):
        if in_game_key(after.get("ingame")) < in_game_key(before.get("ingame")):
            report.error(f"{after.rel}:1", f"in-game date {after.get('ingame')} goes back before {before.rel} ({before.get('ingame')})")
    for note in notes:
        if note.type != "session" or not isinstance(note.get("ingame"), str):
            continue
        for match in WIKILINK.finditer(note.body):
            died = deaths.get(match[2].strip())
            if died and in_game_key(note.get("ingame")) > in_game_key(died):
                report.warn(f"{note.rel}:{note.line_of(match.start())}", f"mentions {match[2].strip()}, dead since {died}")


def in_game_key(value):
    return tuple(map(int, DATE.fullmatch(str(value)).groups()))
