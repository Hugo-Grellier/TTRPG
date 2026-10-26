import tempfile
import json
import unittest
from pathlib import Path

from campaign.dossier_files import (backlinks, dossier_document, dossier_documents,
                                    init_dossier, linked_markdown, validate_dossier, visual_file)
from campaign.store import add_comment, add_observation, add_source, comments_for, connect, create_campaign, establish_fact
from campaign.workspace import document_context, render_workspace


class CampaignDossierFilesTest(unittest.TestCase):
    def test_private_markdown_files_link_comment_and_update_from_another_editor(self):
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / 'campaign.db')
            campaign = create_campaign(db, 'Fictional campaign', 'fr')
            root = Path(temp) / f'dossier-{campaign}'
            (root / 'personnages').mkdir(parents=True)
            (root / '00-Commencer.md').write_text('# Commencer\n\nVoir [Mira](personnages/mira.md).\n')
            (root / 'personnages/mira.md').write_text('# Mira\n\nElle garde le pont.\n')
            docs = dossier_documents(db, campaign)
            self.assertEqual(len(docs), 2)
            home, person = docs
            self.assertIn(f'campaign_files:{person["id"]}', linked_markdown(db, campaign, home['id'],
                           dossier_document(db, campaign, home['id'])[1]))
            self.assertEqual(backlinks(db, campaign, person['id']), [(home['id'], 'Commencer')])
            html = render_workspace(db, campaign, f'campaign_files:{person["id"]}')
            self.assertIn('Fiches de campagne', html)
            self.assertIn('Liens entrants', html)
            self.assertIn('Commencer', html)
            self.assertNotIn('Elle garde le pont.', document_context(db, campaign, f'campaign_files:{person["id"]}', include_text=False))
            self.assertIn('Elle garde le pont.', document_context(db, campaign, f'campaign_files:{person["id"]}', include_text=True))
            add_comment(db, campaign, 'campaign_files', person['id'], 'pont', 'Quel pont ?', line_start=3, line_end=3)
            self.assertEqual(len(comments_for(db, campaign, 'campaign_files', person['id'])), 1)
            (root / 'personnages/mira.md').write_text('# Mira\n\nElle garde le gué.\n')
            updated = render_workspace(db, campaign, f'campaign_files:{person["id"]}')
            self.assertIn('Elle garde le gué.', updated)
            self.assertIn('Ce passage a changé', updated)
            other = create_campaign(db, 'Other')
            with self.assertRaises(Exception):
                dossier_document(db, other, person['id'])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM facts').fetchone()[0], 0)
            db.close()

    def test_original_campaign_can_start_and_extend_private_sheets(self):
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / 'campaign.db')
            campaign = create_campaign(db, 'New world', 'en')
            root = init_dossier(db, campaign)
            self.assertEqual(len(dossier_documents(db, campaign)), 4)
            (root / 'people').mkdir()
            (root / 'people/mira.md').write_text('# Mira\n\nShe wants to keep the ford open.\n')
            (root / '01-Enjeux.md').write_text('# Stakes\n\n[Mira](people/mira.md) can help.\n')
            self.assertEqual(validate_dossier(db, campaign), [])
            self.assertEqual(len(dossier_documents(db, campaign)), 5)
            self.assertIn('People <span>1</span>', render_workspace(db, campaign))
            outside = Path(temp) / 'outside.md'
            outside.write_text('# Private elsewhere\n')
            (root / 'people/outside.md').symlink_to(outside)
            self.assertEqual(len(dossier_documents(db, campaign)), 5)
            (root / '01-Enjeux.md').write_text('# Stakes\n\n[Missing](people/nobody.md)\n')
            self.assertEqual(len(validate_dossier(db, campaign)), 1)
            db.close()

    def test_private_bible_and_visual_stay_inside_the_campaign(self):
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / 'campaign.db')
            campaign = create_campaign(db, 'Visual pilot', 'fr')
            root = init_dossier(db, campaign)
            (root / 'assets').mkdir()
            (root / 'assets/map.png').write_bytes(b'private map')
            (root / 'bible.json').write_text(json.dumps({'title': 'Départ', 'lead': 'État proposé',
                                                          'map': 'map.png', 'map_file': '00-Commencer.md',
                                                          'state': [{'label': 'Table', 'text': 'Aucune séance jouée'}]}))
            self.assertIn('Aucune séance jouée', render_workspace(db, campaign))
            self.assertIn(f'/campaign/{campaign}/visual/map.png', render_workspace(db, campaign))
            source = add_source(db, campaign, 'Journal', 'séance 1', 'test')
            observation = add_observation(db, campaign, source, 'Le pont est tombé')
            establish_fact(db, campaign, observation, 'Décision MJ', 'Le pont est détruit')
            self.assertIn('Le pont est détruit', render_workspace(db, campaign))
            self.assertIn('ÉTAT DE TABLE ET SCÉNARIO PROPOSÉ', render_workspace(db, campaign))
            self.assertEqual(visual_file(db, campaign, 'map.png').read_bytes(), b'private map')
            for name in ('../campaign.db', 'map.svg', 'missing.png'):
                with self.assertRaises(Exception):
                    visual_file(db, campaign, name)
            other = create_campaign(db, 'Other', 'fr')
            with self.assertRaises(Exception):
                visual_file(db, other, 'map.png')
            db.close()


if __name__ == '__main__':
    unittest.main()
