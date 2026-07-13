"""Estrategia: combina veredicto técnico + posición del usuario.

Genera un contexto estructurado en texto (que sirve para el LLM y como
resumen determinista) y niveles operativos sencillos.
"""

from __future__ import annotations


def _fmt(v, suffix="") -> str:
    return f"{v}{suffix}" if v is not None else "n/d"


def build_levels(ind: dict, position: dict) -> dict:
    """Niveles operativos derivados de ATR, soportes/resistencias y coste medio."""
    price = ind.get("price")
    atr = ind.get("atr14")
    levels = {
        "support": ind.get("support"),
        "resistance": ind.get("resistance"),
        "ema50": ind.get("ema50"),
    }
    if price and atr:
        # Stop sugerido: ~1.5x ATR bajo el precio (gestión de riesgo básica)
        levels["suggested_stop"] = round(price - 1.5 * atr, 2)
        levels["atr14"] = atr
    if position.get("has_position"):
        levels["avg_cost"] = position.get("avg_price")
        levels["breakeven"] = position.get("avg_price")
    return levels


def _pct(v) -> str:
    return f"{round(v * 100, 1)}%" if v is not None else "n/d"


def _big(v) -> str:
    """Número grande legible: T/B/M (billón/mil millones/millón en escala EE.UU.)."""
    if v is None:
        return "n/d"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{v / div:.2f}{suf}"
    return f"{v:.0f}"


def build_technical_context(ticker: str, quote: dict, ind: dict, verdict: dict, levels: dict) -> str:
    """Bloque técnico (indicadores + veredicto determinista + niveles)."""
    lines = [f"VALOR: {ticker} — {quote.get('name', '')}"]
    lines.append(
        f"Precio: {_fmt(quote.get('price'))} {quote.get('currency', '')} "
        f"(1d {_fmt(ind.get('change_1d'), '%')}, 5d {_fmt(ind.get('change_5d'), '%')}, "
        f"20d {_fmt(ind.get('change_20d'), '%')})"
    )
    lines.append(f"VEREDICTO TÉCNICO: {verdict['label']} (puntuación {verdict['score']}/100)")
    if verdict.get("signals"):
        lines.append("Señales detectadas:")
        for s in verdict["signals"][:6]:
            lines.append(f"  - [{s['bias']}] {s['text']}")
    lines.append(
        "Indicadores: "
        f"RSI14 {_fmt(ind.get('rsi14'))}, "
        f"EMA20 {_fmt(ind.get('ema20'))}, EMA50 {_fmt(ind.get('ema50'))}, "
        f"EMA200 {_fmt(ind.get('ema200'))}, "
        f"MACD hist {_fmt(ind.get('macd_hist'))}, "
        f"ATR14 {_fmt(ind.get('atr14'))} ({_fmt(ind.get('atr_pct'), '%')})"
    )
    lines.append(
        f"Rango 52 sem: {_fmt(ind.get('low_52w'))} — {_fmt(ind.get('high_52w'))}. "
        f"Soporte {_fmt(levels.get('support'))}, resistencia {_fmt(levels.get('resistance'))}, "
        f"stop sugerido {_fmt(levels.get('suggested_stop'))}."
    )
    return "\n".join(lines)


def build_position_context(position: dict) -> str:
    """Bloque de la posición del usuario (solo si la tiene)."""
    if not position.get("has_position"):
        return "POSICIÓN DEL USUARIO: sin posición abierta."
    lines = [
        f"POSICIÓN DEL USUARIO: {position['total_shares']} acciones a coste medio "
        f"{position['avg_price']} (invertido {position['total_cost']}). "
        f"P&L no realizado {_fmt(position.get('unrealized_pnl'))} "
        f"({_fmt(position.get('unrealized_pnl_pct'), '%')})."
    ]
    realized = position.get("realized_pnl")
    if realized:
        lines.append(f"P&L realizado (ventas previas): {_fmt(realized)}.")
    return "\n".join(lines)


