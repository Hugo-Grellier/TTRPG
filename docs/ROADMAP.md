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

### 2 — Export to Foundry journals (pack done; live sync done)
Generate a module whose compendium pack holds one JournalEntry per folder and
one page per note (Markdown → HTML, `[[id]]` → `@UUID`, GM secrets kept GM-only,
player notes with player ownership). Verify in the local Foundry
(`foundry-local-1`, port 30001) with Kingmaker imported alongside. Then live
sync through foundry-vtt-mcp (`ttrpg foundry plan|apply|pull`, tool
`sync-world`): journals, actors and items, ownership and death, date, clocks,
discovered places. Next: deploy the fork's bridge and Global Progress Clocks
to production (maxi-lab bundle, owner approval), map pins as managed scene
notes from `map-ready`.

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

### 6 — Large original campaigns grounded in the published setting
The tools know two modes: import an adventure and compile it, or invent a
small sandbox from an interview. A long original campaign set in Golarion
needs a third: original material grounded in canon spread over many books.
Measured against an earlier "campaign dossier V0.1" prompt (Westerhold,
Absalom, Kortos, Dahak; November 3, 2026): notes, factions, clocks, secrets,
check and sync hold the result; research, provenance, PCs, reputation and
scale are missing. Needed by any large campaign, AP or not. The owner has
the official PDFs (518 files, `~/Downloads/manual/Pathfinder 2e/`: rulebooks,
Lost Omens, APs, Society, adventures).

- **6a Shared source library (done; scanned books through OCR).** `ttrpg library index <dir>` extracts every
  PDF once (pdftotext, per page) into a library outside campaigns
  (`~/.cache/ttrpg/library/<id>/pNNN.txt` + `catalog.yaml`: id, title, path,
  pages, category, edition legacy/remaster, language). `ttrpg library search
  <regex>` returns book, page and line. `ttrpg source add <id>` declares a
  book in `campaign.yaml` from the catalog (CI has no library, so the
  declaration stays in the campaign). `pdf-text` becomes the one-book case.
  Page images on demand (pdftoppm) for maps. Rules lookups and URLs through
  the Archives of Nethys index the glossary already uses.
- **6b Provenance per paragraph (done).** A cited paragraph is canon; `> [!adaptation]`
  changes canon for this campaign and cites what it changes; `> [!verify]` is
  unverified (community wiki only, memory); an uncited paragraph in a custom
  note is original. Custom notes may cite. The export labels them.
- **6c `ttrpg questions` (done).** Open `[!question]`, `[!idea]`, `[!verify]` across
  the campaign, by note; every skill's report and the GM's to-do list use it.
- **6d Schema for long campaigns (done).** `pc` type (player, ties to NPCs and
  factions, ambitions, secrets, arc hooks; filled after session zero);
  party reputation per faction (GM Core Reputation); renown; `party` size and
  level in `campaign.yaml` for encounter budgets; a home base's improvements;
  mysteries with their clues (where each can be found, when it was found,
  marked by `session-debrief`); `chapter` sections for sandbox arcs.
- **6e Skill `lore-research` (done).** A subject (a district, a deity, a faction)
  gathered from the whole library, remaster first, books that disagree
  shown side by side in `[!question]`, written as a canon note per
  `note-types.md`. Same rules as `campaign-compile`, over the library
  instead of `adventure/`.
- **6f Large-campaign workflow (written; verify below).** `campaign-create` for a large pitch:
  research inventory from the library, a decisions note comparing options
  with a recommendation, drafts (`ttrpg drafts`), agent waves as for the
  Kingmaker compile, a quality checklist (open structure, independent arcs,
  canon cited, geography and travel times, five-PC encounters), report from
  `ttrpg questions`.
- **6g Gaps found by an audit of the dossier prompt (November 3, 2026):**
  - *Region maps and hexploration.* Kortos has no official hex map. Survey
    PathfinderWiki's interactive Golarion map (map.pathfinderwiki.com,
    community-derived from the official maps, vector tiles with coordinates:
    github.com/pf-wikis/mapping) for a region image with real distances;
    otherwise a map page from the library (`library page`). Then a hex grid
    over that image, `hex` notes keyed to it, travel times from GM Core's
    exploration rules, and the Foundry scene through `map-ready`.
  - *Chronology (done).* Define history versus plan: an event dated before
    `campaign.yaml` `start` is the setting's past (cited canon); after it,
    `played: "no"` is planned and `"yes"` happened. A `start` chosen from the
    library (the latest book's year, the outcomes later books give
    adventure paths such as Age of Ashes), with the reasoning in a note.
  - *Library for remote agents.* Cloud agents (Codex, Claude on the web) have
    no PDFs: a way to reach the text (a private host, or committed excerpts
    of what a campaign cites).
  - *Encounters (done).* Survey existing PF2e encounter builders before writing
    one; then a tool that finds creatures by level and trait offline and
    budgets XP for `party` characters at a level.
  - *Standing.* Structure what reputation does not hold: renown, wealth,
    informal influence and legal authority, kept apart.
- **Verify:** the dossier prompt run on a scratch campaign, then compared with
  this list.
- **Later:** a hex grid over any region map (Kortos has no module hex map),
  once a sandbox reaches hexploration in play; French names of lore places
  and organizations when no French edition is in the library.

### Later
Test of how ready to play generated content is: build a world only from an
adventure's PDF (Kingmaker or another AP) with these tools, and compare it with
the same adventure's official Paizo Foundry module (journals, actors, scenes,
walls, lights, encounters).
Player-facing export (only `players` notes, secrets stripped), a read-only
viewer if Foundry and Obsidian are not enough, French translation of imported
AP text on demand, original-campaign starter (factions, fronts, clocks).
