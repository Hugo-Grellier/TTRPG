# Product vision — campaign assistant for GMs

**Status: vision from the interview with the GM, October 23, 2026.** This document describes a **new, independent tool**. LoreForge, SecondChair, and other resources may provide ideas, code, or methods after evaluation; their product and architecture decisions do not govern this tool. Its name remains open.

## In one minute

A campaign assistant for GMs who want to create, with their players, adventures as vivid and memorable as those that inspire them in *Critical Role*, with the richness and polish of a Pathfinder Adventure Path. The GM imagines, discusses, and directs at whatever scale they choose; the assistant helps them write, prepares playable material, tracks choices made at the table, and maintains campaign continuity. Its purpose is to make that ambition accessible to a GM with little time, without exhausting them with note-taking, source searches, or Foundry configuration.

*Critical Role* expresses the narrative ambition: memorable characters, powerful scenes, improvisation, and tangible consequences of player choices. Adventure Paths and the mapmakers mentioned by the GM express the ambition for polished material. The quality of a group's play remains a collective achievement; the tool should give the GM the means and time to pursue it.

## Problem, audience, and measure of success

Running a campaign for years requires imagining, writing, preparing, setting up the VTT, finding information, taking notes, maintaining continuity, and responding to the unexpected. This workload can exhaust an experienced GM and take away the pleasure of imagining and playing with friends.

The first user is the GM behind this vision. The later target audience is a GM who is **not necessarily technical** and uses Foundry and Discord. Pathfinder 2e and Golarion are the first concrete setting; the campaign workspace also works without Foundry. Support for other systems, VTTs, or ways of playing is a later possibility, not a prerequisite for this vision.

The desired long-term outcome is for the GM to keep wanting to prepare and play over time. A campaign and every session are significant human commitments; the GM will not try the tool in a real session until it is sufficiently mature, reliable, and usable. Its value must first be demonstrated away from the table. Later, at the pace at which the GM agrees to play, assess preparation time and fatigue, confidence in continuity, quality of material, correction time, and the GM's enjoyment.

## Collaboration principles

1. **The GM directs at every scale.** They may define a theme, an arc, a session's goals, or the position of an object in a room. They may intervene during the work, comment on an element, request another direction, or delegate widely when they lack energy. The assistant proposes ideas and co-writes with them, especially the memorable moments; it can also produce delegated details on its own.
2. **Play is authoritative.** Events actually played become true for this campaign. A book or AP remains a source and inspiration. The GM specifies what they want to preserve from an AP; decisions made at the table may transform it.
3. **States remain legible.** An official source, session observation, provisional timeline, established fact, GM decision, accepted preparation, rejected proposal, and uncertainty must be distinguishable. An invention is not presented as a memory or official lore. Significant conflicts are brought to the GM with their sources; questions should remain occasional and targeted.
4. **Control comes through direction and review.** The GM does not want to approve every generated detail. They must be able to understand and easily correct changes that matter, without reading Git diffs of JSON or Markdown. An action that becomes visible to players waits for a simple GM gesture.
5. **The GM's language governs output.** The GM chooses the campaign's language. All content produced for the campaign and intended for the GM or players to read or use is written in that language: plot, dossier, preparation, summaries, live bubbles, NPCs, scenes, and publications. Sources may be in other languages; their titles, pages, and verifiable excerpts retain faithful references to the original. Proper names and game terms follow the GM's preferences.
6. **Assistance remains usable.** The dossier and material already prepared can be consulted and played when transcription, a model, or the Internet is unavailable. The tool states what is ready, provisional, or incomplete.

## The campaign journey

### Start from any state

The GM can start from a blank page, an initial draft, an Adventure Path such as *Kingmaker*, or a campaign already underway. The assistant helps discover a direction through conversation, compare genuinely different ideas, and turn existing notes or sources into a usable campaign. It can also support a published campaign whose players have already departed from the text.

