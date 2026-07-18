"""Transacciones, cartera, seguimiento y lista del radar."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import lots, radarwatch, watchlist, yahoo

router = APIRouter(prefix="/api", tags=["portfolio"])


class LotIn(BaseModel):
    ticker: str
    price: float
    shares: float
    side: str = "buy"  # 'buy' o 'sell'
    date: str | None = None
    note: str = ""


class LotEdit(BaseModel):
    """Edición parcial: solo se cambian los campos que llegan."""

    price: float | None = None
    shares: float | None = None
    side: str | None = None
    date: str | None = None
    note: str | None = None


def _ticker_cards(tickers: list[str]) -> list[dict]:
    return [
        {
            "ticker": t,
            "name": (q := yahoo.get_quote(t)).get("name"),
            "price": q.get("price"),
            "currency": q.get("currency"),
            "change_pct": q.get("change_pct"),
        }
        for t in tickers
    ]


# --- Transacciones -----------------------------------------------------------
@router.get("/lots/{ticker}")
def get_lots(ticker: str):
    q = yahoo.get_quote(ticker)
    return lots.summarize(ticker, q.get("price"))


@router.post("/lots")
def add_lot(lot: LotIn):
    if lot.shares <= 0 or lot.price <= 0:
        raise HTTPException(400, "El precio y las acciones deben ser positivos")
    return lots.add_transaction(
        lot.ticker, lot.price, lot.shares, side=lot.side, date=lot.date, note=lot.note
    )


@router.patch("/lots/{lot_id}")
def edit_lot(lot_id: int, body: LotEdit):
    if body.shares is not None and body.shares <= 0:
        raise HTTPException(400, "Las acciones deben ser positivas")
    if body.price is not None and body.price <= 0:
        raise HTTPException(400, "El precio debe ser positivo")
    updated = lots.update_transaction(
        lot_id, price=body.price, shares=body.shares, side=body.side,
        date=body.date, note=body.note,
    )
    if not updated:
        raise HTTPException(404, "Transacción no encontrada")
    return updated


@router.delete("/lots/{lot_id}")
def remove_lot(lot_id: int):
    if not lots.delete_lot(lot_id):
        raise HTTPException(404, "Transacción no encontrada")
    return {"deleted": True, "id": lot_id}


# --- Cartera global ----------------------------------------------------------
@router.get("/portfolio")
def portfolio():
    items = []
    tv = tc = tu = tr = 0.0
    for t in lots.all_tickers():
        q = yahoo.get_quote(t)
        pos = lots.summarize(t, q.get("price"))
        tr += pos.get("realized_pnl", 0) or 0
        entry = {
            "ticker": t,
            "name": q.get("name"),
            "price": q.get("price"),
            "currency": q.get("currency"),
            "change_pct": q.get("change_pct"),
            "has_position": pos["has_position"],
            "realized_pnl": pos.get("realized_pnl", 0),
        }
        if pos["has_position"]:
            entry.update({
                "shares": pos["total_shares"],
                "avg_price": pos["avg_price"],
                "market_value": pos.get("market_value"),
                "unrealized_pnl": pos.get("unrealized_pnl"),
                "unrealized_pnl_pct": pos.get("unrealized_pnl_pct"),
            })
            tv += pos.get("market_value") or 0
            tc += pos.get("total_cost") or 0
            tu += pos.get("unrealized_pnl") or 0
        items.append(entry)
    # Alfabetico por ticker (las posiciones abiertas primero).
    items.sort(key=lambda x: (not x["has_position"], x["ticker"]))
    return {
        "items": items,
        "totals": {
            "market_value": round(tv, 2),
            "cost": round(tc, 2),
            "unrealized_pnl": round(tu, 2),
            "unrealized_pnl_pct": round((tv / tc - 1) * 100, 2) if tc else 0.0,
            "realized_pnl": round(tr, 2),
        },
    }


# --- Lista de seguimiento ----------------------------------------------------
@router.get("/watchlist")
def get_watchlist():
    return _ticker_cards(watchlist.tickers())


@router.get("/watchlist/status/{ticker}")
def watchlist_status(ticker: str):
    return {"in_watchlist": watchlist.contains(ticker)}


@router.post("/watchlist/{ticker}")
def watchlist_add(ticker: str):
    watchlist.add(ticker)
    return {"ok": True}


@router.delete("/watchlist/{ticker}")
def watchlist_remove(ticker: str):
    watchlist.remove(ticker)
    return {"ok": True}


# --- Lista del radar de rupturas (separada del seguimiento) ------------------
@router.get("/radarwatch")
def get_radarwatch():
    return _ticker_cards(radarwatch.tickers())


@router.get("/radarwatch/status/{ticker}")
def radarwatch_status(ticker: str):
    return {"in_radar": radarwatch.contains(ticker)}


@router.post("/radarwatch/{ticker}")
def radarwatch_add(ticker: str):
    radarwatch.add(ticker)
    return {"ok": True}


@router.delete("/radarwatch/{ticker}")
def radarwatch_remove(ticker: str):
    radarwatch.remove(ticker)
    return {"ok": True}
