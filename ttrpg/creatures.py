"""Creatures for encounter building: an index of the pf2e system's bestiaries (level, traits, rarity,
compendium uuid), filtered by level and trait, priced in XP for the party (GM Core, Building Encounters).

The index is built once from a Foundry pf2e system directory and shared by every campaign, beside the
source library.
"""

import csv
import json
from pathlib import Path

from .foundry_import import unpack

# GM Core p. 75 (printed): XP budget for four characters and the adjustment per character beyond four.
THREATS = {"trivial": (40, 10), "low": (60, 20), "moderate": (80, 20), "severe": (120, 30), "extreme": (160, 40)}
# Creature XP by level relative to the party, -4 to +4.
CREATURE_XP = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120, 4: 160}
SKIP_PACKS = {"vehicles", "iconics", "paizo-pregens"}


def budget(party, threat):
    base, per_character = THREATS[threat]
    return base + (party - 4) * per_character


def xp(level, party_level):
    """XP a creature costs; None outside -4..+4 (GM Core: avoid, or treat as trivial or impossible)."""
    return CREATURE_XP.get(level - party_level)


def build(system_dir, out, log=print, unpack=unpack):
    """Write the index of every Actor pack of the pf2e system: one row per creature or hazard."""
    system_dir = Path(system_dir)
    manifest = json.loads((system_dir / "system.json").read_text(encoding="utf-8"))
    rows = []
    for pack in manifest["packs"]:
        if pack["type"] != "Actor" or pack["name"] in SKIP_PACKS:
            continue
        for doc in unpack(system_dir / pack["path"]):
            if doc.get("type") not in ("npc", "hazard"):
                continue
            system = doc.get("system") or {}
            traits = system.get("traits") or {}
            rows.append({
                "uuid": f"Compendium.{manifest['id']}.{pack['name']}.Actor.{doc['_id']}", "id": doc["_id"],
                "name": doc["name"], "type": doc["type"], "level": ((system.get("details") or {}).get("level") or {}).get("value"),
                "rarity": traits.get("rarity", "common"), "size": (traits.get("size") or {}).get("value", ""),
                "traits": traits.get("value") or [], "pack": pack["name"],
                "source": ((system.get("details") or {}).get("publication") or {}).get("title", ""),
            })
        log(f"{pack['name']}: {len(rows)} so far")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"system": manifest["id"], "version": manifest.get("version"), "creatures": rows}, ensure_ascii=False), encoding="utf-8")
    return rows


def translations(glossary):
    """Foundry id -> campaign-language name, from a campaign's glossary.tsv."""
    if not glossary.is_file():
        return {}
    with open(glossary, encoding="utf-8") as tsv:
        return {row["foundry_id"]: row["translation"] for row in csv.DictReader(tsv, delimiter="\t") if row.get("foundry_id")}


def find(rows, levels=None, traits=(), name=None, rarity=None, packs=(), hazards=False):
    """Rows matching every filter, by level then name."""
    traits = {trait.lower() for trait in traits}
    found = [row for row in rows
             if (row["type"] == "hazard") == hazards
             and (levels is None or row["level"] in levels)
             and traits <= {trait.lower() for trait in row["traits"]}
             and (not name or name.lower() in row["name"].lower())
             and (not rarity or row["rarity"] == rarity)
             and (not packs or any(part in row["pack"] for part in packs))]
    return sorted(found, key=lambda row: (row["level"] if row["level"] is not None else -99, row["name"], row["pack"]))
