"""Boucle de surveillance : comptage, blocage, notifications, synchro."""
from __future__ import annotations

import getpass
import os
import platform
import queue
import threading
from datetime import datetime

from .config import Config
from .logic import logical_day
from .notify import notify_kill, notify_threshold
from .processes import find_running, kill_by_name
from .state import State
from .sync import SyncClient, SyncError


def get_identity() -> tuple[str, str]:
    """(nom d'utilisateur Windows, nom de machine)."""
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USERNAME", "inconnu")
    machine = platform.node() or "PC"
    return user or "inconnu", machine


class Monitor(threading.Thread):
    """Thread principal de surveillance.

    Émet des événements dans une queue consommée par l'interface :
      ("tick", None)                  — chaque cycle (rafraîchit le chrono)
      ("status", {"online":bool, "error":str|None})
      ("synced", dict)                — réponse serveur appliquée
      ("notify", 600|300|0)           — notification envoyée
      ("killed", "jeu.exe")           — un jeu a été fermé
      ("day_reset", None)             — nouveau jour logique
    """

    def __init__(self, cfg: Config, state: State, sync: SyncClient,
                 events: "queue.Queue"):
        super().__init__(daemon=True, name="TcontrolMonitor")
        self.cfg = cfg
        self.state = state
        self.sync = sync
        self.events = events
        self.stop_event = threading.Event()
        self._force_sync = threading.Event()
        self._last_running: list[str] = []
        self.user, self.machine = get_identity()

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self.stop_event.set()
        self._force_sync.set()

    def force_sync(self) -> None:
        self._force_sync.set()

    # ------------------------------------------------------------------
    def run(self) -> None:
        self.state.ensure_today()
        self._do_ping()  # synchro immédiate au démarrage
        ticks = 0
        save_every = max(1, round(15 / self.cfg.poll_seconds))
        ping_every = max(1, round(self.cfg.ping_seconds / self.cfg.poll_seconds))
        while not self.stop_event.is_set():
            self.stop_event.wait(self.cfg.poll_seconds)
            if self.stop_event.is_set():
                if self._force_sync.is_set():
                    self._do_ping()
                break
            ticks += 1
            try:
                self._tick(ticks, save_every, ping_every)
            except Exception as e:  # jamais de crash silencieux
                self.events.put(("status", {"online": None, "error": f"Erreur interne : {e}"}))
        self.state.save()

    # ------------------------------------------------------------------
    def _tick(self, ticks: int, save_every: int, ping_every: int) -> None:
        st = self.state

        if st.ensure_today():
            self.events.put(("day_reset", None))

        watched = st.process_set()
        running = find_running(watched)
        blocked = st.is_blocked()

        if blocked and running:
            for name in list(running.keys()):
                if kill_by_name(name):
                    st.kills_today += 1
                    notify_kill(name)
                    self.events.put(("killed", name))
            st.current_game = ""
        elif running:
            st.add_play_time(self.cfg.poll_seconds)
            st.current_game = sorted(running.keys())[0]
        else:
            st.current_game = ""
        self._last_running = sorted(running.keys())

        thr = st.check_notification()
        if thr is not None:
            notify_threshold(thr)
            self.events.put(("notify", thr))

        if ticks % save_every == 0:
            st.save()
        if ticks % ping_every == 0 or self._force_sync.is_set():
            self._force_sync.clear()
            self._do_ping()

        self.events.put(("tick", None))

    # ------------------------------------------------------------------
    def _do_ping(self) -> None:
        st = self.state
        try:
            resp = self.sync.ping(
                user=self.user,
                machine=self.machine,
                delta=int(st.pending_delta),
                day=st.pending_day or st.day or logical_day(st.reset_hour),
                running=self._last_running,
                blocked=st.is_blocked(),
            )
        except SyncError as e:
            st.last_sync_ok = False
            st.save()
            self.events.put(("status", {"online": False, "error": str(e)}))
            return

        day_changed = st.on_ping_success(resp)
        st.last_sync = datetime.now().strftime("%H:%M:%S")
        st.save()
        self.events.put(("status", {"online": True, "error": None}))
        self.events.put(("synced", resp))
        if day_changed:
            self.events.put(("day_reset", None))
