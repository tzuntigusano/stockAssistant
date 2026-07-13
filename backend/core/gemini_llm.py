"""Cliente de Gemini (Google AI, nube). Redacta análisis en lenguaje natural.

Regla de oro (igual que antes): el LLM NO decide el veredicto ni inventa cifras.
Se le pasan datos ya calculados y solo los explica. Streaming vía SSE.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

import httpx

from settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT, GEMINI_URL

# Gemini da 404 "no longer available"/500/503 transitorios de vez en cuando;
# reintentamos ANTES de emitir (no se ha cedido nada aún). El 429 (cuota) NO se
# reintenta: no se arregla insistiendo y solo gasta más cuota.
_RETRY_CODES = {404, 500, 503}
_RETRIES = 3

_SYSTEM_ES = (
    "Eres un analista financiero experto, claro y directo. Responde SIEMPRE en "
    "español de España, sea cual sea el idioma de la pregunta. Te dan datos ya "
    "calculados (indicadores técnicos, fundamentales y la posición del usuario). "
    "Explícalos y razona sobre ellos, pero NO inventes cifras que no te hayan dado "
    "ni cambies los veredictos deterministas. Si te faltan datos, dilo con "
    "franqueza. No des órdenes tajantes de compra/venta: describe escenarios, "
    "niveles y riesgos. IMPORTANTE: esto es información, no asesoramiento financiero regulado."
)
_SYSTEM_EN = (
    "You are an expert financial analyst, clear and direct. ALWAYS reply in "
    "English, whatever the language of the question. You are given already-computed "
    "data (technical and fundamental indicators and the user's position). Explain "
    "and reason about them, but do NOT invent figures you weren't given nor change "
    "the deterministic verdicts. If data is missing, say so honestly. Don't give "
    "blunt buy/sell orders: describe scenarios, levels and risks. IMPORTANT: this "
    "is information, not regulated financial advice."
)


def _system(lang: str) -> str:
    return _SYSTEM_EN if lang == "en" else _SYSTEM_ES


# Compatibilidad para quien lo importe suelto.
SYSTEM_PROMPT = _SYSTEM_ES


def is_available() -> bool:
    return bool(GEMINI_API_KEY)


def _sse_lines(model: str | None, payload: dict):
    """Abre el stream SSE reintentando errores transitorios y cede las líneas.

    Solo reintenta ANTES de recibir un 200 (aún no se emitió nada), así que es
    seguro: nunca duplica texto ya enviado.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("Falta GEMINI_API_KEY en backend/.env")
    mdl = model or GEMINI_MODEL
    url = f"{GEMINI_URL}/models/{mdl}:streamGenerateContent"
    last_err = None
    for attempt in range(_RETRIES):
        cm = httpx.stream(
            "POST", url, params={"alt": "sse", "key": GEMINI_API_KEY},
            json=payload, timeout=GEMINI_TIMEOUT,
        )
        r = cm.__enter__()
        if r.status_code == 200:
            try:
                yield from r.iter_lines()
            finally:
                cm.__exit__(None, None, None)
            return
        detail = r.read().decode("utf-8", "ignore")[:200]
        cm.__exit__(None, None, None)
        last_err = f"Gemini {r.status_code}: {detail}"
        if r.status_code in _RETRY_CODES and attempt < _RETRIES - 1:
            time.sleep(0.7 * (attempt + 1))
            continue
        break
    raise RuntimeError(last_err or "Gemini no respondió")


def _parts(model: str | None, payload: dict):
    """Cede los `parts` de cada evento SSE (texto o functionCall)."""
    for line in _sse_lines(model, payload):
        if not line or not line.startswith("data:"):
            continue
        body = line[5:].strip()
        if body == "[DONE]":
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        for cand in data.get("candidates", []):
            yield from cand.get("content", {}).get("parts", [])


