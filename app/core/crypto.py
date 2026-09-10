"""Hachage local pour le déblocage admin hors ligne."""
from __future__ import annotations

import hashlib
import hmac

_ITER = 60_000
_SALT_PREFIX = "tcontrol-offline-v1:"


def hash_admin(username: str, password: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"),
        (_SALT_PREFIX + username.lower()).encode("utf-8"), _ITER,
    )
    return dk.hex()


def verify_admin(username: str, password: str, cached: dict) -> bool:
    """Vérifie un couple id/mdp contre les admins mémorisés (mode hors ligne)."""
    expected = cached.get(username.lower())
    if not expected:
        return False
    return hmac.compare_digest(expected, hash_admin(username, password))


def remember_admin(username: str, password: str, cached: dict) -> dict:
    cached[username.lower()] = hash_admin(username, password)
    return cached
