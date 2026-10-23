import tempfile
import threading
import unittest
import sqlite3
from string import Formatter
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from campaign.core import DomainError
from campaign.i18n import catalog, t
from campaign.store import (add_observation, add_preparation, add_proposal, add_simulated_event,
                            add_source, campaign_view, connect, correct_fact, create_campaign,
                            establish_fact, journey_view)
from campaign.web import make_handler


class CampaignRulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = connect(Path(self.tmp.name) / "test.db")
        self.addCleanup(self.db.close)
        self.a = create_campaign(self.db, "A")
        self.b = create_campaign(self.db, "B")
        self.source = add_source(self.db, self.a, "Fictional journal", "p. 2", "Test note")

    def test_provenance_and_decision_are_required(self):
        observation = add_observation(self.db, self.a, self.source, "An ambiguous promise", "simulated_play")
        self.assertEqual(campaign_view(self.db, self.a)[3], [])  # Observation != fact.
        establish_fact(self.db, self.a, observation, "The GM decides", "The promise holds until dawn")
        facts = campaign_view(self.db, self.a, "promise")[3]
        self.assertEqual(len(facts), 1)
        self.assertEqual((facts[0]["source_title"], facts[0]["locator"], facts[0]["instruction"]),
                         ("Fictional journal", "p. 2", "The GM decides"))
        self.assertEqual(campaign_view(self.db, self.a, "missing")[3], [])

    def test_cross_campaign_and_player_visibility_are_rejected(self):
        with self.assertRaises(DomainError):
            add_observation(self.db, self.b, self.source, "Leak")
        observation = add_observation(self.db, self.a, self.source, "Secret")
        with self.assertRaises(DomainError):
            establish_fact(self.db, self.b, observation, "Steal", "Leak")
        with self.assertRaises(DomainError):
            establish_fact(self.db, self.a, observation, "Publish", "Secret", access="player")
        self.assertEqual(self.db.execute("SELECT count(*) FROM facts").fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO observations(campaign_id, source_id, text, kind) VALUES (?, ?, ?, ?)",
                            (self.b, self.source, "SQL leak", "note"))

    def test_ui_catalogs_cover_the_same_keys(self):
        self.assertEqual(set(catalog("en")), set(catalog("fr")))
        for key, english in catalog("en").items():
            fields = lambda value: {name for _, name, _, _ in Formatter().parse(value) if name}
            self.assertEqual(fields(english), fields(catalog("fr")[key]), key)
        self.assertEqual(t("facts.title", "fr"), "Faits établis")
        self.assertEqual(t("facts.title", "en"), "Established facts")

    def test_offline_loop_correction_and_campaign_boundary(self):
        draft = add_proposal(self.db, self.a, self.source, "Mira has abandoned the ford")
        revised = add_proposal(self.db, self.a, self.source, "Mira still guards the ford", draft)
        self.assertEqual(campaign_view(self.db, self.a)[3], [])
        observed = add_observation(self.db, self.a, self.source, "Mira promised to hold the crossing")
        original = establish_fact(self.db, self.a, observed, "Accept promise", "Mira holds the crossing until dawn")
        prep = add_preparation(self.db, self.a, original, revised, "Travelers reach Mira's ford", "Wait for dawn or seek a boat")
        event = add_simulated_event(self.db, self.a, prep, "Players seek a boat", "Mira sends a guide")
        proposals, preparations, events, corrections = journey_view(self.db, self.a)
        self.assertEqual((proposals[0]["revised_from"], events[0]["id"]), (draft, event))
        self.assertIsNone(events[0]["consequence"])
        self.assertEqual(campaign_view(self.db, self.a)[1][0]["title"], "Simulated play record")
        consequence = establish_fact(self.db, self.a, events[0]["observation_id"], "Confirm branch", "Mira's guide helps the travelers cross")
        correction = correct_fact(self.db, self.a, original, observed, "Promise was conditional", "Mira holds the crossing only if the bell rings")
        _, preparations, events, corrections = journey_view(self.db, self.a)
        self.assertEqual((preparations[0]["new_fact_id"], events[0]["consequence"], corrections[0]["new_fact_id"]),
                         (correction, "Mira's guide helps the travelers cross", correction))
        self.assertEqual(campaign_view(self.db, self.a, "guide")[3][0]["id"], consequence)
        self.assertIn(consequence, [f["id"] for f in campaign_view(self.db, self.a, "dawn")[3]])
        with self.assertRaises(DomainError):
            add_preparation(self.db, self.b, original, revised, "Leak", "Leak")
        with self.assertRaises(DomainError):
            add_proposal(self.db, self.b, self.source, "Leak")
        with self.assertRaises(DomainError):
            add_simulated_event(self.db, self.b, prep, "Leak", "Leak")
        with self.assertRaises(DomainError):
            add_proposal(self.db, self.a, self.source, "Player draft", access="player")
        with self.assertRaises(DomainError):
            add_preparation(self.db, self.a, original, revised, "Player prep", "Leak", access="player")
        with self.assertRaises(DomainError):
            add_simulated_event(self.db, self.a, prep, "Player event", "Leak", access="player")
        with self.assertRaises(DomainError):
            correct_fact(self.db, self.a, consequence, observed, "Player correction", "Leak", access="player")
        with self.assertRaises(DomainError):
            correct_fact(self.db, self.a, original, observed, "Again", "Again")

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

        with post("/campaign", {"name": "HTTP", "language": "en"}) as response:
            self.assertEqual(response.status, 200)  # urllib follows 303.
        with connect(Path(self.tmp.name) / "http.db") as db:
            cid = db.execute("SELECT id FROM campaigns WHERE name='HTTP'").fetchone()[0]
        post(f"/campaign/{cid}/source", {"title": "Notebook", "locator": "page 7", "note": "Test"}).close()
        post(f"/campaign/{cid}/observation", {"source_id": "1", "text": "Mira promises", "kind": "simulated_play"}).close()
        post(f"/campaign/{cid}/fact", {"observation_id": "1", "instruction": "Confirm", "fact": "Mira promises the bridge"}).close()
        with urlopen(base + f"/campaign/{cid}?q=bridge") as response:
            self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
            body = response.read().decode()
        self.assertIn("Mira promises the bridge", body)
        self.assertIn("Notebook", body)
        self.assertIn("page 7", body)
        self.assertIn("Established facts", body)
        post(f"/campaign/{cid}/proposal", {"source_id": "1", "text": "Draft crossing", "revised_from": ""}).close()
        post(f"/campaign/{cid}/proposal", {"source_id": "1", "text": "Revised crossing", "revised_from": "1"}).close()
        post(f"/campaign/{cid}/preparation", {"fact_id": "1", "proposal_id": "2", "situation": "At the crossing", "alternatives": "Wait or boat"}).close()
        post(f"/campaign/{cid}/event", {"preparation_id": "1", "player_action": "Take the boat", "ruling": "They cross"}).close()
        with urlopen(base + f"/campaign/{cid}") as response:
            body = response.read().decode()
        self.assertIn("Revised crossing", body)
        self.assertIn("Take the boat", body)
        self.assertIn("Awaiting GM consolidation", body)
        with connect(Path(self.tmp.name) / "http.db") as db:
            event_observation = journey_view(db, cid)[2][0]["observation_id"]
        post(f"/campaign/{cid}/fact", {"observation_id": str(event_observation), "instruction": "Confirm", "fact": "The boat crosses safely"}).close()
        post(f"/campaign/{cid}/correction", {"old_fact_id": "1", "observation_id": "1", "instruction": "Correct", "fact": "Mira promises the crossing only at dawn"}).close()
        with urlopen(base + f"/campaign/{cid}?q=Mira") as response:
            body = response.read().decode()
        self.assertIn("Dependent prep sheets", body)
        self.assertIn("Needs review: based on corrected fact", body)
        with urlopen(base + f"/campaign/{cid}?q=bridge") as response:
            body = response.read().decode()
        self.assertIn("The boat crosses safely", body)
        self.assertIn("Consequence of simulated branch", body)
        with urlopen(base + "/?lang=fr") as response:
            self.assertIn("Vos campagnes", response.read().decode())
        with post("/campaign", {"name": "French UI", "language": "fr"}) as response:
            self.assertIn("Faits établis", response.read().decode())
        with self.assertRaises(HTTPError) as error:
            post("/campaign/2/source", {"title": "", "locator": "page 1", "note": "Test"})
        self.assertIn("Titre doit contenir", error.exception.read().decode())
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            post("/campaign/2/observation", {"source_id": "abc", "text": "Test", "kind": "note"})
        self.assertIn("Valeur de formulaire invalide", error.exception.read().decode())
        error.exception.close()
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
