"""Orquestador de las carteras ficticias: junta datos reales y ejecuta las
decisiones que toma `core.paper` (que es quien decide, de forma determinista).

Un ciclo hace SIEMPRE lo mismo, en este orden:
  1. Revisa las posiciones abiertas (¿stop? ¿objetivo? ¿tesis rota? ¿plazo?).
  2. Busca candidatos nuevos (radar + watchlist), ya puntuados por confluencia.
  3. Abre las que pasan el filtro y anota en el diario por qué sí o por qué no.

El radar se escanea UNA vez por ciclo y se comparte entre las dos carteras,
para no duplicar peticiones a Yahoo.
"""

from __future__ import annotations

import time

from core import indicators, paper, paper_store, radar, watchlist, yahoo
from core.breakout_monitor import market_open
from core.i18n import L
from core.marketdata import realtime_prices
from core.paper import OPEN

# Cuántos candidatos del radar se analizan a fondo por ciclo (coste de red).
MAX_CANDIDATES = 12

# Velas que usa cada cartera: la rápida vive en intradía, la normal en diario.
_BARS = {
    "normal": {"period": "1y", "interval": "1d"},
    "fast": {"period": "10d", "interval": "15m"},
}


def _metrics(ticker: str, mode: str) -> dict | None:
    """Indicadores del valor en la temporalidad propia de la cartera."""
    cfg = _BARS.get(mode, _BARS["normal"])
    try:
        bars = yahoo.get_ohlcv(ticker, period=cfg["period"], interval=cfg["interval"])
    except Exception:
        return None
    ind = indicators.compute(bars)
    if not ind.get("ok"):
        return None
    # `compute` llama al RSI "rsi14"; el motor de decisión espera "rsi".
    ind["rsi"] = ind.get("rsi14")
    return ind


def _days_held(pos: dict) -> float:
    return max(0.0, (time.time() - pos["entry_at"]) / 86400)


# --------------------------------------------------------------------------
#  1) Posiciones abiertas
# --------------------------------------------------------------------------
def _manage_open(mode: str, lang: str, execute: bool = True) -> list[dict]:
    positions = paper_store.list_positions(mode, OPEN)
    if not positions:
        return []
    prices = realtime_prices([p["ticker"] for p in positions])
    events = []
    for pos in positions:
        price = prices.get(pos["ticker"])
        met = _metrics(pos["ticker"], mode)
        if price is None and met:
            price = met.get("price")
        decision = paper.check_exit(pos, price, met, _days_held(pos), lang)

        if not execute:
            # Mercado cerrado: el precio es el del último cierre, así que se
            # informa de lo que pasaría pero no se toca nada.
            if decision.get("close"):
                text = L(lang, f"{pos['ticker']} · se cerraría: {decision['text']}",
                         f"{pos['ticker']} · would close: {decision['text']}")
                paper_store.log(mode, "dryrun", text, pos["ticker"])
                events.append({"kind": "dryrun", "ticker": pos["ticker"], "text": text})
            continue

        if decision.get("close"):
            closed = {**pos, "exit_price": decision["price"]}
            pnl = paper.realized_pnl(closed)
            # Devuelve a caja la garantía/importe más el resultado de la operación.
            book = paper_store.get_portfolio(mode)
            freed = pos["shares"] * pos["entry_price"] + pnl
            paper_store.set_cash(mode, book["cash"] + freed)
            paper_store.close_position(
                pos["id"], decision["price"], decision["reason"], decision["text"], pnl
            )
            sign = "+" if pnl >= 0 else ""
            text = (
                f"{pos['ticker']} · " + L(lang, "CIERRE", "CLOSE") + f" @ {decision['price']:.2f} · "
                f"{decision['text']} · P&L {sign}{pnl:.2f}"
            )
            paper_store.log(mode, "exit", text, pos["ticker"])
            events.append({"kind": "exit", "ticker": pos["ticker"], "text": text})

        else:
            if decision.get("runner") and not pos["runner"]:
                paper_store.set_runner(pos["id"])
            if decision.get("new_stop") is not None:
                paper_store.move_stop(pos["id"], decision["new_stop"])
                text = f"{pos['ticker']} · {decision['text']}"
                paper_store.log(mode, "stop", text, pos["ticker"])
                events.append({"kind": "stop", "ticker": pos["ticker"], "text": text})
    return events


