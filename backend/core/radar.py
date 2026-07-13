"""Radar de oportunidades técnicas (screener de rompimientos alcistas).

Cómo funciona:
  1. Reúne un universo de candidatos EN VIVO desde listas dinámicas de Yahoo
     (yf.screen) + la watchlist del usuario + una lista propia.
  2. Sobre cada candidato calcula una serie de criterios de confluencia
     (rompimiento, volumen, momentum, fuerza de tendencia, etc.).
  3. Puntúa 0-100 según los pesos configurables y los rankea.

Es un buscador determinista y transparente: NO predice, señala configuraciones
técnicas favorables. La IA solo las explica aparte.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from core import indicators, watchlist, yahoo
from core.i18n import L

# Listas dinámicas de Yahoo que ofrecemos como fuentes de candidatos (es, en).
PREDEFINED = {
    "day_gainers": ("Mayores subidas del día", "Top gainers today"),
    "most_actives": ("Más activos (volumen)", "Most active (volume)"),
    "small_cap_gainers": ("Small caps al alza", "Small-cap gainers"),
    "aggressive_small_caps": ("Small caps agresivas", "Aggressive small caps"),
    "growth_technology_stocks": ("Tecnológicas de crecimiento", "Growth tech stocks"),
    "undervalued_growth_stocks": ("Crecimiento infravalorado", "Undervalued growth"),
}

DEFAULT_CONFIG = {
    "sources": {
        "predefined": ["day_gainers", "small_cap_gainers", "most_actives"],
        "watchlist": True,
        "custom": [],
    },
    "per_source": 40,
    "max_universe": 80,
    "weights": {
        "donchian": 2,
        "volume": 2,
        "rsi": 1,
        "macd": 1,
        "adx": 2,
        "ema": 1,
        "high52": 1,
        "rel_strength": 2,
        "obv": 1,
        "bollinger": 1,
    },
    "params": {
        "donchian_n": 20,
        "vol_mult": 1.5,
        "vol_window": 20,
        "rsi_thr": 55,
        "adx_thr": 20,
        "near_high_pct": 3.0,
        "atr_min_pct": 2.0,
        "rel_lookback": 20,
        "benchmark": "SPY",
        "min_price": 1.0,
    },
    "min_score": 40,
    "max_results": 25,
}


def _merge(defaults: dict, override: dict | None) -> dict:
    """Fusión superficial por secciones conocidas."""
    if not override:
        return {**defaults}
    cfg = {**defaults}
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(defaults.get(key), dict):
            cfg[key] = {**defaults[key], **val}
        else:
            cfg[key] = val
    return cfg


def sources(lang: str = "es") -> list[dict]:
    return [{"key": k, "label": L(lang, es, en)} for k, (es, en) in PREDEFINED.items()]


def _sf(value) -> float | None:
    """Float seguro (None si NaN/inválido)."""
    try:
        f = float(value)
        return f if f == f else None  # descarta NaN
    except (TypeError, ValueError):
        return None


def _universe(cfg: dict) -> dict[str, str]:
    tickers: dict[str, str] = {}
    src = cfg["sources"]
    for key in src.get("predefined", []):
        if key not in PREDEFINED:
            continue
        try:
            r = yf.screen(key, count=cfg["per_source"])
            for q in r.get("quotes", []):
                sym = q.get("symbol")
                if sym:
                    tickers.setdefault(sym.upper(), q.get("shortName") or sym)
        except Exception:
            continue
    if src.get("watchlist"):
        for s in watchlist.tickers():
            tickers.setdefault(s.upper(), s)
    for s in src.get("custom", []):
        if s:
            tickers.setdefault(s.upper(), s.upper())
    # Acota el tamaño para que el escaneo no tarde demasiado.
    return dict(list(tickers.items())[: cfg["max_universe"]])


def _benchmark_return(benchmark: str, lookback: int) -> float:
    try:
        o = yahoo.get_ohlcv(benchmark, period="6mo")
        closes = [c["close"] for c in o]
        if len(closes) > lookback:
            return (closes[-1] / closes[-1 - lookback] - 1) * 100
    except Exception:
        pass
    return 0.0


def _score(
    sym: str, name: str, cfg: dict, bench_ret: float, apply_filters: bool = True, lang: str = "es"
) -> dict | None:
    try:
        ohlcv = yahoo.get_ohlcv(sym, period="1y")
    except Exception:
        return None
    if not ohlcv or len(ohlcv) < 40:
        return None

    df = indicators.frame(ohlcv)
    close = df["close"]
    price = _sf(close.iloc[-1])
    if price is None:
        return None

    p, w = cfg["params"], cfg["weights"]
    if apply_filters and price < p["min_price"]:
        return None

    # --- Métricas ---
    ema20 = _sf(indicators.ema(close, 20).iloc[-1])
    ema50 = _sf(indicators.ema(close, 50).iloc[-1])
    rsi = _sf(indicators.rsi(close, 14).iloc[-1])
    _, _, hist = indicators.macd(close)
    hist_v = _sf(hist.iloc[-1])
    atr = _sf(indicators.atr(df, 14).iloc[-1])
    atr_pct = (atr / price * 100) if atr else None
    bb_up = _sf(indicators.bollinger(close)[0].iloc[-1])
    adx_s, pdi_s, mdi_s = indicators.adx(df, 14)
    adx_v, pdi_v, mdi_v = _sf(adx_s.iloc[-1]), _sf(pdi_s.iloc[-1]), _sf(mdi_s.iloc[-1])
    obv_s = indicators.obv(df)
    n = int(p["donchian_n"])
    obv_now, obv_prev = _sf(obv_s.iloc[-1]), _sf(obv_s.iloc[-1 - n]) if len(obv_s) > n else None

    donchian_high = _sf(df["high"].iloc[-(n + 1):-1].max()) if len(df) > n else None
    vol = df["volume"]
    vol_ma = _sf(vol.rolling(int(p["vol_window"])).mean().iloc[-1])
    vol_ratio = (float(vol.iloc[-1]) / vol_ma) if vol_ma else None
    high52 = _sf(df["high"].max())
    lb = int(p["rel_lookback"])
    stock_ret = (price / _sf(close.iloc[-1 - lb]) - 1) * 100 if len(close) > lb and _sf(close.iloc[-1 - lb]) else None
    rel = (stock_ret - bench_ret) if stock_ret is not None else None

    # --- Filtro de volatilidad (que un +10% sea plausible) ---
    if apply_filters and atr_pct is not None and atr_pct < p["atr_min_pct"]:
        return None

    # --- Criterios de confluencia (peso 0 = desactivado) ---
    checks: dict[str, tuple[bool, str]] = {
        "donchian": (
            donchian_high is not None and price > donchian_high,
            L(lang, f"Cierre sobre máximo de {n} sesiones", f"Close above {n}-session high"),
        ),
        "volume": (
            vol_ratio is not None and vol_ratio >= p["vol_mult"],
            L(lang, f"Volumen {vol_ratio:.1f}× la media", f"Volume {vol_ratio:.1f}× the average")
            if vol_ratio else L(lang, "Volumen alto", "High volume"),
        ),
        "rsi": (rsi is not None and rsi >= p["rsi_thr"],
                f"RSI {rsi:.0f}" if rsi else L(lang, "RSI fuerte", "Strong RSI")),
        "macd": (hist_v is not None and hist_v > 0, L(lang, "MACD alcista", "Bullish MACD")),
        "adx": (
            adx_v is not None and pdi_v is not None and mdi_v is not None
            and adx_v >= p["adx_thr"] and pdi_v > mdi_v,
            f"ADX {adx_v:.0f} (+DI>−DI)" if adx_v else L(lang, "Tendencia fuerte", "Strong trend"),
        ),
        "ema": (
            ema20 is not None and ema50 is not None and price > ema20 > ema50,
            L(lang, "Sobre EMA20 > EMA50", "Above EMA20 > EMA50"),
        ),
        "high52": (
            high52 is not None and price >= high52 * (1 - p["near_high_pct"] / 100),
            L(lang, "Cerca de máximos de 52 sem", "Near 52-week highs"),
        ),
        "rel_strength": (
            rel is not None and rel > 0,
            L(lang, f"Más fuerte que {p['benchmark']} (+{rel:.1f} pp)",
              f"Stronger than {p['benchmark']} (+{rel:.1f} pp)")
            if rel else L(lang, "Fuerza relativa", "Relative strength"),
        ),
        "obv": (
            obv_now is not None and obv_prev is not None and obv_now > obv_prev,
            L(lang, "OBV al alza (acumulación)", "OBV rising (accumulation)"),
        ),
        "bollinger": (
            bb_up is not None and price > bb_up,
            L(lang, "Cierre sobre banda de Bollinger", "Close above Bollinger band"),
        ),
    }

    total_w = sum(v for v in w.values() if v > 0)
    if total_w == 0:
        return None
    got = sum(w.get(k, 0) for k, (passed, _) in checks.items() if passed and w.get(k, 0) > 0)
    score = round(got / total_w * 100)
    passed = [label for k, (ok, label) in checks.items() if ok and w.get(k, 0) > 0]
    # Checklist completo (solo señales activas): útil para la ficha del valor.
    checklist = [
        {"label": label, "passed": bool(ok)}
        for k, (ok, label) in checks.items()
        if w.get(k, 0) > 0
    ]

    change_pct = None
    if len(close) > 1 and _sf(close.iloc[-2]):
        change_pct = round((price / _sf(close.iloc[-2]) - 1) * 100, 2)

    return {
        "ticker": sym,
        "name": name,
        "price": round(price, 2),
        "change_pct": change_pct,
        "score": score,
        "passed": passed,
        "checklist": checklist,
        "rsi": round(rsi) if rsi else None,
        "adx": round(adx_v) if adx_v else None,
        "vol_ratio": round(vol_ratio, 1) if vol_ratio else None,
        "rel_strength": round(rel, 1) if rel is not None else None,
        "atr_pct": round(atr_pct, 1) if atr_pct else None,
    }


def _normalize(config: dict | None) -> dict:
    cfg = _merge(DEFAULT_CONFIG, config)
    cfg["weights"] = {**DEFAULT_CONFIG["weights"], **(config or {}).get("weights", {})}
    cfg["params"] = {**DEFAULT_CONFIG["params"], **(config or {}).get("params", {})}
    cfg["sources"] = {**DEFAULT_CONFIG["sources"], **(config or {}).get("sources", {})}
    return cfg


def score_one(ticker: str, config: dict | None = None, lang: str = "es") -> dict:
    """Puntúa un único valor con la misma lógica del radar (sin filtros de
    exclusión), devolviendo el checklist completo para su ficha."""
    cfg = _normalize(config)
    bench_ret = _benchmark_return(cfg["params"]["benchmark"], int(cfg["params"]["rel_lookback"]))
    try:
        name = yahoo.get_quote(ticker).get("name", ticker)
    except Exception:
        name = ticker
    res = _score(ticker, name, cfg, bench_ret, apply_filters=False, lang=lang)
    if not res:
        return {"ok": False, "ticker": ticker.upper()}
    res["ok"] = True
    res["benchmark"] = cfg["params"]["benchmark"]
    res["benchmark_return"] = round(bench_ret, 2)
    return res


def scan(config: dict | None = None, lang: str = "es") -> dict:
    cfg = _normalize(config)

    universe = _universe(cfg)
    bench_ret = _benchmark_return(cfg["params"]["benchmark"], int(cfg["params"]["rel_lookback"]))

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [
            ex.submit(_score, sym, name, cfg, bench_ret, True, lang)
            for sym, name in universe.items()
        ]
        for f in futures:
            try:
                r = f.result()
            except Exception:
                r = None
            if r and r["score"] >= cfg["min_score"]:
                results.append(r)

    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "candidates": results[: cfg["max_results"]],
        "scanned": len(universe),
        "matched": len(results),
        "benchmark": cfg["params"]["benchmark"],
        "benchmark_return": round(bench_ret, 2),
    }
