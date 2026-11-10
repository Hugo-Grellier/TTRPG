"""Bring journal pages edited in Foundry back into the campaign notes.

Reads the world's journal database (a copy, never the live files), finds the
pages exported by `export-foundry` (flags.ttrpg), and for each page whose text
changed since the export writes the note body back, with @UUID links turned
into [[id]] again. The GM reviews the result as a Git diff. When the note also
changed in the repository since the export, the repository wins: the page is
reported as a conflict and left alone.
"""

import re
from html import unescape
from pathlib import Path

from . import vault
from .foundry_export import CALLOUT, Exporter, page_hash
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


def from_foundry(text, exporter):
    """Undo foundry_markdown: HTML callouts back to `> [!kind] title`, cited spans back to src: links."""
    def cite(text):
        return re.sub(r'<span data-src="([^"#]+)#p(\d+)">(.*?) \(.*?, p\. \d+\)</span>', r"[\3](src:\1#p\2)", text)

    def quote(kind, own, inner):
        # Inline code written in the notes; the import's converter drops the tag, as the adventures' pages need.
        body = to_markdown(re.sub(r"<code>(.*?)</code>", r"`\1`", inner)).strip()
        lines = [f"> {line}" if line else ">" for line in body.split("\n")] if body else []
        return "\n".join([f"> [!{kind}]{' ' + own if own else ''}"] + lines)

    def block(match):
        tag, kind, own, inner = match["tag"], match["kind"] or "secret", cite(unescape(match["own"] or "")), match["inner"]
        label = "" if tag == "section" else exporter.label.get(kind, kind.capitalize())
        if label or own:
            inner = re.sub(r"^\s*<p><strong>.*?</strong></p>", "", inner, count=1)
        return quote(kind, own, inner)

    # Citations first: inside a callout, the HTML-to-Markdown step would flatten them to text.
    text = cite(text)
    text = re.sub(r'<(?P<tag>section) class="secret" id="secret-\d+"(?: data-title="(?P<own>[^"]*)")?>(?P<kind>)(?P<inner>.*?)</section>'
                  r'|<(?P<tag2>blockquote) class="callout-(?P<kind2>\w+)"(?: data-title="(?P<own2>[^"]*)")?>(?P<inner2>.*?)</blockquote>',
                  lambda m: block({"tag": m["tag"] or m["tag2"], "kind": m["kind"] or m["kind2"], "own": m["own"] or m["own2"],
                                   "inner": m["inner"] if m["tag"] else m["inner2"]}), text, flags=re.S)
    return re.sub(r"\n{3,}", "\n\n", text)


def page_markdown(page):
    text = page.get("text") or {}
    if text.get("format") == 2 and text.get("markdown") is not None:
        return text["markdown"]
    return to_markdown(text.get("content") or "")


def note_body(exporter, note, markdown, header):
    """The note body a page's Foundry text gives back."""
    if header and markdown.startswith(header):
        markdown = markdown[len(header):]
    lead = note.body[: len(note.body) - len(note.body.lstrip("\n"))]
    return lead + reverse_links(from_foundry(markdown, exporter).strip(), exporter) + "\n"


def pull_page(exporter, entry_id, page, report):
    """Write one exported page edited in Foundry back into its note; record the outcome in report."""
    campaign = exporter.campaign
    flags = (page.get("flags") or {}).get("ttrpg")
    # Flags are editable in Foundry: only trust a page sitting at the ids exported for its note.
    if not flags or exporter.pages.get(flags.get("id")) != (entry_id, page.get("_id")):
        return
    markdown = page_markdown(page)
    if page_hash(markdown) == flags.get("exported"):
        report["unchanged"] += 1
        return
    note = campaign.notes.get(flags["id"])
    if note is None:
        report["missing"].append(flags["id"])
        return
    has_secret = any(match[1].lower() == "secret" for match in CALLOUT.finditer(note.body))
    players = note.get("visibility") == "players"
    if body_hash(note.body) != flags.get("body") or (players and has_secret):
        # Repository wins; a player page was exported without its secrets, so its text cannot replace the note.
        report["conflicts"].append(note.rel)
        return
    body = note_body(exporter, note, markdown, flags.get("header") or "")
    meta = dict(note.meta)
    if meta.get("origin") == "ap" and meta.get("source_hash") and body_hash(body) != meta["source_hash"]:
        meta["origin"] = "modified"
    # Frontmatter the pull does not change stays as written (quotes, comments): the diff is the page's text only.
    text = note.path.read_text(encoding="utf-8")
    head = text[: len(text) - len(note.body)] if meta == note.meta else vault.join_frontmatter(meta, "")
    note.path.write_text(head + body, encoding="utf-8")
    report["updated"].append(note.rel)


def new_report():
    return {"updated": [], "conflicts": [], "unchanged": 0, "missing": []}


def pull(root, world_dir):
    exporter = Exporter(vault.load(root))
    report = new_report()
    for entry in unpack(Path(world_dir) / "data" / "journal"):
        for page in entry.get("pages", []):
            pull_page(exporter, entry.get("_id"), page, report)
    return report
