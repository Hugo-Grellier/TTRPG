"""SQLite owns durable campaign state; callers use these transactions."""

import sqlite3
from pathlib import Path

from .core import DomainError, required, visibility
from .i18n import t


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'en'
);
CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  title TEXT NOT NULL, locator TEXT NOT NULL, note TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm'),
  UNIQUE (id, campaign_id)
);
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  source_id INTEGER NOT NULL,
  text TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('note', 'simulated_play')),
  visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm'),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (id, campaign_id),
  FOREIGN KEY (source_id, campaign_id) REFERENCES sources(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  observation_id INTEGER NOT NULL,
  instruction TEXT NOT NULL, decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (id, campaign_id),
  FOREIGN KEY (observation_id, campaign_id) REFERENCES observations(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  decision_id INTEGER NOT NULL UNIQUE,
  text TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm'),
  UNIQUE (id, campaign_id),
  FOREIGN KEY (decision_id, campaign_id) REFERENCES decisions(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  source_id INTEGER NOT NULL, revised_from INTEGER,
  text TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm'),
  UNIQUE (id, campaign_id),
  FOREIGN KEY (source_id, campaign_id) REFERENCES sources(id, campaign_id),
  FOREIGN KEY (revised_from, campaign_id) REFERENCES proposals(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS preparations (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  fact_id INTEGER NOT NULL, proposal_id INTEGER NOT NULL,
  situation TEXT NOT NULL, alternatives TEXT NOT NULL,
  visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm'),
  UNIQUE (id, campaign_id),
  FOREIGN KEY (fact_id, campaign_id) REFERENCES facts(id, campaign_id),
  FOREIGN KEY (proposal_id, campaign_id) REFERENCES proposals(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS simulated_events (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  preparation_id INTEGER NOT NULL, observation_id INTEGER NOT NULL,
  player_action TEXT NOT NULL, ruling TEXT NOT NULL,
  UNIQUE (id, campaign_id),
  FOREIGN KEY (preparation_id, campaign_id) REFERENCES preparations(id, campaign_id),
  FOREIGN KEY (observation_id, campaign_id) REFERENCES observations(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS corrections (
  old_fact_id INTEGER PRIMARY KEY, new_fact_id INTEGER NOT NULL UNIQUE,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  FOREIGN KEY (old_fact_id, campaign_id) REFERENCES facts(id, campaign_id),
  FOREIGN KEY (new_fact_id, campaign_id) REFERENCES facts(id, campaign_id)
);
CREATE TABLE IF NOT EXISTS document_comments (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  target_kind TEXT NOT NULL CHECK (target_kind IN ('sources', 'proposals', 'preparations', 'facts', 'simulated_events')),
  target_id INTEGER NOT NULL, quote TEXT NOT NULL, body TEXT NOT NULL,
  line_start INTEGER, line_end INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm')
);
CREATE TABLE IF NOT EXISTS agent_turns (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  provider TEXT NOT NULL CHECK (provider IN ('codex', 'claude')),
  prompt TEXT NOT NULL, response TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL CHECK (status IN ('running', 'complete', 'error')),
  session_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS product_comments (
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
  file_id INTEGER NOT NULL CHECK (file_id BETWEEN 1 AND 5),
  quote TEXT NOT NULL, body TEXT NOT NULL,
  line_start INTEGER, line_end INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  visibility TEXT NOT NULL DEFAULT 'gm' CHECK (visibility = 'gm')
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    # Existing M0 databases lack the composite key required by M1's campaign-scoped links.
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS facts_campaign_key ON facts(id, campaign_id)")
    for table in ("document_comments", "product_comments"):
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        for column in ("line_start", "line_end"):
            if column not in columns:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER")
    return db


def create_campaign(db, name: str, language: str = "en") -> int:
    name = required(name, "field.name", 100)
    language = required(language, "field.language", 16)
    with db:
        return db.execute("INSERT INTO campaigns(name, language) VALUES (?, ?)", (name, language)).lastrowid


def add_source(db, campaign_id: int, title: str, locator: str, note: str) -> int:
    title = required(title, "field.title", 200)
    locator = required(locator, "label.locator", 200)
    note = required(note, "field.description", 2000)
    _campaign(db, campaign_id)
    with db:
        return db.execute(
            "INSERT INTO sources(campaign_id, title, locator, note) VALUES (?, ?, ?, ?)",
            (campaign_id, title, locator, note),
        ).lastrowid


def add_observation(db, campaign_id: int, source_id: int, text: str, kind: str = "note", access: str = "gm") -> int:
    text = required(text, "label.observation", 2000)
    visibility(access)
    if kind not in ("note", "simulated_play"):
        raise DomainError("error.unknown_kind")
    _owned(db, "sources", source_id, campaign_id)
    with db:
        return db.execute(
            "INSERT INTO observations(campaign_id, source_id, text, kind) VALUES (?, ?, ?, ?)",
            (campaign_id, source_id, text, kind),
        ).lastrowid


def establish_fact(db, campaign_id: int, observation_id: int, instruction: str, fact: str, access: str = "gm") -> int:
    instruction = required(instruction, "label.decision", 1000)
    fact = required(fact, "field.canonical_fact", 2000)
    visibility(access)
    _owned(db, "observations", observation_id, campaign_id)
    with db:
        decision_id = db.execute(
            "INSERT INTO decisions(campaign_id, observation_id, instruction) VALUES (?, ?, ?)",
            (campaign_id, observation_id, instruction),
        ).lastrowid
        return db.execute(
            "INSERT INTO facts(campaign_id, decision_id, text) VALUES (?, ?, ?)",
            (campaign_id, decision_id, fact),
        ).lastrowid


def add_proposal(db, campaign_id, source_id, text, revised_from=None, access="gm"):
    text = required(text, "field.proposal", 2000)
    visibility(access)
    _owned(db, "sources", source_id, campaign_id)
    if revised_from is not None:
        _owned(db, "proposals", revised_from, campaign_id)
    with db:
        return db.execute("INSERT INTO proposals(campaign_id, source_id, revised_from, text) VALUES (?, ?, ?, ?)",
                          (campaign_id, source_id, revised_from, text)).lastrowid


def add_preparation(db, campaign_id, fact_id, proposal_id, situation, alternatives, access="gm"):
    situation = required(situation, "field.situation", 2000)
    alternatives = required(alternatives, "field.alternatives", 2000)
    visibility(access)
    _owned(db, "facts", fact_id, campaign_id)
    _owned(db, "proposals", proposal_id, campaign_id)
    with db:
        return db.execute("INSERT INTO preparations(campaign_id, fact_id, proposal_id, situation, alternatives) VALUES (?, ?, ?, ?, ?)",
                          (campaign_id, fact_id, proposal_id, situation, alternatives)).lastrowid


def add_simulated_event(db, campaign_id, preparation_id, player_action, ruling, access="gm"):
    player_action = required(player_action, "field.player_action", 2000)
    ruling = required(ruling, "field.ruling", 2000)
    visibility(access)
    _owned(db, "preparations", preparation_id, campaign_id)
    language = _campaign(db, campaign_id)["language"]
    with db:
        source_id = db.execute("INSERT INTO sources(campaign_id, title, locator, note) VALUES (?, ?, ?, ?)",
                               (campaign_id, t("event.source_title", language), f"prep #{preparation_id}", t("event.source_note", language))).lastrowid
        observation_id = db.execute("INSERT INTO observations(campaign_id, source_id, text, kind) VALUES (?, ?, ?, 'simulated_play')",
                                    (campaign_id, source_id, f"{player_action} → {ruling}")).lastrowid
        return db.execute("INSERT INTO simulated_events(campaign_id, preparation_id, observation_id, player_action, ruling) VALUES (?, ?, ?, ?, ?)",
                          (campaign_id, preparation_id, observation_id, player_action, ruling)).lastrowid


def correct_fact(db, campaign_id, old_fact_id, observation_id, instruction, fact, access="gm"):
    visibility(access)
    instruction = required(instruction, "label.decision", 1000)
    fact = required(fact, "field.canonical_fact", 2000)
    _owned(db, "facts", old_fact_id, campaign_id)
    _owned(db, "observations", observation_id, campaign_id)
    if db.execute("SELECT 1 FROM corrections WHERE old_fact_id=?", (old_fact_id,)).fetchone():
        raise DomainError("error.already_corrected")
    with db:
        decision_id = db.execute("INSERT INTO decisions(campaign_id, observation_id, instruction) VALUES (?, ?, ?)",
                                 (campaign_id, observation_id, instruction)).lastrowid
        new_id = db.execute("INSERT INTO facts(campaign_id, decision_id, text) VALUES (?, ?, ?)",
                            (campaign_id, decision_id, fact)).lastrowid
        db.execute("INSERT INTO corrections(old_fact_id, new_fact_id, campaign_id) VALUES (?, ?, ?)",
                   (old_fact_id, new_id, campaign_id))
        return new_id


def journey_view(db, campaign_id):
    proposals = db.execute("""SELECT p.*, s.title AS source_title, s.locator FROM proposals p
      JOIN sources s ON s.id=p.source_id WHERE p.campaign_id=? ORDER BY p.id DESC""", (campaign_id,)).fetchall()
    preparations = db.execute("""SELECT p.*, f.text AS fact, r.text AS proposal,
      c.new_fact_id, (SELECT count(*) FROM simulated_events e WHERE e.preparation_id=p.id) AS event_count
      FROM preparations p JOIN facts f ON f.id=p.fact_id JOIN proposals r ON r.id=p.proposal_id
      LEFT JOIN corrections c ON c.old_fact_id=p.fact_id WHERE p.campaign_id=? ORDER BY p.id DESC""", (campaign_id,)).fetchall()
    events = db.execute("""SELECT e.*, p.situation, o.text AS observation,
      (SELECT f.id FROM facts f JOIN decisions d ON d.id=f.decision_id WHERE d.observation_id=e.observation_id ORDER BY f.id DESC LIMIT 1) AS consequence_id,
      (SELECT f.text FROM facts f JOIN decisions d ON d.id=f.decision_id WHERE d.observation_id=e.observation_id ORDER BY f.id DESC LIMIT 1) AS consequence
      FROM simulated_events e JOIN preparations p ON p.id=e.preparation_id
      JOIN observations o ON o.id=e.observation_id WHERE e.campaign_id=? ORDER BY e.id DESC""", (campaign_id,)).fetchall()
    corrections = db.execute("""SELECT c.*, old.text AS old_text, new.text AS new_text FROM corrections c
      JOIN facts old ON old.id=c.old_fact_id JOIN facts new ON new.id=c.new_fact_id
      WHERE c.campaign_id=? ORDER BY new.id DESC""", (campaign_id,)).fetchall()
    return proposals, preparations, events, corrections


COMMENT_TARGETS = {
    "sources": ("note", "locator"),
    "proposals": ("text",),
    "preparations": ("situation", "alternatives"),
    "facts": ("text",),
    "simulated_events": ("player_action", "ruling"),
}
PRODUCT_DOCS = (
    "VISION.md",
    "docs/PRODUCT_PRINCIPLES.md",
    "docs/ARCHITECTURE.md",
    "docs/ROADMAP.md",
    "docs/WORKFLOW.md",
)


def product_doc(file_id):
    if not 1 <= file_id <= len(PRODUCT_DOCS):
        raise DomainError("error.item_missing")
    relative = PRODUCT_DOCS[file_id - 1]
    return relative, (Path(__file__).resolve().parent.parent / relative).read_text(encoding="utf-8")


def comment_lines(db, campaign_id, target_kind, target_id):
    if target_kind == "product_docs":
        _campaign(db, campaign_id)
        return product_doc(target_id)[1].splitlines()
    if target_kind not in COMMENT_TARGETS:
        raise DomainError("error.item_missing")
    _owned(db, target_kind, target_id, campaign_id)
    columns = COMMENT_TARGETS[target_kind]
    row = db.execute(f"SELECT {', '.join(columns)} FROM {target_kind} WHERE id=?", (target_id,)).fetchone()
    return [line for column in columns for line in str(row[column]).splitlines() or [""]]


def add_comment(db, campaign_id, target_kind, target_id, quote, body, access="gm", line_start=None, line_end=None):
    visibility(access)
    lines = comment_lines(db, campaign_id, target_kind, target_id)
    quote = quote.strip()
    if len(quote) > 500:
        raise DomainError("error.required", label="field.quote", limit=500)
    body = required(body, "field.comment", 2000)
    if line_start is not None or line_end is not None:
        if not isinstance(line_start, int) or not isinstance(line_end, int) or not 1 <= line_start <= line_end <= len(lines) or line_end - line_start > 20:
            raise DomainError("error.line_range")
        selected = "\n".join(lines[line_start - 1:line_end])
    else:
        selected = "\n".join(lines)
    if quote and " ".join(quote.split()) not in " ".join(selected.split()):
        raise DomainError("error.quote_missing")
    with db:
        if target_kind == "product_docs":
            return db.execute("INSERT INTO product_comments(campaign_id, file_id, quote, body, line_start, line_end) VALUES (?, ?, ?, ?, ?, ?)",
                              (campaign_id, target_id, quote, body, line_start, line_end)).lastrowid
        return db.execute("INSERT INTO document_comments(campaign_id, target_kind, target_id, quote, body, line_start, line_end) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (campaign_id, target_kind, target_id, quote, body, line_start, line_end)).lastrowid


def comments_for(db, campaign_id, target_kind, target_id):
    if target_kind == "product_docs":
        _campaign(db, campaign_id)
        product_doc(target_id)
        return db.execute("SELECT * FROM product_comments WHERE campaign_id=? AND file_id=? ORDER BY id",
                          (campaign_id, target_id)).fetchall()
    _owned(db, target_kind, target_id, campaign_id)
    return db.execute("SELECT * FROM document_comments WHERE campaign_id=? AND target_kind=? AND target_id=? ORDER BY id",
                      (campaign_id, target_kind, target_id)).fetchall()


def start_agent_turn(db, campaign_id, provider, prompt):
    _campaign(db, campaign_id)
    if provider not in ("codex", "claude"):
        raise DomainError("error.unknown_provider")
    prompt = required(prompt, "field.message", 4000)
    with db:
        return db.execute("INSERT INTO agent_turns(campaign_id, provider, prompt, status) VALUES (?, ?, ?, 'running')",
                          (campaign_id, provider, prompt)).lastrowid


def finish_agent_turn(db, turn_id, response, status, session_id=None):
    with db:
        db.execute("UPDATE agent_turns SET response=?, status=?, session_id=? WHERE id=?",
                   (response[:20000], status, session_id, turn_id))


def agent_turns(db, campaign_id):
    _campaign(db, campaign_id)
    return db.execute("SELECT * FROM agent_turns WHERE campaign_id=? ORDER BY id", (campaign_id,)).fetchall()


def _campaign(db, campaign_id):
    row = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        raise DomainError("error.campaign_missing")
    return row


def _owned(db, table, item_id, campaign_id):
    # table is a constant supplied only by this module.
    if db.execute(f"SELECT 1 FROM {table} WHERE id = ? AND campaign_id = ?", (item_id, campaign_id)).fetchone() is None:
        raise DomainError("error.item_missing")


def campaign_view(db, campaign_id: int, query: str = ""):
    campaign = _campaign(db, campaign_id)
    sources = db.execute("SELECT * FROM sources WHERE campaign_id = ? ORDER BY id DESC", (campaign_id,)).fetchall()
    observations = db.execute("""
      SELECT o.*, s.title AS source_title, s.locator FROM observations o
      JOIN sources s ON s.id = o.source_id
      WHERE o.campaign_id = ? ORDER BY o.id DESC
    """, (campaign_id,)).fetchall()
    pattern = f"%{query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%" if query else "%"
    facts = db.execute("""
      SELECT f.*, d.instruction, o.text AS observation, s.title AS source_title, s.locator
      FROM facts f JOIN decisions d ON d.id = f.decision_id
      JOIN observations o ON o.id = d.observation_id JOIN sources s ON s.id = o.source_id
      WHERE f.campaign_id = ? AND (f.text LIKE ? ESCAPE '\\' OR f.id IN (
        SELECT consequence.id FROM facts consequence
        JOIN decisions cd ON cd.id=consequence.decision_id
        JOIN simulated_events e ON e.observation_id=cd.observation_id
        JOIN preparations p ON p.id=e.preparation_id
        JOIN facts ancestor ON ancestor.id=p.fact_id
        WHERE p.campaign_id=? AND ancestor.text LIKE ? ESCAPE '\\'
      )) ORDER BY f.id DESC
    """, (campaign_id, pattern, campaign_id, pattern)).fetchall()
    return campaign, sources, observations, facts
