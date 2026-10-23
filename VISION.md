# Vision produit — assistant de campagne pour MJ

**Statut : vision issue de l'entretien avec le MJ, 23 octobre 2026.** Ce document décrit un **nouvel outil indépendant**. LoreForge, SecondChair et d'autres ressources peuvent fournir des idées, du code ou des méthodes après examen ; leurs décisions de produit et d'architecture ne gouvernent pas cet outil. Son nom reste ouvert.

## En une minute

Un assistant de campagne pour les MJ qui veulent créer, avec leurs joueurs, des aventures aussi vivantes et marquantes que celles qui les inspirent dans *Critical Role*, avec la richesse et la finition d'un Adventure Path Pathfinder. Le MJ imagine, discute et dirige à l'échelle qui lui plaît ; l'assistant l'aide à écrire, prépare le matériel jouable, suit les choix faits à la table et entretient la cohérence de la campagne. Son but est de rendre cette ambition accessible à un MJ qui a peu de temps, sans l'épuiser à prendre des notes, chercher dans ses sources ou configurer Foundry.

*Critical Role* exprime l'ambition narrative : personnages mémorables, scènes fortes, improvisation et conséquences sensibles des choix des joueurs. Les Adventure Paths et les créateurs de cartes cités par le MJ expriment l'ambition de finition du matériel. La qualité de jeu d'un groupe reste une œuvre collective ; l'outil doit donner au MJ des moyens et du temps pour la viser.

## Problème, public et mesure du succès

Tenir une campagne pendant des années exige d'imaginer, écrire, préparer, installer le VTT, retrouver des informations, prendre des notes, entretenir la cohérence et réagir à l'imprévu. Cette charge peut épuiser un MJ expérimenté et lui retirer le plaisir d'imaginer et de jouer avec ses amis.

Le premier utilisateur est le MJ à l'origine de cette vision. Le public visé ensuite est un MJ **non nécessairement technique** qui utilise Foundry et Discord. Pathfinder 2e et Golarion sont le premier terrain concret ; l'espace de campagne fonctionne aussi sans Foundry. L'ouverture à d'autres systèmes, VTT ou modes de jeu est une possibilité ultérieure, pas une condition imposée à cette vision.

Le résultat recherché à long terme est que le MJ garde l'envie de préparer et de jouer durablement. Une campagne et chaque séance représentent un engagement humain important ; le MJ n'essaiera pas l'outil sur une vraie séance avant qu'il soit suffisamment avancé, fiable et utilisable. La valeur devra d'abord être démontrée hors table. Évaluer ensuite, au rythme où le MJ accepte de jouer : temps et fatigue de préparation, confiance dans la continuité, qualité du matériel, temps de correction et plaisir du MJ.

## Principes de collaboration

1. **Le MJ dirige à toute échelle.** Il peut définir un thème, un arc, les objectifs d'une séance ou la place d'un objet dans une pièce. Il peut intervenir pendant le travail, commenter un élément, demander une autre direction ou déléguer largement lorsqu'il manque d'énergie. L'assistant propose des idées et coécrit avec lui, notamment les moments forts ; il peut aussi produire seul les détails qu'on lui délègue.
2. **Le jeu fait foi.** Les événements réellement joués deviennent vrais pour cette campagne. Un livre ou un AP reste une source et une inspiration. Le MJ indique ce qu'il veut préserver d'un AP ; les décisions prises à la table peuvent le transformer.
3. **Les états restent lisibles.** Source officielle, observation de séance, chronologie provisoire, fait établi, décision du MJ, préparation retenue, proposition non retenue et incertitude doivent pouvoir être distingués. Une invention n'est pas présentée comme un souvenir ni comme du lore officiel. Les conflits significatifs remontent au MJ avec leurs sources ; les questions doivent rester ponctuelles.
4. **Le contrôle passe par la direction et la revue.** Le MJ ne veut pas approuver chaque détail généré. Il doit pouvoir comprendre et corriger facilement les changements qui comptent, sans lire des diffs Git de JSON ou de Markdown. Une action qui devient visible par les joueurs attend un geste simple du MJ.
5. **La langue du MJ gouverne la production.** Le MJ choisit la langue de la campagne. Tous les contenus produits pour la campagne et destinés à être lus ou utilisés par le MJ ou les joueurs sont rédigés dans cette langue : intrigue, dossier, préparation, résumés, bulles en direct, PNJ, scènes et publications. Les sources peuvent être dans d'autres langues ; leurs titres, pages et extraits vérifiables gardent une référence fidèle à l'original. Les noms propres et termes de jeu suivent les préférences du MJ.
6. **L'aide reste praticable.** Le dossier et le matériel déjà préparé sont consultables et jouables lorsque la transcription, un modèle ou Internet sont indisponibles. L'outil annonce ce qui est prêt, provisoire ou incomplet.

