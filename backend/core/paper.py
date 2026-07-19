"""Motor de decisión de las carteras ficticias (paper trading).

TODO lo que decide QUÉ operar, CUÁNTO y CUÁNDO salir vive aquí y es
DETERMINISTA: mismas entradas → misma decisión. No interviene ningún LLM
(regla nº1 del proyecto). La IA, si acaso, solo redacta después.

Dos modos con personalidad distinta:
  - "normal": swing / medio plazo, stops ATR anchos, deja correr con trailing.
  - "fast"  : muy corto plazo, objetivos pequeños en % y stops ceñidos.

Funciones puras (sin BD ni red) para poder testearlas: plan_entry() decide la
apertura y check_exit() decide el cierre.
"""

from __future__ import annotations

from core.i18n import L

# --- Estados de una posición ---
OPEN = "open"
CLOSED = "closed"

# --- Motivos de cierre ---
STOP = "stop"
TARGET = "target"
TRAIL = "trail"
INVALIDATED = "invalidated"
TIME = "time"
MANUAL = "manual"

MODES = {
    "normal": {
        "initial_cash": 1_000.0,
        # Riesgo por operación calibrado para que 8 posiciones quepan en la caja:
        # con stops de ~5% (2×ATR), 0.6% de riesgo ≈ 12% del equity por idea.
        "risk_pct": 0.6,          # % del equity que se arriesga por operación
        "max_positions": 8,
        "max_new_per_cycle": 3,   # no vuelca la cartera entera en las señales de un día
        "max_position_pct": 20.0,  # tope de exposición sobre el equity
        "min_score": 55,
        "min_atr_pct": 1.0,
        "stop_atr_mult": 2.0,
        "target_r": 2.5,          # objetivo en múltiplos de riesgo (R)
        "breakeven_r": 1.0,       # a +1R el stop sube a break-even
        "trail_r": 1.5,           # a partir de +1.5R el stop persigue al precio
        "trail_atr_mult": 1.5,
        "max_hold_days": 45,
        "allow_short": True,
        "horizon": "swing",
    },
    "fast": {
        "initial_cash": 1_000.0,
        # Stops muy ceñidos (1.5%) → hace falta un riesgo pequeño para que la
        # posición no se coma la cartera entera: 0.35% ≈ 23% del equity.
        "risk_pct": 0.35,
        "max_positions": 4,
        "max_new_per_cycle": 2,
        "max_position_pct": 30.0,
        "min_score": 50,
        "min_atr_pct": 2.0,       # sin volatilidad no hay recorrido en horas
        "stop_pct": 1.5,          # stop fijo en % (manda sobre el ATR)
        "target_pct": 3.0,        # objetivo fijo en %
        "stop_atr_mult": 1.0,
        "target_r": 2.0,
        "breakeven_r": 1.0,
        "trail_r": 1.5,
        "trail_atr_mult": 0.8,
        "max_hold_days": 3,
        "allow_short": True,
        "let_winners_run": True,  # en el objetivo, si sigue con fuerza, no cierra
        "horizon": "intraday",
    },
}

HORIZONS = {
    "intraday": ("Intradía / horas", "Intraday / hours"),
    "swing": ("Swing (días-semanas)", "Swing (days-weeks)"),
    "position": ("Posición (semanas-meses)", "Position (weeks-months)"),
}


def mode_config(mode: str) -> dict:
    return MODES.get(mode, MODES["normal"])


def horizon_label(horizon: str, lang: str = "es") -> str:
    es, en = HORIZONS.get(horizon, HORIZONS["swing"])
    return L(lang, es, en)


def _f(value) -> float | None:
    """Float seguro: None si falta o es NaN."""
    try:
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
#  Valoración de una posición abierta
# --------------------------------------------------------------------------
def position_value(pos: dict, price: float | None) -> float:
    """Valor de mercado de la posición (para el equity).

    En corto se inmovilizó `shares * entry` como garantía, así que su valor es
    esa garantía más (o menos) el P&L latente.
    """
    entry, shares = pos["entry_price"], pos["shares"]
    if price is None:
        price = entry
    if pos["side"] == "short":
        return shares * entry + (entry - price) * shares
    return shares * price


