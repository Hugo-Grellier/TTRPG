"""A campaign repository: campaign.yaml plus Markdown notes with YAML frontmatter."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCHEMA = yaml.safe_load((Path(__file__).parent / "schema.yaml").read_text(encoding="utf-8"))
SKIP_DIRS = {".git", ".cache", ".github", "tools", "node_modules", ".obsidian", ".claude", ".agents"}
SKIP_FILES = {"README.md", "AGENTS.md", "CLAUDE.md"}

WIKILINK = re.compile(r"(!?)\[\[([^\]|#]+)(#[^\]|]*)?(?:\|([^\]]*))?\]\]")
SOURCE = re.compile(r"src:([a-z0-9][a-z0-9-]*)#p(\d+)")
UUID = re.compile(r"@UUID\[([^\]]+)\](?:\{([^}]*)\})?")
MDLINK = re.compile(r"\]\((?!https?:|mailto:|src:|modules/|systems/|#)([^)\s]+)\)")


@dataclass
class Note:
    path: Path
    rel: str
    meta: dict
    body: str
    body_line: int
    error: str = ""

    @property
    def id(self):
        return self.path.stem

    @property
    def type(self):
        return self.meta.get("type")

    def get(self, name):
        """Field value, falling back to the schema default."""
        if name in self.meta:
            return self.meta[name]
        spec = fields_for(self.type).get(name, {})
        return spec.get("default")

    def line_of(self, offset):
        return self.body_line + self.body.count("\n", 0, offset)


@dataclass
class Campaign:
    root: Path
    config: dict
    notes: dict = field(default_factory=dict)
    duplicates: list = field(default_factory=list)
    assets: set = field(default_factory=set)


def fields_for(note_type):
    return {**SCHEMA["common"], **(SCHEMA["types"].get(note_type) or {})}


def body_hash(body):
    return hashlib.sha256(body.strip().encode("utf-8")).hexdigest()[:16]


def split_frontmatter(text):
    """Return (meta, body, body_line, error)."""
    if not text.startswith("---\n"):
        return {}, text, 1, "missing frontmatter"
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text, 1, "unterminated frontmatter"
    try:
        meta = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        return {}, text[end + 5:], 1, f"invalid frontmatter YAML ({exc.problem})"
    if not isinstance(meta, dict):
        return {}, text[end + 5:], 1, "frontmatter is not a mapping"
    return meta, text[end + 5:], text.count("\n", 0, end + 5) + 1, ""


def join_frontmatter(meta, body):
    head = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=1000)
    return f"---\n{head}---\n{body}"


def walk(root):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        if path.is_file():
            yield path, rel


def load(root):
    root = Path(root).resolve()
    config_path = root / "campaign.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.is_file() else None
    campaign = Campaign(root, config or {})
    for path, rel in walk(root):
        if path.suffix != ".md":
            campaign.assets.add(path.name)
            continue
        if path.name in SKIP_FILES and len(rel.parts) == 1:
            continue
        meta, body, body_line, error = split_frontmatter(path.read_text(encoding="utf-8"))
        note = Note(path, rel.as_posix(), meta, body, body_line, error)
        if note.id in campaign.notes:
            campaign.duplicates.append((note, campaign.notes[note.id]))
        else:
            campaign.notes[note.id] = note
    return campaign
