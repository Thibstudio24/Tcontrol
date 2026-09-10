"""Fonctions utilitaires pures (pas de dépendance Windows)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

PROC_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\- ()]{0,63}$")


def logical_day(reset_hour: int, now: datetime | None = None) -> str:
    """Jour logique : si l'heure courante est avant l'heure de reset,
    on considère qu'on est encore sur la journée d'hier."""
    now = now or datetime.now()
    if now.hour < reset_hour:
        now -= timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def fmt_duration(seconds: float | int) -> str:
    """7200 -> '2 h 00 min' ; 300 -> '5 min' ; 45 -> '45 s'."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h} h {m:02d} min"
    if m:
        return f"{m} min"
    return f"{s} s"


def normalize_process_name(name: str) -> str:
    """Normalise un nom de processus pour la comparaison (minuscules, strip)."""
    return name.strip().lower()


def is_valid_process_name(name: str) -> bool:
    return bool(PROC_NAME_RE.match(name.strip()))
