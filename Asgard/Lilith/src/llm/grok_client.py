import json
import logging
import os
from typing import Any, Dict, Generator, List, Optional

import requests

logger = logging.getLogger("GrokClient")


class GrokClient:
    """
    Client for xAI Grok via REST API (OpenAI-compatible).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROK_API_KEY")
        self.base_url = "https://api.x.ai/v1"
        self.default_model = "grok-4-fast-reasoning"

    def check_health(self) -> bool:
        if not self.api_key:
            return False
        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # Basic check if grok is in list
                return True
            return False
        except Exception:
            return False

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        model: str = None,
    ) -> Generator[str, None, None]:
        if not self.api_key:
            yield "ðŸš« Error: GROK_API_KEY not found in secrets.env"
            return

        model = model or self.default_model

        # Grok uses standard OpenAI format
        msgs_payload = []
        if system_prompt:
            msgs_payload.append({"role": "system", "content": system_prompt})
        msgs_payload.extend(messages)

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": msgs_payload,
            "stream": True,
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)

            if response.status_code != 200:
                error_msg = f"Grok Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                yield f"ðŸš¨ {error_msg}"
                return

            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        if decoded == "data: [DONE]":
                            break

                        json_str = decoded[6:]
                        try:
                            data = json.loads(json_str)
                            # choices[0].delta.content
                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"âš ï¸ Network Error: {e}"

    def generate_text(
        self, prompt: str, system_prompt: str = None, model: str = None, **kwargs
    ) -> str:
        """
        Non-streaming generation via standard Chat API.
        """
        model = model or self.default_model
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": msgs,
            "stream": False,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"].get("content", "")
            return ""
        except Exception as e:
            logger.error(f"Grok generate error: {e}")
            return ""
