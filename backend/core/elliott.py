"""Ondas de Elliott: conteo DETERMINISTA (la IA solo lo narra después).

Pipeline:
  1. ZigZag: reduce las velas a pivotes alternos (máx/mín) con un retroceso
     mínimo. El umbral define la ESCALA del conteo (Elliott es fractal).
  2. Etiquetado: intenta leer los últimos pivotes como un impulso 1-2-3-4-5
     (alcista o bajista) validando las TRES REGLAS DURAS de Elliott. Si no
     encaja, prueba una corrección A-B-C.
  3. Fibonacci: niveles de retroceso/proyección de la onda en curso.

OJO: Elliott es subjetivo por naturaleza y los conteos se revisan al llegar
velas nuevas. Esto devuelve UN conteo plausible que cumple las reglas, no "la
verdad". Por eso se acompaña siempre de `rules` y `confidence`.
"""

from __future__ import annotations

# Reglas duras (si una falla, el conteo se descarta)
RULE_LABELS = {
    "r1": "La onda 2 no retrocede más del 100% de la onda 1",
    "r2": "La onda 3 no es la más corta de 1, 3 y 5",
    "r3": "La onda 4 no invade el territorio de la onda 1",
}

FIB_RETRACE = (0.382, 0.5, 0.618, 0.786)
FIB_EXTEND = (1.0, 1.618, 2.618)


def zigzag(bars: list[dict], threshold: float = 0.05) -> list[dict]:
    """Pivotes alternos: se confirma un extremo cuando el precio retrocede
    `threshold` (fracción: 0.05 = 5%) desde él."""
    n = len(bars)
    if n < 3:
        return []
    pivots: list[dict] = []
    direction = 0  # 1 = tramo al alza (buscando máximo), -1 = a la baja
    ext_i, ext_p = 0, bars[0]["close"]
    run_hi_i, run_hi = 0, bars[0]["high"]
    run_lo_i, run_lo = 0, bars[0]["low"]

    for i in range(1, n):
        hi, lo = bars[i]["high"], bars[i]["low"]
        if direction == 1:
            if hi >= ext_p:
                ext_i, ext_p = i, hi
            elif lo <= ext_p * (1 - threshold):
                pivots.append({"index": ext_i, "price": ext_p, "kind": "H"})
                direction, ext_i, ext_p = -1, i, lo
        elif direction == -1:
            if lo <= ext_p:
                ext_i, ext_p = i, lo
            elif hi >= ext_p * (1 + threshold):
                pivots.append({"index": ext_i, "price": ext_p, "kind": "L"})
                direction, ext_i, ext_p = 1, i, hi
        else:
            # Aún sin dirección: seguimos máximo y mínimo hasta que uno rompa.
            if hi > run_hi:
                run_hi_i, run_hi = i, hi
            if lo < run_lo:
                run_lo_i, run_lo = i, lo
            if hi >= run_lo * (1 + threshold):
                pivots.append({"index": run_lo_i, "price": run_lo, "kind": "L"})
                direction, ext_i, ext_p = 1, i, hi
            elif lo <= run_hi * (1 - threshold):
                pivots.append({"index": run_hi_i, "price": run_hi, "kind": "H"})
                direction, ext_i, ext_p = -1, i, lo

    # Extremo en curso (la onda que se está formando): provisional.
    if direction != 0:
        pivots.append({
            "index": ext_i,
            "price": ext_p,
            "kind": "H" if direction == 1 else "L",
            "provisional": True,
        })
    return pivots


def _alternates(pivots: list[dict], start_kind: str) -> bool:
    """Los pivotes deben alternar H/L empezando por `start_kind`."""
    want = start_kind
    for p in pivots:
        if p["kind"] != want:
            return False
        want = "L" if want == "H" else "H"
    return True


def _check_rules(pts: list[float], up: bool) -> dict:
    """Reglas duras sobre los precios de los pivotes P0..Pk."""
    rules: dict[str, bool] = {}
    n = len(pts)
    sign = 1 if up else -1

    if n >= 3:  # hay onda 2
        rules["r1"] = (pts[2] - pts[0]) * sign > 0
    if n >= 5:  # hay onda 4 → se puede juzgar la 3 más corta y el solape
        len1 = abs(pts[1] - pts[0])
        len3 = abs(pts[3] - pts[2])
        len5 = abs(pts[5] - pts[4]) if n >= 6 else None
        rules["r2"] = not (len5 is not None and len3 < len1 and len3 < len5)
        rules["r3"] = (pts[4] - pts[1]) * sign > 0
    return rules


def _fib_levels(pts: list[float], current: int, up: bool) -> list[dict]:
    """Niveles relevantes para la onda EN CURSO."""
    out = []
    sign = 1 if up else -1

    def add(label: str, price: float):
        out.append({"label": label, "price": round(price, 4)})

    if current == 2 and len(pts) >= 2:  # retroceso de la 1
        len1 = pts[1] - pts[0]
        for r in FIB_RETRACE:
            add(f"O2 {r:.3f}", pts[1] - len1 * r)
    elif current == 3 and len(pts) >= 3:  # proyección de la 3
        len1 = pts[1] - pts[0]
        for r in FIB_EXTEND:
            add(f"O3 {r:.3f}", pts[2] + len1 * r * sign * (1 if len1 * sign > 0 else -1))
    elif current == 4 and len(pts) >= 4:  # retroceso de la 3
        len3 = pts[3] - pts[2]
        for r in (0.236, 0.382, 0.5):
            add(f"O4 {r:.3f}", pts[3] - len3 * r)
    elif current == 5 and len(pts) >= 5:  # proyección de la 5
        len1 = pts[1] - pts[0]
        for r in (0.618, 1.0, 1.618):
            add(f"O5 {r:.3f}", pts[4] + len1 * r)
    return out


