# Roadmap

Each step is usable on its own. Kingmaker (Foundry module + PDF) and Age of
Ashes (converted pilot) are the test campaigns, in
`~/dev/personal/Campaign/campaign-*`.

## Done

### 1 — Campaign repositories and checker (October 30, 2026)
Schema, checker, Foundry Adventure importer, PDF source extraction, campaign
template (AGENTS.md, skills, pre-commit hook, CI), both campaigns created.

## Next

### 1b — Compile Kingmaker into the campaign layer
Campaign notes are complete references (everything the adventure says about
each subject, structured, in French); session prep condenses them. Skill
`campaign-compile` gathers each subject from every page. Sample first
(Jamandi, Tartuccio, the Greenbelt bandits, Oleg's Trading Post) for the GM
to judge, then every subject of Kingmaker and the Beginner Box by cloud
agents. The earlier distilled notes (Chapter 1, zones 1-2) are replaced.

### 1c — Foundry scene tools in the MCP (tools done; `map-ready` skill next)
Add to a fork of foundry-vtt-mcp what the prototype needed: create a scene
from an image or pack entry; create/update/delete embedded scene documents
(Wall, AmbientLight, AmbientSound, Token, Note, Tile, Region) in one generic
tool; capture the canvas as an image for visual checking. Wall proposals from
an image come from a TTRPG command (OpenCV) and are reviewed visually before
use. Then a `map-ready` skill: map note + encounter notes → tokens, ambience,
pins.

### 2 — Export to Foundry journals (pack done; live update through MCP next)
Generate a module whose compendium pack holds one JournalEntry per folder and
one page per note (Markdown → HTML, `[[id]]` → `@UUID`, GM secrets kept GM-only,
player notes with player ownership). Verify in the local Foundry
(`foundry-local-1`, port 30001) with Kingmaker imported alongside. Then live
edits through foundry-vtt-mcp.

### 3 — Foundry changes back to the repository (done from world files; MCP route for remote servers next)
Read world journals (pack or MCP), turn changed pages back into Markdown,
write them over the notes and leave the diff for GM review. Repository wins a
conflict.

### 4 — Verify remote agents
Push the tools and campaign repositories (owner approval), confirm that Claude
Code on the web and Codex cloud clone the submodule and run the checker, and
that the ChatGPT GitHub connector can read both repositories. Fallback if
submodules fail: CI copies `skills/` into the campaign.

### 5 — After-session pipeline (transcribe, flight, debrief done; automatic recorder next)
Per-speaker Discord recording (start from the LoreForge
`experiments/discord-receive-timing-probe`), local faster-whisper
transcription, Foundry Flight Recorder (`ffr`) summary, GM note → proposed
note updates as a diff. Done: `ttrpg transcribe`, `ttrpg flight`, skill
`session-debrief`, setup in `docs/after-session.md`; recording uses Craig or
the probe run by hand. Next: a recorder bot that starts and stops with the
table's voice channel (needs a bot token, a test server and a host), then a
first real session debriefed end to end.

### Later
Player-facing export (only `players` notes, secrets stripped), a read-only
viewer if Foundry and Obsidian are not enough, French translation of imported
AP text on demand, original-campaign starter (factions, fronts, clocks).
