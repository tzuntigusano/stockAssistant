"""Alertas de precio / indicadores.

Las alertas se guardan en SQLite y se evalúan bajo demanda contra los datos
actuales (el frontend consulta periódicamente mientras la app está abierta).
Tipos soportados:
  - price_above / price_below : precio cruza un umbral
  - rsi_above / rsi_below     : RSI cruza un umbral
  - break_resistance          : precio supera la resistencia detectada
  - break_support             : precio pierde el soporte detectado
"""

from __future__ import annotations

import sqlite3
import time

from core.cache import DB_PATH

_LABELS = {
    "price_above": "Precio por encima de",
    "price_below": "Precio por debajo de",
    "rsi_above": "RSI por encima de",
    "rsi_below": "RSI por debajo de",
    "break_resistance": "Rotura de resistencia",
    "break_support": "Pérdida de soporte",
}

NEEDS_THRESHOLD = {"price_above", "price_below", "rsi_above", "rsi_below"}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            type TEXT NOT NULL,
            threshold REAL,
            note TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def _row(r) -> dict:
    return {
        "id": r[0],
        "ticker": r[1],
        "type": r[2],
        "threshold": r[3],
        "note": r[4],
        "active": bool(r[5]),
        "label": _LABELS.get(r[2], r[2]),
    }


def add(ticker: str, type: str, threshold: float | None = None, note: str = "") -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO alerts (ticker, type, threshold, note, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (ticker.upper(), type, threshold, note, time.time()),
    )
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return get(aid)


def get(alert_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(
        "SELECT id, ticker, type, threshold, note, active FROM alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()
    conn.close()
    return _row(r) if r else None


def list_all(ticker: str | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    if ticker:
        rows = conn.execute(
            "SELECT id, ticker, type, threshold, note, active FROM alerts "
            "WHERE ticker = ? ORDER BY created_at DESC",
            (ticker.upper(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, ticker, type, threshold, note, active FROM alerts "
            "ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [_row(r) for r in rows]


def delete(alert_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def set_active(alert_id: int, active: bool) -> bool:
    """Activa/pausa una alerta sin borrarla (el vigilante solo mira active=1)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "UPDATE alerts SET active = ? WHERE id = ?", (1 if active else 0, alert_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def set_all_active(active: bool, ticker: str | None = None) -> int:
    """Activa/pausa TODAS de golpe (o las de un valor). Devuelve cuántas cambió."""
    conn = sqlite3.connect(DB_PATH)
    if ticker:
        cur = conn.execute(
            "UPDATE alerts SET active = ? WHERE ticker = ?",
            (1 if active else 0, ticker.upper()),
        )
    else:
        cur = conn.execute("UPDATE alerts SET active = ?", (1 if active else 0,))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def distinct_tickers() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM alerts WHERE active = 1"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def evaluate(alert: dict, price: float | None, rsi: float | None,
             support: float | None, resistance: float | None) -> dict | None:
    """Devuelve un dict de disparo si la condición se cumple, o None."""
    t = alert["type"]
    thr = alert["threshold"]
    msg = None

    if t == "price_above" and price is not None and thr is not None and price >= thr:
        msg = f"{price:.2f} ≥ {thr:.2f}"
    elif t == "price_below" and price is not None and thr is not None and price <= thr:
        msg = f"{price:.2f} ≤ {thr:.2f}"
    elif t == "rsi_above" and rsi is not None and thr is not None and rsi >= thr:
        msg = f"RSI {rsi:.0f} ≥ {thr:.0f}"
    elif t == "rsi_below" and rsi is not None and thr is not None and rsi <= thr:
        msg = f"RSI {rsi:.0f} ≤ {thr:.0f}"
    elif t == "break_resistance" and price is not None and resistance and price >= resistance:
        msg = f"{price:.2f} supera resistencia {resistance:.2f}"
    elif t == "break_support" and price is not None and support and price <= support:
        msg = f"{price:.2f} pierde soporte {support:.2f}"

    if msg is None:
        return None
    return {
        "id": alert["id"],
        "ticker": alert["ticker"],
        "label": alert["label"],
        "message": msg,
        "note": alert["note"],
    }
