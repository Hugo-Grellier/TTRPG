import argparse
import os
from contextlib import closing
from pathlib import Path

from .store import (add_observation, add_preparation, add_proposal, add_simulated_event,
                    add_source, connect, correct_fact, create_campaign, establish_fact,
                    journey_view)
from .web import serve


def main():
    parser = argparse.ArgumentParser(description="Local campaign workbench")
    parser.add_argument("command", choices=["serve", "fixture", "reset", "check"])
    parser.add_argument("--db", default=os.environ.get("CAMPAIGN_DB", "data/campaign.db"))
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()
    path = Path(args.db)
    if args.command == "reset":
        if path.exists():
            path.unlink()
        print(f"Test database reset: {path}")
    elif args.command == "check":
        with closing(connect(path)) as db:
            print("SQLite database ready; foreign_keys enabled:", db.execute("PRAGMA foreign_keys").fetchone()[0])
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
