"""Notificaciones de escritorio multiplataforma.

- Windows: toast nativo (windows-toasts), modo "recordatorio" (se queda fijo).
- macOS: `osascript` (display notification) → Centro de notificaciones.
- Linux: `notify-send`.
Degrada con elegancia si no hay canal local (siempre queda Telegram si hay bot).
"""

from __future__ import annotations

import shutil
import subprocess
import sys

_SYS = sys.platform  # 'win32' | 'darwin' | 'linux'

# --- Windows: toast opcional (solo se importa en Windows) ---
_toaster = None
_ToastScenario = None
if _SYS == "win32":
    try:
        from windows_toasts import Toast, ToastScenario, WindowsToaster

        _toaster = WindowsToaster("Analizador de Acciones")
        _ToastScenario = ToastScenario
    except Exception:  # pragma: no cover - depende del entorno
        _toaster = None


def _local_supported() -> bool:
    if _SYS == "win32":
        return _toaster is not None
    if _SYS == "darwin":
        return shutil.which("osascript") is not None
    return shutil.which("notify-send") is not None


SUPPORTED = _local_supported()


def _as_str(s: str) -> str:
    """Cadena escapada para AppleScript (entre comillas dobles)."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _show_local(title: str, message: str, persistent: bool) -> bool:
    """Muestra una notificación de escritorio según el SO. True si lo logró."""
    try:
        if _SYS == "win32":
            if not _toaster:
                return False
            toast = Toast()
            toast.text_fields = [title, message]
            if persistent and _ToastScenario is not None:
                toast.scenario = _ToastScenario.Reminder
            _toaster.show_toast(toast)
            return True

        if _SYS == "darwin":
            if not shutil.which("osascript"):
                return False
            script = f"display notification {_as_str(message)} with title {_as_str(title)}"
            subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
            return True

        # Linux (y otros): notify-send
        if shutil.which("notify-send"):
            args = ["notify-send"]
            if persistent:
                args += ["-t", "0"]  # sin timeout = se queda hasta cerrarla
            args += [title, message]
            subprocess.run(args, check=False, capture_output=True)
            return True
    except Exception:
        pass
    return False


def notify(title: str, message: str, persistent: bool = True) -> bool:
    """Avisa por TODOS los canales: notificación de escritorio (según SO) +
    Telegram si hay bot. Devuelve True si al menos un canal lo envió."""
    sent = _show_local(title, message, persistent)
    try:
        from core import telegram

        if telegram.send(title, message):
            sent = True
    except Exception:
        pass
    return sent
