"""Alertas, notificaciones (Windows + Telegram) y radar de rupturas en directo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import alerts, breakout_monitor, monitor, notifier, scanner, telegram

router = APIRouter(prefix="/api", tags=["alerts"])


class AlertIn(BaseModel):
    ticker: str
    type: str
    threshold: float | None = None
    note: str = ""


class NotifyToggle(BaseModel):
    enabled: bool


class ActiveIn(BaseModel):
    active: bool
    ticker: str | None = None  # solo en el masivo: limita a un valor


# --- Alertas de precio / indicadores -----------------------------------------
@router.get("/alerts")
def list_alerts(ticker: str | None = None):
    return alerts.list_all(ticker)


@router.post("/alerts")
def create_alert(a: AlertIn):
    if a.type in alerts.NEEDS_THRESHOLD and a.threshold is None:
        raise HTTPException(400, "Este tipo de alerta necesita un valor umbral")
    return alerts.add(a.ticker, a.type, a.threshold, a.note)


@router.get("/alerts/check")
def check_alerts():
    return {"triggered": scanner.check()}


@router.post("/alerts/dismiss")
def dismiss_alerts():
    """Quita de la campana las alertas que están saltando (no borra las reglas)."""
    scanner.dismiss()
    return {"ok": True}


@router.post("/alerts/toggle-all")
def toggle_all_alerts(body: ActiveIn):
    """Activa/pausa todas las alertas de golpe (o las de un valor)."""
    return {"changed": alerts.set_all_active(body.active, body.ticker)}


@router.post("/alerts/{alert_id}/toggle")
def toggle_alert(alert_id: int, body: ActiveIn):
    if not alerts.set_active(alert_id, body.active):
        raise HTTPException(404, "Alerta no encontrada")
    return {"active": body.active}


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    if not alerts.delete(alert_id):
        raise HTTPException(404, "Alerta no encontrada")
    return {"deleted": True}


# --- Notificaciones (Windows) -------------------------------------------------
@router.get("/notifications/status")
def notifications_status():
    return {"supported": notifier.SUPPORTED, "enabled": monitor.is_enabled()}


@router.post("/notifications/toggle")
def notifications_toggle(body: NotifyToggle):
    monitor.set_enabled(body.enabled)
    return {"enabled": monitor.is_enabled()}


@router.post("/notifications/test")
def notifications_test():
    ok = notifier.notify(
        "Analizador de Acciones",
        "Notificación de prueba: las alertas funcionan.",
    )
    if not ok:
        raise HTTPException(503, "Ningún canal de notificación disponible")
    return {"sent": True}


# --- Telegram (alertas al móvil) ----------------------------------------------
@router.get("/telegram/status")
def telegram_status():
    return {"configured": telegram.is_configured(), "has_token": telegram.has_token()}


@router.get("/telegram/detect")
def telegram_detect():
    """Escribe algo a tu bot y llama aquí para averiguar tu chat_id."""
    if not telegram.has_token():
        raise HTTPException(400, "Falta TELEGRAM_BOT_TOKEN en backend/.env")
    chats = telegram.detect_chats()
    if not chats:
        raise HTTPException(
            404,
            "Sin mensajes aún: envía cualquier texto a tu bot desde Telegram y reintenta",
        )
    return {"chats": chats}


@router.post("/telegram/test")
def telegram_test():
    if not telegram.is_configured():
        raise HTTPException(400, "Faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID en backend/.env")
    if not telegram.send("📈 Analizador de Acciones", "Prueba: las alertas al móvil funcionan."):
        raise HTTPException(502, "Telegram rechazó el envío (¿token o chat_id incorrectos?)")
    return {"sent": True}


# --- Radar de rupturas en directo ----------------------------------------------
@router.get("/breakouts/status")
def breakouts_status():
    return breakout_monitor.status()


@router.post("/breakouts/toggle")
def breakouts_toggle(body: NotifyToggle):
    breakout_monitor.set_enabled(body.enabled)
    return {"enabled": breakout_monitor.is_enabled()}


@router.get("/breakouts/recent")
def breakouts_recent():
    return {"triggered": breakout_monitor.recent()}


@router.post("/breakouts/clear")
def breakouts_clear():
    breakout_monitor.clear()
    return {"ok": True}


@router.post("/breakouts/scan")
def breakouts_scan(force: bool = False):
    """Fuerza un escaneo inmediato (útil fuera de horario)."""
    return {"triggered": breakout_monitor.scan_once(force=force)}
