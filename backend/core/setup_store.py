"""Persistencia de las alertas de 'setup' (rotura → retest → rebote).

Tabla propia en la misma SQLite. Guarda la configuración (qué nivel vigilar, en
qué temporalidad, dirección) y el ESTADO de la máquina, que debe sobrevivir a
reinicios del backend para no perder en qué fase iba cada alerta.
"""

from __future__ import annotations

import sqlite3
import time

from core.cache import DB_PATH
from core.setup import ARMED


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS setup_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            level_type TEXT NOT NULL DEFAULT 'ema',
            length INTEGER NOT NULL DEFAULT 50,
            tf TEXT NOT NULL DEFAULT '1d',
            direction TEXT NOT NULL DEFAULT 'long',
            state TEXT NOT NULL DEFAULT 'armed',
            last_bar TEXT DEFAULT '',
            note TEXT DEFAULT '',
            lang TEXT NOT NULL DEFAULT 'es',
            active INTEGER NOT NULL DEFAULT 1,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_setup_ticker ON setup_alerts(ticker)")
    conn.commit()
    conn.close()


def _row_to_dict(r) -> dict:
    return {
        "id": r[0],
        "ticker": r[1],
        "level_type": r[2],
        "length": r[3],
        "tf": r[4],
        "direction": r[5],
        "state": r[6],
        "last_bar": r[7],
        "note": r[8],
        "lang": r[9],
        "active": bool(r[10]),
        "created_at": r[11],
        "updated_at": r[12],
    }


_COLS = (
    "id, ticker, level_type, length, tf, direction, state, last_bar, note, "
    "lang, active, created_at, updated_at"
)


def create(
    ticker: str,
    tf: str = "1d",
    length: int = 50,
    direction: str = "long",
    note: str = "",
    lang: str = "es",
    level_type: str = "ema",
) -> dict:
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO setup_alerts "
        "(ticker, level_type, length, tf, direction, state, note, lang, active, "
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (ticker.upper(), level_type, int(length), tf, direction, ARMED, note, lang, now, now),
    )
    conn.commit()
    row = conn.execute(
        f"SELECT {_COLS} FROM setup_alerts WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_all(ticker: str | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    if ticker:
        rows = conn.execute(
            f"SELECT {_COLS} FROM setup_alerts WHERE ticker = ? ORDER BY id DESC",
            (ticker.upper(),),
        ).fetchall()
    else:
        rows = conn.execute(f"SELECT {_COLS} FROM setup_alerts ORDER BY id DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def list_active() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        f"SELECT {_COLS} FROM setup_alerts WHERE active = 1 ORDER BY id"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def update_state(setup_id: int, state: str, last_bar: str | None = None):
    conn = sqlite3.connect(DB_PATH)
    if last_bar is None:
        conn.execute(
            "UPDATE setup_alerts SET state = ?, updated_at = ? WHERE id = ?",
            (state, time.time(), setup_id),
        )
    else:
        conn.execute(
            "UPDATE setup_alerts SET state = ?, last_bar = ?, updated_at = ? WHERE id = ?",
            (state, last_bar, time.time(), setup_id),
        )
    conn.commit()
    conn.close()


def set_active(setup_id: int, active: bool) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "UPDATE setup_alerts SET active = ?, updated_at = ? WHERE id = ?",
        (1 if active else 0, time.time(), setup_id),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def delete(setup_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM setup_alerts WHERE id = ?", (setup_id,))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok
