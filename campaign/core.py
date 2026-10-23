"""Rules shared by the web interface and any future adapter."""


class DomainError(ValueError):
    pass


def required(value: str, label: str, limit: int = 500) -> str:
    value = value.strip()
    if not value or len(value) > limit:
        raise DomainError(f"{label} doit contenir entre 1 et {limit} caractères.")
    return value


def visibility(value: str) -> str:
    if value != "gm":
        raise DomainError("La publication aux joueurs n'est pas encore disponible.")
    return value
