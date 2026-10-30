# Product vision — campaign toolset for GMs

**Status: interview of October 23, 2026, redirected by the owner on October 30, 2026.** The SQLite web workspace built until then is archived at tag `archive/webapp-2026-10-30`; it felt like a clunky app that kept the campaign away from the tools the GM already uses.

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
4. **Control comes through direction and review.** The GM does not want to approve every generated detail. They review changes that matter as readable Markdown diffs in Git, from any editor or chat. An action that becomes visible to players waits for a simple GM gesture.
5. **The GM's language governs output.** The GM chooses the campaign's language. All content produced for the campaign and intended for the GM or players to read or use is written in that language: plot, dossier, preparation, summaries, live bubbles, NPCs, scenes, and publications. Sources may be in other languages; their titles, pages, and verifiable excerpts retain faithful references to the original. Proper names and game terms follow the GM's preferences.
6. **Assistance remains usable.** The dossier and material already prepared can be consulted and played when transcription, a model, or the Internet is unavailable. The tool states what is ready, provisional, or incomplete.

## Shape of the toolset (decision of October 30, 2026)

- **The campaign is a private Git repository of readable files**: one Markdown note per subject with YAML frontmatter, `campaign.yaml` for system, language, calendar and sources. The GM and any agent (Claude Code, Codex, ChatGPT, a text editor, Obsidian) read and edit the same files. Nothing lives in a database.
- **This repository is the toolset**, included in each campaign as the `tools/` submodule: the schema, the checker, importers, exports and the agent skills. It never holds licensed or private campaign content.
- **Coherence is enforced by the checker**, run by agents, the pre-commit hook and CI on every push: unique ids and resolving links, typed fields per note type, one-sided relations with computed inverses, chronology (dates, deaths, session order), and the distinction between imported AP text, GM modifications, GM secrets and player-visible notes.
- **Import or create.** A published adventure arrives from its Foundry module (structured pages, actors, scenes) and its PDF (citations); an original campaign starts almost empty. Both then get refined note by note.
- **Foundry is the table surface.** Notes export to Foundry journals (a generated compendium pack as the reproducible base, live edits through the Foundry MCP); changes made in Foundry come back to the repository as a diff for the GM to review. The repository wins a conflict.
- **After play**, per-speaker Discord audio transcribed locally, Foundry Flight Recorder events and the GM's notes feed a proposed update of the affected notes, reviewed as a Git diff.
- **Agents with a shell** (local or cloud: Claude Code, Codex) run the tools. Web chats with read-only repository access can discuss and draft; CI checks whatever reaches the repository.
- **The GM chooses system and language per campaign.** Tests use PF2e Remaster in French; Kingmaker and Age of Ashes are the first real campaigns.
