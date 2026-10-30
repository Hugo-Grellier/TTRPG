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

    def test_player_visibility(self):
        write(self.root, "h.md", "---\ntype: handout\ntitle: H\nvisibility: players\n---\n[[oleg]]\n")
        self.assertIn("players note links GM-only note [[oleg]]", messages(self.root))

    def test_edited_ap_note_needs_modified_origin(self):
        write(self.root, "ap.md", f"---\ntype: note\ntitle: AP\norigin: ap\nsource_hash: {body_hash('Original.')}\n---\nChanged.\n")
        self.assertIn("set origin: modified", messages(self.root)[0])
        check(self.root, fix=True)
        self.assertIn("origin: modified", (Path(self.root) / "ap.md").read_text())
        self.assertEqual(messages(self.root), [])


class HtmlTest(unittest.TestCase):
    def test_foundry_html(self):
        html = ('<h2>Feast</h2><p>See @UUID[Actor.x]{Oleg} and <strong>run</strong>.</p>'
                '<ul><li>One</li><li>Two</li></ul><section class="sidebar"><p>Note</p></section>'
                '<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>')
        self.assertEqual(to_markdown(html), "## Feast\n\nSee @UUID[Actor.x]{Oleg} and **run**.\n\n- One\n- Two\n\n"
                         "> [!note]\n> Note\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n")


if __name__ == "__main__":
    unittest.main()
