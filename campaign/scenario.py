"""Private scenario source packets and agent-reviewed dossier proposals."""

import re

from .core import DomainError
from .library import library_document

SCENE = re.compile(r"^[A-D]\d{1,2}[A-Z]?\.\s+(.{3,100})$")
CHAPTER = re.compile(r"^CHAPITRE\s+\d+\s*:", re.I)
HEADING = re.compile(r"^[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ0-9][A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ0-9 ’'(),:!?.\-]{5,95}$")
CHOICE = re.compile(r"\b(si les PJ|les PJ peuvent|selon (leur|que)|au choix|en fonction de)\b", re.I)
CLUE = re.compile(r"\b(découvr|apprenn|révèl|indice|interrog|enquêt|trouv|remarqu)\w*", re.I)
ACTOR = re.compile(r"\b(PNJ|créature|ennemi|adversaire|gardien|chef|espion|culte|gobelin|kobold|humain|elfe)\b", re.I)
LOW_VALUE = re.compile(r"^(?:\d+|Pathfinder 2|Seconde édition|CHAPITRE \d+ :|NIVEAU \d+|POINTS D’EXPÉRIENCE|©|\bTABLE DES MATIÈRES\b|DU CHEVALIER|CHEVALIER INFERNAL|LA COLLINE|BOÎTE À OUTILS|LES ÉLUS DU CONSEIL|CITADELLE D’ALTAÉREIN|OPEN GAME LICENSE.*|\d+\. COPYRIGHT NOTICE|PEU COURANT.*|MOYENNE .*|NB PETITE.*|ENVIRONNEMENTAL .*|ENCHANTEMENT|CRÉATURE ARTIFICIELLE)$", re.I)


def _clean(line):
    return " ".join(line.strip().split())


def _section_starts(pages):
    starts = [(1, "Ouverture et repères")]
    for page in pages:
        lines = [_clean(line) for line in page["text"].splitlines()[:12] if _clean(line)]
        for i, line in enumerate(lines[:5]):
            if CHAPTER.match(line) and page["pdf_page"] > 5 and i + 1 < len(lines) and not lines[i + 1].strip().isdigit():
                title = line.rstrip(" :") + " · " + lines[i + 1].title()
                starts.append((page["pdf_page"], title))
                break
        if page["pdf_page"] > 5 and lines:
            first = lines[0].upper()
            if first.startswith("BRÈCHEMONT,"):
                starts.append((page["pdf_page"], "Annexe · Brèchemont"))
            elif first.startswith("BOÎTE À OUTILS"):
                starts.append((page["pdf_page"], "Annexe · Boîte à outils"))
            elif first == "SECONDE ÉDITION" and page["pdf_page"] > 80 and not any(start >= 95 for start, _ in starts):
                starts.append((page["pdf_page"], "Publicité et crédits"))
    return sorted(dict(starts).items())


def _candidate(line):
    scene = SCENE.match(line)
    if scene and len(line) <= 95 and not re.search(r"\b(PJ|Perception|DD\s*\d+)\b", line, re.I):
        return "scene", line[:115]
    if len(line) < 12 or len(line) > 230 or LOW_VALUE.match(line):
        return None
    if HEADING.fullmatch(line) and len(line.split()) <= 12:
        if re.search(r"\(\d+\)$", line):
            return "encounter", line[:115]
        if line.startswith("ÉVÉNEMENT "):
            return "event", line[:115]
        return "heading", line[:115]
    if CHOICE.search(line):
        return "choice", line[:115]
    if CLUE.search(line):
        return "clue", line[:115]
    return None


def _context(lines, index):
    excerpt = []
    for raw in lines[index:index + 5]:
        line = _clean(raw)
        if not line and excerpt:
            break
        if line:
            excerpt.append(line)
        if sum(map(len, excerpt)) > 430:
            break
    return " ".join(excerpt)[:650]


