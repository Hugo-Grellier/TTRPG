# Campaign repository

This repository is a tabletop campaign prepared by its GM: one Markdown note
per subject, with YAML frontmatter. `campaign.yaml` sets the game system, the
language every note is written in, the calendar and the cited sources. The
tools live in the `tools/` submodule (repository `TTRPG`); its skills are
linked into `.claude/skills` and `.agents/skills`. If you cannot open the
submodule (web chat), read the same files in the `TTRPG` repository:
`skills/*/SKILL.md` and `ttrpg/schema.yaml`.

## Start of work

With a shell, update the tools first, then check the campaign against them:

```sh
git submodule update --init --remote tools && tools/bin/ttrpg check
```

If the update brings new errors, fix the notes (or tell the GM) and commit
the `tools` bump with the fixes. Dependabot also opens a pull request when
the tools move.

## Rules

- The GM decides. Propose, explain, and edit what you are asked to edit; do
  not invent canon silently. Mark open choices `> [!question]`.
- One subject, one note. The file name is the id (`armag-twice-born.md`),
  unique across the repository. Link with `[[id]]` or `[[id|text]]`, embed
  images with `![[file.png]]`. Never use relative Markdown links.
- Frontmatter follows `tools/ttrpg/schema.yaml`. A relation is written on one
  side only (an NPC lists its `factions`; a faction never lists members).
- `origin: ap` notes are imported adventure text. When you change their body,
  set `origin: modified`. New notes are `origin: custom`.
- `visibility: gm` is the default. A `players` note may only link other
  `players` notes. Inside any note, `> [!secret]` blocks never reach players.
- Cite a source page as `[p. 12](src:km#p12)`; the id must be declared under
  `sources` in `campaign.yaml`. Source PDFs are never committed; a local copy
  of their text may exist in `.cache/sources/<id>/pNNN.txt`.
- Foundry references (`@UUID[Actor...]`, `@UUID[Compendium...]`, `@Check[...]`)
  are kept as written: they become clickable in Foundry.
- In-game dates are quoted `"4710-03-15"` strings; real dates are plain.

## Before you finish

Run `tools/bin/ttrpg check` and fix every error. It runs again as a pre-commit
hook and in CI on every push, so an edit from any tool is checked the same way.
Without a shell (web chat), hand the GM a change that respects the rules above
and say it is unchecked.
