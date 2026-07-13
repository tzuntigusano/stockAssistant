"""Radar de rupturas EN DIRECTO sobre la lista del radar (radarwatch).

Modo híbrido:
  - CONTEXTO (nivel de resistencia, volumen medio, ATR) desde velas de Yahoo,
    refrescado cada ~60 s (cambia despacio, el retraso no importa).
  - PRECIO EN VIVO comprobado cada ~8 s (Finnhub si hay clave → instantáneo;
    si no, Yahoo). Cuando el precio en vivo rompe la resistencia y el contexto
    está caliente (volumen/expansión) → notificación de Windows al instante.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from core import breakout, marketdata, notifier, radarwatch
from settings import (
    BREAKOUT_ENABLED,
    BREAKOUT_INTERVAL,
    CONTEXT_INTERVAL,
    REALTIME_INTERVAL,
)

_NY = ZoneInfo("America/New_York")
_state = {"enabled": BREAKOUT_ENABLED}
_recent: deque = deque(maxlen=30)
_last_fired: dict[str, float] = {}
_context: dict[str, dict] = {}      # ticker -> contexto de velas
_last_ctx_refresh = 0.0
_thread: threading.Thread | None = None

COOLDOWN = 1800  # no repetir el aviso del mismo valor en 30 min


def is_enabled() -> bool:
    return _state["enabled"]


def set_enabled(value: bool):
    _state["enabled"] = bool(value)


def recent() -> list[dict]:
    return list(_recent)


def clear():
    _recent.clear()


def _interval() -> int:
    """Ritmo del bucle: rápido si hay tiempo real, lento si solo Yahoo.

    Con Finnhub gratis (~60 llamadas/min) el ritmo se relaja si hay muchos
    valores, para no superar el límite (cada valor = 1 llamada por ciclo).
    """
    if not marketdata.realtime_available():
        return BREAKOUT_INTERVAL
    n = len(radarwatch.tickers()) or 1
    safe = -(-n * 60 // 55)  # ceil(n*60/55): mantiene <= ~55 llamadas/min
    return max(REALTIME_INTERVAL, safe)


def market_open(now: datetime | None = None) -> bool:
    now = now or datetime.now(_NY)
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes <= 16 * 60  # 09:30–16:00 hora de Nueva York


def scan_once(force: bool = False) -> list[dict]:
    """Un ciclo: refresca contexto si toca y comprueba precio en vivo."""
    global _last_ctx_refresh
    tickers = radarwatch.tickers()
    if not tickers:
        return []
    if not force and not market_open():
        return []

    now = time.time()
    # Refresca el contexto (velas de Yahoo) si está caduco.
    if force or not _context or now - _last_ctx_refresh > CONTEXT_INTERVAL:
        try:
            bars_by = marketdata.recent_bars(tickers, interval="1m", period="1d")
            for t in tickers:
                _context[t] = breakout.context(bars_by.get(t, []))
            _last_ctx_refresh = now
        except Exception:
            pass

    prices = marketdata.realtime_prices(tickers)

    fired = []
    for t in tickers:
        ctx = _context.get(t)
        price = prices.get(t)
        if not ctx or not ctx.get("ok") or price is None:
            continue
        res = breakout.is_breakout(ctx, price)
        if not res["triggered"]:
            continue
        if now - _last_fired.get(t, 0) < COOLDOWN:
            continue
        _last_fired[t] = now
        event = {
            "ticker": t,
            "price": res["price"],
            "resistance": res["resistance"],
            "rvol": res["rvol"],
            "at": datetime.now(_NY).strftime("%H:%M:%S"),
            "message": f"Rotura de {res['resistance']} → {res['price']} · volumen {res['rvol']}×",
        }
        _recent.appendleft(event)
        fired.append(event)
        notifier.notify(f"🚀 {t} · Rotura alcista", event["message"])
    return fired


def _loop():
    while True:
        try:
            if _state["enabled"]:
                scan_once()
        except Exception:
            pass
        time.sleep(_interval())


def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="breakout-monitor")
    _thread.start()


def status() -> dict:
    rt = marketdata.realtime_available()
    return {
        "enabled": _state["enabled"],
        "interval": _interval(),
        "realtime": rt,
        "provider": marketdata.realtime_provider(),
        "market_open": market_open(),
        "watchlist": radarwatch.tickers(),
    }
