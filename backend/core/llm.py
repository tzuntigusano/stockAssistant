"""Cliente del LLM local (Ollama). Respaldo cuando Gemini no está disponible.

Misma regla que Gemini: NO decide veredictos ni inventa cifras, solo redacta
sobre datos ya calculados. No hace function calling (no controla el gráfico).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

import httpx

from settings import OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_URL

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_SYSTEM_ES = (
    "Eres un analista financiero claro y directo. Responde SIEMPRE en español de "
    "España, sea cual sea el idioma de la pregunta. Te dan datos ya calculados "
    "(indicadores, fundamentales, la posición del usuario). Tu trabajo es "
    "EXPLICARLOS, no inventar cifras ni cambiar el veredicto que te dan. No des "
    "órdenes tajantes de compra/venta: describe el escenario y sus riesgos. "
    "IMPORTANTE: información, no asesoramiento regulado."
)
_SYSTEM_EN = (
    "You are a clear, direct financial analyst. ALWAYS reply in English, whatever "
    "the language of the question. You are given already-computed data "
    "(indicators, fundamentals, the user's position). Your job is to EXPLAIN them, "
    "not invent figures nor change the verdict given. Don't give blunt buy/sell "
    "orders: describe the scenario and its risks. IMPORTANT: information, not "
    "regulated advice."
)


def _system(lang: str) -> str:
    return _SYSTEM_EN if lang == "en" else _SYSTEM_ES


# Compatibilidad.
SYSTEM_PROMPT = _SYSTEM_ES


def is_available() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _tail_keep(s: str, tag: str) -> int:
    """Mayor sufijo de `s` que es prefijo de `tag` (para no cortar un <think> a
    caballo entre dos fragmentos del stream)."""
    for k in range(min(len(s), len(tag) - 1), 0, -1):
        if tag.startswith(s[-k:]):
            return k
    return 0


def _filter_think_stream(chunks: Iterator[str]) -> Iterator[str]:
    """Elimina en streaming lo que haya entre <think> y </think> (qwen)."""
    inside = False
    pending = ""
    for chunk in chunks:
        pending += chunk
        emit = ""
        while pending:
            if inside:
                j = pending.find("</think>")
                if j == -1:
                    keep = _tail_keep(pending, "</think>")
                    pending = pending[len(pending) - keep:] if keep else ""
                    break
                pending = pending[j + 8:]
                inside = False
            else:
                k = pending.find("<think>")
                if k == -1:
                    keep = _tail_keep(pending, "<think>")
                    if keep:
                        emit += pending[: len(pending) - keep]
                        pending = pending[len(pending) - keep:]
                    else:
                        emit += pending
                        pending = ""
                    break
                emit += pending[:k]
                pending = pending[k + 7:]
                inside = True
        if emit:
            yield emit
    if not inside and pending:
        yield pending


def _stream(messages: list[dict], temperature: float = 0.4) -> Iterator[str]:
    """Generador de fragmentos de texto desde Ollama (streaming)."""

    def raw() -> Iterator[str]:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "think": False,  # ignorado si el modelo no es 'thinking'
            "options": {"temperature": temperature},
        }
        with httpx.stream(
            "POST", f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = data.get("message", {}).get("content", "")
                if piece:
                    yield piece

    yield from _filter_think_stream(raw())


def narrate_stream(user_text: str, model: str | None = None, lang: str = "es") -> Iterator[str]:
    """Redacta el análisis a partir del prompt ya construido (instrucción + datos)."""
    yield from _stream(
        [
            {"role": "system", "content": _system(lang)},
            {"role": "user", "content": user_text},
        ]
    )


_CMD_SYSTEM = (
    "Eres un controlador de un gráfico de trading. Respondes SOLO con un objeto "
    "JSON válido, sin texto ni explicaciones fuera del JSON."
)


def _extract_json(text: str) -> dict:
    text = _THINK_RE.sub("", text).strip()
    i, j = text.find("{"), text.rfind("}")
    return json.loads(text[i : j + 1] if i >= 0 and j > i else text)


def chart_command(message: str, chart_state: str) -> dict | None:
    """Pide a Ollama (JSON forzado) el estado completo deseado del gráfico.

    Devuelve {interval?, emas?, indicators?, reply} o None si no se pudo parsear.
    Equivale al function calling de Gemini pero con `format:"json"`.
    """
    user = (
        f'Estado actual del gráfico: {chart_state}\n'
        f'Orden del usuario: "{message}"\n\n'
        "Devuelve un JSON con el estado COMPLETO deseado tras la orden. Incluye SOLO "
        "las claves que cambian:\n"
        '- "interval": una de "5m","15m","60m","4h","1d","1wk" (para "1h" usa "60m"; '
        'diario "1d"; semanal "1wk"; para "en 4h" usa "4h")\n'
        '- "emas": lista COMPLETA de EMAs, cada una {"length": entero, "tf": ""} '
        '(tf "" salvo que pida una temporalidad MAYOR: "1h","4h","1d","1wk"). [] = ninguna\n'
        '- "indicators": lista COMPLETA de "volume","bollinger","rsi","levels". [] = ninguno\n'
        '- "reply": confirmación breve en español\n\n'
        'REGLA EMAs: "muéstrame/enséñame/pon la EMA X" = SOLO esa EMA (emas=[{"length":X,"tf":""}]); '
        '"añade la EMA X" = las EMAs actuales + X; "quita la EMA X" = las actuales sin X. '
        "Mismo criterio para los indicadores.\n"
        'Ejemplo "muéstrame la EMA 50" (con EMAs actuales 9,20,50): '
        '{"emas":[{"length":50,"tf":""}],"reply":"Mostrando solo la EMA 50."}\n'
        'Ejemplo "muéstrame solo la EMA 200 en 4h": '
        '{"interval":"4h","emas":[{"length":200,"tf":""}],"indicators":[],"reply":"Listo: 4h con la EMA 200."}'
    )
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _CMD_SYSTEM},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        content = r.json().get("message", {}).get("content", "")
        return _extract_json(content)
    except Exception:
        return None


def converse_stream(context: str, history: list[dict], model: str | None = None, lang: str = "es") -> Iterator[str]:
    """Chat con memoria, anclando el contexto para no inventar cifras."""
    messages = [
        {"role": "system", "content": _system(lang)},
        {
            "role": "user",
            "content": "Datos actuales del valor (úsalos como base, no inventes cifras):\n" + context,
        },
        {"role": "assistant", "content": "De acuerdo, tengo los datos del valor delante."},
    ]
    for m in history:
        role = "assistant" if m.get("role") == "assistant" else "user"
        content = (m.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    yield from _stream(messages, temperature=0.5)
