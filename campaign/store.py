"""SQLite owns durable campaign state; callers use these transactions."""

import sqlite3
from pathlib import Path

from .core import DomainError, required, visibility


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'fr'
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
  FOREIGN KEY (decision_id, campaign_id) REFERENCES decisions(id, campaign_id)
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def create_campaign(db, name: str, language: str = "fr") -> int:
    name = required(name, "Nom", 100)
    language = required(language, "Langue", 16)
    with db:
        return db.execute("INSERT INTO campaigns(name, language) VALUES (?, ?)", (name, language)).lastrowid


def add_source(db, campaign_id: int, title: str, locator: str, note: str) -> int:
    title = required(title, "Titre", 200)
    locator = required(locator, "Repère", 200)
    note = required(note, "Description", 2000)
    _campaign(db, campaign_id)
    with db:
        return db.execute(
            "INSERT INTO sources(campaign_id, title, locator, note) VALUES (?, ?, ?, ?)",
            (campaign_id, title, locator, note),
        ).lastrowid


def add_observation(db, campaign_id: int, source_id: int, text: str, kind: str = "note", access: str = "gm") -> int:
    text = required(text, "Observation", 2000)
    visibility(access)
    if kind not in ("note", "simulated_play"):
        raise DomainError("Type d'observation inconnu.")
    _owned(db, "sources", source_id, campaign_id)
    with db:
        return db.execute(
            "INSERT INTO observations(campaign_id, source_id, text, kind) VALUES (?, ?, ?, ?)",
            (campaign_id, source_id, text, kind),
        ).lastrowid


def establish_fact(db, campaign_id: int, observation_id: int, instruction: str, fact: str, access: str = "gm") -> int:
    instruction = required(instruction, "Décision", 1000)
    fact = required(fact, "Fait", 2000)
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


def _campaign(db, campaign_id):
    row = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        raise DomainError("Campagne introuvable.")
    return row


def _owned(db, table, item_id, campaign_id):
    # table is a constant supplied only by this module.
    if db.execute(f"SELECT 1 FROM {table} WHERE id = ? AND campaign_id = ?", (item_id, campaign_id)).fetchone() is None:
        raise DomainError("Élément introuvable dans cette campagne.")


def campaign_view(db, campaign_id: int, query: str = ""):
    campaign = _campaign(db, campaign_id)
    sources = db.execute("SELECT * FROM sources WHERE campaign_id = ? ORDER BY id DESC", (campaign_id,)).fetchall()
    observations = db.execute("""
      SELECT o.*, s.title AS source_title, s.locator FROM observations o
      JOIN sources s ON s.id = o.source_id
      WHERE o.campaign_id = ? ORDER BY o.id DESC
    """, (campaign_id,)).fetchall()
    facts = db.execute("""
      SELECT f.*, d.instruction, o.text AS observation, s.title AS source_title, s.locator
      FROM facts f JOIN decisions d ON d.id = f.decision_id
      JOIN observations o ON o.id = d.observation_id JOIN sources s ON s.id = o.source_id
      WHERE f.campaign_id = ? AND f.text LIKE ? ESCAPE '\\' ORDER BY f.id DESC
    """, (campaign_id, f"%{query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%" if query else "%")).fetchall()
    return campaign, sources, observations, facts
