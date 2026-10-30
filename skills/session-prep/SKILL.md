---
name: session-prep
description: Prepare the next game session from the campaign repository - what the party knows, where they are, what is likely to happen, and what is still missing. Use when the GM asks to prepare, plan, or get ready for a session.
---

# Prepare a session

1. Read the latest `sessions/*.md` (by `day`) and its in-game date. If there
   is none, ask the GM where the party stands; never assume.
2. Collect what is in play: the party's location, open and active `quest`s,
   `clock`s with an owner, NPCs and factions linked from the last session.
3. List the scenes the party can reach next, with links, and for each one
   what is ready (`prep: ready`) and what is missing (stat references, map,
   motivation, consequences).
4. Write `sessions/<day>-prep.md` (`type: note`, `visibility: gm`) with: where
   we start, three to five likely threads, open GM decisions as
   `> [!question]`, and a short missing-prep checklist. This sheet is where
   the campaign is condensed: the notes are complete references, the sheet
   keeps only what this session needs, each item linking to its note.
   - **NPCs to have at hand**: per NPC, a card of four to six lines: role now,
     look and voice, what they want from the PCs this session, what they
     can reveal and at what price, their statistics link.
   - **Places and scenes**: per likely scene, the read-aloud text, the stakes,
     the opposition with its link, and the outcomes, from the scene note.
   - Secrets the PCs may learn this session, in `> [!secret]` blocks.
5. Do not mark anything as played. Run `tools/bin/ttrpg check`.
6. If the GM wants it at the table: `tools/bin/ttrpg export-foundry --install
   <Foundry Data/modules>` builds the module of journals (one entry per kind
   of note, links to the adventure's own pages and scenes, secrets revealable
   in Foundry). In Foundry: enable the module, then import its compendium
   entries, keeping ids, over the previous import.
