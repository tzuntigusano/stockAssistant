"""API del analizador de acciones — FastAPI, todo local y gratuito.

Arranque:  uvicorn main:app --reload   (desde backend/, con el venv activo)
Rutas: ver routers/ (market, portfolio, ai, screener, alerts) y CLAUDE.md.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import alerts, breakout_monitor, cache, feed, lots, monitor, radarwatch, watchlist
from routers import ai, market, portfolio, screener
from routers import alerts as alerts_router
from routers import feed as feed_router
from settings import CORS_ORIGINS

app = FastAPI(title="Analizador de Acciones", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router)
app.include_router(portfolio.router)
app.include_router(ai.router)
app.include_router(screener.router)
app.include_router(alerts_router.router)
app.include_router(feed_router.router)


@app.on_event("startup")
def _startup():
    cache.init_db()
    lots.init_db()
    watchlist.init_db()
    alerts.init_db()
    radarwatch.init_db()
    feed.init_db()
    monitor.start()  # vigilante de alertas → notificaciones Windows/Telegram
    breakout_monitor.start()  # radar de rupturas en directo (lista radarwatch)


@app.get("/api/health")
def health():
    return {"ok": True}
