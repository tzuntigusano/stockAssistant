"""Transacciones del usuario (compras y ventas) y cálculo de P&L.

Modelo de coste medio: cada compra actualiza el precio medio; cada venta
realiza P&L contra ese precio medio y reduce la posición. Todo persiste en la
misma SQLite del cache, en la tabla `lots`.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import date as _date

from core.cache import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            side TEXT NOT NULL DEFAULT 'buy',
            date TEXT NOT NULL,
            price REAL NOT NULL,
            shares REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lots_ticker ON lots(ticker)")
    # Migración suave: añade la columna `side` si la tabla es antigua.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(lots)").fetchall()]
    if "side" not in cols:
        conn.execute("ALTER TABLE lots ADD COLUMN side TEXT NOT NULL DEFAULT 'buy'")
    conn.commit()
    conn.close()


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "ticker": row[1],
        "side": row[2],
        "date": row[3],
        "price": row[4],
        "shares": row[5],
        "note": row[6],
    }


def add_transaction(
    ticker: str,
    price: float,
    shares: float,
    side: str = "buy",
    date: str | None = None,
    note: str = "",
) -> dict:
    ticker = ticker.upper()
    side = "sell" if side == "sell" else "buy"
    date = date or _date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO lots (ticker, side, date, price, shares, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ticker, side, date, float(price), float(shares), note, time.time()),
    )
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": tx_id, "ticker": ticker, "side": side, "date": date,
            "price": price, "shares": shares, "note": note}


def get_transactions(ticker: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, ticker, side, date, price, shares, note FROM lots "
        "WHERE ticker = ? ORDER BY date, id",
        (ticker.upper(),),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def update_transaction(
    lot_id: int,
    price: float | None = None,
    shares: float | None = None,
    side: str | None = None,
    date: str | None = None,
    note: str | None = None,
) -> dict | None:
    """Edita una transacción existente. Solo cambia los campos que se pasan.

    El coste medio y el P&L se recalculan solos: summarize() recorre siempre las
    transacciones actuales, así que no hay nada más que actualizar.
    """
    sets, params = [], []
    if price is not None:
        sets.append("price = ?")
        params.append(float(price))
    if shares is not None:
        sets.append("shares = ?")
        params.append(float(shares))
    if side is not None:
        sets.append("side = ?")
        params.append("sell" if side == "sell" else "buy")
    if date is not None:
        sets.append("date = ?")
        params.append(date)
    if note is not None:
        sets.append("note = ?")
        params.append(note)
    if not sets:
        return get_transaction(lot_id)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(f"UPDATE lots SET {', '.join(sets)} WHERE id = ?", (*params, lot_id))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return get_transaction(lot_id) if changed else None


def get_transaction(lot_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, ticker, side, date, price, shares, note FROM lots WHERE id = ?",
        (lot_id,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def delete_lot(lot_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("DELETE FROM lots WHERE id = ?", (lot_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def all_tickers() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT ticker FROM lots ORDER BY ticker").fetchall()
    conn.close()
    return [r[0] for r in rows]


def summarize(ticker: str, current_price: float | None) -> dict:
    """Recorre las transacciones en orden y calcula posición + P&L.

    Devuelve posición abierta (acciones netas, coste medio, P&L no realizado)
    y el P&L realizado acumulado de las ventas.
    """
    txs = get_transactions(ticker)
    if not txs:
        return {"has_position": False, "lots": [], "realized_pnl": 0.0}

    shares = 0.0
    avg = 0.0
    realized = 0.0
    enriched: list[dict] = []

    for t in txs:
        item = dict(t)
        if t["side"] == "buy":
            cost = avg * shares + t["price"] * t["shares"]
            shares += t["shares"]
            avg = cost / shares if shares else 0.0
            if current_price:
                item["pnl"] = round((current_price - t["price"]) * t["shares"], 2)
                item["pnl_pct"] = round((current_price / t["price"] - 1) * 100, 2)
        else:  # venta
            qty = min(t["shares"], shares) if shares > 0 else 0.0
            r = (t["price"] - avg) * qty
            realized += r
            item["realized"] = round(r, 2)
            item["realized_pct"] = round((t["price"] / avg - 1) * 100, 2) if avg else None
            shares = max(0.0, shares - t["shares"])
        enriched.append(item)

    result: dict = {
        "has_position": shares > 1e-9,
        "lots": enriched,
        "realized_pnl": round(realized, 2),
    }
    if shares > 1e-9:
        total_cost = avg * shares
        result["total_shares"] = round(shares, 4)
        result["avg_price"] = round(avg, 4)
        result["total_cost"] = round(total_cost, 2)
        if current_price:
            market_value = shares * current_price
            result["current_price"] = current_price
            result["market_value"] = round(market_value, 2)
            result["unrealized_pnl"] = round(market_value - total_cost, 2)
            result["unrealized_pnl_pct"] = (
                round((market_value / total_cost - 1) * 100, 2) if total_cost else 0.0
            )
    return result
