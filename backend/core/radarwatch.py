"""Lista de MONITOREO EN DIRECTO (radar de rupturas).

Es una lista APARTE de la watchlist general: solo los valores que el usuario
marca expresamente para vigilarse cada ~45 s en busca de rupturas.
"""

from __future__ import annotations

import sqlite3
import time

from core.cache import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS radar_watch (
            ticker TEXT PRIMARY KEY,
            added_at REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add(ticker: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO radar_watch (ticker, added_at) VALUES (?, ?)",
        (ticker.upper(), time.time()),
    )
    conn.commit()
    conn.close()


def remove(ticker: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM radar_watch WHERE ticker = ?", (ticker.upper(),))
    conn.commit()
    conn.close()


def tickers() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticker FROM radar_watch ORDER BY ticker"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def contains(ticker: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM radar_watch WHERE ticker = ?", (ticker.upper(),)
    ).fetchone()
    conn.close()
    return row is not None
