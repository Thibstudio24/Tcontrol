"""État persistant de l'app : cache du serveur (mode hors ligne),
compteurs locaux et drapeaux de notification."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, fields

from .config import app_data_dir
from .logic import logical_day

DEFAULT_LIMIT = 7200          # 2 h si jamais aucune synchro n'a eu lieu
NOTIFY_THRESHOLDS = (600, 300, 0)   # 10 min, 5 min, écoulé


@dataclass
class State:
    # --- données synchronisées avec le serveur (cache) ---
    day: str = ""                  # jour logique courant (côté serveur si dispo)
    server_used: int = 0           # total validé par le serveur (toutes machines)
    limit: int = DEFAULT_LIMIT     # limite globale en secondes
    reset_hour: int = 0            # heure de reset quotidien
    processes: list = field(default_factory=list)   # noms normalisés (.exe)
    alias: str = ""
    blocked_server: bool = False   # le serveur a déclaré le blocage
    last_sync: str = ""            # ISO datetime du dernier ping réussi
    last_sync_ok: bool = False     # état courant de la connexion

    # --- compteurs locaux ---
    pending_delta: float = 0.0     # secondes jouées non encore envoyées
    pending_day: str = ""          # jour logique auquel appartient pending_delta
    notified: dict = field(default_factory=lambda: {str(t): False for t in NOTIFY_THRESHOLDS})
    kills_today: int = 0
    current_game: str = ""         # jeu actuellement détecté (pour l'UI)

    # --- admins enregistrés (déblocage hors ligne) ---
    cached_admins: dict = field(default_factory=dict)  # user -> hash pbkdf2

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    # ----- persistance ------------------------------------------------------
    @staticmethod
    def path():
        return app_data_dir() / "cache.json"

    @classmethod
    def load(cls) -> "State":
        p = cls.path()
        st = cls()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(st, k) and not k.startswith("_"):
                        setattr(st, k, v)
            except Exception:
                pass
        return st

    def save(self) -> None:
        with self._lock:
            data = {f.name: getattr(self, f.name)
                    for f in fields(self)
                    if not f.name.startswith("_")}
        try:
            self.path().write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
        except Exception:
            pass

    # ----- logique métier ---------------------------------------------------
    def process_set(self) -> set:
        return set(self.processes)

    def local_used(self) -> float:
        """Estimation locale du temps consommé aujourd'hui."""
        if self.pending_day and self.pending_day != self.day:
            return float(self.server_used)  # delta d'un autre jour : pas compté ici
        return self.server_used + self.pending_delta

    def remaining(self) -> float:
        return max(0.0, self.limit - self.local_used())

    def is_blocked(self) -> bool:
        return self.blocked_server or (self.limit > 0 and self.local_used() >= self.limit)

    def add_play_time(self, seconds: float) -> None:
        with self._lock:
            if not self.pending_day or self.pending_delta <= 0:
                self.pending_day = self.day
            self.pending_delta += seconds

    def on_ping_success(self, resp: dict) -> bool:
        """Applique la réponse du serveur. Retourne True si nouveau jour."""
        old_day = self.day
        with self._lock:
            self.day = resp.get("day", self.day)
            self.server_used = int(resp.get("used", self.server_used))
            self.limit = int(resp.get("limit", self.limit))
            self.reset_hour = int(resp.get("reset_hour", self.reset_hour))
            self.blocked_server = bool(resp.get("blocked", False))
            self.alias = resp.get("alias", self.alias) or ""
            procs = resp.get("processes")
            if isinstance(procs, list):
                self.processes = [str(p).strip().lower() for p in procs]
            # le delta vient d'être absorbé par le serveur
            self.pending_delta = 0.0
            self.pending_day = ""
            self.last_sync_ok = True
            day_changed = self.day != old_day
            if day_changed and old_day:
                # nouveau jour annoncé par le serveur → réarme notifications/compteurs
                self.notified = {str(t): False for t in NOTIFY_THRESHOLDS}
                self.kills_today = 0
        return day_changed

    def new_day_reset(self, day: str) -> None:
        with self._lock:
            self.day = day
            self.server_used = 0
            self.blocked_server = False
            self.pending_delta = 0.0
            self.pending_day = ""
            self.kills_today = 0
            self.notified = {str(t): False for t in NOTIFY_THRESHOLDS}

    # ----- notifications ------------------------------------------------------
    def check_notification(self) -> int | None:
        """Retourne le seuil (600/300/0) fraîchement franchi, ou None."""
        rem = self.remaining()
        with self._lock:
            for t in NOTIFY_THRESHOLDS:
                key = str(t)
                if not self.notified.get(key) and rem <= t:
                    self.notified[key] = True
                    if t == 0:
                        return 0
                    return t
        return None

    # ----- divers --------------------------------------------------------------
    def ensure_today(self, reset_hour: int | None = None) -> bool:
        """Si le jour logique a changé, remet les compteurs à zéro. Retourne True si reset."""
        rh = self.reset_hour if reset_hour is None else reset_hour
        today = logical_day(rh)
        if self.day and self.day != today:
            self.new_day_reset(today)
            return True
        if not self.day:
            self.day = today
        return False