# --------------------------------------------------------------------------
#  2) Candidatos nuevos
# --------------------------------------------------------------------------
def _candidates(lang: str) -> list[dict]:
    """Universo ya filtrado y puntuado: radar (screener de Yahoo + watchlist)."""
    try:
        result = radar.scan(None, lang)
        cands = result.get("candidates", [])
    except Exception:
        cands = []
    seen = {c["ticker"] for c in cands}
    # La watchlist entra siempre, aunque el screener no la haya sacado hoy.
    for t in watchlist.tickers():
        if t.upper() in seen:
            continue
        try:
            one = radar.score_one(t, None, lang)
        except Exception:
            continue
        if one.get("ok"):
            cands.append(one)
    cands.sort(key=lambda c: c.get("score", 0), reverse=True)
    return cands[:MAX_CANDIDATES]


def _seek_entries(mode: str, candidates: list[dict], lang: str, execute: bool = True) -> list[dict]:
    held = paper_store.open_tickers(mode)
    max_new = paper.mode_config(mode)["max_new_per_cycle"]
    events, skipped = [], []
    for cand in candidates:
        if len(events) >= max_new:
            break
        ticker = cand["ticker"]
        if ticker in held:
            continue
        book = paper_store.get_portfolio(mode)
        equity = _equity(mode, book)
        open_count = len(paper_store.list_positions(mode, OPEN))
        met = _metrics(ticker, mode)
        if not met:
            continue
        merged = {**cand, **met, "score": cand.get("score", 0), "passed": cand.get("passed", [])}
        plan = paper.plan_entry(merged, mode, equity, book["cash"], open_count, lang)

        if not plan.get("open"):
            skipped.append(f"{ticker} ({plan.get('reason', '')})")
            continue

        side_txt = L(lang, "LARGO", "LONG") if plan["side"] == "long" else L(lang, "CORTO", "SHORT")
        if not execute:
            # Con el mercado cerrado solo se puede fingir el precio de entrada
            # (sería el último cierre), así que se anota la idea sin ejecutarla.
            text = L(
                lang,
                f"{ticker} · se abriría {side_txt} · stop {plan['stop']:.2f} · "
                f"objetivo {plan['target']:.2f} · {plan['thesis']}",
                f"{ticker} · would open {side_txt} · stop {plan['stop']:.2f} · "
                f"target {plan['target']:.2f} · {plan['thesis']}",
            )
            paper_store.log(mode, "dryrun", text, ticker)
            events.append({"kind": "dryrun", "ticker": ticker, "text": text})
            held.add(ticker)
            continue

        name = cand.get("name", ticker)
        pos = paper_store.open_position(mode, ticker, name, plan)
        paper_store.set_cash(mode, book["cash"] - plan["shares"] * plan["entry_price"])
        held.add(ticker)
        text = (
            f"{ticker} · {side_txt} {plan['shares']:.2f} @ {plan['entry_price']:.2f} · "
            + L(lang, "stop", "stop") + f" {plan['stop']:.2f} · "
            + L(lang, "objetivo", "target") + f" {plan['target']:.2f} · {plan['thesis']}"
        )
        paper_store.log(mode, "entry", text, ticker)
        events.append({"kind": "entry", "ticker": ticker, "text": text, "position": pos})

    # Deja constancia también de los ciclos en los que se decidió no operar.
    if not events:
        detail = "; ".join(skipped[:4]) if skipped else L(
            lang, "sin candidatos del radar", "no radar candidates")
        paper_store.log(mode, "skip", L(
            lang, f"Sin operaciones nuevas: {detail}", f"No new trades: {detail}"))
    return events


