"""Bring a running Foundry world up to date with the campaign notes.

The notes are the desired state. Every world document the sync owns carries
`flags.ttrpg` with a hash of its data and the same deterministic id as the
journal pack `export-foundry` builds, so links between pages keep working. The
sync never touches a document without that flag.

It talks to the foundry-mcp backend (the fork with the `sync-world` tool) as a
second client of its control channel, JSON lines on 127.0.0.1:31414, beside
the instance Claude Code runs; the GM's browser must be connected to it.
"""

import hashlib
import json
import socket
from datetime import datetime, timedelta

from . import vault
from .foundry_export import Exporter, foundry_id, page_hash
from .foundry_sync import new_report, note_body, pull_page
from .hexmap import CELL, hex_centre
from .check import in_game_key

HOST, PORT = "127.0.0.1", 31414
# Bytes per apply call: the bridge's WebRTC channel takes 64 KB a message and each query 10 s.
BATCH = 40_000
TYPES = ["Folder", "JournalEntry", "JournalEntryPage", "Actor", "Item", "ActiveEffect", "Note"]
DEAD = {"fr": "Mort", "en": "Dead"}
CLOCKS = "global-progress-clocks.activeClocks"
# pf2e world clock: the in-game year is the real one plus the theme's offset.
YEAR_OFFSET = {"AR": 2700, "IC": 5200, "CE": 0}
NOT_CONNECTED = ("\nNo GM browser is connected: open the world as a GM in a browser on this machine, with the module "
                 "Foundry MCP Bridge active in that world.")


class Backend:
    """A client of the foundry-mcp backend's control channel."""

    def __init__(self, host=HOST, port=PORT, timeout=60):
        try:
            self.socket = socket.create_connection((host, port), timeout=timeout)
        except OSError as error:
            raise SystemExit(f"foundry-mcp backend not reachable on {host}:{port} ({error}): start it with "
                             "`node <foundry-vtt-mcp>/packages/mcp-server/dist/backend.js` (Claude Code with the "
                             "foundry-mcp server starts it too), then open the world as GM in a browser") from None
        self.stream = self.socket.makefile("rwb")
        self.count = 0

    def call(self, tool, **args):
        self.count += 1
        request = {"id": str(self.count), "method": "call_tool", "params": {"name": tool, "args": args}}
        self.stream.write((json.dumps(request, ensure_ascii=False) + "\n").encode())
        self.stream.flush()
        reply = json.loads(self.stream.readline())
        if "error" in reply:
            raise SystemExit(f"foundry-mcp: {reply['error'].get('message')}")
        text = reply["result"]["content"][-1]["text"]
        if reply["result"].get("isError"):
            hint = NOT_CONNECTED if "not connected" in text else ""
            raise SystemExit(f"foundry-mcp: {text}{hint}")
        return json.loads(text)

    def world(self):
        """The world the GM's browser is in: its id and title."""
        return self.call("get-world-info")

    def sync(self, **args):
        result = self.call("sync-world", **args)
        if isinstance(result, dict) and result.get("error"):
            raise SystemExit(f"foundry-mcp: {result['error']} (is the connected user a GM, writes allowed in the bridge settings?)")
        return result


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def ours(flags, campaign, known):
    """A world document, clock or cell belongs to this campaign when it carries its id; one synced before
    campaigns were marked belongs to it only if this campaign still wants it (never deleted, never another's)."""
    flags = flags or {}
    return flags.get("campaign") == campaign or ("campaign" not in flags and known)


def managed(document_name, _id, data, parent=None):
    """A desired document: its data carries flags.ttrpg.hash, the hash of everything else."""
    data = json.loads(json.dumps(data))
    data.pop("_key", None)
    data.setdefault("flags", {}).setdefault("ttrpg", {})
    data["flags"]["ttrpg"]["hash"] = digest(data)
    document = {"documentName": document_name, "_id": _id, "data": data}
    if parent:
        document["parent"] = parent
    return document


