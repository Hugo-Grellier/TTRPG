"""English -> campaign-language names of game things (spells, items, creatures...), for notes to
name them as players see them in Foundry.

Names and Foundry ids come from pathfinder-fr's data (https://pf2e.pathfinder-fr.org, built from
the pf2e system and the pf2-fr translation); pre-remaster names, which adventures written before the
remaster use, are mapped to their remaster equivalent with Archives of Nethys (https://2e.aonprd.com).
"""

import json
import urllib.request
from pathlib import Path

PATHFINDER_FR = "https://pf2e.pathfinder-fr.org/assets/data/{}.json"
DATASETS = ["actions", "ancestries", "archetypes", "backgrounds", "classes", "class-features", "conditions",
            "creatures", "deities", "effects", "equipment", "feats", "hazards", "heritages", "languages",
            "skills", "spells", "traits", "vehicles"]
AON = "https://elasticsearch.aonprd.com/aon/_search"
# Archives of Nethys category -> pathfinder-fr dataset, to prefer the right homonym (Invisibility the spell, not the rune).
KINDS = {"spell": "spells", "ritual": "spells", "equipment": "equipment", "weapon": "equipment", "armor": "equipment",
         "shield": "equipment", "relic": "equipment", "feat": "feats", "action": "actions", "creature": "creatures",
         "condition": "conditions", "hazard": "hazards", "trait": "traits", "deity": "deities", "background": "backgrounds",
         "heritage": "heritages", "ancestry": "ancestries", "class": "classes", "class-feature": "class-features",
         "archetype": "archetypes", "language": "languages", "skill": "skills", "vehicle": "vehicles"}


def fetch(url, cache, body=None):
    if cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    request = urllib.request.Request(url, data=body and json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def names(data, language):
    """(foundry id, english, translated) for each entry of a pathfinder-fr dataset."""
    entries = data if isinstance(data, list) else [{"_id": "", **entry} for entry in data.values()]
    for entry in entries:
        translated = ((entry.get("translations") or {}).get(language) or {}).get("name")
        if entry.get("name") and translated:
            yield entry.get("_id", ""), entry["name"], translated


def aon_renames():
    """(category, pre-remaster name, remaster name) from Archives of Nethys."""
    docs, scroll = {}, None
    query = {"size": 5000, "_source": ["name", "category", "remaster_id"],
             "query": {"bool": {"should": [{"exists": {"field": "remaster_id"}}, {"exists": {"field": "legacy_id"}}]}}}
    page = fetch(AON + "?scroll=2m", None, query)
    while page["hits"]["hits"]:
        docs.update((hit["_id"], hit["_source"]) for hit in page["hits"]["hits"])
        page = fetch(AON.replace("/aon/_search", "/_search/scroll"), None, {"scroll": "2m", "scroll_id": page["_scroll_id"]})
    for doc in docs.values():
        for new in doc.get("remaster_id") or []:
            if doc.get("name") and docs.get(new, {}).get("name") not in (None, doc["name"]):
                yield doc.get("category", ""), doc["name"], docs[new]["name"]


def build(cache_dir, language="fr", renames=aon_renames):
    """Rows (kind, foundry id, english, translated, remaster name or '')."""
    rows, by_name = set(), {}
    for kind in DATASETS:
        for foundry_id, english, translated in names(fetch(PATHFINDER_FR.format(kind), Path(cache_dir) / f"{kind}.json"), language):
            rows.add((kind, foundry_id, english, translated, ""))
            by_name.setdefault(english.lower(), {}).setdefault(kind, (foundry_id, translated))
    for category, old, new in renames():
        matches = by_name.get(new.lower()) or {}
        kind = KINDS.get(category) if KINDS.get(category) in matches else next(iter(matches), None)
        if kind and old.lower() not in by_name:
            rows.add((kind, matches[kind][0], old, matches[kind][1], new))
    return sorted(rows)


def write(root, rows):
    clean = lambda text: " ".join(str(text).split())
    out = Path(root) / "glossary.tsv"
    out.write_text("kind\tfoundry_id\tenglish\ttranslation\tremaster\n"
                   + "".join("\t".join(map(clean, row)) + "\n" for row in rows), encoding="utf-8")
    return out
