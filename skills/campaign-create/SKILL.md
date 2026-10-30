---
name: campaign-create
description: Build original campaign material with the GM - a sandbox from a pitch, or a new region, faction, settlement or threat added to any campaign, imported or not. Use when the GM wants to invent rather than import.
---

# Create campaign material

Works the same in an empty sandbox and in a campaign built from an adventure:
created notes are `origin: custom` and sit beside any `adventure/` text.

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
   language. A `notes/00-pitch.md` with the pitch, themes and lines/veils.
2. **Map** - one `region` per area, then `hex`, `settlement` or `location`
   notes for what the PCs can reach in the first sessions. Each place gets
   at least one reason to go there.
3. **Factions** - three to five, each with a goal that collides with another
   and a `clock` (four to eight segments) for what it does if the PCs do
   nothing.
4. **People** - for each faction a leader and one or two faces, plus NPCs who
   live in the starting places. Every NPC wants something.
5. **Hooks** - `quest` notes (rumors, jobs, threats) that send the PCs toward
   the factions. More hooks than the party can follow.
6. **Opening** - the first `scene` and a `session-prep` note from the
   `session-prep` skill.

Notes follow `tools/ttrpg/schema.yaml` (fields) and `tools/ttrpg/note-types.md`
(sections). Statistics are Foundry compendium links (`@UUID[Compendium...]`)
chosen by level, never invented stat blocks.

## Rules

- The GM decides. Do what was asked at the scale asked: one tavern is one
  note, not a district.
- Keep it playable: every note answers "what do I do with this at the table?"
- Write what is true in `> [!secret]` blocks when the players would learn it
  through play.
- Run `tools/bin/ttrpg check`, then summarize what exists, how it connects,
  and the open `> [!question]`s.
