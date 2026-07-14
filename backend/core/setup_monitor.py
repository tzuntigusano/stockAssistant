"""Hilo vigilante de las alertas de 'setup' (rotura → retest → rebote).

Cada ciclo, por cada setup activo: baja sus velas (Yahoo, en la temporalidad de
la alerta), corre la máquina de estados (core.setup) y, si hay transición,
guarda el nuevo estado y manda un aviso DISTINTO según la fase (escritorio +
Telegram vía notifier). El estado persiste, así que sobrevive a reinicios.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from core import indicators, notifier, setup, setup_store, yahoo
from core.i18n import L

_NY = ZoneInfo("America/New_York")
_recent: deque = deque(maxlen=40)
_thread: threading.Thread | None = None
_state = {"enabled": True}

INTERVAL = 120  # s entre ciclos (la caché de Yahoo evita pegar de más)

# Temporalidad de la alerta → (period, interval, resample) para Yahoo.
_TF_FETCH = {
    "15m": ("30d", "15m", None),
    "1h": ("180d", "60m", None),
    "60m": ("180d", "60m", None),
    "4h": ("360d", "60m", "4h"),
    "1d": ("2y", "1d", None),
    "1wk": ("10y", "1wk", None),
}


def is_enabled() -> bool:
    return _state["enabled"]


def set_enabled(value: bool):
    _state["enabled"] = bool(value)


def recent() -> list[dict]:
    return list(_recent)


def _bars(ticker: str, tf: str) -> list[dict]:
    period, interval, rule = _TF_FETCH.get(tf, _TF_FETCH["1d"])
    data = yahoo.get_ohlcv(ticker, period=period, interval=interval)
    if rule:
        data = indicators.resample(data, rule)
    return data


def _phase_message(s: dict, r: dict) -> tuple[str, str]:
    """(título, cuerpo) del aviso, en el idioma guardado en la alerta."""
    lang = s.get("lang", "es")
    tkr = s["ticker"]
    lvl = f"EMA{s['length']} ({s['tf']})"
    up = s["direction"] != "short"
    ev = r["event"]
    if ev == setup.BREAK:
        title = f"🔨 {tkr} · " + L(lang, "Fase 1: rotura", "Phase 1: breakout")
        body = (
            L(lang, f"Rotura al alza de {lvl}", f"Broke above {lvl}")
            if up
            else L(lang, f"Rotura a la baja de {lvl}", f"Broke below {lvl}")
        )
    elif ev == setup.RETEST_EV:
        title = f"🎯 {tkr} · " + L(lang, "Fase 2: retest", "Phase 2: retest")
        body = L(lang, f"Retest de {lvl} en curso", f"Retesting {lvl}")
    elif ev == setup.BOUNCE:
        title = f"✅ {tkr} · " + L(lang, "Fase 3: rebote confirmado", "Phase 3: bounce confirmed")
        vol = f"RVOL {r['rvol']}×"
        body = (
            L(lang, f"Rebote con volumen ({vol})", f"Bounce with volume ({vol})")
            if up
            else L(lang, f"Rechazo bajista con volumen ({vol})", f"Bearish rejection with volume ({vol})")
        )
    else:  # INVALIDATED
        title = f"⚠️ {tkr} · " + L(lang, "Setup invalidado", "Setup invalidated")
        body = L(lang, f"Cierre fuera de {lvl}; vuelve a esperar la rotura",
                 f"Closed beyond {lvl}; waiting for the breakout again")
    return title, body


def scan_once() -> list[dict]:
    fired = []
    for s in setup_store.list_active():
        try:
            bars = _bars(s["ticker"], s["tf"])
            if len(bars) < setup.DEFAULTS["min_bars"]:
                continue
            cfg = {"direction": s["direction"], "length": s["length"]}
            r = setup.advance(s["state"], bars, cfg)
            if not r.get("ok") or not r["event"]:
                continue
            last_bar = bars[-1].get("date", "")
            setup_store.update_state(s["id"], r["state"], last_bar)
            title, body = _phase_message(s, r)
            event = {
                "id": s["id"],
                "ticker": s["ticker"],
                "phase": r["state"],
                "event": r["event"],
                "at": datetime.now(_NY).strftime("%H:%M:%S"),
                "title": title,
                "message": body,
            }
            _recent.appendleft(event)
            fired.append(event)
            notifier.notify(title, body)
        except Exception:
            pass
    return fired


def _loop():
    while True:
        try:
            if _state["enabled"]:
                scan_once()
        except Exception:
            pass
        time.sleep(INTERVAL)


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="setup-monitor")
    _thread.start()


def status() -> dict:
    return {"enabled": _state["enabled"], "active": len(setup_store.list_active())}
