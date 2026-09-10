"""Icône de la zone de notification (system tray)."""
from __future__ import annotations

import threading


def _make_image(size: int = 64):
    """Petite horloge dessinée à la volée (aucune ressource externe requise)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size // 16
    d.ellipse((m, m, size - m, size - m), fill="#0e7490", outline="#22d3ee",
              width=max(2, size // 21))
    c = size / 2
    d.line((c, c, c, size * 0.27), fill="white", width=max(2, size // 16))
    d.line((c, c, size * 0.70, size * 0.58), fill="white", width=max(2, size // 16))
    return img


class TrayIcon:
    """Encapsule pystray ; se désactive silencieusement si indisponible."""

    def __init__(self, on_open, on_quit):
        self._icon = None
        self._thread = None
        try:
            import pystray
            self._pystray = pystray
            self._icon = pystray.Icon(
                "Tcontrol", _make_image(), "Tcontrol",
                menu=pystray.Menu(
                    pystray.MenuItem("Ouvrir Tcontrol", lambda *_: on_open(), default=True),
                    pystray.MenuItem("Quitter (admin)", lambda *_: on_quit()),
                ),
            )
        except Exception:
            self._icon = None

    @property
    def available(self) -> bool:
        return self._icon is not None

    def show(self) -> None:
        if self._icon is not None and (self._thread is None or not self._thread.is_alive()):
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()

    def hide(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
