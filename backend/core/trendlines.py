"""Detección de líneas de tendencia (lo que un chartista traza a mano).

No es un indicador de librería: se aproxima. La idea:
  1. Detectar pivotes (swing highs/lows): extremos locales.
  2. Ajustar rectas entre pivotes del mismo tipo.
  3. Validar: una recta de SOPORTE es válida si los CIERRES la respetan (no
     cierran por debajo) desde su primer ancla; resistencia al revés.
  4. Puntuar por nº de toques (y recencia) y quedarse con la mejor de cada tipo.

Es determinista y transparente. Como es una aproximación, lo suyo es DIBUJARLA
en el gráfico para validarla con el ojo.
"""

from __future__ import annotations


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


def _fit(bars: list[dict], pivots: list[int], kind: str, tol: float) -> dict | None:
    """Mejor recta (soporte o resistencia) que pasa por dos pivotes y que los
    cierres respetan desde el primer ancla hasta el final."""
    key = "low" if kind == "support" else "high"
    best = None
    for a in range(len(pivots)):
        for b in range(a + 1, len(pivots)):
            i1, i2 = pivots[a], pivots[b]
            if i2 == i1:
                continue
            slope = (bars[i2][key] - bars[i1][key]) / (i2 - i1)
            intercept = bars[i1][key] - slope * i1

            # La recta no debe estar rota: los cierres la respetan desde i1.
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
            score = (touches, i2)  # más toques y ancla más reciente
            if touches >= 2 and (best is None or score > best["score"]):
                best = {
                    "kind": kind,
                    "i1": i1,
                    "slope": slope,
                    "intercept": intercept,
                    "touches": touches,
                    "score": score,
                }
    return best


def detect(bars: list[dict], k: int = 3, window: int = 150) -> list[dict]:
    """Devuelve hasta una recta de soporte y una de resistencia sobre las
    últimas `window` velas. Cada recta: kind, touches, slope/intercept (en
    índice de vela) e índice del primer ancla `i1`."""
    if not bars or len(bars) < 2 * k + 5:
        return []
    data = bars[-window:]
    tol = _median_range(data)
    highs, lows = _swings(data, k)
    out = []
    sup = _fit(data, lows, "support", tol)
    res = _fit(data, highs, "resistance", tol)
    for line in (sup, res):
        if not line:
            continue
        line.pop("score", None)
        # Offset del índice al conjunto original (por si se recorta la ventana).
        line["offset"] = len(bars) - len(data)
        out.append(line)
    return out


def value_at(line: dict, index_in_window: int) -> float:
    """Valor de la recta en un índice (referido a la ventana usada en detect)."""
    return line["intercept"] + line["slope"] * index_in_window
