"""Shalltear Bloodfallen - Agente de clasificación y triaje.

Backend: Venice AI (llama-3.3-70b)
Especialidad: Clasificación rápida, parsing NL, triaje de intents
"""
import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from Core.memory import get_muninn_client
from Core.models.agent import AgentCapabilities, AgentConfig
from Core.persona import get_persona_loader

from Agents.Base import VanirAgent


class ShalltearAgent(VanirAgent):
    """Shalltear - Clasificadora táctica del Panteón."""

    VENICE_API_URL = "https://api.venice.ai/api/v1/chat/completions"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._persona_loader = get_persona_loader()
        self._muninn = get_muninn_client()
        self._api_key = os.getenv("VENICE_API_KEY", "")

    @property
    def agent_id(self) -> str:
        return "shalltear"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=False,
            max_context_tokens=32768,
            specialties=["classification", "parsing", "triage", "intent_detection"],
            supported_tasks=[
                "clasificar_complejidad",
                "detectar_intent",
                "parsear_parametros",
                "triaje_tarea",
            ],
        )

    async def is_available(self) -> bool:
        """Verificar si Venice API está disponible."""
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.venice.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _get_system_prompt(self) -> str:
        """Obtener system prompt de Shalltear."""
        return self._persona_loader.get_system_prompt("shalltear")

    async def execute(self, task: str, context: dict[str, Any]) -> str:
        """Ejecutar tarea de clasificación."""
        self._set_busy(task)

        try:
            # Obtener memoria contextual
            memories = await self._muninn.get_memory(self.agent_id, task)
            memory_context = ""
            if memories:
                memory_context = "\n\nContexto relevante:\n" + "\n".join(
                    [m.get("content", "") for m in memories[:3]]
                )

            system_prompt = self._get_system_prompt()
            full_prompt = f"{task}{memory_context}"

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    self.VENICE_API_URL,
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
                        "max_tokens": 2048,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"]

                # Guardar memoria fire-and-forget
                self._muninn.write_memory_sync(
                    self.agent_id,
                    f"Tarea: {task}\nResultado: {result[:200]}...",
                    {"task_type": "classification"},
                )

                return result

        except Exception as e:
            self._set_error(str(e))
            raise
        finally:
            self._set_idle()

    async def stream(
        self, task: str, context: dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Streaming de respuesta (Shalltear rara vez necesita stream)."""
        # Para shalltear, devolvemos el resultado completo de una vez
        result = await self.execute(task, context)
        yield result