def build_fundamental_context(fund: dict, news: list[dict]) -> str:
    """Bloque fundamental rico + titulares recientes (catalizadores)."""
    lines = ["DATOS FUNDAMENTALES:"]
    if fund.get("sector") or fund.get("industry"):
        lines.append(f"Sector/industria: {_fmt(fund.get('sector'))} / {_fmt(fund.get('industry'))}")
    if fund.get("business_summary"):
        lines.append(f"Negocio: {fund['business_summary']}")
    lines.append(
        "Valoración: "
        f"cap. {_big(fund.get('marketCap'))}, EV {_big(fund.get('enterpriseValue'))}, "
        f"PER {_fmt(fund.get('trailingPE'))} (fwd {_fmt(fund.get('forwardPE'))}), "
        f"P/B {_fmt(fund.get('priceToBook'))}, P/S {_fmt(fund.get('priceToSalesTrailing12Months'))}, "
        f"PEG {_fmt(fund.get('pegRatio'))}, EV/EBITDA {_fmt(fund.get('enterpriseToEbitda'))}"
    )
    lines.append(
        "Rentabilidad: "
        f"margen neto {_pct(fund.get('profitMargins'))}, bruto {_pct(fund.get('grossMargins'))}, "
        f"operativo {_pct(fund.get('operatingMargins'))}, ROE {_pct(fund.get('returnOnEquity'))}, "
        f"ROA {_pct(fund.get('returnOnAssets'))}"
    )
    lines.append(
        "Crecimiento: "
        f"ingresos {_pct(fund.get('revenueGrowth'))}, beneficios {_pct(fund.get('earningsGrowth'))}, "
        f"BPA trim. {_pct(fund.get('earningsQuarterlyGrowth'))}. "
        f"Ingresos {_big(fund.get('totalRevenue'))}, EBITDA {_big(fund.get('ebitda'))}, "
        f"beneficio neto {_big(fund.get('netIncomeToCommon'))}"
    )
    lines.append(
        "Balance/caja: "
        f"caja {_big(fund.get('totalCash'))}, deuda {_big(fund.get('totalDebt'))}, "
        f"deuda/patrimonio {_fmt(fund.get('debtToEquity'))}, ratio corriente {_fmt(fund.get('currentRatio'))}, "
        f"FCF {_big(fund.get('freeCashflow'))}"
    )
    # yfinance da dividendYield ya en porcentaje (0.34 = 0.34%), no como fracción.
    dy = fund.get("dividendYield")
    dy_txt = f"{round(dy, 2)}%" if dy is not None else "n/d"
    lines.append(
        "BPA/dividendo: "
        f"BPA {_fmt(fund.get('trailingEps'))} (fwd {_fmt(fund.get('forwardEps'))}), "
        f"rent. div. {dy_txt}, payout {_pct(fund.get('payoutRatio'))}, "
        f"beta {_fmt(fund.get('beta'))}"
    )
    lines.append(
        "Analistas: "
        f"precio objetivo medio {_fmt(fund.get('targetMeanPrice'))} "
        f"(rango {_fmt(fund.get('targetLowPrice'))}–{_fmt(fund.get('targetHighPrice'))}), "
        f"recomendación {_fmt(fund.get('recommendationKey'))} "
        f"({_fmt(fund.get('numberOfAnalystOpinions'))} analistas)"
    )
    if fund.get("next_earnings"):
        lines.append(f"Próximos resultados: {fund['next_earnings']}")
    if news:
        lines.append("Titulares recientes (posibles catalizadores):")
        for n in news[:6]:
            pub = n.get("publisher") or ""
            lines.append(f"  - {n.get('title', '')}{f' ({pub})' if pub else ''}")
    return "\n".join(lines)


# --- Constructor de prompt por módulos (elegidos en el front) ---

TEMPLATES = {
    "es": (
        "Como experto en trading y bolsa, hazme un {analisis} para {ticker}"
        "{posicion}{temporalidad} con el objetivo de {objetivo}. {formato}"
    ),
    "en": (
        "As a trading and markets expert, give me a {analisis} for {ticker}"
        "{posicion}{temporalidad} with the goal of {objetivo}. {formato}"
    ),
}
# Compatibilidad: valor por defecto (español) para quien lo importe suelto.
INSTRUCTION_TEMPLATE = TEMPLATES["es"]

MODULE_ORDER = ["analisis", "posicion", "temporalidad", "objetivo", "formato"]

