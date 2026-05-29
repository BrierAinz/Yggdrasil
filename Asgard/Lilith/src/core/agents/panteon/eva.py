"""
EVA - Agente Analista (Grok)
Especialidad: Análisis de múltiples archivos, documentación, resúmenes largos.
Trigger: contexto > 50k tokens, análisis de proyectos completos, lectura de docs.

Implementación: Usa API Grok (xAI) con protocolo OpenAI
Model: grok-4-fast-reasoning
"""
import json
import os
from typing import Any, Dict, Generator, List

import requests

from .base_agent import BaseAgent


class EvaAgent(BaseAgent):
    """
    Eva - Analista meticulosa bajo las órdenes de Lilith.
    Especialista en contexto largo, análisis y documentación.
    Usa Grok (xAI) para análisis profundos.
    """

    name = "Eva"
    description = (
        "Analista meticulosa. Especialista en contexto largo, análisis y documentación."
    )

    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-4-fast-reasoning"

    def is_available(self) -> bool:
        """Verifica si la API key de Grok está configurada"""
        return self.api_key is not None and len(self.api_key) > 0

    def get_system_prompt(self) -> str:
        try:
            from pathlib import Path

            from src.core.persona.loader import get_persona_loader

            base_path = Path(__file__).resolve().parent.parent.parent.parent
            loader = get_persona_loader(base_path)
            return loader.get_system_prompt("eva", include_common=True)
        except Exception:
            return "[Eva — Analista] Agente analista meticuloso y estructurado. Fallback..."

    def execute(self, task: str, context: str = "") -> str:
        """
        Ejecuta una tarea de análisis usando API Grok (xAI).

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional (código, documentos, etc.)

        Returns:
            Resultado del análisis
        """
        if not self.is_available():
            return "[Eva offline] GROK_API_KEY no configurada. Fallback a Lilith."

        # Mejora-1: leer memoria previa del vault de Eva (sync via thread)
        memory_block = ""
        try:
            import asyncio as _asyncio
            import concurrent.futures as _cf
            from pathlib import Path as _Path

            from src.core.memory.muninn_memory import MuninnMemory as _MM

            _bp = _Path(__file__).resolve().parent.parent.parent.parent
            with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                memory_block = _ex.submit(
                    _asyncio.run, _MM(_bp).get_agent_memory("eva", task)
                ).result(timeout=2)
        except Exception:
            pass

        # Construir el contenido del mensaje
        if context:
            user_content = f"""CONTEXTO:
{context}

TAREA:
{task}"""
        else:
            user_content = task

        # Headers en formato OpenAI (Grok es compatible)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        system_prompt = self.get_system_prompt()
        if memory_block:
            system_prompt = system_prompt + "\n\n" + memory_block

        # Body en formato OpenAI Chat Completions
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:
                data = response.json()
                # Extraer contenido de la respuesta OpenAI
                if "choices" in data and len(data["choices"]) > 0:
                    result_text = data["choices"][0]["message"].get("content", "")
                    # Mejora-1: escribir resultado en vault de Eva (fire-and-forget)
                    try:
                        from pathlib import Path as _Path

                        from src.core.memory.muninn_memory import MuninnMemory as _MM
                        from src.core.memory.muninn_memory import (
                            _run_coro_fire_and_forget,
                        )

                        _bp = _Path(__file__).resolve().parent.parent.parent.parent
                        _run_coro_fire_and_forget(
                            _MM(_bp).write_agent_output("eva", task, result_text)
                        )
                    except Exception:
                        pass
                    return result_text
                return "[Eva error] Respuesta vacía de la API"
            else:
                error_text = response.text
                return f"[Eva error] HTTP {response.status_code}: {error_text}. Fallback a Lilith."

        except requests.Timeout:
            return "[Eva timeout] La API tardó demasiado. Fallback a Lilith."
        except requests.ConnectionError:
            return "[Eva error] No se pudo conectar a la API. Fallback a Lilith."
        except Exception as e:
            return f"[Eva error] {str(e)}. Fallback a Lilith."

    def stream_execute(
        self, task: str, context: str = ""
    ) -> Generator[str, None, None]:
        """
        Ejecuta una tarea con streaming de respuesta.

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional

        Yields:
            Chunks de la respuesta
        """
        if not self.is_available():
            yield "[Eva offline] GROK_API_KEY no configurada. Fallback a Lilith."
            return

        # Construir el contenido del mensaje
        if context:
            user_content = f"""CONTEXTO:
{context}

TAREA:
{task}"""
        else:
            user_content = task

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": user_content},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120,
            )

            if response.status_code != 200:
                error_msg = f"[Eva error] HTTP {response.status_code}: {response.text}"
                yield error_msg
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
                            if "choices" in data:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            yield f"[Eva error] {str(e)}. Fallback a Lilith."
