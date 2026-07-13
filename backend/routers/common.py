"""Helpers compartidos entre routers."""

from __future__ import annotations

from fastapi import HTTPException

from core import indicators, lots, signals, strategy, yahoo


def analyze(ticker: str, lang: str = "es"):
    q = yahoo.get_quote(ticker)
    o = yahoo.get_ohlcv(ticker, period="1y", interval="1d")
    ind = indicators.compute(o)
    verdict = signals.evaluate(ind, lang)
    return q, ind, verdict


def strategy_data(ticker: str, lang: str = "es"):
    """Datos deterministas del valor para alimentar a la IA."""
    q, ind, verdict = analyze(ticker, lang)
    if q.get("price") is None:
        raise HTTPException(404, f"No se encontraron datos para '{ticker}'")
    position = lots.summarize(ticker, q.get("price"))
    levels = strategy.build_levels(ind, position)
    return q, ind, verdict, position, levels


def chat_context(ticker: str, lang: str = "es") -> tuple[dict, str]:
    """Contexto completo (técnico + posición + fundamental + noticias) para el chat."""
    q, ind, verdict, position, levels = strategy_data(ticker, lang)
    parts = [
        strategy.build_technical_context(ticker, q, ind, verdict, levels),
        strategy.build_position_context(position),
        strategy.build_fundamental_context(yahoo.get_fundamentals(ticker), yahoo.get_news(ticker)),
    ]
    return position, "\n\n".join(parts)
