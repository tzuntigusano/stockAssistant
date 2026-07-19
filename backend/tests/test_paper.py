"""Motor de decisión de las carteras ficticias (core.paper).

Es quien decide qué se compra, cuánto y cuándo se sale, así que cada regla
merece su test: alineación de tendencia, tamaño por riesgo, stops/objetivos y
las cuatro salidas (stop, objetivo, invalidación, plazo) más el trailing.
"""

from core import paper


def _metrics(price=100.0, ema20=98.0, ema50=95.0, rsi=60.0, atr=2.0, score=80, atr_pct=2.5,
             macd_hist=0.5):
    return {
        "price": price, "ema20": ema20, "ema50": ema50, "rsi": rsi,
        "atr14": atr, "score": score, "atr_pct": atr_pct, "macd_hist": macd_hist,
        "passed": ["Volumen 2.0× la media", "MACD alcista"],
    }


def _position(mode="normal", side="long", entry=100.0, stop=96.0, target=110.0, shares=10.0):
    return {
        "mode": mode, "side": side, "entry_price": entry, "stop": stop,
        "initial_stop": stop, "target": target, "shares": shares, "stop_moved": False,
    }


# --- Apertura: filtros ---

def test_no_abre_si_la_confluencia_es_baja():
    plan = paper.plan_entry(_metrics(score=30), "normal", 1_000, 1_000, 0)
    assert plan["open"] is False


def test_no_abre_si_la_cartera_esta_llena():
    cfg = paper.mode_config("normal")
    plan = paper.plan_entry(_metrics(), "normal", 1_000, 1_000, cfg["max_positions"])
    assert plan["open"] is False


def test_no_abre_sin_tendencia_alineada():
    # Precio por encima de la EMA20 pero la EMA20 por debajo de la EMA50: revuelto.
    plan = paper.plan_entry(_metrics(price=100, ema20=98, ema50=99), "normal", 1_000, 1_000, 0)
    assert plan["open"] is False


def test_no_abre_si_la_volatilidad_es_insuficiente_en_la_rapida():
    # ATR 1.2% pasa el filtro de la normal (1%) pero no el de la rápida (2%).
    m = _metrics(atr_pct=1.2)
    assert paper.plan_entry(m, "normal", 1_000, 1_000, 0)["open"] is True
    assert paper.plan_entry(m, "fast", 1_000, 1_000, 0)["open"] is False


def test_no_abre_sin_caja():
    plan = paper.plan_entry(_metrics(), "normal", 1_000, 0, 0)
    assert plan["open"] is False


def test_funciona_con_una_cartera_pequena_de_1000():
    # Con 1.000 $ el tope del 20% deja 200 $; debe seguir abriendo posiciones.
    plan = paper.plan_entry(_metrics(), "normal", 1_000, 1_000, 0)
    assert plan["open"] is True
    notional = plan["shares"] * plan["entry_price"]
    assert 30 <= notional <= 200


# --- Apertura: dirección, niveles y tamaño ---

def test_abre_largo_con_tendencia_alcista():
    plan = paper.plan_entry(_metrics(), "normal", 1_000, 1_000, 0)
    assert plan["open"] is True
    assert plan["side"] == "long"
    assert plan["stop"] < plan["entry_price"] < plan["target"]


def test_abre_corto_con_tendencia_bajista():
    m = _metrics(price=95.0, ema20=98.0, ema50=100.0, rsi=40.0)
    plan = paper.plan_entry(m, "normal", 1_000, 1_000, 0)
    assert plan["open"] is True
    assert plan["side"] == "short"
    assert plan["target"] < plan["entry_price"] < plan["stop"]


def test_el_tamano_respeta_el_riesgo_configurado():
    # Riesgo 0.6% de 1.000 = 6 $; stop a 2×ATR = 4 $ por acción → 1.5 acciones.
    plan = paper.plan_entry(_metrics(), "normal", 1_000, 1_000, 0)
    assert plan["shares"] == 1.5
    assert plan["risk_amount"] == 6.0
    # Y el presupuesto de riesgo manda: la posición queda por debajo del tope.
    assert plan["shares"] * plan["entry_price"] < 1_000 * 0.20


def test_el_tamano_se_limita_por_la_exposicion_maxima():
    # Un stop muy ceñido pediría muchísimas acciones: manda el tope del 20%.
    plan = paper.plan_entry(_metrics(atr=0.1), "normal", 1_000, 1_000, 0)
    assert plan["shares"] * plan["entry_price"] <= 1_000 * 0.20 + 1


def test_la_cartera_rapida_usa_objetivos_en_porcentaje():
    plan = paper.plan_entry(_metrics(), "fast", 1_000, 1_000, 0)
    assert plan["open"] is True
    assert plan["target"] == 103.0  # +3% fijo
    assert plan["horizon"] == "intraday"


def test_las_aperturas_por_ciclo_estan_limitadas():
    # Si no, un solo día de señales llenaría la cartera entera de golpe.
    for mode in ("normal", "fast"):
        cfg = paper.mode_config(mode)
        assert 0 < cfg["max_new_per_cycle"] < cfg["max_positions"]


