"""Vigilante en segundo plano: revisa las alertas periódicamente y lanza
notificaciones de Windows cuando se cumplen.

Disparo por flanco: cada alerta notifica una vez cuando pasa a cumplirse; se
"rearma" sola cuando deja de cumplirse, para no repetir el aviso en cada ciclo.
"""

from __future__ import annotations

import threading
import time

from core import notifier, scanner
from settings import NOTIFY_ENABLED, NOTIFY_INTERVAL

_thread: threading.Thread | None = None
_firing: set[int] = set()  # ids de alertas que ya estaban disparadas
_state = {"enabled": NOTIFY_ENABLED, "interval": NOTIFY_INTERVAL}


def is_enabled() -> bool:
    return _state["enabled"]


def set_enabled(value: bool):
    _state["enabled"] = bool(value)


def _loop():
    while True:
        try:
            if _state["enabled"]:
                triggered = scanner.scan()
                current: set[int] = set()
                for a in triggered:
                    current.add(a["id"])
                    if a["id"] not in _firing:
                        note = a.get("note") or ""
                        full = a["message"] + (f"\n📝 {note}" if note else "")
                        notifier.notify(f"{a['ticker']} · {a['label']}", full)
                _firing.clear()
                _firing.update(current)
        except Exception:
            pass
        time.sleep(_state["interval"])


def start():
    """Arranca el hilo vigilante (idempotente)."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="alert-monitor")
    _thread.start()
