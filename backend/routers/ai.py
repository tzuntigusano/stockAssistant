"""Estrategia (prompt por módulos) y chat con IA (Gemini, con respaldo Ollama)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import gemini_llm, llm, lots, strategy, yahoo
from core.i18n import L, lang_directive
from routers import common
from settings import GEMINI_MODEL, GEMINI_MODELS, OLLAMA_MODEL

router = APIRouter(prefix="/api", tags=["ai"])

# Id especial: si el front elige este "modelo", se usa Ollama local en vez de Gemini.
OLLAMA_ID = "ollama"


def _is_ollama(model: str | None) -> bool:
    return (model or "") == OLLAMA_ID


class StrategyIn(BaseModel):
    selections: dict | None = None  # {analisis, posicion, temporalidad, objetivo, formato}
    model: str | None = None        # id de modelo (Gemini o 'ollama'); None = por defecto
    lang: str = "es"                # idioma de la respuesta de la IA


class ChatIn(BaseModel):
    question: str | None = None
    history: list[dict] | None = None  # [{role, content}, ...] terminando en user
    model: str | None = None
    chart_state: str | None = None     # estado actual del gráfico (para update_chart)
    force_chart: bool = False          # el front cree que es una orden de gráfico → mode ANY
    lang: str = "es"                   # idioma de la respuesta de la IA


@router.get("/llm/status")
def llm_status():
    return {
        "available": gemini_llm.is_available() or llm.is_available(),
        "model": GEMINI_MODEL,
    }


@router.get("/models/status")
def models_status():
    return {
        "gemini_available": gemini_llm.is_available(),
        "ollama_available": llm.is_available(),
        "model": GEMINI_MODEL,
        "models": GEMINI_MODELS + [{"id": OLLAMA_ID, "label": f"Ollama · {OLLAMA_MODEL} (local)"}],
    }


@router.get("/strategy/modules")
def strategy_modules(lang: str = "es"):
    """Definición de los módulos para construir el prompt en el front."""
    return {
        "order": strategy.MODULE_ORDER,
        "modules": strategy.modules(lang),
        "template": strategy.TEMPLATES.get(lang, strategy.TEMPLATES["es"]),
    }


MAX_PORTFOLIO_TICKERS = 15  # tope de seguridad: evita un prompt desmesurado


@router.post("/strategy-all/stream")
def build_portfolio_strategy_stream(body: StrategyIn):
    """Informe de TODA la cartera en UNA sola llamada a la IA.

    Recorre los valores con posición abierta, arma un bloque determinista por
    cada uno (técnico + mi posición) y pide un único informe con una sección
    por valor y una visión de conjunto. Una sola llamada mantiene a raya la
    cuota de Gemini (el free tier da 429 enseguida).
    """
    lang = body.lang or "es"
    blocks, tickers = [], []
    for t in lots.all_tickers():
        if len(tickers) >= MAX_PORTFOLIO_TICKERS:
            break
        try:
            q, ind, verdict, position, levels = common.strategy_data(t, lang)
        except Exception:
            continue  # un valor sin datos no debe tumbar el informe entero
        if not position.get("has_position"):
            continue  # solo donde he metido dinero
        tickers.append(t)
        blocks.append(
            f"===== {t} =====\n"
            + strategy.build_technical_context(t, q, ind, verdict, levels)
            + "\n"
            + strategy.build_position_context(position)
        )

    if not tickers:
        raise HTTPException(404, L(lang, "No tienes posiciones abiertas.", "You have no open positions."))

    instruction = L(
        lang,
        "Como experto en trading y bolsa, analiza MI CARTERA COMPLETA. Para CADA valor "
        "escribe una sección breve con: situación técnica, qué hacer con mi posición "
        "actual (mantener, ampliar, reducir o salir) y los niveles clave a vigilar. "
        "Termina con una VISIÓN DE CONJUNTO de la cartera: qué valores están mejor y "
        "peor, riesgos de concentración y por dónde empezar. Usa encabezados por valor.",
        "As a trading and markets expert, analyse MY WHOLE PORTFOLIO. For EACH holding "
        "write a short section with: technical situation, what to do with my current "
        "position (hold, add, trim or exit) and the key levels to watch. Finish with an "
        "OVERALL VIEW of the portfolio: which holdings look best and worst, concentration "
        "risks and where to start. Use a heading per holding.",
    )
    prompt = (
        f"{instruction}\n\n"
        + L(lang, "DATOS DE MI CARTERA (base para tu análisis, no inventes cifras):",
            "MY PORTFOLIO DATA (basis for your analysis, do not invent figures):")
        + "\n\n"
        + "\n\n".join(blocks)
        + lang_directive(lang)
    )

    meta = json.dumps({"portfolio": True, "tickers": tickers}, ensure_ascii=False)
    use_ollama = _is_ollama(body.model)
    provider = llm if use_ollama else gemini_llm

    def gen():
        yield meta + "\n\n"
        if use_ollama and not llm.is_available():
            yield "\n[Ollama no está disponible en localhost:11434]"
            return
        if not use_ollama and not gemini_llm.is_available():
            yield "\n[Falta GEMINI_API_KEY en backend/.env para generar el análisis con Gemini]"
            return
        try:
            yield from provider.narrate_stream(prompt, body.model, lang)
        except Exception as e:
            yield f"\n[No se pudo generar el análisis con IA: {e}]"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@router.post("/strategy/{ticker}/stream")
def build_strategy_stream(ticker: str, body: StrategyIn):
    """Streaming: primera línea = metadatos JSON + '\\n\\n', luego el texto."""
    t = ticker.upper()
    lang = body.lang or "es"
    q, ind, verdict, position, levels = common.strategy_data(ticker, lang)
    sel = body.selections or {}

    instruction = strategy.build_instruction(sel, t, lang)
    parts = []
    if strategy.wants_technical(sel):
        parts.append(strategy.build_technical_context(t, q, ind, verdict, levels))
    if strategy.wants_position(sel):
        parts.append(strategy.build_position_context(position))
    if strategy.wants_fundamental(sel):
        parts.append(strategy.build_fundamental_context(yahoo.get_fundamentals(ticker), yahoo.get_news(ticker)))
    data_block = "\n\n".join(parts)
    prompt = (
        f"{instruction}\n\nDATOS DISPONIBLES (base para tu análisis, no inventes cifras):\n"
        f"{data_block}"
        f"{lang_directive(lang)}"
    )

    meta = json.dumps(
        {"verdict": verdict, "levels": levels, "position": position, "instruction": instruction},
        ensure_ascii=False,
    )
    use_ollama = _is_ollama(body.model)

    def gen():
        yield meta + "\n\n"
        if use_ollama and not llm.is_available():
            yield "\n[Ollama no está disponible en localhost:11434]"
            return
        if not use_ollama and not gemini_llm.is_available():
            yield "\n[Falta GEMINI_API_KEY en backend/.env para generar el análisis con Gemini]"
            return
        provider = llm if use_ollama else gemini_llm
        try:
            yield from provider.narrate_stream(prompt, body.model, lang)
        except Exception as e:
            yield f"\n[No se pudo generar el análisis con IA: {e}]"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@router.post("/chat/{ticker}/stream")
def chat_stream(ticker: str, body: ChatIn):
    """Chat con IA. 1ª línea = meta JSON {chart: cfg|null} + '\\n\\n', luego el texto.

    Con Gemini el chat puede controlar el gráfico (function calling). Con Ollama
    solo responde texto (chart siempre null).
    """
    use_ollama = _is_ollama(body.model)
    if use_ollama and not llm.is_available():
        raise HTTPException(503, "Ollama no está disponible en localhost:11434")
    if not use_ollama and not gemini_llm.is_available():
        raise HTTPException(503, "Falta GEMINI_API_KEY en backend/.env")

    lang = body.lang or "es"
    _, context = common.chat_context(ticker, lang)
    history = body.history
    if not history:
        if not body.question:
            raise HTTPException(400, "Falta la pregunta")
        history = [{"role": "user", "content": body.question}]
    # Fuerza el idioma en el ÚLTIMO turno del usuario (lo más reciente que lee la IA).
    if history and history[-1].get("role") == "user":
        history = [*history[:-1], {**history[-1], "content": (history[-1].get("content") or "") + lang_directive(lang)}]
    chart_state = body.chart_state or "desconocido"

    def gen_ollama():
        # Si el gate cree que es una orden de gráfico, pedimos el JSON del comando.
        if body.force_chart:
            msg = history[-1].get("content", "") if history else ""
            cmd = llm.chart_command(msg, chart_state)
            if cmd:
                cfg = {k: cmd[k] for k in ("interval", "emas", "indicators") if k in cmd}
                reply = cmd.get("reply") or ("✅ Chart updated." if lang == "en" else "✅ Gráfico actualizado.")
                yield json.dumps({"chart": cfg}, ensure_ascii=False) + "\n\n"
                yield reply
                return
        # Chat normal (texto).
        yield json.dumps({"chart": None}, ensure_ascii=False) + "\n\n"
        try:
            yield from llm.converse_stream(context, history, None, lang)
        except Exception as e:
            yield f"\n[Error de IA: {e}]"

    def gen_gemini():
        meta_sent = False
        try:
            for kind, payload in gemini_llm.converse_stream_tools(
                context, chart_state, history, body.model, force=body.force_chart, lang=lang
            ):
                if kind == "call":
                    cfg = {k: payload[k] for k in ("interval", "emas", "indicators") if k in payload}
                    reply = payload.get("reply") or ("✅ Chart updated." if lang == "en" else "✅ Gráfico actualizado.")
                    yield json.dumps({"chart": cfg}, ensure_ascii=False) + "\n\n"
                    yield reply
                    return
                if not meta_sent:
                    yield json.dumps({"chart": None}, ensure_ascii=False) + "\n\n"
                    meta_sent = True
                yield payload
            if not meta_sent:
                yield json.dumps({"chart": None}, ensure_ascii=False) + "\n\n"
        except Exception as e:
            if not meta_sent:
                yield json.dumps({"chart": None}, ensure_ascii=False) + "\n\n"
            yield f"\n[Error de IA: {e}]"

    gen = gen_ollama if use_ollama else gen_gemini
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
