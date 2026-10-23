import argparse
import os
from contextlib import closing
from pathlib import Path

from .store import add_observation, add_source, connect, create_campaign, establish_fact
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
            if db.execute("""SELECT 1 FROM facts f JOIN decisions d ON d.id=f.decision_id
              JOIN observations o ON o.id=d.observation_id JOIN sources s ON s.id=o.source_id
              JOIN campaigns c ON c.id=f.campaign_id
              WHERE c.name=? AND s.title=? AND f.text=?""",
              ("The Ford Watchers", "Fictional GM notebook", "Mira promised to keep the crossing open until dawn.")).fetchone():
                print("Fixture already loaded")
                return
            cid = create_campaign(db, "The Ford Watchers")
            sid = add_source(db, cid, "Fictional GM notebook", "page 3", "An invented note for this demo; no licensed material.")
            oid = add_observation(db, cid, sid, "Mira promised to keep the crossing open until dawn.", "simulated_play")
            establish_fact(db, cid, oid, "Accept the promise from simulated play.", "Mira promised to keep the crossing open until dawn.")
            print(f"Fixture loaded: campaign {cid}")
    else:
        serve(path, args.port)


if __name__ == "__main__":
    main()
