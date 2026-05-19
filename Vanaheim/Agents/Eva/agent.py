"""Eva - La Analista Meticulosa.

Backend: Grok/xAI (grok-4-fast-reasoning)
Especialidad: Análisis de contexto largo, documentación, insights
"""

import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from Core.memory import get_muninn_client
from Core.models.agent import AgentCapabilities, AgentConfig
from Core.persona import get_persona_loader

from Agents.Base import VanirAgent


class EvaAgent(VanirAgent):
    """Eva - Analista meticulosa del Panteón."""

    GROK_API_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._persona_loader = get_persona_loader()
        self._muninn = get_muninn_client()
        self._api_key = os.getenv("GROK_API_KEY", "")

    @property
    def agent_id(self) -> str:
        return "eva"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=False,
            max_context_tokens=128000,
            specialties=[
                "analysis",
                "documentation",
                "insights",
                "summarization",
                "research",
            ],
            supported_tasks=[
                "analizar_documento",
                "generar_documentacion",
                "sintetizar_informacion",
                "investigar",
                "resumir",
            ],
        )

    async def is_available(self) -> bool:
        """Verificar si Grok API está disponible."""
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.x.ai/v1/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _get_system_prompt(self) -> str:
        """Obtener system prompt de Eva."""
        return self._persona_loader.get_system_prompt("eva")

    async def execute(self, task: str, context: dict[str, Any]) -> str:
        """Ejecutar tarea de análisis."""
        self._set_busy(task)

        try:
            # Obtener memoria contextual
            memories = await self._muninn.get_memory(self.agent_id, task, limit=3)
            memory_context = ""
            if memories:
                memory_context = "\n\nContexto previo:\n" + "\n".join(
                    [m.get("content", "") for m in memories]
                )

            system_prompt = self._get_system_prompt()
            full_prompt = f"{task}{memory_context}"

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    self.GROK_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt},
                        ],
                        "temperature": self.config.temperature,
                        "max_tokens": 8192,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"]

                # Guardar memoria
                self._muninn.write_memory_sync(
                    self.agent_id,
                    f"Analysis: {task[:150]}...\nResult: {result[:300]}...",
                    {"task_type": "analysis"},
                )

                return result

        except Exception as e:
            self._set_error(str(e))
            raise
        finally:
            self._set_idle()

    async def stream(self, task: str, context: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streaming de análisis."""
        self._set_busy(task)

        try:
            memories = await self._muninn.get_memory(self.agent_id, task, limit=2)
            memory_context = ""
            if memories:
                memory_context = "\n\nContexto previo:\n" + "\n".join(
                    [m.get("content", "") for m in memories]
                )

            system_prompt = self._get_system_prompt()
            full_prompt = f"{task}{memory_context}"

            async with (
                httpx.AsyncClient(timeout=self.config.timeout) as client,
                client.stream(
                    "POST",
                    self.GROK_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt},
                        ],
                        "temperature": self.config.temperature,
                        "max_tokens": 8192,
                        "stream": True,
                    },
                ) as resp,
            ):
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            import json

                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError):
                                continue

        except Exception as e:
            yield f"[Error: {e!s}]"
        finally:
            self._set_idle()
