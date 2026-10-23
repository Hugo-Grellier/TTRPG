"""Small, dependency-free UI catalog. English keys are stable across locales."""

import json
from functools import lru_cache
from importlib.resources import files


def locale(language: str) -> str:
    return "fr" if language.lower().startswith("fr") else "en"


@lru_cache(maxsize=2)
def catalog(language: str) -> dict[str, str]:
    language = locale(language)
    return json.loads(files("campaign").joinpath("locales", f"{language}.json").read_text(encoding="utf-8"))


def t(key: str, language: str = "en", **values) -> str:
    translated = catalog(language).get(key, catalog("en").get(key, key))
    return translated.format(**values)
