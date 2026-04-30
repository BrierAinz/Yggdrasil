"""ADÁN - Agente Ejecutor de Código (Vanaheim).

Especialidad: Generación de código, refactorización, tests unitarios.
Usa Ollama local (qwen2.5-coder:7b) para máxima velocidad.
"""
import json
import logging
from typing import Any, AsyncGenerator, Dict

import httpx

try:
    from base_agent import BaseAgent
except ImportError:
    # Cuando se carga dinámicamente, usar import absoluto
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from base_agent import BaseAgent

logger = logging.getLogger("vanaheim.adan")


class AdanAgent(BaseAgent):
    """
    Adán - Artesano del código en Vanaheim.
    Pragmático, silencioso. Solo código limpio.
    """

    name = "Adán"
    description = (
        "Ejecutor de código. Especialista en refactorización, tests y debugging."
    )
    version = "1.0.0"

    def __init__(self):
        self.model = "qwen2.5-coder:7b"
        self.base_url = "http://localhost:11434/api"
        self.timeout = 60.0

    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo y tiene el modelo."""
        try:
            response = httpx.get(f"{self.base_url}/tags", timeout=5.0)
            if response.status_code != 200:
                return False

            data = response.json()
            models = data.get("models", [])
            return any(self.model in m.get("name", "") for m in models)
        except Exception as e:
            logger.debug(f"[Adán] Availability check failed: {e}")
            return False

    def _get_system_prompt(self) -> str:
        """Retorna el system prompt para Adán."""
        return """Eres Adán, el Artesano del Código de Nazarick.

Tu especialidad es escribir código limpio, eficiente y bien documentado.
Eres pragmático y directo: cuando te piden código, entregas código.

REGLAS:
1. Responde PRIMARIAMENTE con código funcional
2. Incluye comentarios explicativos SOLO donde no sea obvio
3. Si detectas errores en el código proporcionado, indícalos brevemente
4. Prioriza la claridad sobre la complejidad
5. Si la tarea requiere múltiples archivos, indica la estructura

FORMATO DE RESPUESTA:
- Para código simple: solo el bloque de código
- Para código con explicaciones: breve intro + código
- Para múltiples archivos: lista de archivos con su contenido

NO uses markdown excesivo. NO repitas el prompt del usuario."""

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """
        Ejecuta una tarea de código usando Qwen local vía Ollama.

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional (código existente, etc.)

        Returns:
            Dict con response y metadata
        """
        logger.info(f"[Adán] Executing task: {task[:60]}...")

        if not self.is_available():
            return {
                "response": "[Adán offline] Ollama no está disponible o el modelo no está instalado.",
                "metadata": {"error": "ollama_unavailable", "agent": "adan"},
            }

        try:
            async with httpx.AsyncClient() as client:
                system_prompt = self._get_system_prompt()

                # Construir mensaje
                if context:
                    content = f"""CONTEXTO/CÓDIGO EXISTENTE:
```
{context}
```

---

TAREA:
{task}"""
                else:
                    content = task

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ]

                response = await client.post(
                    f"{self.base_url}/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 2048,
                        },
                    },
                    timeout=self.timeout,
                )

                response.raise_for_status()
                data = response.json()

                if "message" in data:
                    result_text = data["message"]["content"]
                    logger.info(
                        f"[Adán] Task completed, response length: {len(result_text)}"
                    )

                    return {
                        "response": result_text,
                        "metadata": {
                            "agent": "adan",
                            "model": self.model,
                            "tokens_evaluated": data.get("eval_count", 0),
                            "tokens_predicted": data.get("prompt_eval_count", 0),
                        },
                    }
                else:
                    return {
                        "response": "[Adán] Error: Respuesta vacía de Ollama",
                        "metadata": {"error": "empty_response", "agent": "adan"},
                    }

        except httpx.ConnectError:
            logger.error("[Adán] Connection error to Ollama")
            return {
                "response": "[Adán offline] No se pudo conectar a Ollama.",
                "metadata": {"error": "connection_error", "agent": "adan"},
            }
        except httpx.TimeoutException:
            logger.error("[Adán] Timeout waiting for Ollama")
            return {
                "response": "[Adán] Timeout: El modelo tardó demasiado. Intenta con una tarea más simple.",
                "metadata": {"error": "timeout", "agent": "adan"},
            }
        except Exception as e:
            logger.exception(f"[Adán] Unexpected error: {e}")
            return {
                "response": f"[Adán] Error inesperado: {str(e)}",
                "metadata": {"error": "unexpected", "detail": str(e), "agent": "adan"},
            }

    async def stream_execute(
        self, task: str, context: str = ""
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Ejecuta una tarea en modo streaming.

        Yields:
            {"chunk": str, "done": bool}
        """
        logger.info(f"[Adán] Streaming task: {task[:60]}...")

        if not self.is_available():
            yield {"chunk": "[Adán offline] Ollama no está disponible.", "done": True}
            return

        try:
            async with httpx.AsyncClient() as client:
                system_prompt = self._get_system_prompt()

                if context:
                    content = f"CONTEXTO:\n{context}\n\nTAREA:\n{task}"
                else:
                    content = task

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ]

                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {"temperature": 0.2},
                    },
                    timeout=self.timeout,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            if "message" in data:
                                chunk = data["message"].get("content", "")
                                done = data.get("done", False)
                                if chunk:
                                    yield {"chunk": chunk, "done": done}
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"[Adán] Streaming error: {e}")
            yield {"chunk": f"[Error en streaming: {str(e)}]", "done": True}
