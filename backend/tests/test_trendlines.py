"""Detección de líneas de tendencia (core.trendlines).

Se construye un zigzag cuyos mínimos descansan sobre una recta ascendente y se
comprueba que la detección encuentra ese soporte con varios toques.
"""

from core import trendlines


def _bar(low, high, close=None, open_=None, volume=1000.0):
    close = (low + high) / 2 if close is None else close
    open_ = close if open_ is None else open_
    return {"open": open_, "high": high, "low": low, "close": close, "volume": volume}


def _zigzag():
    """60 velas: mínimos sobre la recta soporte(i)=100+0.5·i; picos por encima."""
    bars = []
    for i in range(60):
        base = 100 + 0.5 * i
        phase = i % 10
        if phase == 0:  # valle: toca el soporte
            bars.append(_bar(base, base + 1.0, close=base + 0.8))
        elif phase == 5:  # pico
            bars.append(_bar(base + 4, base + 6, close=base + 5))
        else:
            bars.append(_bar(base + 2, base + 3.5, close=base + 2.8))
    return bars


def test_detecta_soporte_ascendente():
    lines = trendlines.detect(_zigzag(), k=3)
    sup = [ln for ln in lines if ln["kind"] == "support"]
    assert sup, "no encontró soporte"
    assert sup[0]["touches"] >= 3
    assert sup[0]["slope"] > 0  # ascendente


def test_pocas_velas_no_detecta():
    assert trendlines.detect([], k=3) == []
