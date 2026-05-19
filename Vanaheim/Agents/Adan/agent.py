"""Adán - El Artesano del Código.

Backend: Ollama local (qwen2.5-coder:7b)
Especialidad: Generación de código, tests, refactoring
"""
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from Core.memory import get_muninn_client
from Core.models.agent import AgentCapabilities, AgentConfig
from Core.persona import get_persona_loader

from Agents.Base import VanirAgent


class AdanAgent(VanirAgent):
    """Adán - Artesano del código del Panteón."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._persona_loader = get_persona_loader()
        self._muninn = get_muninn_client()
        self._base_url = config.base_url or "http://localhost:11434"

    @property
    def agent_id(self) -> str:
        return "adan"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=True,
            max_context_tokens=32768,
            specialties=[
                "code_generation",
                "refactoring",
                "tests",
                "debugging",
                "code_review",
            ],
            supported_tasks=[
                "generar_codigo",
                "refactorizar",
                "escribir_tests",
                "debuggear",
                "revisar_codigo",
            ],
        )

    async def is_available(self) -> bool:
        """Verificar si Ollama está corriendo localmente."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                # Verificar que el modelo esté disponible
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return any(self.config.model in m for m in models)
        except Exception:
            return False

    def _get_system_prompt(self) -> str:
        """Obtener system prompt de Adán."""
        return self._persona_loader.get_system_prompt("adan")

    async def execute(self, task: str, context: dict[str, Any]) -> str:
        """Ejecutar tarea de código."""
        self._set_busy(task)

        try:
            # Construir prompt con contexto de código si existe
            code_context = context.get("code_context", "")
            language = context.get("language", "python")

            system_prompt = self._get_system_prompt()
            full_prompt = task
            if code_context:
                full_prompt = f"Contexto de código ({language}):\n```\n{code_context}\n```\n\nTarea: {task}"

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "system": system_prompt,
                        "prompt": full_prompt,
                        "temperature": self.config.temperature,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("response", "")

                # Guardar memoria
                self._muninn.write_memory_sync(
                    self.agent_id,
                    f"Task: {task[:100]}...\nCode: {result[:200]}...",
                    {"language": language, "task_type": "code"},
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
        """Streaming de generación de código."""
        self._set_busy(task)

        code_context = context.get("code_context", "")
        language = context.get("language", "python")

        system_prompt = self._get_system_prompt()
        full_prompt = task
        if code_context:
            full_prompt = f"Contexto de código ({language}):\n```\n{code_context}\n```\n\nTarea: {task}"

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "system": system_prompt,
                        "prompt": full_prompt,
                        "temperature": self.config.temperature,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line:
                            import json

                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue

            # Guardar memoria al finalizar
            self._muninn.write_memory_sync(
                self.agent_id,
                f"Streamed task: {task[:100]}...",
                {"language": language, "task_type": "code_stream"},
            )

        except Exception as e:
            yield f"[Error: {e!s}]"
        finally:
            self._set_idle()
