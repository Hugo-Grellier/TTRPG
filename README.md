# TTRPG campaign tools

Tools for preparing tabletop campaigns kept as plain Markdown in a private Git
repository, editable from any editor, Obsidian, or AI agent, and checked for
coherence on every commit.

```sh
pip install -r requirements.txt && npm ci        # PyYAML; Node only for Foundry import
bin/ttrpg new ../Campaign/campaign-x --name "X" --language fr --tools-url <git url of this repo>
cd ../Campaign/campaign-x
tools/bin/ttrpg import-foundry --module ~/foundrydata/Data/modules/<adventure-module>
tools/bin/ttrpg pdf-text km /path/to/adventure.pdf --title "Adventure"
tools/bin/ttrpg check
tools/bin/ttrpg export-foundry --install ~/foundrydata/Data/modules   # journals module
tools/bin/ttrpg pull-foundry ~/foundrydata/Data/worlds/<world>          # edits made in Foundry -> notes
```

A campaign repository holds `campaign.yaml` (system, language, calendar,
sources), one note per subject (`type`, `title`, typed relations in
frontmatter; `[[id]]` links in the body), assets, and `tools/` as a Git
submodule. Note types and fields are defined in `ttrpg/schema.yaml`; agent
instructions in `template/AGENTS.md` and `skills/`.

After cloning a campaign: `git submodule update --init` and
`git config core.hooksPath .githooks`.
