"""Détection et fermeture de processus (Windows)."""
from __future__ import annotations

import subprocess
import sys
from collections import Counter

import psutil

from .logic import normalize_process_name


def list_running() -> list[dict]:
    """Liste unique des noms de processus actifs, triée alphabétiquement.

    Retourne [{'name': 'steam.exe', 'count': 3}, ...]"""
    counter: Counter = Counter()
    for p in psutil.process_iter(["name"]):
        try:
            n = (p.info.get("name") or "").strip().lower()
            if n:
                counter[n] += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return [{"name": n, "count": c} for n, c in sorted(counter.items())]


def find_running(watched: set[str]) -> dict[str, list[psutil.Process]]:
    """Processus surveillés actuellement lancés : {nom_normalisé: [Process]}."""
    found: dict[str, list[psutil.Process]] = {}
    if not watched:
        return found
    for p in psutil.process_iter(["name"]):
        try:
            n = normalize_process_name(p.info.get("name") or "")
            if n in watched:
                found.setdefault(n, []).append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return found


def kill_tree(proc: psutil.Process) -> bool:
    """Tue un processus et ses enfants. Retourne True si au moins une action a réussi."""
    ok = False
    try:
        for child in proc.children(recursive=True):
            try:
                child.kill()
                ok = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        proc.kill()
        ok = True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return ok


def kill_by_name(name: str) -> int:
    """Tue toutes les instances d'un processus (par nom d'image).

    Sous Windows, taskkill /F /T est le plus efficace (gère l'arbre complet,
    y compris certains processus refusant psutil). Retour le Nb tué."""
    killed = 0
    if sys.platform.startswith("win"):
        try:
            r = subprocess.run(
                ["taskkill", "/F", "/T", "/IM", name],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=10,
            )
            killed = r.returncode == 0
        except Exception:
            killed = 0
        if killed:
            return 1
    # Fallback psutil
    for p in psutil.process_iter(["name"]):
        try:
            if normalize_process_name(p.info.get("name") or "") == normalize_process_name(name):
                if kill_tree(p):
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return killed
