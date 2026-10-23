import tempfile
import threading
import unittest
import sqlite3
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from campaign.core import DomainError
from campaign.store import add_observation, add_source, campaign_view, connect, create_campaign, establish_fact
from campaign.web import make_handler


class CampaignRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = connect(Path(self.tmp.name) / "test.db")
        self.addCleanup(self.db.close)
        self.a = create_campaign(self.db, "A")
        self.b = create_campaign(self.db, "B")
        self.source = add_source(self.db, self.a, "Journal fictif", "p. 2", "Texte de test")

    def test_provenance_and_decision_are_required(self):
        observation = add_observation(self.db, self.a, self.source, "Une promesse ambiguë", "simulated_play")
        self.assertEqual(campaign_view(self.db, self.a)[3], [])  # Observation != fait.
        establish_fact(self.db, self.a, observation, "Le MJ tranche", "La promesse tient jusqu'à l'aube")
        facts = campaign_view(self.db, self.a, "promesse")[3]
        self.assertEqual(len(facts), 1)
        self.assertEqual((facts[0]["source_title"], facts[0]["locator"], facts[0]["instruction"]),
                         ("Journal fictif", "p. 2", "Le MJ tranche"))
        self.assertEqual(campaign_view(self.db, self.a, "absent")[3], [])

    def test_cross_campaign_and_player_visibility_are_rejected(self):
        with self.assertRaises(DomainError):
            add_observation(self.db, self.b, self.source, "Fuite")
        observation = add_observation(self.db, self.a, self.source, "Secret")
        with self.assertRaises(DomainError):
            establish_fact(self.db, self.b, observation, "Voler", "Fuite")
        with self.assertRaises(DomainError):
            establish_fact(self.db, self.a, observation, "Publier", "Secret", access="player")
        self.assertEqual(self.db.execute("SELECT count(*) FROM facts").fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO observations(campaign_id, source_id, text, kind) VALUES (?, ?, ?, ?)",
                            (self.b, self.source, "Fuite SQL", "note"))

    def test_http_form_to_sqlite_to_search(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(self.tmp.name) / "http.db"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"

        def post(path, fields, origin=None):
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if origin:
                headers["Origin"] = origin
            return urlopen(Request(base + path, urlencode(fields).encode(), headers))

        with post("/campaign", {"name": "HTTP", "language": "fr"}) as response:
            self.assertEqual(response.status, 200)  # urllib follows 303.
        with connect(Path(self.tmp.name) / "http.db") as db:
            cid = db.execute("SELECT id FROM campaigns WHERE name='HTTP'").fetchone()[0]
        post(f"/campaign/{cid}/source", {"title": "Carnet", "locator": "page 7", "note": "Essai"}).close()
        post(f"/campaign/{cid}/observation", {"source_id": "1", "text": "Mira promet", "kind": "simulated_play"}).close()
        post(f"/campaign/{cid}/fact", {"observation_id": "1", "instruction": "Confirmer", "fact": "Mira promet le pont"}).close()
        with urlopen(base + f"/campaign/{cid}?q=pont") as response:
            body = response.read().decode()
        self.assertIn("Mira promet le pont", body)
        self.assertIn("Carnet", body)
        self.assertIn("page 7", body)
        with self.assertRaises(HTTPError) as error:
            post(f"/campaign/{cid}/source", {"title": "X", "locator": "Y", "note": "Z"}, "http://evil.example")
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(base + f"/campaign/{cid}", headers={"Host": f"evil.example:{server.server_port}"}))
        self.assertEqual(error.exception.code, 403)
        error.exception.close()


if __name__ == "__main__":
    unittest.main()
