"""Máquina de estados de un 'setup': rotura → retest → rebote con volumen.

Determinista y SIN efectos: recibe el estado actual + las velas (ya cerradas) y
devuelve el estado siguiente y qué transición se ha disparado, para que el
notificador mande un aviso distinto en cada fase. La IA no interviene.

Vale para largos y cortos (en corto todo es en espejo: rotura a la baja,
pullback al nivel, rechazo bajista con volumen). El "nivel" es enchufable: hoy
una EMA; mañana una trendline con la misma máquina, cambiando solo `level_at()`.
"""

from __future__ import annotations

import pandas as pd

from core import indicators

# --- Estados ---
ARMED = "armed"        # esperando la rotura
BROKEN = "broken"      # rota; esperando el retest
RETEST = "retest"      # de vuelta en el nivel; esperando el rebote
CONFIRMED = "confirmed"  # rebote con volumen: setup confirmado (terminal)

# --- Eventos (transiciones que disparan aviso) ---
BREAK = "break"
RETEST_EV = "retest"
BOUNCE = "bounce"
INVALIDATED = "invalidated"

DEFAULTS = {
    "length": 50,          # EMA a vigilar
    "break_buffer": 0.1,   # % más allá del nivel para confirmar la rotura
    "retest_band": 0.5,    # cercanía al nivel que cuenta como toque (·ATR)
    "stop_buffer": 1.0,    # cierre más allá del nivel = invalidado (·ATR)
    "vol_mult": 1.5,       # RVOL mínimo del rebote
    "vol_window": 20,      # velas para media de volumen y ATR
    "min_bars": 30,
}


def ema_level(bars: list[dict], length: int) -> tuple[float, float]:
    """EMA en la última vela y en la anterior (para detectar el cruce)."""
    s = pd.Series([b["close"] for b in bars], dtype=float)
    e = indicators.ema(s, length)
    return float(e.iloc[-1]), float(e.iloc[-2])


def line_level(anchors: list[dict], bars: list[dict]) -> tuple[float, float]:
    """Valor de una trendline CONGELADA en la última vela y la anterior.

    `anchors` = [{"t": unix_s, "p": precio}, {"t": unix_s, "p": precio}]. El
    offset temporal absoluto se cancela (solo importan las diferencias), así que
    no hace falta preocuparse de zonas horarias mientras la conversión sea la
    misma que usó el endpoint al crear los anclas.
    """
    t1, p1 = anchors[0]["t"], anchors[0]["p"]
    t2, p2 = anchors[1]["t"], anchors[1]["p"]
    slope = (p2 - p1) / (t2 - t1) if t2 != t1 else 0.0

    def at(bar: dict) -> float:
        ts = pd.Timestamp(bar["date"]).timestamp()
        return p1 + slope * (ts - t1)

    return at(bars[-1]), at(bars[-2])


def _atr(bars: list[dict], window: int) -> float:
    win = bars[-window:]
    ranges = [b["high"] - b["low"] for b in win]
    return sum(ranges) / len(ranges) if ranges else 0.0


def _avg_vol(bars: list[dict], window: int) -> float:
    win = bars[-window:]
    vols = [b["volume"] for b in win if b["volume"] > 0]
    return sum(vols) / len(vols) if vols else 0.0


def advance(
    state: str,
    bars: list[dict],
    cfg: dict | None = None,
    level: float | None = None,
    prev_level: float | None = None,
) -> dict:
    """Evalúa la ÚLTIMA vela cerrada y devuelve el estado siguiente + evento.

    `event` es None si no hay transición. La máquina solo compara precio ↔ nivel:
    si `level`/`prev_level` vienen dados (trendline), se usan; si no, se calcula
    la EMA de `cfg["length"]`. Así el mismo motor sirve para EMA o trendline.
    """
    c = {**DEFAULTS, **(cfg or {})}
    short = c.get("direction") == "short"
    if not bars or len(bars) < c["min_bars"]:
        return {"ok": False, "state": state, "event": None}

    if level is None or prev_level is None:
        level, prev_level = ema_level(bars, c["length"])
    atr = _atr(bars, c["vol_window"])
    avg_vol = _avg_vol(bars, c["vol_window"])

    last, prev = bars[-1], bars[-2]
    close = last["close"]
    rvol = (last["volume"] / avg_vol) if avg_vol else 0.0
    bb = c["break_buffer"] / 100.0
    band = c["retest_band"] * atr
    stop = c["stop_buffer"] * atr

    if not short:
        broke = close > level * (1 + bb) and prev["close"] <= prev_level * (1 + bb)
        touch = last["low"] <= level + band
        bounce = close > last["open"] and close > level and rvol >= c["vol_mult"]
        invalid = close < level - stop
    else:
        broke = close < level * (1 - bb) and prev["close"] >= prev_level * (1 - bb)
        touch = last["high"] >= level - band
        bounce = close < last["open"] and close < level and rvol >= c["vol_mult"]
        invalid = close > level + stop

    base = {
        "ok": True,
        "level": round(level, 4),
        "rvol": round(rvol, 1),
        "price": round(close, 4),
    }

    def out(new_state: str, event: str | None) -> dict:
        return {**base, "state": new_state, "event": event}

    if state == ARMED:
        if broke:
            return out(BROKEN, BREAK)
    elif state == BROKEN:
        if invalid:
            return out(ARMED, INVALIDATED)
        if touch:
            return out(RETEST, RETEST_EV)
    elif state == RETEST:
        if invalid:
            return out(ARMED, INVALIDATED)
        if bounce:
            return out(CONFIRMED, BOUNCE)
    # CONFIRMED (terminal) o sin transición: se mantiene.
    return out(state, None)
