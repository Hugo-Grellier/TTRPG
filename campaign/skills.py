"""Discover locally installed skills for the conversation composer."""

from pathlib import Path

from .agent_cli import ROOT


def available_skills():
    home = Path.home()
    roots = (
        (home / ".agents/skills", "Shared", False),
        (home / ".codex/skills", "Codex", False),
        (home / ".claude/skills", "Claude", False),
        (ROOT / ".agents/skills", "Project", False),
        (ROOT / ".claude/skills", "Project", False),
        (home / ".codex/plugins/cache", "Plugin", True),
        (home / ".claude/skills/synced", "Claude", True),
    )
    found = {}
    for root, origin, recursive in roots:
        if not root.is_dir():
            continue
        manifests = root.rglob("SKILL.md") if recursive else (entry / "SKILL.md" for entry in root.iterdir() if not entry.name.startswith("."))
        for manifest in manifests:
            if not manifest.is_file() or "/.trash/" in str(manifest):
                continue
            try:
                lines = manifest.read_text(encoding="utf-8")[:5000].splitlines()
            except OSError:
                continue
            if not lines or lines[0] != "---":
                continue
            name, description, collecting = "", "", False
            for line in lines[1:]:
                if line == "---":
                    break
                if line.startswith("name:"):
                    name = line.partition(":")[2].strip().strip('"\'')
                    collecting = False
                elif line.startswith("description:"):
                    description = line.partition(":")[2].strip().strip('"\'')
                    collecting = description in (">", "|")
                    if collecting:
                        description = ""
                elif collecting and line.startswith("  "):
                    description += " " + line.strip()
                elif collecting and line and not line.startswith(" "):
                    collecting = False
            if name and name not in found:
                found[name] = (name, description.strip()[:180], origin)
    return sorted(found.values(), key=lambda item: item[0].casefold())
