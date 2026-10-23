# Atelier de campagne (nom de travail)

Assistant de campagne pour MJ, au stade de fondation locale. [Vision](VISION.md) · [Roadmap](docs/ROADMAP.md) · [État de reprise](docs/STATE.md).

## Prérequis et commandes

Python 3.12+ et `make`. Aucun paquet Python, compte cloud ni API payante n'est nécessaire.

```sh
make doctor        # versions et SQLite
make fixture       # campagne fictive, idempotent
make start         # http://127.0.0.1:8765
make check         # tests et compilation
make reset         # efface la base locale de test (serveur arrêté)
make resume        # santé + état de reprise
```

`make demo` charge la fixture puis démarre le serveur. `DB=/tmp/essai.db PORT=8899 make demo` permet une base et un port isolés. Arrêter avec Ctrl+C.

## Démonstration actuelle

Ouvrir une campagne fictive. Chercher « promis » : le fait renvoie à une décision, une observation et un repère dans une source fictive. Créer ensuite une campagne, enregistrer une source localisée, relever une observation (note ou jeu simulé), formuler une décision du MJ et un fait établi, puis retrouver ce fait par recherche. Recharger la page : SQLite conserve les données. Une observation seule reste non canonique.

Ce prototype ne lit aucun PDF, ne prépare pas de séance et n'a ni connexion Foundry/Discord ni compte utilisateur. Il écoute uniquement sur `127.0.0.1` et ne doit pas être exposé tel quel au réseau. La seule visibilité disponible est MJ. La fixture est inventée et peut être supprimée avec `make reset`.

## Travail avec un agent

Dans une nouvelle session Claude Code ou Codex, saisir **« Continue la roadmap. »**. Pour une remarque sur l'expérience, formuler directement le ressenti et le résultat voulu. Le protocole est dans [WORKFLOW.md](docs/WORKFLOW.md) ; aucune approbation de ticket ou de plan n'est requise.