def actors_and_items(exporter):
    """Actors and items the notes define.

    An npc or item with `stats` (a compendium uuid) becomes a world copy named as the note,
    with its `adjust`ment. An npc linked to an adventure actor (`foundry: Actor.<id>`) is adopted
    only when the notes have something to write on it: its `owners` (players by user name) or
    its death (a dead status effect). A copy can have owners and die too.
    """
    documents = []
    for note in exporter.notes:
        if note.type not in ("npc", "item"):
            continue
        title = note.meta.get("title") or note.id
        flags = {"id": note.id, "path": note.rel}
        owners = {f"@{name}": 3 for name in note.get("owners") or []}
        flags["owners"] = sorted(note.get("owners") or [])
        stats, foundry = note.get("stats"), str(note.get("foundry") or "")
        if stats:
            name = "Actor" if note.type == "npc" else "Item"
            _id = foundry_id(exporter.module_id, name.lower(), note.id)
            data = {"name": title, "flags": {"ttrpg": {**flags, "source": stats, "adjust": note.get("adjust")}}}
            if name == "Actor":
                data["prototypeToken"] = {"name": title}
            if owners:
                data["ownership"] = owners
            document = managed(name, _id, data)
            document["source"] = stats
            if note.get("adjust"):
                document["adjust"] = note.get("adjust")
            documents.append(document)
        elif note.type == "npc" and foundry.startswith("Actor.") and (owners or note.get("state") == "dead"):
            _id = foundry.split(".")[1]
            data = {"flags": {"ttrpg": {**flags, "adopted": True}}}
            if owners:
                data["ownership"] = owners
            document = managed("Actor", _id, data)
            document["adopt"] = True
            documents.append(document)
        else:
            continue
        if note.type == "npc" and note.get("state") == "dead":
            dead = DEAD.get(exporter.config.get("language"), DEAD["en"])
            documents.append(managed("ActiveEffect", foundry_id(exporter.module_id, "dead", note.id),
                                     {"name": dead, "img": "icons/svg/skull.svg", "statuses": ["dead"], "flags": {"ttrpg": {"id": note.id, "path": note.rel}}},
                                     f"Actor.{documents[-1]['_id']}"))
    return documents


def map_pins(exporter):
    """A pin per place the notes put on a region map (`map` and `cells`, the map note giving the scene and
    its `grid` size): at the centre of the place's first cell, opening its page; places sharing a cell sit
    side by side. Foundry shows a pin to the users who can read its page, so players only see those of
    `visibility: players` places."""
    cells = {}
    for note in sorted(exporter.notes, key=lambda note: note.id):
        scene, listed = exporter.map_scene(note.get("map")), note.get("cells")
        size = exporter.campaign.notes[str(note.get("map"))].get("grid") if scene else None
        if isinstance(size, int) and isinstance(listed, list) and listed and CELL.fullmatch(str(listed[0])):  # the checker reports a bad cell
            cells.setdefault((scene, size, listed[0]), []).append(note)
    documents = []
    for (scene, size, cell), notes in cells.items():
        # ponytail: region maps are hex columns, odd columns down (map-ready builds them so); another
        # grid needs the scene's grid type, which sync-world does not return yet.
        x, y = hex_centre(*(int(part) for part in cell.split("_")), size)
        for index, note in enumerate(notes):
            entry, page = exporter.pages[note.id]
            documents.append(managed("Note", foundry_id(exporter.module_id, "pin", note.id),
                                     {"entryId": entry, "pageId": page, "y": round(y),
                                      "x": round(x + (index - (len(notes) - 1) / 2) * size / 3),
                                      "text": note.meta.get("title") or note.id,
                                      "flags": {"ttrpg": {"id": note.id, "path": note.rel}}}, scene))
    return documents


