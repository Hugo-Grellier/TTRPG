"""Bring journal pages edited in Foundry back into the campaign notes.

Reads the world's journal database (a copy, never the live files), finds the
pages exported by `export-foundry` (flags.ttrpg), and for each page whose text
changed since the export writes the note body back, with @UUID links turned
into [[id]] again. The GM reviews the result as a Git diff. When the note also
changed in the repository since the export, the repository wins: the page is
reported as a conflict and left alone.
"""

import re
from pathlib import Path

from . import vault
from .foundry_export import Exporter
from .foundry_import import unpack
from .html_md import to_markdown
from .vault import UUID, body_hash


def reverse_links(text, exporter):
    """Foundry Markdown back to repository Markdown."""
    by_page = {f"JournalEntry.{entry}.JournalEntryPage.{page}": note_id for note_id, (entry, page) in exporter.pages.items()}
    for note in exporter.campaign.notes.values():
        source = str(note.meta.get("source", ""))
        if source.startswith("JournalEntry.") and note.id not in exporter.pages:
            by_page[source] = note.id
        if note.type == "map" and note.meta.get("foundry"):
            by_page[note.meta["foundry"]] = note.id

    def link(match):
        uuid, label = match[1], match[2]
        target, _, anchor = uuid.partition("#")
        note_id = by_page.get(target)
        if note_id is None:
            return match[0]
        title = exporter.campaign.notes[note_id].meta.get("title")
        suffix = f"#{anchor}" if anchor else ""
        return f"[[{note_id}{suffix}]]" if not label or label == title else f"[[{note_id}{suffix}|{label}]]"

    text = UUID.sub(link, text)
    prefix = re.escape(f"modules/{exporter.module_id}/assets/")
    text = re.sub(r"!\[([^\]]*)\]\(" + prefix + r"([^)]+)\)", lambda m: f"![[{m[2]}|{m[1]}]]" if m[1] else f"![[{m[2]}]]", text)
    return re.sub(r"(?<!!)\[([^\]]*)\]\(" + prefix + r"([^)]+)\)", r"[[\2|\1]]", text)


def page_markdown(page):
    text = page.get("text") or {}
    if text.get("format") == 2 and text.get("markdown") is not None:
        return text["markdown"]
    return to_markdown(text.get("content") or "")


def pull(root, world_dir):
    campaign = vault.load(root)
    exporter = Exporter(campaign)
    report = {"updated": [], "conflicts": [], "unchanged": 0, "missing": []}
    for entry in unpack(Path(world_dir) / "data" / "journal"):
        for page in entry.get("pages", []):
            flags = (page.get("flags") or {}).get("ttrpg")
            if not flags:
                continue
            markdown = page_markdown(page)
            if body_hash(markdown) == flags.get("exported"):
                report["unchanged"] += 1
                continue
            note = campaign.notes.get(flags["id"])
            if note is None:
                report["missing"].append(flags["id"])
                continue
            if body_hash(note.body) != flags.get("body") or (flags.get("players") and "[!secret]" in note.body):
                # Repository wins; a player page was exported without its secrets, so its text cannot replace the note.
                report["conflicts"].append(note.rel)
                continue
            header = flags.get("header") or ""
            if header and markdown.startswith(header):
                markdown = markdown[len(header):]
            lead = note.body[: len(note.body) - len(note.body.lstrip("\n"))]
            body = lead + reverse_links(markdown.strip(), exporter) + "\n"
            meta = dict(note.meta)
            if meta.get("origin") == "ap" and meta.get("source_hash") and body_hash(body) != meta["source_hash"]:
                meta["origin"] = "modified"
            note.path.write_text(vault.join_frontmatter(meta, body), encoding="utf-8")
            report["updated"].append(note.rel)
    return report
