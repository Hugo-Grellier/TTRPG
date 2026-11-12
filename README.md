# TTRPG campaign tools

Tools for preparing tabletop campaigns kept as plain Markdown in a private Git
repository, editable from any editor, Obsidian, or AI agent, and checked for
coherence on every commit.

A GM starting from nothing follows `docs/getting-started.md` (install,
first campaign, connecting Foundry, the sync loop, first sync of a world the
players use).

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && npm ci   # Node only for Foundry import
bin/ttrpg new ../Campaign/campaign-x --name "X" --language fr
cd ../Campaign/campaign-x
tools/bin/ttrpg import-foundry --module ~/foundrydata/Data/modules/<adventure-module>
tools/bin/ttrpg pdf-text km /path/to/adventure.pdf --title "Adventure"
tools/bin/ttrpg library index ~/pdfs/Pathfinder         # once: every PDF the GM owns, shared by all campaigns
tools/bin/ttrpg library search "Westerhold" --pages     # which books and pages mention it
tools/bin/ttrpg source add absalom-city-of-lost-omens   # declare a book; cite as src:<id>#p<N>
tools/bin/ttrpg source excerpts                          # commit the cited pages' text in sources/ for agents without the library
tools/bin/ttrpg aon Dahak                               # Archives of Nethys: book, page, URL, legacy/remaster
tools/bin/ttrpg creatures --index ~/foundrydata/Data/systems/pf2e   # once: index of the system's bestiaries
tools/bin/ttrpg creatures --party-level 2 --trait undead  # creatures, their XP for the party, compendium links
tools/bin/ttrpg hexmap --control "Absalom=1346,1272" ... # PathfinderWiki's places onto an official map's hexes
tools/bin/ttrpg check
tools/bin/ttrpg export-foundry --install ~/foundrydata/Data/modules   # journals module
tools/bin/ttrpg pull-foundry ~/foundrydata/Data/worlds/<world>          # edits made in Foundry -> notes
tools/bin/ttrpg foundry plan|apply|pull   # live sync of a running world through foundry-mcp (skill foundry-sync)
```

A campaign repository holds `campaign.yaml` (system, language, calendar,
sources), one note per subject (`type`, `title`, typed relations in
frontmatter; `[[id]]` links in the body), assets, and `tools/` as a Git
submodule. Note types and fields are defined in `ttrpg/schema.yaml`; agent
instructions in `template/AGENTS.md` and `skills/`.

After cloning a campaign: `git submodule update --init` and
`git config core.hooksPath .githooks`.
