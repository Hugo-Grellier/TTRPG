---
name: foundry-sync
description: Bring the running Foundry world up to date with the campaign notes - journals, actors and items the notes define, NPC ownership and death, the in-game date, clocks, discovered places and their map cells, a pin per place on its region map - and bring back what changed in Foundry during play. Use when the GM asks to update, sync or push the campaign to Foundry, or after a session debrief or any edit the table should see.
---

# Sync the Foundry world

Needs the `foundry-mcp` backend (fork with the `sync-world` tool) running and
a GM browser connected to the world, with the bridge module active there.
`tools/bin/ttrpg foundry` talks to the backend on `127.0.0.1:31414` and says
what is missing: backend not running (it prints the command; one-time setup
in `tools/docs/getting-started.md`), or no GM browser in the world.

Every command prints the world the GM's browser is in. `campaign.yaml` names
the worlds this campaign may sync (`world: <id>` or a list); `apply` and
`pull` refuse another world, and `apply` refuses until one is named. Adding
the id is the GM's decision: show them the world line and ask, never add a
world to get past the refusal.

Images in notes and the hex hover panel are files, served by the campaign's
own module: when `plan` notes that `ttrpg-<id>` is not active, or after
images changed, run `tools/bin/ttrpg export-foundry --install <Foundry
Data/modules>` (or hand the GM `.cache/foundry/ttrpg-<id>/` to copy to the
server) and have the GM enable the module in the world.

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
| note with `map` and `cells`, its map note with `foundry: Scene.<id>` and `grid` (the scene's grid size) | a pin at the centre of its first cell, opening its page; notes sharing a cell sit side by side. Hex columns with odd columns down only (what `map-ready` builds). Foundry shows a pin to the users who can read its page: players see the pins of `visibility: players` notes |
| place `discovered: "yes"` | a title-only page in the players' "discovered places" journal (the GM page stays hidden); with `map` and `cells` (`["i_j"]`, World Explorer offsets), those cells revealed |

Only documents the sync created or adopted (they carry `flags.ttrpg`) are
ever changed or deleted; the GM's own journals, actors, clocks and revealed
cells are left alone.