def _stream(contents: list[dict], model: str | None, temperature: float = 0.5, lang: str = "es") -> Iterator[str]:
    """Llama a Gemini con streaming SSE y va soltando el texto por trozos."""
    payload = {
        "system_instruction": {"parts": [{"text": _system(lang)}]},
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    for part in _parts(model, payload):
        if part.get("text"):
            yield part["text"]


# Herramienta que permite a la IA controlar el gráfico desde el chat.
CHART_TOOL = {
    "function_declarations": [
        {
            "name": "update_chart",
            "description": (
                "Actualiza el gráfico de velas que ve el usuario (indicadores y temporalidad). "
                "Úsala cuando pida mostrar, ocultar, quitar o dejar 'solo' EMAs, volumen, RSI, "
                "Bollinger, soportes/resistencias, o cambiar el intervalo/temporalidad. Devuelve "
                "SIEMPRE el estado COMPLETO deseado tras el cambio, partiendo del estado actual "
                "que se te da. REGLA EMAs: 'muéstrame/enséñame/pon la EMA X' → muestra SOLO esa "
                "(emas=[{length:X}]); 'añade la EMA X' → las EMAs actuales + X; 'quita la EMA X' "
                "→ las actuales sin X. Mismo criterio para los indicadores. Si en cambio es una "
                "pregunta de análisis, responde con texto normal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "interval": {
                        "type": "string",
                        "enum": ["5m", "15m", "60m", "4h", "1d", "1wk"],
                        "description": "Temporalidad de las velas. '1h'→'60m', diario→'1d', "
                                       "semanal→'1wk'. Para ver algo 'en 4h', pon 4h aquí.",
                    },
                    "emas": {
                        "type": "array",
                        "description": "Lista COMPLETA de EMAs tras el cambio (vacía = ninguna).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "length": {"type": "integer"},
                                "tf": {
                                    "type": "string",
                                    "description": "Timeframe MAYOR para EMA multi-timeframe "
                                                   "(1h,4h,1d,1wk). Vacío = la del gráfico.",
                                },
                            },
                            "required": ["length"],
                        },
                    },
                    "indicators": {
                        "type": "array",
                        "description": "Lista COMPLETA de indicadores no-EMA tras el cambio "
                                       "(vacía = ninguno).",
                        "items": {"type": "string", "enum": ["volume", "bollinger", "rsi", "levels"]},
                    },
                    "reply": {
                        "type": "string",
                        "description": "Confirmación breve en español de lo que has cambiado.",
                    },
                },
            },
        }
    ]
}


def _stream_tools(contents: list[dict], model: str | None, temperature: float = 0.4, force: bool = False, lang: str = "es"):
    """Como _stream pero con la herramienta update_chart. Cede tuplas:
    ('call', args_dict) si la IA llama a la función, o ('text', trozo) si redacta.

    `force=True` → mode ANY: obliga a llamar update_chart (para órdenes claras
    de gráfico). Si no, AUTO: la IA decide entre actuar o responder texto."""
    payload = {
        "system_instruction": {"parts": [{"text": _system(lang)}]},
        "contents": contents,
        "tools": [CHART_TOOL],
        "tool_config": {"function_calling_config": {"mode": "ANY" if force else "AUTO"}},
        "generationConfig": {"temperature": temperature},
    }
    for part in _parts(model, payload):
        if "functionCall" in part:
            yield ("call", part["functionCall"].get("args", {}) or {})
        elif part.get("text"):
            yield ("text", part["text"])


def converse_stream_tools(context: str, chart_state: str, history: list[dict], model: str | None = None, force: bool = False, lang: str = "es"):
    """Chat que además puede controlar el gráfico. Cede tuplas ('call'|'text', …)."""
    contents = [
        {
            "role": "user",
            "parts": [{"text": (
                "Datos del valor (úsalos como base, no inventes cifras):\n" + context +
                "\n\nESTADO ACTUAL DEL GRÁFICO (para calcular el estado completo en update_chart):\n"
                + chart_state
            )}],
        },
        {"role": "model", "parts": [{"text": "Entendido, tengo los datos y el estado del gráfico."}]},
    ]
    for m in history:
        role = "model" if m.get("role") == "assistant" else "user"
        content = (m.get("content") or "").strip()
        if content:
            contents.append({"role": role, "parts": [{"text": content}]})
    yield from _stream_tools(contents, model, 0.4, force=force, lang=lang)


def narrate_stream(user_text: str, model: str | None = None, lang: str = "es") -> Iterator[str]:
    """Redacta el análisis a partir del prompt ya construido (instrucción + datos)."""
    yield from _stream([{"role": "user", "parts": [{"text": user_text}]}], model, 0.5, lang)


def converse_stream(context: str, history: list[dict], model: str | None = None, lang: str = "es") -> Iterator[str]:
    """Chat con memoria. Ancla el contexto técnico para no inventar cifras.

    Gemini usa roles 'user' y 'model' (no 'assistant').
    """
    contents = [
        {
            "role": "user",
            "parts": [{"text": "Datos actuales del valor (úsalos como base, no inventes cifras):\n" + context}],
        },
        {"role": "model", "parts": [{"text": "De acuerdo, tengo los datos del valor delante."}]},
    ]
    for m in history:
        role = "model" if m.get("role") == "assistant" else "user"
        content = (m.get("content") or "").strip()
        if content:
            contents.append({"role": role, "parts": [{"text": content}]})
    yield from _stream(contents, model, 0.6, lang)
