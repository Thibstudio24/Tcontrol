"""Client API : dialogue avec le site Tcontrol (PHP)."""
from __future__ import annotations

import requests

from .config import Config, APP_VERSION


class SyncError(Exception):
    """Erreur de communication ou réponse invalide (serveur config. incorrecte,
    pare-feu de l'hébergeur, etc.)."""


class SyncClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"Tcontrol-App/{APP_VERSION}"})

    # ------------------------------------------------------------------ interne
    def _post(self, endpoint: str, payload: dict) -> dict:
        if not self.cfg.configured:
            raise SyncError("Serveur non configuré (URL / clé API manquantes).")
        url = self.cfg.api_url(endpoint)
        payload = dict(payload)
        payload.setdefault("key", self.cfg.api_key)
        try:
            r = self.session.post(url, json=payload, timeout=8)
        except requests.exceptions.SSLError as e:
            raise SyncError(
                "Certificat SSL invalide (auto-signé ?). Solutions : installe le "
                "certificat SSL gratuit dans ton panneau InfinityFree (recommandé), "
                "ou utilise http:// dans l'URL de l'API."
            ) from e
        except requests.RequestException as e:
            raise SyncError(f"Réseau injoignable ({e.__class__.__name__}) — "
                            f"vérifie internet et l'URL du serveur.") from e
        try:
            data = r.json()
        except ValueError as e:
            # InfinityFree affiche parfois une page de vérification JavaScript
            # à la place de la vraie réponse : on le signale clairement.
            raise SyncError(
                "Réponse invalide (pas du JSON). Si le site est sur InfinityFree, "
                "son pare-feu bloque peut-être les requêtes hors navigateur — "
                "voir le guide de déploiement."
            ) from e
        if not isinstance(data, dict) or not data.get("ok"):
            raise SyncError(str(data.get("error", f"Erreur serveur HTTP {r.status_code}")))
        return data

    # ------------------------------------------------------------------ API publique
    def ping(self, *, user: str, machine: str, delta: int, day: str,
             running: list[str], blocked: bool) -> dict:
        return self._post("ping.php", {
            "user": user,
            "machine": machine,
            "delta": max(0, min(int(delta), 900)),
            "day": day,
            "running": running[:20],
            "blocked": blocked,
            "version": APP_VERSION,
        })

    def auth(self, username: str, password: str) -> tuple[bool, str]:
        """Retourne (ok, erreur_éventuelle)."""
        try:
            self._post("auth.php", {"username": username, "password": password})
            return True, ""
        except SyncError as e:
            return False, str(e)

    def admin_state(self, username: str, password: str) -> dict:
        return self._post("admin.php", {
            "action": "state", "username": username, "password": password,
        })

    def admin_add_process(self, username: str, password: str, name: str) -> dict:
        return self._post("admin.php", {
            "action": "add_process", "username": username, "password": password,
            "name": name,
        })

    def admin_remove_process(self, username: str, password: str, name: str) -> dict:
        return self._post("admin.php", {
            "action": "remove_process", "username": username, "password": password,
            "name": name,
        })
