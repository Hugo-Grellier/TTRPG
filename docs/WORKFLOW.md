# Autonomous execution

## Continue the roadmap

1. Read `docs/STATE.md`, the first ready milestone in `docs/ROADMAP.md`, and relevant principles. `make resume` checks local health. Inspect `git status` before edits. Do not redo work merely because an old message lacks its completion report.
2. Choose the smallest journey that demonstrates a milestone capability. Write a proportionate internal plan. Consult official documentation or run a small experiment when a technical risk warrants it. Routine plans do not wait for approval.
3. Use a branch or worktree when changes overlap; keep changes small and integrable. The application has one canonical source of truth. Adapters use versioned contracts with fixtures. Keep private data out of Git.
4. Run `make check`, then start and actually navigate the application; capture visual evidence for visual outcomes. For critical capabilities, have an independent agent challenge the result when available, or run a separate QA pass from `docs/QA.md`. Fix findings and rerun affected checks.
5. Update the milestone's four I/T/D/P states, limitations, and `docs/STATE.md`. Evidence names the command, environment, and observation. Never claim an external integration based only on a fixture test.
6. Integrate reversible development changes promptly after defined checks and within granted Git permissions; human PR review is not the default gate. Show the owner the application or preview first, then a reproducible journey, evidence, and relevant product decisions. Continue to another outcome only when the previous one is satisfactorily verified.

**Blockers:** reproduce and diagnose, try a fix, narrow scope reversibly, try an alternative, then escalate only when hardware access, private data, spending, production, or a vision decision truly requires it. A failing test is agent work. An escalation states the problem, impact, concrete options, recommendation, and decision needed.

**Interruption:** record the milestone, last evidence, touched files, next command, and uncertainty in `docs/STATE.md`. Temporary outputs and PDFs stay out of the repository. On resumption, inspect real state and processing markers before rerunning long work. Future import jobs need idempotent IDs and cursors; resuming a CLI conversation alone is insufficient.

## Product feedback

Inspect the cited page or journey with a representative fixture. Infer the user outcome, compare it with product invariants, make reversible improvements directly, verify adjacent journeys, and show the new experience. Update the roadmap only if the priority or outcome changes; record a durable decision only when it prevents future misunderstanding. A creative preference that changes the vision or an irreversible publication returns to the owner.

## Language conventions

Repository code, comments, tests, documentation, and default interface copy use English. The product supports campaign language through explicit translation catalogs: English is the default and French is available when chosen for the campaign. Content authored for a campaign follows its language; source titles and locators remain faithful to the original. Add new interface copy to the catalogs and verify both languages rather than embedding translations in templates.

## Capabilities actually available at bootstrap

- `codex exec` and `codex exec resume`, `claude -p` and `claude --resume` exist in the installed CLIs; Codex and Claude offer worktrees and session/subagent mechanisms. These capabilities were checked with `--help`, not a permanent unattended run. See the [Codex CLI](https://learn.chatgpt.com/docs/developer-commands?surface=cli) and [Claude Code CLI](https://code.claude.com/docs/en/cli-reference).
- Git has local bootstrap commits but no remote; `gh auth status` reports an invalid token. A GitHub Actions workflow exists, but no remote CI has run. GitHub is not a prerequisite for continuing.
- Local HTTP tests and browser inspection are separate evidence. The HTTP test covers forms; browser automation availability depends on the session environment. Do not claim an inspection that did not happen.
- No permanent daemon, scheduler, or development API budget is assumed. To automate without supervision, first install and measure the chosen executor; repository documents remain the durable state.
