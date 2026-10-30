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
   we start, three to five likely threads, NPCs to have at hand, open GM
   decisions as `> [!question]`, and a short missing-prep checklist.
5. Do not mark anything as played. Run `tools/bin/ttrpg check`.
