"""Rename notes and rewrite every link to them, in bodies and frontmatter."""

import re
from pathlib import Path

from . import vault


def relink(root, renames):
    """Rewrite [[old]] links and frontmatter references for every old -> new id. Returns files changed."""
    if not renames:
        return 0
    pattern = re.compile(r"(\[\[)(" + "|".join(map(re.escape, sorted(renames, key=len, reverse=True))) + r")(?=[\]|#])")
    changed = 0
    for path, _ in vault.walk(Path(root)):
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        meta, body, _, error = vault.split_frontmatter(text)
        new_body = pattern.sub(lambda m: m[1] + renames[m[2]], body)
        new_meta = {key: swap(value, renames) for key, value in meta.items()}
        if new_body == body and new_meta == meta:
            continue
        if meta.get("source_hash") == vault.body_hash(body):
            new_meta["source_hash"] = vault.body_hash(new_body)  # relinking is not a GM edit
        path.write_text(vault.join_frontmatter(new_meta, new_body) if not error else pattern.sub(lambda m: m[1] + renames[m[2]], text), encoding="utf-8")
        changed += 1
    return changed


def swap(value, renames):
    if isinstance(value, list):
        return [swap(item, renames) for item in value]
    if isinstance(value, str):
        inner = value[2:-2].split("|")[0] if value.startswith("[[") and value.endswith("]]") else value
        if inner in renames:
            return value.replace(inner, renames[inner], 1)
    return value


def rename(root, old, new):
    campaign = vault.load(root)
    note = campaign.notes.get(old)
    if note is None:
        raise SystemExit(f"no note {old!r}")
    if new in campaign.notes:
        raise SystemExit(f"{new!r} already exists ({campaign.notes[new].rel})")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", new):
        raise SystemExit("ids are lowercase ASCII letters, digits and dashes")
    note.path.rename(note.path.with_name(f"{new}.md"))
    return relink(root, {old: new})