def _build_impulse(seq: list[dict], up: bool, rules: dict, at_end: bool) -> dict:
    pts = [p["price"] for p in seq]
    completed = len(seq) - 1  # ondas terminadas
    provisional = seq[-1].get("provisional", False)
    current = min(completed + 1, 5) if provisional else completed
    # Más ondas y reglas validadas = más confianza; si el conteo no llega hasta
    # el último pivote, es menos relevante para operar ahora.
    conf = 0.3 + 0.08 * completed + 0.1 * len(rules) + (0.15 if at_end else 0.0)
    return {
        "pattern": "impulse_up" if up else "impulse_down",
        "up": up,
        "pivots": seq,
        "labels": [str(i) for i in range(len(seq))],  # P0, 1, 2, 3...
        "rules": rules,
        "completed_waves": completed,
        "current_wave": current,
        "fibs": _fib_levels(pts, current, up),
        "confidence": round(min(1.0, conf), 2),
    }


def _try_impulse(pivots: list[dict], up: bool) -> dict | None:
    """Busca DÓNDE encaja un impulso 1-5 válido entre los pivotes recientes.

    Un analista no mira solo los últimos 6 puntos: busca el tramo donde la
    estructura cuadra. Barremos finales recientes y, para cada uno, el arranque
    que dé más ondas, descartando todo lo que viole una regla dura.
    """
    start_kind = "L" if up else "H"
    n = len(pivots)
    best = None
    for end in range(n - 1, max(n - 5, 0), -1):      # 4 finales más recientes
        for length in (6, 5, 4, 3):                   # preferimos más ondas
            start = end - length + 1
            if start < 0:
                continue
            seq = pivots[start : end + 1]
            if seq[0]["kind"] != start_kind or not _alternates(seq, start_kind):
                continue
            rules = _check_rules([p["price"] for p in seq], up)
            if any(v is False for v in rules.values()):
                continue  # viola una regla dura → conteo inválido
            cand = _build_impulse(seq, up, rules, at_end=(end == n - 1))
            if best is None or cand["confidence"] > best["confidence"]:
                best = cand
            break  # con este final ya tenemos el conteo más largo válido
    return best


def _try_abc(pivots: list[dict], up: bool) -> dict | None:
    """Corrección simple A-B-C (3 tramos) cuando no hay impulso válido."""
    start = "H" if up else "L"  # una corrección bajista arranca en un máximo
    seq = pivots[-4:]
    while seq and seq[0]["kind"] != start:
        seq = seq[1:]
    if len(seq) < 3 or not _alternates(seq, start):
        return None
    return {
        "pattern": "abc",
        "up": up,
        "pivots": seq,
        "labels": ["0", "A", "B", "C"][: len(seq)],
        "rules": {},
        "completed_waves": len(seq) - 1,
        "current_wave": len(seq) - 1,
        "fibs": [],
        "confidence": 0.35,
    }


def detect(bars: list[dict], threshold: float = 0.05) -> dict:
    """Conteo de ondas sobre las velas dadas. Devuelve {} si no hay nada claro."""
    pivots = zigzag(bars, threshold)
    if len(pivots) < 3:
        return {}
    candidates = [
        _try_impulse(pivots, up=True),
        _try_impulse(pivots, up=False),
        _try_abc(pivots, up=True),
        _try_abc(pivots, up=False),
    ]
    best = max((c for c in candidates if c), key=lambda c: c["confidence"], default=None)
    if not best:
        return {}
    best["threshold"] = threshold
    best["all_pivots"] = pivots
    return best


def summarize(res: dict, lang: str = "es") -> str:
    """Resumen en texto del conteo, para que la IA lo NARRE (no lo invente)."""
    if not res:
        return ""
    from core.i18n import L

    if res["pattern"] == "abc":
        head = L(lang, "Corrección A-B-C en curso", "A-B-C correction in progress")
    else:
        head = L(
            lang,
            f"Impulso {'alcista' if res['up'] else 'bajista'} de Elliott",
            f"{'Bullish' if res['up'] else 'Bearish'} Elliott impulse",
        )
    lines = [
        f"ONDAS DE ELLIOTT: {head}",
        L(lang, f"Onda en curso: {res['current_wave']}", f"Current wave: {res['current_wave']}")
        + L(lang, f" (ondas completadas: {res['completed_waves']})",
            f" (completed waves: {res['completed_waves']})"),
        L(lang, f"Confianza del conteo: {res['confidence']:.0%}",
          f"Count confidence: {res['confidence']:.0%}"),
    ]
    for p, label in zip(res["pivots"], res["labels"], strict=False):
        lines.append(f"  {label}: {round(p['price'], 4)}")
    if res.get("fibs"):
        lines.append(L(lang, "Niveles Fibonacci de la onda en curso:",
                       "Fibonacci levels for the current wave:"))
        for f in res["fibs"]:
            lines.append(f"  {f['label']} → {f['price']}")
    lines.append(
        L(lang,
          "(Conteo determinista que cumple las 3 reglas de Elliott. Es UNA lectura "
          "posible, no la única: puede revisarse con velas nuevas.)",
          "(Deterministic count satisfying Elliott's 3 rules. It is ONE possible "
          "reading, not the only one: it may be revised as new candles arrive.)")
    )
    return "\n".join(lines)
