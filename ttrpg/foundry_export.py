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
from html import escape
import shutil
import string
import subprocess
from datetime import date
from pathlib import Path

from markdown_it import MarkdownIt

from . import vault
from .foundry_import import TOOLS, require_foundry_cli, slug
from .vault import CALLOUT, SOURCE, WIKILINK, body_hash, fields_for

CATEGORIES = {
    "npc": "npcs", "faction": "factions", "location": "places", "settlement": "places", "region": "places",
    "hex": "places", "quest": "quests", "clock": "clocks", "event": "events", "map": "maps", "scene": "scenes",
    "session": "sessions", "handout": "handouts", "item": "items", "chapter": "chapters", "note": "notes",
    "pc": "pcs", "mystery": "mysteries", "company": "pcs",
}
LABELS = {
    "fr": {"npcs": "PNJ", "factions": "Factions", "places": "Lieux", "discovered": "Lieux découverts", "quests": "Quêtes", "clocks": "Horloges",
           "events": "Chronologie", "maps": "Cartes", "scenes": "Scènes", "sessions": "Séances",
           "handouts": "Aides de jeu", "items": "Objets", "chapters": "Chapitres", "notes": "Notes",
           "pcs": "Personnages joueurs", "mysteries": "Mystères",
           "secret": "Secret", "question": "Question", "idea": "Idée", "adaptation": "Adaptation", "verify": "À vérifier", "note": "Note", "info": "Info",
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
                      "items": "Objets", "reputation": "Réputation", "player": "Joueur", "class": "Classe",
                      "renown": "Renommée"},
           "values": {"alive": "vivant", "dead": "mort", "missing": "disparu", "unknown": "inconnu",
                      "open": "ouverte", "active": "en cours", "done": "terminée", "failed": "échouée",
                      "yes": "oui", "no": "non", "raw": "image seule", "walled": "murée", "lit": "éclairée",
                      "ready": "prête", "battle": "combat", "overview": "vue d'ensemble",
                      "neighbourhood": "connus du quartier", "local": "héros locaux", "regional": "personnalités régionales",
                      "international": "célèbres dans plusieurs nations", "legendary": "légendaires", "playing": "en jeu", "absent": "absent", "retired": "retiré", "solved": "résolu", "abandoned": "abandonné"},
           "values_by_type": {"mystery": {"open": "ouvert"},
                              "hex": {"open": "dégagé", "difficult": "difficile", "greater-difficult": "très difficile",
                                      "reconnoitered": "reconnu", "mapped": "cartographié"}},
           "hud": {"hex": "Case", "region": "Région", "terrain": "Terrain", "travel": "Voyage", "explored": "Exploration",
                   "unknown": "Inexploré", "places": "Lieux",
                   "plains": "plaine", "hills": "collines", "forest": "forêt", "mountain": "montagne", "swamp": "marais",
                   "desert": "désert", "aquatic": "eau", "arctic": "glace"}},
    "en": {"npcs": "NPCs", "factions": "Factions", "places": "Places", "discovered": "Discovered places", "quests": "Quests", "clocks": "Clocks",
           "events": "Timeline", "maps": "Maps", "scenes": "Scenes", "sessions": "Sessions",
           "handouts": "Handouts", "items": "Items", "chapters": "Chapters", "notes": "Notes",
           "pcs": "Player characters", "mysteries": "Mysteries",
           "secret": "Secret", "question": "Question", "idea": "Idea", "adaptation": "Adaptation", "verify": "To verify", "note": "Note", "info": "Info",
           "todo": "To do", "quote": "", "progress": "Progress",
           "values_by_type": {"hex": {"greater-difficult": "greater difficult"}},
           "hud": {"hex": "Hex", "region": "Region", "terrain": "Terrain", "travel": "Travel", "explored": "Explored",
                   "unknown": "Unexplored", "places": "Places",
                   "plains": "plains", "hills": "hills", "forest": "forest", "mountain": "mountain", "swamp": "swamp",
                   "desert": "desert", "aquatic": "water", "arctic": "arctic"}},
}
HIDDEN_FIELDS = {"type", "title", "origin", "visibility", "prep", "aliases", "tags", "source", "source_hash", "foundry",
                 "image", "grid", "segments", "filled"}
HUD = Path(__file__).parent / "foundry"
ALPHABET = string.ascii_letters + string.digits


def foundry_id(*parts):
    """A stable 16-character Foundry id."""
    number = int.from_bytes(hashlib.sha256(":".join(parts).encode()).digest(), "big")
    return "".join(ALPHABET[(number >> (6 * i)) % len(ALPHABET)] for i in range(16))


def page_hash(markdown):
    """Hash of a page's Markdown, blind to blank-line runs (Foundry's editor and appends vary them)."""
    return body_hash(re.sub(r"\n{3,}", "\n\n", markdown))


