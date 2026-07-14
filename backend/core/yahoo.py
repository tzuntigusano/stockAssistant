"""Datos de Yahoo Finance vía yfinance (gratis, sin API key).

Escrito para yfinance 1.5.x: fast_info, el nuevo formato de noticias (anidado
en 'content') y yf.Search para la búsqueda.
"""

from __future__ import annotations

import yfinance as yf

from core.cache import get, set


def _f(value):
    """Convierte a float de forma segura (o None)."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_quote(ticker: str) -> dict:
    cache_key = f"quote:{ticker.upper()}"
    cached = get("quote", cache_key)
    if cached:
        return cached

    stock = yf.Ticker(ticker)
    fi = stock.fast_info  # rápido; propiedades documentadas de FastInfo

    def fget(attr):
        try:
            return _f(getattr(fi, attr))
        except Exception:
            return None

    # .info es más lento y a veces falla: lo envolvemos.
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    result = {
        "symbol": ticker.upper(),
        "name": info.get("shortName") or info.get("longName") or ticker.upper(),
        "price": fget("last_price"),
        "previous_close": fget("previous_close"),
        "day_high": fget("day_high"),
        "day_low": fget("day_low"),
        "open": fget("open"),
        "market_cap": info.get("marketCap") or fget("market_cap"),
        "pe_ratio": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_high": fget("year_high"),
        "fifty_two_low": fget("year_low"),
        "currency": info.get("currency") or getattr(fi, "currency", None) or "USD",
        "sector": info.get("sector"),
        "exchange": info.get("exchange"),
    }
    # Variación del día
    if result["price"] and result["previous_close"]:
        result["change"] = round(result["price"] - result["previous_close"], 4)
        result["change_pct"] = round((result["price"] / result["previous_close"] - 1) * 100, 2)

    set("quote", cache_key, result)
    return result


def get_ohlcv(ticker: str, period: str = "1y", interval: str = "1d", prepost: bool = False) -> list[dict]:
    cache_key = f"ohlcv:{ticker.upper()}:{period}:{interval}:{int(prepost)}"
    cached = get("ohlcv", cache_key)
    if cached:
        return cached

    stock = yf.Ticker(ticker)
    # prepost=True añade pre-market y after-hours (solo tiene efecto en intradía).
    # Yahoo falla a veces (límite de peticiones por IP, red, región). Al abrir una
    # ficha por primera vez (caché fría) el front dispara una ráfaga de llamadas y
    # Yahoo puede devolver 429. Degradamos a vacío en vez de propagar un 500; al
    # reintentar, la caché ya está caliente y se rellena.
    try:
        df = stock.history(period=period, interval=interval, prepost=prepost)
    except Exception:
        return []
    if df.empty:
        return []

    # En intradía conservamos la hora; en diario o superior basta la fecha.
    intraday = any(interval.endswith(s) for s in ("m", "h"))
    date_fmt = "%Y-%m-%d %H:%M" if intraday else "%Y-%m-%d"

    result = []
    for date, row in df.iterrows():
        result.append({
            "date": date.strftime(date_fmt),
            "open": _f(row["Open"]),
            "high": _f(row["High"]),
            "low": _f(row["Low"]),
            "close": _f(row["Close"]),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        })

    set("ohlcv", cache_key, result)
    return result


_FUND_FIELDS = [
    # Identidad / negocio
    "sector", "industry", "country", "fullTimeEmployees",
    # Valoración
    "marketCap", "enterpriseValue", "trailingPE", "forwardPE", "priceToBook",
    "pegRatio", "priceToSalesTrailing12Months", "enterpriseToEbitda",
    # Rentabilidad / márgenes
    "profitMargins", "grossMargins", "operatingMargins", "ebitdaMargins",
    "returnOnEquity", "returnOnAssets",
    # Crecimiento
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
    "totalRevenue", "ebitda", "netIncomeToCommon",
    # Balance / caja
    "totalCash", "totalDebt", "debtToEquity", "currentRatio", "quickRatio",
    "freeCashflow", "operatingCashflow",
    # BPA / dividendo
    "trailingEps", "forwardEps", "dividendYield", "payoutRatio",
    "fiveYearAvgDividendYield", "beta",
    # Analistas
    "targetMeanPrice", "targetHighPrice", "targetLowPrice",
    "numberOfAnalystOpinions", "recommendationKey", "recommendationMean",
    # Medias / rango
    "fiftyDayAverage", "twoHundredDayAverage", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
]


def get_fundamentals(ticker: str) -> dict:
    """Foto fundamental lo más completa posible (valoración, márgenes, deuda,
    crecimiento, analistas, próxima fecha de resultados y resumen del negocio)."""
    cache_key = f"fund:{ticker.upper()}"
    cached = get("fundamentals", cache_key)
    if cached is not None:
        return cached

    stock = yf.Ticker(ticker)
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    out: dict = {"symbol": ticker.upper(), "name": info.get("shortName") or info.get("longName")}
    for f in _FUND_FIELDS:
        out[f] = info.get(f)

    summary = info.get("longBusinessSummary")
    out["business_summary"] = summary[:600] if summary else None

    # Próxima fecha de resultados (catalizador cercano).
    try:
        cal = stock.calendar or {}
        ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if isinstance(ed, (list, tuple)) and ed:
            ed = ed[0]
        out["next_earnings"] = str(ed) if ed else None
    except Exception:
        out["next_earnings"] = None

    set("fundamentals", cache_key, out)
    return out


def get_news(ticker: str, count: int = 10) -> list[dict]:
    cache_key = f"news:{ticker.upper()}"
    cached = get("news", cache_key)
    if cached:
        return cached

    stock = yf.Ticker(ticker)
    try:
        raw = stock.news or []
    except Exception:
        raw = []

    result = []
    for item in raw[:count]:
        # yfinance 1.5.x anida los datos en 'content'; soportamos ambos formatos.
        c = item.get("content", item)
        title = c.get("title", "")
        if not title:
            continue
        provider = c.get("provider", {})
        publisher = provider.get("displayName") if isinstance(provider, dict) else item.get("publisher", "")
        url = ""
        canonical = c.get("canonicalUrl") or c.get("clickThroughUrl")
        if isinstance(canonical, dict):
            url = canonical.get("url", "")
        result.append({
            "title": title,
            "publisher": publisher or "",
            "link": url or item.get("link", ""),
            "published_at": c.get("pubDate") or c.get("displayTime") or "",
            "summary": c.get("summary", ""),
        })

    set("news", cache_key, result)
    return result


def search_query(query: str, count: int = 8) -> list[dict]:
    """Busca tickers por texto usando yf.Search."""
    try:
        res = yf.Search(query, max_results=count)
        quotes = res.quotes or []
    except Exception:
        return []

    out = []
    for q in quotes[:count]:
        if not q.get("symbol"):
            continue
        out.append({
            "symbol": q.get("symbol", ""),
            "name": q.get("shortname") or q.get("longname") or q.get("symbol", ""),
            "exchange": q.get("exchDisp") or q.get("exchange", ""),
            "type": q.get("quoteType") or q.get("typeDisp", ""),
        })
    return out
