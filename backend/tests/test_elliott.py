"""Conteo de ondas de Elliott (core.elliott).

Se construyen recorridos de precio sintéticos con giros exactos, para poder
comprobar que el ZigZag encuentra esos giros y que las TRES REGLAS DURAS
descartan los conteos inválidos.
"""

from core import elliott


def _bars(path: list[float], steps: int = 6) -> list[dict]:
    """Velas interpolando en línea recta entre los puntos de giro."""
    def bar(p: float) -> dict:
        return {"open": p, "high": p, "low": p, "close": p, "volume": 1000}

    out = [bar(path[0])]
    for a, b in zip(path, path[1:], strict=False):
        for s in range(steps):
            out.append(bar(a + (b - a) * (s + 1) / steps))
    return out


# Impulso alcista de manual: 100 → 120 → 110 → 160 → 140 → 175
IMPULSO = [100, 120, 110, 160, 140, 175]


def test_zigzag_encuentra_los_giros():
    piv = elliott.zigzag(_bars(IMPULSO), threshold=0.05)
    precios = [round(p["price"], 2) for p in piv]
    assert precios == [100, 120, 110, 160, 140, 175]
    assert [p["kind"] for p in piv] == ["L", "H", "L", "H", "L", "H"]
    assert piv[-1].get("provisional") is True  # la última onda está en curso


def test_impulso_alcista_valido():
    res = elliott.detect(_bars(IMPULSO), threshold=0.05)
    assert res["pattern"] == "impulse_up"
    assert res["rules"] == {"r1": True, "r2": True, "r3": True}
    assert res["current_wave"] == 5
    assert res["confidence"] > 0.5


def test_regla3_detecta_el_solape_de_la_onda_4():
    # Onda 4 (115) invade el territorio de la onda 1 (120).
    reglas = elliott._check_rules([100, 120, 110, 160, 115, 175], up=True)
    assert reglas["r3"] is False


def test_regla1_detecta_retroceso_mayor_del_100():
    # Onda 2 (95) cae por debajo del origen (100).
    reglas = elliott._check_rules([100, 120, 95, 160, 140, 175], up=True)
    assert reglas["r1"] is False


def test_regla2_detecta_la_onda_3_mas_corta():
    # len1=100, len3=10, len5=80 → la 3 es la más corta.
    reglas = elliott._check_rules([100, 200, 150, 160, 120, 200], up=True)
    assert reglas["r2"] is False


def test_un_conteo_que_viola_reglas_no_se_devuelve_entero():
    # Con el solape de la onda 4, no puede devolverse la secuencia completa de 6.
    piv = elliott.zigzag(_bars([100, 120, 110, 160, 115, 175]), threshold=0.05)
    res = elliott._try_impulse(piv, up=True)
    assert res is None or len(res["pivots"]) < 6


def test_fibonacci_de_la_onda_en_curso():
    res = elliott.detect(_bars(IMPULSO), threshold=0.05)
    assert res["fibs"], "deberia proponer niveles para la onda 5"
    assert all("price" in f and "label" in f for f in res["fibs"])


def test_summarize_menciona_onda_y_confianza():
    res = elliott.detect(_bars(IMPULSO), threshold=0.05)
    txt = elliott.summarize(res, "es")
    assert "ELLIOTT" in txt
    assert "Onda en curso" in txt
    assert "Confianza" in txt


def test_pocas_velas_no_detecta():
    assert elliott.detect([], threshold=0.05) == {}
    assert elliott.zigzag([{"open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]) == []
