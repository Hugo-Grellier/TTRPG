---
name: campaign-compile
description: Build complete, structured campaign notes (NPC, faction, place, hex, region, scene, quest, item, clock, event) from the imported adventure text in adventure/, gathering everything every page says about each subject, translated into the campaign language. Use when the GM asks to compile, complete, process or prepare subjects, a chapter, a region or an appendix of an imported adventure.
---

# Compile an adventure into campaign notes

The repository has two layers. `adventure/` is the published text, imported
and re-importable: never edit it here. The campaign layer (`npcs/`,
`factions/`, `places/`, `scenes/`, `quests/`, `items/`, `clocks/`,
`events/`) is what the GM maintains through play. Each campaign note is the
complete reference on one subject: everything the adventure says about it,
from every page, structured per `tools/ttrpg/note-types.md` and written in
the language of `campaign.yaml`. Notes are never summaries: session prep
(`session-prep`) condenses them for a given session.

## Scope

The GM names subjects, or a chapter, region or appendix. For a chapter or
region, the subjects are every NPC, faction, place, hex, scene, quest, item
and threat it contains or mentions. List them first and say how many.

Each subject is compiled from the whole adventure, not from the scope: a
chapter only chooses which subjects to do.

## For each subject

1. **Find the note.** Search `npcs/`, `factions/`, `places/`, `scenes/`,
   `quests/`, `items/` by title and `aliases` (`grep -ril`). `npcs/` already
   holds a draft for every unique Foundry actor (`prep: draft`, a todo
   callout, the AP pages that mention it): complete it; never create a
   second note. A subject with one main AP page (a hex, a scene, a
   settlement) takes that page's id without the module prefix
   (`km-a23-dueling-chamber` → `a23-dueling-chamber`).
2. **Gather every source.** `grep -ril` the title, each alias, short forms
   of the name and the Foundry id across `adventure/`, including
   appendices, gazetteers, handouts, the campaign synopsis and every later
   chapter; and `.cache/sources/*` (PDF text) if present. Read each hit in
   context, the whole paragraph or room, not the matching line. Keep the
   list of pages read.
3. **Write the note.** Every section of its type in `note-types.md` that the
   sources support, in order. Translate and reformulate; merge what several
   pages repeat; keep every fact, number, DC, condition and name.
   Frontmatter per `tools/ttrpg/schema.yaml`: the structured facts (level,
   ancestry, location, factions, chapters, leader, region...) as fields;
   `origin: ap`; `prep: ready` once every source is covered.
4. **Check coverage.** Go through the list of pages read: each must be cited
   in the note, and each fact it gives about the subject must be in it. A
   page that says nothing new is still cited in Sources.

## Rules

- Facts come from the adventure. Never fill a gap with invention presented as
  fact: `> [!question]` for what the GM must decide, `> [!idea]` for a
  suggestion. Where pages contradict each other, give both, cited, in a
  `> [!question]`.
- What the players must not learn early goes in `> [!secret]` blocks, in the
  section it belongs to.
- Relations live on one side (NPC `factions`, place `in`); see `inverse` in
  the schema.
- A clock for every threat or faction that advances on its own; events for
  the adventure's expected timeline, `played: "no"`, dated from `start` in
  `campaign.yaml`. If `start` is missing, propose one from the AP
  introduction in your summary and skip dated events.
- Link subjects to each other's campaign notes (`[[jamandi-aldori]]`), and to
  AP pages only as sources.
- Do not change `adventure/` or the stat blocks; do not mark anything played.

## Finish

1. `tools/bin/ttrpg check` with zero errors.
2. Append the scope, date, the subjects compiled and those seen but left for
   later to `notes/compile-progress.md` (`type: note`; create it if needed).
3. Commit on a branch `compile/<scope>` and open a pull request whose body
   lists the notes created or completed, the open `[!question]`s, and
   anything in the adventure you found ambiguous. The GM reviews the diff.
