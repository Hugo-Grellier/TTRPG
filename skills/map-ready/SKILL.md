---
name: map-ready
description: Make a Foundry scene ready to play from a campaign map note and its encounters - scene, walls, tokens, lights, sounds and pins - through the Foundry MCP scene tools, checked visually. Use when the GM asks to prepare, build or finish a map or battle scene.
---

# Make a map ready to play

Needs the `foundry-mcp` server (fork with `create-scene`, `scene-documents`,
`capture-scene`) and a GM browser connected to the world. Without it, stop and
say so: this skill does not edit Foundry by other means.

## 1. Read the campaign side

- The `map` note (`maps/map-*.md`): `foundry` scene id, `image`, `stage`,
  `locations`, and its Areas, Tokens and Ambience sections.
- Every place and scene note it covers (its `locations`, and notes whose body
  links `[[map-…]]`): who is there, hidden or not, what the PCs see first,
  time of day, light sources, sounds, traps, doors, secrets.
- For each creature: the `@UUID[Actor...]` in its note or encounter. Adventure
  actors are `<Adventure uuid>.Actor.<id>`; module scenes are
  `<Adventure uuid>.Scene.<id>`.

No map yet (`ttrpg maps` lists places with creatures and no battle map):
propose one to the GM - a fitting module scene to copy, or an image to use -
before building anything.

## 2. Build

1. Scene: copy with `create-scene` (`sourceUuid`) or create from `image`.
   Name it after the place (`GB12. Tuskgutter's Lair`) and give it a fixed
   `id`: 16 letters/digits derived from the map note id (`python3 -c "from
   ttrpg.foundry_export import foundry_id; print(foundry_id('ttrpg-<campaign>',
   'scene', '<map note id>'))"` run in `tools/`), so the scene has the same id in
   every world and exported links to it keep working.
2. `capture-scene` (plan) and look at it before placing anything. Coordinates
   are image pixels: pixel in the capture / `pixelsPerImagePixel`.
3. Remove what does not belong (tokens and pins of a reused generic map).
4. Walls: keep the module's; on a bare image, wall the edges that block
   movement and sight, doors as `door: 1`, secret doors `door: 2`. Check the
   result in a capture before going on.
5. Tokens with `actorUuid`, at the positions the text gives; hidden (`hidden:
   true`) if the PCs should not see them on arrival. On outdoor maps, bushes
   and forest edges are walled: a yellow outline in the plan capture blocks
   sight. Measure the open ground in the capture before placing, and never put
   a token or pin inside an outline unless the text hides it there.
6. Ambience: darkness for the time of day (`create-scene` `darkness`), a light
   per fire or lamp the text mentions, ambient sounds that fit (look in the
   module's `assets/audio-*` paths first), with `darkness: {min, max}` for
   sounds that only play at night.
7. Pins (`Note`) on every keyed area, each linked to its journal page when the
   campaign is exported, with a short text the GM reads at a glance.

## 3. Check and record

- `capture-scene` in `plan` mode: every token, pin and wall where intended,
  nothing left from a reused map. Fix and capture again until it is right.
- `capture-scene` in `view` mode once, to see what the darkness hides.
- Update the map note: Areas, Tokens and Ambience as built; `stage: lit`, or
  `walled` if lighting is still missing. Only the GM sets `ready`, after a
  look or a session.
- Run `tools/bin/ttrpg check`. Report what you built, what you guessed (a
  position the text did not give), and what is left for the GM.
