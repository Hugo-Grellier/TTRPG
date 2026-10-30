# Agent entry point

`VISION.md` defines the product destination. Change it only for an explicit product decision or faithful translation requested by the owner. For a task, read only the relevant branch: `docs/PRODUCT_PRINCIPLES.md` for authority and privacy, `docs/ARCHITECTURE.md` for boundaries, `docs/ROADMAP.md` for what comes next, `docs/WORKFLOW.md` for execution, and `docs/STATE.md` for resuming work.

**“Continue the roadmap”**: read `docs/STATE.md` and the first ready milestone in `docs/ROADMAP.md`, run `make resume`, build the user journey, inspect the running application, seek independent review if available, and update the evidence and state. Continue without routine technical approval. Show the owner a usable journey and its limitations.

**Product feedback**: inspect the affected journey, infer the intended outcome, make reversible improvements directly, rerun affected journeys, update the roadmap or principles only when the direction changes, and show the resulting experience.

The current server is local and GM-only. Any player publication requires an explicit GM action and a tested player-read boundary. Sources, observations, and proposals never become canonical on their own. Integrations do not write directly to durable campaign memory. Keep private and licensed data out of Git.

Escalate only for a substantial change to the product vision, unauthorized spending, private data, production resources, significant legal or security risk, or indispensable hardware access. Agents own ordinary plans, tests, technical choices, and reversible changes.

## Engineering discipline

Loop on every task: gather context, act, verify, repeat. Read `docs/GOTCHAS.md` before starting work; after any owner correction, add the pattern there as a rule.

**Plans.** When the owner asks for a plan, deliver only the plan until they say go. Follow an owner-written plan exactly; if you find a real problem, flag it and wait. For a vague request outside the roadmap, outline what you would build and where, and get approval first. "Yes", "do it", "push": execute without restating the plan. Roadmap continuation keeps its autonomy above.

**Refactors.** Before restructuring a file over 300 lines, first remove its dead code, unused imports and debug output, committed separately. Run multi-file refactors in phases of at most 5 files, verifying each phase before the next; outside roadmap work, wait for the owner's go between phases. Afterwards delete whatever became unused. When renaming, grep separately for calls, imports, string literals, templates, `workspace.js`/CSS references, and tests.

**Quality.** Fix the structural flaw instead of patching the symptom: duplicated state, inconsistent patterns, wrong ownership. One source of truth; fix display bugs at the source, never by copying state. Build only what is asked or clearly needed now. Write code like the surrounding code, with plain names and sparse comments. Study any code the owner points to and match its patterns. Work from pasted errors and logs; when a bug report has none, ask for the raw output.

**Verification.** Nothing is done until `make check` passes and the affected journey has been run in the application (see `docs/WORKFLOW.md`). State plainly what was not verified. After fixing a bug, say why it happened and what would prevent that class of bug. When reviewing your own work, give the perfectionist's and the pragmatist's view and let the owner choose.

**Recovery.** After two failed attempts at a fix, stop, reread the whole relevant section, and say where your model was wrong. "Step back" means rethink from scratch and propose something different.

**Context.** Tasks spanning more than 5 independent files go to parallel subagents of 5-8 files each, when the tool provides them; wait for their completion rather than polling. In long sessions, reread a file before editing it. Read large files in chunks, and rerun narrower when results look truncated. Before compacting or stopping, record state in `docs/STATE.md`; scratch outputs stay outside the repository.

**Safety.** Before deleting a file, confirm nothing references it. Never discard uncommitted work you did not create. Push only when told. Offer a checkpoint commit before risky changes, and flag files that grow hard to reason about.
