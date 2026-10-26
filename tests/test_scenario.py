import tempfile
import unittest
from pathlib import Path

from campaign.scenario import _candidate, analyze_document, classify_headings, dossier_stats, index_document, summarize_document
from campaign.store import connect, create_campaign
from campaign.workspace import document_context, render_workspace


class ScenarioDossierTests(unittest.TestCase):
    def test_short_scene_titles_are_kept(self):
        self.assertEqual(_candidate('A4. Cuisine'), ('scene', 'A4. Cuisine'))
        self.assertEqual(_candidate('B6. Maître'), ('scene', 'B6. Maître'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = connect(Path(self.temp.name) / 'private.db')
        self.campaign = create_campaign(self.db, 'Fictional test', 'fr')
        with self.db:
            self.document = self.db.execute("""INSERT INTO library_documents
                (campaign_id,title,source_path,sha256,page_count,extraction_method)
                VALUES(?,?,?,?,?,'pdftotext')""",
                (self.campaign, 'Invented adventure', '/tmp/invented.pdf', 'example', 3)).lastrowid
            for number, content in enumerate((
                'Opening\n',
                'CHAPITRE 1 :\nLE PASSAGE\nA1. La vieille porte\nSi les PJ ouvrent la porte, une cloche sonne.\n',
                'A2. Le pont\nMAISON DES BRUMES\nLes PJ découvrent la clef sous la pierre.\n'), 1):
                self.db.execute("INSERT INTO library_pages(campaign_id,document_id,pdf_page,text,quality) VALUES(?,?,?,?,?)",
                                (self.campaign, self.document, number, content, 'text'))

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_resumable_review_and_source_links_without_canon(self):
        indexed = index_document(self.db, self.campaign, self.document)
        self.assertEqual(indexed['pages'], 3)
        self.assertGreaterEqual(indexed['candidates'], 2)
        reviewed = self.db.execute("SELECT COUNT(*) FROM scenario_candidates WHERE kind NOT IN ('scene','heading','event','encounter')").fetchone()[0]
        calls = []

        def reviewer(prompt):
            calls.append(prompt)
            ids = [int(line.split('|')[0].strip()) for line in prompt.splitlines() if ' | ' in line]
            return {'keep': [ids[0]]}

        result = analyze_document(self.db, self.campaign, self.document, reviewer=reviewer, batch_size=1)
        self.assertEqual(result['pending'], 0)
        self.assertEqual(result['selected'], result['candidates'])
        self.assertEqual(len(calls), reviewed)
        self.assertEqual(analyze_document(self.db, self.campaign, self.document, reviewer=reviewer)['selected'], result['selected'])
        self.assertEqual(len(calls), reviewed)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM facts').fetchone()[0], 0)
        summarize_document(self.db, self.campaign, self.document,
                           summarizer=lambda _: {'summary': 'Les joueurs explorent la porte et le pont.'})
        classify_headings(self.db, self.campaign, self.document,
                          classifier=lambda _: {'types': {str(r['id']): 'place' for r in self.db.execute("SELECT id FROM scenario_candidates WHERE kind='heading'")}})
        html = render_workspace(self.db, self.campaign, f'scenario_dossiers:{self.document}')
        self.assertIn('3/3 pages indexées', html)
        self.assertIn(f'doc=library_documents:{self.document}&amp;page=2#L3', html)
        self.assertIn('Rien ici n’est canonique', html)
        self.assertIn('Les joueurs explorent la porte', html)
        self.assertIn('Lieux', html)
        self.assertIn('Parcours par scène', html)
        self.assertIn('éléments liés', html)
        hidden = document_context(self.db, self.campaign, f'scenario_dossiers:{self.document}', include_text=False)
        shared = document_context(self.db, self.campaign, f'scenario_dossiers:{self.document}', include_text=True)
        self.assertNotIn('La vieille porte', hidden)
        self.assertIn('La vieille porte', shared)

    def test_rejects_unknown_model_ids_and_other_campaign(self):
        index_document(self.db, self.campaign, self.document)
        with self.assertRaises(ValueError):
            analyze_document(self.db, self.campaign, self.document, reviewer=lambda _: {'keep': [99999]})
        self.assertGreater(dossier_stats(self.db, self.campaign, self.document)['pending'], 0)
        other = create_campaign(self.db, 'Other')
        with self.assertRaises(Exception):
            dossier_stats(self.db, other, self.document)


if __name__ == '__main__':
    unittest.main()
