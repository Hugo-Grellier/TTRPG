"""Export campaign notes as a Foundry module holding one JournalEntry compendium.

One entry per kind of note (NPCs, factions, places...), one page per note.
[[id]] links become @UUID links: to the exported page, to the original page of
an imported adventure (its `source`), or to the Foundry scene of a map note.
`> [!secret]` blocks become Foundry secrets the GM can reveal; other callouts
become labelled blockquotes. Foundry ids derive from note ids, so exporting
again updates the same documents. Pages keep their Markdown (format 2), which
lets changes made in Foundry come back to the repository.
"""

import hashlib
import json
import re
import shutil
import string
import subprocess
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

from . import vault
from .foundry_import import TOOLS, require_foundry_cli, slug
from .vault import SOURCE, WIKILINK, body_hash, fields_for

CATEGORIES = {
    "npc": "npcs", "faction": "factions", "location": "places", "settlement": "places", "region": "places",
    "hex": "places", "quest": "quests", "clock": "clocks", "event": "events", "map": "maps", "scene": "scenes",
    "session": "sessions", "handout": "handouts", "item": "items", "chapter": "chapters", "note": "notes",
}
LABELS = {
    "fr": {"npcs": "PNJ", "factions": "Factions", "places": "Lieux", "quests": "Quêtes", "clocks": "Horloges",
           "events": "Chronologie", "maps": "Cartes", "scenes": "Scènes", "sessions": "Séances",
           "handouts": "Aides de jeu", "items": "Objets", "chapters": "Chapitres", "notes": "Notes",
           "secret": "Secret", "question": "Question", "idea": "Idée", "note": "Note", "info": "Info",
           "todo": "À faire", "quote": "", "progress": "Progression",
           "fields": {"level": "Niveau", "state": "État", "died": "Mort le", "location": "Lieu", "factions": "Factions",
                      "leader": "Chef", "base": "Base", "region": "Région", "in": "Dans", "giver": "Commanditaire",
                      "date": "Date", "participants": "Participants", "played": "Joué", "owner": "Porteur",
                      "day": "Jour", "ingame": "Date en jeu", "present": "Présents", "stage": "Préparation",
                      "kind": "Genre", "locations": "Lieux", "chapter": "Chapitre", "coord": "Coordonnées",
                      "terrain": "Terrain", "members": "Membres", "residents": "Habitants", "settlements": "Colonies",
                      "contains": "Contient", "scenes": "Scènes", "maps": "Cartes", "hexes": "Hexes",
                      "subregions": "Sous-régions",
                      "ancestry": "Ascendance",
                      "population": "Population", "government": "Gouvernement", "possessions": "Possède",
                      "items": "Objets"},
           "values": {"alive": "vivant", "dead": "mort", "missing": "disparu", "unknown": "inconnu",
                      "open": "ouverte", "active": "en cours", "done": "terminée", "failed": "échouée",
                      "yes": "oui", "no": "non", "raw": "image seule", "walled": "murée", "lit": "éclairée",
                      "ready": "prête", "battle": "combat", "overview": "vue d'ensemble"}},
    "en": {"npcs": "NPCs", "factions": "Factions", "places": "Places", "quests": "Quests", "clocks": "Clocks",
           "events": "Timeline", "maps": "Maps", "scenes": "Scenes", "sessions": "Sessions",
           "handouts": "Handouts", "items": "Items", "chapters": "Chapters", "notes": "Notes",
           "secret": "Secret", "question": "Question", "idea": "Idea", "note": "Note", "info": "Info",
           "todo": "To do", "quote": "", "progress": "Progress"},
}
HIDDEN_FIELDS = {"type", "title", "origin", "visibility", "prep", "aliases", "tags", "source", "source_hash", "foundry",
                 "image", "grid", "segments", "filled"}
CALLOUT = re.compile(r"^> \[!(\w+)\][^\n]*\n((?:>[^\n]*\n?)*)", re.M)
ALPHABET = string.ascii_letters + string.digits


def foundry_id(*parts):
    """A stable 16-character Foundry id."""
    number = int.from_bytes(hashlib.sha256(":".join(parts).encode()).digest(), "big")
    return "".join(ALPHABET[(number >> (6 * i)) % len(ALPHABET)] for i in range(16))


def exported(note):
    """Campaign notes, plus imported adventure pages the GM has changed; raw session material stays home."""
    if "raw" in (note.meta.get("tags") or []):
        return False
    return not note.rel.startswith("adventure/") or note.get("origin") != "ap"


