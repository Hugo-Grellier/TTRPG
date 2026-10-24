"""Editable preparation drafts stay private until the GM accepts them."""

from difflib import unified_diff

from .agent_cli import draft_checkout
from .core import DomainError
from .paths import data_dir
from .store import revise_preparation


SITUATION_START = "<!-- field:situation -->"
SITUATION_END = "<!-- /field:situation -->"
ALTERNATIVES_START = "<!-- field:alternatives -->"
ALTERNATIVES_END = "<!-- /field:alternatives -->"


def _current(db, campaign_id, preparation_id):
    row = db.execute("SELECT situation, alternatives FROM preparations WHERE id=? AND campaign_id=?",
                     (preparation_id, campaign_id)).fetchone()
    if row is None:
        raise DomainError("error.item_missing")
    return row


def _render(preparation_id, situation, alternatives):
    return (f"# Preparation #{preparation_id}\n\n"
            f"## Situation\n\n{SITUATION_START}\n{situation.strip()}\n{SITUATION_END}\n\n"
            f"## Alternatives\n\n{ALTERNATIVES_START}\n{alternatives.strip()}\n{ALTERNATIVES_END}\n")


def _paths(campaign_id, preparation_id):
    draft = data_dir() / "drafts" / f"campaign-{campaign_id}" / "data" / "preparations" / f"preparation-{preparation_id}.md"
    baseline = data_dir() / "draft-baselines" / f"campaign-{campaign_id}" / f"preparation-{preparation_id}.md"
    return draft, baseline


def ensure_preparation_draft(db, campaign_id, preparation_id):
    row = _current(db, campaign_id, preparation_id)
    checkout = draft_checkout(campaign_id)
    path, baseline = _paths(campaign_id, preparation_id)
    if not path.resolve().is_relative_to(checkout.resolve()):
        raise DomainError("error.draft_conflict")
    if not path.exists():
        content = _render(preparation_id, row["situation"], row["alternatives"])
        path.parent.mkdir(parents=True, exist_ok=True)
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(content, encoding="utf-8")
        path.write_text(content, encoding="utf-8")
    elif not baseline.is_file():
        raise DomainError("error.draft_conflict")
    return path


def _fields(content):
    try:
        situation = content.split(SITUATION_START, 1)[1].split(SITUATION_END, 1)[0].strip()
        alternatives = content.split(ALTERNATIVES_START, 1)[1].split(ALTERNATIVES_END, 1)[0].strip()
    except IndexError as exc:
        raise DomainError("error.draft_format") from exc
    if not situation or not alternatives:
        raise DomainError("error.draft_format")
    return situation, alternatives


def preparation_draft_review(db, campaign_id, preparation_id):
    row = _current(db, campaign_id, preparation_id)
    path, baseline = _paths(campaign_id, preparation_id)
    if not path.exists() and not baseline.exists():
        return None
    if not path.is_file() or not baseline.is_file():
        raise DomainError("error.draft_conflict")
    if not path.resolve().is_relative_to((data_dir() / "drafts" / f"campaign-{campaign_id}").resolve()):
        raise DomainError("error.draft_conflict")
    base = baseline.read_text(encoding="utf-8")
    proposed = path.read_text(encoding="utf-8")
    current = _render(preparation_id, row["situation"], row["alternatives"])
    try:
        fields = _fields(proposed) if proposed != base else None
        if fields and proposed != _render(preparation_id, *fields):
            fields = None
    except DomainError:
        fields = None
    status = "unchanged" if proposed == base else "invalid" if fields is None else "ready" if current == base else "applied" if current == proposed else "conflict"
    diff = "".join(unified_diff(base.splitlines(True), proposed.splitlines(True),
                                fromfile="current preparation", tofile="draft preparation"))
    return {"path": path, "status": status, "diff": diff[:30000], "fields": fields}


def apply_preparation_draft(db, campaign_id, preparation_id):
    review = preparation_draft_review(db, campaign_id, preparation_id)
    if review is None or review["status"] == "unchanged":
        raise DomainError("error.draft_missing")
    if review["status"] == "invalid":
        raise DomainError("error.draft_format")
    if review["status"] != "ready":
        raise DomainError("error.draft_conflict")
    revise_preparation(db, campaign_id, preparation_id, *review["fields"])


def restart_preparation_draft(db, campaign_id, preparation_id):
    review = preparation_draft_review(db, campaign_id, preparation_id)
    if review is None or review["status"] != "applied":
        raise DomainError("error.draft_conflict")
    row = _current(db, campaign_id, preparation_id)
    content = _render(preparation_id, row["situation"], row["alternatives"])
    path, baseline = _paths(campaign_id, preparation_id)
    baseline.write_text(content, encoding="utf-8")
    path.write_text(content, encoding="utf-8")
