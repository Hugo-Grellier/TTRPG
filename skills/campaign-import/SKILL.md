---
name: campaign-import
description: Import an adventure path into a campaign repository from its Foundry module and/or its PDF, then make the imported notes usable. Use when starting a campaign from published material.
---

# Import an adventure

Foundry module (preferred: structured pages, links, actors, scenes):

```sh
tools/bin/ttrpg import-foundry --module /path/to/Data/modules/<module-id>
```

Requires Node and `npm ci` once in `tools/`. Pages land in
`adventure/<journal>/`, typed by `tools/ttrpg/maps/<module-id>.yaml` (add a map
for a new module). Links between pages become `[[id]]`; actors, scenes and
compendium links stay Foundry `@UUID` and are verified against
`.foundry/index.json`. Re-running refreshes untouched AP notes and keeps every
note the GM changed.

PDF (citations and anything the module lacks):

```sh
tools/bin/ttrpg pdf-text km /path/to/Kingmaker.pdf --title "Kingmaker AP"
```

This declares source `km` in `campaign.yaml` and writes page text to
`.cache/sources/km/` (ignored by Git, local only). Cite as `[p. 42](src:km#p42)`.

After an import, run `tools/bin/ttrpg check`, then report counts per type and
what the GM should review first (chapter one, main NPCs). Do not rewrite
imported text in bulk; refinement happens note by note with the GM.