# --- Cierres ---

def test_cierra_por_stop():
    r = paper.check_exit(_position(), 95.0, _metrics(), 1.0)
    assert r["close"] is True
    assert r["reason"] == paper.STOP


def test_cierra_por_objetivo():
    r = paper.check_exit(_position(), 111.0, _metrics(), 1.0)
    assert r["close"] is True
    assert r["reason"] == paper.TARGET


def test_cierra_por_tesis_invalidada():
    # Ni stop ni objetivo, pero el precio se va por debajo de la EMA50.
    r = paper.check_exit(_position(stop=90.0), 97.0, _metrics(ema50=98.0), 1.0)
    assert r["close"] is True
    assert r["reason"] == paper.INVALIDATED


def test_cierra_por_plazo_agotado():
    cfg = paper.mode_config("normal")
    r = paper.check_exit(_position(stop=90.0), 101.0, _metrics(ema50=95.0), cfg["max_hold_days"])
    assert r["close"] is True
    assert r["reason"] == paper.TIME


def test_corto_cierra_por_stop_al_subir():
    pos = _position(side="short", entry=100.0, stop=104.0, target=92.0)
    r = paper.check_exit(pos, 105.0, _metrics(ema50=110.0), 1.0)
    assert r["close"] is True
    assert r["reason"] == paper.STOP


# --- Dejar correr las ganancias (solo cartera rápida) ---

def test_la_rapida_no_cierra_en_el_objetivo_si_la_tendencia_aguanta():
    # Precio por encima del objetivo, pero EMA20 + MACD + RSI siguen alcistas.
    pos = _position(mode="fast", entry=100.0, stop=98.5, target=103.0)
    met = _metrics(price=103.5, ema20=101.0, ema50=99.0, rsi=65, macd_hist=0.4, atr=0.8)
    r = paper.check_exit(pos, 103.5, met, 0.5)
    assert r["close"] is False
    assert r["runner"] is True
    assert r["new_stop"] > 98.5  # y blinda lo ganado subiendo el stop


def test_la_rapida_si_cierra_en_el_objetivo_cuando_el_impulso_se_apaga():
    # Mismo precio, pero el MACD ya gira: se toma el beneficio.
    pos = _position(mode="fast", entry=100.0, stop=98.5, target=103.0)
    met = _metrics(price=103.5, ema20=101.0, ema50=99.0, rsi=65, macd_hist=-0.1, atr=0.8)
    r = paper.check_exit(pos, 103.5, met, 0.5)
    assert r["close"] is True
    assert r["reason"] == paper.TARGET


def test_la_normal_cierra_siempre_en_el_objetivo():
    # La cartera de swing no estira: su ventaja ya está en el trailing previo.
    met = _metrics(price=111.0, ema20=105.0, ema50=95.0, rsi=70, macd_hist=0.6)
    r = paper.check_exit(_position(), 111.0, met, 1.0)
    assert r["close"] is True
    assert r["reason"] == paper.TARGET


def test_still_trending_exige_las_tres_patas():
    fuerte = _metrics(price=103.0, ema20=101.0, rsi=60, macd_hist=0.3)
    assert paper.still_trending(fuerte, "long") is True
    assert paper.still_trending({**fuerte, "rsi": 50}, "long") is False
    assert paper.still_trending({**fuerte, "macd_hist": -0.1}, "long") is False
    assert paper.still_trending({**fuerte, "price": 100.0}, "long") is False
    assert paper.still_trending(None, "long") is False


# --- Trailing ---

def test_el_stop_sube_a_break_even_en_1r():
    # R = 4 €; a +1R (104) el stop pasa de 96 a la entrada.
    r = paper.check_exit(_position(), 104.0, _metrics(ema50=95.0), 1.0)
    assert r["close"] is False
    assert r["new_stop"] == 100.0


def test_el_stop_persigue_al_precio_pasado_1_5r():
    # A +2R (108) el stop trepa por detrás del precio, ya por encima de la entrada.
    r = paper.check_exit(_position(), 108.0, _metrics(ema50=95.0), 1.0)
    assert r["close"] is False
    assert r["new_stop"] > 100.0


def test_sin_movimiento_no_toca_el_stop():
    r = paper.check_exit(_position(), 101.0, _metrics(ema50=95.0), 1.0)
    assert r["close"] is False
    assert "new_stop" not in r


# --- Contabilidad ---

def test_pnl_realizado_en_largo_y_en_corto():
    largo = {**_position(), "exit_price": 110.0}
    corto = {**_position(side="short"), "exit_price": 90.0}
    assert paper.realized_pnl(largo) == 100.0
    assert paper.realized_pnl(corto) == 100.0


def test_valor_de_una_posicion_corta_incluye_la_garantia():
    # Corto de 10 a 100 con el precio en 90: 1.000 de garantía + 100 de ganancia.
    assert paper.position_value(_position(side="short"), 90.0) == 1100.0
