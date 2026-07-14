"""Máquina de estados del setup rotura → retest → rebote (core.setup).

Es el 'cerebro' de la alerta: merece tests que fijen cada transición en largo y
en corto. Se construyen velas sintéticas con una base plana (EMA ≈ precio) y se
añade la vela de cada escenario.
"""

from core import setup


def _bar(close, open_=None, high=None, low=None, volume=1000.0):
    open_ = close if open_ is None else open_
    high = max(open_, close) + 0.5 if high is None else high
    low = min(open_, close) - 0.5 if low is None else low
    return {"open": open_, "high": high, "low": low, "close": close, "volume": volume}


def _flat(n=40, price=100.0, volume=1000.0):
    return [_bar(price, price, price + 0.5, price - 0.5, volume) for _ in range(n)]


# --- LARGOS ---

def test_largo_rotura():
    bars = _flat() + [_bar(103, open_=100, high=103.5, low=100)]
    r = setup.advance(setup.ARMED, bars, {"direction": "long"})
    assert r["state"] == setup.BROKEN
    assert r["event"] == setup.BREAK


def test_largo_no_rompe_si_ya_estaba_encima():
    # Precio pegado a la EMA, sin cruce fresco: no dispara.
    bars = _flat() + [_bar(100.05)]
    r = setup.advance(setup.ARMED, bars, {"direction": "long"})
    assert r["event"] is None
    assert r["state"] == setup.ARMED


def test_largo_retest():
    # Tras romper, el precio recae y su mínimo toca la banda del nivel.
    bars = _flat() + [_bar(104), _bar(103), _bar(101.5, open_=102.5, high=102.6, low=100.3)]
    r = setup.advance(setup.BROKEN, bars, {"direction": "long"})
    assert r["state"] == setup.RETEST
    assert r["event"] == setup.RETEST_EV


def test_largo_rebote_con_volumen():
    # Vela verde que cierra sobre el nivel con volumen alto.
    bars = _flat() + [_bar(103), _bar(101), _bar(104, open_=101, high=104.5, low=100.5, volume=4000)]
    r = setup.advance(setup.RETEST, bars, {"direction": "long", "vol_mult": 1.5})
    assert r["state"] == setup.CONFIRMED
    assert r["event"] == setup.BOUNCE
    assert r["rvol"] >= 1.5


def test_largo_rebote_sin_volumen_no_confirma():
    bars = _flat() + [_bar(103), _bar(101), _bar(104, open_=101, high=104.5, low=100.5, volume=1000)]
    r = setup.advance(setup.RETEST, bars, {"direction": "long", "vol_mult": 1.5})
    assert r["event"] is None
    assert r["state"] == setup.RETEST


def test_largo_invalidado():
    bars = _flat() + [_bar(104), _bar(97, open_=100, high=100, low=96.5)]
    r = setup.advance(setup.BROKEN, bars, {"direction": "long"})
    assert r["state"] == setup.ARMED
    assert r["event"] == setup.INVALIDATED


# --- CORTOS (espejo) ---

def test_corto_rotura_a_la_baja():
    bars = _flat() + [_bar(97, open_=100, high=100, low=96.5)]
    r = setup.advance(setup.ARMED, bars, {"direction": "short"})
    assert r["state"] == setup.BROKEN
    assert r["event"] == setup.BREAK


def test_corto_rebote_bajista_con_volumen():
    # Vela roja que cierra bajo el nivel con volumen: rechazo bajista.
    bars = _flat() + [_bar(97), _bar(99), _bar(96, open_=99, high=99.5, low=95.5, volume=4000)]
    r = setup.advance(setup.RETEST, bars, {"direction": "short", "vol_mult": 1.5})
    assert r["state"] == setup.CONFIRMED
    assert r["event"] == setup.BOUNCE


# --- Guardas ---

def test_pocas_velas_no_evalua():
    r = setup.advance(setup.ARMED, _flat(10), {"direction": "long"})
    assert r["ok"] is False


def test_line_level_interpola_la_trendline():
    import pandas as pd

    ts1 = pd.Timestamp("2026-01-01").timestamp()
    ts2 = pd.Timestamp("2026-01-02").timestamp()
    anchors = [{"t": ts1, "p": 100.0}, {"t": ts2, "p": 110.0}]
    bars = [{"date": "2026-01-01"}, {"date": "2026-01-02"}]
    level, prev = setup.line_level(anchors, bars)
    assert round(level, 2) == 110.0  # última vela
    assert round(prev, 2) == 100.0   # anterior
