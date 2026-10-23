# Architecture retenue

## Choix et compromis

Un monorepo et un cœur applicatif modulaire constituent le point de départ. Python porte le domaine, la persistance et les traitements longs ; une interface web est servie localement. TypeScript sera utilisé pour l'adaptateur Foundry v14 et, si la complexité de l'interface le justifie, pour le frontend. La tranche actuelle emploie Python standard, HTML et SQLite : installation immédiate, zéro service externe et véritable persistance. Un frontend React ou full TypeScript offrirait une meilleure unité de langage avec Foundry et un écosystème UI riche ; il ajouterait dès aujourd'hui build, dépendances et duplication des modèles autour du cœur Python préféré. Reconsidérer au moment où l'édition et la revue deviennent réellement interactives.

Le monolithe modulaire évite le coût de coordination de trois dépôts, de microservices ou d'un bus. Des paquets ou processus séparés pourront livrer le module Foundry et le bot Discord selon leurs contraintes d'installation. Aucun adaptateur ne possède une seconde vérité canonique. Une base graphe n'est pas justifiée avant des requêtes relationnelles mesurées ; SQLite relationnel permet déjà des liens et contraintes. L'event sourcing intégral complique projections et corrections ; les décisions et les provenances sont explicites dans des tables ordinaires. Une histoire des corrections sera ajoutée quand le parcours correspondant existe.

## Frontières actuelles

```text
Navigateur MJ -> campaign.web -> campaign.store -> SQLite
                             -> campaign.core (validation)
```

`campaign.core` n'importe aucune infrastructure. `campaign.store` possède les transactions et vérifie l'appartenance à une campagne. `campaign.web` ne décide pas du canon : il transmet une décision du MJ au store. Le schéma est créé au premier accès. `data/` reste hors Git. Le serveur n'écoute que la boucle locale et n'a pas d'authentification ; un accès distant demandera authentification, autorisation et migration de schéma avant usage réel.

Le noyau initial garde `campaign_id` sur chaque élément, même lorsque le lien indirect paraît suffisant : les requêtes de lecture et les vérifications d'appartenance restent explicites. Les faits sont ajoutés via une décision, avec observation et source liées. Les contraintes SQL rejettent les références absentes et toute visibilité autre que `gm`. L'API métier rejette aussi les références à une autre campagne. Une lecture joueur n'existe pas encore : on ne peut donc pas prendre l'écran MJ pour une preuve de séparation des vues.

## Frontières à ouvrir au fil des jalons

- **Bibliothèque/import** : garder les PDF privés hors dépôt ; chaque passage extrait porte document, édition, page, méthode et qualité. Un traitement long aura un identifiant, des unités de travail idempotentes, un curseur de reprise et une couverture vérifiée par chapitre. Recherche et citation restent distinctes de l'établissement canonique. Aucun import complet d'AP n'est annoncé aujourd'hui.
- **Foundry v14/PF2e** : contrat d'échange versionné avec exemples fictifs, identifiant stable d'élément et visibilité. L'adaptateur TS observe ou propose ; l'application tranche et persiste. Pour synchroniser, comparer l'état canonique, l'empreinte de la dernière exportation et l'état présent de Foundry, afficher les retouches du MJ, puis appliquer seulement les champs choisis. Les `flags` et opérations de documents de Foundry rendent ce prototype plausible, sans prouver la préservation des retouches. Voir [développement des modules](https://foundryvtt.com/article/module-development/) et [API Scene v14](https://foundryvtt.com/api/classes/foundry.documents.Scene.html).
- **Discord/transcription** : un adaptateur envoie des observations datées avec locuteur et confiance, jamais des faits. Consentement, conservation de l'audio et correction de locuteur précèdent l'essai en séance.
- **Modèles/CLI/assets** : les tâches consomment une entrée versionnée et rendent proposition, références, état et coût observé. La décision canonique reste dans le cœur. Les abonnements de développement Claude Code/Codex ne sont pas un fournisseur produit ni un budget d'inférence garanti. Le plafond produit doit être appliqué avant toute dépense, avec réservation puis rapprochement du coût réel ; au plafond, lecture locale et travaux différés.

Sauvegarde initiale : arrêter le serveur et copier le fichier SQLite. Avant des données réelles ou un schéma évolutif, ajouter migrations versionnées et test de restauration. Ne pas traiter la simple copie de la fixture comme une preuve de récupération après panne.
