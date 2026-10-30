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

For each subject that matters in the scope, create or complete one note.
Search first (`grep -ril` on titles and `aliases`): `npcs/` already holds a
draft for every unique Foundry actor (`prep: draft`, a todo callout and the
AP pages that mention it). Complete it; never create a second note.

Every note: frontmatter per `tools/ttrpg/schema.yaml`, `origin: ap` (facts
from the adventure; `custom` for your own suggestions, which go in
`> [!idea]` blocks), `prep: ready` once it holds everything below, sources as
`[[ap-page-id]]` links (add `src:` PDF pages only if `.cache/sources/` is
available). Keep proper names as in the AP; translate the rest. Aim for one
screen per note: the AP page keeps the detail.

**NPC** (`npcs/<id>.md`): fields `level`, `state`, `location`, `factions`,
`foundry`. Body sections:
- `## À la table` - role in two lines, appearance and voice in two lines,
  what they want, how they react to the PCs.
- `## Ce qu'il sait` - what they can reveal, and at what price or condition.
- `## Relations` - one line per relation to another note, with its stakes.
- `## Statistiques` - the `@UUID[Actor...]` link, plus any AP adjustment.
- `## Sources` - the AP pages.

**Faction** (`factions/<id>.md`): `leader`, `base`. `## But`, `## Moyens`
(members by link, resources), `## Ce qui se passe si les PJ n'agissent pas`
(link the faction's clock), `## Sources`.

**Place** (`places/<id>.md`, type `location` or `settlement`; hexes already
exist as `hex` notes in `adventure/`): `in` or `region`. `## À montrer aux
joueurs`, `## Ce qui s'y trouve` (scenes, NPCs, treasure by link),
`## Sources`.

**Quest** (`quests/<id>.md`): `giver`, `state: open`. Goal, reward,
completion condition, sources. The AP's quest pages already exist as `quest`
notes in `adventure/`: if one covers it, link it instead of copying.

**Clock** (`clocks/<id>.md`) for every threat or faction that advances on its
own: `segments`, `filled: 0`, `owner`. One line per segment: what happens
when it fills. This is the front: what the world does without the PCs.

**Event** (`events/<id>.md`) for the adventure's expected timeline:
`date` (quoted in-game `"YYYY-MM-DD"`), `participants`, `location`,
`played: "no"`. If the AP gives no absolute date, derive it from
`start` in `campaign.yaml`; if that key is missing, propose one from the AP
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
