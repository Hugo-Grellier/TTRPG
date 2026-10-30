"""Import a Foundry Adventure document into campaign notes.

Journal pages become Markdown notes under adventure/<journal>/, typed by the
module's map file. Links between pages become [[id]]; links to actors, scenes,
tables and compendium entries stay as Foundry @UUID enrichers and are listed in
.foundry/index.json so the checker can verify them. Re-running the import
refreshes untouched AP notes and never overwrites a modified or custom one.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import yaml

from .html_md import to_markdown
from .vault import UUID, body_hash, join_frontmatter, split_frontmatter

TOOLS = Path(__file__).resolve().parent.parent
LABELS = {
    "fr": {"stats": "Statistiques", "todo": "Fiche à distiller depuis le texte de l'aventure.",
           "pages": "Pages AP", "scene": "Scène Foundry", "pins": "Épingles"},
    "en": {"stats": "Statistics", "todo": "Draft: distill from the adventure text.",
           "pages": "AP pages", "scene": "Foundry scene", "pins": "Pins"},
}
INDEXED = {"actors": "Actor", "scenes": "Scene", "tables": "RollTable", "items": "Item",
           "macros": "Macro", "playlists": "Playlist"}


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def unpack(pack_dir):
    """Return the Adventure documents of a LevelDB pack, via the Foundry CLI."""
    if not (TOOLS / "node_modules" / "@foundryvtt" / "foundryvtt-cli").is_dir():
        raise SystemExit(f"Foundry CLI missing: run `npm ci` in {TOOLS}")
    with tempfile.TemporaryDirectory() as work:
        # LevelDB writes its log and manifest on open: never open a live module's pack.
        copy, out = Path(work) / "pack", Path(work) / "json"
        shutil.copytree(pack_dir, copy, ignore=shutil.ignore_patterns("LOCK"))
        subprocess.run(["node", str(TOOLS / "ttrpg" / "unpack.mjs"), str(copy), str(out)], check=True)
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(out.glob("*.json"))]


def load_map(module_id):
    path = Path(__file__).parent / "maps" / f"{module_id}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {"rules": [], "skip": []}


def folder_names(adventure, folder_id):
    folders = {folder["_id"]: folder for folder in adventure.get("folders", [])}
    names = []
    while folder_id in folders:
        names.append(folders[folder_id]["name"])
        folder_id = folders[folder_id].get("folder")
    return names


def rule_for(mapping, adventure, journal):
    folders = folder_names(adventure, journal.get("folder"))
    for rule in mapping.get("rules", []):
        if rule.get("journal") == journal["name"] or rule.get("folder") in folders:
            return rule
    return {"top": "note", "rest": "note"}


def unique_npcs(adventure):
    """Named NPCs of the adventure, keyed by note id. They own the short ids."""
    npcs = {}
    for actor in adventure.get("actors", []):
        if actor.get("type") == "npc" and ((actor.get("system") or {}).get("traits") or {}).get("rarity") == "unique":
            npcs.setdefault(slug(actor["name"]), actor)
    return npcs


def map_ids(adventure):
    """One map note per scene, prefixed so it never takes a page's id."""
    ids, taken = {}, set()
    for scene in adventure.get("scenes", []):
        note_id = f"map-{slug(scene['name'])}"
        note_id = note_id if note_id not in taken else f"{note_id}-{slug(scene['_id'])}"
        taken.add(note_id)
        ids[scene["_id"]] = note_id
    return ids