def exported(note):
    """Campaign notes, plus imported adventure pages the GM has changed; raw session material stays home."""
    if "raw" in (note.meta.get("tags") or []):
        return False
    return not note.rel.startswith("adventure/") or note.get("origin") != "ap"


class Exporter:
    def __init__(self, campaign):
        self.campaign = campaign
        self.config = campaign.config
        # `id` keeps every Foundry id stable when the campaign is renamed; older campaigns fall back to the name.
        self.module_id = f"ttrpg-{slug(self.config.get('id') or self.config.get('name', 'campaign'))}"
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

    def value(self, kind, v):
        """A field value in the campaign language; a type may override the shared label (grammatical gender)."""
        own = self.label.get("values_by_type", {}).get(kind, {})
        return own.get(str(v), self.label.get("values", {}).get(str(v), str(v)))

    def header(self, note):
        """Frontmatter relations and state as one line of links above the body."""
        parts = []
        for name, value in note.meta.items():
            if name in HIDDEN_FIELDS or value in (None, "", []):
                continue
            spec = fields_for(note.type).get(name, {})
            values = value if isinstance(value, list) else [value]
            # Foundry's Markdown takes `23_23 … 23_23` for emphasis: a plain value's underscores are escaped.
            shown = [f"[[{vault_id(v)}]]" if spec.get("kind") in ("ref", "refs")
                     else self.value(note.type, v).replace("_", r"\_") for v in values]
            parts.append(f"**{self.field(name)}** {', '.join(shown)}")
        if note.type == "clock" and isinstance(note.get("segments"), int):
            filled = note.get("filled") or 0
            parts.append(f"**{self.label['progress']}** {'●' * filled}{'○' * (note.get('segments') - filled)}")
        for field, others in sorted(group(self.inverse.get(note.id, [])).items()):
            parts.append(f"**{self.field(field)}** " + ", ".join(f"[[{other.id}]]" for other in others))
        return " · ".join(parts)

    def field(self, name):
        return self.label.get("fields", {}).get(name, name)

    def callouts(self, markdown):
        """Callouts as HTML blocks: secrets as Foundry secrets, others as labelled blockquotes. The
        callout's own title (`> [!question] Title`) is kept in data-title for the way back."""
        secret = iter(range(1, 10_000))

        def callout(match):
            kind, inner = match[1].lower(), re.sub(r"^> ?", "", match[2], flags=re.M)
            own = match[0].split("\n", 1)[0].split("]", 1)[1].strip()
            body = self.markdown.render(inner).strip()
            attr = f' data-title="{escape(own)}"' if own else ""
            # The title is Markdown too (a one-line callout is all title): shown rendered, kept raw in data-title.
            shown = self.markdown.renderInline(own)
            if kind == "secret":
                heading = f"<p><strong>{shown}</strong></p>" if own else ""
                return f'<section class="secret" id="secret-{next(secret)}"{attr}>{heading}{body}</section>\n\n'
            label = self.label.get(kind, kind.capitalize())
            title = ": ".join(part for part in (label, shown) if part)
            return f'<blockquote class="callout-{kind}"{attr}>' + (f"<p><strong>{title}</strong></p>" if title else "") + f"{body}</blockquote>\n\n"
        return CALLOUT.sub(callout, markdown)

    def foundry_markdown(self, markdown):
        """The page Markdown Foundry stores: it renders the page's HTML from it with its own converter,
        which knows neither callouts nor src: links, so those go in as HTML (foundry_sync reverses them)."""
        sources = self.config.get("sources") or {}
        cited = re.sub(r"\[([^\]]*)\]\((" + SOURCE.pattern + r")\)",
                       lambda m: f'<span data-src="{m[3]}#p{m[4]}">{m[1]} ({sources.get(m[3], {}).get("title", m[3])}, p. {m[4]})</span>', markdown)
        return self.callouts(cited)

    def html(self, markdown):
        """Render Markdown to HTML, turning callouts into secrets and labelled blockquotes."""
        return self.markdown.render(self.callouts(self.cite(markdown)))

    def page(self, note):
        entry, page = self.pages[note.id]
        header = self.header(note)
        players = note.get("visibility") == "players"
        body = note.body.strip() + "\n"
        if players:
            # Clients receive a page's raw text: a page players can read carries no secrets.
            body = CALLOUT.sub(lambda m: "" if m[1].lower() == "secret" else m[0], body)
        markdown = self.foundry_markdown(self.convert((header + "\n\n" if header else "") + body))
        return {
            "_id": page, "_key": f"!journal.pages!{entry}.{page}", "name": note.meta.get("title") or note.id,
            "type": "text", "title": {"show": True, "level": 1},
            "text": {"format": 2, "markdown": markdown, "content": self.markdown.render(markdown)},
            # A GM page is explicitly none: inheriting would give it the entry's level, limited as soon as
            # one page of the entry is shown to players (and clients receive the text of what they can see).
            "ownership": {"default": 2 if players else 0},
            # The way back compares against these: what was exported, and the repository body it came from.
            "flags": {"ttrpg": {"id": note.id, "path": note.rel, "header": self.convert(header),
                                "exported": page_hash(markdown), "body": body_hash(body), **self.hex_flags(note)}},
            "sort": 0,
        }

    def map_scene(self, map_id):
        note = self.campaign.notes.get(str(map_id or ""))
        scene = str(note.get("foundry") or "") if note else ""
        return scene if scene.startswith("Scene.") else ""

    def hex_flags(self, note):
        """Where a place sits on a region map, for the hex hover panel: its scene, its cells and, for a hex, what the
        panel shows (players get them through the title-only discovered page)."""
        scene, cells = self.map_scene(note.get("map")), note.get("cells")
        if not scene or not isinstance(cells, list):
            return {}
        out = {"scene": scene, "cells": [str(cell) for cell in cells]}
        if note.type == "hex":
            region = self.campaign.notes.get(str(note.get("region") or ""))
            out.update({"kind": "hex", "region": (region.meta.get("title") or region.id) if region else "",
                        "terrain": str(note.get("terrain") or ""), "travel": self.value("hex", note.get("travel")) if note.get("travel") else "",
                        "explored": self.value("hex", note.get("explored")) if note.get("explored") not in (None, "no") else ""})
        return out

    def hex_tables(self):
        """Per region map scene, the public hex table: region, terrain and travel of every cell."""
        from .hexmap import hex_table
        out = {}
        hud = self.label.get("hud", LABELS["en"]["hud"])
        for note in self.campaign.notes.values():
            scene = self.map_scene(note.id) if note.type == "map" else ""
            table = hex_table(note) if scene else {}
            if not table:
                continue
            cells = {}
            for cell, row in table.items():
                region = self.campaign.notes.get(row["region"])
                cells[cell] = {"region": (region.meta.get("title") or region.id) if region else "",
                               "terrain": hud.get(row["terrain"], row["terrain"]),
                               "travel": self.value("hex", row["travel"]) if row["travel"] else ""}
            out[scene.split(".", 1)[1]] = {"cells": cells}
        return out

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
                # Foundry lists an entry for a player only at observer; its GM pages stay explicitly none.
                "ownership": {"default": 2 if any(page["ownership"]["default"] for page in pages) else 0},
                "sort": (order + 1) * 100, "flags": {"ttrpg": {"category": category}}, "folder": None,
            }
        if self.discovered():
            yield self.discovered()

    def discovered(self):
        """A players page per place the PCs discovered: its title only, the GM page stays hidden."""
        notes = sorted((note for note in self.notes if note.get("discovered") == "yes" and note.get("visibility") != "players"),
                       key=lambda note: str(note.meta.get("title") or note.id).lower())
        if not notes:
            return None
        entry = foundry_id(self.module_id, "entry", "discovered")
        pages = [{"_id": foundry_id(self.module_id, "discovered", note.id), "_key": f"!journal.pages!{entry}.{foundry_id(self.module_id, 'discovered', note.id)}",
                  "name": note.meta.get("title") or note.id, "type": "text", "title": {"show": True, "level": 1},
                  "text": {"format": 2, "markdown": "", "content": ""}, "ownership": {"default": 2}, "sort": (index + 1) * 100,
                  "flags": {"ttrpg": {"discovered": note.id, "path": note.rel, "exported": page_hash(""), **self.hex_flags(note)}}}
                 for index, note in enumerate(notes)]
        return {"_id": entry, "_key": f"!journal!{entry}", "name": self.label["discovered"], "pages": pages,
                "ownership": {"default": 2}, "sort": (len(LABELS["en"]) + 1) * 100,
                "flags": {"ttrpg": {"category": "discovered"}}, "folder": None}

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
        tables = self.hex_tables()
        for scene, table in tables.items():
            (out / "hexes").mkdir(exist_ok=True)
            (out / "hexes" / f"{scene}.json").write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
        (out / "scripts").mkdir(exist_ok=True)
        shutil.copy2(HUD / "hex-hud.mjs", out / "scripts" / "hex-hud.mjs")
        shutil.copy2(HUD / "hex-hud.css", out / "styles.css")
        (out / "hud.json").write_text(json.dumps({"labels": self.label.get("hud", LABELS["en"]["hud"]),
                                                  "scenes": sorted(tables)}, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "id": self.module_id, "title": f"{self.config.get('name')} (TTRPG)",
            "description": "Campaign notes exported from the campaign repository. Regenerated by ttrpg export-foundry; edit the repository, not this module.",
            "version": date.today().isoformat(), "compatibility": {"minimum": "13", "verified": "14"},
            "esmodules": ["scripts/hex-hud.mjs"], "styles": ["styles.css"],
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
