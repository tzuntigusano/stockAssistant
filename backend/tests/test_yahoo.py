"""Resiliencia de la capa de datos de Yahoo.

Regresión: al abrir una ficha por primera vez (caché fría) el front dispara una
ráfaga de llamadas y Yahoo puede devolver 429. get_ohlcv debe degradar a [] en
vez de propagar la excepción (que se convertía en un 500 al buscar un stock).
"""

import core.yahoo as yahoo


class _FakeTicker:
    def __init__(self, *args, **kwargs):
        pass

    def history(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests (simulado)")


def test_get_ohlcv_degrada_a_vacio_si_yahoo_falla(monkeypatch):
    # Fuerza caché fría y un Yahoo que lanza excepción.
    monkeypatch.setattr(yahoo, "get", lambda *a, **k: None)
    monkeypatch.setattr(yahoo.yf, "Ticker", _FakeTicker)
    assert yahoo.get_ohlcv("ZZZZ", period="1mo", interval="1d") == []
