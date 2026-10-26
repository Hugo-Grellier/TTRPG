import tempfile
import threading
import time
import unittest
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import patch

from campaign.campaign_file_drafts import (apply_campaign_file_draft, campaign_file_draft_review,
                                           ensure_campaign_file_draft, restart_campaign_file_draft)
from campaign.dossier_files import dossier_documents, init_dossier
from campaign.store import connect, create_campaign
from campaign.web import make_handler


class CampaignFileDraftTest(unittest.TestCase):
    def test_chat_only_includes_sheet_after_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "campaign.db"
            with closing(connect(db_path)) as db:
                campaign = create_campaign(db, "Mira test", "en")
                init_dossier(db, campaign)
                file_id = dossier_documents(db, campaign)[0]["id"]
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with patch("campaign.web.run_cli", return_value=("Done", "test-session", True)) as cli, \
                     patch("campaign.web.ensure_campaign_file_draft", return_value=Path(temp) / "draft.md") as draft:
                    for include in (False, True):
                        fields = {"provider": "codex", "doc": f"campaign_files:{file_id}", "prompt": "Review the ford"}
                        if include:
                            fields["include_page"] = "yes"
                        with urlopen(Request(base + f"/campaign/{campaign}/chat", urlencode(fields).encode(),
                                             {"Content-Type": "application/x-www-form-urlencoded"})):
                            pass
                        for _ in range(100):
                            with urlopen(base + f"/campaign/{campaign}/chat-status") as response:
                                if response.read() == b"complete":
                                    break
                            time.sleep(.01)
                        else:
                            self.fail("CLI turn did not complete")
                        prompt = cli.call_args.args[1]
                        self.assertEqual("Editable private campaign sheet draft:" in prompt, include)
                        self.assertEqual("# Start here" in prompt, include)
                    draft.assert_called_once_with(unittest.mock.ANY, campaign, file_id)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_review_accept_conflict_and_invalid_links(self):
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp)
            db = connect(private / "campaign.db")
            campaign = create_campaign(db, "Mira's ford", "en")
            root = init_dossier(db, campaign)
            sheet = root / "00-Commencer.md"
            original = sheet.read_text()
            file_id = next(row["id"] for row in dossier_documents(db, campaign) if row["path"] == sheet.name)
            checkout = private / "drafts" / f"campaign-{campaign}"
            checkout.mkdir(parents=True)
            with (patch("campaign.campaign_file_drafts.data_dir", return_value=private),
                  patch("campaign.campaign_file_drafts.draft_checkout", return_value=checkout)):
                proposal = ensure_campaign_file_draft(db, campaign, file_id)
                self.assertEqual(proposal.read_text(), original)
                self.assertEqual(campaign_file_draft_review(db, campaign, file_id)["status"], "unchanged")
                proposal.write_text(original + "\n## New choice\n\nKeep the ford open.\n")
                self.assertEqual(campaign_file_draft_review(db, campaign, file_id)["status"], "ready")
                apply_campaign_file_draft(db, campaign, file_id)
                self.assertIn("Keep the ford open", sheet.read_text())
                self.assertEqual(campaign_file_draft_review(db, campaign, file_id)["status"], "applied")
                self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 0)
                restart_campaign_file_draft(db, campaign, file_id)
                proposal.write_text(sheet.read_text() + "\n[Missing](nobody.md)\n")
                review = campaign_file_draft_review(db, campaign, file_id)
                self.assertEqual(review["status"], "invalid")
                self.assertIn("missing sheet", review["problems"][0])
                with self.assertRaises(Exception):
                    apply_campaign_file_draft(db, campaign, file_id)
                proposal.write_text(sheet.read_text() + "\n## Another choice\n\nWait.\n")
                sheet.write_text(sheet.read_text() + "\nGM edited this sheet.\n")
                self.assertEqual(campaign_file_draft_review(db, campaign, file_id)["status"], "conflict")
                with self.assertRaises(Exception):
                    apply_campaign_file_draft(db, campaign, file_id)
                other = create_campaign(db, "Other", "en")
                with self.assertRaises(Exception):
                    ensure_campaign_file_draft(db, other, file_id)
            db.close()
