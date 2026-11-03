---
name: campaign-create
description: Build original campaign material with the GM - a sandbox from a pitch, a long campaign (levels 1-20) from a detailed brief, or a new region, faction, settlement or threat added to any campaign, imported or not. Use when the GM wants to invent rather than import.
---

# Create campaign material

Works the same in an empty sandbox and in a campaign built from an adventure:
invented notes are `origin: custom` and sit beside any `adventure/` text;
notes that report the published setting are written by `lore-research`.

## Interview first

Ask, one short round at a time, only what the notes need and the GM has not
said: tone and themes, the starting area and its scale, two or three forces
in conflict, what the PCs are and why they are here, what must stay secret.
Offer two or three concrete options per question rather than open prompts.
Stop asking when the GM says "go" or "à toi de voir": decide, and mark your
decisions as `> [!idea]` so they stay visibly yours until adopted.

## Build in this order

A sandbox runs on factions and places, not on a plot. Each step links the
previous ones.

1. **Frame** - `campaign.yaml`: `start` (in-game date play begins), `name`,
   language, `party` (number of PCs). PCs get `pc` notes with their players
   after session zero; before it, leave room for them (arc hooks), never
   write their backgrounds. A `company` note holds the group's renown,
   wealth, influence and authority as play builds them. A `notes/00-pitch.md` with the pitch, themes and lines/veils.
2. **Map** - one `region` per area, then `hex`, `settlement` or `location`
   notes for what the PCs can reach in the first sessions. Each place gets
   at least one reason to go there.
3. **Factions** - three to five, each with a goal that collides with another
   and a `clock` (four to eight segments) for what it does if the PCs do
   nothing.
4. **People** - for each faction a leader and one or two faces, plus NPCs who
   live in the starting places. Every NPC wants something.
5. **Hooks** - `quest` notes (rumors, jobs, threats) that send the PCs toward
   the factions. More hooks than the party can follow. Long conspiracies are
   `mystery` notes with their clues spread over places and NPCs; possible
   arcs are `chapter` notes (`note-types.md`, chapter (arc)), never a script.
6. **Opening** - the first `scene` and a `session-prep` note from the
   `session-prep` skill.

## A large campaign

When the GM brings a long brief (a campaign over many levels, its
inspirations, principles, places, a prologue, a first act, a distant threat),
the brief replaces most of the interview: ask only what it leaves open and
blocks the work. Then:

1. **Principles** - `notes/00-pitch.md`: promise, tone, inspirations, the
   brief's design principles as rules future work must respect, lines and
   veils. Short; the brief's own words where they are good.
2. **Research inventory** - every published subject the brief touches
   (places, organizations, people, deities, creatures, events, the rules
   subsystems it needs): `tools/bin/ttrpg library search <name> --pages` and
   `tools/bin/ttrpg aon <name>` for each. Write
   `.cache/research/inventory.tsv` (type, id, title, aliases, main_page,
   pages as `book#pN;...`, tier `major` or not), declare the books
   (`tools/bin/ttrpg source add <id>...`), then
   `tools/bin/ttrpg drafts --inventory .cache/research/inventory.tsv`.
3. **Canon** - the `lore-research` skill on each draft, major subjects first,
   one agent per few subjects in parallel (a capable model for major ones);
   agents report, you finish.
4. **Decisions** - `notes/01-decisions.md`: each choice the brief asks you to
   study (a destination, a patron, a relic, a first antagonist...) as a
   table of options with criteria, sources and a recommendation in
   `> [!idea]`; the GM adopts, rejects or changes each. Choices made in play
   or by the GM move to the notes they concern.
5. **Build** - the steps above (map, factions with clocks, people, hooks,
   mysteries, arcs, opening) on top of canon, the brief's levels in
   `chapter` notes: the near ones detailed, the far ones as directions.
   Encounters for `party` characters, threats the PCs can see coming.
6. **Review** - against the brief's principles and these questions: can the
   PCs ignore or change every situation? do independent arcs exist, beside
   the main threat? is every canon fact cited and every change an
   `[!adaptation]`? do places, distances and travel times fit the official
   maps? is each subsystem used worth its cost to the GM? Fix what fails;
   say what you could not check.
7. **Report** - what exists, the main canon findings that shaped it, the
   decisions waiting on the GM, the risks, and `tools/bin/ttrpg questions`.

Notes follow `tools/ttrpg/schema.yaml` (fields) and `tools/ttrpg/note-types.md`
(sections). Statistics are Foundry compendium links (`@UUID[Compendium...]`)
chosen by level, never invented stat blocks: `tools/bin/ttrpg creatures
--party-level N --trait <trait>` lists them with their XP for the party and
their `@UUID[...]`.

## Rules

- The GM decides. Do what was asked at the scale asked: one tavern is one
  note, not a district.
- Keep it playable: every note answers "what do I do with this at the table?"
- Write what is true in `> [!secret]` blocks when the players would learn it
  through play.
- Set in the published world: use canon before inventing it. Search the GM's
  library (`tools/bin/ttrpg library search <name> --pages`, then read the
  pages) and Archives of Nethys (`tools/bin/ttrpg aon <name>`), cite what
  you take, mark changes `> [!adaptation]` and unchecked facts `> [!verify]`
  (`note-types.md`, Provenance).
- Run `tools/bin/ttrpg check`, then summarize what exists, how it connects,
  and what `tools/bin/ttrpg questions` lists.
