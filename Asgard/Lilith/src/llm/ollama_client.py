import json
import logging
import sys
from typing import Callable, Optional

import requests

logger = logging.getLogger("OllamaClient")


class OllamaClient:
    def __init__(self, host="localhost", port=11434):
        self.base_url = f"http://{host}:{port}"

    def check_health(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def stream_chat(
        self,
        model: str,
        prompt: str,
        on_chunk: Callable[[str], None],
        system: Optional[str] = None,
    ):
        """
        Generates chat response and calls on_chunk(chunk) for each part.
        """
        if not self.check_health():
            on_chunk(
                "âŒ Error: Ollama no estÃ¡ accesible. AsegÃºrate de que estÃ¡ corriendo."
            )
            return

        url = f"{self.base_url}/api/generate"
        payload = {"model": model, "prompt": prompt, "stream": True}
        if system:
            payload["system"] = system

        try:
            logger.info(f"Sending request to Ollama (model={model})")
            response = requests.post(url, json=payload, stream=True, timeout=120)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if not chunk.get("done"):
                            text = chunk.get("response", "")
                            if text:
                                on_chunk(text)
                    except json.JSONDecodeError:
                        pass

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            on_chunk(f"âŒ Error comunicÃ¡ndose con Ollama: {e}")

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = "qwen2.5-coder:7b",
        **kwargs,
    ) -> str:
        """
        Non-streaming generation via Ollama /api/generate.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "system": system_prompt,
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("response", "")
            return ""
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return ""
