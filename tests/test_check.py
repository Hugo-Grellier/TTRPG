import json
import tempfile
import unittest
from pathlib import Path

from ttrpg.check import check
from ttrpg.html_md import to_markdown
from ttrpg.vault import body_hash


def write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def messages(root, **kwargs):
    return [message for _, _, message in check(root, **kwargs)[1].items]


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = self.dir.name
        write(self.root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nsources:\n  km: {title: KM, pages: 10}\n")
        write(self.root, "factions/swordlords.md", "---\ntype: faction\ntitle: Swordlords\n---\nAldori.\n")
        write(self.root, "npcs/oleg.md", "---\ntype: npc\ntitle: Oleg\nfactions: [swordlords]\n---\nSee [[swordlords]], [p. 3](src:km#p3), roll [[/r 1d4]].\n")

    def tearDown(self):
        self.dir.cleanup()

    def test_clean_campaign_passes(self):
        self.assertEqual(messages(self.root), [])

    def test_links_refs_and_sources(self):
        write(self.root, "npcs/bad.md", "---\ntype: npc\ntitle: Bad\nfactions: [oleg]\n---\n[[nobody]] [x](oleg.md) [p](src:km#p99) [q](src:zz#p1) ![[gone.png]] [[lost.pdf|map]]\n")
        found = "\n".join(messages(self.root))
        for expected in ("'oleg' is a npc, expected faction", "broken link [[nobody]]", "relative link",
                         "page 99 outside km", "unknown source 'zz'", "missing asset 'gone.png'", "missing asset 'lost.pdf'"):
            self.assertIn(expected, found)

    def test_schema_and_duplicates(self):
        write(self.root, "x/oleg.md", "---\ntype: npc\ntitle: Oleg 2\n---\n")
        write(self.root, "a.md", "---\ntype: monster\ntitle: A\n---\n")
        write(self.root, "c.md", "---\ntype: clock\ntitle: C\nsegments: 4\nfilled: 6\nmembers: []\n---\n")
        found = "\n".join(messages(self.root))
        for expected in ("duplicate id 'oleg'", "unknown type 'monster'", "filled must be between", "unknown field 'members'"):
            self.assertIn(expected, found)

    def test_chronology(self):
        write(self.root, "npcs/oleg.md", '---\ntype: npc\ntitle: Oleg\nstate: dead\ndied: "4710-03-01"\n---\n')
        write(self.root, "e.md", '---\ntype: event\ntitle: Feast\ndate: "4710-04-01"\nparticipants: [oleg]\n---\n')
        write(self.root, "s1.md", '---\ntype: session\ntitle: S1\nday: 2026-01-01\ningame: "4710-05-01"\n---\n[[oleg]]\n')
        write(self.root, "s2.md", '---\ntype: session\ntitle: S2\nday: 2026-01-08\ningame: "4710-04-01"\n---\n')
        found = "\n".join(messages(self.root))
        self.assertIn("oleg died 4710-03-01, before this event", found)
        self.assertIn("goes back before s1.md", found)
        self.assertIn("mentions oleg, dead since", found)

    def test_campaign_start_date(self):
        write(self.root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nstart: 4710-03-01\n")
        self.assertIn("start must be a quoted in-game date YYYY-MM-DD", messages(self.root))

    def test_large_assets_and_map_gaps(self):
        from ttrpg.check import map_gaps
        from ttrpg.vault import load
        (Path(self.root) / "big.png").write_bytes(b"0" * 6_000_000)
        self.assertIn("6 MB: compress it (webp) or track it with Git LFS", messages(self.root))
        write(self.root, ".gitattributes", "*.png filter=lfs diff=lfs merge=lfs -text\n")
        self.assertEqual(messages(self.root), [])
        write(self.root, "h1.md", "---\ntype: hex\ntitle: H1\n---\n@UUID[Actor.a]{Boar}\n")
        write(self.root, "h2.md", "---\ntype: hex\ntitle: H2\n---\n@UUID[Actor.b]{Bear} [[map-den]]\n")
        write(self.root, "map-den.md", "---\ntype: map\ntitle: Den\n---\n")
        self.assertEqual([note.id for note in map_gaps(load(self.root))], ["h1"])
        write(self.root, "map-world.md", "---\ntype: map\ntitle: World\nkind: overview\n---\nPins: [[h1]]\n")
        self.assertEqual([note.id for note in map_gaps(load(self.root))], ["h1"])
        write(self.root, "map-lair.md", "---\ntype: map\ntitle: Lair\n---\nPins: [[h1]]\n")
        self.assertEqual(map_gaps(load(self.root)), [])

    def test_player_visibility(self):
        write(self.root, "h.md", "---\ntype: handout\ntitle: H\nvisibility: players\n---\n[[oleg]]\n")
        self.assertIn("players note links GM-only note [[oleg]]", messages(self.root))

    def test_edited_ap_note_needs_modified_origin(self):
        write(self.root, "ap.md", f"---\ntype: note\ntitle: AP\norigin: ap\nsource_hash: {body_hash('Original.')}\n---\nChanged.\n")
        self.assertIn("set origin: modified", messages(self.root)[0])
        check(self.root, fix=True)
        self.assertIn("origin: modified", (Path(self.root) / "ap.md").read_text())
        self.assertEqual(messages(self.root), [])


class RenameTest(unittest.TestCase):
    def test_rename_updates_links_and_keeps_ap_hash(self):
        from ttrpg.rename import rename
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "f.md", "---\ntype: faction\ntitle: F\n---\n")
            write(root, "n.md", "---\ntype: npc\ntitle: N\nfactions: [f]\n---\n[[f|F]] and [[f#Goal]]\n")
            body = "See [[f]].\n"
            write(root, "ap.md", f"---\ntype: note\ntitle: AP\norigin: ap\nsource_hash: {body_hash(body)}\n---\n{body}")
            self.assertEqual(rename(root, "f", "swordlords"), 2)
            self.assertIn("factions:\n- swordlords", (Path(root) / "n.md").read_text())
            self.assertIn("[[swordlords|F]] and [[swordlords#Goal]]", (Path(root) / "n.md").read_text())
            self.assertEqual(messages(root), [])


class ExportTest(unittest.TestCase):
    def test_region_map_hex_table_and_panel_flags(self):
        from ttrpg.check import check
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "places/cairn.md", "---\ntype: region\ntitle: Cairnlands\n---\nR.\n")
            write(root, "maps/kortos.md", "---\ntype: map\ntitle: K\nkind: overview\nfoundry: Scene.abc\n---\nM.\n")
            write(root, "maps/kortos.hexes.tsv", "cell\tregion\tterrain\ttravel\n23_30\tcairn\tplains\topen\n")
            write(root, "places/tertres.md", "---\ntype: hex\ntitle: Les Tertres\nregion: cairn\nmap: kortos\ncells: [\"22_32\"]\n"
                  "travel: difficult\nexplored: reconnoitered\ndiscovered: \"yes\"\n---\nH.\n")
            self.assertEqual([m for _, _, m in check(root)[1].items], [])
            exporter = Exporter(load(root))
            self.assertEqual(exporter.hex_tables(), {"abc": {"cells": {"23_30": {"region": "Cairnlands", "terrain": "plaine", "travel": "dégagé"}}}})
            places = {e["name"]: e for e in exporter.entries()}
            gm = next(p for p in places["Lieux"]["pages"] if p["name"] == "Les Tertres")["flags"]["ttrpg"]
            shown = places["Lieux découverts"]["pages"][0]["flags"]["ttrpg"]
            for flags in (gm, shown):
                self.assertEqual((flags["scene"], flags["cells"], flags["region"], flags["travel"], flags["explored"]),
                                 ("Scene.abc", ["22_32"], "Cairnlands", "difficile", "reconnu"))
            write(root, "maps/kortos.hexes.tsv", "cell\tregion\tterrain\ttravel\n23-30\tkortos\tlava\tfast\n")
            write(root, "maps/kortos.md", "---\ntype: map\ntitle: K\nkind: overview\nfoundry: abc\n---\nM.\n")
            self.assertEqual(sorted(m for _, _, m in check(root)[1].items), sorted([
                "foundry: 'abc' must be a scene uuid (Scene.<id>)", "cell '23-30' must be a grid offset i_j",
                "23-30: region 'kortos' is not a region note", "23-30: terrain 'lava' not in ['plains', 'hills', 'forest', 'mountain', 'swamp', 'desert', 'aquatic', 'arctic']",
                "23-30: travel 'fast' not in ['open', 'difficult', 'greater-difficult']"]))

    def test_links_secrets_and_inverse_relations(self):
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nsources:\n  km: {title: KM, pages: 9}\n")
            write(root, "factions/f.md", "---\ntype: faction\ntitle: Lames\n---\nBut.\n")
            write(root, "npcs/n.md", "---\ntype: npc\ntitle: Oleg\nfactions: [f]\n---\nVoir [[f|les Lames]], [[km-p]] [p. 3](src:km#p3).\n\n> [!secret]\n> Il ment.\n")
            write(root, "adventure/j/km-p.md", "---\ntype: note\ntitle: Page\norigin: ap\nsource: JournalEntry.J.JournalEntryPage.P\n---\nAP\n")
            exporter = Exporter(load(root))
            entries = {entry["name"]: entry for entry in exporter.entries()}
            self.assertEqual(sorted(entries), ["Factions", "PNJ"])
            oleg = entries["PNJ"]["pages"][0]["text"]
            faction = exporter.pages["f"]
            self.assertIn(f"@UUID[JournalEntry.{faction[0]}.JournalEntryPage.{faction[1]}]{{les Lames}}", oleg["markdown"])
            self.assertIn("@UUID[JournalEntry.J.JournalEntryPage.P]{Page}", oleg["markdown"])
            self.assertIn('<span data-src="km#p3">p. 3 (KM, p. 3)</span>', oleg["markdown"])
            self.assertIn("p. 3 (KM, p. 3)", oleg["content"])
            self.assertIn('<section class="secret" id="secret-1"><p>Il ment.</p>', oleg["content"])
            self.assertIn("**Membres** @UUID[", entries["Factions"]["pages"][0]["text"]["markdown"])
            self.assertEqual(exporter.pages, Exporter(load(root)).pages)
            write(root, "h.md", "---\ntype: handout\ntitle: Lettre\nvisibility: players\n---\nTexte.\n\n> [!secret]\n> Faux.\n")
            handout = next(Exporter(load(root)).entries())
            self.assertNotIn("Faux", json.dumps(handout))

    def test_foundry_markdown_comes_back_as_repository_markdown(self):
        from ttrpg.foundry_export import Exporter
        from ttrpg.foundry_sync import reverse_links
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "factions/f.md", "---\ntype: faction\ntitle: Lames\n---\nBut.\n")
            body = "Voir [[f]] et [[f|les Lames]], ![[x.png|carte]].\n\n> [!secret]\n> Il ment."
            write(root, "npcs/n.md", f"---\ntype: npc\ntitle: Oleg\n---\n{body}\n")
            write(root, "x.png", "png")
            exporter = Exporter(load(root))
            self.assertEqual(reverse_links(exporter.convert(body), exporter), body)

    def test_page_markdown_carries_callouts_and_citations_as_html(self):
        # Foundry renders a Markdown page's HTML itself, ignoring ours: callouts and citations must be in the Markdown.
        from ttrpg.foundry_export import Exporter
        from ttrpg.foundry_sync import from_foundry
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nsources:\n  km: {title: KM (EN), pages: 9}\n")
            body = "Voir [p. 3](src:km#p3).\n\n> [!secret]\n> Il **ment** ([p. 4](src:km#p4)).\n\n> [!question] Palier du cadeau\n> À trancher."
            write(root, "npcs/n.md", f"---\ntype: npc\ntitle: Oleg\n---\n{body}\n")
            exporter = Exporter(load(root))
            sent = exporter.foundry_markdown(exporter.convert(body))
            self.assertIn('<section class="secret" id="secret-1"><p>Il <strong>ment</strong> (<span data-src="km#p4">p. 4 (KM (EN), p. 4)</span>).</p></section>', sent)
            self.assertIn('data-title="Palier du cadeau"><p><strong>Question : Palier du cadeau</strong></p>'.replace(" : ", ": "), sent)
            self.assertIn('<span data-src="km#p3">p. 3 (KM (EN), p. 3)</span>', sent)
            self.assertEqual(from_foundry(sent, exporter).strip(), body)
            # A one-line callout is all title: its citation and emphasis show rendered and come back as written.
            body = "> [!secret] Il **ment** ([p. 4](src:km#p4)).\n\n> [!question] Qui ? ([p. 5](src:km#p5))\n> À trancher dans `campaign.yaml`."
            sent = exporter.foundry_markdown(exporter.convert(body))
            self.assertIn('<p><strong>Il <strong>ment</strong> (<span data-src="km#p4">p. 4 (KM (EN), p. 4)</span>).</strong></p></section>', sent)
            self.assertEqual(from_foundry(sent, exporter).strip(), body)
            # A page exported before titles were rendered (escaped in the heading) comes back the same.
            old = ('<section class="secret" id="secret-1" data-title="Vu (&lt;span data-src=&quot;km#p4&quot;&gt;p. 4 (KM (EN), p. 4)&lt;/span&gt;)">'
                   "<p><strong>Vu (&lt;span data-src=&quot;km#p4&quot;&gt;p. 4 (KM (EN), p. 4)&lt;/span&gt;)</strong></p></section>")
            self.assertEqual(from_foundry(old, exporter).strip(), "> [!secret] Vu ([p. 4](src:km#p4))")


