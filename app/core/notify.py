"""Notifications toast Windows (avec repli gracieux)."""
from __future__ import annotations

import threading

_TOASTER = None
_ToastCls = None

try:  # fork maintenu de win10toast
    from win10toast_persist import ToastNotifier as _ToastCls  # type: ignore
except Exception:  # pragma: no cover
    try:
        from win10toast import ToastNotifier as _ToastCls  # type: ignore
    except Exception:
        _ToastCls = None

try:
    from plyer import notification as _plyer_notification  # type: ignore
except Exception:  # pragma: no cover
    _plyer_notification = None


def _get_toaster():
    global _TOASTER
    if _TOASTER is None and _ToastCls is not None:
        try:
            _TOASTER = _ToastCls()
        except Exception:
            _TOASTER = False  # ne plus réessayer
    return _TOASTER or None


def toast(title: str, message: str, duration: int = 6) -> None:
    """Affiche une notification. Jamais bloquant, jamais d'exception."""
    def _show():
        toaster = _get_toaster()
        if toaster is not None:
            try:
                toaster.show_toast(title, message, duration=duration, threaded=True)
                return
            except Exception:
                pass
        if _plyer_notification is not None:
            try:
                _plyer_notification.notify(title=title, message=message, timeout=duration)
            except Exception:
                pass

    threading.Thread(target=_show, daemon=True).start()


# --- messages prédéfinis -----------------------------------------------------

def notify_threshold(threshold: int) -> None:
    if threshold == 600:
        toast("Tcontrol — 10 minutes", "Il te reste 10 minutes de jeu aujourd'hui.")
    elif threshold == 300:
        toast("Tcontrol — 5 minutes",
              "Plus que 5 minutes ! Pense à sauvegarder ta partie.")
    elif threshold == 0:
        toast("Tcontrol — Temps écoulé",
              "Ton temps de jeu est écoulé pour aujourd'hui. "
              "Les jeux bloqués s'ouvriront à nouveau après le reset.", duration=10)


def notify_kill(name: str) -> None:
    toast("Tcontrol — Jeu bloqué",
          f"« {name} » a été fermé : le temps de jeu du jour est écoulé.")
