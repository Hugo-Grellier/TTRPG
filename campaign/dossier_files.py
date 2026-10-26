"""Private Markdown campaign documents, editable in any text editor."""

import re
import json
from pathlib import Path

from .core import DomainError


LINK = re.compile(r"\]\(([^)#]+\.md)(#[^)]+)?\)")
SOURCE = re.compile(r"\]\(source:pdf/(\d+)/(\d+)#L(\d+)\)")
SOURCE_REF = re.compile(r"source:pdf/(\d+)/(\d+)#L(\d+)")
VISUAL = re.compile(r"\]\(visual:([a-zA-Z0-9][a-zA-Z0-9_-]*\.png)\)")


def dossier_root(db, campaign_id):
    row = db.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if row is None:
        raise DomainError("error.item_missing")
    database_file = Path(db.execute("PRAGMA database_list").fetchone()["file"]).resolve()
    return database_file.parent / f"dossier-{campaign_id}"


def dossier_documents(db, campaign_id):
    root = dossier_root(db, campaign_id)
    if not root.is_dir():
        return []
    present = set()
    for path in sorted(root.rglob("*.md")):
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            continue
        relative = path.relative_to(root).as_posix()
        present.add(relative)
        with db:
            db.execute("INSERT OR IGNORE INTO campaign_files(campaign_id,path) VALUES(?,?)", (campaign_id, relative))
    return [row for row in db.execute("SELECT id,path FROM campaign_files WHERE campaign_id=? ORDER BY path", (campaign_id,))
            if row["path"] in present]