class FakeWorld:
    """The sync-world tool over an in-memory world."""

    def __init__(self, settings=None):
        self.docs = {}
        self.settings = settings or {}
        self.time = 0
        self.calendar = False
        self.scenes = {}
        self.pins = {}

    def sync(self, op, types=None, text=False, **calls):
        if op == "setting":
            if calls["key"] not in self.settings:
                raise SystemExit(f"foundry-mcp: Error: {calls['key']} is not a registered game setting")
            return {"value": json.loads(json.dumps(self.settings[calls["key"]]))}
        if op == "merge-setting":
            value = self.settings[calls["key"]]
            for key in calls.get("remove", []):
                del value[key]
            value.update(json.loads(json.dumps(calls.get("set", {}))))
            return {"keys": len(value)}
        if op == "time":
            self.time = calls.get("worldTime", self.time)
            return {"worldTime": self.time}
        if op == "calendar":
            if not self.calendar:
                return {"active": False}
            # A toy calendar: 12 months of 31 days, world time 0 = year 0.
            days = self.time // 86400
            out = {"active": True, "current": {"year": days // 372, "month": days % 372 // 31, "day": days % 31}}
            if calls.get("date"):
                d = calls["date"]
                out["timestamp"] = (d["year"] * 372 + d["month"] * 31 + d["day"]) * 86400
            return out
        if op == "flag":
            scene = self.scenes.get(calls["uuid"])
            return {"exists": scene is not None, "value": json.loads(json.dumps(scene)) if scene is not None else None}
        if op == "merge-flag":
            scene = self.scenes[calls["uuid"]]
            for key in calls.get("remove", []):
                del scene[key]
            scene.update(json.loads(json.dumps(calls.get("set", {}))))
            return {"changed": 1}
        if op == "scene-notes":
            return {"exists": calls["uuid"] in self.pins, "notes": json.loads(json.dumps(self.pins.get(calls["uuid"], [])))}
        if op == "apply" and any(d["documentName"] == "Note" for d in calls.get("adopt", [])):
            for change in calls["adopt"]:
                pin = next(p for p in self.pins[change["parent"]] if p["_id"] == change["_id"])
                data = dict(change["data"])
                if data.pop("flags.-=ttrpg", "keep") is None:
                    pin["flags"] = None
                pin.update({k: v for k, v in data.items() if k != "flags"})
                if "flags" in data:
                    pin["flags"] = data["flags"]["ttrpg"]
            return {"created": 0, "updated": len(calls["adopt"]), "deleted": 0, "missing": []}
        if op == "inventory":
            out = []
            for doc in self.docs.values():
                if types and doc["documentName"] not in types:
                    continue
                item = {"documentName": doc["documentName"], "_id": doc["_id"], "flags": doc["data"]["flags"]["ttrpg"]}
                if doc.get("parent"):
                    item["parent"] = doc["parent"]
                if text and doc["documentName"] == "JournalEntryPage":
                    item["markdown"] = doc["data"]["text"]["markdown"]
                out.append(item)
            return {"documents": out}
        done = {"created": 0, "updated": 0, "deleted": 0, "missing": []}
        for doc in calls.get("create", []) + calls.get("adopt", []):
            self.docs[doc["_id"]] = json.loads(json.dumps(doc))
        for doc in calls.get("update", []):
            if "flags.-=ttrpg" in doc["data"]:
                del self.docs[doc["_id"]]  # released: no longer listed
            else:
                self.docs[doc["_id"]] = json.loads(json.dumps(doc))
        done["created"] = len(calls.get("create", []))
        done["updated"] = len(calls.get("update", [])) + len(calls.get("adopt", []))
        for ref in calls.get("delete", []):
            self.docs = {k: d for k, d in self.docs.items() if k != ref["_id"] and d.get("parent") != f"{ref['documentName']}.{ref['_id']}"}
            done["deleted"] += 1
        return done


class LiveSyncTest(unittest.TestCase):
    def test_two_campaigns_share_a_world(self):
        from ttrpg import foundry_live
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write(a, "campaign.yaml", "name: A\nsystem: pf2e\nlanguage: fr\n")
            write(a, "npcs/n.md", "---\ntype: npc\ntitle: Oleg\n---\nA.\n")
            write(b, "campaign.yaml", "name: B\nsystem: pf2e\nlanguage: fr\n")
            write(b, "npcs/m.md", "---\ntype: npc\ntitle: Hilde\n---\nB.\n")
            world = FakeWorld()
            foundry_live.sync(a, world, apply=True)
            first = set(world.docs)
            steps, done = foundry_live.sync(b, world, apply=True)
            self.assertEqual((done["created"], done["deleted"]), (3, 0))  # folder, entry, page
            self.assertTrue(first <= set(world.docs))
            steps, _ = foundry_live.sync(a, world)
            self.assertEqual([len(steps[x]) for x in ("create", "update", "delete", "edited")], [0, 0, 0, 0])
            # Documents synced before campaigns were marked: kept, and adopted only by the campaign that wants them.
            for doc in world.docs.values():
                doc["data"]["flags"]["ttrpg"].pop("campaign")
                doc["data"]["flags"]["ttrpg"]["hash"] = "legacy"
            steps, _ = foundry_live.sync(b, world)
            self.assertEqual((len(steps["delete"]), len(steps["update"])), (0, 3))

    def test_plan_apply_edit_and_pull(self):
        from ttrpg import foundry_live
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "factions/f.md", "---\ntype: faction\ntitle: Lames\n---\nBut.\n")
            write(root, "npcs/n.md", "---\ntype: npc\ntitle: Oleg\n---\nVoir [[f]].\n")
            world = FakeWorld()
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual(done, {"created": 5, "updated": 0, "deleted": 0, "missing": []})  # folder, 2 entries, 2 pages
            pages = {d["_id"] for d in world.docs.values() if d["documentName"] == "JournalEntryPage"}
            self.assertEqual(pages, {page for _, page in Exporter(load(root)).pages.values()})
            steps, _ = foundry_live.sync(root, world)
            self.assertEqual([len(steps[a]) for a in ("adopt", "create", "update", "release", "delete", "edited")], [0] * 6)
            write(root, "npcs/n.md", '---\ntype: npc\ntitle: "Oleg"  # le marchand\n---\nVoir [[f]] demain.\n')
            (Path(root) / "factions/f.md").unlink()
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual(done, {"created": 0, "updated": 1, "deleted": 1, "missing": []})  # the factions entry, its page with it
            page = next(d for d in world.docs.values() if d["documentName"] == "JournalEntryPage")
            page["data"]["text"]["markdown"] += "\n\nAjouté dans Foundry.\n\n> [!secret] Tapé tel quel."  # the export writes a section
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertIsNone(done)
            self.assertEqual(len(steps["edited"]), 1)
            self.assertEqual(foundry_live.pull(root, world)["updated"], ["npcs/n.md"])
            self.assertEqual((Path(root) / "npcs/n.md").read_text(),  # frontmatter as written
                             '---\ntype: npc\ntitle: "Oleg"  # le marchand\n---\nVoir f demain.\n\nAjouté dans Foundry.\n\n> [!secret] Tapé tel quel.\n')
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual((len(steps["edited"]), done["updated"]), (0, 1))

    def test_actors_copied_adopted_and_released(self):
        from ttrpg import foundry_live
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "npcs/ermite.md", "---\ntype: npc\ntitle: Ermite\nstats: Compendium.pf2e.pathfinder-bestiary.Actor.abc\nadjust: elite\n---\nVit seul.\n")
            write(root, "npcs/amiri.md", "---\ntype: npc\ntitle: Amiri\nfoundry: Actor.AAAAAAAAAAAAAAAA\nowners: [Alice]\nstate: dead\n---\nBarbare.\n")
            write(root, "npcs/oleg.md", "---\ntype: npc\ntitle: Oleg\nfoundry: Actor.BBBBBBBBBBBBBBBB\n---\nAubergiste.\n")
            world = FakeWorld()
            steps, done = foundry_live.sync(root, world, apply=True)
            actors = {d["data"].get("name") or d["_id"]: d for d in steps["create"] + steps["adopt"] if d["documentName"] == "Actor"}
            self.assertEqual(sorted(actors), ["AAAAAAAAAAAAAAAA", "Ermite"])  # Oleg: nothing to write on his actor
            self.assertEqual((actors["Ermite"]["source"], actors["Ermite"]["adjust"]), ("Compendium.pf2e.pathfinder-bestiary.Actor.abc", "elite"))
            self.assertEqual(actors["AAAAAAAAAAAAAAAA"]["data"]["ownership"], {"@Alice": 3})
            dead = next(d for d in steps["create"] if d["documentName"] == "ActiveEffect")
            self.assertEqual((dead["parent"], dead["data"]["statuses"], dead["data"]["name"]), ("Actor.AAAAAAAAAAAAAAAA", ["dead"], "Mort"))
            write(root, "npcs/amiri.md", "---\ntype: npc\ntitle: Amiri\nfoundry: Actor.AAAAAAAAAAAAAAAA\nowners: [Bob]\nstate: dead\n---\nBarbare.\n")
            steps, _ = foundry_live.sync(root, world, apply=True)
            amiri = next(d for d in steps["update"] if d["documentName"] == "Actor")
            self.assertEqual(amiri["data"]["ownership"], {"@Bob": 3, "@Alice": 0})
            write(root, "npcs/amiri.md", "---\ntype: npc\ntitle: Amiri\nfoundry: Actor.AAAAAAAAAAAAAAAA\n---\nBarbare.\n")
            steps, _ = foundry_live.sync(root, world, apply=True)
            self.assertEqual([d["_id"] for d in steps["release"]], ["AAAAAAAAAAAAAAAA"])
            self.assertEqual(steps["release"][0]["data"]["ownership"], {"@Bob": 0})  # access taken back
            self.assertEqual([d["documentName"] for d in steps["delete"]], ["ActiveEffect"])

    def test_date_and_clocks(self):
        from ttrpg import foundry_live
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", 'name: T\nsystem: pf2e\nlanguage: fr\nstart: "4710-02-23"\n')
            write(root, "clocks/assaut.md", "---\ntype: clock\ntitle: Assaut\nsegments: 4\nfilled: 1\n---\n- un\n- deux\n- trois\n- quatre\n")
            clock = {"dateTheme": "AR", "worldCreatedOn": "2026-10-30T11:28:59.647Z"}
            world = FakeWorld({"pf2e.worldClock": clock, foundry_live.CLOCKS: {"gm": {"id": "gm", "name": "MJ", "value": 2, "max": 6}}})
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual(steps["time"]["date"], "4710-02-23")
            self.assertEqual(foundry_live.world_time("4710-02-23", clock, 0) - foundry_live.world_time("4710-02-22", clock, 0), 86400)
            pushed = world.settings[foundry_live.CLOCKS]
            self.assertIn("gm", pushed)  # the GM's own clock stays
            ours = next(value for key, value in pushed.items() if key != "gm")
            self.assertEqual((ours["value"], ours["max"], ours["private"]), (1, 4, True))
            steps, _ = foundry_live.sync(root, world)
            self.assertEqual((steps["time"], steps["clocks"]), (None, {}))
            world.time += 3 * 86400  # the GM moved time on in play
            self.assertEqual(foundry_live.sync(root, world)[0]["time_ahead"], "4710-02-23")
            ours["value"] = 3  # and filled the clock in Foundry
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertIsNone(done)
            self.assertEqual(len(steps["clocks_edited"]), 1)
            self.assertEqual(foundry_live.pull(root, world)["updated"], ["clocks/assaut.md"])
            self.assertIn("filled: 3", (Path(root) / "clocks/assaut.md").read_text())
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual(world.settings[foundry_live.CLOCKS][ours["id"]]["ttrpg"]["value"], 3)

    def test_date_through_simple_calendar(self):
        from ttrpg import foundry_live
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", 'name: T\nsystem: pf2e\nlanguage: fr\nstart: "4710-02-23"\n')
            world = FakeWorld()
            world.calendar = True
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(world.time, (4710 * 372 + 31 + 22) * 86400)
            write(root, "sessions/s1.md", '---\ntype: session\ntitle: S1\nday: "2026-11-01"\ningame: "4710-02-25"\n---\nJouée.\n')
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(world.time, (4710 * 372 + 31 + 24) * 86400)

    def test_discovered_places(self):
        from ttrpg import foundry_live
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "maps/region.md", "---\ntype: map\ntitle: Région\nfoundry: Scene.SSSSSSSSSSSSSSSS\n---\n")
            write(root, "places/tour.md", '---\ntype: hex\ntitle: Tour\ndiscovered: "yes"\nmap: region\ncells: [3_4]\n---\nSecret de la tour.\n')
            self.assertIn("must be a quoted grid offset", "\n".join(messages(root)))  # YAML reads 3_4 as 34
            write(root, "places/tour.md", '---\ntype: hex\ntitle: Tour\ndiscovered: "yes"\nmap: region\ncells: ["3_4"]\n---\nSecret de la tour.\n')
            self.assertEqual(messages(root), [])
            entries = {e["name"]: e for e in Exporter(load(root)).entries()}
            self.assertEqual(entries["Lieux"]["pages"][0]["ownership"], {"default": 0})  # the GM text stays hidden
            stub = entries["Lieux découverts"]["pages"][0]
            self.assertEqual((stub["name"], stub["text"]["markdown"], stub["ownership"]), ("Tour", "", {"default": 2}))
            write(root, "places/autre.md", "---\ntype: hex\ntitle: Autre\n---\nMJ.\n")
            other = next(p for e in Exporter(load(root)).entries() for p in e["pages"] if p["flags"]["ttrpg"].get("id") == "autre")
            self.assertEqual(other["ownership"], {"default": 0})  # not limited through its entry
            world = FakeWorld()
            world.scenes["Scene.SSSSSSSSSSSSSSSS"] = {"0_0": {"offset": {"i": 0, "j": 0}, "reveal": True}}  # revealed by the GM
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(sorted(world.scenes["Scene.SSSSSSSSSSSSSSSS"]), ["0_0", "3_4"])
            write(root, "places/tour.md", '---\ntype: hex\ntitle: Tour\nmap: region\ncells: ["3_4"]\n---\nSecret de la tour.\n')
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(sorted(world.scenes["Scene.SSSSSSSSSSSSSSSS"]), ["0_0"])

    def test_map_pins_open_campaign_notes(self):
        from ttrpg import foundry_live
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "adventure/a/km-a23-duel.md", "---\ntype: note\ntitle: A23\norigin: ap\nsource: JournalEntry.AAAAAAAAAAAAAAAA.JournalEntryPage.PPPPPPPPPPPPPPPP\n---\nAP\n")
            write(root, "scenes/a23-duel.md", "---\ntype: scene\ntitle: Salle de duel\n---\nCompilé.\n")
            write(root, "maps/siege.md", "---\ntype: map\ntitle: Siège\nfoundry: Scene.SSSSSSSSSSSSSSSS\n---\n")
            world = FakeWorld()
            world.pins["Scene.SSSSSSSSSSSSSSSS"] = [
                {"_id": "N1", "entryId": "AAAAAAAAAAAAAAAA", "pageId": "PPPPPPPPPPPPPPPP", "flags": None},
                {"_id": "N2", "entryId": "AAAAAAAAAAAAAAAA", "pageId": "QQQQQQQQQQQQQQQQ", "flags": None}]
            foundry_live.sync(root, world, apply=True)
            entry, page = Exporter(load(root)).pages["a23-duel"]
            n1, n2 = world.pins["Scene.SSSSSSSSSSSSSSSS"]
            self.assertEqual((n1["entryId"], n1["pageId"], n2["pageId"]), (entry, page, "QQQQQQQQQQQQQQQQ"))
            self.assertEqual(foundry_live.sync(root, world)[0]["pins"], [])
            (Path(root) / "scenes/a23-duel.md").unlink()
            foundry_live.sync(root, world, apply=True)
            self.assertEqual((n1["pageId"], n1["flags"]), ("PPPPPPPPPPPPPPPP", None))
            self.assertEqual(world.pins["Scene.SSSSSSSSSSSSSSSS"][0]["pageId"], "PPPPPPPPPPPPPPPP")

    def test_placed_notes_get_managed_pins(self):
        from ttrpg import foundry_live
        from ttrpg.foundry_export import Exporter
        from ttrpg.hexmap import hex_centre, hex_offset
        from ttrpg.vault import load
        scene = "Scene.SSSSSSSSSSSSSSSS"
        with tempfile.TemporaryDirectory() as root:
            write(root, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\n")
            write(root, "maps/region.md", f"---\ntype: map\ntitle: Région\nkind: overview\nfoundry: {scene}\ngrid: 71\n---\n")
            write(root, "places/tour.md", '---\ntype: hex\ntitle: Tour\nmap: region\ncells: ["23_30", "23_31"]\n---\nMJ.\n')
            write(root, "places/ailleurs.md", "---\ntype: hex\ntitle: Ailleurs\n---\nMJ.\n")
            self.assertEqual(messages(root), [])
            world = FakeWorld()
            foundry_live.sync(root, world, apply=True)
            pins = lambda: [d for d in world.docs.values() if d["documentName"] == "Note"]
            pin = pins()[0]["data"]
            # Foundry's getCenterPoint({i: 23, j: 30}) on a 71 px hex-columns-odd grid: (1885.63, 1633).
            self.assertEqual([(d["parent"], pin["x"], pin["y"], pin["text"]) for d in pins()], [(scene, 1886, 1633, "Tour")])
            self.assertEqual((pin["entryId"], pin["pageId"]), Exporter(load(root)).pages["tour"])
            self.assertEqual(hex_offset(*hex_centre(24, 23, 71), 71), (24, 23))
            # The scene lists the pin with its flags: the retargeting of adventure pins leaves it alone.
            world.pins[scene] = [{"_id": pins()[0]["_id"], "entryId": pin["entryId"], "pageId": pin["pageId"], "flags": pin["flags"]["ttrpg"]}]
            steps = foundry_live.sync(root, world)[0]
            self.assertEqual([steps[action] for action in ("create", "update", "delete", "pins")], [[], [], [], []])
            write(root, "places/tour.md", '---\ntype: hex\ntitle: Tour\nmap: region\ncells: ["24_23"]\n---\nMJ.\n')
            foundry_live.sync(root, world, apply=True)
            self.assertEqual((pins()[0]["data"]["x"], pins()[0]["data"]["y"]), (1455, 1740))
            write(root, "places/ailleurs.md", '---\ntype: hex\ntitle: Ailleurs\nmap: region\ncells: ["24_23"]\n---\nMJ.\n')
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(sorted(d["data"]["x"] for d in pins()), [1443, 1467])  # two places of one cell, side by side
            write(root, "places/tour.md", "---\ntype: hex\ntitle: Tour\n---\nMJ.\n")
            (Path(root) / "places/ailleurs.md").unlink()
            foundry_live.sync(root, world, apply=True)
            self.assertEqual(pins(), [])

    def test_batches_stay_small(self):
        from ttrpg.foundry_live import BATCH, batches
        docs = [{"documentName": "JournalEntryPage", "_id": str(i), "data": {"text": "x" * 10_000}} for i in range(10)]
        calls = list(batches("create", docs))
        self.assertGreater(len(calls), 2)
        self.assertTrue(all(len(json.dumps(call)) < BATCH + 11_000 for call in calls))
        self.assertEqual(sum(len(call["create"]) for call in calls), 10)


class HtmlTest(unittest.TestCase):
    def test_foundry_html(self):
        html = ('<h2>Feast</h2><p>See @UUID[Actor.x]{Oleg} and <strong>run</strong>.</p>'
                '<ul><li>One</li><li>Two</li></ul><section class="sidebar"><p>Note</p></section>'
                '<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>')
        self.assertEqual(to_markdown(html), "## Feast\n\nSee @UUID[Actor.x]{Oleg} and **run**.\n\n- One\n- Two\n\n"
                         "> [!note]\n> Note\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n")


class SessionTest(unittest.TestCase):
    def test_tracks_split_at_pauses_and_merge_by_time(self):
        from ttrpg.session import merge, speaker, tracks, utterances
        words = [(1.0, 1.4, " The"), (1.5, 2.0, " bridge."), (12.0, 12.5, " The"), (12.6, 13.0, " river.")]
        alice = utterances(words)
        self.assertEqual(alice, [(1.0, 2.0, "The bridge."), (12.0, 13.0, "The river.")])
        self.assertEqual(utterances([(55.0, 55.2, " C"), (73.0, 73.4, "'est"), (73.5, 74.0, " un")]), [(55.0, 74.0, "C'est un")])
        self.assertEqual([who for _, _, who, _ in merge({"Alice": alice, "Bob": [(6.0, 7.0, "Fire!")]})], ["Alice", "Bob", "Alice"])
        self.assertEqual(speaker(Path("1-alice.flac"), {}), ("alice", "unknown"))
        self.assertEqual(speaker(Path("speaker-001.wav"), {"speaker-001": "Hugo"}), ("Hugo", "player"))
        players = {".omegadraco": {"name": "Hugo", "role": "gm"}, "Archivist AI": {"role": "bot"}, "theo.bueno": {"name": "Théo"}}
        self.assertEqual(speaker(Path("5-_omegadraco.flac"), {}, players), ("Hugo", "gm"))
        self.assertEqual(speaker(Path("2-Archivist_AI_1906.flac"), {}, players), ("Archivist_AI_1906", "bot"))
        self.assertEqual(speaker(Path("3-theo_bueno.flac"), {}, players), ("Théo", "player"))
        with tempfile.TemporaryDirectory() as root:
            write(root, "capture/tracks/speaker-001.opus-packets", "")
            write(root, "capture/decoded/speaker-001.wav", "")
            self.assertEqual([path.name for path in tracks([Path(root) / "capture"], Path(root))], ["speaker-001.wav"])

    def test_glossary_maps_legacy_names(self):
        from ttrpg import glossary
        spells = [{"_id": "aAbfKn8maGjJjk2W", "name": "Mystic Armor", "translations": {"fr": {"name": "Armure mystique"}}}]
        runes = [{"_id": "r1", "name": "Invisibility", "translations": {"fr": {"name": "Invisibilité (rune)"}}}]
        with tempfile.TemporaryDirectory() as cache:
            for kind in glossary.DATASETS:
                data = {"spells": spells, "equipment": runes}.get(kind, [])
                (Path(cache) / f"{kind}.json").write_text(json.dumps(data))
            rows = glossary.build(cache, renames=lambda: [("spell", "Mage Armor", "Mystic Armor")])
        self.assertIn(("spells", "aAbfKn8maGjJjk2W", "Mage Armor", "Armure mystique", "Mystic Armor"), rows)
        self.assertIn(("equipment", "r1", "Invisibility", "Invisibilité (rune)", ""), rows)

    def test_drafts_only_for_missing_notes(self):
        from ttrpg.drafts import drafts
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        write(self.root, "npcs/oleg.md", "---\ntype: npc\ntitle: Oleg\n---\n")
        write(self.root, "adventure/km-a01.md", "---\ntype: ap\ntitle: A1\n---\n")
        write(self.root, "inv.tsv", "type\tid\ttitle\taliases\tmain_page\tpages\ttier\n"
              "npc\toleg\tOleg\t\t\t\t\nscene\ta01-hall\tHall\tThe Hall\tkm-a01\tkm-a01;km-zz\tmajor\n")
        made, skipped = drafts(self.root, Path(self.root) / "inv.tsv")
        self.assertEqual((made, skipped), (["scenes/a01-hall.md"], ["oleg"]))
        text = (Path(self.root) / "scenes/a01-hall.md").read_text(encoding="utf-8")
        self.assertIn("prep: draft", text)
        self.assertIn("[[km-a01]]", text)
        self.assertNotIn("km-zz", text)
        write(self.root, "lore.tsv", "type\tid\ttitle\taliases\tmain_page\tpages\ttier\n"
              "settlement\twesterhold\tWesterhold\t\t\tcity#p11;city#p29\t\nfaction\tinn-friends\tFriends\t\t\t\t\n")
        drafts(self.root, Path(self.root) / "lore.tsv")
        text = (Path(self.root) / "places/westerhold.md").read_text(encoding="utf-8")
        self.assertIn("origin: ap", text)
        self.assertIn("[p. 29](src:city#p29)", text)
        self.assertIn("origin: custom", (Path(self.root) / "factions/inn-friends.md").read_text(encoding="utf-8"))

    def test_windows_cut_between_speech(self):
        from ttrpg.session import windows
        speech = [{"start": 0, "end": 5}, {"start": 8, "end": 10}, {"start": 12, "end": 20}, {"start": 30, "end": 31}]
        self.assertEqual(windows(speech, size=10), [(0, 10), (12, 20), (30, 31)])

    def test_flight_summary_counts_a_check_once(self):
        from ttrpg.session import flight_summary
        check = {"type": "pf2e.check", "at": "+1:00.0", "data": {"actor": {"name": "Kyra"}, "statistic": "diplomacy", "outcome": "success", "dc": 20, "roll": {"total": 24}}}
        events = [{"type": "session.start", "at": "+0:00.0", "data": {"label": "S1"}},
                  {"type": "scene.summary", "at": "+0:00.0", "data": {"scene": "s", "name": "Crypt"}},
                  check, {**check, "at": "+1:00.1", "observed": True},
                  {"type": "combat.start", "at": "+2:00.0", "data": {"combat": "c1"}},
                  {"type": "combat.turn", "at": "+2:00.0", "combat": "c1:r1t0", "data": {"actor": {"name": "Goblin"}}},
                  {"type": "combat.turn", "at": "+2:30.0", "combat": "c1:r1t0", "data": {"dur": 30000}},
                  {"type": "combat.end", "at": "+5:00.0", "data": {"combat": "c1", "rounds": 2}}]
        text, day = flight_summary({"t0": "2026-10-10T18:00:00+00:00", "events": events})
        self.assertEqual(text.count("Kyra: diplomacy success, 24 vs DC 20"), 1)
        self.assertIn("- +2:00.0 to +5:00.0, 2 rounds: Goblin\n", text)
        self.assertIn("- +0:00.0 Crypt", text)
        self.assertEqual(day[:7], "2026-10")


if __name__ == "__main__":
    unittest.main()


class LibraryTest(unittest.TestCase):
    def setUp(self):
        from ttrpg import library
        self.library = library
        self.dir = tempfile.TemporaryDirectory()
        base = Path(self.dir.name)
        self.books, self.lib, self.campaign = base / "books", base / "lib", base / "campaign"
        for rel in ("Lost Omens/10. City of Marvels.pdf", "Society/01-04. Bandits of the Wood.pdf",
                    "Box/Accessories/Flip-Mat.pdf", "Box (Legacy)/Accessories/Flip-Mat.pdf", "Rules/[PZO1] GM Book.pdf"):
            write(self.books, rel, "pdf")
        write(self.campaign, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nsources:\n  km: {title: KM, pages: 9}\n")
        self.extracted = []

    def tearDown(self):
        self.dir.cleanup()

    def fake_extract(self, pdf, out):
        self.extracted.append(Path(pdf).name)
        write(out, "p001.txt", f"Cover of {Path(pdf).stem}\n")
        write(out, "p002.txt", "The Dragon of the West lairs here.\nnothing\n")
        return 2

    def test_index_ids_search_and_declare(self):
        catalog = self.library.index(self.lib, [self.books], self.fake_extract, log=lambda _: None)
        self.assertEqual(sorted(catalog), ["accessories-flip-mat", "bandits-of-the-wood",
                                           "city-of-marvels", "flip-mat", "gm-book"])
        self.assertEqual(catalog["city-of-marvels"]["title"], "City of Marvels")
        # unchanged files are not extracted again, and ids stay put
        self.extracted.clear()
        self.assertEqual(self.library.index(self.lib, [self.books], self.fake_extract, log=lambda _: None), catalog)
        self.assertEqual(self.extracted, [])
        hits = list(self.library.search(self.lib, "dragon of", ["city"]))
        self.assertEqual(hits, [("city-of-marvels", 2, "The Dragon of the West lairs here.")])
        self.library.declare(self.campaign, self.lib, "city-of-marvels", "com")
        self.assertIn("already declared as com", self.library.declare(self.campaign, self.lib, "city-of-marvels"))
        write(self.campaign, "npcs/a.md", "---\ntype: npc\ntitle: A\n---\nSeen [p. 2](src:com#p2).\n")
        self.assertEqual(messages(self.campaign), [])
        self.assertEqual((self.campaign / ".cache/sources/com/p002.txt").read_text().splitlines()[0], "The Dragon of the West lairs here.")
        # excerpts: cited pages committed in sources/, uncited ones dropped, unknown text reported
        from ttrpg.vault import load
        write(self.campaign, "sources/com/p001.txt", "old\n")
        write(self.campaign, "npcs/b.md", "---\ntype: npc\ntitle: B\n---\nMissing [p. 3](src:km#p3).\n")
        self.assertEqual(self.library.excerpts(load(self.campaign)), (1, 1, ["km#p3"]))
        self.assertEqual(sorted(p.name for p in (self.campaign / "sources").rglob("*.txt")), ["p002.txt"])
        self.assertEqual(self.library.excerpts(load(self.campaign)), (0, 0, ["km#p3"]))
        self.assertEqual(messages(self.campaign), [])
        with self.assertRaises(KeyError):
            self.library.declare(self.campaign, self.lib, "nope")

    def test_aon_marks_editions(self):
        hits = {"hits": {"hits": [{"_source": {"name": "Dahak", "category": "deity", "source_raw": ["Codex pg. 28"],
                                               "url": "/Deities.aspx?ID=337", "legacy_id": ["deity-150"], "summary": " First  child "}}]}}
        self.assertEqual(list(self.library.aon("Dahak", fetch=lambda *_: hits)),
                         [("Dahak", "deity", "Codex pg. 28", "https://2e.aonprd.com/Deities.aspx?ID=337", "First child", "remaster")])

    def test_provenance_callouts_and_open_items(self):
        from ttrpg.vault import load, open_items
        write(self.campaign, "places/w.md", "---\ntype: location\ntitle: W\n---\nCanon [p. 2](src:km#p2).\n\n"
              "> [!adaptation]\n> The keep is ruined here.\n\n> [!verify] Wiki says a mill\n> stands here.\n\n"
              "> [!question]\n> Who owns the inn?\n\n> [!secret]\n> Hidden.\n")
        self.assertEqual(messages(self.campaign), ["[!adaptation] without a citation: cite the canon it changes"])
        write(self.campaign, "npcs/glued.md", "---\ntype: npc\ntitle: Glued\n---\n> [!secret]\n> One.\n> [!secret]\n> Two.\n")
        self.assertIn("callout inside another: leave a blank line between two callouts", messages(self.campaign))
        (self.campaign / "npcs/glued.md").unlink()
        items = [(line, kind, text) for _, line, kind, text in open_items(load(self.campaign))]
        self.assertEqual(items, [(10, "verify", "Wiki says a mill"), (13, "question", "Who owns the inn?")])

    def test_long_campaign_types(self):
        write(self.campaign, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nparty: 5\n")
        write(self.campaign, "pcs/ayla.md", "---\ntype: pc\ntitle: Ayla\nplayer: Alice\nclass: Rogue\nlevel: 3\n---\nConcept.\n")
        write(self.campaign, "factions/guild.md", "---\ntype: faction\ntitle: Guild\nreputation: 12\n---\nG.\n")
        write(self.campaign, "mysteries/m.md", "---\ntype: mystery\ntitle: M\n---\n> [!secret]\n> Truth.\n")
        self.assertEqual(messages(self.campaign), [])
        from ttrpg.foundry_export import Exporter
        from ttrpg.vault import load
        write(self.campaign, "quests/q.md", "---\ntype: quest\ntitle: Q\nstate: open\n---\nQ.\n")
        write(self.campaign, "mysteries/m.md", "---\ntype: mystery\ntitle: M\nstate: open\n---\nM.\n")
        campaign = load(self.campaign)
        exporter = Exporter(campaign)
        self.assertIn("ouverte", exporter.header(campaign.notes["q"]))   # la quête
        self.assertIn("ouvert", exporter.header(campaign.notes["m"]))    # le mystère
        self.assertNotIn("ouverte", exporter.header(campaign.notes["m"]))
        campaign.notes["q"].meta["cells"] = ["23_23"]  # Foundry's Markdown would pair the underscores of two cells
        self.assertIn(r"23\_23", exporter.header(campaign.notes["q"]))
        write(self.campaign, "factions/guild.md", "---\ntype: faction\ntitle: Guild\nreputation: 60\n---\nG.\n")
        write(self.campaign, "campaign.yaml", "name: T\nsystem: pf2e\nlanguage: fr\nparty: five\n")
        self.assertEqual(sorted(messages(self.campaign)), ["party must be the number of player characters",
                                                           "reputation: must be between -50 and 50"])

    def test_section_twice_warns(self):
        write(self.campaign, "places/w.md", "---\ntype: location\ntitle: W\n---\n## Dans la campagne\nA.\n\n## Dans la campagne\nB.\n")
        self.assertEqual(messages(self.campaign), ["section 'Dans la campagne' appears twice: merge them"])

    def test_campaign_id_names_module(self):
        from ttrpg.foundry_export import Exporter
        write(self.campaign, "campaign.yaml", "name: Long title (draft)\nid: west\nsystem: pf2e\nlanguage: fr\n")
        self.assertEqual(messages(self.campaign), [])
        from ttrpg import vault
        self.assertEqual(Exporter(vault.load(self.campaign)).module_id, "ttrpg-west")
        write(self.campaign, "campaign.yaml", "name: T\nid: West Hold\nsystem: pf2e\nlanguage: fr\n")
        self.assertEqual(messages(self.campaign), ["id must be lowercase letters, digits and dashes (it names the Foundry module)"])

    def test_stats_is_bare_uuid(self):
        write(self.campaign, "npcs/v.md", "---\ntype: npc\ntitle: V\nstats: '@UUID[Compendium.pf2e.x.Actor.y]'\n---\nV.\n")
        self.assertEqual(messages(self.campaign), ["stats: '@UUID[Compendium.pf2e.x.Actor.y]' must be the bare uuid (Compendium.pf2e...), not a link"])

    def test_scanned_books_detected(self):
        self.assertTrue(self.library.mostly_images(["", " \n", "x" * 50, ""]))
        self.assertFalse(self.library.mostly_images(["text " * 20] * 3 + [""] * 2))

    def test_events_before_start_are_history(self):
        write(self.campaign, "campaign.yaml", 'name: T\nsystem: pf2e\nlanguage: fr\nstart: "4725-01-01"\n')
        write(self.campaign, "events/war.md", '---\ntype: event\ntitle: War\ndate: "4719-05-01"\n---\nPast.\n')
        self.assertEqual(messages(self.campaign), [])
        write(self.campaign, "events/war.md", '---\ntype: event\ntitle: War\ndate: "4719-05-01"\nplayed: "yes"\n---\nPast.\n')
        self.assertEqual(messages(self.campaign), ["played on 4719-05-01, before the campaign starts (4725-01-01): events before start are the setting's past"])

    def test_creatures_budget_and_filters(self):
        from ttrpg import creatures
        self.assertEqual([creatures.budget(5, t) for t in creatures.THREATS], [50, 80, 100, 150, 200])
        self.assertEqual((creatures.xp(1, 3), creatures.xp(8, 3)), (20, None))
        write(self.books, "pf2e/system.json", json.dumps({"id": "pf2e", "packs": [
            {"name": "bestiary", "type": "Actor", "path": "packs/bestiary"}, {"name": "iconics", "type": "Actor", "path": "packs/iconics"}]}))
        docs = [{"_id": "a1", "name": "Ghoul", "type": "npc", "system": {"details": {"level": {"value": 1}}, "traits": {"value": ["undead"], "rarity": "common"}}},
                {"_id": "a2", "name": "Wolf", "type": "npc", "system": {"details": {"level": {"value": 1}}, "traits": {"value": ["animal"]}}},
                {"_id": "a3", "name": "Pit", "type": "hazard", "system": {"details": {"level": {"value": 0}}, "traits": {"value": ["trap"]}}},
                {"_id": "a4", "name": "Hero", "type": "character"}]
        rows = creatures.build(self.books / "pf2e", self.lib / "creatures.json", log=lambda _: None, unpack=lambda path: docs)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["uuid"] for r in creatures.find(rows, range(0, 3), ["Undead"])], ["Compendium.pf2e.bestiary.Actor.a1"])
        self.assertEqual([r["name"] for r in creatures.find(rows, hazards=True)], ["Pit"])

    def test_company(self):
        write(self.campaign, "places/inn.md", "---\ntype: location\ntitle: Inn\n---\nI.\n")
        write(self.campaign, "pcs/company.md", "---\ntype: company\ntitle: La compagnie\nrenown: local\nbase: inn\n---\nC.\n")
        self.assertEqual(messages(self.campaign), [])
        write(self.campaign, "pcs/company.md", "---\ntype: company\ntitle: La compagnie\nrenown: famous\n---\nC.\n")
        self.assertEqual(len(messages(self.campaign)), 1)

    def test_hexmap_matches_foundry_offsets_and_fits(self):
        from ttrpg import hexmap
        # offsets read from Foundry 14 (hex columns, size 61, image origin 158.48, 152.5)
        for (x, y), want in {(1346, 1272): (23, 28), (952, 1314): (24, 20), (564, 1374): (25, 13),
                             (910, 412): (9, 20), (752, 1522): (27, 17)}.items():
            self.assertEqual(hexmap.hex_offset(x + 158.48264889255228, y + 152.5, 61), want)
        places = [("A", "city", 0, 0, ""), ("B", "city", 1, 0, ""), ("C", "city", 0, 1, ""), ("Far", "city", 50, 50, "")]
        out, errors = hexmap.place(places, {"A": (100, 500), "B": (300, 500), "C": (100, 300)}, 61, (0, 0), (1000, 1000))
        self.assertEqual([row[:4] for row in out], [("A", "city", 100, 500), ("B", "city", 300, 500), ("C", "city", 100, 300)])
        self.assertLess(max(errors.values()), 1e-6)
        with self.assertRaises(KeyError):
            hexmap.place(places, {"A": (0, 0), "B": (1, 0), "Nowhere": (2, 2)}, 61, (0, 0), (10, 10))
