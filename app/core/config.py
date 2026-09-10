"""Configuration locale de l'app (stockée dans %APPDATA%/Tcontrol)."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

APP_NAME = "Tcontrol"
APP_VERSION = "1.0.0"

# URL de l'API de TON site InfinityFree (pré-remplie — modifiable ensuite
# dans 🔑 Admin → Configuration si tu changes d'hébergement)
DEFAULT_SERVER_URL = "https://tcontrol.thibstudio.rf.gd/api"


def app_data_dir() -> Path:
    """Dossier de données persistant, sûr en écriture même si l'exe
    est dans un dossier protégé."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        d = base / APP_NAME
    else:
        d = Path.home() / ".tcontrol"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Config:
    server_url: str = DEFAULT_SERVER_URL   # URL du dossier /api du site
    api_key: str = ""                      # clé API affichée dans l'admin du site
    poll_seconds: int = 2                  # fréquence de scan des processus
    ping_seconds: int = 60                 # fréquence de synchro serveur
    extra: dict = field(default_factory=dict)

    # ----- persistance -----------------------------------------------------
    @staticmethod
    def path() -> Path:
        return app_data_dir() / "config.json"

    @classmethod
    def load(cls) -> "Config":
        p = cls.path()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cfg = cls()
                for k in ("server_url", "api_key", "poll_seconds", "ping_seconds"):
                    if k in data:
                        setattr(cfg, k, data[k])
                cfg.extra = {k: v for k, v in data.items() if k not in vars(cfg)}
                return cfg
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        p = self.path()
        p.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False),
                     encoding="utf-8")

    # ----- helpers ---------------------------------------------------------
    @property
    def configured(self) -> bool:
        return bool(self.server_url.strip()) and bool(self.api_key.strip())

    def api_url(self, endpoint: str) -> str:
        return f"{self.server_url.rstrip('/')}/{endpoint.lstrip('/')}"
