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
            self.assertIn("[p. 3](src:km#p3)", oleg["markdown"])
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
