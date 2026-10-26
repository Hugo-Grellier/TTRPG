"""Private campaign sheet drafts edited in the isolated CLI checkout."""

import os
import tempfile
from difflib import unified_diff
from pathlib import Path

from .agent_cli import draft_checkout
from .core import DomainError
from .dossier_files import document_problems, dossier_document
from .paths import data_dir


def _paths(campaign_id, file_id):
    checkout = data_dir() / "drafts" / f"campaign-{campaign_id}"
    proposal = checkout / "data" / "campaign-files" / f"sheet-{file_id}.md"
    baseline = data_dir() / "draft-baselines" / f"campaign-{campaign_id}" / f"sheet-{file_id}.md"
    return checkout, proposal, baseline


def ensure_campaign_file_draft(db, campaign_id, file_id):
    _, content, _ = dossier_document(db, campaign_id, file_id)
    checkout = draft_checkout(campaign_id)
    root, proposal, baseline = _paths(campaign_id, file_id)
    if (checkout.resolve() != root.resolve() or not proposal.resolve().is_relative_to(checkout.resolve())
            or baseline.is_symlink() or not baseline.resolve().is_relative_to((data_dir() / "draft-baselines").resolve())):
        raise DomainError("error.draft_conflict")
    if proposal.exists() or baseline.exists():
        if not proposal.is_file() or not baseline.is_file() or proposal.is_symlink() or baseline.is_symlink():
            raise DomainError("error.draft_conflict")
    else:
        proposal.parent.mkdir(parents=True, exist_ok=True)
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(content, encoding="utf-8")
        proposal.write_text(content, encoding="utf-8")
    return proposal


def campaign_file_draft_review(db, campaign_id, file_id):
    row, current, _ = dossier_document(db, campaign_id, file_id)
    checkout, proposal, baseline = _paths(campaign_id, file_id)
    if not proposal.exists() and not baseline.exists():
        return None
    if (not proposal.is_file() or not baseline.is_file() or proposal.is_symlink() or baseline.is_symlink()
            or not proposal.resolve().is_relative_to(checkout.resolve())
            or not baseline.resolve().is_relative_to((data_dir() / "draft-baselines").resolve())):
        raise DomainError("error.draft_conflict")
    if proposal.stat().st_size > 1_000_000:
        raise DomainError("error.campaign_draft_invalid")
    try:
        base = baseline.read_text(encoding="utf-8")
        proposed = proposal.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise DomainError("error.campaign_draft_invalid") from exc
    problems = document_problems(db, campaign_id, row["path"], proposed) if proposed != base else []
    if proposed != base and not any(line.startswith("# ") for line in proposed.splitlines()):
        problems.append("Missing Markdown title")
    status = ("unchanged" if proposed == base else "invalid" if problems else
              "ready" if current == base else "applied" if current == proposed else "conflict")
    diff = "".join(unified_diff(base.splitlines(True), proposed.splitlines(True),
                                fromfile=row["path"], tofile="proposed sheet"))
    return {"path": proposal, "status": status, "diff": diff[:30000], "problems": problems,
            "base": base, "proposed": proposed, "source": row["path"]}


def apply_campaign_file_draft(db, campaign_id, file_id):
    review = campaign_file_draft_review(db, campaign_id, file_id)
    if review is None or review["status"] == "unchanged":
        raise DomainError("error.draft_missing")
    if review["status"] == "invalid":
        raise DomainError("error.campaign_draft_invalid")
    if review["status"] != "ready":
        raise DomainError("error.draft_conflict")
    _, _, target = dossier_document(db, campaign_id, file_id)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, mode="w", encoding="utf-8") as temporary:
        temporary.write(review["proposed"])
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(target.stat().st_mode)
        if target.read_text(encoding="utf-8") != review["base"]:
            raise DomainError("error.draft_conflict")
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def restart_campaign_file_draft(db, campaign_id, file_id):
    review = campaign_file_draft_review(db, campaign_id, file_id)
    if review is None or review["status"] != "applied":
        raise DomainError("error.draft_conflict")
    _, content, _ = dossier_document(db, campaign_id, file_id)
    _, proposal, baseline = _paths(campaign_id, file_id)
    baseline.write_text(content, encoding="utf-8")
    proposal.write_text(content, encoding="utf-8")
