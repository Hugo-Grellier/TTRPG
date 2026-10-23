import argparse
import os
from contextlib import closing
from pathlib import Path

from .store import add_observation, add_source, connect, create_campaign, establish_fact
from .web import serve


def main():
    parser = argparse.ArgumentParser(description="Atelier de campagne local")
    parser.add_argument("command", choices=["serve", "fixture", "reset", "check"])
    parser.add_argument("--db", default=os.environ.get("CAMPAIGN_DB", "data/campaign.db"))
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()
    path = Path(args.db)
    if args.command == "reset":
        if path.exists():
            path.unlink()
        print(f"Base de test remise à zéro : {path}")
    elif args.command == "check":
        with closing(connect(path)) as db:
            print("Base SQLite prête ; contrôle foreign_keys :", db.execute("PRAGMA foreign_keys").fetchone()[0])
    elif args.command == "fixture":
        with closing(connect(path)) as db:
            if db.execute("""SELECT 1 FROM facts f JOIN decisions d ON d.id=f.decision_id
              JOIN observations o ON o.id=d.observation_id JOIN sources s ON s.id=o.source_id
              JOIN campaigns c ON c.id=f.campaign_id
              WHERE c.name=? AND s.title=? AND f.text=?""",
              ("Les Veilleurs du gué", "Carnet fictif du MJ", "Mira a promis de garder le passage ouvert jusqu'à l'aube.")).fetchone():
                print("Fixture déjà présente")
                return
            cid = create_campaign(db, "Les Veilleurs du gué")
            sid = add_source(db, cid, "Carnet fictif du MJ", "page 3", "Une note inventée pour la démonstration ; aucun livre sous licence.")
            oid = add_observation(db, cid, sid, "Mira a promis de garder le passage ouvert jusqu'à l'aube.", "simulated_play")
            establish_fact(db, cid, oid, "Retenir la promesse du jeu simulé.", "Mira a promis de garder le passage ouvert jusqu'à l'aube.")
            print(f"Fixture chargée : campagne {cid}")
    else:
        serve(path, args.port)


if __name__ == "__main__":
    main()
