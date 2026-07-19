"""Hilo que hace vivir a las carteras ficticias.

Corre un ciclo cada `INTERVAL` mientras el mercado de EE.UU. esté abierto y la
app encendida. Si la app estaba apagada NO recupera lo perdido: simplemente
arranca en el primer ciclo con el mercado abierto (por eso el primer ciclo se
lanza nada más arrancar si ya estamos en horario).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from core import notifier, paper_engine, paper_store
from core.breakout_monitor import market_open
from core.i18n import L

_NY = ZoneInfo("America/New_York")
_recent: deque = deque(maxlen=60)
_thread: threading.Thread | None = None
_lock = threading.Lock()
_state = {"enabled": True, "lang": "es", "last_run": None, "running": False}

INTERVAL = 900  # 15 min entre ciclos automáticos


def is_enabled() -> bool:
    return _state["enabled"]


def set_enabled(value: bool):
    _state["enabled"] = bool(value)


def set_lang(lang: str):
    if lang in ("es", "en"):
        _state["lang"] = lang


def recent() -> list[dict]:
    return list(_recent)


def _notify(events: dict, lang: str):
    """Un aviso de escritorio/Telegram por cada apertura o cierre."""
    for mode, evs in events.items():
        tag = L(lang, "Cartera normal", "Core portfolio") if mode == "normal" else L(
            lang, "Cartera rápida", "Fast portfolio")
        for e in evs:
            if e["kind"] == "entry":
                title = f"🧪 {tag} · " + L(lang, "nueva operación", "new trade")
            elif e["kind"] == "exit":
                title = f"🧪 {tag} · " + L(lang, "operación cerrada", "trade closed")
            else:
                continue
            try:
                notifier.notify(title, e["text"])
            except Exception:
                pass


def run_once(lang: str | None = None, source: str = "auto") -> dict:
    """Un ciclo completo de las dos carteras. `source` distingue el botón manual
    del automático en el diario. Serializado: nunca dos ciclos a la vez."""
    lang = lang or _state["lang"]
    if not _lock.acquire(blocking=False):
        return {"skipped": True, "reason": "busy"}
    _state["running"] = True
    try:
        result = paper_engine.run_cycle(lang)
        _state["last_run"] = time.time()
        stamp = datetime.now(_NY).strftime("%H:%M:%S")
        label = L(lang, "manual", "manual") if source == "manual" else L(lang, "automático", "automatic")
        mode_txt = "" if result["executed"] else L(
            lang, " · SIMULACRO (mercado cerrado, no se ejecuta nada)",
            " · DRY RUN (market closed, nothing executed)")
        for mode, evs in result["events"].items():
            paper_store.log(mode, "cycle", L(
                lang,
                f"Ciclo {label} a las {stamp} NY · {result['candidates']} candidatos analizados{mode_txt}",
                f"{label.capitalize()} cycle at {stamp} NY · {result['candidates']} candidates reviewed{mode_txt}",
            ))
            for e in evs:
                _recent.appendleft({**e, "mode": mode, "at": stamp})
        _notify(result["events"], lang)
        return result
    finally:
        _state["running"] = False
        _lock.release()


def _loop():
    # El primer ciclo va sin esperar: si arrancas la app con el mercado abierto,
    # las carteras se ponen al día en cuanto el backend levanta.
    while True:
        try:
            if _state["enabled"] and market_open():
                run_once(source="auto")
        except Exception:
            pass
        time.sleep(INTERVAL)


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="paper-monitor")
    _thread.start()


def status() -> dict:
    return {
        "enabled": _state["enabled"],
        "running": _state["running"],
        "market_open": market_open(),
        "last_run": _state["last_run"],
        "interval": INTERVAL,
        "ny_time": datetime.now(_NY).strftime("%H:%M"),
    }
