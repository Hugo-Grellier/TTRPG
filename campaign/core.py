"""Rules shared by the web interface and any future adapter."""

from .i18n import t


class DomainError(ValueError):
    def __init__(self, key: str, **values):
        self.key = key
        self.values = values
        super().__init__(self.localized())

    def localized(self, language: str = "en") -> str:
        values = {name: t(value, language) if name == "label" else value for name, value in self.values.items()}
        return t(self.key, language, **values)


def required(value: str, label: str, limit: int = 500) -> str:
    value = value.strip()
    if not value or len(value) > limit:
        raise DomainError("error.required", label=label, limit=limit)
    return value


def visibility(value: str) -> str:
    if value != "gm":
        raise DomainError("error.player_publication")
    return value
