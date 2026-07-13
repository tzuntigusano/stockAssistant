"""Alertas al móvil vía bot de Telegram (opcional).

Se activa definiendo TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en backend/.env.
detect_chats() ayuda a obtener el chat_id: escribe algo al bot y llámalo.
"""

from __future__ import annotations

import httpx

from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_API = "https://api.telegram.org/bot{token}/{method}"


def is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def has_token() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


def send(title: str, message: str) -> bool:
    """Envía un mensaje al chat configurado. Nunca lanza excepción."""
    if not is_configured():
        return False
    try:
        r = httpx.post(
            _API.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage"),
            json={"chat_id": TELEGRAM_CHAT_ID, "text": f"{title}\n{message}"},
            timeout=10,
        )
        return r.status_code == 200 and r.json().get("ok", False)
    except Exception:
        return False


def detect_chats() -> list[dict]:
    """Lista los chats que han escrito al bot (para averiguar tu chat_id)."""
    if not TELEGRAM_BOT_TOKEN:
        return []
    try:
        r = httpx.get(
            _API.format(token=TELEGRAM_BOT_TOKEN, method="getUpdates"), timeout=10
        )
        r.raise_for_status()
        chats: dict[int, dict] = {}
        for u in r.json().get("result", []):
            msg = u.get("message") or u.get("edited_message") or {}
            chat = msg.get("chat")
            if chat and chat.get("id"):
                chats[chat["id"]] = {
                    "chat_id": chat["id"],
                    "name": chat.get("first_name") or chat.get("title") or "",
                    "username": chat.get("username", ""),
                }
        return list(chats.values())
    except Exception:
        return []
