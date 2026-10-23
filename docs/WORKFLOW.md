# Exécution autonome

## Continuer la roadmap

1. Lire `docs/STATE.md`, l'entrée du premier jalon prêt dans `docs/ROADMAP.md` et les principes pertinents. `make resume` donne la santé locale. Regarder `git status` avant toute modification. Ne pas reprendre une tâche déjà achevée sur la foi d'un ancien message.
2. Choisir le plus petit parcours qui démontre une capacité du jalon. Écrire un plan interne proportionné. Rechercher la documentation officielle ou faire un essai court lorsqu'un risque technique est réel. Ne pas soumettre ce plan à validation ordinaire.
3. Travailler dans une branche ou un worktree si les changements se chevauchent ; garder les changements petits et intégrables. Une seule source canonique dans l'application. Les adaptateurs utilisent des contrats versionnés avec fixtures. Les données privées restent hors Git.
4. Lancer `make check`, puis démarrer et parcourir réellement l'application ; capturer une preuve visuelle si le résultat est visuel. Pour une capacité critique, faire examiner les cas adverses par un agent indépendant si disponible, ou refaire une passe QA séparée depuis `docs/QA.md`. Corriger puis rejouer les contrôles touchés.
5. Mettre à jour les quatre états I/T/D/P du jalon, ses limites et `docs/STATE.md`. Une preuve indique commande, environnement et observation. Ne jamais annoncer une intégration externe après un simple test de fixture.
6. Intégrer rapidement un changement réversible en développement après contrôles et dans les permissions Git accordées ; pas de revue humaine PR systématique. Le propriétaire voit d'abord l'application ou la preview, puis le parcours reproductible, les preuves et les décisions produit. Continuer un autre résultat seulement si la vérification précédente est satisfaisante.

**Blocage :** reproduire et diagnostiquer, tenter une solution, réduire le périmètre de manière réversible, essayer une alternative, puis escalader seulement si l'accès matériel, les données privées, le coût, la production ou une décision de vision l'exigent. Un test rouge est du travail pour l'agent. L'escalade tient en problème, impact, options, recommandation et décision nécessaire.

**Interruption :** conserver dans `docs/STATE.md` le jalon, la dernière preuve, les fichiers touchés, la prochaine commande et l'incertitude. Les sorties temporaires et PDF restent hors dépôt. À la reprise, vérifier l'état réel et les marqueurs de traitement avant de réexécuter une opération longue. Les travaux futurs d'import auront identifiants idempotents et curseurs ; la reprise d'une conversation CLI ne suffit pas.

## Feedback produit

Observer la page ou le parcours cité avec une fixture représentative. Reformuler en interne le résultat utilisateur, comparer aux invariants, modifier directement ce qui est réversible, vérifier les parcours adjacents et montrer la nouvelle expérience. Modifier roadmap seulement si priorité ou résultat change ; documenter une décision durable seulement si elle évite un futur contresens. Une préférence créative qui change la vision ou une publication irréversible revient au propriétaire.

## Capacités réellement disponibles au bootstrap

- `codex exec` et `codex exec resume`, `claude -p` et `claude --resume` existent dans les CLI installées ; Codex et Claude proposent des worktrees et des mécanismes de sessions/sous-agents. Les capacités ont été vérifiées via `--help`, pas par une exécution autonome nocturne. Voir [Codex CLI](https://learn.chatgpt.com/docs/developer-commands?surface=cli) et [Claude Code CLI](https://code.claude.com/docs/en/cli-reference).
- Git est local sans commit ni remote initial ; `gh auth status` signale un jeton invalide. Le fichier GitHub Actions existe, mais aucune CI distante n'a tourné. GitHub n'est donc pas un prérequis pour continuer.
- Test HTTP local et navigateur sont deux preuves distinctes. Le test HTTP couvre les formulaires ; la disponibilité du navigateur automatisé dépend de l'environnement de la session. Ne pas inventer une inspection si elle n'a pas eu lieu.
- Aucun daemon permanent, scheduler ou budget d'API de développement n'est présumé. Pour automatiser sans supervision, installer et mesurer d'abord l'exécuteur choisi ; les documents du dépôt demeurent l'état durable.
