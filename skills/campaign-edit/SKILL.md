---
name: campaign-edit
description: Create or change notes in a campaign repository (NPC, place, faction, scene, quest, event, clock, session) while keeping links, schema, chronology and player visibility coherent. Use for any edit to campaign content.
---

# Edit campaign notes

1. Read `campaign.yaml` for language and system, `tools/ttrpg/schema.yaml`
   for the fields of the note type you touch and `tools/ttrpg/note-types.md`
   for its sections. Write in the campaign language.
2. Find before you create: search file names and `aliases` for the subject.
   If a note exists, edit it; do not create a second one.
3. New note: file `<id>.md` in the folder of its kind (`npcs/`, `places/`,
   `factions/`, `scenes/`, `quests/`, `events/`, `clocks/`, `sessions/`), id in
   lowercase ASCII with dashes. Minimal frontmatter:

   ```yaml
   ---
   type: npc
   title: Oleg Leveton
   origin: custom
   location: olegs-trading-post
   factions: [swordlords]
   ---
   ```

4. Relations are written on one side only (see `inverse` in the schema). To
   put an NPC in a faction, edit the NPC's `factions`, not the faction.
5. Editing an `origin: ap` body: set `origin: modified`. Keep Foundry
   enrichers (`@UUID[...]`, `@Check[...]`) intact unless the change is about
   them.
6. A death, a move, a captured quest giver: update the state fields
   (`state`, `died`, `location`, quest `state`) and, if it happened in play, an
   `event` with `played: "yes"` and its in-game `date`.
7. Secrets the players must not see go in `> [!secret]` blocks or in
   `visibility: gm` notes; a `players` note never links a GM note.
8. Run `tools/bin/ttrpg check`. Fix errors; read warnings. Summarize what
   changed and anything left for the GM to decide.
