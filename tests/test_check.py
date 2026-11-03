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
            write(root, "npcs/n.md", "---\ntype: npc\ntitle: Oleg\n---\nVoir [[f]] demain.\n")
            (Path(root) / "factions/f.md").unlink()
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertEqual(done, {"created": 0, "updated": 1, "deleted": 1, "missing": []})  # the factions entry, its page with it
            page = next(d for d in world.docs.values() if d["documentName"] == "JournalEntryPage")
            page["data"]["text"]["markdown"] += "\n\nAjouté dans Foundry."
            steps, done = foundry_live.sync(root, world, apply=True)
            self.assertIsNone(done)
            self.assertEqual(len(steps["edited"]), 1)
            self.assertEqual(foundry_live.pull(root, world)["updated"], ["npcs/n.md"])
            self.assertIn("Ajouté dans Foundry.", (Path(root) / "npcs/n.md").read_text())
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
