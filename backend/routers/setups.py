"""Endpoints de las alertas de 'setup' (rotura → retest → rebote)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import setup_monitor, setup_store

router = APIRouter(prefix="/api", tags=["setups"])

_TFS = {"15m", "1h", "60m", "4h", "1d", "1wk"}


class Anchor(BaseModel):
    t: float  # timestamp unix (segundos)
    p: float  # precio


class SetupIn(BaseModel):
    ticker: str
    tf: str = "1d"
    length: int = 50
    direction: str = "long"
    note: str = ""
    lang: str = "es"
    level_type: str = "ema"  # 'ema' | 'trendline'
    line: list[Anchor] | None = None  # anclas de la trendline (si level_type=trendline)


class ToggleIn(BaseModel):
    active: bool


@router.get("/setups")
def list_setups(ticker: str | None = None):
    return setup_store.list_all(ticker)


@router.post("/setups")
def create_setup(body: SetupIn):
    if body.tf not in _TFS:
        raise HTTPException(400, f"Temporalidad no válida: {body.tf}")
    if body.direction not in ("long", "short"):
        raise HTTPException(400, "La dirección debe ser 'long' o 'short'")
    if body.level_type not in ("ema", "trendline"):
        raise HTTPException(400, "level_type debe ser 'ema' o 'trendline'")
    line = None
    if body.level_type == "trendline":
        if not body.line or len(body.line) < 2:
            raise HTTPException(400, "Una alerta de trendline necesita la línea (2 anclas)")
        line = [{"t": a.t, "p": a.p} for a in body.line[:2]]
    length = max(1, min(int(body.length), 400))
    return setup_store.create(
        body.ticker, tf=body.tf, length=length, direction=body.direction,
        note=body.note, lang=body.lang, level_type=body.level_type, line=line,
    )


@router.post("/setups/{setup_id}/toggle")
def toggle_setup(setup_id: int, body: ToggleIn):
    if not setup_store.set_active(setup_id, body.active):
        raise HTTPException(404, "Alerta no encontrada")
    return {"active": body.active}


@router.delete("/setups/{setup_id}")
def delete_setup(setup_id: int):
    return {"deleted": setup_store.delete(setup_id)}


@router.get("/setups/recent")
def recent_setups():
    return {"events": setup_monitor.recent()}


@router.get("/setups/status")
def setups_status():
    return setup_monitor.status()


@router.post("/setups/scan")
def scan_setups():
    """Fuerza un ciclo de comprobación ahora mismo (útil para probar)."""
    return {"fired": setup_monitor.scan_once()}
