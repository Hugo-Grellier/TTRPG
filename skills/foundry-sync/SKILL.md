---
name: foundry-sync
description: Bring the running Foundry world up to date with the campaign notes - journals, actors and items the notes define, NPC ownership and death, the in-game date, clocks, discovered places and their map cells - and bring back what changed in Foundry during play. Use when the GM asks to update, sync or push the campaign to Foundry, or after a session debrief or any edit the table should see.
---

# Sync the Foundry world

Needs the `foundry-mcp` backend (fork with the `sync-world` tool) running and
a GM browser connected to the world. `tools/bin/ttrpg foundry` talks to it on
`127.0.0.1:31414`; if it says the backend is not reachable, ask the GM to start
Claude Code with the foundry-mcp server and open the world as GM.

## Steps

1. `tools/bin/ttrpg check` with zero errors: notes with errors are not synced.
2. `tools/bin/ttrpg foundry pull`: pages edited in Foundry and clocks moved
   in play come back into the notes. Show the GM the `git diff`; a conflict
   (changed on both sides) keeps the repository and is reported, never merged
   silently.
3. `tools/bin/ttrpg foundry plan`: list what would change, and show it to the
   GM: creations, updates, deletions, adopted adventure actors, the date,
   clocks and map cells. Deletions and anything the GM did not expect need
   their approval.
4. `tools/bin/ttrpg foundry apply`. It refuses while something changed in
   Foundry since the last sync (run `pull` first); `--force` overwrites those
   changes, only when the GM asks for it.
5. Run `plan` again: nothing left to do means the world matches the notes.

## What the notes drive

| In the notes | In the world |
| --- | --- |
| every exported note | a page in its category journal, in the campaign folder; `visibility: players` readable by players |
| npc or item with `stats` (a compendium uuid), npc `adjust` (`elite`, `weak`) | a world copy named as the note |
| npc with `foundry: Actor.<id>` and `owners` (player user names) or `state: dead` | the adventure actor: owners' ownership, a dead status effect; released when the note no longer asks |
| last session `ingame`, else played events, else `campaign.yaml` `start` | the world date (Simple Calendar when active, else the pf2e world clock); never moved back once play moved it on |
| clock `segments` and `filled` | Global Progress Clocks, private unless `visibility: players` |
| map note with `foundry: Scene.<id>` | its pins that open an adventure page whose subject has a campaign note (`km-a23-…` → `a23-…`) open the note's page instead; the original link is kept and restored if the note goes |
| place `discovered: "yes"` | a title-only page in the players' "discovered places" journal (the GM page stays hidden); with `map` and `cells` (`["i_j"]`, World Explorer offsets), those cells revealed |

Only documents the sync created or adopted (they carry `flags.ttrpg`) are
ever changed or deleted; the GM's own journals, actors, clocks and revealed
cells are left alone.