## Parcours de la campagne

### Démarrer depuis n'importe quel état

Le MJ peut commencer avec une page blanche, un premier brouillon, un Adventure Path tel que *Kingmaker*, ou une campagne déjà en cours. L'assistant aide à découvrir une direction par conversation, à comparer des idées réellement différentes et à transformer des notes ou sources existantes en campagne exploitable. Il peut également soutenir une campagne publiée dont les joueurs ont déjà dévié du texte.

**Importer un AP signifie traiter l'ouvrage entier**, pas seulement créer une bibliothèque de recherche. À partir des PDF possédés par le MJ, l'outil produit un dossier structuré pour tous les chapitres : intrigue, scènes, personnages, lieux, secrets, embranchements et liens entre éléments. Chaque chapitre doit être assez complet pour mener ses scènes depuis le dossier ; les liens vers le PDF permettent de vérifier le texte d'origine et les règles exactes. Le PDF est la source de référence initiale. Le MJ peut ensuite discuter de changements, améliorer le contenu et laisser la campagne diverger selon la partie. Le dossier indique les chapitres incomplets.

Un import long affiche sa progression, conserve les parties déjà réalisées avec un statut provisoire et reprend sans recommencer lorsqu'un abonnement ou un service atteint sa limite. Il n'est déclaré complet qu'après vérification de la couverture de tous les chapitres et de leurs liens. La production des scènes Foundry suit normalement le rythme du jeu ; le MJ peut demander une préparation complète à l'avance.

### Concevoir et entretenir la campagne

L'espace de campagne est un lieu de travail dédié, utilisable sans Foundry. La conversation sert à discuter et diriger ; des vues éditoriales servent à voir le résultat. Le MJ peut annoter un personnage, un lieu, une scène ou un passage comme dans une revue de document, demander une correction locale et revenir au chat pour une direction générale. Le ton et le style éditorial peuvent évoluer au fil d'une longue campagne ; l'assistant apprend des consignes, des exemples et des corrections du MJ.

Le dossier recherché a la lisibilité et l'utilité d'un AP, avec la mémoire vivante de cette table. Il comprend au minimum :

- prémisse, thèmes, direction actuelle et choix éditoriaux du MJ ;
- état du monde, lieux, factions, personnages, relations et motivations ;
- secrets, connaissances des personnages joueurs, fils narratifs ouverts et promesses en attente ;
- historique des événements joués, décisions, changements et références qui les étayent ;
- situation présente, conséquences durables des choix des joueurs, possibilités pour les prochaines séances et « what next » ;
- scènes, rencontres, cartes, aides de jeu et autres éléments directement utilisables.

Il doit être possible de retrouver, après trois ans de jeu, qui a fait quoi et pourquoi la situation actuelle existe. Le MJ peut aussi retrouver les pistes abandonnées sans les confondre avec ce qui est établi. Quand deux sources se contredisent, l'outil montre le désaccord et demande un arbitrage ciblé si celui-ci change la suite du travail. Les PNJ gardent des intentions cohérentes ; les décisions des joueurs changent durablement relations, ressources et situations futures et ouvrent d'autres scènes possibles.

### Préparer une séance

Le MJ peut explorer longtemps une intrigue avec l'assistant, coécrire les moments forts ou simplement déléguer une préparation. Le résultat comprend des situations jouables qui réagissent à plusieurs choix plausibles des joueurs, des PNJ incarnables, les éléments PF2e utiles, les références et le matériel VTT requis. Une vue « séance dans une heure » donne immédiatement l'état actuel, le rappel de la dernière séance, les personnes et enjeux importants, les scènes probables, les informations à révéler, les bifurcations possibles et ce qui manque encore.

La production visuelle peut commencer par des schémas pendant la discussion. Une fois la direction retenue, l'objectif est une carte d'une qualité comparable aux cartes professionnelles citées par le MJ (Paizo, Tom Cartos, Forgotten Adventures, Dread Maps), puis une scène Foundry prête à jouer : murs, éclairage, sons, tokens, objets, événements, pièges et autres éléments pertinents. Le MJ peut imposer une carte, fournir ses assets, demander une recherche, une adaptation ou une génération. « Prête » signifie que le MJ peut ouvrir et mener la scène après inspection. Tout élément manquant ou médiocre reste visible avec une solution proposée ; l'outil ne cache pas le travail restant derrière cette étiquette.