# --------------------------------------------------------------------------
#  Ciclo completo
# --------------------------------------------------------------------------
def run_cycle(
    lang: str = "es",
    modes: tuple[str, ...] = ("normal", "fast"),
    execute: bool | None = None,
) -> dict:
    """Un ciclo de las dos carteras.

    Solo se EJECUTAN órdenes con el mercado abierto: fuera de horario el único
    precio disponible es el del último cierre, y llenar la cartera a ese precio
    sería una ejecución falsa. Con el mercado cerrado el ciclo hace un simulacro
    (`execute=False`): analiza igual y anota lo que haría, sin tocar la cartera.
    """
    if execute is None:
        execute = market_open()
    candidates = _candidates(lang)
    out: dict[str, list[dict]] = {}
    for mode in modes:
        events = _manage_open(mode, lang, execute)
        events += _seek_entries(mode, candidates, lang, execute)
        out[mode] = events
    return {
        "at": time.time(),
        "candidates": len(candidates),
        "executed": execute,
        "events": out,
    }


# --------------------------------------------------------------------------
#  Estado para la API
# --------------------------------------------------------------------------
def _equity(mode: str, book: dict | None = None, prices: dict | None = None) -> float:
    book = book or paper_store.get_portfolio(mode)
    total = book["cash"]
    for pos in paper_store.list_positions(mode, OPEN):
        price = (prices or {}).get(pos["ticker"])
        total += paper.position_value(pos, price)
    return round(total, 2)


def summary(mode: str, lang: str = "es") -> dict:
    """Foto completa de una cartera: caja, equity, posiciones y estadísticas."""
    book = paper_store.get_portfolio(mode)
    cfg = paper.mode_config(mode)
    open_pos = paper_store.list_positions(mode, OPEN)
    closed = paper_store.list_positions(mode, paper.CLOSED)

    prices = realtime_prices([p["ticker"] for p in open_pos]) if open_pos else {}
    enriched = []
    invested = 0.0
    for pos in open_pos:
        price = prices.get(pos["ticker"])
        pnl, pnl_pct = paper.unrealized(pos, price)
        invested += paper.position_value(pos, price)
        enriched.append({
            **pos,
            "current_price": price,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": pnl_pct,
            "horizon_label": paper.horizon_label(pos["horizon"], lang),
            "days_held": round(_days_held(pos), 1),
        })

    for pos in closed:
        pos["exit_reason_label"] = paper.exit_reason_label(pos["exit_reason"], lang)
        if pos["entry_price"]:
            diff = (
                (pos["entry_price"] - (pos["exit_price"] or 0))
                if pos["side"] == "short"
                else ((pos["exit_price"] or 0) - pos["entry_price"])
            )
            pos["pnl_pct"] = round(diff / pos["entry_price"] * 100, 2)

    equity = round(book["cash"] + invested, 2)
    initial = book["initial_cash"]
    wins = [p for p in closed if (p["pnl"] or 0) > 0]
    realized = round(sum(p["pnl"] or 0 for p in closed), 2)

    return {
        "mode": mode,
        "cash": round(book["cash"], 2),
        "initial_cash": initial,
        "equity": equity,
        "total_pnl": round(equity - initial, 2),
        "total_pnl_pct": round((equity / initial - 1) * 100, 2) if initial else 0.0,
        "realized_pnl": realized,
        "open_positions": enriched,
        "closed_positions": closed[:40],
        "trades": len(closed),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "config": {
            "risk_pct": cfg["risk_pct"],
            "max_positions": cfg["max_positions"],
            "min_score": cfg["min_score"],
            "horizon": cfg["horizon"],
            "horizon_label": paper.horizon_label(cfg["horizon"], lang),
            "max_hold_days": cfg["max_hold_days"],
        },
    }


def compare(lang: str = "es") -> dict:
    """Las dos carteras enfrentadas, para ver qué enfoque rinde mejor."""
    data = {m: summary(m, lang) for m in ("normal", "fast")}
    return {
        "portfolios": data,
        "market_open": market_open(),
        "leader": max(data, key=lambda m: data[m]["total_pnl_pct"]),
    }
