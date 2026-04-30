"""
Cliente HTTP para OpenRouter API

Usado por Crystal para acceder a modelos remotos con fallback a Ollama local.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Cliente para OpenRouter API con soporte de streaming y fallback"""

    def __init__(self, config_path: Optional[Path] = None):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"

        # Cargar config
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "model": "anthropic/claude-sonnet-4-20250514",
                "fallback_model": "grok-beta",
            }

        self.model = self.config.get("model", "anthropic/claude-sonnet-4-20250514")
        self.fallback_model = self.config.get("fallback_model", "grok-beta")

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set, OpenRouter calls will fail")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        use_fallback: bool = False,
    ) -> Dict[str, Any]:
        """
        Llamada a OpenRouter para chat completion

        Args:
            messages: Lista de mensajes [{role, content}]
            max_tokens: Máximo de tokens en respuesta
            temperature: Temperatura del modelo
            use_fallback: Usar modelo de fallback

        Returns:
            Response dict con content y metadata
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")

        model = self.fallback_model if use_fallback else self.model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lilith.local",
            "X-Title": "Lilith Crystal",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "success": True,
                    "content": data["choices"][0]["message"]["content"],
                    "model": model,
                    "usage": data.get("usage", {}),
                    "finish_reason": data["choices"][0].get("finish_reason"),
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                "model": model,
            }

        except Exception as e:
            logger.error(f"OpenRouter request failed: {e}")
            return {"success": False, "error": str(e), "model": model}

    async def chat_completion_with_fallback(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Llamada con cascada: modelo principal → fallback → error

        Returns:
            Response dict con success, content, y metadata
        """
        # Intentar modelo principal
        result = await self.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            use_fallback=False,
        )

        if result["success"]:
            return result

        logger.warning(f"Primary model failed: {result.get('error')}, trying fallback")

        # Intentar fallback
        result_fallback = await self.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            use_fallback=True,
        )

        if result_fallback["success"]:
            result_fallback["used_fallback"] = True
            return result_fallback

        # Ambos fallaron
        logger.error(f"Both OpenRouter models failed")
        return {
            "success": False,
            "error": f"Primary: {result.get('error')}; Fallback: {result_fallback.get('error')}",
            "used_fallback": True,
        }


# Singleton global
_openrouter_client: Optional[OpenRouterClient] = None


def get_openrouter_client(config_path: Optional[Path] = None) -> OpenRouterClient:
    """Obtener instancia singleton del cliente OpenRouter"""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient(config_path=config_path)
    return _openrouter_client