def dossier_document(db, campaign_id, file_id):
    row = db.execute("SELECT id,path FROM campaign_files WHERE campaign_id=? AND id=?", (campaign_id, file_id)).fetchone()
    if row is None:
        raise DomainError("error.item_missing")
    root = dossier_root(db, campaign_id).resolve()
    path = (root / row["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix != ".md":
        raise DomainError("error.item_missing")
    return row, path.read_text(encoding="utf-8"), path


def document_title(relative, content):
    return next((line[2:].strip() for line in content.splitlines() if line.startswith("# ")), Path(relative).stem)


def linked_markdown(db, campaign_id, file_id, content):
    row, _, _ = dossier_document(db, campaign_id, file_id)
    paths = {item["path"]: item["id"] for item in dossier_documents(db, campaign_id)}
    def link(match):
        target = (Path(row["path"]).parent / match[1]).as_posix()
        target = Path(target)
        # Path.resolve is unavailable for an unsaved relative target; normalize without allowing traversal.
        parts = []
        for part in target.parts:
            if part == "..":
                if not parts:
                    return match[0]
                parts.pop()
            elif part != ".":
                parts.append(part)
        other = paths.get("/".join(parts))
        return f"](/workspace/{campaign_id}?doc=campaign_files:{other}{match[2] or ''})" if other else match[0]
    content = LINK.sub(link, content)
    content = SOURCE.sub(lambda m: f"](/workspace/{campaign_id}?doc=library_documents:{m[1]}&page={m[2]}#L{m[3]})", content)
    return VISUAL.sub(lambda m: f"](/campaign/{campaign_id}/visual/{m[1]})", content)


def visual_file(db, campaign_id, filename):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*\.png", filename):
        raise DomainError("error.item_missing")
    root = (dossier_root(db, campaign_id) / "assets").resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise DomainError("error.item_missing")
    return path


def bible_element_texts(db, campaign_id):
    """Stable review targets for the private visual home."""
    path = dossier_root(db, campaign_id) / "bible.json"
    if not path.is_file():
        return {}
    try:
        bible = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(bible, dict):
        return {}
    elements = {"hero": f'{bible.get("title", "")} — {bible.get("lead", "")}' }
    for item in bible.get("state", []):
        elements[f'state:{item["label"]}'] = f'{item["label"]} — {item["text"]}'
    for group in ("stakes", "scenes", "people"):
        for item in bible.get(group, []):
            elements[f'{group}:{item["file"]}'] = f'{item["title"]} — {item.get("summary", "")}'
    for item in bible.get("relations", {}).get("nodes", []):
        elements[f'relation:{item["file"]}'] = item["label"]
    if bible.get("map_file"):
        elements[f'map:{bible["map_file"]}'] = bible.get("map_alt", "Carte")
    for row in db.execute("SELECT id,text FROM facts WHERE campaign_id=?", (campaign_id,)):
        elements[f'fact:{row["id"]}'] = row["text"]
    return elements


def backlinks(db, campaign_id, file_id):
    target, _, _ = dossier_document(db, campaign_id, file_id)
    found = []
    # ponytail: scan private sheets on demand; index links if a full AP makes this slow.
    for row in dossier_documents(db, campaign_id):
        if row["id"] == file_id:
            continue
        source, text, _ = dossier_document(db, campaign_id, row["id"])
        for link in LINK.finditer(text):
            resolved = (Path(source["path"]).parent / link[1]).as_posix()
            parts = []
            for part in Path(resolved).parts:
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            if "/".join(parts) == target["path"]:
                found.append((row["id"], document_title(row["path"], text)))
                break
    return found


def init_dossier(db, campaign_id):
    """Create a small private starting set for an original campaign."""
    root = dossier_root(db, campaign_id)
    repository = Path(__file__).resolve().parent.parent
    if root.resolve().is_relative_to(repository):
        raise ValueError("Campaign documents must stay outside the source repository")
    root.mkdir(parents=True, exist_ok=True)
    language = db.execute("SELECT language FROM campaigns WHERE id=?", (campaign_id,)).fetchone()["language"]
    french = language == "fr"
    templates = {
        "00-Commencer.md": "# Commencer\n\n> Préparation privée · proposition MJ.\n\n## Prochaine séance\n\nÀ définir.\n\n## Navigation\n\n[Enjeux](01-Enjeux.md) · [Relations](02-Relations.md) · [Chronologie](03-Chronologie.md)\n" if french else
                            "# Start here\n\n> Private GM preparation · proposal.\n\n## Next session\n\nTo define.\n\n## Navigate\n\n[Stakes](01-Enjeux.md) · [Relations](02-Relations.md) · [Timeline](03-Chronologie.md)\n",
        "01-Enjeux.md": "# Enjeux\n\n## Situation\n\nÀ définir.\n\n## Ce qui peut changer\n\nÀ définir.\n" if french else
                       "# Stakes\n\n## Situation\n\nTo define.\n\n## What can change\n\nTo define.\n",
        "02-Relations.md": "# Relations\n\nDécrire chaque lien, son enjeu et les fiches concernées.\n" if french else
                          "# Relations\n\nDescribe each link, its stakes, and the relevant sheets.\n",
        "03-Chronologie.md": "# Chronologie provisoire\n\nDistinguer le passé du scénario, les possibilités futures et les événements réellement joués.\n" if french else
                            "# Provisional timeline\n\nSeparate scenario backstory, possible future events, and events actually played.\n",
    }
    for relative, content in templates.items():
        path = root / relative
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    dossier_documents(db, campaign_id)
    return root


def validate_dossier(db, campaign_id):
    """Report broken private sheet links, visuals, and invalid PDF locators."""
    root = dossier_root(db, campaign_id)
    problems = []
    for row in dossier_documents(db, campaign_id):
        _, content, _ = dossier_document(db, campaign_id, row["id"])
        problems.extend(document_problems(db, campaign_id, row["path"], content))
    manifest = root / "bible.json"
    if manifest.is_file():
        try:
            bible = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(bible, dict) or not all(key in bible for key in ("title", "lead")):
                raise ValueError("missing title or lead")
        except (OSError, ValueError) as exc:
            problems.append(f'bible.json: invalid presentation manifest ({exc})')
        else:
            items = [bible] + bible.get("stakes", []) + bible.get("scenes", []) + bible.get("people", []) + bible.get("relations", {}).get("nodes", [])
            paths = {row["path"] for row in dossier_documents(db, campaign_id)}
            for item in items:
                for key in ("file", "map_file"):
                    if item.get(key) and item[key] not in paths:
                        problems.append(f'bible.json: missing sheet {item[key]}')
                for key in ("image", "map"):
                    if item.get(key):
                        try:
                            visual_file(db, campaign_id, item[key])
                        except DomainError:
                            problems.append(f'bible.json: missing visual {item[key]}')
    return problems


def document_problems(db, campaign_id, relative, content):
    """Validate one saved or proposed sheet against this campaign's private dossier."""
    root = dossier_root(db, campaign_id).resolve()
    parent = (root / relative).parent
    problems = []
    for match in LINK.finditer(content):
        target = (parent / match[1]).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            problems.append(f'{relative}: missing sheet {match[1]}')
    for match in SOURCE_REF.finditer(content):
        document_id, page_number, line_number = map(int, match.groups())
        page = db.execute("SELECT text FROM library_pages WHERE campaign_id=? AND document_id=? AND pdf_page=?",
                          (campaign_id, document_id, page_number)).fetchone()
        if page is None or not 1 <= line_number <= len(page["text"].splitlines()):
            problems.append(f'{relative}: invalid PDF locator {match[0]}')
    for match in VISUAL.finditer(content):
        try:
            visual_file(db, campaign_id, match[1])
        except DomainError:
            problems.append(f'{relative}: missing visual {match[1]}')
    return problems