def unrealized(pos: dict, price: float | None) -> tuple[float, float]:
    """(P&L latente en €, P&L latente en %) de una posición abierta."""
    entry, shares = pos["entry_price"], pos["shares"]
    if price is None or not entry:
        return 0.0, 0.0
    diff = (entry - price) if pos["side"] == "short" else (price - entry)
    pnl = diff * shares
    return round(pnl, 2), round(diff / entry * 100, 2)


def realized_pnl(pos: dict) -> float:
    """P&L realizado de una posición ya cerrada."""
    exit_price = pos.get("exit_price")
    if exit_price is None:
        return 0.0
    diff = (
        (pos["entry_price"] - exit_price)
        if pos["side"] == "short"
        else (exit_price - pos["entry_price"])
    )
    return round(diff * pos["shares"], 2)


# --------------------------------------------------------------------------
#  Apertura
# --------------------------------------------------------------------------
def _direction(m: dict, cfg: dict) -> str | None:
    """Largo, corto o nada, según la alineación de tendencia. Sin medias tintas:
    si el valor no está claramente a favor en un sentido, no se opera."""
    price = _f(m.get("price"))
    ema20, ema50 = _f(m.get("ema20")), _f(m.get("ema50"))
    rsi = _f(m.get("rsi"))
    if price is None or ema20 is None or ema50 is None:
        return None
    if price > ema20 > ema50 and (rsi is None or rsi >= 50):
        return "long"
    if cfg.get("allow_short") and price < ema20 < ema50 and (rsi is None or rsi <= 50):
        return "short"
    return None


def still_trending(metrics: dict | None, side: str) -> bool:
    """¿El movimiento sigue teniendo fuerza a favor de la posición?

    Se exige confluencia de las tres patas (precio sobre/bajo la EMA20, MACD
    acompañando y RSI en zona de fuerza). Si falta cualquiera, el impulso ya no
    es limpio y se toma el beneficio en vez de estirar la operación.
    """
    if not metrics:
        return False
    price = _f(metrics.get("price"))
    ema20 = _f(metrics.get("ema20"))
    hist = _f(metrics.get("macd_hist"))
    rsi = _f(metrics.get("rsi"))
    if None in (price, ema20, hist, rsi):
        return False
    if side == "short":
        return price < ema20 and hist < 0 and rsi <= 45
    return price > ema20 and hist > 0 and rsi >= 55


def _levels(entry: float, side: str, atr: float | None, cfg: dict) -> tuple[float, float]:
    """(stop, objetivo). El modo rápido usa porcentajes fijos; el normal, ATR."""
    if cfg.get("stop_pct") and cfg.get("target_pct"):
        stop_dist = entry * cfg["stop_pct"] / 100
        if atr:  # nunca por debajo del ruido: al menos 0.6 ATR
            stop_dist = max(stop_dist, atr * 0.6)
        target_dist = entry * cfg["target_pct"] / 100
    else:
        stop_dist = (atr or entry * 0.02) * cfg["stop_atr_mult"]
        target_dist = stop_dist * cfg["target_r"]
    if side == "short":
        return round(entry + stop_dist, 2), round(entry - target_dist, 2)
    return round(entry - stop_dist, 2), round(entry + target_dist, 2)


