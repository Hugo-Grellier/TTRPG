# Chosen architecture

## Choices and tradeoffs

A monorepo with a modular application core is the starting point. Python owns the domain, persistence, and long-running processing; a web interface is served locally. TypeScript will be used for the Foundry v14 adapter and, if the interface becomes complex enough to justify it, the frontend. The current slice uses Python's standard library, HTML, and SQLite: immediate setup, no external service, and real persistence. A React frontend or full TypeScript stack would provide a shared language with Foundry and a rich UI ecosystem; today it would add a build, dependencies, and duplicated models around the owner's preferred Python core. Revisit this when editing and review workflows become substantially interactive.

The modular monolith avoids the coordination cost of three repositories, microservices, or a message bus. Separate packages or processes may eventually deliver the Foundry module and Discord bot according to their installation needs. No adapter owns another canonical truth. A graph database has no justification before measured relational-query needs; relational SQLite already supports links and constraints. Full event sourcing complicates projections and corrections; decisions and provenance are explicit in ordinary tables. Add correction history when that journey exists.

## Current boundaries

```text
GM browser -> campaign.web -> campaign.store -> SQLite
                           -> campaign.core (validation)
```

`campaign.core` imports no infrastructure. `campaign.store` owns transactions and checks campaign ownership. `campaign.web` does not decide canon: it passes the GM's decision to the store. The schema is created on first access. `data/` stays out of Git. The server listens only on loopback and has no authentication; remote access will require authentication, authorization, and schema migrations before real use.

Repository code and documentation are in English. The interface renders English by default and French for campaigns whose language is `fr`, using explicit JSON catalogs instead of translated strings in templates. Campaign-authored content follows the chosen campaign language; source titles and locators retain their original wording. Keep new UI copy in both catalogs and test the language selection.

The core keeps `campaign_id` on each element even where an indirect link might suffice, making read queries and ownership checks explicit. Facts are added through a decision linked to an observation and source. Proposal revisions, prep sheets, simulated events, and corrections retain their links; correcting a fact flags prep sheets that cite it. SQL constraints reject missing and cross-campaign references and any visibility other than `gm`; the domain API also rejects cross-campaign references. No player-read path exists yet, so the GM screen does not prove separation of player views.

## Boundaries to open in later milestones

- **Library/import:** keep private PDFs outside the repository; each extracted passage records document, edition, page, method, and quality. A long-running job will have an ID, idempotent work units, a resume cursor, and verified chapter coverage. Search and citation remain separate from establishing canon. No complete AP import is claimed today.
- **Foundry v14/PF2e:** use a versioned exchange contract with fictional examples, stable item ID, and visibility. The TS adapter observes or proposes; the application decides and persists. For synchronization, compare canonical state, the fingerprint of the last export, and current Foundry state; show GM edits, then apply only selected fields. Foundry `flags` and document operations make this prototype plausible, but do not prove preservation of edits. See [module development](https://foundryvtt.com/article/module-development/) and the [Scene v14 API](https://foundryvtt.com/api/classes/foundry.documents.Scene.html).
- **Discord/transcription:** an adapter submits dated observations with speaker and confidence, never facts. Consent, audio retention, and speaker correction precede a live-session trial.
- **Models/CLIs/assets:** jobs consume versioned input and return proposals, references, status, and observed cost. Canonical decisions remain in the core. Claude Code/Codex development subscriptions are neither a product provider nor a guaranteed inference budget. Enforce the product spending cap before each expense, with a reservation and reconciliation against actual cost; at the cap, use local reading and defer jobs.

Initial backup: stop the server and copy the SQLite file. Before real data or evolving schemas, add versioned migrations and a restore test. Copying a fixture is not proof of disaster recovery.
