"""
Lilith — Notificador proactivo de Telegram.
Envía mensajes a Ainz sin que él pregunte (activaciones Muninn, alertas, etc.).
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("lilith.telegram_notifier")


def _bot_token() -> str:
    return (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def _owner_chat_id() -> str:
    return (os.getenv("TELEGRAM_OWNER_CHAT_ID") or "").strip()


async def notify_owner_telegram(
    message: str, urgent: bool = False, parse_mode: str = "Markdown"
) -> bool:
    """
    Envía una notificación proactiva a Ainz por Telegram.
    Retorna True si se envió, False si falló o no está configurado.
    """
    token = _bot_token()
    chat_id = _owner_chat_id()
    if not token or not chat_id:
        logger.debug(
            "[TelegramNotifier] TELEGRAM_BOT_TOKEN o TELEGRAM_OWNER_CHAT_ID no configurados."
        )
        return False

    prefix = "🔴 " if urgent else "🔔 "
    text = f"{prefix}{message}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            if resp.status_code == 200:
                logger.debug("[TelegramNotifier] Notificación enviada.")
                return True
            logger.warning(
                "[TelegramNotifier] HTTP %s: %s", resp.status_code, resp.text[:200]
            )
    except Exception as e:
        logger.warning("[TelegramNotifier] Error: %s", e)
    return False


def notify_owner_telegram_sync(message: str, urgent: bool = False) -> bool:
    """Versión síncrona de notify_owner_telegram. Para uso desde threads/contextos sync."""
    import requests as _req

    token = _bot_token()
    chat_id = _owner_chat_id()
    if not token or not chat_id:
        return False
    prefix = "🔴 " if urgent else "🔔 "
    text = f"{prefix}{message}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = _req.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False
