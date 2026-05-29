"""
Cliente para el modelo local sin censura usado con el público general.
Si el modelo responde con DELEGATE_TO_LILITH, la API delegará en Lilith (orquestador/herramientas).
Compatible con Ollama (y APIs tipo OpenAI /api/chat).
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("LocalPublicLLM")

_DELEGATE_MARKER = "DELEGATE_TO_LILITH"
_DEFAULT_CONFIG = {
    "enabled": False,
    "base_url": "http://localhost:11434",
    "model": "llama3.2",
    "delegate_marker": _DELEGATE_MARKER,
    "timeout_seconds": 60,
    "max_tokens": 1024,
}


def _config_path(base_path: Optional[Path] = None) -> Path:
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / "Config" / "local_public_llm.json"


def get_local_public_config(base_path: Optional[Path] = None) -> dict:
    """Carga Config/local_public_llm.json. Nunca falla."""
    try:
        from src.core.json_safe import safe_load

        path = _config_path(base_path)
        data = safe_load(path, default=_DEFAULT_CONFIG)
        return data if isinstance(data, dict) else _DEFAULT_CONFIG.copy()
    except Exception:
        return _DEFAULT_CONFIG.copy()


def is_local_public_enabled(base_path: Optional[Path] = None) -> bool:
    return bool(get_local_public_config(base_path).get("enabled"))


def generate(
    system_prompt: str,
    user_message: str,
    base_path: Optional[Path] = None,
) -> Tuple[str, bool]:
    """
    Llama al modelo local (Ollama). Devuelve (respuesta_texto, quiere_delegar).
    quiere_delegar=True si la respuesta contiene el delegate_marker (Lilith debe responder).
    """
    cfg = get_local_public_config(base_path)
    if not cfg.get("enabled"):
        return ("", True)
    base_url = (cfg.get("base_url") or "").rstrip("/")
    model = cfg.get("model") or "llama3.2"
    marker = (cfg.get("delegate_marker") or _DELEGATE_MARKER).strip()
    timeout = int(cfg.get("timeout_seconds") or 60)
    max_tokens = int(cfg.get("max_tokens") or 1024)
    if not base_url or not model:
        return ("", True)

    try:
        import httpx

        url = f"{base_url}/api/chat"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, json=body)
        if r.status_code != 200:
            logger.warning("Local public LLM %s status %s", url, r.status_code)
            return ("", True)
        data = r.json()
        msg = data.get("message") if isinstance(data, dict) else None
        content = (msg.get("content") or "").strip() if isinstance(msg, dict) else ""
        wants_delegate = marker in content
        if wants_delegate:
            content = content.replace(marker, "").strip()
        return (content, wants_delegate)
    except Exception as e:
        logger.warning("Local public LLM error: %s", e)
        return ("", True)


async def generate_async(
    system_prompt: str,
    user_message: str,
    base_path: Optional[Path] = None,
) -> Tuple[str, bool]:
    """Versión async (para no bloquear el event loop)."""
    return await asyncio.to_thread(generate, system_prompt, user_message, base_path)