def desired(exporter):
    """The world documents the notes describe: one folder, a journal per category, a page per note,
    the actors and items of `actors_and_items`, and the pins of `map_pins`."""
    name = exporter.config.get("name", "Campagne")
    folder = foundry_id(exporter.module_id, "folder", "journal")
    # The folder also remembers the in-game date the sync last gave the world clock.
    documents = [managed("Folder", folder, {"name": name, "type": "JournalEntry", "sorting": "m",
                                            "flags": {"ttrpg": {"date": current_date(exporter.campaign)}}})]
    for entry in exporter.entries():
        pages = entry.pop("pages")
        documents.append(managed("JournalEntry", entry["_id"], {**entry, "folder": folder}))
        documents += [managed("JournalEntryPage", page["_id"], page, f"JournalEntry.{entry['_id']}") for page in pages]
    documents += actors_and_items(exporter)
    documents += map_pins(exporter)
    # Several campaigns can share a world: each document names its campaign (the module id).
    for document in documents:
        flags = document["data"]["flags"]["ttrpg"]
        flags.pop("hash")
        flags["campaign"] = exporter.module_id
        flags["hash"] = digest(document["data"])
    return documents


def key(document):
    return document["documentName"], document["_id"]


def plan(documents, world):
    """create / update / delete lists, and the pages edited in Foundry since the last sync."""
    want = {key(document): document for document in documents}
    have = {key(document): document for document in world}
    create = [document for k, document in want.items() if k not in have and not document.get("adopt")]
    adopt = [document for k, document in want.items() if k not in have and document.get("adopt")]
    update = [document for k, document in want.items()
              if k in have and (have[k].get("flags") or {}).get("hash") != document["data"]["flags"]["ttrpg"]["hash"]]
    gone = {k for k in have if k not in want}
    # A document the sync adopted is never deleted: it only loses its flags.
    release = [{"documentName": k[0], "_id": k[1], "data": {"flags.-=ttrpg": None}, "flags": have[k]["flags"]} for k in gone
               if (have[k].get("flags") or {}).get("adopted")]
    gone -= {key(document) for document in release}
    # Ownership the sync granted and the notes no longer give is taken back (level 0).
    for document in update + release:
        if document["documentName"] not in ("Actor", "Item"):
            continue
        before = set((have[key(document)].get("flags") or {}).get("owners") or [])
        now = set(((document.get("data") or {}).get("flags") or {}).get("ttrpg", {}).get("owners") or [])
        if before - now:
            document["data"]["ownership"] = {**document["data"].get("ownership", {}), **{f"@{name}": 0 for name in sorted(before - now)}}
    # Deleting an entry deletes its pages.
    delete = [{k: v for k, v in document.items() if k != "markdown"} for k, document in have.items()
              if k in gone and not (document.get("parent") and tuple(document["parent"].split(".")) in gone)]
    edited = []
    for k, document in have.items():
        if k[0] != "JournalEntryPage" or "markdown" not in document:
            continue
        current = page_hash(document["markdown"])
        target = want.get(k, {}).get("data", {}).get("flags", {}).get("ttrpg", {}).get("exported")
        if current != (document.get("flags") or {}).get("exported") and current != target:
            edited.append(document)
    order = {name: index for index, name in enumerate(TYPES)}
    create.sort(key=lambda document: order[document["documentName"]])
    delete.sort(key=lambda document: -order[document["documentName"]])
    return {"adopt": adopt, "create": create, "update": update, "release": release, "delete": delete, "edited": edited}


def batches(action, documents):
    """Consecutive calls of at most BATCH bytes, keeping the given order."""
    batch, size = [], 0
    for document in documents:
        length = len(json.dumps(document, ensure_ascii=False).encode())
        if batch and size + length > BATCH:
            yield {action: batch}
            batch, size = [], 0
        batch.append(document)
        size += length
    if batch:
        yield {action: batch}


def label(document):
    """What a planned document is, for the GM: its note path when it has one."""
    data = document.get("data") or {}
    flags = (data.get("flags") or {}).get("ttrpg") or document.get("flags") or {}
    name = data.get("name")
    return flags.get("path") or name or f"{document['documentName']} {document['_id']}"


def current_date(campaign):
    """The in-game date play has reached: the last session's, else the last played event's, else the start."""
    dates = [note.get("ingame") for note in campaign.notes.values() if note.type == "session"]
    dates += [note.get("date") for note in campaign.notes.values() if note.type == "event" and note.get("played") == "yes"]
    dates = [str(value) for value in dates if value]
    return max(dates, key=in_game_key) if dates else (str(campaign.config["start"]) if campaign.config.get("start") else None)


