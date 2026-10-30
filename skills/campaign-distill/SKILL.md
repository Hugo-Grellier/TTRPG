---
name: campaign-distill
description: Turn imported adventure text (adventure/) into the maintained campaign layer - short, structured NPC, faction, place, quest, clock and event notes in the campaign language, linked back to the AP pages. Use when the GM asks to distill, process or prepare a chapter, region or appendix of an imported adventure.
---

# Distill an adventure into campaign notes

The repository has two layers. `adventure/` is the published text, imported
and re-importable: never edit it here. The campaign layer (`npcs/`,
`factions/`, `places/`, `quests/`, `clocks/`, `events/`) is what the GM
maintains through play: short notes, in the language of `campaign.yaml`,
that say what matters at the table and link to the AP page for the rest.

## Scope

Work on the scope the GM names (a chapter journal such as
`adventure/1-a-call-for-heroes/`, a hex region, an appendix). Start by reading
its index note (same name as the folder) and every page under it. Read pages
outside the scope only to resolve a link. Do not distill outside the scope;
list what you saw for later instead.

## What to produce

For each subject that matters in the scope, create or complete one note in
the campaign layer, written as `tools/ttrpg/note-types.md` says for its type.
Search first (`grep -ril` on titles and `aliases`): `npcs/` already holds a
draft for every unique Foundry actor (`prep: draft`, a todo callout and the
AP pages that mention it). Complete it; never create a second note.

- Folders: `npcs/`, `factions/`, `places/` (location, settlement), `quests/`,
  `clocks/`, `events/`. Hexes and regions already exist in `adventure/`;
  the AP quest pages too: link them instead of copying.
- Frontmatter per `tools/ttrpg/schema.yaml`; `origin: ap` for facts from the
  adventure, `prep: ready` once the note has every section.
- Sources: `[[ap-page-id]]` links; add `src:` PDF pages only if
  `.cache/sources/` is available. Keep proper names as in the AP; translate
  the rest.
- A clock for every threat or faction that advances on its own.
- Events for the adventure's expected timeline, `played: "no"`, dated from
  `start` in `campaign.yaml`. If `start` is missing, propose one from the AP
  introduction in your summary and skip dated events.

## Rules

- Facts come from the AP. Never fill a gap with invention presented as fact:
  write `> [!question]` for what the GM must decide, `> [!idea]` for a
  suggestion.
- Relations live on one side (NPC `factions`, place `in`); see `inverse` in
  the schema.
- GM secrets the players must not learn early go in `> [!secret]` blocks.
- Do not change `adventure/` or the stat blocks; do not mark anything played.

## Finish

1. `tools/bin/ttrpg check` with zero errors.
2. Append the scope, date and counts to `notes/distill-progress.md`
   (`type: note`; create it if needed), with the subjects seen but left for
   another scope.
3. Commit on a branch `distill/<scope>` and open a pull request whose body
   lists the notes created or completed, the open `[!question]`s, and
   anything in the AP you found ambiguous. The GM reviews the diff.