def plan(adventure, mapping, prefix, reserved=()):
    """Assign every kept page an id, path and frontmatter before converting any link."""
    taken, pages, journals = set(reserved), {}, {}

    def claim(*candidates):
        for candidate in candidates:
            if candidate not in taken:
                taken.add(candidate)
                return candidate
        raise ValueError(f"no free id among {candidates}")

    for journal in sorted(adventure.get("journal", []), key=lambda j: (j.get("sort", 0), j["name"])):
        if journal["name"] in mapping.get("skip", []):
            continue
        rule = rule_for(mapping, adventure, journal)
        journal_slug = slug(journal["name"])
        journal_id = claim(journal_slug, f"{prefix}-{journal_slug}")
        journals[journal["_id"]] = {"id": journal_id, "dir": journal_slug, "journal": journal, "pages": []}
        parent = None
        for page in sorted(journal.get("pages", []), key=lambda p: p.get("sort", 0)):
            level = (page.get("title") or {}).get("level", 1)
            note_type = rule["top"] if level == 1 else rule["rest"]
            page_id = claim(slug(page["name"]), f"{journal_slug}-{slug(page['name'])}", f"{journal_slug}-{slug(page['_id'])}")
            meta = {"type": note_type, "title": page["name"], "origin": "ap",
                    "source": f"JournalEntry.{journal['_id']}.JournalEntryPage.{page['_id']}"}
            if rule.get("visibility"):
                meta["visibility"] = rule["visibility"]
            if level == 1:
                parent = page_id
            elif rule.get("parent") and parent:
                meta[rule["parent"]] = parent
            pages[page["_id"]] = {"id": page_id, "page": page, "meta": meta, "level": level,
                                  "path": f"adventure/{journal_slug}/{page_id}.md", "journal": journal["_id"]}
            journals[journal["_id"]]["pages"].append(page["_id"])
    return journals, pages


def convert_links(text, journals, pages, maps):
    def replace(match):
        uuid, label = match[1], match[2]
        target = uuid.split("#")[0]
        parts = target.split(".")
        note_id = None
        if target.startswith(".") and len(parts) == 2:
            note_id = pages.get(parts[1], {}).get("id")
        elif parts[0] == "JournalEntry" and len(parts) == 4:
            note_id = pages.get(parts[3], {}).get("id")
        elif parts[0] == "JournalEntry" and len(parts) == 2:
            note_id = journals.get(parts[1], {}).get("id")
        elif parts[0] == "Scene" and len(parts) == 2 and parts[1] in maps:
            note_id = maps[parts[1]]
        else:
            return match[0]
        if note_id is None:
            return label or match[0]
        return f"[[{note_id}|{label}]]" if label else f"[[{note_id}]]"
    return UUID.sub(replace, text)


def page_body(entry, journals, pages, maps):
    page = entry["page"]
    if page.get("type") == "image" and page.get("src"):
        return f"![{page['name']}]({page['src']})\n" + (f"\n{page['image']['caption']}\n" if (page.get("image") or {}).get("caption") else "")
    text = page.get("text") or {}
    body = text.get("markdown") if text.get("format") == 2 and text.get("markdown") else to_markdown(text.get("content") or "")
    return convert_links(body, journals, pages, maps)


