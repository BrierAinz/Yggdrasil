"""
LM Studio Client
================
Cliente para conectar con LM Studio API (OpenAI-like).
Soporta deteccion automatica de modelo con DEFAULT_MODEL = "auto".
Soporta streaming SSE.
"""
import json
from typing import Any, Dict, Iterator, List, Optional

import httpx

from .config import DEFAULT_MODEL, LM_STUDIO_URL


class LMStudioClient:
    """Cliente para LM Studio API."""

    def __init__(self, base_url: str = LM_STUDIO_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=120.0)

        if self.model == "auto":
            models = self.list_models()
            if models:
                self.model = models[0].get("id", "unknown")
            else:
                self.model = "local-model"

    def list_models(self) -> List[Dict]:
        """Lista modelos disponibles."""
        try:
            response = self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Error listando modelos: {e}")
            return []

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Envia mensaje al modelo y recibe respuesta completa."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error HTTP: {e.response.status_code}")
            print(f"   Response: {e.response.text[:500]}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Error: {e}")
            return {"error": str(e)}

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """Streaming generator: yield chunks de texto."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.strip():
                        continue
                    line = line.strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as e:
            yield f"\n[Error streaming: {e}]\n"

    def close(self):
        """Cierra el cliente."""
        self.client.close()


def test_connection() -> bool:
    """Verifica conexion con LM Studio."""
    try:
        client = LMStudioClient()
        models = client.list_models()
        client.close()
        if models:
            print("Conexion exitosa a LM Studio")
            print(f"   Modelos disponibles: {len(models)}")
            for m in models[:5]:
                print(f"   - {m.get('id', 'unknown')}")
            return True
        else:
            print("LM Studio responde pero no hay modelos cargados")
            return False
    except ConnectionError:
        print("No se puede conectar a LM Studio")
        print("   Asegurate que el servidor este corriendo en puerto 1234")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("Probando conexion a LM Studio...")
    test_connection()
