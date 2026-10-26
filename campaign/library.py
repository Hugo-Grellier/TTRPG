"""Private, page-addressed PDF sources. Extraction never establishes campaign canon."""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from .core import DomainError, required, visibility


ROOT = Path(__file__).resolve().parent.parent


def import_pdf(db, campaign_id, source_path, title="", access="gm"):
    visibility(access)
    if db.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone() is None:
        raise DomainError("error.campaign_missing")
    path = Path(source_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise DomainError("error.pdf_invalid")
    if path.is_relative_to(ROOT):
        raise DomainError("error.pdf_private")
    title = required(title or path.stem, "field.title", 200)
    before = path.stat()
    if before.st_size > 150_000_000:
        raise DomainError("error.pdf_too_large")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    sha256 = digest.hexdigest()
    existing = db.execute("SELECT id FROM library_documents WHERE campaign_id=? AND sha256=?",
                          (campaign_id, sha256)).fetchone()
    if existing:
        return existing["id"]
    if not shutil.which("pdfinfo") or not shutil.which("pdftotext"):
        raise DomainError("error.pdf_tools_missing")
    try:
        info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True, timeout=30).stdout
        page_count = int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))
        output = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"],
                                capture_output=True, check=True, timeout=180).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, AttributeError, ValueError) as exc:
        raise DomainError("error.pdf_extract_failed") from exc
    output = "".join(character for character in output if character in "\n\t\f" or 32 <= ord(character) != 127)
    pages = output.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != page_count or path.stat().st_size != before.st_size or path.stat().st_mtime_ns != before.st_mtime_ns:
        raise DomainError("error.pdf_extract_failed")
    with db:
        inserted = db.execute("""INSERT OR IGNORE INTO library_documents
          (campaign_id, title, source_path, sha256, page_count, extraction_method)
          VALUES (?, ?, ?, ?, ?, 'pdftotext')""",
          (campaign_id, title, str(path), sha256, page_count))
        if not inserted.rowcount:
            return db.execute("SELECT id FROM library_documents WHERE campaign_id=? AND sha256=?",
                              (campaign_id, sha256)).fetchone()["id"]
        document_id = inserted.lastrowid
        db.executemany("""INSERT INTO library_pages(campaign_id, document_id, pdf_page, text, quality)
          VALUES (?, ?, ?, ?, ?)""", (
            (campaign_id, document_id, number, text,
             "empty" if len(text.strip()) < 100 else "thin" if len(text.strip()) < 500 else "text")
            for number, text in enumerate(pages, 1)
        ))
    return document_id


def library_documents(db, campaign_id, access="gm"):
    visibility(access)
    if db.execute("SELECT 1 FROM campaigns WHERE id=?", (campaign_id,)).fetchone() is None:
        raise DomainError("error.campaign_missing")
    return db.execute("SELECT * FROM library_documents WHERE campaign_id=? ORDER BY id", (campaign_id,)).fetchall()


def library_document(db, campaign_id, document_id, access="gm"):
    visibility(access)
    row = db.execute("SELECT * FROM library_documents WHERE id=? AND campaign_id=?",
                     (document_id, campaign_id)).fetchone()
    if row is None:
        raise DomainError("error.item_missing")
    return row


def library_page(db, campaign_id, document_id, pdf_page, access="gm"):
    visibility(access)
    library_document(db, campaign_id, document_id)
    row = db.execute("SELECT * FROM library_pages WHERE document_id=? AND campaign_id=? AND pdf_page=?",
                     (document_id, campaign_id, pdf_page)).fetchone()
    if row is None:
        raise DomainError("error.item_missing")
    return row


def library_search(db, campaign_id, document_id, query, access="gm"):
    visibility(access)
    library_document(db, campaign_id, document_id)
    query = required(query, "workspace.library_search", 100)
    results = []
    # ponytail: linear page scan is enough for a local pilot; add FTS when a large library makes it slow.
    for row in db.execute("SELECT pdf_page, text FROM library_pages WHERE campaign_id=? AND document_id=? ORDER BY pdf_page",
                          (campaign_id, document_id)):
        position = row["text"].casefold().find(query.casefold())
        if position >= 0:
            excerpt = " ".join(row["text"][max(0, position - 80):position + len(query) + 120].split())
            results.append((row["pdf_page"], excerpt))
    return len(results), results[:40]