def world_time(date, clock, now):
    """pf2e world time (seconds since the world's creation) for an in-game date, keeping the time of day."""
    created = datetime.fromisoformat(clock["worldCreatedOn"].replace("Z", "+00:00"))
    offset = YEAR_OFFSET.get(clock.get("dateTheme"))
    if offset is None:
        return None
    year, month, day = (int(part) for part in date.lstrip("-").split("-"))
    current = created + timedelta(seconds=now)
    target = current.replace(year=year - offset, month=month, day=day)
    return int((target - created).total_seconds())


def clocks(exporter):
    """Global Progress Clocks entries, one per clock note; `ttrpg.value` remembers what was pushed."""
    out = {}
    for note in exporter.notes:
        if note.type != "clock":
            continue
        _id = foundry_id(exporter.module_id, "clock", note.id)
        filled = int(note.get("filled") or 0)
        out[_id] = {"id": _id, "type": "clock", "name": note.meta.get("title") or note.id, "value": filled,
                    "max": int(note.get("segments")), "private": note.get("visibility") != "players",
                    "ttrpg": {"id": note.id, "path": note.rel, "value": filled, "campaign": exporter.module_id}}
    return out


def parse_date(date):
    year, month, day = (int(part) for part in date.lstrip("-").split("-"))
    return (-year if date.startswith("-") else year, month, day)


def date_step(date, backend, pushed):
    """(world time to set, or None; True when Foundry's date is past the notes').

    The notes' date wins while Foundry's still shows what the last sync set (or nothing was
    synced yet); once the GM has moved time on in play, the sync only ever moves it forward.
    Simple Calendar converts dates when it is active, else the pf2e world clock does.
    """
    year, month, day = parse_date(date)
    calendar = backend.sync(op="calendar", date={"year": year, "month": month - 1, "day": day - 1})
    if calendar.get("active"):
        current = calendar["current"]
        world = (current["year"], current["month"] + 1, current["day"] + 1)
        target, worldtime = (year, month, day), calendar["timestamp"]
    else:
        clock = backend.sync(op="setting", key="pf2e.worldClock")["value"] or {}
        now = backend.sync(op="time")["worldTime"]
        worldtime = world_time(date, clock, now) if clock.get("worldCreatedOn") else None
        if worldtime is None:
            return None, False
        created = datetime.fromisoformat(clock["worldCreatedOn"].replace("Z", "+00:00"))
        offset = YEAR_OFFSET[clock.get("dateTheme")]
        shown = (created + timedelta(seconds=now)).date()
        world, target = (shown.year + offset, shown.month, shown.day), (year, month, day)
    if target != world and (pushed in (None, world) or target > world):
        return worldtime, False
    return None, target < world


def explored(exporter):
    """World Explorer cells to reveal, per map scene: those of the places the PCs discovered."""
    out = {}
    for note in exporter.notes:
        if note.get("discovered") != "yes" or not note.get("map") or not note.get("cells"):
            continue
        scene = str(exporter.campaign.notes[note.get("map")].get("foundry") or "") if note.get("map") in exporter.campaign.notes else ""
        if not scene.startswith("Scene."):
            continue
        for cell in note.get("cells"):
            if not isinstance(cell, str) or cell.count("_") != 1:
                continue  # the checker reports it
            i, j = (int(part) for part in cell.split("_"))
            out.setdefault(scene, {})[f"{i}_{j}"] = {"offset": {"i": i, "j": j}, "reveal": True,
                                                     "ttrpg": {"id": note.id, "campaign": exporter.module_id}}
    return out


def campaign_pages(exporter):
    """AP page uuid -> the campaign note that replaces it: `km-a23-dueling-chamber` -> `a23-dueling-chamber`,
    the id the compile skill gives a subject with one main AP page."""
    out = {}
    for note in exporter.campaign.notes.values():
        source = str(note.meta.get("source") or "")
        if not note.rel.startswith("adventure/") or ".JournalEntryPage." not in source or "-" not in note.id:
            continue
        target = note.id.split("-", 1)[1]
        if target in exporter.pages and not exporter.campaign.notes[target].rel.startswith("adventure/"):
            out[source] = target
    return out


