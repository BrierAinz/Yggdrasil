from pathlib import Path
from typing import Optional

import httpx


async def notify_owner(base_path: Path, message: str, channel_id: Optional[str] = None):
    """Envía un mensaje al owner vía la API interna de Discord."""
    import os

    api_url = (os.getenv("LILITH_API_URL") or "http://127.0.0.1:8000").rstrip("/")
    token = (os.getenv("LILITH_INTERNAL_TOKEN") or "").strip()
    payload = {
        "text": message,
        "user_id": "webhook-system",
        "role": "owner",
        "channel": "dm",
        "channel_id": channel_id or "",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{api_url}/api/discord/chat",
            json=payload,
            headers={"X-Lilith-Token": token},
        )
