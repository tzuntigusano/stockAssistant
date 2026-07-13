"""P&L de cartera (core.lots.summarize).

Se testa la MATEMÁTICA (coste medio, realizado/no realizado) sin tocar SQLite:
se sustituye get_transactions por una lista fija con monkeypatch.
"""

from core import lots


def _fake_txs(txs):
    """Devuelve las transacciones dadas ignorando el ticker (para monkeypatch)."""
    return lambda ticker: [dict(t) for t in txs]


def test_sin_transacciones_no_hay_posicion(monkeypatch):
    monkeypatch.setattr(lots, "get_transactions", _fake_txs([]))
    out = lots.summarize("AAA", current_price=None)
    assert out["has_position"] is False
    assert out["realized_pnl"] == 0.0


def test_coste_medio_de_dos_compras(monkeypatch):
    txs = [
        {"side": "buy", "date": "2024-01-01", "price": 10.0, "shares": 10},
        {"side": "buy", "date": "2024-01-02", "price": 20.0, "shares": 10},
    ]
    monkeypatch.setattr(lots, "get_transactions", _fake_txs(txs))
    out = lots.summarize("AAA", current_price=30.0)
    assert out["has_position"] is True
    assert out["total_shares"] == 20
    assert out["avg_price"] == 15.0            # (10*10 + 20*10) / 20
    assert out["total_cost"] == 300.0
    assert out["unrealized_pnl"] == 300.0      # 20 * 30 - 300


def test_venta_realiza_pnl_contra_coste_medio(monkeypatch):
    txs = [
        {"side": "buy", "date": "2024-01-01", "price": 10.0, "shares": 10},
        {"side": "sell", "date": "2024-01-03", "price": 15.0, "shares": 5},
    ]
    monkeypatch.setattr(lots, "get_transactions", _fake_txs(txs))
    out = lots.summarize("AAA", current_price=15.0)
    assert out["realized_pnl"] == 25.0         # (15 - 10) * 5
    assert out["total_shares"] == 5            # quedan 5 abiertas
    assert out["avg_price"] == 10.0            # una venta no cambia el coste medio


def test_vender_todo_cierra_la_posicion(monkeypatch):
    txs = [
        {"side": "buy", "date": "2024-01-01", "price": 10.0, "shares": 10},
        {"side": "sell", "date": "2024-01-03", "price": 12.0, "shares": 10},
    ]
    monkeypatch.setattr(lots, "get_transactions", _fake_txs(txs))
    out = lots.summarize("AAA", current_price=12.0)
    assert out["has_position"] is False
    assert out["realized_pnl"] == 20.0         # (12 - 10) * 10
