"""Detección de líneas de tendencia (lo que un chartista traza a mano).

No es un indicador de librería: se aproxima. La idea:
  1. Detectar pivotes (swing highs/lows): extremos locales.
  2. Ajustar rectas entre pivotes del mismo tipo.
  3. Validar: una recta de SOPORTE es válida si los CIERRES la respetan (no
     cierran por debajo) desde su primer ancla; resistencia al revés.
  4. Puntuar y quedarse con las más ÚTILES: se priorizan las cercanas al precio
     actual (a punto de romperse/testearse) y con más toques; se devuelven
     varias candidatas de cada tipo para poder elegir.

Es determinista y transparente. Como es una aproximación, lo suyo es DIBUJARLA
en el gráfico para validarla con el ojo.
"""

from __future__ import annotations

NEAR_PCT = 0.15  # una recta es "relevante" si su valor de hoy está a ≤15% del precio


def _swings(bars: list[dict], k: int) -> tuple[list[int], list[int]]:
    """Índices de swing highs y swing lows (extremo local en ventana ±k)."""
    highs, lows = [], []
    n = len(bars)
    for i in range(k, n - k):
        seg = bars[i - k : i + k + 1]
        if bars[i]["high"] >= max(b["high"] for b in seg):
            highs.append(i)
        if bars[i]["low"] <= min(b["low"] for b in seg):
            lows.append(i)
    return highs, lows


def _median_range(bars: list[dict]) -> float:
    rngs = sorted(b["high"] - b["low"] for b in bars)
    return rngs[len(rngs) // 2] if rngs else 0.0


def value_at(line: dict, index_in_window: int) -> float:
    """Valor de la recta en un índice (referido a la ventana usada en detect)."""
    return line["intercept"] + line["slope"] * index_in_window


def _candidates(bars: list[dict], pivots: list[int], kind: str, tol: float) -> list[dict]:
    """Todas las rectas válidas (cierres las respetan, ≥2 toques) de un tipo."""
    key = "low" if kind == "support" else "high"
    out = []
    for a in range(len(pivots)):
        for b in range(a + 1, len(pivots)):
            i1, i2 = pivots[a], pivots[b]
            if i2 == i1:
                continue
            slope = (bars[i2][key] - bars[i1][key]) / (i2 - i1)
            intercept = bars[i1][key] - slope * i1

            broken = False
            for x in range(i1, len(bars)):
                ly = intercept + slope * x
                c = bars[x]["close"]
                if (kind == "support" and c < ly - tol) or (
                    kind == "resistance" and c > ly + tol
                ):
                    broken = True
                    break
            if broken:
                continue

            touches = sum(
                1
                for pi in pivots
                if pi >= i1 and abs(bars[pi][key] - (intercept + slope * pi)) <= tol
            )
            if touches >= 2:
                out.append({"kind": kind, "i1": i1, "slope": slope,
                            "intercept": intercept, "touches": touches})
    return out


def detect(bars: list[dict], k: int = 3, window: int = 150, max_per_kind: int = 2) -> list[dict]:
    """Hasta `max_per_kind` rectas de soporte y de resistencia sobre las últimas
    `window` velas, priorizando las cercanas al precio y con más toques."""
    if not bars or len(bars) < 2 * k + 5:
        return []
    data = bars[-window:]
    tol = _median_range(data)
    price = data[-1]["close"]
    last = len(data) - 1
    highs, lows = _swings(data, k)
    offset = len(bars) - len(data)

    out = []
    for kind, pivots in (("support", lows), ("resistance", highs)):
        cands = _candidates(data, pivots, kind, tol)
        # Relevancia: primero las cuyo valor de hoy está cerca del precio.
        near = [c for c in cands if price and abs(value_at(c, last) - price) / price <= NEAR_PCT]
        pool = near or cands
        # Más toques y ancla más reciente primero.
        pool.sort(key=lambda c: (c["touches"], c["i1"]), reverse=True)
        # Quita casi-duplicadas (mismo valor de hoy dentro de tol).
        kept: list[dict] = []
        for c in pool:
            v = value_at(c, last)
            if all(abs(v - value_at(o, last)) > tol for o in kept):
                c["offset"] = offset
                kept.append(c)
            if len(kept) >= max_per_kind:
                break
        out.extend(kept)
    return out
