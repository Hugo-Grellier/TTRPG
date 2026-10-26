"""Resumable, private scenario dossier from page-addressed PDF text.

Source excerpts remain proposals. A local model filters exact candidates; it never
writes campaign facts or introduces uncited names.
"""

import json
import re
from urllib.request import Request, urlopen

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


def _ollama(prompt, model, timeout=240, schema=None):
    base = "http://127.0.0.1:11434"
    with urlopen(base + "/api/tags", timeout=5) as response:
        names = {item["name"] for item in json.load(response)["models"]}
    if model not in names:
        raise RuntimeError(f"Local Ollama model unavailable: {model}")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False,
                          "format": schema or {"type": "object", "properties": {"keep": {"type": "array", "items": {"type": "integer"}}},
                                               "required": ["keep"], "additionalProperties": False},
                          "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 350}}).encode()
    with urlopen(Request(base + "/api/generate", data=payload, headers={"Content-Type": "application/json"}), timeout=timeout) as response:
        result = json.load(response)
    return json.loads(result["response"])


def analyze_document(db, campaign_id, document_id, model="qwen3:4b-16k", batch_size=16, reviewer=None, progress=None):
    """Filter source candidates in checkpoints. Safe to rerun after interruption."""
    index_document(db, campaign_id, document_id)
    reviewer = reviewer or (lambda prompt: _ollama(prompt, model))
    with db:
        db.execute("""UPDATE scenario_candidates SET status='selected',model='structural'
            WHERE campaign_id=? AND document_id=? AND kind IN ('scene','heading','event','encounter') AND status='pending'""",
            (campaign_id, document_id))
    while True:
        rows = db.execute("""SELECT id,kind,name,pdf_page FROM scenario_candidates
            WHERE campaign_id=? AND document_id=? AND status='pending' ORDER BY id LIMIT ?""",
            (campaign_id, document_id, batch_size)).fetchall()
        if not rows:
            break
        choices = "\n".join(f"{r['id']} | {r['kind']} | PDF p.{r['pdf_page']} | {r['name']}" for r in rows)
        prompt = (f"Tu édites un dossier PRATIQUE pour un MJ. Parmi les {len(rows)} fragments du PDF ci-dessous, "
                  f"choisis AU MAXIMUM {min(6, len(rows))} éléments vraiment utilisables pendant une séance. "
                  "Priorité aux scènes nommées, personnages, lieux, rencontres, indices précis et choix avec conséquence explicite. "
                  "Rejette absolument les phrases coupées, titres répétés, crédits, renvois de livre, règles génériques et simple narration. "
                  "Si aucun ne convient, keep est vide. Réponds uniquement en JSON {'keep':[ID,...]}.\n" + choices)
        try:
            response = reviewer(prompt)
            valid = {row["id"] for row in rows}
            keep = set(response["keep"])
            if len(keep) > 6 or not all(type(item) is int and item in valid for item in keep):
                raise ValueError("Model returned an unknown candidate ID")
        except Exception:
            with db:
                db.executemany("UPDATE scenario_candidates SET attempts=attempts+1 WHERE id=?", [(row["id"],) for row in rows])
            raise
        with db:
            db.executemany("UPDATE scenario_candidates SET status=?, attempts=attempts+1, model=? WHERE id=?",
                           [("selected" if row["id"] in keep else "rejected", model, row["id"]) for row in rows])
        if progress:
            progress(dossier_stats(db, campaign_id, document_id))
    return dossier_stats(db, campaign_id, document_id)


def summarize_document(db, campaign_id, document_id, model="qwen3:4b-16k", summarizer=None, progress=None):
    """Write short provisional chapter overviews from cited, selected cards."""
    document = library_document(db, campaign_id, document_id)
    schema = {"type": "object", "properties": {"summary": {"type": "string"}},
              "required": ["summary"], "additionalProperties": False}
    summarizer = summarizer or (lambda prompt: _ollama(prompt, model, schema=schema))
    sections = db.execute("""SELECT * FROM scenario_sections WHERE campaign_id=? AND document_id=?
        AND summary_status='pending' ORDER BY start_page""", (campaign_id, document_id)).fetchall()
    for section in sections:
        if ((section["title"] == "Ouverture et repères" and document["page_count"] > 10)
                or section["title"] == "Publicité et crédits"
                or (document["page_count"] > 10 and section["title"].startswith("Annexe"))):
            continue
        rows = db.execute("""SELECT id,pdf_page,kind,evidence FROM scenario_candidates
            WHERE section_id=? AND status='selected' ORDER BY pdf_page,line_number""",
            (section["id"],)).fetchall()
        if not rows:
            continue
        if len(rows) > 32:
            rows = [rows[round(i * (len(rows) - 1) / 31)] for i in range(32)]
        excerpts = "\n".join(f"{r['id']} | p.{r['pdf_page']} | {r['kind']} | {r['evidence'][:220]}" for r in rows)
        prompt = (f"Rédige pour un MJ un aperçu de 2 à 4 phrases de la section « {section['title']} ». "
                  "Utilise exclusivement les extraits exacts ci-dessous. Décris situation, action jouable et enjeu. "
                  "Si les extraits sont insuffisants, dis-le. Ne complète pas l'intrigue de mémoire. "
                  "Réponds en JSON avec summary.\n" + excerpts)
        result = summarizer(prompt)
        summary = result["summary"].strip()
        if not summary or len(summary) > 800:
            raise ValueError("Invalid section overview")
        with db:
            db.execute("UPDATE scenario_sections SET summary=?, summary_status='proposed' WHERE id=?",
                       (summary, section["id"]))
        if progress:
            progress(section["title"])


def classify_headings(db, campaign_id, document_id, model="qwen3:4b-16k", classifier=None, progress=None):
    """Group named source headings for navigation; categories remain provisional."""
    library_document(db, campaign_id, document_id)
    categories = {"person", "place", "faction", "item", "creature", "topic"}
    schema = {"type": "object", "properties": {"types": {"type": "object", "additionalProperties": {"type": "string", "enum": sorted(categories)}}},
              "required": ["types"], "additionalProperties": False}
    classifier = classifier or (lambda prompt: _ollama(prompt, model, schema=schema))
    while True:
        rows = db.execute("""SELECT id,name,evidence,pdf_page FROM scenario_candidates
            WHERE campaign_id=? AND document_id=? AND kind='heading' AND status='selected' AND category=''
            ORDER BY id LIMIT 10""", (campaign_id, document_id)).fetchall()
        if not rows:
            break
        prompt = ("Classe chaque rubrique d'un scénario de jeu de rôle selon le type d'élément qu'elle nomme: "
                  "person (personnage nommé), place (lieu), faction (groupe/organisation), item (objet), "
                  "creature (espèce ou adversaire), topic (autre rubrique). Utilise le contexte exact. "
                  "Réponds en JSON avec types, dictionnaire ID vers catégorie; inclue exactement tous les ID.\n" +
                  "\n".join(f"{r['id']} | PDF p.{r['pdf_page']} | {r['name']} | {r['evidence'][:180]}" for r in rows))
        result = classifier(prompt)["types"]
        expected = {str(row["id"]) for row in rows}
        if set(result) != expected or any(value not in categories for value in result.values()):
            raise ValueError("Invalid heading classification")
        with db:
            db.executemany("UPDATE scenario_candidates SET category=? WHERE id=?",
                           [(result[str(row["id"])], row["id"]) for row in rows])
        if progress:
            progress(len(rows))
