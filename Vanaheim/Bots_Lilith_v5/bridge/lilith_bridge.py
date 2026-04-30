"""LilithBridge - Interfaz entre Bot Telegram y LilithEngine via Gateway REST."""
from typing import Any, Dict, List, Optional

import httpx

_GATEWAY_URL = "http://localhost:8000"


async def ask(
    message: str, history: Optional[List[Dict]] = None, user_id: str = "telegram"
) -> dict:
    """Procesa un mensaje via Gateway y retorna la respuesta del engine."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{_GATEWAY_URL}/api/telegram/chat",
            json={"text": message, "history": history, "user_id": user_id},
        )
        r.raise_for_status()
        return r.json()


async def ask_stream(
    message: str, history: Optional[List[Dict]] = None, user_id: str = "telegram"
):
    """Generador de chunks para streaming (placeholder - usa ask completo)."""
    result = await ask(message, history, user_id)
    yield result.get("reply", "")


def ask_sync(
    message: str, history: Optional[List[Dict]] = None, user_id: str = "telegram"
) -> dict:
    """Version sincrona del ask."""
    import httpx

    with httpx.Client(timeout=120.0) as client:
        r = client.post(
            f"{_GATEWAY_URL}/api/telegram/chat",
            json={"text": message, "history": history, "user_id": user_id},
        )
        r.raise_for_status()
        return r.json()
