"""Datos de mercado y análisis técnico (sin LLM)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core import elliott, indicators, marketdata, signals, trendlines, yahoo
from routers.common import analyze

router = APIRouter(prefix="/api", tags=["market"])

# Temporalidades del panel de sentimiento: (period, interval, resample)
_TF_CONFIG = {
    "1h": ("1mo", "60m", None),
    "4h": ("3mo", "60m", "4h"),
    "1d": ("1y", "1d", None),
}


@router.get("/search")
def search(q: str):
    return yahoo.search_query(q) if q else []


@router.get("/quote/{ticker}")
def quote(ticker: str):
    data = yahoo.get_quote(ticker)
    if data.get("price") is None:
        raise HTTPException(404, f"No se encontraron datos para '{ticker}'")
    return data


@router.get("/ohlcv/{ticker}")
def ohlcv(ticker: str, period: str = "1y", interval: str = "1d"):
    return yahoo.get_ohlcv(ticker, period=period, interval=interval)


@router.get("/news/{ticker}")
def news(ticker: str):
    return yahoo.get_news(ticker)


# Temporalidades que puede pedir una EMA en modo MTF: (period, interval, resample)
_TF_FETCH = {
    "1h": ("180d", "60m", None),
    "4h": ("360d", "60m", "4h"),
    "1d": ("3y", "1d", None),
    "1wk": ("10y", "1wk", None),
}
# Resolución relativa de cada intervalo (para saber si una EMA MTF es "mayor").
_RANK = {"5m": 1, "15m": 2, "30m": 2, "60m": 3, "1h": 3, "4h": 4, "1d": 5, "1wk": 6}


def _get_ohlcv(ticker: str, period: str, interval: str, prepost: bool = False) -> list[dict]:
    """OHLCV del gráfico. 4h no existe en yfinance → se reagrupa desde 60m.
    prepost=True añade pre-market/after-hours (solo afecta a intradía)."""
    if interval == "4h":
        return indicators.resample(
            yahoo.get_ohlcv(ticker, period=period, interval="60m", prepost=prepost), "4h"
        )
    return yahoo.get_ohlcv(ticker, period=period, interval=interval, prepost=prepost)


@router.get("/chart/{ticker}")
def chart(ticker: str, period: str = "1y", interval: str = "1d", prepost: bool = False):
    """Velas + indicadores del propio timeframe (sin EMAs)."""
    return indicators.chart_bundle(_get_ohlcv(ticker, period, interval, prepost))


@router.get("/ema/{ticker}")
def ema(ticker: str, length: int = 20, tf: str = "", period: str = "1y", interval: str = "1d", prepost: bool = False):
    """Una EMA para el gráfico. `tf` vacío = mismo timeframe; si es mayor, MTF."""
    length = max(1, min(int(length), 400))
    chart_df = indicators.frame(_get_ohlcv(ticker, period, interval, prepost))
    if chart_df.empty:
        return {"points": []}

    # Una EMA en temporalidad igual o menor que el gráfico = misma temporalidad.
    use_mtf = tf in _TF_FETCH and _RANK.get(tf, 9) > _RANK.get(interval, 0)
    if not use_mtf:
        points = indicators.ema_line(chart_df, chart_df, length)
    else:
        p, i, rule = _TF_FETCH[tf]
        tf_data = yahoo.get_ohlcv(ticker, period=p, interval=i, prepost=prepost)
        if rule:
            tf_data = indicators.resample(tf_data, rule)
        points = indicators.ema_line(chart_df, indicators.frame(tf_data), length)
    return {"points": points}


@router.get("/trendlines/{ticker}")
def trendlines_ep(ticker: str, period: str = "1y", interval: str = "1d", prepost: bool = False):
    """Líneas de tendencia detectadas (soporte/resistencia) para dibujar en el
    gráfico. Cada línea son 2 puntos {time,value} en el mismo formato que las
    velas del /chart, para que se alineen."""
    bars = _get_ohlcv(ticker, period, interval, prepost)
    lines = trendlines.detect(bars)
    if not lines:
        return {"lines": []}
    df = indicators.frame(bars)
    intraday = indicators._is_intraday(df)
    window = 150  # debe coincidir con trendlines.detect
    data = bars[-window:]
    idxs = list(df.index)[-len(data):]
    last = len(data) - 1
    out = []
    for ln in lines:
        i1 = ln["i1"]
        y1 = round(trendlines.value_at(ln, i1), 4)
        y2 = round(trendlines.value_at(ln, last), 4)
        out.append({
            "kind": ln["kind"],
            "touches": ln["touches"],
            # Para dibujar (mismo formato de tiempo que las velas del /chart).
            "points": [
                {"time": indicators._time(idxs[i1], intraday), "value": y1},
                {"time": indicators._time(idxs[last], intraday), "value": y2},
            ],
            # Para congelar la línea en una alerta (timestamps absolutos).
            "anchors": [
                {"t": int(idxs[i1].timestamp()), "p": y1},
                {"t": int(idxs[last].timestamp()), "p": y2},
            ],
        })
    return {"lines": out}


@router.get("/elliott/{ticker}")
def elliott_ep(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    prepost: bool = False,
    threshold: float = 0.05,
):
    """Conteo de ondas de Elliott para dibujar en el gráfico.

    `points` = polilínea de la estructura, `labels` = etiquetas 1-5 / A-B-C
    (marcadores) y `fibs` = niveles de la onda en curso. Los tiempos van en el
    mismo formato que las velas de /chart para que todo encaje.
    """
    bars = _get_ohlcv(ticker, period, interval, prepost)
    res = elliott.detect(bars, threshold=max(0.01, min(float(threshold), 0.5)))
    if not res:
        return {"found": False}

    df = indicators.frame(bars)
    intraday = indicators._is_intraday(df)
    idxs = list(df.index)

    points, labels = [], []
    for p, label in zip(res["pivots"], res["labels"], strict=False):
        i = min(p["index"], len(idxs) - 1)
        t = indicators._time(idxs[i], intraday)
        points.append({"time": t, "value": round(p["price"], 4)})
        if label != "0":  # el punto de arranque no se etiqueta
            labels.append({"time": t, "value": round(p["price"], 4), "text": label,
                           "kind": p["kind"]})

    return {
        "found": True,
        "pattern": res["pattern"],
        "up": res["up"],
        "current_wave": res["current_wave"],
        "completed_waves": res["completed_waves"],
        "confidence": res["confidence"],
        "rules": res["rules"],
        "threshold": res["threshold"],
        "points": points,
        "labels": labels,
        "fibs": res["fibs"],
    }


@router.get("/price/{ticker}")
def price(ticker: str):
    """Precio en tiempo real (Finnhub si hay clave, si no Yahoo)."""
    t = ticker.upper()
    return {
        "price": marketdata.realtime_prices([t]).get(t),
        "realtime": marketdata.realtime_available(),
    }


@router.get("/analysis/{ticker}")
def analysis(ticker: str, lang: str = "es"):
    q, ind, verdict = analyze(ticker, lang)
    if q.get("price") is None:
        raise HTTPException(404, f"No se encontraron datos para '{ticker}'")
    return {"quote": q, "indicators": ind, "verdict": verdict}


@router.get("/sentiment/{ticker}")
def sentiment(ticker: str, lang: str = "es"):
    out = {}
    for tf, (period, interval, rule) in _TF_CONFIG.items():
        try:
            data = yahoo.get_ohlcv(ticker, period=period, interval=interval)
            if rule:
                data = indicators.resample(data, rule)
            ind = indicators.compute(data)
            out[tf] = {
                "verdict": signals.evaluate(ind, lang),
                "rsi": ind.get("rsi14"),
                "price": ind.get("price"),
            }
        except Exception as e:
            out[tf] = {
                "verdict": {"score": 50, "label": "NEUTRAL", "signals": []},
                "error": str(e),
            }
    return out
