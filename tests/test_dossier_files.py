import tempfile
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from campaign.dossier_files import (backlinks, bible_element_texts, dossier_document, dossier_documents,
                                    init_dossier, linked_markdown, validate_dossier, visual_file)
from campaign.store import (add_bible_comment, add_comment, add_observation, add_source, bible_comments,
                            comments_for, connect, create_campaign, establish_fact)
from campaign.workspace import document_context, render_workspace
from campaign.web import make_handler


class CampaignDossierFilesTest(unittest.TestCase):
    def test_bible_review_targets_tolerate_missing_optional_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / 'campaign.db')
            campaign = create_campaign(db, 'Partial bible', 'fr')
            root = init_dossier(db, campaign)
            (root / 'bible.json').write_text(json.dumps({
                'title': 'Départ', 'lead': 'Essai',
                'state': [{'label': 'Table'}, {'text': 'Sans étiquette'}],
                'stakes': [{'file': '01-Enjeux.md'}, {'title': 'Sans fiche'}],
                'scenes': [{'file': '00-Commencer.md', 'summary': 'Ouverture'}],
                'relations': {'nodes': [{'file': '02-Relations.md'}]},
            }))
            self.assertEqual(bible_element_texts(db, campaign), {
                'hero': 'Départ — Essai',
                'state:Table': 'Table',
                'stakes:01-Enjeux.md': '01-Enjeux.md',
                'scenes:00-Commencer.md': '00-Commencer.md — Ouverture',
                'relation:02-Relations.md': '02-Relations.md',
            })
            db.close()

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
            self.assertIn(f'/workspace/{campaign}?doc=library_documents:7&page=12', linked_markdown(
                db, campaign, home['id'], '[PDF](source:pdf/7/12#L4)'))
            self.assertEqual(backlinks(db, campaign, person['id']), [(home['id'], 'Commencer')])
            html = render_workspace(db, campaign, f'campaign_files:{person["id"]}')
            self.assertIn('sheet-mode ', html)
            self.assertNotIn('sheet-mode review-open', html)
            self.assertIn('id="sheet-review-toggle" aria-expanded="false"', html)
            self.assertIn('id="comment-form" hidden', html)
            self.assertIn('data-line-start="3" data-line-end="3"', html)
            self.assertIn('Fiches de campagne', html)
            self.assertIn('Liens entrants', html)
            self.assertIn('Commencer', html)
            self.assertNotIn('Elle garde le pont.', document_context(db, campaign, f'campaign_files:{person["id"]}', include_text=False))
            self.assertIn('Elle garde le pont.', document_context(db, campaign, f'campaign_files:{person["id"]}', include_text=True))
            add_comment(db, campaign, 'campaign_files', person['id'], 'pont', 'Quel pont ?', line_start=3, line_end=3)
            self.assertEqual(len(comments_for(db, campaign, 'campaign_files', person['id'])), 1)
            with_comments = render_workspace(db, campaign, f'campaign_files:{person["id"]}')
            self.assertIn('sheet-mode review-open', with_comments)
            self.assertIn('id="sheet-review-toggle" aria-expanded="true"', with_comments)
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
            (root / 'bible.json').write_text(json.dumps({'title': 'Start', 'lead': 'An open ford'}))
            self.assertIn('Current state', render_workspace(db, campaign))
            self.assertIn('No played session has been recorded', render_workspace(db, campaign))
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
                                                          'state': [{'label': 'Table', 'text': 'Aucune séance jouée'}],
                                                          'stakes': [{'tag': 'Urgence · rouge', 'title': 'Sauvetage'}]}))
            self.assertIn('Aucune séance jouée', render_workspace(db, campaign))
            self.assertIn('<small>Urgence</small>', render_workspace(db, campaign))
            self.assertNotIn('Urgence · rouge', render_workspace(db, campaign))
            self.assertIn(f'/campaign/{campaign}/visual/map.png', render_workspace(db, campaign))
            commented = add_bible_comment(db, campaign, 'state:Table', 'Préciser le début de séance')
            self.assertEqual(bible_comments(db, campaign)[0]['id'], commented)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM facts').fetchone()[0], 0)
            self.assertIn('Préciser le début de séance', render_workspace(db, campaign, comment_mode=True))
            self.assertIn('data-bible-key="state:Table" data-bible-quote=', render_workspace(db, campaign, comment_mode=True))
            (root / 'bible.json').write_text(json.dumps({'title': 'Départ', 'lead': 'État proposé',
                                                          'state': [{'label': 'Table', 'text': 'La salle est occupée'}]}))
            self.assertIn('Cet élément a changé', render_workspace(db, campaign, comment_mode=True))
            with self.assertRaises(Exception):
                add_bible_comment(db, campaign, 'state:Inventé', 'Impossible')
            source = add_source(db, campaign, 'Journal', 'séance 1', 'test')
            observation = add_observation(db, campaign, source, 'Le pont est tombé')
            fact_id = establish_fact(db, campaign, observation, 'Décision MJ', 'Le pont est détruit')
            self.assertIn('Le pont est détruit', render_workspace(db, campaign))
            self.assertIn('ÉTAT DE TABLE ET SCÉNARIO PROPOSÉ', render_workspace(db, campaign))
            self.assertIn(f'data-bible-key="fact:{fact_id}"', render_workspace(db, campaign, comment_mode=True))
            add_bible_comment(db, campaign, f'fact:{fact_id}', 'À discuter')
            self.assertEqual(visual_file(db, campaign, 'map.png').read_bytes(), b'private map')
            for name in ('../campaign.db', 'map.svg', 'missing.png'):
                with self.assertRaises(Exception):
                    visual_file(db, campaign, name)
            other = create_campaign(db, 'Other', 'fr')
            with self.assertRaises(Exception):
                visual_file(db, other, 'map.png')
            with self.assertRaises(Exception):
                add_bible_comment(db, other, 'state:Table', 'Copie interdite')
            db.close()

    def test_bible_comment_http_journey(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / 'campaign.db'
            db = connect(db_path)
            campaign = create_campaign(db, 'Review pilot', 'fr')
            root = init_dossier(db, campaign)
            (root / 'bible.json').write_text(json.dumps({'title': 'Départ', 'lead': 'Essai',
                                                          'state': [{'label': 'Table', 'text': 'La salle est vide'}]}))
            db.close()
            server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(db_path))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                payload = urlencode({'target_key': 'state:Table', 'body': 'Ajouter les joueurs'}).encode()
                with urlopen(Request(f'{base}/campaign/{campaign}/bible-comment', data=payload)) as response:
                    self.assertIn('comment=1', response.url)
                    self.assertIn('Ajouter les joueurs', response.read().decode())
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(f'{base}/campaign/{campaign}/bible-comment',
                                    data=urlencode({'target_key': 'state:Autre', 'body': 'Erreur'}).encode()))
                self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


if __name__ == '__main__':
    unittest.main()
