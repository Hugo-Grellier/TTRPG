import subprocess
import tempfile
import threading
import time
import unittest
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from campaign.core import DomainError
from campaign.library import import_pdf, library_document, library_page, library_search
from campaign.store import add_comment, comments_for, connect, create_campaign
from campaign.workspace import document_context, render_workspace
from campaign.web import make_handler


class LibraryTest(unittest.TestCase):
    def test_private_pdf_pages_remain_sources_with_comments_and_page_citations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.pdf"
            path.write_bytes(b"%PDF-1.4\nfictional test")
            with closing(connect(Path(directory) / "boundary.db")) as boundary_db:
                boundary_campaign = create_campaign(boundary_db, "Boundary")
                with patch("campaign.library.ROOT", Path(directory)), self.assertRaises(DomainError):
                    import_pdf(boundary_db, boundary_campaign, path)
            def extracted(command, **_):
                if command[0] == "pdfinfo":
                    return subprocess.CompletedProcess(command, 0, "Pages: 2\n", "")
                return subprocess.CompletedProcess(command, 0,
                    b"Mira guards the ford.\n<script>alert(1)</script>\f\f", b"")
            with closing(connect(Path(directory) / "private.db")) as db:
                campaign = create_campaign(db, "Ford")
                other = create_campaign(db, "Other")
                with patch("campaign.library.shutil.which", return_value="local-tool"), patch(
                    "campaign.library.subprocess.run", side_effect=extracted
                ) as process:
                    document = import_pdf(db, campaign, path)
                    self.assertEqual(import_pdf(db, campaign, path), document)
                    self.assertEqual(process.call_count, 2)
                self.assertEqual(library_document(db, campaign, document)["page_count"], 2)
                first = library_page(db, campaign, document, 1)
                self.assertEqual(library_page(db, campaign, document, 2)["quality"], "empty")
                self.assertEqual(library_search(db, campaign, document, "Mira")[0], 1)
                add_comment(db, campaign, "library_pages", first["id"], "Mira", "Ask why", line_start=1, line_end=1)
                self.assertEqual(len(comments_for(db, campaign, "library_pages", first["id"])), 1)
                with patch("campaign.workspace.draft_diff", return_value=""):
                    page = render_workspace(db, campaign, f"library_documents:{document}", 1, "Mira")
                self.assertIn("PDF page 1 / 2", page)
                self.assertIn(f'/campaign/{campaign}/pdf/{document}#page=1', page)
                self.assertIn(f'<iframe class="pdf-reader" src="/campaign/{campaign}/pdf/{document}#page=1"', page)
                self.assertIn('<details class="pdf-extracted" open>', page)
                empty_page = render_workspace(db, campaign, f"library_documents:{document}", 2)
                self.assertIn('sheet-mode ', empty_page)
                self.assertNotIn('sheet-mode review-open', empty_page)
                self.assertIn(f'<iframe class="pdf-reader" src="/campaign/{campaign}/pdf/{document}#page=2"', empty_page)
                self.assertIn("Ask why", page)
                self.assertIn("&lt;script&gt;", page)
                self.assertNotIn("<script>alert(1)</script>", page)
                self.assertIn("PDF page 1/2", document_context(db, campaign, f"library_documents:{document}", 1))
                metadata_only = document_context(db, campaign, f"library_documents:{document}", 1, False)
                self.assertIn("PDF page 1/2", metadata_only)
                self.assertNotIn("Mira guards", metadata_only)
                self.assertNotIn("Ask why", metadata_only)
                self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 0)
                with self.assertRaises(DomainError):
                    library_page(db, other, document, 1)
                with self.assertRaises(DomainError):
                    add_comment(db, other, "library_pages", first["id"], "Mira", "Leak")
                with self.assertRaises(DomainError):
                    import_pdf(db, campaign, path, access="player")

            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(directory) / "private.db"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            seen = []
            def fake_cli(provider, prompt, previous_session=None, campaign_id=1, on_update=None):
                seen.append(prompt)
                return "Mock answer", "mock-session", True
            try:
                pdf_url = f"http://127.0.0.1:{server.server_port}/campaign/{campaign}/pdf/{document}"
                with urlopen(pdf_url) as response:
                    self.assertEqual(response.headers["Content-Type"], "application/pdf")
                    self.assertIn("inline", response.headers["Content-Disposition"])
                    self.assertEqual(response.read(), path.read_bytes())
                with urlopen(Request(pdf_url, method="HEAD")) as response:
                    self.assertEqual(response.headers["Content-Length"], str(path.stat().st_size))
                    self.assertEqual(response.read(), b"")
                with urlopen(Request(pdf_url, headers={"Range": "bytes=0-7"})) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.headers["Content-Range"], f"bytes 0-7/{path.stat().st_size}")
                    self.assertEqual(response.read(), path.read_bytes()[:8])
                with self.assertRaises(HTTPError) as denied:
                    urlopen(f"http://127.0.0.1:{server.server_port}/campaign/{other}/pdf/{document}")
                self.assertEqual(denied.exception.code, 400)
                with patch("campaign.web.run_cli", side_effect=fake_cli):
                    for include_page in (False, True):
                        fields = {"provider": "codex", "doc": f"library_documents:{document}",
                                  "page": "1", "prompt": "Discuss this source"}
                        if include_page:
                            fields["include_page"] = "yes"
                        with urlopen(Request(f"http://127.0.0.1:{server.server_port}/campaign/{campaign}/chat",
                                             urlencode(fields).encode())):
                            pass
                        for _ in range(100):
                            with closing(connect(Path(directory) / "private.db")) as check:
                                complete = check.execute("SELECT count(*) FROM agent_turns WHERE status='complete'").fetchone()[0]
                            if complete == len(seen) == (2 if include_page else 1):
                                break
                            time.sleep(.02)
                        else:
                            self.fail("Mocked CLI turn did not finish")
                self.assertNotIn("Mira guards the ford", seen[0])
                self.assertNotIn("Ask why", seen[0])
                self.assertIn("Mira guards the ford", seen[1])
                self.assertIn("Ask why", seen[1])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_incomplete_extraction_does_not_store_a_partial_source(self):
        with tempfile.TemporaryDirectory() as directory, closing(connect(Path(directory) / "private.db")) as db:
            path = Path(directory) / "scenario.pdf"
            path.write_bytes(b"%PDF-1.4\nfictional test")
            campaign = create_campaign(db, "Ford")
            def incomplete(command, **_):
                output = "Pages: 2\n" if command[0] == "pdfinfo" else b"Only one page\f"
                return subprocess.CompletedProcess(command, 0, output, "")
            with patch("campaign.library.shutil.which", return_value="local-tool"), patch(
                "campaign.library.subprocess.run", side_effect=incomplete
            ), self.assertRaises(DomainError):
                import_pdf(db, campaign, path)
            self.assertEqual(db.execute("SELECT count(*) FROM library_documents").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM library_pages").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
