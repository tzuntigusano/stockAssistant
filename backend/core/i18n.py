"""Helper mínimo de traducción para los textos deterministas del backend.

La UI elige el idioma; los endpoints reciben `lang` ('es' | 'en') y los módulos
que generan texto (señales, checklist, radar, estrategia) lo pasan por aquí.
"""

from __future__ import annotations


def L(lang: str, es: str, en: str) -> str:
    """Devuelve la cadena en el idioma pedido ('en' → inglés; resto → español)."""
    return en if lang == "en" else es


def lang_directive(lang: str) -> str:
    """Frase para forzar el idioma de la respuesta de la IA (se añade al prompt)."""
    return "\n\nReply in English." if lang == "en" else "\n\nResponde en español de España."
