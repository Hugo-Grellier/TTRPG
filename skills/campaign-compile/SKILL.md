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

Order: places, hexes and scenes first, then items and quests, then NPCs and
factions. Facts live in their subject's note (`note-types.md`): a scene's
mechanics go in the scene note, and an NPC compiled after it only links it.
When a subject you write about has no note yet (a place, a scene, an NPC the
scope mentions), create it: compiled if it is in the scope, otherwise a
draft (`prep: draft`, the facts you saw, a `> [!todo]` and its AP pages) so
links and fields (`base`, `in`, `location`) point at campaign notes, never at
AP pages.

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
   chapter; and `.cache/sources/*` (PDF text) if present. Open and read each
   page in full, never only grep excerpts: what matters is often in the next
   paragraph. Keep the list of pages read.
3. **Write the note.** Every section of its type in `note-types.md` that the
   sources support, in order. Translate and reformulate; merge what several
   pages repeat; keep every fact, number, DC, condition and name.
   Frontmatter per `tools/ttrpg/schema.yaml`: the structured facts (level,
   ancestry, location, factions, leader, region...) as fields;
   `origin: ap` (compiling is not changing the adventure: `modified` is for
   the GM's own changes); `prep: ready` once every source is covered, open
   `[!question]`s included.
4. **Check coverage.** Go through the list of pages read: each fact a page
   gives about the subject is in the note (or in the note of the scene or
   subject it belongs to, linked), and every page that says something about
   the subject is cited. Pages that only match a homonym or a generic word
   are left out.

## Rules

- Facts come from the adventure. Never fill a gap with invention presented as
  fact: `> [!question]` for what the GM must decide, `> [!idea]` for a
  suggestion. Where pages contradict each other, give both, cited, in a
  `> [!question]`, and never state either version as fact elsewhere in the
  note, In brief included.
- A name with no official translation in `glossary.tsv` keeps the source's
  spelling: never invent a French name for a proper name, a creature or a
  game term (*Old Sharptooth* stays *Old Sharptooth*). Names of documents
  that exist only in the adventure module (world items, effects, actors) stay
  as Foundry shows them.
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
- Names of items, spells, actions, conditions and creatures: as the campaign
  language's edition names them, from `glossary.tsv` when present
  (`ttrpg glossary` builds it). Look up the id of the linked Foundry document
  first (`grep TmQalYKNNRuEdoTh glossary.tsv`), else the English name
  (`grep -P "\tMage Armor\t" glossary.tsv`: pre-remaster names give the
  remaster one and its translation); the kind column tells a spell from an
  item of the same name. Rules text and details: <https://2e.aonprd.com>
  (English) and <https://pf2e.pathfinder-fr.org> (French).
- A scene's `level` is the level of its encounter or, if none, the party
  level the adventure gives. Area numbers and other facts you deduce (from a
  map, an index order) are written as such ("probablement la zone 06"), never
  as if the text gave them.
- PDF citations `src:id#pN` use the PDF page, the number of the file in
  `.cache/sources/<id>/`, not the printed folio.
- Do not change `adventure/` or the stat blocks; do not mark anything played.

## Finish

When you are one of several agents compiling in parallel, skip this: report
your notes, their `[!question]`s and the subjects without a note to the
agent that gave you your list, which finishes for all.

1. `tools/bin/ttrpg check` with zero errors.
2. Append the scope, date, the subjects compiled and those seen but left for
   later to `notes/compile-progress.md` (`type: note`; create it if needed).
3. Commit on a branch `compile/<scope>` and open a pull request whose body
   lists the notes created or completed, the open `[!question]`s, and
   anything in the adventure you found ambiguous. The GM reviews the diff.
