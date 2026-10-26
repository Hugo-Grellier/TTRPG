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
- **Status:** I partial (IDE-like shell with document-first desktop layout, full-width campaign sheets and optional comments pane, and visual campaign home, separate Campaign/Product navigation, rendered Markdown documents and CLI replies, exact-passage comments and element comments on the visual bible with one-click transfer to chat, local PDF source pages with comments and page context, editable playbooks, installed skill catalog, writable CLI chat in isolated draft worktrees, private Markdown preparation drafts and linked campaign sheets, visible diffs, explicit GM acceptance, and nonblocking local CLI turns); T partial (`make check`, 22 tests); D partial (previous real CLI edit and resume checks; isolated Chrome preparation and conversation journeys; real 31-sheet campaign dossier and exact-link journey on desktop and mobile, October 26, 2026); P no. Next ready unit: make the campaign sheets editable through the supervised agent draft workflow and improve the full IDE journey.
- **Known limitations:** no token streaming, interactive terminal, or player publication. Product document acceptance replaces the chosen file in the main checkout without a commit; preparation revisions are stored privately in SQLite. A conflicted preparation draft needs manual reconciliation. One local CLI turn runs at a time; an interrupted turn is marked failed after six minutes. The bottom strip shows CLI state only. No live CLI was invoked for this unit because the account's paid usage mode is uncertain.

## Later

### M2 — Editorial dossier and long memory

- **User outcome:** find people, places, promises, contradictions, and “what next” after a long fictional history.
- **Demonstration:** replay several simulated years, correct a late attribution, and inspect consequences without confusing a hypothesis with a fact.
- **Success criteria:** evidence-backed queries, focused conflicts, read permissions, corrections propagated to relevant preparations and publications.
- **Dependencies/risks:** M1; relationship UX and correction history.
- **Status:** planned. I/T/D/P: no.
- **Known limitations:** narrative quality requires human review.

### M3 — Structured preparation from an AP or original creation

- **User outcome:** open a private set of editable GM documents: one sheet per important person, place, faction, and situation, plus a visual campaign bible showing the current table state or a clearly labeled proposed starting state. Use linked relationships, a timeline, maps, portraits, stakes, source links, and visible preparation gaps. Original campaigns grow the same structure iteratively.
- **Demonstration:** transform one owned scenario into a structured private dossier, open a character from the overview, follow its links and backlinks, inspect its source, edit it in another Markdown editor, and see the changed text in the workspace. Start a fictional original campaign with empty sheets and extend it. Later, do this for every volume of Kingmaker and verify each chapter before claiming completion.
- **Success criteria:** useful per-subject sheets with motivations and stakes, an appealing visual entry point, color-coded scene information, maps and portraits where available, relationship navigation, a timeline separated from played history, source citations, external editing, exact-passage comments, interruption/resume, coverage and gaps, AP/campaign/proposal separation, and no duplicate work.
- **Dependencies/risks:** source extraction and editorial judgment; relations and timeline must not become canon merely because they were imported. PDF rights, editions, and processing time remain relevant.
- **Status:** I partial (private PDF import and source packets; 31 private Markdown preparation documents for a real 100-page scenario, a visual bible with proposed starting state, five scene cards, color-coded stakes, clickable six-node relationship diagram, extracted private maps and six verified NPC portraits; all 31 editorial sheets use color-coded section cards and the provisional timeline has a visual spine; cross-links, backlinks, citations, exact-passage comments, original-campaign starter and dossier validator); T partial (22 tests, including private visual boundaries and bible comment HTTP journey); D partial (real browser journey at desktop and mobile widths, October 26, 2026); P awaiting owner judgment. Complete AP import I/T/D/P: no.
- **Known limitations:** the 31 sheets are a first structured editorial pass, not 55 complete playable scene sheets or a complete AP. The relationship graph covers six major subjects; the fuller relationship sheet shows 15 linked entries. Maps and portraits cover only selected subjects, and many rooms lack a visual play aid. Physical PDF pages may differ from printed page numbers. Scanned pages need separate extraction; interpretations need GM verification. The PDF, extracted text, and campaign sheets remain private outside Git.

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
