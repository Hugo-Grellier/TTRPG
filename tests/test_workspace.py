import tempfile
import threading
import unittest
import subprocess
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from campaign.agent_cli import (apply_draft_file, draft_checkout, draft_file_review,
                                parse_claude, parse_codex, run_cli)
from campaign.core import DomainError
from campaign.paths import data_dir
from campaign.markdown import render_blocks
from campaign.prep_drafts import (apply_preparation_draft, ensure_preparation_draft,
                                  preparation_draft_review, restart_preparation_draft)
from campaign.skills import available_skills
from campaign.store import (add_comment, add_observation, add_preparation, add_proposal,
                            add_source, agent_turns, comments_for, connect,
                            create_campaign, establish_fact, product_doc)
from campaign.web import make_handler
from campaign.workspace import render_workspace


class WorkspaceTest(unittest.TestCase):
    def test_private_preparation_draft_requires_gm_acceptance(self):
        with tempfile.TemporaryDirectory() as directory, closing(connect(Path(directory) / "db.sqlite")) as db:
            cid = create_campaign(db, "Ford")
            other = create_campaign(db, "Other")
            source = add_source(db, cid, "Note", "p. 1", "Mira watches the ford")
            observation = add_observation(db, cid, source, "Mira watches the ford")
            fact = establish_fact(db, cid, observation, "Accept", "Mira watches the ford")
            proposal = add_proposal(db, cid, source, "Wait for a guide")
            prep = add_preparation(db, cid, fact, proposal, "Travelers arrive", "Wait or cross")
            state = Path(directory) / "private"
            checkout = state / "drafts" / f"campaign-{cid}"
            checkout.mkdir(parents=True)
            with patch("campaign.prep_drafts.data_dir", return_value=state), patch(
                "campaign.prep_drafts.draft_checkout", return_value=checkout
            ):
                path = ensure_preparation_draft(db, cid, prep)
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "unchanged")
                with self.assertRaises(DomainError):
                    ensure_preparation_draft(db, other, prep)
                path.write_text(path.read_text().replace("Travelers arrive", "Travelers reach the ford"))
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "ready")
                self.assertEqual(db.execute("SELECT situation FROM preparations WHERE id=?", (prep,)).fetchone()[0], "Travelers arrive")
                apply_preparation_draft(db, cid, prep)
                self.assertEqual(db.execute("SELECT situation FROM preparations WHERE id=?", (prep,)).fetchone()[0], "Travelers reach the ford")
                self.assertEqual(db.execute("SELECT count(*) FROM preparation_revisions").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 1)
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "applied")
                accepted = path.read_text()
                path.write_text(path.read_text().replace("<!-- field:situation -->", ""))
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "invalid")
                with self.assertRaises(DomainError):
                    apply_preparation_draft(db, cid, prep)
                path.write_text(accepted.replace("# Preparation #1", "# Edited title"))
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "invalid")
                path.write_text(accepted)
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "applied")
                restart_preparation_draft(db, cid, prep)
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "unchanged")
                path.write_text(path.read_text().replace("Wait or cross", "Cross at dusk"))
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "ready")
                db.execute("UPDATE preparations SET situation=? WHERE id=?", ("Another GM edit", prep))
                db.commit()
                self.assertEqual(preparation_draft_review(db, cid, prep)["status"], "conflict")
                with self.assertRaises(DomainError):
                    apply_preparation_draft(db, cid, prep)

    def test_local_skill_catalog_excludes_hidden_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / ".agents/skills/story-review"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: story-review\ndescription: Review a scene.\n---\n")
            hidden = root / ".agents/skills/.trash/old"
            hidden.mkdir(parents=True)
            (hidden / "SKILL.md").write_text("---\nname: hidden\ndescription: Old.\n---\n")
            with patch("campaign.skills.ROOT", root), patch("campaign.skills.Path.home", return_value=root):
                self.assertEqual(available_skills(), [("story-review", "Review a scene.", "Shared")])

    def test_reviewed_draft_applies_once_and_refuses_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            (root / "docs").mkdir()
            target = root / "docs/WORKFLOW.md"
            target.write_text("Original\n")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "docs/WORKFLOW.md"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "base"], check=True)
            state = Path(directory) / "private"
            with patch("campaign.agent_cli.ROOT", root), patch("campaign.agent_cli.data_dir", return_value=state):
                draft = draft_checkout(1)
                (draft / "docs/WORKFLOW.md").write_text("Proposed\n")
                self.assertEqual(draft_file_review(1, 5)["status"], "ready")
                apply_draft_file(1, 5)
                self.assertEqual(target.read_text(), "Proposed\n")
                self.assertEqual(draft_file_review(1, 5)["status"], "applied")
                target.write_text("Manual edit\n")
                self.assertEqual(draft_file_review(1, 5)["status"], "conflict")
                with self.assertRaises(DomainError):
                    apply_draft_file(1, 5)
                self.assertEqual(target.read_text(), "Manual edit\n")
                with self.assertRaises(DomainError):
                    apply_draft_file(1, 99)

    def test_private_storage_path_is_configurable_outside_checkout(self):
        with patch.dict("os.environ", {"TTRPG_DATA_DIR": "/tmp/private-campaigns"}):
            self.assertEqual(data_dir(), Path("/tmp/private-campaigns"))

    def test_markdown_is_rendered_without_executing_source_html(self):
        blocks = list(render_blocks("# Heading\n\nA **bold** word.\n\n<script>alert(1)</script>"))
        rendered = "".join(block[2] for block in blocks)
        self.assertIn("<h1>Heading</h1>", rendered)
        self.assertIn("<strong>bold</strong>", rendered)
        self.assertNotIn("<script>", rendered)

    def test_cli_invocations_edit_isolated_draft_and_resume_explicit_sessions(self):
        with patch("campaign.agent_cli.draft_checkout", return_value=Path('/tmp/draft')), patch("campaign.agent_cli.shutil.which", side_effect=lambda name: name), patch(
            "campaign.agent_cli.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, '{"type":"thread.started","thread_id":"abc"}\n{"type":"item.completed","item":{"type":"agent_message","text":"Draft"}}', ""),
        ) as process:
            self.assertEqual(run_cli("codex", "Revise"), ("Draft", "abc", True))
            self.assertIn("workspace-write", process.call_args.args[0])
            self.assertEqual(process.call_args.kwargs['cwd'], Path('/tmp/draft'))
            run_cli("codex", "Continue", "abc")
            self.assertEqual(process.call_args.args[0][-3:], ["resume", "abc", "Continue"])
        with patch("campaign.agent_cli.draft_checkout", return_value=Path('/tmp/draft')), patch("campaign.agent_cli.shutil.which", return_value="claude"), patch(
            "campaign.agent_cli.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, '{"result":"Draft","session_id":"xyz"}', ""),
        ) as process:
            self.assertEqual(run_cli("claude", "Revise", "xyz"), ("Draft", "xyz", True))
            self.assertIn("--tools=Read,Grep,Glob,Edit,Write,Skill", process.call_args.args[0])
            self.assertIn("--restricted", process.call_args.args[0])
            self.assertNotIn("Bash", " ".join(process.call_args.args[0]))

    def test_comment_stays_private_and_does_not_change_canon(self):
        with tempfile.TemporaryDirectory() as directory, closing(connect(Path(directory) / "db.sqlite")) as db:
            cid = create_campaign(db, "Gué", "fr")
            other = create_campaign(db, "Other")
            source = add_source(db, cid, "Carnet", "p. 1", "Mira garde le gué")
            markdown_source = add_source(db, cid, "Markdown note", "p. 2", "Mira **garde** le gué")
            self.assertIn("<strong>garde</strong>", render_workspace(db, cid, f"sources:{markdown_source}"))
            add_comment(db, cid, "sources", source, "Mira garde", "Rendre cela plus ambigu")
            self.assertIn("Rendre cela plus ambigu", render_workspace(db, cid, f"sources:{source}"))
            self.assertIn("Commentaires", render_workspace(db, cid, f"sources:{source}"))
            self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 0)
            self.assertEqual(len(comments_for(db, cid, "sources", source)), 1)
            add_comment(db, cid, "sources", source, "Mira garde", "Review line 1", line_start=1, line_end=1)
            self.assertIn('data-line="1"', render_workspace(db, cid, f"sources:{source}"))
            self.assertIn('L1', render_workspace(db, cid, f"sources:{source}"))
            with self.assertRaises(DomainError):
                add_comment(db, cid, "sources", source, "Mira", "Wrong line", line_start=2, line_end=2)
            with self.assertRaises(DomainError):
                add_comment(db, other, "sources", source, "Mira", "Leak")
            with self.assertRaises(DomainError):
                add_comment(db, cid, "sources", source, "invented quote", "Wrong anchor")
            with self.assertRaises(DomainError):
                add_comment(db, cid, "sources", source, "Mira", "Leak", access="player")
            _, vision = product_doc(1)
            self.assertIn("Product vision", vision)
            add_comment(db, cid, "product_docs", 1, "Product vision", "Lead with conversation")
            add_comment(db, cid, "product_docs", 1, "a new, independent tool", "Review precise selection", line_start=3, line_end=3, char_offset=34)
            product_page = render_workspace(db, cid, "product_docs:1")
            self.assertIn("Lead with conversation", product_page)
            self.assertIn('data-quote="Product vision"', product_page)
            self.assertIn("<strong>new, independent tool</strong>", product_page)
            self.assertEqual(len(comments_for(db, cid, "product_docs", 1)), 2)
            self.assertEqual(comments_for(db, cid, "product_docs", 1)[1]["char_offset"], 34)
            self.assertEqual(len(comments_for(db, other, "product_docs", 1)), 0)
            with self.assertRaises(DomainError):
                add_comment(db, cid, "product_docs", 99, "Product vision", "Invalid file")

    def test_cli_json_and_browser_routes(self):
        self.assertEqual(parse_codex('{"type":"thread.started","thread_id":"abc"}\n{"type":"item.completed","item":{"type":"agent_message","text":"Draft"}}'), ("Draft", "abc"))
        self.assertEqual(parse_claude('{"result":"Draft","session_id":"xyz"}'), ("Draft", "xyz"))
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "db.sqlite"
            with closing(connect(db_path)) as db:
                cid = create_campaign(db, "Mira's ford", "en")
                source = add_source(db, cid, "Note", "page 1", "Mira keeps the ford")
                observation = add_observation(db, cid, source, "Mira keeps the ford")
                fact = establish_fact(db, cid, observation, "Accept this", "Mira keeps the ford")
                proposal = add_proposal(db, cid, source, "Travelers must wait")
                preparation = add_preparation(db, cid, fact, proposal, "Travelers arrive", "Wait or find a boat")
                other = create_campaign(db, "Other")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(thread.join, 2)
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            base = f"http://127.0.0.1:{server.server_port}"

            def post(path, fields):
                return urlopen(Request(base + path, urlencode(fields).encode(),
                                       {"Content-Type": "application/x-www-form-urlencoded"}))

            with urlopen(base + "/") as response:
                self.assertIn("/workspace/1", response.read().decode())
            with urlopen(base + "/workspace/1?doc=sources:1") as response:
                body = response.read().decode()
                self.assertIn("Mira keeps the ford", body)
                self.assertIn("Address review comments", body)
                self.assertIn('class="sidebar-tabs"', body)
                self.assertNotIn('title="VISION.md"', body)
            with urlopen(base + "/workspace/1?doc=product_docs:1") as response:
                product_body = response.read().decode()
                self.assertIn("Product vision", product_body)
                self.assertIn('title="VISION.md"', product_body)
            with urlopen(base + f"/workspace/1?doc=preparations:{preparation}") as response:
                self.assertIn("Download preparation as Markdown", response.read().decode())
            with urlopen(base + f"/campaign/1/preparation/{preparation}.md") as response:
                exported = response.read().decode()
                self.assertIn("Travelers arrive", exported)
                self.assertIn("Wait or find a boat", exported)
                self.assertEqual(response.headers["Content-Type"], "text/markdown; charset=utf-8")
                self.assertIn("attachment", response.headers["Content-Disposition"])
            with self.assertRaises(HTTPError) as missing:
                urlopen(base + f"/campaign/{other}/preparation/{preparation}.md")
            self.assertEqual(missing.exception.code, 400)
            missing.exception.close()
            with urlopen(base + "/assets/workspace.css") as response:
                self.assertIn("text/css", response.headers["Content-Type"])
                self.assertIn(".app-shell", response.read().decode())
            post("/campaign/1/comment", {"target_kind": "sources", "target_id": source,
                                        "quote": "Mira keeps", "body": "Check the bell",
                                        "line_start": 1, "line_end": 1, "char_offset": 0}).close()
            with urlopen(base + "/workspace/1?doc=sources:1") as response:
                self.assertIn("Check the bell", response.read().decode())
            with patch("campaign.web.run_cli", return_value=("A possible revision", "session-1", True)) as cli:
                post("/campaign/1/chat", {"provider": "codex", "doc": "sources:1", "prompt": "Revise Mira"}).close()
            self.assertIn("Check the bell", cli.call_args.args[1])
            with patch("campaign.web.apply_draft_file") as apply:
                post("/campaign/1/apply-draft", {"file_id": 5}).close()
            apply.assert_called_once_with(1, 5)
            with closing(connect(db_path)) as db:
                turn = agent_turns(db, cid)[0]
                self.assertEqual((turn["response"], turn["status"], turn["session_id"]),
                                 ("A possible revision", "complete", "session-1"))
                self.assertEqual(db.execute("SELECT count(*) FROM facts").fetchone()[0], 1)
            with self.assertRaises(HTTPError) as error:
                post("/campaign/1/comment", {"target_kind": "sources", "target_id": source,
                                            "quote": "missing", "body": "Bad"})
            self.assertEqual(error.exception.code, 400)
            error.exception.close()


if __name__ == "__main__":
    unittest.main()
