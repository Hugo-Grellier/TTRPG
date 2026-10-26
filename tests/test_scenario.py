import tempfile
import unittest
from pathlib import Path

from campaign.scenario import _candidate, apply_agent_review, dossier_stats, index_document, review_packet
from campaign.store import connect, create_campaign
from campaign.workspace import document_context, render_workspace


class ScenarioDossierTests(unittest.TestCase):
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
        index_document(self.db, self.campaign, self.document)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_short_scene_titles_are_kept(self):
        self.assertEqual(_candidate('A4. Cuisine'), ('scene', 'A4. Cuisine'))
        self.assertEqual(_candidate('B6. Maître'), ('scene', 'B6. Maître'))

    def test_chat_agent_review_is_private_resumable_and_source_linked(self):
        packet = review_packet(self.db, self.campaign, self.document, 2, 3)
        self.assertEqual([p['pdf_page'] for p in packet['pages']], [2, 3])
        self.assertEqual(packet['pages'][0]['lines'][2]['text'], 'A1. La vieille porte')
        scene = next(r for r in packet['candidates'] if r['name'] == 'A1. La vieille porte')
        place = next(r for r in packet['candidates'] if r['name'] == 'MAISON DES BRUMES')
        section = packet['sections'][0]
        review = {'document_id': self.document, 'source_sha256': packet['source_sha256'], 'reviewer': 'codex-chat',
                  'candidates': [{'id': scene['id'], 'status': 'selected', 'note': 'Une porte sonne quand les PJ entrent.'},
                                 {'id': place['id'], 'status': 'selected', 'category': 'place', 'note': 'Lieu à explorer.'}],
                  'elements': [{'kind': 'person', 'title': 'La gardienne', 'body': 'Elle attend près de la porte.',
                                'pdf_page': 2, 'line_number': 3, 'quote': 'La vieille porte'},
                               {'kind': 'scene', 'title': 'A1. La vieille porte', 'body': 'Une cloche sonne si les PJ ouvrent la porte.',
                                'pdf_page': 2, 'line_number': 3, 'quote': 'A1. La vieille porte'}],
                  'sections': [{'id': section['id'], 'summary': 'Les PJ explorent la porte et le pont.'}]}
        self.assertEqual(apply_agent_review(self.db, self.campaign, self.document, review), {'candidates': 2, 'sections': 1, 'elements': 2})
        self.assertEqual(apply_agent_review(self.db, self.campaign, self.document, review), {'candidates': 2, 'sections': 1, 'elements': 2})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM scenario_elements').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT attempts FROM scenario_candidates WHERE id=?', (scene['id'],)).fetchone()[0], 0)
        self.assertEqual(dossier_stats(self.db, self.campaign, self.document)['selected'], 2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM facts').fetchone()[0], 0)
        html = render_workspace(self.db, self.campaign, f'scenario_dossiers:{self.document}')
        self.assertIn('3/3 pages indexées', html)
        self.assertIn(f'doc=library_documents:{self.document}&amp;page=2#L3', html)
        self.assertIn('Les PJ explorent la porte et le pont.', html)
        self.assertIn('Lieu à explorer.', html)
        self.assertIn('Fiches rédigées dans le chat', html)
        self.assertIn('Parcours par scène', html)
        self.assertIn('Une cloche sonne si les PJ ouvrent la porte.', html)
        hidden = document_context(self.db, self.campaign, f'scenario_dossiers:{self.document}', include_text=False)
        shared = document_context(self.db, self.campaign, f'scenario_dossiers:{self.document}', include_text=True)
        self.assertNotIn('La vieille porte', hidden)
        self.assertIn('La vieille porte', shared)

    def test_rejects_wrong_source_cross_campaign_and_invalid_category_atomically(self):
        packet = review_packet(self.db, self.campaign, self.document, 2, 2)
        candidate = packet['candidates'][0]
        wrong = {'document_id': self.document, 'source_sha256': 'wrong', 'reviewer': 'codex-chat',
                 'candidates': [{'id': candidate['id'], 'status': 'selected'}]}
        with self.assertRaises(ValueError):
            apply_agent_review(self.db, self.campaign, self.document, wrong)
        wrong['candidates'] = []
        wrong['elements'] = [{'kind': 'person', 'title': 'Intrus', 'body': 'Un détail fabriqué.',
                              'pdf_page': 2, 'line_number': 3, 'quote': 'Cette citation est fausse'}]
        with self.assertRaises(ValueError):
            apply_agent_review(self.db, self.campaign, self.document, wrong)
        wrong['source_sha256'] = packet['source_sha256']
        wrong['candidates'].append({'id': 99999, 'status': 'selected'})
        with self.assertRaises(ValueError):
            apply_agent_review(self.db, self.campaign, self.document, wrong)
        self.assertEqual(dossier_stats(self.db, self.campaign, self.document)['selected'], 0)
        other = create_campaign(self.db, 'Other')
        with self.assertRaises(Exception):
            review_packet(self.db, other, self.document, 1, 1)


if __name__ == '__main__':
    unittest.main()
