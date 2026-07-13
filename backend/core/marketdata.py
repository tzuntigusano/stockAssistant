"""Fuente de datos de mercado intradía — PLUGGABLE.

Hoy usa Yahoo Finance (gratis, con retraso y velas de 1 min como mínimo).
El diseño deja el enchufe listo para un proveedor en TIEMPO REAL (Finnhub,
Alpaca…): basta con añadir su función y ampliar el `if` de recent_bars().
"""

from __future__ import annotations

import httpx
import pandas as pd
import yfinance as yf

from settings import FINNHUB_API_KEY


def _extract(data, ticker: str):
    """Saca el sub-DataFrame plano de un ticker, tolerando columnas MultiIndex
    en cualquier orden ((ticker, campo) o (campo, ticker))."""
    cols = data.columns
    if isinstance(cols, pd.MultiIndex):
        if ticker in set(cols.get_level_values(0)):
            return data[ticker]
        if ticker in set(cols.get_level_values(1)):
            return data.xs(ticker, axis=1, level=1)
        return None
    return data  # columnas planas (un solo ticker)


def _df_to_bars(df) -> list[dict]:
    if df is None or df.empty:
        return []
    bars = []
    for idx, row in df.iterrows():
        try:
            c = float(row["Close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c != c:  # NaN
            continue
        bars.append({
            "t": idx.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": c,
            "volume": float(row["Volume"]) if row["Volume"] == row["Volume"] else 0.0,
        })
    return bars


def _yahoo_recent(tickers: list[str], interval: str, period: str) -> dict[str, list[dict]]:
    """Descarga en UNA llamada las velas recientes de todos los tickers."""
    if not tickers:
        return {}
    data = yf.download(
        tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )
    out: dict[str, list[dict]] = {}
    for t in tickers:
        try:
            out[t] = _df_to_bars(_extract(data, t))
        except Exception:
            out[t] = []
    return out


def recent_bars(
    tickers: list[str], interval: str = "1m", period: str = "1d"
) -> dict[str, list[dict]]:
    """Velas de CONTEXTO (nivel, volumen medio, ATR). Yahoo basta aquí."""
    return _yahoo_recent(tickers, interval, period)


# --------------------------------------------------------------------------
#  Precio EN TIEMPO REAL (para detectar la rotura al instante)
# --------------------------------------------------------------------------
def realtime_available() -> bool:
    return bool(FINNHUB_API_KEY)


def realtime_provider() -> str:
    return "finnhub" if FINNHUB_API_KEY else "yahoo"


def _finnhub_price(ticker: str) -> float | None:
    r = httpx.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": ticker, "token": FINNHUB_API_KEY},
        timeout=8,
    )
    r.raise_for_status()
    c = r.json().get("c")
    return float(c) if c else None


def _yahoo_price(ticker: str) -> float | None:
    try:
        fi = yf.Ticker(ticker).fast_info
        return float(fi.last_price)
    except Exception:
        return None


def realtime_prices(tickers: list[str]) -> dict[str, float | None]:
    """Precio actual por ticker. Finnhub si hay clave (instantáneo), si no Yahoo."""
    out: dict[str, float | None] = {}
    for t in tickers:
        try:
            out[t] = _finnhub_price(t) if FINNHUB_API_KEY else _yahoo_price(t)
        except Exception:
            out[t] = None
    return out
