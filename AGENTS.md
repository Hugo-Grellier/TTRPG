# Agent entry point

This repository is the campaign toolset, not a campaign. `VISION.md` holds the
product direction (change it only on an explicit owner decision),
`docs/ROADMAP.md` the next steps, `docs/STATE.md` where work stopped,
`docs/GOTCHAS.md` rules learned from owner corrections. Read GOTCHAS before
starting.

**“Continue the roadmap”**: read `docs/STATE.md` and the first step under Next
in `docs/ROADMAP.md`, build it, verify it on the real campaigns in
`~/dev/personal/Campaign/`, and update STATE.

## Layout

- `ttrpg/`: Python package (`bin/ttrpg` runs it). `schema.yaml` is the single
  definition of note types; `check.py` enforces it; `maps/<module>.yaml` types
  imported Foundry journals.
- `skills/`: agent skills, linked into every campaign's `.claude/skills` and
  `.agents/skills`. Write them for agents that only see the campaign.
- `template/`: files copied by `ttrpg new` into a campaign.

## Rules

- No licensed or private campaign content in this repository; tests use
  invented data.
- Campaign files stay readable and editable by hand. Prefer a checker rule
  over a tool that writes for the GM.
- `make check` passes before you finish; run changed tools against both real
  campaigns (`git submodule update --remote tools && tools/bin/ttrpg check`
  in each) before pushing, since every campaign picks up `main`. A schema
  change that invalidates notes ships with the fix or a migration note. Say plainly what was not verified.
- Fix structure, not symptoms; one source of truth; build what is needed now.
  Match the surrounding code. Commit in small steps; push only when told.
- After two failed attempts at a fix, stop and say where your model was wrong.
