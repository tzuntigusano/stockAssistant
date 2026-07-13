"""Evalúa todas las alertas activas contra los datos actuales.

Lo usan tanto el endpoint /api/alerts/check como el vigilante en segundo plano
(core.monitor), para que ambos apliquen exactamente la misma lógica.
"""

from __future__ import annotations

from core import alerts, indicators, yahoo

# Alertas que el usuario ha "borrado" de la campana. Se rearman solas: cuando
# una deja de cumplirse sale de aquí, así vuelve a aparecer si cruza de nuevo.
_dismissed: set[int] = set()


def scan() -> list[dict]:
    triggered: list[dict] = []
    for t in alerts.distinct_tickers():
        active = [a for a in alerts.list_all(t) if a["active"]]
        if not active:
            continue
        try:
            q = yahoo.get_quote(t)
            ind = indicators.compute(yahoo.get_ohlcv(t))
        except Exception:
            continue
        price, rsi = q.get("price"), ind.get("rsi14")
        sup, res = ind.get("support"), ind.get("resistance")
        for a in active:
            fired = alerts.evaluate(a, price, rsi, sup, res)
            if fired:
                triggered.append(fired)
    return triggered


def check() -> list[dict]:
    """Como scan() pero oculta las que el usuario ha borrado de la campana.
    Lo usa el endpoint del frontend; el vigilante de notificaciones usa scan()."""
    triggered = scan()
    ids = {a["id"] for a in triggered}
    _dismissed.intersection_update(ids)  # rearme: descarta solo lo que aún salta
    return [a for a in triggered if a["id"] not in _dismissed]


def dismiss():
    """Marca como descartadas todas las alertas activas (las que ahora saltan
    se ocultan hasta que dejen de cumplirse; el resto se ignoran en check())."""
    for a in alerts.list_all():
        if a["active"]:
            _dismissed.add(a["id"])