_MODULES: dict[str, dict] = {
    "es": {
        "analisis": {
            "label": "Análisis", "default": "tecnico",
            "options": [
                {"key": "tecnico", "label": "Técnico",
                 "text": "análisis técnico usando cualquier indicador que necesites (EMAs, volumen, RSI, soportes, resistencias u otros)"},
                {"key": "fundamental", "label": "Fundamental", "text": "análisis fundamental"},
                {"key": "ambos", "label": "Técnico + Fundamental",
                 "text": "análisis técnico usando cualquier indicador que necesites (EMAs, volumen, RSI, soportes, resistencias u otros) y análisis fundamental"},
            ],
        },
        "posicion": {
            "label": "Mi posición", "default": "no",
            "options": [
                {"key": "no", "label": "No", "text": ""},
                {"key": "si", "label": "Sí", "text": " teniendo en cuenta mi posición (volumen y media)"},
            ],
        },
        "temporalidad": {
            "label": "Temporalidad", "default": "cualquiera",
            "options": [
                {"key": "cualquiera", "label": "Cualquiera", "text": ""},
                {"key": "diario", "label": "Diario", "text": " en temporalidad diaria"},
                {"key": "1h", "label": "1 hora", "text": " en temporalidad de 1 hora"},
                {"key": "semanal", "label": "Semanal", "text": " en temporalidad semanal"},
            ],
        },
        "objetivo": {
            "label": "Objetivo", "default": "iniciar",
            "options": [
                {"key": "iniciar", "label": "Iniciar", "text": "iniciar una nueva posición"},
                {"key": "dca", "label": "DCA", "text": "hacer DCA"},
                {"key": "aumentar", "label": "Aumentar", "text": "aumentar posición"},
                {"key": "swing", "label": "Swing trade", "text": "hacer un swing trade"},
            ],
        },
        "formato": {
            "label": "Formato", "default": "extendido",
            "options": [
                {"key": "extendido", "label": "Extendido",
                 "text": "FORMATO: desarrolla el análisis completo, bien explicado y estructurado por secciones con encabezados."},
                {"key": "resumido", "label": "Resumido",
                 "text": "FORMATO OBLIGATORIO: responde SOLO con una lista de viñetas muy breves (máximo 6), sin introducción ni cierre ni saludos. Cada viñeta, una idea concreta y accionable en una sola línea. Nada de párrafos largos."},
            ],
        },
    },
    "en": {
        "analisis": {
            "label": "Analysis", "default": "tecnico",
            "options": [
                {"key": "tecnico", "label": "Technical",
                 "text": "technical analysis using any indicators you need (EMAs, volume, RSI, supports, resistances or others)"},
                {"key": "fundamental", "label": "Fundamental", "text": "fundamental analysis"},
                {"key": "ambos", "label": "Technical + Fundamental",
                 "text": "technical analysis using any indicators you need (EMAs, volume, RSI, supports, resistances or others) and fundamental analysis"},
            ],
        },
        "posicion": {
            "label": "My position", "default": "no",
            "options": [
                {"key": "no", "label": "No", "text": ""},
                {"key": "si", "label": "Yes", "text": " taking my position into account (volume and average)"},
            ],
        },
        "temporalidad": {
            "label": "Timeframe", "default": "cualquiera",
            "options": [
                {"key": "cualquiera", "label": "Any", "text": ""},
                {"key": "diario", "label": "Daily", "text": " on the daily timeframe"},
                {"key": "1h", "label": "1 hour", "text": " on the 1-hour timeframe"},
                {"key": "semanal", "label": "Weekly", "text": " on the weekly timeframe"},
            ],
        },
        "objetivo": {
            "label": "Goal", "default": "iniciar",
            "options": [
                {"key": "iniciar", "label": "Open", "text": "opening a new position"},
                {"key": "dca", "label": "DCA", "text": "dollar-cost averaging (DCA)"},
                {"key": "aumentar", "label": "Add", "text": "adding to my position"},
                {"key": "swing", "label": "Swing trade", "text": "a swing trade"},
            ],
        },
        "formato": {
            "label": "Format", "default": "extendido",
            "options": [
                {"key": "extendido", "label": "Extended",
                 "text": "FORMAT: develop the full analysis, well explained and structured in sections with headings."},
                {"key": "resumido", "label": "Summary",
                 "text": "MANDATORY FORMAT: reply ONLY with a very short bullet list (max 6), no intro, closing or greetings. Each bullet is one concrete, actionable idea on a single line. No long paragraphs."},
            ],
        },
    },
}

# Compatibilidad para importadores que esperan MODULES (español).
MODULES = _MODULES["es"]


def modules(lang: str = "es") -> dict:
    return _MODULES.get(lang, _MODULES["es"])


def _opt_text(module: str, key: str | None, lang: str) -> str:
    mod = modules(lang)[module]
    chosen = key or mod["default"]
    for o in mod["options"]:
        if o["key"] == chosen:
            return o["text"]
    for o in mod["options"]:  # fallback al default
        if o["key"] == mod["default"]:
            return o["text"]
    return ""


def build_instruction(sel: dict, ticker: str, lang: str = "es") -> str:
    """Frase-instrucción a partir de las opciones elegidas (misma que ve el front)."""
    return TEMPLATES.get(lang, TEMPLATES["es"]).format(
        analisis=_opt_text("analisis", sel.get("analisis"), lang),
        ticker=ticker,
        posicion=_opt_text("posicion", sel.get("posicion"), lang),
        temporalidad=_opt_text("temporalidad", sel.get("temporalidad"), lang),
        objetivo=_opt_text("objetivo", sel.get("objetivo"), lang),
        formato=_opt_text("formato", sel.get("formato"), lang),
    )


def wants_fundamental(sel: dict) -> bool:
    return sel.get("analisis") in ("fundamental", "ambos")


def wants_technical(sel: dict) -> bool:
    return sel.get("analisis", "tecnico") in ("tecnico", "ambos")


def wants_position(sel: dict) -> bool:
    return sel.get("posicion") == "si"
