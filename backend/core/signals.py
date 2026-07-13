"""Motor de reglas: convierte indicadores en un veredicto alcista/bajista.

Produce una puntuación 0-100 (0 = muy bajista, 100 = muy alcista) y una lista
de señales legibles que explican el porqué. Es determinista y transparente:
la IA (core.llm) solo redacta encima de esto, no inventa el veredicto.
"""

from __future__ import annotations

from core.i18n import L


def _verdict_label(score: int, lang: str) -> str:
    if score >= 70:
        return L(lang, "ALCISTA", "BULLISH")
    if score >= 58:
        return L(lang, "LIGERAMENTE ALCISTA", "SLIGHTLY BULLISH")
    if score > 42:
        return L(lang, "NEUTRAL", "NEUTRAL")
    if score > 30:
        return L(lang, "LIGERAMENTE BAJISTA", "SLIGHTLY BEARISH")
    return L(lang, "BAJISTA", "BEARISH")


def evaluate(ind: dict, lang: str = "es") -> dict:
    """Recibe el dict de indicators.compute() y devuelve el veredicto."""
    if not ind.get("ok"):
        return {
            "score": 50,
            "label": L(lang, "NEUTRAL", "NEUTRAL"),
            "signals": [],
            "reason": ind.get("reason", "datos_insuficientes"),
        }

    price = ind["price"]
    signals: list[dict] = []
    score = 50  # arrancamos neutrales y sumamos/restamos

    def add(delta: int, es: str, en: str, bias: str):
        nonlocal score
        score += delta
        signals.append({"text": L(lang, es, en), "bias": bias, "weight": abs(delta)})

    # --- Tendencia por medias móviles ---
    ema20, ema50, ema200 = ind.get("ema20"), ind.get("ema50"), ind.get("ema200")
    if ema20 and ema50:
        if price > ema20 > ema50:
            add(12, "Precio sobre EMA20 y EMA50 (tendencia alcista de corto plazo)",
                "Price above EMA20 and EMA50 (short-term uptrend)", "alcista")
        elif price < ema20 < ema50:
            add(-12, "Precio bajo EMA20 y EMA50 (tendencia bajista de corto plazo)",
                "Price below EMA20 and EMA50 (short-term downtrend)", "bajista")
        elif price > ema50:
            add(5, "Precio por encima de la EMA50", "Price above EMA50", "alcista")
        else:
            add(-5, "Precio por debajo de la EMA50", "Price below EMA50", "bajista")

    if ema200:
        if price > ema200:
            add(8, "Precio sobre la EMA200 (tendencia de fondo alcista)",
                "Price above EMA200 (long-term uptrend)", "alcista")
        else:
            add(-8, "Precio bajo la EMA200 (tendencia de fondo bajista)",
                "Price below EMA200 (long-term downtrend)", "bajista")

    # --- RSI ---
    rsi = ind.get("rsi14")
    if rsi is not None:
        if rsi >= 70:
            add(-6, f"RSI en sobrecompra ({rsi:.0f}) — riesgo de corrección",
                f"RSI overbought ({rsi:.0f}) — pullback risk", "bajista")
        elif rsi <= 30:
            add(6, f"RSI en sobreventa ({rsi:.0f}) — posible rebote",
                f"RSI oversold ({rsi:.0f}) — possible bounce", "alcista")
        elif rsi >= 55:
            add(5, f"RSI con impulso comprador ({rsi:.0f})",
                f"RSI with buying momentum ({rsi:.0f})", "alcista")
        elif rsi <= 45:
            add(-5, f"RSI con impulso vendedor ({rsi:.0f})",
                f"RSI with selling momentum ({rsi:.0f})", "bajista")

    # --- MACD ---
    hist = ind.get("macd_hist")
    if hist is not None:
        if hist > 0:
            add(8, "MACD por encima de su señal (impulso alcista)",
                "MACD above its signal (bullish momentum)", "alcista")
        else:
            add(-8, "MACD por debajo de su señal (impulso bajista)",
                "MACD below its signal (bearish momentum)", "bajista")

    # --- Momentum de precio ---
    ch20 = ind.get("change_20d")
    if ch20 is not None:
        if ch20 > 8:
            add(6, f"Fuerte subida en 20 sesiones ({ch20:+.1f}%)",
                f"Strong rise over 20 sessions ({ch20:+.1f}%)", "alcista")
        elif ch20 < -8:
            add(-6, f"Fuerte caída en 20 sesiones ({ch20:+.1f}%)",
                f"Strong drop over 20 sessions ({ch20:+.1f}%)", "bajista")

    # --- Proximidad a extremos de 52 semanas ---
    hi, lo = ind.get("high_52w"), ind.get("low_52w")
    if hi and price >= hi * 0.98:
        add(4, "Cotiza cerca de máximos de 52 semanas",
            "Trading near 52-week highs", "alcista")
    if lo and price <= lo * 1.03:
        add(-4, "Cotiza cerca de mínimos de 52 semanas",
            "Trading near 52-week lows", "bajista")

    score = max(0, min(100, score))
    # Ordena señales por peso (las más relevantes primero)
    signals.sort(key=lambda s: s["weight"], reverse=True)

    return {
        "score": score,
        "label": _verdict_label(score, lang),
        "signals": signals,
    }
