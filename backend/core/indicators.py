"""Indicadores técnicos calculados a mano con pandas/numpy.

Se evita pandas-ta a propósito (sin mantenimiento y roto en Python 3.14).
La entrada es la lista de velas OHLCV que devuelve core.yahoo.get_ohlcv().
"""

from __future__ import annotations

import pandas as pd


def _to_df(ohlcv: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(ohlcv)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def frame(ohlcv: list[dict]) -> pd.DataFrame:
    """DataFrame público (indexado por fecha) para el radar de rompimientos."""
    return _to_df(ohlcv)


def _true_range(df: pd.DataFrame) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def adx(df: pd.DataFrame, period: int = 14):
    """ADX + Direccional Movement (+DI / -DI). Fuerza y dirección de tendencia."""
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = ((up > down) & (up > 0)) * up
    minus_dm = ((down > up) & (down > 0)) * down
    atr_ = _true_range(df).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    adx_ = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx_, plus_di, minus_di


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume: acumula volumen según el signo del cambio de precio."""
    direction = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * df["volume"]).cumsum()


def resample(ohlcv: list[dict], rule: str) -> list[dict]:
    """Reagrupa velas a una temporalidad mayor (ej. '4h' desde datos de 60m)."""
    df = _to_df(ohlcv)
    if df.empty:
        return []
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    r = df.resample(rule).agg(agg).dropna()
    out = []
    for idx, row in r.iterrows():
        out.append({
            "date": idx.strftime("%Y-%m-%d %H:%M"),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"]),
        })
    return out


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Media exponencial de Wilder
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def bollinger(series: pd.Series, window: int = 20, num_std: float = 2.0):
    mid = sma(series, window)
    std = series.rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def _round(value, ndigits: int = 2):
    if value is None or pd.isna(value):
        return None
    return round(float(value), ndigits)


def _pivots(df: pd.DataFrame, lookback: int = 60):
    """Soportes/resistencias sencillos: mínimos/máximos recientes."""
    recent = df.tail(lookback)
    if recent.empty:
        return {"support": None, "resistance": None}
    return {
        "support": _round(recent["low"].min()),
        "resistance": _round(recent["high"].max()),
    }


def _time(idx, intraday: bool):
    """Tiempo para lightweight-charts: timestamp UNIX en intradía, fecha en diario."""
    return int(idx.timestamp()) if intraday else idx.strftime("%Y-%m-%d")


def _points(series: pd.Series, ndigits: int = 4, intraday: bool = False) -> list[dict]:
    """Serie → [{time, value}] para lightweight-charts, sin NaN."""
    out = []
    for idx, val in series.items():
        if val == val:  # descarta NaN
            out.append({"time": _time(idx, intraday), "value": round(float(val), ndigits)})
    return out


def _is_intraday(df: pd.DataFrame) -> bool:
    """True si algún dato lleva hora (no todo a medianoche)."""
    return bool((df.index.hour != 0).any() or (df.index.minute != 0).any())


def _norm_index(idx):
    """Índice temporal a UTC sin tz, para poder alinear temporalidades distintas."""
    if getattr(idx, "tz", None) is not None:
        return idx.tz_convert("UTC").tz_localize(None)
    return idx


def ema_line(chart_df: pd.DataFrame, tf_df: pd.DataFrame, length: int) -> list[dict]:
    """Serie EMA para el gráfico.

    Si `tf_df` es el mismo `chart_df`, EMA normal sobre el cierre del gráfico.
    Si es una temporalidad mayor (MTF), se calcula ahí y se rellena hacia
    adelante sobre las velas del gráfico (escalón, como hace TradingView).
    """
    intraday = _is_intraday(chart_df)
    if tf_df is chart_df:
        return _points(ema(chart_df["close"], length), intraday=intraday)

    e = ema(tf_df["close"], length).copy()
    e.index = _norm_index(e.index)
    e = e[~e.index.duplicated(keep="last")].sort_index()
    cn = _norm_index(chart_df.index)
    filled = e.reindex(e.index.union(cn)).sort_index().ffill().reindex(cn)
    out = []
    for orig, val in zip(chart_df.index, filled.values, strict=False):
        if val == val:
            out.append({"time": _time(orig, intraday), "value": round(float(val), 4)})
    return out


def chart_bundle(ohlcv: list[dict]) -> dict:
    """Velas + indicadores del propio timeframe (sin EMAs; esas van aparte).

    Las EMAs se piden por separado (endpoint /ema) porque su longitud y su
    temporalidad son configurables por el usuario.
    """
    empty = {"candles": [], "volume": [], "rsi": [], "bb_upper": [],
             "bb_lower": [], "support": None, "resistance": None}
    df = _to_df(ohlcv)
    if df.empty or len(df) < 2:
        return empty

    intraday = _is_intraday(df)
    close = df["close"]
    candles = [
        {
            "time": _time(idx, intraday),
            "open": round(float(r["open"]), 4),
            "high": round(float(r["high"]), 4),
            "low": round(float(r["low"]), 4),
            "close": round(float(r["close"]), 4),
        }
        for idx, r in df.iterrows()
    ]
    volume = [
        {"time": _time(idx, intraday),
         "value": int(r["volume"]) if r["volume"] == r["volume"] else 0,
         "up": bool(r["close"] >= r["open"])}
        for idx, r in df.iterrows()
    ]
    bb_up, _bb_mid, bb_low = bollinger(close)
    return {
        "candles": candles,
        "volume": volume,
        "rsi": _points(rsi(close, 14), 2, intraday=intraday),
        "bb_upper": _points(bb_up, intraday=intraday),
        "bb_lower": _points(bb_low, intraday=intraday),
        **_pivots(df),
    }


def compute(ohlcv: list[dict]) -> dict:
    """Calcula el paquete de indicadores. Devuelve los últimos valores + contexto."""
    df = _to_df(ohlcv)
    if df.empty or len(df) < 30:
        return {"ok": False, "reason": "datos_insuficientes"}

    close = df["close"]
    price = float(close.iloc[-1])

    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    ema200 = ema(close, 200)
    rsi14 = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)
    atr14 = atr(df, 14)
    bb_up, bb_mid, bb_low = bollinger(close)

    # Cambios de precio
    def pct_change(bars: int):
        if len(close) <= bars:
            return None
        return _round((price / close.iloc[-1 - bars] - 1) * 100)

    latest = {
        "ok": True,
        "price": _round(price),
        "ema20": _round(ema20.iloc[-1]),
        "ema50": _round(ema50.iloc[-1]),
        "ema200": _round(ema200.iloc[-1]) if len(close) >= 200 else None,
        "rsi14": _round(rsi14.iloc[-1]),
        "macd": _round(macd_line.iloc[-1], 3),
        "macd_signal": _round(signal_line.iloc[-1], 3),
        "macd_hist": _round(hist.iloc[-1], 3),
        "atr14": _round(atr14.iloc[-1]),
        "atr_pct": _round(atr14.iloc[-1] / price * 100) if price else None,
        "bb_upper": _round(bb_up.iloc[-1]),
        "bb_lower": _round(bb_low.iloc[-1]),
        "change_1d": pct_change(1),
        "change_5d": pct_change(5),
        "change_20d": pct_change(20),
        "high_52w": _round(df["high"].max()),
        "low_52w": _round(df["low"].min()),
    }
    latest.update(_pivots(df))
    return latest
