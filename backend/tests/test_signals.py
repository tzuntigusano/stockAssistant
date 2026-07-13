"""Motor de veredictos determinista (core.signals).

La IA solo redacta encima de esto, así que estas reglas son el "cerebro":
merecen tests que fijen su comportamiento.
"""

from core.signals import evaluate


def _ind(**over) -> dict:
    """Indicadores neutrales por defecto; cada test sobreescribe lo que necesita."""
    base = {
        "ok": True,
        "price": 100.0,
        "ema20": 100.0,
        "ema50": 100.0,
        "ema200": 100.0,
        "rsi14": 50.0,
        "macd_hist": 0.0,
        "change_20d": 0.0,
        "high_52w": 130.0,
        "low_52w": 70.0,
    }
    base.update(over)
    return base


def test_datos_insuficientes_devuelve_neutral():
    out = evaluate({"ok": False, "reason": "pocos_datos"})
    assert out["score"] == 50
    assert out["label"] == "NEUTRAL"
    assert out["signals"] == []


def test_escenario_muy_alcista_puntua_alto():
    out = evaluate(_ind(price=120, ema20=110, ema50=105, ema200=100,
                        rsi14=60, macd_hist=1.5, change_20d=12))
    assert out["score"] >= 70
    assert out["label"] == "ALCISTA"


def test_escenario_muy_bajista_puntua_bajo():
    out = evaluate(_ind(price=80, ema20=90, ema50=95, ema200=100,
                        rsi14=40, macd_hist=-1.5, change_20d=-12))
    assert out["score"] <= 42
    assert "BAJISTA" in out["label"]


def test_score_siempre_entre_0_y_100():
    fuerte = evaluate(_ind(price=200, ema20=150, ema50=120, ema200=100,
                           rsi14=72, macd_hist=5, change_20d=40, high_52w=201))
    assert 0 <= fuerte["score"] <= 100


def test_ingles_traduce_la_etiqueta():
    out = evaluate(_ind(price=120, ema20=110, ema50=105, ema200=100,
                        macd_hist=1.5), lang="en")
    assert out["label"] == "BULLISH"
    # y las señales salen en inglés
    assert any("Price above" in s["text"] for s in out["signals"])


def test_las_senales_se_ordenan_por_peso():
    out = evaluate(_ind(price=120, ema20=110, ema50=105, ema200=100, macd_hist=1))
    pesos = [s["weight"] for s in out["signals"]]
    assert pesos == sorted(pesos, reverse=True)