def index_document(db, campaign_id, document_id):
    document = library_document(db, campaign_id, document_id)
    pages = db.execute("SELECT pdf_page, text, quality FROM library_pages WHERE campaign_id=? AND document_id=? ORDER BY pdf_page",
                       (campaign_id, document_id)).fetchall()
    if len(pages) != document["page_count"]:
        raise DomainError("error.pdf_extract_failed")
    starts = _section_starts(pages)
    first_chapter = next((start for start, title in starts if title.upper().startswith("CHAPITRE")), None)
    with db:
        for i, (start, title) in enumerate(starts):
            end = starts[i + 1][0] - 1 if i + 1 < len(starts) else document["page_count"]
            db.execute("""INSERT OR IGNORE INTO scenario_sections(campaign_id,document_id,title,start_page,end_page)
                VALUES(?,?,?,?,?)""", (campaign_id, document_id, title, start, end))
        sections = db.execute("SELECT id,start_page,end_page FROM scenario_sections WHERE campaign_id=? AND document_id=? ORDER BY start_page",
                              (campaign_id, document_id)).fetchall()
        for page in pages:
            number = page["pdf_page"]
            section_id = next(row["id"] for row in sections if row["start_page"] <= number <= row["end_page"])
            db.execute("INSERT OR IGNORE INTO scenario_pages(campaign_id,document_id,pdf_page,section_id) VALUES(?,?,?,?)",
                       (campaign_id, document_id, number, section_id))
            section_title = next(title for start, title in reversed(starts) if start <= number)
            if (page["quality"] == "empty" or section_title == "Publicité et crédits"
                    or (first_chapter and first_chapter <= 10 and number <= first_chapter - 2)):
                continue
            lines = page["text"].splitlines()
            for line_number, raw in enumerate(lines, 1):
                line = _clean(raw)
                match = _candidate(line)
                if match and not (match[0] in ("choice", "clue") and (raw[:1].islower() or len(line) < 35)):
                    kind, name = match
                    db.execute("""INSERT OR IGNORE INTO scenario_candidates
                        (campaign_id,document_id,section_id,pdf_page,line_number,kind,name,evidence)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (campaign_id, document_id, section_id, number, line_number, kind, name, _context(lines, line_number - 1)))
    return dossier_stats(db, campaign_id, document_id)


def dossier_stats(db, campaign_id, document_id):
    library_document(db, campaign_id, document_id)
    return db.execute("""SELECT (SELECT COUNT(*) FROM scenario_pages WHERE campaign_id=? AND document_id=?) AS pages,
        (SELECT COUNT(*) FROM scenario_candidates WHERE campaign_id=? AND document_id=?) AS candidates,
        (SELECT COUNT(*) FROM scenario_candidates WHERE campaign_id=? AND document_id=? AND status='pending') AS pending,
        (SELECT COUNT(*) FROM scenario_candidates WHERE campaign_id=? AND document_id=? AND status='selected') AS selected,
        (SELECT COUNT(*) FROM scenario_candidates WHERE campaign_id=? AND document_id=? AND status='error') AS errors""",
        (campaign_id, document_id) * 5).fetchone()


CATEGORIES = {"person", "place", "faction", "item", "creature", "topic"}
REVIEWERS = {"codex-chat", "claude-code-chat"}
ELEMENT_KINDS = {"scene", "person", "place", "faction", "item", "creature", "clue",
                 "choice", "event", "encounter", "secret", "hook", "rule"}


def review_packet(db, campaign_id, document_id, first_page, last_page):
    """Bounded private source packet for an agent already in the GM's chat."""
    document = library_document(db, campaign_id, document_id)
    if first_page < 1 or last_page < first_page or last_page > document["page_count"] or last_page - first_page >= 8:
        raise ValueError("Choose one to eight PDF pages")
    pages = db.execute("""SELECT pdf_page,text,quality FROM library_pages
        WHERE campaign_id=? AND document_id=? AND pdf_page BETWEEN ? AND ? ORDER BY pdf_page""",
        (campaign_id, document_id, first_page, last_page)).fetchall()
    if len(pages) != last_page - first_page + 1:
        raise ValueError("Missing source page")
    sections = db.execute("""SELECT id,title,start_page,end_page FROM scenario_sections
        WHERE campaign_id=? AND document_id=? AND end_page>=? AND start_page<=? ORDER BY start_page""",
        (campaign_id, document_id, first_page, last_page)).fetchall()
    candidates = db.execute("""SELECT id,pdf_page,line_number,kind,name,status,category,note,model
        FROM scenario_candidates WHERE campaign_id=? AND document_id=? AND pdf_page BETWEEN ? AND ?
        ORDER BY pdf_page,line_number""", (campaign_id, document_id, first_page, last_page)).fetchall()
    return {"document_id": document_id, "source_sha256": document["sha256"],
            "sections": [dict(row) for row in sections],
            "pages": [{"pdf_page": row["pdf_page"], "quality": row["quality"],
                       "lines": [{"line": number, "text": line} for number, line in enumerate(row["text"].splitlines(), 1)]}
                      for row in pages],
            "candidates": [dict(row) for row in candidates]}


def apply_agent_review(db, campaign_id, document_id, review):
    """Accept a chat agent's private JSON as source-linked proposals, never canon."""
    if not isinstance(review, dict):
        raise ValueError("Review must be an object")
    document = library_document(db, campaign_id, document_id)
    if review.get("document_id") != document_id or review.get("source_sha256") != document["sha256"]:
        raise ValueError("Review does not match the imported PDF")
    reviewer = review.get("reviewer")
    if reviewer not in REVIEWERS:
        raise ValueError("Reviewer must be a Codex or Claude Code chat session")
    updates = review.get("candidates", [])
    summaries = review.get("sections", [])
    elements = review.get("elements", [])
    if not isinstance(updates, list) or not isinstance(summaries, list) or not isinstance(elements, list):
        raise ValueError("Invalid review lists")
    seen_candidates, seen_sections = set(), set()
    candidate_changes, section_changes, element_changes = [], [], []
    for item in updates:
        if not isinstance(item, dict):
            raise ValueError("Invalid candidate decision")
        candidate_id = item.get("id")
        row = db.execute("""SELECT id,kind FROM scenario_candidates
            WHERE id=? AND campaign_id=? AND document_id=?""", (candidate_id, campaign_id, document_id)).fetchone()
        if row is None or candidate_id in seen_candidates:
            raise ValueError("Unknown or duplicate candidate")
        seen_candidates.add(candidate_id)
        status = item.get("status")
        category = item.get("category", "")
        note = item.get("note", "")
        if (status not in ("selected", "rejected") or not isinstance(category, str)
                or category not in CATEGORIES | {""} or not isinstance(note, str)):
            raise ValueError("Invalid candidate decision")
        note = note.strip()
        if category and row["kind"] != "heading":
            raise ValueError("Only named headings have a category")
        if status == "rejected" and (category or note):
            raise ValueError("Rejected items cannot have notes")
        if len(note) > 4000:
            raise ValueError("Candidate note too long")
        candidate_changes.append((status, category, note, reviewer, candidate_id))
    for item in summaries:
        if not isinstance(item, dict):
            raise ValueError("Invalid section summary")
        section_id = item.get("id")
        row = db.execute("""SELECT id FROM scenario_sections WHERE id=? AND campaign_id=? AND document_id=?""",
                         (section_id, campaign_id, document_id)).fetchone()
        if row is None or section_id in seen_sections:
            raise ValueError("Unknown or duplicate section")
        seen_sections.add(section_id)
        summary = item.get("summary", "")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 4000:
            raise ValueError("Invalid section summary")
        section_changes.append((summary.strip(), section_id))
    for item in elements:
        if not isinstance(item, dict):
            raise ValueError("Invalid scenario element")
        page_number, line_number = item.get("pdf_page"), item.get("line_number")
        page = db.execute("""SELECT text FROM library_pages WHERE campaign_id=? AND document_id=? AND pdf_page=?""",
                          (campaign_id, document_id, page_number)).fetchone()
        if page is None or not isinstance(line_number, int):
            raise ValueError("Unknown source location")
        lines = page["text"].splitlines()
        if line_number < 1 or line_number > len(lines):
            raise ValueError("Unknown source line")
        kind, title, body, quote = (item.get("kind"), item.get("title", ""),
                                    item.get("body", ""), item.get("quote", ""))
        if (kind not in ELEMENT_KINDS or not isinstance(title, str) or not isinstance(body, str)
                or not isinstance(quote, str) or not 3 <= len(title.strip()) <= 160
                or not 8 <= len(body.strip()) <= 4000 or not 4 <= len(quote.strip()) <= 160
                or _clean(quote) not in _clean(lines[line_number - 1])):
            raise ValueError("Invalid or ungrounded scenario element")
        section = db.execute("""SELECT id FROM scenario_sections WHERE campaign_id=? AND document_id=?
            AND start_page<=? AND end_page>=?""", (campaign_id, document_id, page_number, page_number)).fetchone()
        if section is None:
            raise ValueError("Source page has no section")
        element_changes.append((campaign_id, document_id, section["id"], page_number, line_number,
                                kind, title.strip(), body.strip(), quote.strip(), reviewer))
    with db:
        db.executemany("""UPDATE scenario_candidates SET status=?,category=?,note=?,model=?
            WHERE id=?""", candidate_changes)
        db.executemany("""UPDATE scenario_sections SET summary=?,summary_status='proposed' WHERE id=?""", section_changes)
        db.executemany("""INSERT INTO scenario_elements
            (campaign_id,document_id,section_id,pdf_page,line_number,kind,title,body,quote,reviewer)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(document_id,pdf_page,line_number,kind,title)
            DO UPDATE SET body=excluded.body,quote=excluded.quote,reviewer=excluded.reviewer""", element_changes)
    return {"candidates": len(candidate_changes), "sections": len(section_changes), "elements": len(element_changes)}