def plan_entry(
    metrics: dict,
    mode: str,
    equity: float,
    cash: float,
    open_count: int,
    lang: str = "es",
) -> dict:
    """Decide si abrir posición sobre un candidato ya puntuado por el radar.

    `metrics` mezcla la salida de radar._score (score, price, atr_pct, passed…)
    con la de indicators.compute (ema20, ema50, atr14…).

    Devuelve {"open": False, "reason": txt} o {"open": True, ...orden...}.
    """
    cfg = mode_config(mode)

    if open_count >= cfg["max_positions"]:
        return {"open": False, "reason": L(
            lang, f"Cartera llena ({cfg['max_positions']} posiciones)",
            f"Portfolio full ({cfg['max_positions']} positions)")}

    score = _f(metrics.get("score")) or 0
    if score < cfg["min_score"]:
        return {"open": False, "reason": L(
            lang, f"Confluencia insuficiente ({score:.0f} < {cfg['min_score']})",
            f"Not enough confluence ({score:.0f} < {cfg['min_score']})")}

    atr_pct = _f(metrics.get("atr_pct"))
    if atr_pct is not None and atr_pct < cfg["min_atr_pct"]:
        return {"open": False, "reason": L(
            lang, f"Volatilidad baja para este plazo (ATR {atr_pct:.1f}%)",
            f"Volatility too low for this horizon (ATR {atr_pct:.1f}%)")}

    side = _direction(metrics, cfg)
    if side is None:
        return {"open": False, "reason": L(
            lang, "Tendencia no alineada (ni largo ni corto claros)",
            "Trend not aligned (neither long nor short is clear)")}

    entry = _f(metrics.get("price"))
    if not entry or entry <= 0:
        return {"open": False, "reason": L(lang, "Sin precio válido", "No valid price")}

    atr = _f(metrics.get("atr14"))
    stop, target = _levels(entry, side, atr, cfg)
    risk_per_share = abs(entry - stop)
    if risk_per_share <= 0:
        return {"open": False, "reason": L(lang, "Stop inválido", "Invalid stop")}

    # Tamaño por riesgo: se arriesga un % fijo del equity hasta el stop.
    risk_budget = equity * cfg["risk_pct"] / 100
    shares = risk_budget / risk_per_share
    # Topes: ni más del X% del equity en una idea, ni más caja de la que hay.
    max_notional = min(equity * cfg["max_position_pct"] / 100, cash)
    if max_notional <= 0:
        return {"open": False, "reason": L(lang, "Sin caja disponible", "No cash available")}
    shares = min(shares, max_notional / entry)
    shares = round(shares, 4)
    # Mínimo relativo al tamaño de la cartera: en una de 1.000 $ un mínimo fijo
    # de 100 $ sería el 10% del capital y descartaría operaciones razonables.
    min_notional = max(20.0, equity * 0.03)
    if shares * entry < min_notional:
        return {"open": False, "reason": L(
            lang, "Posición demasiado pequeña con el riesgo permitido",
            "Position too small for the allowed risk")}

    rr = round(abs(target - entry) / risk_per_share, 2)
    return {
        "open": True,
        "side": side,
        "entry_price": round(entry, 2),
        "shares": shares,
        "stop": stop,
        "target": target,
        "risk_amount": round(risk_per_share * shares, 2),
        "rr": rr,
        "horizon": cfg["horizon"],
        "score": round(score),
        "thesis": _thesis(metrics, side, rr, lang),
    }


def _thesis(metrics: dict, side: str, rr: float, lang: str = "es") -> str:
    """Tesis en texto a partir de las señales que SÍ se cumplieron (determinista)."""
    passed = metrics.get("passed") or []
    head = L(
        lang,
        "Largo: tendencia alcista alineada" if side == "long" else "Corto: tendencia bajista alineada",
        "Long: aligned uptrend" if side == "long" else "Short: aligned downtrend",
    )
    detail = "; ".join(passed[:4]) if passed else L(lang, "sin señales extra", "no extra signals")
    return f"{head}. {detail}. " + L(lang, f"Ratio beneficio/riesgo {rr}:1", f"Reward/risk {rr}:1")


