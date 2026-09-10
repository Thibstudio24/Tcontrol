"""Démarrage automatique avec Windows (clé de registre Run, par utilisateur)."""
from __future__ import annotations

import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Tcontrol"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    # mode dev : on enregistre python + script
    import __main__
    return f'"{sys.executable}" "{getattr(__main__, "__file__", "main.py")}"'


def is_supported() -> bool:
    return sys.platform.startswith("win")


def is_autostart_enabled() -> bool:
    if not is_supported():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_REG_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> bool:
    """Active ou retire le démarrage automatique. Retourne True si succès."""
    if not is_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP_REG_NAME, 0, winreg.REG_SZ, _exe_path())
            else:
                try:
                    winreg.DeleteValue(k, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
