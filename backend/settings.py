"""Configuración central del backend. Todo local y gratuito."""

import os
from pathlib import Path

# Carga variables desde backend/.env si existe (GEMINI_API_KEY, FINNHUB_API_KEY, etc.).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# --- Gemini (Google AI, nube) ---
# Clave gratuita en https://aistudio.google.com → backend/.env como GEMINI_API_KEY.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = os.getenv(
    "GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta"
)
# gemini-2.5-flash = el que mejor hace function calling (control del gráfico) en
# las pruebas; sus 404 transitorios los absorbe el reintento. Cambiable en el front.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Modelos que ofrece el desplegable del front (etiqueta ↔ id).
GEMINI_MODELS = [
    {"id": "gemini-2.5-flash", "label": "2.5 Flash (recomendado)"},
    {"id": "gemini-flash-latest", "label": "Flash latest"},
]
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "120"))

# --- Ollama (LLM local, respaldo gratis/offline cuando Gemini no puede) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.6:latest")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "180"))

# --- Radar de rupturas en directo ---
BREAKOUT_ENABLED = os.getenv("BREAKOUT_ENABLED", "1") == "1"
# Sondeo cuando NO hay tiempo real (solo Yahoo): más lento para no abusar.
BREAKOUT_INTERVAL = int(os.getenv("BREAKOUT_INTERVAL", "45"))
# Fuente de las VELAS de contexto (nivel, volumen medio, ATR). Yahoo sirve.
MARKETDATA_PROVIDER = os.getenv("MARKETDATA_PROVIDER", "yahoo")

# Tiempo real (Finnhub): si hay clave, el radar comprueba el PRECIO al instante.
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
# Cada cuántos segundos comprueba el precio en tiempo real (Finnhub).
REALTIME_INTERVAL = int(os.getenv("REALTIME_INTERVAL", "8"))
# Cada cuántos segundos refresca el contexto (velas de Yahoo: nivel/volumen).
CONTEXT_INTERVAL = int(os.getenv("CONTEXT_INTERVAL", "60"))

# --- Alertas al móvil por Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Notificaciones de Windows ---
# Activadas por defecto; se pueden desactivar en caliente desde la app.
NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "1") == "1"
# Cada cuántos segundos revisa el vigilante las alertas.
NOTIFY_INTERVAL = int(os.getenv("NOTIFY_INTERVAL", "120"))

# --- Servidor ---
# Orígenes permitidos para CORS (el frontend de Vite corre en 5173).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
