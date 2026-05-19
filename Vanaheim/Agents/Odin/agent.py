"""Odín - El Sabio Investigador.

Backend: Kimi 262k context (kimi-for-coding)
Especialidad: Análisis masivo, investigación profunda, creativo (absorbió a Lucifer)
"""

import os
from collections.abc import AsyncGenerator
from typing import Any, Literal

import httpx
from Core.memory import get_muninn_client
from Core.models.agent import AgentCapabilities, AgentConfig
from Core.persona import get_persona_loader

from Agents.Base import VanirAgent


class OdinAgent(VanirAgent):
    """Odín - Sabio investigador del Panteón (absorbió a Lucifer)."""

    KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._persona_loader = get_persona_loader()
        self._muninn = get_muninn_client()
        self._api_key = os.getenv("KIMI_API_KEY", "")
        self._intent = "analysis"  # default, creative, analysis

    @property
    def agent_id(self) -> str:
        return "odin"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=False,
            max_context_tokens=262000,
            specialties=[
                "deep_analysis",
                "research",
                "creative_writing",
                "synthesis",
                "architectural_review",
            ],
            supported_tasks=[
                "analizar_proyecto_completo",
                "investigar_profundo",
                "sintetizar_creativo",
                "revision_arquitectura",
                "storytelling",
            ],
        )

    async def is_available(self) -> bool:
        """Verificar si Kimi API está disponible."""
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.moonshot.cn/v1/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _get_system_prompt(
        self, intent: Literal["default", "creative", "analysis"] = "analysis"
    ) -> str:
        """Obtener system prompt según el modo de Odín."""
        base_prompt = self._persona_loader.get_system_prompt("odin")

        modifiers = {
            "creative": "\n\nModo: Creativo. Explora ideas audaces, genera contenido original, piensa fuera de lo convencional.",
            "analysis": "\n\nModo: Análisis profundo. Examina todos los aspectos, identifica patrones, proporciona insights detallados.",
            "default": "\n\nModo: Balanceado. Adapta el estilo según el contexto de la tarea.",
        }

        return base_prompt + modifiers.get(intent, modifiers["analysis"])

    def _detect_intent(self, task: str) -> Literal["default", "creative", "analysis"]:
        """Detectar el intent de la tarea."""
        task_lower = task.lower()

        creative_keywords = [
            "escribe",
            "crea",
            "genera",
            "story",
            "narrativa",
            "cuento",
            "creativo",
            "original",
            "imagina",
            "diseña",
            "inventa",
        ]
        analysis_keywords = [
            "analiza",
            "investiga",
            "examina",
            "review",
            "estudia",
            "evalúa",
            "compara",
            "sintetiza",
            "resume",
            "diagnóstico",
        ]

        creative_score = sum(1 for kw in creative_keywords if kw in task_lower)
        analysis_score = sum(1 for kw in analysis_keywords if kw in task_lower)

        if creative_score > analysis_score:
            return "creative"
        elif analysis_score > creative_score:
            return "analysis"
        return "default"

    async def execute(self, task: str, context: dict[str, Any]) -> str:
        """Ejecutar tarea de análisis profundo."""
        self._set_busy(task)

        try:
            # Detectar intent
            intent = context.get("intent", self._detect_intent(task))
            self._intent = intent

            # Obtener memoria extensa
            memories = await self._muninn.get_memory(self.agent_id, task, limit=10)
            memory_context = ""
            if memories:
                memory_context = "\n\nContexto previo relevante:\n" + "\n---\n".join(
                    [m.get("content", "") for m in memories[:5]]
                )

            system_prompt = self._get_system_prompt(intent)

            # Construir prompt con contexto masivo si existe
            large_context = context.get("large_context", "")
            full_prompt = task
            if large_context:
                full_prompt = f"Contexto:\n{large_context[:200000]}\n\n---\n\nTarea: {task}"
            if memory_context:
                full_prompt += memory_context

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    self.KIMI_API_URL,
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
                        "temperature": 0.8 if intent == "creative" else 0.3,
                        "max_tokens": 16384,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"]

                # Guardar memoria
                self._muninn.write_memory_sync(
                    self.agent_id,
                    f"Odín ({intent}): {task[:200]}...\nResult: {result[:400]}...",
                    {"intent": intent, "task_type": "deep_analysis"},
                )

                return result

        except Exception as e:
            self._set_error(str(e))
            raise
        finally:
            self._set_idle()

    async def stream(self, task: str, context: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streaming para análisis/creatividad."""
        self._set_busy(task)

        try:
            intent = context.get("intent", self._detect_intent(task))
            system_prompt = self._get_system_prompt(intent)

            large_context = context.get("large_context", "")
            full_prompt = task
            if large_context:
                full_prompt = f"Contexto:\n{large_context[:100000]}\n\n---\n\nTarea: {task}"

            async with (
                httpx.AsyncClient(timeout=self.config.timeout) as client,
                client.stream(
                    "POST",
                    self.KIMI_API_URL,
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
                        "temperature": 0.8 if intent == "creative" else 0.3,
                        "max_tokens": 16384,
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
