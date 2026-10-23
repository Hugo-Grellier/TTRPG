# Roadmap par résultats observables

**Lecture des preuves :** `I` = implémenté, `T` = tests automatiques passés, `D` = démontré sur environnement réel pertinent, `P` = qualité jugée satisfaisante par le propriétaire. Un `T` de fixture ne vaut jamais `D` sur Foundry, Discord ou AP complet. État « démontré » exige le parcours indiqué et ses limites publiées.

## Maintenant

### M0 — Fondation locale et provenance élémentaire

- **Résultat utilisateur :** le MJ crée une campagne fictive, relie une observation à une source, décide d'un fait et le retrouve avec sa provenance.
- **Démonstration :** `make demo` ; chercher « promis » dans la fixture, puis créer une autre campagne, sa source, une observation, une décision et rechercher le fait après rechargement.
- **Critères :** persistance SQLite, observation non canonique avant décision, source et décision visibles avec le résultat, refus des références entre campagnes et de la visibilité joueur.
- **Dépendances/risques :** Python local ; pas de source documentaire vérifiée ni d'identité utilisateur.
- **État :** I oui ; T oui (unitaire et trajet HTTP) ; D local HTTP et captures Chrome bureau/mobile oui ; P non demandé.
- **Limites :** saisie manuelle, une seule vue MJ, pas de correction, pas de PDF, aucun VTT.

### M1 — Une boucle de campagne hors table

- **Résultat utilisateur :** partir d'une source fictive, modifier une proposition de campagne, préparer une situation, jouer une bifurcation simulée, consolider et retrouver pourquoi l'état a changé.
- **Démonstration :** scénario fixe « gué de Mira » : le MJ corrige une proposition, ouvre une fiche de préparation, choisit une action de joueurs simulés, arbitre le retour, puis recherche la promesse et ses conséquences avec provenance.
- **Critères :** les propositions ne sont pas canoniques ; préparation et simulation sont marquées comme telles ; la correction d'un fait signale les éléments dépendants ; aucun secret n'entre dans un contenu publiable ; le parcours reste lisible après redémarrage. Tests de régression et inspection navigateur.
- **Dépendances/risques :** modèle de propositions, correction et liens de dépendance ; il faut garder l'édition simple. Commencer par un seul scénario fictif et des choix explicites, sans génération IA.
- **État :** prévu, prochain jalon prêt. I non ; T non ; D non ; P non.
- **Limites connues :** simulation manuelle, pas de vraie séance ni de PDF.
- **Unités proches :** (1) modéliser proposition et correction traçable ; (2) fiche de préparation liée au canon ; (3) événement simulé et revue groupée minimale ; (4) recherche des conséquences ; (5) parcours navigateur et QA adversariale. Livrer une unité seulement si le parcours entier reste vérifiable.

## Ensuite

### M2 — Dossier éditorial et mémoire longue

- **Résultat utilisateur :** retrouver personnes, lieux, promesses, contradictions et « what next » après une longue histoire fictive.
- **Démonstration :** rejouer plusieurs années simulées, corriger une attribution tardive et examiner les conséquences sans confondre hypothèse et fait.
- **Critères :** requêtes avec preuves, conflits ciblés, droits de lecture, corrections suivies jusqu'aux préparations et publications concernées.
- **Dépendances/risques :** M1 ; ergonomie des relations et historique des corrections.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** la qualité narrative demandera une revue humaine.

### M3 — Bibliothèque puis AP entier reprenable

- **Résultat utilisateur :** rechercher dans ses PDF avec titre/page et parcourir tous les chapitres d'un AP possédé, avec couverture et lacunes visibles.
- **Démonstration :** prototype précoce sur PDF complexes fictifs/publics, interruption/reprise ; ensuite Kingmaker entier dans un environnement privé, chaque chapitre vérifié avant déclaration de complétude.
- **Critères :** citations contrôlables, tâches idempotentes, progression et couverture, distinction AP/campagne/proposition, reprise sans duplication.
- **Dépendances/risques :** M2 pour la transformation en dossier ; extraction PDF, droits, éditions et coût de traitement. Prototype d'extraction à démarrer en parallèle de M1/M2.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** l'essai fictif ne valide pas Kingmaker ; ses PDF restent privés.

### M4 — Préparation jouable et qualité des assets

- **Résultat utilisateur :** obtenir une vue « séance dans une heure », avec situations, PNJ, bifurcations et état exact du matériel.
- **Démonstration :** une semaine fictive sans préparation, puis revue de la fiche et des éléments prêts/manquants ; comparer un prototype de carte à des références professionnelles sur lisibilité et temps de retouche.
- **Critères :** fiche utilisable hors ligne, références et incertitudes, alternatives plausibles, qualité éditoriale présentée au propriétaire.
- **Dépendances/risques :** M1 et mémoire M2 ; qualité créative, droits des assets, coût de production. Prototype de cartes tôt, avant pipeline définitif.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** une carte techniquement valide peut rester médiocre à jouer.

### M5 — Scène Foundry retouchable

- **Résultat utilisateur :** synchroniser une scène PF2e prête à inspecter sans effacer les retouches dans Foundry.
- **Démonstration :** instance Foundry v14 de test isolée, scène d'exploration puis dialogue/combat, retouche manuelle, resynchronisation et aperçu de conflit.
- **Critères :** murs/lumières/objets attendus vérifiés ; pas de doublon ; retouches préservées ; visibilité joueur testée ; qualité visuelle revue séparément.
- **Dépendances/risques :** M4 ; licence/instance de test, API Foundry, assets. Prototype de synchronisation précoce avec une scène fictive.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** aucune compatibilité Foundry prouvée aujourd'hui.

### M6 — Retour de séance et aide live contrôlée

- **Résultat utilisateur :** consulter chronologie provisoire, corriger les voix et le hors jeu, recevoir une aide courte privée puis publier seulement ce qu'il choisit.
- **Démonstration :** audio mixte fabriqué, désaccord de locuteur, panne de modèle, suggestion expirée, publication après geste du MJ ; budget de séance atteint.
- **Critères :** transcription ambiguë signalée, aucune promotion automatique au canon, secrets protégés, délai et coût mesurés, matériel préparé disponible en panne.
- **Dépendances/risques :** M2/M4/M5 ; Discord, consentement, voix partagées, 1–2 s de latence et plafond dur. Prototype audio coût/latence tôt, avant bot complet.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** un enregistrement fabriqué ne prédit pas la qualité d'une séance réelle.

### M7 — Installation, sauvegarde et campagne Kingmaker hors table complète

- **Résultat utilisateur :** installer, restaurer et parcourir la même campagne AP transformée de bout en bout avant toute séance réelle.
- **Démonstration :** restauration sur machine de test ; AP entier, bifurcations simulées, plusieurs scènes Foundry, aide live simulée, corrections et coût affichés.
- **Critères :** couverture de l'AP vérifiée, restauration testée, parcours intégré inspectable et décision du propriétaire sur l'usage réel.
- **Dépendances/risques :** M3–M6 ; packaging non technique, qualité globale et données privées.
- **État :** prévu. I/T/D/P : non.
- **Limites connues :** la valeur durable se mesurera seulement dans l'usage accepté par le MJ.