def write_note(path, meta, body, stats):
    """Write an AP note unless the GM has taken it over."""
    if path.is_file():
        old_meta, old_body, _, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if old_meta.get("origin") != "ap" or body_hash(old_body) != old_meta.get("source_hash"):
            stats["kept"] += 1
            return
    meta = {**meta, "source_hash": body_hash(body)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(join_frontmatter(meta, body), encoding="utf-8")
    stats["written"] += 1


def seed_npc(path, actor, pages, stats, label):
    """Create a draft campaign NPC from a unique actor; never touch an existing one."""
    if path.is_file():
        return
    level = ((actor.get("system") or {}).get("details") or {}).get("level", {}).get("value")
    meta = {"type": "npc", "title": actor["name"], "origin": "ap", "prep": "draft", "foundry": f"Actor.{actor['_id']}"}
    if isinstance(level, int):
        meta["level"] = level
    mentions = [entry for entry in pages.values() if actor["_id"] in json.dumps(entry["page"].get("text") or {})]
    lines = [f"{label['stats']} : @UUID[Actor.{actor['_id']}]{{{actor['name']}}}", "",
             f"> [!todo] {label['todo']}", ""]
    lines += [f"{label['pages']} :"] + [f"- [[{entry['id']}]]" for entry in mentions] if mentions else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(join_frontmatter(meta, "\n".join(lines).rstrip() + "\n"), encoding="utf-8")
    stats["seeded"] += 1


def seed_map(path, scene, pages, stats, label):
    """Create a campaign map note from a Foundry scene; never touch an existing one."""
    if path.is_file():
        return
    level = next(iter(scene.get("levels") or []), {})
    image = (level.get("background") or {}).get("src") or (scene.get("background") or {}).get("src") or ""
    counts = {kind: len(scene.get(kind) or []) for kind in ("walls", "lights", "sounds", "tokens", "notes")}
    stage = "lit" if counts["walls"] and counts["lights"] else "walled" if counts["walls"] else "raw"
    meta = {"type": "map", "title": scene["name"], "origin": "ap", "prep": "draft",
            "foundry": f"Scene.{scene['_id']}", "stage": stage,
            "kind": "battle" if (scene.get("grid") or {}).get("type") == 1 else "overview"}
    if image:
        meta["image"] = image
    if isinstance((scene.get("grid") or {}).get("size"), int):
        meta["grid"] = scene["grid"]["size"]
    pinned = []
    for pin in scene.get("notes") or []:
        page_id = pages.get(pin.get("pageId") or "", {}).get("id")
        if page_id and page_id not in pinned:
            pinned.append(page_id)
    lines = ([f"![{scene['name']}]({image})", ""] if image else [])
    lines += [f"{label['scene']} : " + ", ".join(f"{count} {kind}" for kind, count in counts.items()), ""]
    lines += [f"{label['pins']} :"] + [f"- [[{page_id}]]" for page_id in pinned] if pinned else []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(join_frontmatter(meta, "\n".join(lines).rstrip() + "\n"), encoding="utf-8")
    stats["maps"] += 1


def remove_stale(root, planned, stats):
    """Delete untouched AP pages the module no longer has (or that moved)."""
    for path in (root / "adventure").rglob("*.md"):
        if path in planned:
            continue
        meta, body, _, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("origin") == "ap" and body_hash(body) == meta.get("source_hash"):
            path.unlink()
            stats["removed"] += 1


def import_adventure(root, adventure, module_id):
    root = Path(root)
    config = yaml.safe_load((root / "campaign.yaml").read_text(encoding="utf-8")) if (root / "campaign.yaml").is_file() else {}
    label = LABELS.get((config or {}).get("language"), LABELS["en"])
    mapping = load_map(module_id)
    npcs = unique_npcs(adventure)
    maps = map_ids(adventure)
    journals, pages = plan(adventure, mapping, slug(module_id), reserved=set(npcs) | set(maps.values()))
    stats = {"written": 0, "kept": 0, "seeded": 0, "maps": 0, "removed": 0}
    planned = {root / entry["path"] for entry in pages.values()}
    planned |= {root / "adventure" / journal["dir"] / f"{journal['id']}.md" for journal in journals.values()}
    if (root / "adventure").is_dir():
        remove_stale(root, planned, stats)
    for entry in pages.values():
        write_note(root / entry["path"], entry["meta"], page_body(entry, journals, pages, maps), stats)
    for note_id, actor in npcs.items():
        seed_npc(root / "npcs" / f"{note_id}.md", actor, pages, stats, label)
    for scene in adventure.get("scenes", []):
        seed_map(root / "maps" / f"{maps[scene['_id']]}.md", scene, pages, stats, label)
    for journal in journals.values():
        lines = []
        for page_id in journal["pages"]:
            entry = pages[page_id]
            lines.append("  " * (min(entry["level"], 3) - 1) + f"- [[{entry['id']}|{entry['page']['name']}]]")
        meta = {"type": "note", "title": journal["journal"]["name"], "origin": "ap",
                "source": f"JournalEntry.{journal['journal']['_id']}"}
        write_note(root / "adventure" / journal["dir"] / f"{journal['id']}.md", meta, "\n".join(lines) + "\n", stats)
    index = {f"{prefix}.{doc['_id']}": doc["name"]
             for key, prefix in INDEXED.items() for doc in adventure.get(key, [])}
    (root / ".foundry").mkdir(exist_ok=True)
    (root / ".foundry" / "index.json").write_text(json.dumps(index, indent=0, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    stats["indexed"] = len(index)
    return stats


def import_module(root, module_dir):
    module_dir = Path(module_dir)
    manifest = json.loads((module_dir / "module.json").read_text(encoding="utf-8"))
    total = {"written": 0, "kept": 0, "seeded": 0, "maps": 0, "removed": 0, "indexed": 0}
    for pack in manifest.get("packs", []):
        if pack.get("type") != "Adventure":
            continue
        for adventure in unpack(module_dir / pack["path"]):
            for key, value in import_adventure(root, adventure, manifest["id"]).items():
                total[key] += value
    return total