**Importing an AP means processing the entire work**, not merely building a search library. From PDFs owned by the GM, the tool produces a structured dossier for every chapter: plot, scenes, characters, locations, secrets, branches, and links between elements. Each chapter must be complete enough to run its scenes from the dossier; links to the PDF allow the original text and exact rules to be checked. The PDF is the initial reference source. The GM can then discuss changes, improve the material, and let the campaign diverge through play. The dossier identifies incomplete chapters.

A long import shows progress, preserves completed parts with a provisional status, and resumes without starting over when a subscription or service reaches its limit. It is declared complete only after coverage of all chapters and their links has been verified. Foundry scene production normally follows the pace of play; the GM may request complete preparation in advance.

### Design and maintain the campaign

The campaign workspace is a dedicated place to work, usable without Foundry. Conversation is for discussion and direction; editorial views show the result. The GM can annotate a character, location, scene, or passage as in a document review, request a local correction, and return to chat for broader direction. Tone and editorial style may evolve over a long campaign; the assistant learns from the GM's instructions, examples, and corrections.

The desired dossier has the readability and usefulness of an AP, with the living memory of this table. It includes at least:

- premise, themes, current direction, and the GM's editorial choices;
- state of the world, locations, factions, characters, relationships, and motivations;
- secrets, player-character knowledge, open story threads, and outstanding promises;
- history of played events, decisions, changes, and the references supporting them;
- present situation, lasting consequences of player choices, possibilities for coming sessions, and “what next”;
- scenes, encounters, maps, handouts, and other directly usable elements.

After three years of play, it must be possible to find who did what and why the current situation exists. The GM can also recover abandoned threads without confusing them with established events. When two sources contradict each other, the tool shows the disagreement and asks for a targeted ruling if it changes the work ahead. NPCs maintain coherent intentions; player decisions durably change relationships, resources, and future situations and open up other possible scenes.

### Prepare a session

The GM may explore a plot at length with the assistant, co-write the high points, or simply delegate preparation. The result includes playable situations that respond to several plausible player choices, NPCs the GM can portray, useful PF2e elements, references, and required VTT material. A “session in an hour” view immediately shows the current state, a recap of the last session, important people and stakes, likely scenes, information to reveal, possible branches, and what is still missing.

Visual production may start with sketches during discussion. Once a direction is chosen, the goal is a map of quality comparable to the professional maps cited by the GM (Paizo, Tom Cartos, Forgotten Adventures, Dread Maps), followed by a Foundry scene ready to play: walls, lighting, sounds, tokens, objects, events, traps, and other relevant elements. The GM may require a particular map, provide assets, or ask for a search, adaptation, or generation. “Ready” means the GM can open and run the scene after inspecting it. Anything missing or mediocre remains visible with a proposed remedy; the tool does not hide remaining work behind that label.

### Play and respond

A Discord bot joins at the beginning of a session and leaves at the end; it also captures out-of-game conversation. It receives one track per Discord user and must be able to distinguish multiple people on one track when they share a microphone. When attribution changes the meaning of a fact and remains uncertain, it displays “speaker uncertain” instead of guessing. This case can be tested with a manufactured mixed recording rather than waiting for it to happen at the GM's table.

The transcript feeds private contextual assistance for the GM, displayed in Foundry or another suitable surface. It resembles a small bubble with **one short primary suggestion**, whose color or visual prominence reflects importance. It may suggest a rule when discussion reveals confusion, recall a relevant fact, suggest a line or acting advice when the GM describes an NPC, or show a possible consequence of player choices. The suggestion expires with the scene or context that justified it. Its source remains accessible; the GM can dismiss it, keep it, or ask for more. If the context is uncertain, the bubble presents a lead to check. The GM may also ask the assistant directly.

When players overturn the preparation, the ambition is to let the GM continue without a visible break: improvise an NPC or plot response, find credible options, or even quickly prepare a map or scene. The assistant can work in the background. The GM triggers anything visible to players with a simple gesture, such as dragging a rule, spell, or action from a compendium into chat. The durable campaign dossier can be updated after the session.