class Exporter:
    def __init__(self, campaign):
        self.campaign = campaign
        self.config = campaign.config
        self.module_id = f"ttrpg-{slug(self.config.get('name', 'campaign'))}"
        self.label = LABELS.get(self.config.get("language"), LABELS["en"])
        self.markdown = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough")
        self.notes = [note for note in campaign.notes.values() if exported(note) and not note.error]
        self.pages = {note.id: (foundry_id(self.module_id, "entry", CATEGORIES.get(note.type, "notes")),
                                foundry_id(self.module_id, "page", note.id)) for note in self.notes}
        self.inverse = self.inverse_relations()
        self.assets = set()

    def inverse_relations(self):
        """target id -> [(inverse field, source note)], from the schema's `inverse` names."""
        inverse = {}
        for note in self.notes:
            for name, spec in fields_for(note.type).items():
                if not spec.get("inverse") or not note.meta.get(name):
                    continue
                values = note.meta[name] if isinstance(note.meta[name], list) else [note.meta[name]]
                for value in values:
                    inverse.setdefault(vault_id(value), []).append((spec["inverse"], note))
        return inverse

    def link(self, target, label=None, anchor=""):
        note = self.campaign.notes.get(target)
        if note is None:
            return label or target
        label = label or note.meta.get("title") or target
        anchor = f"#{slug(anchor)}" if anchor else ""
        if target in self.pages:
            entry, page = self.pages[target]
            return f"@UUID[JournalEntry.{entry}.JournalEntryPage.{page}{anchor}]{{{label}}}"
        if str(note.meta.get("source", "")).startswith("JournalEntry."):
            return f"@UUID[{note.meta['source']}{anchor}]{{{label}}}"
        if note.type == "map" and note.meta.get("foundry"):
            return f"@UUID[{note.meta['foundry']}]{{{label}}}"
        return label

    def convert(self, text):
        """Repository Markdown to Foundry Markdown: links, assets and source citations."""
        def wikilink(match):
            embed, target, anchor, label = match[1], match[2].strip(), (match[3] or "")[1:], match[4]
            if re.search(r"\.[A-Za-z0-9]{2,4}$", target):
                self.assets.add(target)
                path = f"modules/{self.module_id}/assets/{target}"
                return f"![{label or ''}]({path})" if embed else f"[{label or target}]({path})"
            return self.link(target, label, anchor)
        return WIKILINK.sub(wikilink, text)

    def cite(self, text):
        """Source citations as plain text in HTML; the Markdown keeps src: links for the way back."""
        sources = self.config.get("sources") or {}
        return re.sub(r"\[([^\]]*)\]\((" + SOURCE.pattern + r")\)",
                      lambda m: f"{m[1]} ({sources.get(m[3], {}).get('title', m[3])}, p. {m[4]})", text)

    def header(self, note):
        """Frontmatter relations and state as one line of links above the body."""
        parts = []
        for name, value in note.meta.items():
            if name in HIDDEN_FIELDS or value in (None, "", []):
                continue
            spec = fields_for(note.type).get(name, {})
            values = value if isinstance(value, list) else [value]
            shown = [f"[[{vault_id(v)}]]" if spec.get("kind") in ("ref", "refs")
                     else self.label.get("values", {}).get(str(v), str(v)) for v in values]
            parts.append(f"**{self.field(name)}** {', '.join(shown)}")
        if note.type == "clock" and isinstance(note.get("segments"), int):
            filled = note.get("filled") or 0
            parts.append(f"**{self.label['progress']}** {'●' * filled}{'○' * (note.get('segments') - filled)}")
        for field, others in sorted(group(self.inverse.get(note.id, [])).items()):
            parts.append(f"**{self.field(field)}** " + ", ".join(f"[[{other.id}]]" for other in others))
        return " · ".join(parts)

    def field(self, name):
        return self.label.get("fields", {}).get(name, name)

    def html(self, markdown):
        """Render Markdown to HTML, turning callouts into secrets and labelled blockquotes."""
        secret = iter(range(1, 10_000))

        def callout(match):
            kind, inner = match[1].lower(), re.sub(r"^> ?", "", match[2], flags=re.M)
            body = self.markdown.render(inner)
            if kind == "secret":
                return f'<section class="secret" id="secret-{next(secret)}">{body}</section>\n\n'
            title = self.label.get(kind, kind.capitalize())
            return f'<blockquote class="callout-{kind}">' + (f"<p><strong>{title}</strong></p>" if title else "") + f"{body}</blockquote>\n\n"
        return self.markdown.render(CALLOUT.sub(callout, self.cite(markdown)))

    def page(self, note):
        entry, page = self.pages[note.id]
        header = self.header(note)
        players = note.get("visibility") == "players"
        body = note.body.strip() + "\n"
        if players:
            # Clients receive a page's raw text: a page players can read carries no secrets.
            body = CALLOUT.sub(lambda m: "" if m[1].lower() == "secret" else m[0], body)
        markdown = self.convert((header + "\n\n" if header else "") + body)
        return {
            "_id": page, "_key": f"!journal.pages!{entry}.{page}", "name": note.meta.get("title") or note.id,
            "type": "text", "title": {"show": True, "level": 1},
            "text": {"format": 2, "markdown": markdown, "content": self.html(markdown)},
            "ownership": {"default": 2 if players else -1},
            # The way back compares against these: what was exported, and the repository body it came from.
            "flags": {"ttrpg": {"id": note.id, "path": note.rel, "header": self.convert(header),
                                "exported": body_hash(markdown), "body": body_hash(body)}},
            "sort": 0,
        }

    def entries(self):
        grouped = {}
        for note in self.notes:
            grouped.setdefault(CATEGORIES.get(note.type, "notes"), []).append(note)
        for order, (category, notes) in enumerate(sorted(grouped.items(), key=lambda item: list(LABELS["en"]).index(item[0]))):
            notes.sort(key=lambda note: (str(note.get("date") or note.get("day") or ""), str(note.meta.get("title") or note.id).lower()))
            entry = foundry_id(self.module_id, "entry", category)
            pages = [self.page(note) for note in notes]
            for index, page in enumerate(pages):
                page["sort"] = (index + 1) * 100
            yield {
                "_id": entry, "_key": f"!journal!{entry}", "name": self.label[category], "pages": pages,
                "ownership": {"default": 1 if any(page["ownership"]["default"] == 2 for page in pages) else 0},
                "sort": (order + 1) * 100, "flags": {"ttrpg": {"category": category}}, "folder": None,
            }

    def write(self, out):
        out = Path(out)
        if out.exists():
            shutil.rmtree(out)
        source = out / "_source"
        source.mkdir(parents=True)
        entries = list(self.entries())
        for entry in entries:
            (source / f"{entry['_id']}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
        require_foundry_cli()
        subprocess.run(["node", str(TOOLS / "ttrpg" / "pack.mjs"), str(source), str(out / "packs" / "notes")], check=True)
        shutil.rmtree(source)
        root = self.campaign.root.resolve()
        files = {path.name: path for path, rel in vault.walk(root)
                 if path.suffix != ".md" and not any(part.startswith(".") for part in rel.parts)}
        for name in sorted(self.assets):
            path = files.get(name)
            # Only files the exported notes cite, real files inside the campaign.
            if path is None or path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            (out / "assets").mkdir(exist_ok=True)
            shutil.copy2(path, out / "assets" / name)
        manifest = {
            "id": self.module_id, "title": f"{self.config.get('name')} (TTRPG)",
            "description": "Campaign notes exported from the campaign repository. Regenerated by ttrpg export-foundry; edit the repository, not this module.",
            "version": date.today().isoformat(), "compatibility": {"minimum": "13", "verified": "14"},
            "packs": [{"name": "notes", "label": f"{self.config.get('name')}", "path": "packs/notes", "type": "JournalEntry",
                       "ownership": {"PLAYER": "NONE", "TRUSTED": "NONE", "ASSISTANT": "OWNER"}}],
        }
        (out / "module.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"module": self.module_id, "entries": len(entries), "pages": sum(len(e["pages"]) for e in entries), "path": str(out)}


def vault_id(value):
    value = str(value).strip()
    return value[2:-2].split("|")[0] if value.startswith("[[") else value


def group(pairs):
    grouped = {}
    for field, note in pairs:
        grouped.setdefault(field, []).append(note)
    return grouped


def export(root, out=None):
    campaign = vault.load(root)
    exporter = Exporter(campaign)
    return exporter.write(out or Path(root) / ".cache" / "foundry" / exporter.module_id)
