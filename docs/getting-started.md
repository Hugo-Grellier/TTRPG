# Getting started: from nothing to a synced Foundry world

For a GM who runs their own Foundry VTT (version 14, system pf2e: the only
pair verified so far). You need a computer with `git`, Python 3.11 or later
and, for Foundry, Node 20 or later. Linux and macOS shells are assumed.

The campaign lives in a Git repository of Markdown notes on your computer.
Foundry is a view of it: you prepare in the notes (by hand, in Obsidian, or
by talking to an agent such as Claude Code or Codex), then one command brings
the world up to date, and another brings back what changed during play.

## 1. Create the campaign

```sh
git clone https://github.com/Hugo-Grellier/TTRPG.git ttrpg
python3 -m venv ttrpg/.venv && ttrpg/.venv/bin/pip install -r ttrpg/requirements.txt
ttrpg/bin/ttrpg new campaign-x --name "My campaign" --language fr
cd campaign-x
python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt
tools/bin/ttrpg check          # "0 notes, 0 errors, 0 warnings"
git add -A && git commit -m "Empty campaign"
```

`new` copies the template, writes `campaign.yaml` (its `id` names everything
the tools create in Foundry: never change it once synced) and adds the tools
as the `tools/` submodule, so the campaign always says which version of the
tools it was checked with. From here on only `tools/bin/ttrpg` is used; the
first clone can be deleted. If `python3 -m venv` is missing
(Debian, Ubuntu: `apt install python3-venv`), or with `uv`:
`uv venv tools/.venv && uv pip install --python tools/.venv/bin/python -r tools/requirements.txt`.
A tool that lacks its packages prints the install line itself.

Keep the repository private (GitHub, a NAS, or no remote at all): it holds
your secrets and text from books you own.

## 2. Write notes

Open the campaign folder with your agent and describe what you want; the
instructions it follows are `AGENTS.md` and the skills in `tools/skills/`.
By hand: one note per subject, in the folder of its type (`npcs/`,
`places/`, `scenes/`…), with the frontmatter `tools/ttrpg/note-types.md`
describes. Notes are GM-only unless they say `visibility: players`.

`tools/bin/ttrpg check` says what is incoherent (a link to a note that does
not exist, a secret in a players' note, a date out of order). It runs on
every commit; a commit with errors is refused.

For a published adventure you own as a Foundry module:
`tools/bin/ttrpg import-foundry --module <Foundry Data>/modules/<module>`
(needs `npm ci` in `tools/`).

## 3. Connect Foundry, once

The sync talks to the world through your browser: a small program on your
computer (the backend) and a Foundry module (the bridge) that connects your
GM session to it. Both come from a fork of foundry-vtt-mcp that adds the sync.

1. **Bridge module.** In Foundry's setup screen, *Install Module*, paste the
   manifest URL
   `https://github.com/Hugo-Grellier/foundry-vtt-mcp/releases/latest/download/module.json`
   and install. Do not pick "Foundry MCP Bridge" from Foundry's module list
   instead: that one has no sync. Then enable the module in your world
   (*Manage Modules*). Its default settings are the right ones.
2. **Backend.** On your computer, once:

   ```sh
   git clone --branch feat/sync-world https://github.com/Hugo-Grellier/foundry-vtt-mcp.git
   cd foundry-vtt-mcp && npm ci && npm run build
   ```

   then, each time you want to sync:
   `node foundry-vtt-mcp/packages/mcp-server/dist/backend.js`
   and leave it running. (Claude Code configured with the foundry-mcp server
   starts it by itself.)
3. **Your browser.** Log in to the world as a GM, on the same computer as
   the backend, and keep the tab open. A notification says the bridge is
   connected. Only a GM session is accepted; players' browsers are refused.
4. **Name the world.** `tools/bin/ttrpg foundry plan` prints the world your
   browser is in. Add its id to `campaign.yaml`:

   ```yaml
   world: my-world            # or a list: [my-world, my-test-world]
   ```

   `apply` and `pull` refuse any other world, so a browser left in the wrong
   world cannot receive this campaign.

## 4. Images and the hex panel

The sync carries documents (journals, actors, pins, the date, clocks). Files
do not travel that way: images embedded in notes and the hex hover panel are
served by a small Foundry module built from the campaign.

```sh
tools/bin/ttrpg export-foundry --install <Foundry Data>/modules
```

then enable `ttrpg-<campaign id>` in the world, once. Run the command again
when you add or change images. If Foundry runs on another machine, build
without `--install` and copy `.cache/foundry/ttrpg-<id>/` to the server's
`Data/modules/`. `plan` reminds you while the module is not active.

## 5. The loop

```sh
tools/bin/ttrpg check            # zero errors
tools/bin/ttrpg foundry pull     # what changed in Foundry comes back into the notes; read the git diff
tools/bin/ttrpg foundry plan     # what would change in the world; changes nothing
tools/bin/ttrpg foundry apply    # do it
tools/bin/ttrpg foundry plan     # all zeros: the world matches the notes
```

Before a session: the loop. After a session: `pull` (pages you edited at
the table, clocks you moved), then your debrief (`docs/after-session.md` for
the recorded-session pipeline), then the loop again.

What the notes drive in the world is listed in
`tools/skills/foundry-sync/SKILL.md`. The sync only ever changes or deletes
what it created or adopted; your own journals, actors and scenes are left
alone. If a page was edited in Foundry since the last sync, `apply` refuses
until you `pull`; when both sides changed, the notes win and the conflict is
reported.

## 6. First sync of a world your players use

1. Back up the world (Foundry's setup screen, or a copy of
   `Data/worlds/<world>` while the world is stopped).
2. `plan` first. Check the `world:` line it prints, read the list. Nothing
   is written by `plan`.
3. `apply` when no player is connected, the first time: it creates a
   campaign folder with one journal per note category, and moves the world
   date to the campaign's.
4. Log in as a player (a second browser profile) and look: players see the
   pages and pins of `visibility: players` notes only.

## Limits to know

- **Curious players.** Foundry sends every journal to every connected
  browser and only hides what a player may not open. A player who opens the
  browser's developer console can read GM pages, as with any journal a GM
  writes in Foundry. Every note is synced (except untouched adventure text),
  by choice: the tools assume a table where the GM trusts the players not to
  go looking.
- Verified with Foundry 14 and pf2e 8.6 only. Clocks need the module Global
  Progress Clocks; the date uses Simple Calendar Reborn when active, else
  the pf2e world clock; revealed map cells need World Explorer.
- Map pins are placed on hex maps with columns, odd columns down (what the
  `map-ready` skill builds).
- One GM browser at a time should be connected to the backend.