def pins(exporter, backend):
    """Map pins of the map notes' scenes that open an AP page with a campaign note: point them at the note's
    page, remembering the original; released (original restored) when the note no longer exists."""
    mapping, changes = campaign_pages(exporter), []
    for note in exporter.notes:
        scene = str(note.get("foundry") or "")
        if note.type != "map" or not scene.startswith("Scene."):
            continue
        listed = backend.sync(op="scene-notes", uuid=scene)
        for pin in listed["notes"]:
            flags = pin.get("flags") or {}
            original = flags.get("original") or {"entryId": pin.get("entryId"), "pageId": pin.get("pageId")}
            target = mapping.get(f"JournalEntry.{original['entryId']}.JournalEntryPage.{original['pageId']}")
            if target:
                entry, page = exporter.pages[target]
                if (pin.get("entryId"), pin.get("pageId"), flags.get("id")) != (entry, page, target):
                    changes.append({"documentName": "Note", "parent": scene, "_id": pin["_id"],
                                    "data": {"entryId": entry, "pageId": page,
                                             "flags": {"ttrpg": {"id": target, "path": exporter.campaign.notes[target].rel, "original": original}}}})
            elif "original" in flags:  # a pin of `map_pins` has none: it is the sync's own
                changes.append({"documentName": "Note", "parent": scene, "_id": pin["_id"],
                                "data": {**original, "flags.-=ttrpg": None}, "flags": flags})
    return changes


def world_state(exporter, backend, world=()):
    """The date and clocks steps: what to set, and what the GM changed in Foundry since the last sync."""
    steps = {"time": None, "time_ahead": None, "clocks": {}, "clocks_remove": [], "clocks_edited": [], "explore": [],
             "pins": pins(exporter, backend)}
    # Map exploration: only the cells the sync revealed are ever hidden again; the GM's stay.
    wanted = explored(exporter)
    scenes = set(wanted) | {d["parent"] for d in world if d.get("parent", "").startswith("Scene.")}
    for note in exporter.notes:
        if note.type == "map" and str(note.get("foundry") or "").startswith("Scene."):
            scenes.add(note.get("foundry"))
    for scene in sorted(scenes):
        current = backend.sync(op="flag", uuid=scene, scope="world-explorer", key="gridData")
        if not current["exists"]:
            continue
        cells = current["value"] or {}
        want = wanted.get(scene, {})
        mine = {key for key, value in cells.items() if isinstance(value, dict) and value.get("ttrpg")
                and ours(value["ttrpg"], exporter.module_id, key in want)}
        change = {key: value for key, value in want.items() if cells.get(key) != value}
        remove = sorted(mine - set(want))
        if change or remove:
            steps["explore"].append({"uuid": scene, "set": change, "remove": remove})
    date = current_date(exporter.campaign)
    if date:
        pushed = next((d.get("flags", {}).get("date") for d in world if d["documentName"] == "Folder"), None)
        worldtime, ahead = date_step(date, backend, parse_date(pushed) if pushed else None)
        if worldtime is not None:
            steps["time"] = {"date": date, "worldTime": worldtime}
        if ahead:
            steps["time_ahead"] = date
    try:
        current = backend.sync(op="setting", key=CLOCKS)["value"] or {}
    except SystemExit as error:
        if "not a registered" not in str(error):
            raise
        return steps  # the clocks module is not enabled in this world
    want = clocks(exporter)
    mine = {key: value for key, value in current.items() if isinstance(value, dict) and value.get("ttrpg")
            and ours(value["ttrpg"], exporter.module_id, key in want)}
    edited = {key for key, value in mine.items()
              if key in want and value.get("value") not in (value["ttrpg"].get("value"), want[key]["value"])}
    steps["clocks_edited"] = [mine[key] for key in sorted(edited)]
    steps["clocks"] = {key: value for key, value in want.items() if current.get(key) != value and key not in edited}
    steps["clocks_remove"] = sorted(key for key in mine if key not in want)
    return steps


