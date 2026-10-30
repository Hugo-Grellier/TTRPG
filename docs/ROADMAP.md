# Roadmap

Each step is usable on its own. Kingmaker (Foundry module + PDF) and Age of
Ashes (converted pilot) are the test campaigns, in
`~/dev/personal/Campaign/campaign-*`.

## Done

### 1 — Campaign repositories and checker (October 30, 2026)
Schema, checker, Foundry Adventure importer, PDF source extraction, campaign
template (AGENTS.md, skills, pre-commit hook, CI), both campaigns created.

## Next

### 2 — Export to Foundry journals
Generate a module whose compendium pack holds one JournalEntry per folder and
one page per note (Markdown → HTML, `[[id]]` → `@UUID`, GM secrets kept GM-only,
player notes with player ownership). Verify in the local Foundry
(`foundry-local-1`, port 30001) with Kingmaker imported alongside. Then live
edits through foundry-vtt-mcp.

### 3 — Foundry changes back to the repository
Read world journals (pack or MCP), turn changed pages back into Markdown,
write them over the notes and leave the diff for GM review. Repository wins a
conflict.

### 4 — Verify remote agents
Push the tools and campaign repositories (owner approval), confirm that Claude
Code on the web and Codex cloud clone the submodule and run the checker, and
that the ChatGPT GitHub connector can read both repositories. Fallback if
submodules fail: CI copies `skills/` into the campaign.

### 5 — After-session pipeline
Per-speaker Discord recording (start from the LoreForge
`experiments/discord-receive-timing-probe`), local faster-whisper
transcription, Foundry Flight Recorder (`ffr`) summary, GM note → proposed
note updates as a diff.

### Later
Player-facing export (only `players` notes, secrets stripped), a read-only
viewer if Foundry and Obsidian are not enough, French translation of imported
AP text on demand, original-campaign starter (factions, fronts, clocks).