### Jouer et rebondir

Un bot Discord rejoint la séance au début et la quitte à la fin ; il capte aussi les échanges hors jeu. Il reçoit une piste par utilisateur Discord et doit pouvoir distinguer plusieurs personnes sur une piste lorsqu'elles partagent un micro. Quand l'attribution change le sens d'un fait et reste incertaine, il affiche « locuteur incertain » plutôt que de deviner. Ce cas peut être testé avec un enregistrement mixte fabriqué, sans attendre qu'il se produise à la table du MJ.

La transcription alimente une aide contextuelle privée au MJ, affichable dans Foundry ou une autre surface adaptée. Elle ressemble à une petite bulle avec **une suggestion principale courte**, dont la couleur ou le niveau visuel reflète l'importance. Elle peut proposer une règle lorsqu'une discussion révèle une confusion, rappeler un fait pertinent, suggérer une réplique ou un conseil d'interprétation quand le MJ décrit un PNJ, ou montrer une conséquence possible des choix des joueurs. La suggestion expire avec la scène ou le contexte qui la justifie. Sa source reste accessible ; le MJ peut l'écarter, la garder ou demander plus. Si le contexte est incertain, la bulle présente une piste à vérifier. Le MJ peut aussi interroger l'assistant directement.

Quand les joueurs déjouent la préparation, l'ambition est de permettre au MJ de continuer sans rupture visible : improviser un PNJ ou une parade scénaristique, trouver des options crédibles, voire préparer rapidement une carte ou une scène. L'assistant peut travailler en arrière-plan. Le MJ déclenche d'un geste simple ce qui devient visible pour les joueurs, par exemple en glissant une règle, un sort ou une action issue d'un compendium dans le chat. La mise à jour durable du dossier de campagne peut attendre le retour de séance.

### Revenir de séance et continuer

La transcription sert à produire une **chronologie provisoire immédiatement consultable**, les éléments de campagne touchés, les conséquences possibles et les décisions qui appellent réellement le MJ. L'agent distingue les événements en jeu des échanges hors jeu ; il retient les décisions de campagne, intentions de jeu et questions utiles, sans transformer le bavardage en mémoire de campagne. Le transcript intégral reste consultable pendant une durée choisie par le MJ. L'audio brut n'a pas vocation à être conservé après le traitement nécessaire.

Une revue groupée met en avant les passages ambigus et les faits lourds de conséquences avant leur intégration durable au dossier. Elle permet de corriger, accepter, écarter, commenter et demander une autre proposition sans valider chaque ligne. Les corrections se propagent aux connaissances des personnages, relations, préparations et autres éléments internes qui en dépendent. Une correction tardive signale séparément les publications déjà vues par les joueurs. Le MJ peut corriger rapidement une attribution incertaine ou une erreur factuelle sans refaire inutilement tout le travail.

