"""Radar de oportunidades técnicas (screener de rompimientos)."""

from __future__ import annotations

from fastapi import APIRouter

from core import radar

router = APIRouter(prefix="/api/radar", tags=["screener"])


@router.get("/sources")
def radar_sources(lang: str = "es"):
    return {"predefined": radar.sources(lang), "defaults": radar.DEFAULT_CONFIG}


@router.post("")
def radar_scan(config: dict | None = None, lang: str = "es"):
    return radar.scan(config, lang)


@router.post("/score/{ticker}")
def radar_score_one(ticker: str, config: dict | None = None, lang: str = "es"):
    return radar.score_one(ticker, config, lang)
