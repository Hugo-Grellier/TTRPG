"""Draft campaign notes for the subjects a compile inventory lists, so links and fields can point at them
before they are compiled. Existing notes are never touched."""

import csv
from pathlib import Path

from . import vault

FOLDERS = {"npc": "npcs", "faction": "factions", "location": "places", "settlement": "places", "hex": "places",
           "region": "places", "scene": "scenes", "item": "items", "quest": "quests", "handout": "handouts", "mystery": "mysteries",
           "pc": "pcs", "company": "pcs", "chapter": "arcs", "clock": "clocks", "event": "events"}


def drafts(root, inventory):
    """Write a `prep: draft` note per inventory row (type, id, title, aliases, main_page, pages, tier) with no note yet.
    `pages` (semicolon-separated) holds AP note ids or library citations `book#pN` (declare the books first)."""
    root = Path(root)
    existing = {path.stem for path in root.rglob("*.md") if "tools" not in path.relative_to(root).parts}
    made, skipped = [], []
    with open(inventory, encoding="utf-8") as tsv:
        for row in csv.DictReader(tsv, delimiter="\t"):
            kind, note_id = (row.get("type") or "").strip(), (row.get("id") or "").strip()
            if kind not in FOLDERS or not note_id or note_id in existing:
                skipped.append(note_id)
                continue
            split = lambda field: [part.strip() for part in (row.get(field) or "").split(";") if part.strip()]
            # A page is an AP note id or a library citation `book#pN`; a subject without any is the campaign's own.
            cited = [page for page in split("pages") if "#p" in page]
            pages = [page for page in split("pages") if page in existing]
            meta = {"type": kind, "title": row["title"].strip(), "origin": "ap" if cited or pages else "custom", "prep": "draft"}
            if aliases := [alias for alias in split("aliases") if alias != meta["title"]]:
                meta["aliases"] = aliases
            if (row.get("tier") or "").strip() == "major":
                meta["tags"] = ["major"]
            sources = [f"- [[{page}]]\n" for page in pages] + [f"- [p. {page.split('#p')[1]}](src:{page})\n" for page in cited]
            body = "> [!todo] Fiche à compléter depuis ses sources.\n\nSources :\n" + "".join(sources) if sources else "> [!todo] Fiche à écrire.\n"
            path = root / FOLDERS[kind] / f"{note_id}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(vault.join_frontmatter(meta, body), encoding="utf-8")
            existing.add(note_id)
            made.append(path.relative_to(root).as_posix())
    return made, skipped
