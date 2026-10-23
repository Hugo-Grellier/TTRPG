# Scénarios adverses et preuves

La fixture versionnée `make fixture` est entièrement fictive. Elle vérifie un trajet court, pas la qualité d'un AP ou d'une séance. Les nouveaux scénarios doivent partir des sept réussites de `VISION.md` et chercher comment une assertion pourrait être fausse.

| Risque à falsifier | Jeu d'essai avant intégration | Preuve exigée |
| --- | --- | --- |
| Mémoire longue / provenance | promesse ancienne, deux sources divergentes, repères cassés | réponse avec source et incertitude, correction testée |
| AP / canon / proposition | chapitre source contredit la table, idée rejetée | états distincts à l'écran et dans les requêtes |
| Correction tardive | attribution changée après préparation et publication | dépendances corrigées, publication déjà vue signalée |
| Confidentialité | secret MJ dans plusieurs objets liés | test négatif de toute lecture/publication joueur |
| Bifurcation / préparation | joueurs simulés suivent puis quittent l'AP | fiche jouable et conséquences durables, revue éditoriale |
| Foundry | scène retouchée entre deux synchronisations | test sur v14 réel, aperçu de conflit, aucun écrasement/doublon |
| Transcription | deux voix sur une piste et apartés hors jeu | locuteur incertain, aucune promotion abusive au canon |
| Panne / plafond | fournisseur indisponible et coût au plafond | accès aux préparations, refus de dépense, reprise idempotente |

Pour chaque jalon, enregistrer séparément test automatique, essai intégré, inspection visuelle si pertinente, environnement réel externe, revue de qualité ressentie, limites. Une QA indépendante reçoit la vision, le scénario et le produit, puis tente de produire une contre-preuve sans adopter les hypothèses d'implémentation. Si aucun agent séparé n'est disponible, effectuer une seconde passe depuis cette matrice après l'implémentation.

Les PDF sous licence, extraits longs, transcriptions réelles et audio brut restent dans l'environnement privé de test. Les fixtures publiques et les rapports ne contiennent que des inventions ou des références autorisées.
