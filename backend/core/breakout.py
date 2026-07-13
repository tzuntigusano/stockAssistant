"""Detección de rupturas alcistas sobre velas intradía.

La señal de una vela de rotura (como la de HIMS) son 3 cosas a la vez:
  1. El precio supera el techo de la consolidación (máximo reciente).
  2. Pico de volumen (RVOL) muy por encima de la media.
  3. Vela de rango grande (expansión respecto al rango medio ~ ATR).

Modo rápido/agresivo: exige rotura + vela verde + (volumen ALTO o expansión).
Se acepta algún falso positivo a cambio de avisar cuanto antes.
"""

from __future__ import annotations

DEFAULTS = {
    "level_lookback": 30,   # velas para el techo de consolidación (máx. reciente)
    "vol_window": 20,       # velas para la media de volumen / rango
    "vol_mult": 3.0,        # volumen de la vela / media  → pico
    "range_mult": 1.5,      # rango de la vela / rango medio → expansión
    "break_buffer": 0.05,   # % por encima del nivel para confirmar la rotura
    "min_bars": 25,
}


def context(bars: list[dict], cfg: dict | None = None) -> dict:
    """Contexto de las VELAS (lo que cambia despacio): nivel de resistencia,
    si el volumen ya está caliente y si hubo expansión de rango.
    Se combina luego con el precio EN VIVO en is_breakout()."""
    c = {**DEFAULTS, **(cfg or {})}
    if not bars or len(bars) < c["min_bars"]:
        return {"ok": False}

    last = bars[-1]
    prior = bars[:-1]
    n = len(prior)

    window = prior[-c["level_lookback"]:] if n >= c["level_lookback"] else prior
    resistance = max(b["high"] for b in window)

    volwin = prior[-c["vol_window"]:] if n >= c["vol_window"] else prior
    vols = [b["volume"] for b in volwin if b["volume"] > 0]
    vol_avg = sum(vols) / len(vols) if vols else 0.0
    ranges = [b["high"] - b["low"] for b in volwin]
    atr = sum(ranges) / len(ranges) if ranges else 0.0

    rvol = (last["volume"] / vol_avg) if vol_avg else 0.0
    expansion = ((last["high"] - last["low"]) / atr) if atr else 0.0

    return {
        "ok": True,
        "resistance": round(resistance, 4),
        "rvol": round(rvol, 1),
        "expansion": round(expansion, 1),
        "vol_ok": rvol >= c["vol_mult"],
        "expanded": expansion >= c["range_mult"],
        "break_buffer": c["break_buffer"],
    }


def is_breakout(ctx: dict, live_price: float) -> dict:
    """Dispara si el precio EN VIVO supera la resistencia y el contexto está
    caliente (volumen alto o expansión). Modo rápido/agresivo."""
    if not ctx or not ctx.get("ok") or live_price is None:
        return {"triggered": False}
    broke = live_price > ctx["resistance"] * (1 + ctx["break_buffer"] / 100)
    hot = ctx["vol_ok"] or ctx["expanded"]
    return {
        "triggered": broke and hot,
        "price": round(live_price, 2),
        "resistance": ctx["resistance"],
        "rvol": ctx["rvol"],
    }


def evaluate(bars: list[dict], cfg: dict | None = None) -> dict:
    c = {**DEFAULTS, **(cfg or {})}
    if not bars or len(bars) < c["min_bars"]:
        return {"ok": False, "triggered": False}

    last = bars[-1]
    prior = bars[:-1]
    n = len(prior)

    # Nivel = máximo de las últimas `level_lookback` velas previas.
    window = prior[-c["level_lookback"]:] if n >= c["level_lookback"] else prior
    resistance = max(b["high"] for b in window)

    # Media de volumen y de rango (proxy de ATR) de las velas previas.
    volwin = prior[-c["vol_window"]:] if n >= c["vol_window"] else prior
    vols = [b["volume"] for b in volwin if b["volume"] > 0]
    vol_avg = sum(vols) / len(vols) if vols else 0.0
    ranges = [b["high"] - b["low"] for b in volwin]
    atr = sum(ranges) / len(ranges) if ranges else 0.0

    price = last["close"]
    rvol = (last["volume"] / vol_avg) if vol_avg else 0.0
    expansion = ((last["high"] - last["low"]) / atr) if atr else 0.0

    broke = price > resistance * (1 + c["break_buffer"] / 100)
    green = last["close"] >= last["open"]
    spike = rvol >= c["vol_mult"]
    expanded = expansion >= c["range_mult"]

    triggered = broke and green and (spike or expanded)

    return {
        "ok": True,
        "triggered": triggered,
        "price": round(price, 2),
        "resistance": round(resistance, 2),
        "rvol": round(rvol, 1),
        "expansion": round(expansion, 1),
        "broke": broke,
        "green": green,
        "spike": spike,
        "expanded": expanded,
    }