### Review a session and continue

The transcript is used to produce an **immediately consultable provisional timeline**, the campaign elements touched, possible consequences, and decisions that truly require the GM. The agent distinguishes in-game events from out-of-game exchanges; it retains campaign decisions, play intentions, and useful questions without turning casual conversation into campaign memory. The full transcript remains available for a period chosen by the GM. Raw audio is not intended to be kept after the necessary processing.

A grouped review highlights ambiguous passages and consequential facts before durable integration into the dossier. It allows the GM to correct, accept, discard, comment, and ask for another proposal without approving every line. Corrections propagate to character knowledge, relationships, preparations, and other dependent internal elements. A late correction separately flags publications already seen by players. The GM can quickly correct uncertain speaker attribution or a factual error without needlessly repeating all the work.

[ArchivistAI's session review](https://www.myarchivist.ai/documentation) is a journey reference: editable timeline, proposed entities, and correction before integration. Its [claimed filtering of out-of-game exchanges](https://www.myarchivist.ai/faq) inspires a case to measure, without assuming that it or our tool is reliable.

The GM can publish a secret-free selection to players: a campaign journal, discovered information, or, for example, a town newspaper recounting their exploits. To improve their GMing, they may ask for a rehearsal before a session, discreet advice during play, or feedback afterward. A player may request private post-session feedback focused on their own play goals, without a “performance” grade.

## PF2e library, sources, and provenance

The GM owns a complete collection of PF2e PDFs. They want to index and search it for rules, Golarion lore, ideas, and complete adventures or campaigns. A response based on a book gives its title and page; it distinguishes a retrieved passage, interpretation, translation, and invention. Responses also support session and encounter design, even though Foundry already automates some rules. An AP's PDFs may underpin a campaign that subsequently diverges according to the table.

PDFs and transcripts may be processed by external services if the GM chooses; a local option remains desirable, especially to control cost. The GM's PDFs, transcripts, and private campaigns are not resources to distribute with the software. The GM and players know a session is being recorded when a Discord bot joins the channel; the experience must make that information and the processing choices clear.

## Possible interfaces and responsibilities

The experience may be divided into:

| Part | Intended role |
| --- | --- |
| Campaign workspace | Create, discuss, search, prepare, review, comment, correct, and consult without Foundry. |
| Foundry module | Observe play context, create and synchronize playable elements, display assistance to the GM, and execute actions triggered by the GM. |
| Discord bot | Capture the session, provide transcription, and possibly offer player commands or publications. |
| Agents and processing | Research, write, transcribe, generate or adapt assets, prepare material, and consolidate the campaign. |

This division is a product hypothesis, not an accepted architecture. Synchronization must avoid duplicates and preserve GM edits in Foundry. The GM's private workspace contains secrets, sources, proposals, and advice; players see only what the GM chooses to publish to them.

### Repository organization to decide

**Hypothesis to evaluate: three code repositories**, while keeping this vision document independent. The proposed functional boundaries are:

| Provisional repository | Contents and reason for separation |
| --- | --- |
| Campaign application | Campaign workspace, dossier, PF2e library, agents, session processing, and review interface. It owns durable memory, visibility rules, and exchange contracts. |
| Foundry module | Installable Foundry extension, in-session interface, observations, and production of VTT material. Foundry imposes its own package, compatibility, and release cycle. |
| Discord bot | Session capture and transcription, possible player commands and publications. It has its own Discord permissions, secrets, continuous availability, and installation cycle. It sends observations to the campaign application without holding a second canonical memory. |

These three parts could live in one, two, or three repositories. Decide after a first integrated journey by comparing installation for a nontechnical GM, frequency of changes crossing several parts, need to publish the Foundry module and bot separately, secret management, compatibility testing, and coordination cost. A separate repository should simplify a real boundary, not merely reflect an architecture diagram.

Whatever the split, the campaign application owns durable memory and defines a versioned exchange contract with examples. Foundry and Discord consume that contract. An integrated demonstration brings the components together on a Foundry instance and in a Discord test environment. An additional “shared contracts” repository also requires concrete justification.

This proposal follows delivery boundaries; it does not require dividing work among teams or publishing every component from the start. Names, licenses for the new code, and technologies remain to be chosen.

## Cost and candidate resources

The GM already pays about €20 per month for Claude and €20 for Codex, and hosts Foundry on a server with a GTX 1080; a GTX 1070 is available but not powered. Their gaming PC has an RX 9070 XT. They want to avoid much higher recurring spending and might accept around **€1–2 in API costs per session**, with local options where the hardware permits. **1–2 seconds** of latency is acceptable for some live suggestions; the type of assistance shown must depend on actual latency.

Codex and Claude Code/Cowork are candidates for long-running work before and after sessions, **including the initial full import of an AP using the GM's subscriptions**. Their access, usage limits, and recovery after interruption must be verified in the real integration. The initial import does not assume paid API calls. WhisperX is a candidate for consolidated transcription. Local streaming transcription, local voice models, real-time APIs, Dungeondraft, asset libraries, ComfyUI, Midjourney, GPT Image, Nano Banana, and online resource searches are paths **to compare and measure**, not selected dependencies. Visual quality, usage rights, Foundry compatibility, processing time, actual cost, and ease of installation for a nontechnical GM should distinguish these options.

### Saving credits and tokens during use

Cost control concerns **daily use of the product**, distinct from development cost. The tool must track costs by campaign, session, task, and provider, show an estimate before a heavy operation, and let the GM set a limit. The total price includes model calls, transcription, images, storage, and any external services; it must not be obscured by an existing subscription.

The architecture to evaluate should reduce calls without harming useful quality:

- retrieve relevant passages from books and the campaign first, instead of sending the whole library or history in every prompt;
- keep structured summaries, references, and reusable results; invalidate this cache when facts, sources, or instructions change;
- process changes since the previous session rather than regenerate the whole dossier after every session;
- reserve expensive models and reasoning for creative decisions or difficult research; use local, simple, or cheaper processing for transcription, classification, and repetitive work when quality suffices;
- batch work that can wait, avoid continuous calls during a session when no relevant context changes, and limit the size of live responses;
- offer the GM cost and quality profiles while flagging tasks that a cheap profile would handle poorly;
- measure cost, latency, and quality together on representative scenarios before choosing a provider or model.

These mechanisms are outcome requirements and design paths; they do not yet determine the provider, cache format, or routing policy. The indicative €1–2 API limit per session must be tested across complete usage, including retries and errors. The per-session cap is **hard**: once reached, live assistance uses local resources and already prepared material; deferrable work waits until the GM raises the cap or chooses another option.

## Validation before any real session

LoreForge and SecondChair are **existing resources to inventory**, like tools, modules, libraries, and examples available online. Examine their functions, tests, fictional data, limits, and reusable pieces without automatically adopting their choices. PF2e/Foundry community resources and the APs the GM owns may help define a quality bar and test cases, while respecting usage rights.

Build an off-table testbed with a fictional campaign and **Kingmaker, an AP the GM owns in PDF form**. Test structure and references across the entire AP. Simulate sessions and player decisions that first follow and then depart from the AP: fixed scenarios catch regressions; freer simulated players test improvisation. Their actions are test data and never become facts of the GM's future campaign. The testbed covers months or years of continuity: contradictory notes, imperfect transcription, branches, urgent preparation, Foundry scenes, and service outages. Replay the same cases after each change to spot regressions. The AP PDFs and their excerpts stay in the private test environment, outside public repositories and published results.

Test the module on a **real local Foundry instance**, with a test world separate from the GM's campaign: installation, scene creation and editing, walls, lights, sounds, actors, items, events, player visibility, and resynchronization. Choose several different Kingmaker situations, including exploration, dialogue, and combat. [Paizo's official Kingmaker module](https://foundryvtt.com/packages/pf2e-kingmaker), which the GM does not own, provides a public reference for coverage and polish; testing assumes neither its purchase nor reproduction of its exclusive assets. [Foundry's official FAQ](https://foundryvtt.com/article/faq/) allows a private development instance under the same license if only one instance is accessible to other users. Protect the license key and keep the test instance inaccessible to players. Complement this with human review of text, maps, and UX. Technical tests alone do not prove narrative quality or ease of use.

Before asking the GM to commit a real campaign or session, have them walk through **the same Kingmaker campaign from end to end**: the entire AP imported, sources retrievable, GM-directed changes, simulated sessions with branches, several inspectable Foundry scenes, simulated live assistance, a correctable post-session review, preserved continuity, and visible costs and remaining work. Review and creative choices are normal; reconstructing the dossier and repeatedly setting up Foundry should already be handled. The GM then decides whether the product is mature enough for a real session. Its durable value will be judged through use when that time comes.

## Success scenarios to demonstrate

1. **Long campaign.** The GM asks who made a promise two years earlier. The tool finds the fact, its context, and its source in the campaign's language, and honestly signals any uncertainty.
2. **Transformed AP.** The GM loads all the Kingmaker PDFs, finds every chapter and its links, then specifies what to preserve. A subscription limit interrupts processing; it resumes without loss. Simulated players then take an unexpected path. The tool distinguishes the published text from this table's history and proposes a coherent continuation.
3. **Session in an hour.** After a week with no preparation, the GM gets a usable sheet, knows what is ready in Foundry and what is missing, then plays without reconstructing the result.
4. **Live improvisation.** A rules question or unexpected NPC comes up. The private bubble provides short, relevant help; a Foundry action visible to players happens only after the GM's gesture.
5. **Post-session review.** In-game events are distinguished from out-of-game conversation and linked to campaign elements. The GM quickly corrects a wrong attribution and an unfounded suggestion; these corrections remain effective in the next preparation. A mixed recording tests the case of two voices on one track.
6. **Produced scene.** The GM chooses or has a map produced; the Foundry scene contains the expected elements and remains inspectable and editable before play.
7. **Outage and cap.** During a session without a model or Internet, or after reaching the paid cap, the GM retains access to the dossier and already prepared material; available local assistance remains usable.

## Framework for autonomous implementation

This document gives the **complete destination**, without pretending that a single overnight effort can achieve professional editorial quality and integrate every service. An agent charged with implementation must turn each scenario above into an observable result in a test environment, measure what works, and explicitly report what is missing. A simulated interface, merely illustrative map, or summary without provenance does not constitute complete implementation of this vision.

The new tool must make its own decisions about the source of truth, campaign states and authority, component boundaries, permissions, player visibility, source processing, and exchanges with Foundry. LoreForge and SecondChair may be studied or selectively reused; their documents remain specific to those projects. Development can progress without waiting for a real session thanks to the fictional cases, simulations, and integrated demonstrations described above.

### Points still to decide or verify

- Exact model of relationships, states, provenance, and contradiction resolution; which ideas to adopt from SecondChair.
- Precise UX for comments, review, history, and Foundry synchronization.
- Achievable quality of generated or assembled maps, a possible Dungeondraft pipeline, and asset availability.
- Cost, latency, and quality of Discord capture, speaker identification, and local assistance on the hardware described.
- Model routing policy, budgets, caching, and cost measurement for actual product use.
- Simple installation, updates, backup, and restoration for a nontechnical GM.
- Handling complex PDFs, editions, and languages, as well as rights for assets and content published to players.
- Form and terms of use of advice intended for players.

These points call for prototypes and explicit decisions. They do not remove any capability from the destination described here.