La [revue de séance d'ArchivistAI](https://www.myarchivist.ai/documentation) est une référence de parcours : chronologie éditable, entités proposées, correction avant intégration. Son [tri annoncé des échanges hors jeu](https://www.myarchivist.ai/faq) inspire un cas à mesurer, sans présumer de sa fiabilité ni de celle de notre outil.

Le MJ peut publier aux joueurs une sélection sans secrets : journal de campagne, informations découvertes ou, par exemple, un journal de ville racontant leurs exploits. Pour progresser dans son jeu, le MJ peut demander une répétition avant séance, un conseil discret en direct ou un retour après séance. Un joueur peut demander après séance un retour privé centré sur ses propres objectifs de jeu, sans note de « performance ».

## Bibliothèque PF2e, sources et provenance

Le MJ possède une collection complète de PDF PF2e. Il veut pouvoir l'indexer et y rechercher des règles, du lore de Golarion, des idées et des scénarios ou campagnes complets. Une réponse fondée sur un livre indique le titre et la page ; elle distingue le passage retrouvé, l'interprétation, la traduction et l'invention. Les réponses servent aussi au design des séances et des rencontres, même si Foundry automatise déjà une partie des règles. Les PDF d'un AP peuvent servir de base à une campagne qui diverge ensuite selon la table.

Les PDF et transcriptions peuvent être traités par des services externes si le MJ le choisit ; une option locale reste souhaitée, notamment pour maîtriser le coût. Les PDF du MJ, les transcriptions et les campagnes privées ne sont pas des ressources à distribuer avec le logiciel. Le MJ et les joueurs savent qu'une séance est enregistrée lorsqu'un bot Discord rejoint le canal ; l'expérience doit rendre cette information et les choix de traitement clairs.

## Interfaces et responsabilités envisagées

L'expérience peut se répartir entre :

| Partie | Rôle voulu |
| --- | --- |
| Espace de campagne | Créer, discuter, rechercher, préparer, relire, commenter, corriger et consulter sans Foundry. |
| Module Foundry | Observer le contexte de jeu, créer et synchroniser les éléments jouables, afficher l'aide au MJ et exécuter les actions que le MJ déclenche. |
| Bot Discord | Capturer la séance, fournir la transcription et éventuellement des commandes ou publications pour les joueurs. |
| Agents et traitements | Rechercher, écrire, transcrire, générer ou adapter des assets, préparer le matériel et consolider la campagne. |

Ce découpage est une hypothèse de produit, pas une architecture acceptée. La synchronisation doit éviter les doublons et préserver les retouches du MJ dans Foundry. L'espace privé du MJ contient secrets, sources, propositions et conseils ; les joueurs ne voient que ce que le MJ choisit de leur publier.

### Organisation des dépôts à décider

**Hypothèse à évaluer : trois dépôts de code**, tout en gardant ce document de vision indépendant. Les frontières fonctionnelles envisagées sont :

| Dépôt provisoire | Contenu et raison de la séparation |
| --- | --- |
| Application de campagne | Espace de campagne, dossier, bibliothèque PF2e, agents, traitement des séances et interface de revue. Elle possède la mémoire durable, les règles de visibilité et les contrats d'échange. |
| Module Foundry | Extension installable dans Foundry, interface en séance, observations et production du matériel VTT. Foundry impose son propre paquet, sa compatibilité et son cycle de publication. |
| Bot Discord | Capture et transcription des séances, commandes et publications éventuelles pour les joueurs. Il a ses propres permissions Discord, secrets, disponibilité continue et cycle d'installation. Il transmet des observations à l'application de campagne sans détenir une deuxième mémoire canonique. |

Ces trois parties peuvent vivre dans un, deux ou trois dépôts. Décider après un premier parcours intégré, en comparant : installation pour un MJ non technique, fréquence des changements traversant plusieurs parties, besoin de publier séparément le module Foundry et le bot, gestion des secrets, tests de compatibilité et coût de coordination. Un dépôt séparé doit simplifier une frontière réelle, pas seulement refléter un schéma d'architecture.

Quelle que soit la répartition, l'application de campagne possède la mémoire durable et définit un contrat d'échange versionné avec des exemples. Foundry et Discord consomment ce contrat. Une démonstration intégrée réunit les composants sur une instance Foundry et un environnement Discord de test. Un dépôt supplémentaire « contrats communs » exige lui aussi une justification concrète.

Cette proposition suit les frontières de livraison, pas une obligation de distribuer le travail en équipes ou de publier tous les composants dès le début. Les noms, licences du nouveau code et technologies restent à choisir.

## Coût et moyens candidats

Le MJ paie déjà environ 20 € par mois pour Claude et 20 € pour Codex, et héberge Foundry sur un serveur avec une GTX 1080 ; une GTX 1070 est disponible mais non alimentée. Son PC de jeu possède une RX 9070 XT. Il souhaite éviter une dépense récurrente beaucoup plus élevée et pourrait accepter environ **1–2 € d'API par séance**, avec des options locales lorsque le matériel le permet. Une latence de **1–2 secondes** pour certaines suggestions en direct est acceptable ; le type d'aide affichée doit dépendre de la latence réelle.

Codex et Claude Code/Cowork sont des candidats pour le travail long avant et après séance, **y compris l'import initial complet d'un AP au moyen des abonnements du MJ**. Leur accès, leurs limites d'usage et la reprise après interruption doivent être vérifiés dans l'intégration réelle. L'import initial ne suppose pas l'achat d'appels API. WhisperX est un candidat pour la transcription consolidée. La transcription locale en flux, les modèles vocaux locaux, les API temps réel, Dungeondraft, des banques d'assets, ComfyUI, Midjourney, GPT Image, Nano Banana et la recherche de ressources en ligne sont des pistes **à comparer et mesurer**, pas des dépendances choisies. La qualité visuelle, les droits d'usage, la compatibilité Foundry, le temps de traitement, le coût réel et la facilité d'installation pour un MJ non technique doivent départager ces pistes.

### Économie des crédits et des tokens pendant l'usage

La maîtrise du coût concerne **l'utilisation quotidienne du produit**, distincte du coût de son développement. L'outil doit suivre le coût par campagne, séance, tâche et fournisseur, afficher une estimation avant une opération lourde et permettre au MJ de fixer une limite. Le prix final comprend les appels aux modèles, la transcription, les images, le stockage et les éventuels services externes ; il ne doit pas être masqué par un abonnement déjà payé.

L'architecture à évaluer doit économiser les appels sans dégrader la qualité utile :

- récupérer d'abord les passages pertinents des livres et de la campagne, au lieu d'envoyer toute la bibliothèque ou tout l'historique dans chaque prompt ;
- conserver des résumés structurés, des références et des résultats réutilisables ; invalider ce cache lorsque les faits, sources ou consignes changent ;
- traiter les changements depuis la dernière séance plutôt que régénérer tout le dossier à chaque retour ;
- réserver les modèles et raisonnements coûteux aux décisions créatives ou recherches difficiles ; utiliser des traitements locaux, simples ou moins chers pour transcription, classement et tâches répétitives quand leur qualité suffit ;
- regrouper les travaux qui peuvent attendre, éviter les appels continus en séance lorsqu'aucun contexte pertinent ne change et borner la taille des réponses affichées en direct ;
- proposer au MJ des profils de coût et de qualité, tout en signalant les tâches qu'un profil bon marché accomplirait mal ;
- mesurer coût, latence et qualité ensemble sur les scénarios représentatifs avant de retenir un fournisseur ou un modèle.

Ces mécanismes sont des exigences de résultat et des pistes de conception ; ils ne fixent pas encore le fournisseur, le format de cache ou la politique de routage. Le plafond indicatif de 1–2 € d'API par séance doit être vérifié sur un usage complet, y compris les reprises et les erreurs. Le plafond par séance est **dur** : lorsqu'il est atteint, l'aide en direct utilise les ressources locales et le matériel déjà préparé ; les travaux différables attendent que le MJ relève le plafond ou choisisse une autre option.

## Validation avant toute séance réelle

LoreForge et SecondChair sont des **ressources existantes à inventorier**, au même titre que les outils, modules, bibliothèques et exemples disponibles sur Internet. Examiner leurs fonctions, tests, données fictives, limites et éléments réutilisables sans importer automatiquement leurs choix. Les ressources de la communauté PF2e/Foundry et les AP que le MJ possède peuvent aider à définir un niveau de qualité et des cas d'essai, dans le respect de leurs droits d'usage.

Construire un banc d'essai hors table avec une campagne fictive et **Kingmaker, AP que le MJ possède en PDF**. Tester la structure et les références sur l'AP entier. Simuler des séances et des décisions de joueurs qui suivent puis dévient de l'AP : des scénarios fixes détectent les régressions, des joueurs simulés plus libres éprouvent l'improvisation. Leurs actions sont des données de test et ne deviennent jamais des faits de la future campagne du MJ. Le banc couvre plusieurs mois ou années de continuité : notes contradictoires, transcription imparfaite, bifurcations, préparation urgente, scènes Foundry et panne d'un service. Rejouer les mêmes cas après chaque changement pour voir les régressions. Les PDF de l'AP et leurs extraits restent dans l'environnement privé de test, hors des dépôts publics et des résultats publiés.

Tester le module sur une **véritable instance Foundry locale**, avec un monde de test séparé de la campagne du MJ : installation, création et retouche de scènes, murs, lumières, sons, acteurs, objets, événements, visibilité joueur et resynchronisation. Choisir plusieurs situations différentes de Kingmaker, notamment exploration, dialogue et combat. Le [module officiel Kingmaker de Paizo](https://foundryvtt.com/packages/pf2e-kingmaker), que le MJ ne possède pas, fournit une référence publique pour la couverture et la finition ; le test ne suppose ni son achat ni la reproduction de ses assets exclusifs. La [FAQ officielle de Foundry](https://foundryvtt.com/article/faq/) permet une instance privée de développement avec la même licence si une seule instance est accessible aux autres utilisateurs. Protéger la clé de licence et garder l'instance de test inaccessible aux joueurs. Compléter par une revue humaine des textes, des cartes et de l'UX. Des tests techniques seuls ne prouvent pas la qualité narrative ou la facilité d'emploi.

Avant de demander au MJ d'engager une vraie campagne ou une vraie séance, lui faire parcourir **la même campagne Kingmaker de bout en bout** : AP importé en entier, sources retrouvables, changements décidés par le MJ, séances simulées avec bifurcations, plusieurs scènes Foundry inspectables, aide live simulée, retour de séance corrigeable, continuité préservée, coûts et travail restant visibles. Une revue et des choix créatifs sont normaux ; la reconstruction du dossier et la mise en place répétitive dans Foundry doivent déjà être prises en charge. Le MJ décide ensuite si le produit est assez mûr pour une séance réelle. Sa valeur durable se jugera avec l'usage, lorsque ce moment viendra.

## Scénarios de réussite à démontrer

1. **Campagne longue.** Le MJ demande qui a fait une promesse deux ans plus tôt. L'outil retrouve le fait, son contexte et sa source, dans la langue de la campagne, et signale honnêtement toute incertitude.
2. **AP transformé.** Le MJ charge tous les PDF de Kingmaker, retrouve chaque chapitre et ses liens, puis précise ce qu'il veut préserver. Une limite d'abonnement interrompt le traitement ; il reprend sans perte. Les joueurs simulés prennent ensuite une voie inattendue. L'outil distingue le texte publié de l'histoire de cette table et propose une suite cohérente.
3. **Séance dans une heure.** Après une semaine sans préparation, le MJ obtient une fiche utilisable, sait ce qui est prêt dans Foundry et ce qui manque, puis joue sans devoir reconstruire le résultat.
4. **Improvisation en direct.** Une question de règle ou un PNJ imprévu surgit. La bulle privée fournit une aide courte et pertinente ; une action Foundry visible par les joueurs n'a lieu qu'après le geste du MJ.
5. **Retour de séance.** Les événements en jeu sont distingués des échanges hors jeu et reliés aux éléments de campagne. Le MJ corrige rapidement une mauvaise attribution et une suggestion infondée ; ces corrections restent effectives dans la préparation suivante. Un enregistrement mixte vérifie le cas de deux voix sur une piste.
6. **Scène produite.** Le MJ choisit ou fait produire une carte ; la scène Foundry comprend les éléments attendus et reste inspectable et retouchable avant le jeu.
7. **Panne et plafond.** Pendant une séance sans modèle, sans Internet ou après atteinte du plafond payant, le MJ conserve l'accès au dossier et au matériel déjà préparé ; l'aide locale disponible reste utilisable.

## Cadre pour une implémentation autonome

Ce document donne la **destination complète**, sans prétendre qu'un seul travail nocturne puisse atteindre une qualité éditoriale professionnelle et intégrer tous les services. Un agent chargé d'implémenter doit transformer chaque scénario ci-dessus en résultat observable dans un environnement de test, mesurer ce qui fonctionne et rapporter explicitement ce qui manque. Une interface simulée, une carte seulement illustrative ou un résumé sans provenance ne constituent pas l'implémentation complète de cette vision.

Le nouvel outil doit prendre ses propres décisions sur la source de vérité, les états et l'autorité de la campagne, les frontières entre composants, les permissions, la visibilité joueur, le traitement des sources et les échanges avec Foundry. LoreForge et SecondChair peuvent être étudiés ou réutilisés sélectivement ; leurs documents restent propres à leurs projets. Le développement peut avancer sans attendre une vraie séance, grâce aux cas fictifs, aux simulations et aux démonstrations intégrées décrits plus haut.

### Points encore à trancher ou vérifier

- Modèle exact de relations, d'états, de provenance et de résolution des contradictions ; quelles idées de SecondChair reprendre.
- UX précise des commentaires, de la revue, de l'historique et de la synchronisation Foundry.
- Qualité réalisable des cartes générées ou assemblées, pipeline Dungeondraft éventuel et disponibilité des assets.
- Coût, latence et qualité de la capture Discord, de l'identification des voix et de l'assistance locale sur le matériel cité.
- Politique de routage des modèles, budgets, cache et mesures de coût pour l'usage réel du produit.
- Installation, mises à jour, sauvegarde et restauration simples pour un MJ non technique.
- Traitement des PDF complexes, éditions et langues, ainsi que des droits des assets et des contenus publiés aux joueurs.
- Forme et conditions d'usage des conseils destinés aux joueurs.

Ces points appellent des prototypes et des décisions explicites. Ils ne retirent aucune capacité à la destination décrite ici.
