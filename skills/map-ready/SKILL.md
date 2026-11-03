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
7. Pins (`Note`) on every keyed area, linked to the adventure's page of that
   area (or the campaign note's page), with a short text the GM reads at a
   glance; `ttrpg foundry apply` then points them at the campaign notes.
   A module scene already built (walls, lights, tokens, pins) only needs
   checking against the notes: compare its tokens with each scene note's
   Opposition and report differences to the GM before changing either.

## Region map for hexploration

An `overview` map note for a region the PCs explore hex by hex (no
creatures, no walls):

1. Find the official map with a scale bar in the GM's library:
   `tools/bin/ttrpg library search '^\s*\d+ miles\s*$' --pages` narrowed with
   two place names of the region, then `library page <id> <N>` to look.
   Prefer the largest printing. Community maps (PathfinderWiki's) place
   things well but their distances are not canon: never use them for scale.
2. Render the page at 300 dpi (`pdftoppm -png -r 300 -f N -l N <pdf>`); the
   embedded raster has no place names (they are vector text). Crop to the
   map, keep the scale bar, and save it under the world's
   `Data/worlds/<world>/maps/` (licensed art: never in the repository).
3. Measure the scale bar in pixels (its dark horizontal run). GM Core: a hex
   is 12 miles corner to corner, about a day of travel. For hex columns,
   `gridSize` = round(12 x pixels per mile x sqrt(3) / 2).
4. `create-scene` with `gridType: hex-columns-odd`, that `gridSize`,
   `gridDistance: 12`, `gridUnits: mi`, and the fixed id. Capture it: the
   scale bar should span its miles / 12 hexes.
5. Hex notes are keyed by the Foundry grid offset `"i_j"` (row, column; the
   World Explorer `cells` format): `coord: "23_28"`, `map: <map note>`,
   `cells: ["23_28"]`. A place's hex: its image position plus the scene
   origin (`canvas.dimensions.sceneRect`), through `canvas.grid.getOffset`.
   Check two distances the books give (e.g. "75 miles west of Absalom")
   against the map and write the result in the map note.

## 3. Check and record

- `capture-scene` in `plan` mode: every token, pin and wall where intended,
  nothing left from a reused map. Fix and capture again until it is right.
- `capture-scene` in `view` mode once, to see what the darkness hides.
- Update the map note: Areas, Tokens and Ambience as built; `stage: lit`, or
  `walled` if lighting is still missing. Only the GM sets `ready`, after a
  look or a session.
- Run `tools/bin/ttrpg check`. Report what you built, what you guessed (a
  position the text did not give), and what is left for the GM.
