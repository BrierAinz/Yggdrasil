"""Crystal - La Cara Pública.

Backend: Kimi (kimi-for-coding) con fallback a Ollama
Especialidad: Asistente conversacional para Discord/usuarios públicos
"""
import os
from typing import Any, AsyncGenerator, Dict

import httpx
from Agents.Base import VanirAgent
from Core.memory import get_muninn_client
from Core.models.agent import AgentCapabilities, AgentConfig
from Core.persona import get_persona_loader


class CrystalAgent(VanirAgent):
    """Crystal - Asistente público del Panteón."""

    KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
    OLLAMA_URL = "http://localhost:11434"

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._persona_loader = get_persona_loader()
        self._muninn = get_muninn_client()
        self._kimi_key = os.getenv("CRYSTAL_KIMI_API_KEY") or os.getenv(
            "KIMI_API_KEY", ""
        )
        self._use_ollama_fallback = True

    @property
    def agent_id(self) -> str:
        return "crystal"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=False,
            max_context_tokens=8192,
            specialties=[
                "conversation",
                "general_assistance",
                "faq",
                "help",
            ],
            supported_tasks=[
                "conversar",
                "responder_preguntas",
                "ayuda_general",
            ],
        )

    async def is_available(self) -> bool:
        """Verificar disponibilidad (Kimi primero, luego Ollama)."""
        if self._kimi_key:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        "https://api.moonshot.cn/v1/models",
                        headers={"Authorization": f"Bearer {self._kimi_key}"},
                    )
                    if resp.status_code == 200:
                        return True
            except Exception:
                pass

        # Fallback a Ollama
        if self._use_ollama_fallback:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.OLLAMA_URL}/api/tags")
                    return resp.status_code == 200
            except Exception:
                return False

        return False

    def _get_system_prompt(self) -> str:
        """Obtener system prompt de Crystal."""
        return self._persona_loader.get_system_prompt("crystal")

    async def _call_kimi(self, messages: list, stream: bool = False) -> str:
        """Llamar a Kimi API."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                self.KIMI_API_URL,
                headers={
                    "Authorization": f"Bearer {self._kimi_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "max_tokens": 4096,
                    "stream": stream,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, prompt: str, system: str, stream: bool = False) -> str:
        """Llamar a Ollama fallback."""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.post(
                f"{self.OLLAMA_URL}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "system": system,
                    "prompt": prompt,
                    "temperature": self.config.temperature,
                    "stream": stream,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def execute(self, task: str, context: Dict[str, Any]) -> str:
        """Ejecutar tarea conversacional."""
        self._set_busy(task)

        try:
            # Construir historial si existe
            history = context.get("conversation_history", [])
            system_prompt = self._get_system_prompt()

            messages = [{"role": "system", "content": system_prompt}]

            # Agregar historial
            for msg in history[-5:]:  # Solo últimos 5 mensajes
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append({"role": role, "content": content})

            # Agregar mensaje actual
            messages.append({"role": "user", "content": task})

            # Intentar Kimi primero
            result = ""
            if self._kimi_key:
                try:
                    result = await self._call_kimi(messages)
                except Exception:
                    pass

            # Fallback a Ollama
            if not result and self._use_ollama_fallback:
                full_prompt = "\n".join(
                    [f"{m['role']}: {m['content']}" for m in messages]
                )
                result = await self._call_ollama(full_prompt, system_prompt)

            if not result:
                result = "Lo siento, no puedo procesar tu solicitud en este momento."

            # Guardar memoria
            user_id = context.get("user_id")
            self._muninn.write_memory_sync(
                self.agent_id,
                f"User: {task[:100]}...\nCrystal: {result[:150]}...",
                {"user_id": user_id, "channel": context.get("channel")},
            )

            return result

        except Exception as e:
            self._set_error(str(e))
            raise
        finally:
            self._set_idle()

    async def stream(
        self, task: str, context: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Streaming conversacional."""
        self._set_busy(task)

        try:
            history = context.get("conversation_history", [])
            system_prompt = self._get_system_prompt()

            messages = [{"role": "system", "content": system_prompt}]
            for msg in history[-3:]:
                messages.append(
                    {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                )
            messages.append({"role": "user", "content": task})

            # Intentar Kimi streaming
            if self._kimi_key:
                try:
                    async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                        async with client.stream(
                            "POST",
                            self.KIMI_API_URL,
                            headers={
                                "Authorization": f"Bearer {self._kimi_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": self.config.model,
                                "messages": messages,
                                "temperature": self.config.temperature,
                                "stream": True,
                            },
                        ) as resp:
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
                            return
                except Exception:
                    pass

            # Fallback sin streaming
            result = await self.execute(task, context)
            yield result

        except Exception as e:
            yield f"[Error: {str(e)}]"
        finally:
            self._set_idle()
