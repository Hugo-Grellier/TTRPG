# Roadmap by observable user outcomes

**Evidence key:** `I` = implemented, `T` = automated tests passed, `D` = demonstrated in the relevant real environment, `P` = owner judged the quality satisfactory. A fixture `T` never counts as `D` for Foundry, Discord, or a complete AP. “Demonstrated” requires the stated journey and published limitations.

## Now

### M0 — Local foundation and basic provenance

- **User outcome:** the GM creates a fictional campaign, links an observation to a source, decides a fact, and finds it with provenance.
- **Demonstration:** `make demo`; search for “promised” in the fixture, then create another campaign, source, observation, and decision; search for the fact after reloading.
- **Success criteria:** SQLite persistence; observation remains noncanonical until a decision; source and decision appear with the result; cross-campaign references and player visibility are rejected.
- **Dependencies/risks:** local Python; no verified documentary source or user identity.
- **Status:** I yes; T yes (unit and HTTP journey); D local HTTP and desktop/mobile Chrome screenshots yes; P not requested.
- **Known limitations:** manual entry, GM-only view, no correction, PDF, or VTT.

### M1 — An offline campaign loop

- **User outcome:** start from a fictional source, revise a campaign proposal, prepare a situation, play a simulated branch, consolidate it, and find why the state changed.
- **Demonstration:** fixed “Mira's ford” scenario: the GM corrects a proposal, opens a prep sheet, chooses a simulated player action, rules on the outcome, then searches for the promise and its consequences with provenance.
- **Success criteria:** proposals are noncanonical; preparation and simulation are labeled; fact correction identifies dependent elements; no secret enters publishable content; the journey remains readable after restart. Regression tests and browser inspection.
- **Dependencies/risks:** proposal model, corrections, and dependency links; keep editing simple. Begin with one fictional scenario and explicit choices, without AI generation.
- **Status:** I yes; T yes (`make check`, five tests on Python 3.14.4, including HTTP form journey, correction, privacy and campaign ownership); D yes (local Chrome 155 browser form journey against a fresh SQLite database on October 23, 2026, plus desktop and mobile visual inspection); P not requested.
- **Known limitations:** manually authored preparation and simulation; one-hop consequence search; correction flags dependent prep sheets for GM review without rewriting them; no player publication route, real session, or PDF.
- **Delivered units:** proposal revisions, fact correction and dependent-prep warning, prep linked to canon, simulated event and explicit GM consolidation, linked consequence search, browser journey and adversarial QA.

### M1.5 — Conversation-first campaign workspace

- **User outcome:** discuss the campaign with Codex or Claude Code beside the relevant document, comment on an exact passage, and keep a suggested revision separate from canon until the GM acts.
- **Demonstration:** open the fictional Mira prep in a three-pane workspace, select a passage, leave a comment, ask Codex to address it, continue the same conversation, switch to Claude Code, and review a proposed document change. A terminal is optional.
- **Success criteria:** actual CLI sessions and resume, campaign language and selected-document context, comments anchored to private documents, workflows/skills discoverable from chat, proposed edits reviewable before acceptance, no direct agent write to durable campaign memory, and usable layout at desktop and mobile widths.
- **Dependencies/risks:** installed and authenticated CLIs, subscription limits, and a clear review model for document revisions.
- **Status:** I partial (IDE-like shell, line comments on campaign and product docs, editable playbook prompts, writable CLI chat in isolated draft worktrees, and visible Git diff); T partial (HTTP and domain checks); D partial (local Chrome line-comment journey, real writable Codex edit, previous two-turn Codex conversation and Claude Code reply); P no. Next ready unit: make skills discoverable and add an explicit GM action to accept reviewed draft changes.
- **Known limitations:** CLI replies are synchronous; no streaming, terminal input, draft acceptance action, or player publication. The bottom strip shows CLI state only.

## Later

### M2 — Editorial dossier and long memory

- **User outcome:** find people, places, promises, contradictions, and “what next” after a long fictional history.
- **Demonstration:** replay several simulated years, correct a late attribution, and inspect consequences without confusing a hypothesis with a fact.
- **Success criteria:** evidence-backed queries, focused conflicts, read permissions, corrections propagated to relevant preparations and publications.
- **Dependencies/risks:** M1; relationship UX and correction history.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** narrative quality requires human review.

### M3 — Library and resumable complete AP

- **User outcome:** search owned PDFs with title/page and browse every chapter of an owned AP, with coverage and gaps visible.
- **Demonstration:** early prototype on complex fictional/public PDFs with interruption/resume; later, all of Kingmaker in a private environment, verifying each chapter before claiming completion.
- **Success criteria:** checkable citations, idempotent jobs, progress and coverage, AP/campaign/proposal separation, no duplicate work on resume.
- **Dependencies/risks:** M2 for turning an AP into a dossier; PDF extraction, rights, editions, and processing cost. Start an extraction prototype alongside M1/M2.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** a fictional trial does not validate Kingmaker; its PDFs remain private.

### M4 — Playable preparation and asset quality

- **User outcome:** get a “session in an hour” view with situations, NPCs, branches, and the exact state of the materials.
- **Demonstration:** a fictional week without preparation, then review the prep sheet and ready/missing items; compare a map prototype with professional references for readability and editing time.
- **Success criteria:** offline-usable sheet, references and uncertainty, plausible alternatives, editorial quality shown to the owner.
- **Dependencies/risks:** M1 and M2 memory; creative quality, asset rights, production cost. Prototype maps early, before choosing a pipeline.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** a technically valid map may still be poor to play on.

### M5 — Editable Foundry scene

- **User outcome:** synchronize an inspectable PF2e scene without erasing GM edits in Foundry.
- **Demonstration:** isolated Foundry v14 test instance, exploration then dialogue/combat scene, manual edit, resynchronization, and conflict preview.
- **Success criteria:** expected walls/lights/objects verified; no duplication; edits preserved; player visibility tested; visual quality reviewed separately.
- **Dependencies/risks:** M4; license/test instance, Foundry API, assets. Prototype synchronization early with one fictional scene.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** no Foundry compatibility has been proven yet.

### M6 — Session review and controlled live assistance

- **User outcome:** read a provisional timeline, correct speakers and out-of-game talk, receive short private help, then publish only what the GM chooses.
- **Demonstration:** manufactured mixed audio, speaker disagreement, model outage, expired suggestion, publication after GM action, and a reached session budget.
- **Success criteria:** ambiguous transcription flagged, no automatic promotion to canon, secrets protected, latency and cost measured, prepared material available during outages.
- **Dependencies/risks:** M2/M4/M5; Discord, consent, shared microphones, 1–2 s latency, and hard spending cap. Prototype audio cost/latency early, before a full bot.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** manufactured recordings do not predict quality in a real session.

### M7 — Installation, backup, and complete offline Kingmaker campaign

- **User outcome:** install, restore, and traverse the same transformed AP campaign end to end before any real session.
- **Demonstration:** restore on a test machine; entire AP, simulated branches, several Foundry scenes, simulated live help, corrections, and visible cost.
- **Success criteria:** verified AP coverage, tested restore, inspectable integrated journey, and owner decision about real use.
- **Dependencies/risks:** M3–M6; nontechnical packaging, overall quality, and private data.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** durable value can only be measured in GM-approved real use.
