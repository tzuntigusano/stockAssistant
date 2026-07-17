"""API del analizador de acciones — FastAPI, todo local y gratuito.

Arranque:  uvicorn main:app --reload   (desde backend/, con el venv activo)
Rutas: ver routers/ (market, portfolio, ai, screener, alerts) y CLAUDE.md.
"""

from __future__ import annotations

import os
import sys
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import (
    alerts,
    breakout_monitor,
    cache,
    feed,
    lots,
    monitor,
    radarwatch,
    setup_monitor,
    setup_store,
    watchlist,
)
from routers import ai, market, portfolio, screener, setups
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
app.include_router(setups.router)


@app.on_event("startup")
def _startup():
    cache.init_db()
    lots.init_db()
    watchlist.init_db()
    alerts.init_db()
    radarwatch.init_db()
    feed.init_db()
    setup_store.init_db()
    monitor.start()  # vigilante de alertas → notificaciones Windows/Telegram
    breakout_monitor.start()  # radar de rupturas en directo (lista radarwatch)
    setup_monitor.start()  # vigilante de setups (rotura → retest → rebote)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/system/restart")
def restart_backend():
    """Reinicia el proceso del backend (re-exec de uvicorn). Útil cuando la
    sesión interna de yfinance se degrada tras muchas horas y empiezan los 500.
    Responde antes de reiniciar; el front espera a que /health vuelva."""

    def _do():
        time.sleep(0.7)  # deja que la respuesta HTTP se envíe antes de reiniciar
        os.execv(sys.executable, [sys.executable, "-m", "uvicorn", *sys.argv[1:]])

    threading.Thread(target=_do, daemon=True).start()
    return {"restarting": True}
