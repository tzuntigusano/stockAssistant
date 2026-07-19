"""Endpoints de las carteras ficticias (paper trading).

OJO con el orden: las rutas fijas (/paper/run, /paper/log…) van ANTES que
/paper/{mode}, o FastAPI se las tragaría como si `mode` fuese "run".
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import alerts, paper, paper_engine, paper_monitor, paper_store
from core.i18n import L
from core.marketdata import realtime_prices

router = APIRouter(prefix="/api", tags=["paper"])

_MODES = ("normal", "fast")


def _check(mode: str):
    if mode not in _MODES:
        raise HTTPException(400, f"Cartera no válida: {mode}")


class ToggleIn(BaseModel):
    enabled: bool


class RunIn(BaseModel):
    lang: str = "es"


@router.get("/paper")
def paper_compare(lang: str = "es"):
    """Las dos carteras enfrentadas + estado del mercado."""
    return paper_engine.compare(lang)


@router.get("/paper/status")
def paper_status():
    return paper_monitor.status()


@router.post("/paper/toggle")
def paper_toggle(body: ToggleIn):
    paper_monitor.set_enabled(body.enabled)
    return {"enabled": paper_monitor.is_enabled()}


@router.post("/paper/run")
def paper_run(body: RunIn):
    """Botón de re-análisis: fuerza un ciclo AHORA. Con el mercado abierto
    ejecuta; con el mercado cerrado hace un simulacro (analiza y anota lo que
    haría, sin abrir nada), porque fuera de horario no hay precio real al que
    ejecutar."""
    paper_monitor.set_lang(body.lang)
    result = paper_monitor.run_once(body.lang, source="manual")
    if result.get("skipped"):
        raise HTTPException(409, L(body.lang, "Ya hay un análisis en curso",
                                   "An analysis is already running"))
    return result


@router.get("/paper/log")
def paper_log(mode: str | None = None, limit: int = 60):
    if mode:
        _check(mode)
    return {"entries": paper_store.list_log(mode, min(limit, 200))}


@router.get("/paper/recent")
def paper_recent():
    return {"events": paper_monitor.recent()}


@router.post("/paper/positions/{pos_id}/close")
def paper_close(pos_id: int, lang: str = "es"):
    """Cierre manual de una posición ficticia al precio actual."""
    pos = paper_store.get_position(pos_id)
    if not pos or pos["status"] != paper.OPEN:
        raise HTTPException(404, L(lang, "Posición no encontrada o ya cerrada",
                                   "Position not found or already closed"))
    price = realtime_prices([pos["ticker"]]).get(pos["ticker"]) or pos["entry_price"]
    pnl = paper.realized_pnl({**pos, "exit_price": price})
    book = paper_store.get_portfolio(pos["mode"])
    paper_store.set_cash(pos["mode"], book["cash"] + pos["shares"] * pos["entry_price"] + pnl)
    text = L(lang, "Cerrada a mano", "Closed manually")
    paper_store.close_position(pos_id, price, paper.MANUAL, text, pnl)
    paper_store.log(pos["mode"], "exit",
                    f"{pos['ticker']} · {text} @ {price:.2f} · P&L {pnl:+.2f}", pos["ticker"])
    return {"closed": True, "price": price, "pnl": pnl}


@router.post("/paper/positions/{pos_id}/alerts")
def paper_position_alerts(pos_id: int, lang: str = "es"):
    """Crea alertas REALES (de las de la campana) con el objetivo y el stop de
    la operación ficticia, para que el usuario se entere aunque no mire la app."""
    pos = paper_store.get_position(pos_id)
    if not pos:
        raise HTTPException(404, L(lang, "Posición no encontrada", "Position not found"))
    long = pos["side"] == "long"
    tag = L(lang, "Cartera ficticia", "Paper portfolio")
    created = [
        alerts.add(
            pos["ticker"],
            "price_above" if long else "price_below",
            pos["target"],
            f"{tag}: " + L(lang, "objetivo", "target"),
        ),
        alerts.add(
            pos["ticker"],
            "price_below" if long else "price_above",
            pos["stop"],
            f"{tag}: stop",
        ),
    ]
    return {"created": created}


@router.post("/paper/reset/{mode}")
def paper_reset(mode: str):
    _check(mode)
    paper_store.reset(mode)
    return {"reset": True, "mode": mode}


@router.get("/paper/{mode}")
def paper_one(mode: str, lang: str = "es"):
    _check(mode)
    return paper_engine.summary(mode, lang)