# --------------------------------------------------------------------------
#  Cierre
# --------------------------------------------------------------------------
def check_exit(
    pos: dict,
    price: float | None,
    metrics: dict | None,
    days_held: float,
    lang: str = "es",
) -> dict:
    """Decide si cerrar una posición abierta. Prioridad: stop → objetivo →
    invalidación de la tesis → time-stop. Si no toca cerrar, puede devolver un
    stop actualizado (break-even / trailing).
    """
    cfg = mode_config(pos.get("mode", "normal"))
    if price is None:
        return {"close": False}

    side = pos["side"]
    entry, stop, target = pos["entry_price"], pos["stop"], pos["target"]
    long = side == "long"

    # 1) Stop (incluye el trailing ya guardado en la posición)
    if (long and price <= stop) or (not long and price >= stop):
        moved = pos.get("stop_moved")
        reason = TRAIL if moved else STOP
        return {"close": True, "reason": reason, "price": price, "text": L(
            lang,
            f"Stop {'dinámico' if moved else 'inicial'} tocado en {stop:.2f}",
            f"{'Trailing' if moved else 'Initial'} stop hit at {stop:.2f}")}

    # 2) Objetivo. Si la cartera deja correr las ganancias y el impulso sigue
    #    intacto, no se cierra: se blinda lo ganado subiendo el stop y se sigue.
    #    En cuanto el impulso se rompa, este mismo bloque cerrará por objetivo.
    if (long and price >= target) or (not long and price <= target):
        if cfg.get("let_winners_run") and still_trending(metrics, side):
            atr = _f((metrics or {}).get("atr14")) or abs(entry - stop)
            dist = atr * cfg["trail_atr_mult"]
            candidate = round(price - dist, 2) if long else round(price + dist, 2)
            if (long and candidate > stop) or (not long and candidate < stop):
                return {"close": False, "new_stop": candidate, "runner": True, "text": L(
                    lang,
                    f"Objetivo superado pero la tendencia aguanta: se deja correr, stop a {candidate:.2f}",
                    f"Target passed but the trend holds: letting it run, stop at {candidate:.2f}")}
            return {"close": False, "runner": True}
        return {"close": True, "reason": TARGET, "price": price, "text": L(
            lang, f"Objetivo alcanzado en {target:.2f}", f"Target reached at {target:.2f}")}

    # 3) Invalidación de la tesis (pierde la media que la sostenía)
    if metrics:
        ref = _f(metrics.get("ema50" if cfg["horizon"] != "intraday" else "ema20"))
        name = "EMA50" if cfg["horizon"] != "intraday" else "EMA20"
        if ref is not None and ((long and price < ref) or (not long and price > ref)):
            return {"close": True, "reason": INVALIDATED, "price": price, "text": L(
                lang, f"Tesis invalidada: precio al otro lado de la {name}",
                f"Thesis invalidated: price crossed the {name}")}

    # 4) Time-stop: si en su plazo no ha hecho nada, el capital se libera
    if days_held >= cfg["max_hold_days"]:
        return {"close": True, "reason": TIME, "price": price, "text": L(
            lang, f"Plazo agotado ({cfg['max_hold_days']} días) sin alcanzar objetivo",
            f"Time limit reached ({cfg['max_hold_days']} days) without hitting target")}

    # 5) Sin cierre: ¿toca mover el stop?
    risk = abs(entry - pos.get("initial_stop", stop)) or abs(entry - stop)
    if risk > 0:
        progress = ((price - entry) if long else (entry - price)) / risk
        new_stop = None
        if progress >= cfg["trail_r"]:
            atr = _f((metrics or {}).get("atr14")) or risk / cfg.get("stop_atr_mult", 2.0)
            dist = atr * cfg["trail_atr_mult"]
            candidate = round(price - dist, 2) if long else round(price + dist, 2)
            if (long and candidate > stop) or (not long and candidate < stop):
                new_stop = candidate
        elif progress >= cfg["breakeven_r"]:
            be = round(entry, 2)
            if (long and be > stop) or (not long and be < stop):
                new_stop = be
        if new_stop is not None:
            return {"close": False, "new_stop": new_stop, "text": L(
                lang, f"Stop movido a {new_stop:.2f}", f"Stop moved to {new_stop:.2f}")}

    return {"close": False}


def exit_reason_label(reason: str, lang: str = "es") -> str:
    labels = {
        STOP: ("Stop", "Stop"),
        TRAIL: ("Stop dinámico", "Trailing stop"),
        TARGET: ("Objetivo", "Target"),
        INVALIDATED: ("Tesis invalidada", "Thesis invalidated"),
        TIME: ("Plazo agotado", "Time limit"),
        MANUAL: ("Cierre manual", "Manual close"),
    }
    es, en = labels.get(reason, (reason, reason))
    return L(lang, es, en)
