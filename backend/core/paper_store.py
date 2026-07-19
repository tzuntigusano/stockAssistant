"""Persistencia de las carteras ficticias (paper trading).

Tres tablas en la misma SQLite: la caja de cada cartera, sus posiciones
(abiertas y cerradas, con stop/objetivo/tesis) y el diario de sesión, que
incluye también los ciclos en los que se decidió NO operar y por qué.
"""

from __future__ import annotations

import sqlite3
import time

from core.cache import DB_PATH
from core.paper import CLOSED, OPEN, mode_config

MODES = ("normal", "fast")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_portfolios (
            mode TEXT PRIMARY KEY,
            cash REAL NOT NULL,
            initial_cash REAL NOT NULL,
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            ticker TEXT NOT NULL,
            name TEXT DEFAULT '',
            side TEXT NOT NULL DEFAULT 'long',
            shares REAL NOT NULL,
            entry_price REAL NOT NULL,
            entry_at REAL NOT NULL,
            stop REAL NOT NULL,
            initial_stop REAL NOT NULL,
            target REAL NOT NULL,
            rr REAL DEFAULT 0,
            horizon TEXT DEFAULT 'swing',
            thesis TEXT DEFAULT '',
            score INTEGER DEFAULT 0,
            stop_moved INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',
            exit_price REAL,
            exit_at REAL,
            exit_reason TEXT DEFAULT '',
            exit_text TEXT DEFAULT '',
            pnl REAL DEFAULT 0,
            runner INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_pos ON paper_positions(mode, status)")
    # Migración suave: `runner` marca las que superaron el objetivo y siguen vivas.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(paper_positions)").fetchall()]
    if "runner" not in cols:
        conn.execute("ALTER TABLE paper_positions ADD COLUMN runner INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            at REAL NOT NULL,
            kind TEXT NOT NULL,
            ticker TEXT DEFAULT '',
            text TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_paper_log ON paper_log(mode, at)")
    # Alta de las dos carteras la primera vez, con su capital inicial.
    for mode in MODES:
        cash = mode_config(mode)["initial_cash"]
        conn.execute(
            "INSERT OR IGNORE INTO paper_portfolios (mode, cash, initial_cash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (mode, cash, cash, time.time()),
        )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
#  Caja
# --------------------------------------------------------------------------
def get_portfolio(mode: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(
        "SELECT mode, cash, initial_cash, created_at FROM paper_portfolios WHERE mode = ?",
        (mode,),
    ).fetchone()
    conn.close()
    if not r:
        cash = mode_config(mode)["initial_cash"]
        return {"mode": mode, "cash": cash, "initial_cash": cash, "created_at": time.time()}
    return {"mode": r[0], "cash": r[1], "initial_cash": r[2], "created_at": r[3]}


def set_cash(mode: str, cash: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE paper_portfolios SET cash = ? WHERE mode = ?", (float(cash), mode))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
#  Posiciones
# --------------------------------------------------------------------------
_COLS = (
    "id, mode, ticker, name, side, shares, entry_price, entry_at, stop, initial_stop, "
    "target, rr, horizon, thesis, score, stop_moved, status, exit_price, exit_at, "
    "exit_reason, exit_text, pnl, runner"
)


def _row(r) -> dict:
    return {
        "id": r[0], "mode": r[1], "ticker": r[2], "name": r[3], "side": r[4],
        "shares": r[5], "entry_price": r[6], "entry_at": r[7], "stop": r[8],
        "initial_stop": r[9], "target": r[10], "rr": r[11], "horizon": r[12],
        "thesis": r[13], "score": r[14], "stop_moved": bool(r[15]), "status": r[16],
        "exit_price": r[17], "exit_at": r[18], "exit_reason": r[19],
        "exit_text": r[20], "pnl": r[21], "runner": bool(r[22]),
    }


def open_position(mode: str, ticker: str, name: str, order: dict) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO paper_positions (mode, ticker, name, side, shares, entry_price, "
        "entry_at, stop, initial_stop, target, rr, horizon, thesis, score, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            mode, ticker.upper(), name, order["side"], order["shares"],
            order["entry_price"], time.time(), order["stop"], order["stop"],
            order["target"], order.get("rr", 0), order.get("horizon", "swing"),
            order.get("thesis", ""), order.get("score", 0), OPEN,
        ),
    )
    conn.commit()
    row = conn.execute(f"SELECT {_COLS} FROM paper_positions WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row(row)


def list_positions(mode: str | None = None, status: str | None = None) -> list[dict]:
    q = f"SELECT {_COLS} FROM paper_positions"
    where, params = [], []
    if mode:
        where.append("mode = ?")
        params.append(mode)
    if status:
        where.append("status = ?")
        params.append(status)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY entry_at DESC"
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


def get_position(pos_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute(f"SELECT {_COLS} FROM paper_positions WHERE id = ?", (pos_id,)).fetchone()
    conn.close()
    return _row(r) if r else None


def move_stop(pos_id: int, stop: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE paper_positions SET stop = ?, stop_moved = 1 WHERE id = ?", (float(stop), pos_id)
    )
    conn.commit()
    conn.close()


def set_runner(pos_id: int):
    """Marca la posición como 'dejada correr' (superó el objetivo y sigue viva)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE paper_positions SET runner = 1 WHERE id = ?", (pos_id,))
    conn.commit()
    conn.close()


def close_position(pos_id: int, price: float, reason: str, text: str, pnl: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE paper_positions SET status = ?, exit_price = ?, exit_at = ?, "
        "exit_reason = ?, exit_text = ?, pnl = ? WHERE id = ?",
        (CLOSED, float(price), time.time(), reason, text, float(pnl), pos_id),
    )
    conn.commit()
    conn.close()


def open_tickers(mode: str) -> set[str]:
    return {p["ticker"] for p in list_positions(mode, OPEN)}


# --------------------------------------------------------------------------
#  Diario
# --------------------------------------------------------------------------
def log(mode: str, kind: str, text: str, ticker: str = ""):
    """kind: 'entry' | 'exit' | 'stop' | 'skip' | 'cycle' | 'system'."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO paper_log (mode, at, kind, ticker, text) VALUES (?, ?, ?, ?, ?)",
        (mode, time.time(), kind, ticker.upper(), text),
    )
    conn.commit()
    conn.close()


def list_log(mode: str | None = None, limit: int = 60) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    if mode:
        rows = conn.execute(
            "SELECT id, mode, at, kind, ticker, text FROM paper_log WHERE mode = ? "
            "ORDER BY at DESC, id DESC LIMIT ?",
            (mode, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, mode, at, kind, ticker, text FROM paper_log "
            "ORDER BY at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [
        {"id": r[0], "mode": r[1], "at": r[2], "kind": r[3], "ticker": r[4], "text": r[5]}
        for r in rows
    ]


def reset(mode: str):
    """Vuelve a empezar: borra posiciones y diario y repone el capital inicial.

    El capital se relee de la configuración (no de la fila), para que cambiar
    `initial_cash` en MODES surta efecto al reiniciar la cartera.
    """
    cash = mode_config(mode)["initial_cash"]
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM paper_positions WHERE mode = ?", (mode,))
    conn.execute("DELETE FROM paper_log WHERE mode = ?", (mode,))
    conn.execute(
        "UPDATE paper_portfolios SET cash = ?, initial_cash = ?, created_at = ? WHERE mode = ?",
        (cash, cash, time.time(), mode),
    )
    conn.commit()
    conn.close()
