"""Indicadores calculados a mano (core.indicators).

Se testea contra propiedades conocidas, no contra valores mágicos: si algún
día se cambia la implementación, estos tests siguen siendo válidos.
"""

import pandas as pd

from core.indicators import bollinger, ema, macd, resample, rsi, sma


def test_rsi_100_en_serie_siempre_creciente():
    # Sin pérdidas, el RSI tiende a 100.
    serie = pd.Series(range(1, 40), dtype=float)
    r = rsi(serie).iloc[-1]
    assert round(r) == 100


def test_rsi_0_en_serie_siempre_decreciente():
    serie = pd.Series(range(40, 1, -1), dtype=float)
    r = rsi(serie).iloc[-1]
    assert round(r) == 0


def test_ema_reacciona_mas_rapido_que_sma():
    # Justo tras un escalón al alza, la EMA ya va por delante de la SMA.
    serie = pd.Series([10.0] * 10 + [20.0])
    assert ema(serie, 5).iloc[-1] > sma(serie, 5).iloc[-1]


def test_macd_hist_es_linea_menos_senal():
    serie = pd.Series(range(1, 60), dtype=float)
    line, signal, hist = macd(serie)
    assert abs((line.iloc[-1] - signal.iloc[-1]) - hist.iloc[-1]) < 1e-9


def test_bollinger_mid_es_la_media_y_las_bandas_la_rodean():
    serie = pd.Series(range(1, 40), dtype=float)
    upper, mid, lower = bollinger(serie, window=20)
    assert lower.iloc[-1] < mid.iloc[-1] < upper.iloc[-1]


def test_resample_agrega_velas_correctamente():
    # Dos horas de velas de 60m → una vela de 2h con OHLCV agregado.
    ohlcv = [
        {"date": "2024-01-01 09:00", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100},
        {"date": "2024-01-01 09:30", "open": 11, "high": 15, "low": 8, "close": 14, "volume": 200},
    ]
    out = resample(ohlcv, "2h")
    assert len(out) == 1
    vela = out[0]
    assert vela["open"] == 10       # primera
    assert vela["high"] == 15       # máximo
    assert vela["low"] == 8         # mínimo
    assert vela["close"] == 14      # última
    assert vela["volume"] == 300    # suma