def held(exporter, document):
    """Whether the notes already hold a page's Foundry text."""
    flags = document.get("flags") or {}
    note = exporter.campaign.notes.get(flags.get("id"))
    return note is not None and note_body(exporter, note, document["markdown"], flags.get("header") or "").strip() == note.body.strip()


def sync(root, backend, apply=False, force=False):
    exporter = Exporter(vault.load(root))
    want = desired(exporter)
    known = {key(document) for document in want}
    world = [document for document in backend.sync(op="inventory", types=TYPES, text=True)["documents"]
             if ours(document.get("flags"), exporter.module_id, key(document) in known)]
    steps = plan(want, world)
    # Text the notes already hold is not an edit to lose: after a pull, Foundry may still carry what the GM
    # typed (a Markdown callout, a src: link) where the export writes its own form.
    steps["edited"] = [document for document in steps["edited"] if not held(exporter, document)]
    steps.update(world_state(exporter, backend, world))
    if force:
        # Overwrite what changed in Foundry with the notes, even where the notes did not change.
        want = {key(document): document for document in desired(exporter)}
        queued = {key(document) for document in steps["update"]}
        steps["update"] += [want[key(document)] for document in steps["edited"]
                            if key(document) in want and key(document) not in queued]
        steps["clocks"].update({key: clocks(exporter)[key] for key in (c["id"] for c in steps["clocks_edited"])})
    if apply and (steps["edited"] or steps["clocks_edited"]) and not force:
        return steps, None
    done = None
    if apply:
        done = {"created": 0, "updated": 0, "deleted": 0, "missing": []}
        for action in ("adopt", "create", "update", "release", "delete"):
            for call in batches("update" if action == "release" else action, steps[action]):
                for name, value in backend.sync(op="apply", **call).items():
                    done[name] += value
        if steps["time"]:
            backend.sync(op="time", worldTime=steps["time"]["worldTime"])
        for call in batches("adopt", steps["pins"]):
            done["updated"] += backend.sync(op="apply", **call)["updated"]
        for change in steps["explore"]:
            backend.sync(op="merge-flag", scope="world-explorer", key="gridData", **change)
        if steps["clocks"] or steps["clocks_remove"]:
            backend.sync(op="merge-setting", key=CLOCKS, set=steps["clocks"], remove=steps["clocks_remove"])
    return steps, done


def world_guard(config, world, apply):
    """Why this campaign must not be synced with the connected world, or None. `campaign.yaml` names its
    worlds (`world`: an id or a list, a test world beside the players' one): the GM's browser may be in another."""
    declared = config.get("world") or []
    declared = [declared] if isinstance(declared, str) else declared
    if world["id"] in declared:
        return None
    if declared:
        return f"this campaign syncs with {', '.join(declared)} (campaign.yaml `world`), not with {world['id']}"
    if apply:
        return f"campaign.yaml names no world: add `world: {world['id']}` to sync this campaign with {world['title']}"
    return None


def pull(root, backend):
    exporter = Exporter(vault.load(root))
    report = new_report()
    known = {key(document) for document in desired(exporter)}
    for document in backend.sync(op="inventory", types=["JournalEntryPage"], text=True)["documents"]:
        if not ours(document.get("flags"), exporter.module_id, key(document) in known):
            continue
        page = {"_id": document["_id"], "flags": {"ttrpg": document.get("flags")},
                "text": {"format": 2, "markdown": document.get("markdown", "")}}
        pull_page(exporter, document["parent"].split(".")[1], page, report)
    for clock in world_state(exporter, backend)["clocks_edited"]:
        note = exporter.campaign.notes.get(clock["ttrpg"]["id"])
        if note is None:
            continue
        meta = dict(note.meta, filled=int(clock["value"]))
        note.path.write_text(vault.join_frontmatter(meta, note.body), encoding="utf-8")
        report["updated"].append(note.rel)
    return report
