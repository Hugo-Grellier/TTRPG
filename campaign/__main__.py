import argparse
import json
import os
from contextlib import closing
from pathlib import Path

from .core import DomainError
from .library import ROOT, import_pdf, library_document
from .store import (add_observation, add_preparation, add_proposal, add_simulated_event,
                    add_source, connect, correct_fact, create_campaign, establish_fact,
                    journey_view)
from .web import serve
from .paths import data_dir
from .scenario import apply_agent_review, index_document, review_packet
from .dossier_files import dossier_documents, init_dossier, validate_dossier


def main():
    parser = argparse.ArgumentParser(description="Local campaign workbench")
    parser.add_argument("command", choices=["serve", "fixture", "reset", "check", "import-pdf", "index-scenario", "scenario-packet", "review-scenario", "init-dossier", "check-dossier"])
    parser.add_argument("--db", default=os.environ.get("CAMPAIGN_DB", data_dir() / "campaign.db"))
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--campaign-id", type=int)
    parser.add_argument("--file")
    parser.add_argument("--title", default="")
    parser.add_argument("--document-id", type=int)
    parser.add_argument("--first-page", type=int)
    parser.add_argument("--last-page", type=int)
    args = parser.parse_args()
    path = Path(args.db)
    if args.command == "reset":
        if path.exists():
            path.unlink()
        print(f"Test database reset: {path}")
    elif args.command == "check":
        with closing(connect(path)) as db:
            print("SQLite database ready; foreign_keys enabled:", db.execute("PRAGMA foreign_keys").fetchone()[0])
    elif args.command == "import-pdf":
        if not args.campaign_id or not args.file:
            parser.error("import-pdf requires --campaign-id and --file")
        try:
            with closing(connect(path)) as db:
                document_id = import_pdf(db, args.campaign_id, args.file, args.title)
                document = library_document(db, args.campaign_id, document_id)
                print(f"Private source #{document_id}: {document['title']} · {document['page_count']} PDF pages")
                print(f"Open: http://127.0.0.1:{args.port}/workspace/{args.campaign_id}?doc=library_documents:{document_id}")
        except DomainError as exc:
            parser.error(exc.localized())
    elif args.command in ("init-dossier", "check-dossier"):
        if not args.campaign_id:
            parser.error(f"{args.command} requires --campaign-id")
        with closing(connect(path)) as db:
            if args.command == "init-dossier":
                print(f"Private Markdown dossier: {init_dossier(db, args.campaign_id)}")
            else:
                problems = validate_dossier(db, args.campaign_id)
                for problem in problems:
                    print(problem)
                print(f"{len(dossier_documents(db, args.campaign_id))} sheets · {len(problems)} broken links/locators")
                if problems:
                    raise SystemExit(1)
    elif args.command in ("index-scenario", "scenario-packet", "review-scenario"):
        if not args.campaign_id or not args.document_id:
            parser.error(f"{args.command} requires --campaign-id and --document-id")
        with closing(connect(path)) as db:
            if args.command == "index-scenario":
                stats = index_document(db, args.campaign_id, args.document_id)
                print(f"{stats['pages']} pages indexed · {stats['selected']} selected · {stats['pending']} pending")
            elif args.command == "scenario-packet":
                if not args.first_page or not args.last_page:
                    parser.error("scenario-packet requires --first-page and --last-page")
                print(json.dumps(review_packet(db, args.campaign_id, args.document_id,
                                               args.first_page, args.last_page), ensure_ascii=False, indent=2))
            else:
                if not args.file:
                    parser.error("review-scenario requires --file")
                review_path = Path(args.file).expanduser().resolve()
                if review_path.is_relative_to(ROOT):
                    parser.error("Review JSON must stay outside the source repository")
                result = apply_agent_review(db, args.campaign_id, args.document_id,
                                            json.loads(review_path.read_text(encoding="utf-8")))
                print(f"Agent review applied: {result['elements']} elements · {result['candidates']} candidates · {result['sections']} sections")
    elif args.command == "fixture":
        with closing(connect(path)) as db:
            existing = db.execute("""SELECT 1 FROM facts f JOIN decisions d ON d.id=f.decision_id
              JOIN observations o ON o.id=d.observation_id JOIN sources s ON s.id=o.source_id
              JOIN campaigns c ON c.id=f.campaign_id
              WHERE c.name=? AND s.title=? AND f.text=?""",
              ("The Ford Watchers", "Fictional GM notebook", "Mira promised to keep the crossing open until dawn.")).fetchone()
            if not existing:
                cid = create_campaign(db, "The Ford Watchers")
                sid = add_source(db, cid, "Fictional GM notebook", "page 3", "An invented note for this demo; no licensed material.")
                oid = add_observation(db, cid, sid, "Mira promised to keep the crossing open until dawn.", "simulated_play")
                establish_fact(db, cid, oid, "Accept the promise from simulated play.", "Mira promised to keep the crossing open until dawn.")
                print(f"M0 fixture loaded: campaign {cid}")
            row = db.execute("SELECT id FROM campaigns WHERE name=?", ("Mira's ford — offline loop",)).fetchone()
            if row:
                print(f"M1 fixture already loaded: campaign {row[0]}")
                return
            cid = create_campaign(db, "Mira's ford — offline loop")
            sid = add_source(db, cid, "Fictional ford note", "page 1", "Invented source: Mira keeps the ford open when the bell rings.")
            draft = add_proposal(db, cid, sid, "Mira has abandoned the ford and the crossing is closed.")
            revised = add_proposal(db, cid, sid, "Mira is at the ford; the bell signals when the crossing is safe.", draft)
            oid = add_observation(db, cid, sid, "The note says Mira guards the crossing when the bell rings.")
            fact = establish_fact(db, cid, oid, "Accept the bell condition for this campaign.", "Mira keeps the ford open when the bell rings.")
            prep = add_preparation(db, cid, fact, revised, "Travelers arrive before the bell rings; Mira asks them to wait.", "Wait for the bell; look for a boat; ask Mira for a guide.")
            add_simulated_event(db, cid, prep, "The players look for a boat instead of waiting.", "Mira sends a guide to help them cross.")
            event_observation = journey_view(db, cid)[2][0]["observation_id"]
            establish_fact(db, cid, event_observation, "Consolidate the simulated branch.", "Mira's guide helped the travelers cross by boat.")
            correct_fact(db, cid, fact, oid, "Clarify the old shorthand before future preparation.", "Mira keeps the ford open only after the bell rings.")
            print(f"M1 fixture loaded: campaign {cid}")
    else:
        serve(path, args.port)


if __name__ == "__main__":
    main()
