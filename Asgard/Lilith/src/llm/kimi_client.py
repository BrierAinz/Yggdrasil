"""
Kimi Client - Anthropic Messages API Protocol
API: https://api.kimi.com/coding/v1
Model: kimi-for-coding (262k context)
"""
import json
import logging
import os
from typing import Any, Dict, Generator, List, Optional

import requests

logger = logging.getLogger("KimiClient")


class KimiClient:
    """
    Client for Kimi API using Anthropic Messages API protocol.
    Context: 262k tokens
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("KIMI_API_KEY")
        self.base_url = "https://api.kimi.com/coding"
        self.default_model = "kimi-for-coding"

    def check_health(self) -> bool:
        """Check if Kimi API is available"""
        if not self.api_key:
            return False
        url = f"{self.base_url}/v1/models"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        model: str = None,
    ) -> Generator[str, None, None]:
        """
        Stream chat completion using Anthropic Messages API format.
        Note: Kimi returns complete response, not true streaming.
        We simulate streaming by yielding words.
        """
        if not self.api_key:
            yield "🚫 Error: KIMI_API_KEY not found in secrets.env"
            return

        model = model or self.default_model

        # Convert OpenAI format messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            anthropic_messages.append({"role": role, "content": msg["content"]})

        url = f"{self.base_url}/v1/messages"
        payload = {"model": model, "max_tokens": 8096, "messages": anthropic_messages}

        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            logger.info(f"Kimi request to {url} with model {model}")
            response = requests.post(url, headers=headers, json=payload, timeout=120)

            if response.status_code != 200:
                error_msg = f"Kimi Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                yield f"🚨 {error_msg}"
                return

            # Parse the complete response
            data = response.json()
            logger.debug(f"Kimi response: {json.dumps(data, indent=2)[:500]}...")

            # Extract content from Anthropic format
            full_text = ""
            if "content" in data and isinstance(data["content"], list):
                for block in data["content"]:
                    if block.get("type") == "text":
                        full_text += block.get("text", "")
            elif "content" in data and isinstance(data["content"], str):
                full_text = data["content"]

            if not full_text:
                logger.warning("Kimi returned empty content")
                yield ""
                return

            # Simulate streaming by yielding words
            words = full_text.split(" ")
            for i, word in enumerate(words):
                if i < len(words) - 1:
                    yield word + " "
                else:
                    yield word

        except requests.Timeout:
            logger.error("Kimi request timed out")
            yield "⚠️ Error: Timeout esperando respuesta de Kimi"
        except Exception as e:
            logger.error(f"Kimi stream error: {e}", exc_info=True)
            yield f"⚠️ Error: {e}"

    def generate_text(
        self, prompt: str, system_prompt: str = None, model: str = None, **kwargs
    ) -> str:
        """Non-streaming generation."""
        model = model or self.default_model

        url = f"{self.base_url}/v1/messages"
        payload = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        try:
            # Kimi puede tardar; permitir hasta 5 minutos para evitar respuestas vacías por timeout.
            resp = requests.post(url, headers=headers, json=payload, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                # Extract content from Anthropic format
                if "content" in data and isinstance(data["content"], list):
                    return "".join(
                        block.get("text", "")
                        for block in data["content"]
                        if block.get("type") == "text"
                    )
                elif "content" in data and isinstance(data["content"], str):
                    return data["content"]
                return ""
            logger.error(f"Kimi error {resp.status_code}: {resp.text}")
            return ""
        except Exception as e:
            logger.error(f"Kimi generate error: {e}")
            return ""
