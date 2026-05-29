"""
ADÁN - Agente Ejecutor de Código (Qwen local)
Especialidad: Generación de código, refactorización, tests unitarios.
Trigger: tareas de generación de código puro sin necesidad de contexto externo.
"""
from pathlib import Path

import httpx

from .base_agent import BaseAgent


class AdanAgent(BaseAgent):
    """
    Adán - Ejecutor de código bajo las órdenes de Lilith.
    Pragmático, silencioso. Solo código limpio.
    """

    name = "Adán"
    description = "Ejecutor de código. Pragmático, silencioso. Solo código limpio."

    def __init__(self):
        self.model = "qwen2.5-coder:7b"
        self.base_url = "http://localhost:11434/api"

    def is_available(self) -> bool:
        """Verifica si Ollama está corriendo"""
        import httpx

        try:
            response = httpx.get(f"{self.base_url}/tags", timeout=5.0)
            return response.status_code == 200
        except:
            return False

    def get_system_prompt(self) -> str:
        try:
            from pathlib import Path

            from src.core.persona.loader import get_persona_loader

            base_path = Path(__file__).resolve().parent.parent.parent.parent
            loader = get_persona_loader(base_path)
            return loader.get_system_prompt("adan", include_common=True)
        except Exception:
            return "[Adán — Ejecutor de código] Agente pragmático y silencioso. Fallback..."

    async def execute(self, task: str, context: str = "", **_kwargs) -> str:
        """
        Ejecuta una tarea de código usando Qwen local vía Ollama.

        Args:
            task: La tarea a ejecutar (ej: "genera una función de hash")
            context: Contexto adicional (código existente, etc.)

        Returns:
            Código generado
        """
        # Mejora-1: leer memoria previa del vault de Adán
        memory_block = ""
        try:
            from pathlib import Path as _Path

            from src.core.memory.muninn_memory import MuninnMemory as _MM

            _bp = _Path(__file__).resolve().parent.parent.parent.parent
            memory_block = await _MM(_bp).get_agent_memory("adan", task)
        except Exception:
            pass

        try:
            async with httpx.AsyncClient() as client:
                system_prompt = self.get_system_prompt()
                if memory_block:
                    system_prompt = system_prompt + "\n\n" + memory_block
                messages = [{"role": "system", "content": system_prompt}]

                # Construir el mensaje del usuario
                if context:
                    content = f"""CONTEXTO EXISTENTE:
```
{context}
```

---

TAREA:
{task}"""
                else:
                    content = task

                messages.append({"role": "user", "content": content})

                response = await client.post(
                    f"{self.base_url}/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.2, "num_predict": 2048},
                    },
                    timeout=180.0,
                )

                response.raise_for_status()
                data = response.json()

                if "message" in data:
                    result_text = data["message"]["content"]
                    # Mejora-1: escribir resultado en vault de Adán (fire-and-forget)
                    try:
                        from src.core.memory.muninn_memory import (
                            _run_coro_fire_and_forget,
                        )

                        _run_coro_fire_and_forget(
                            _MM(_bp).write_agent_output("adan", task, result_text)
                        )
                    except Exception:
                        pass
                    return result_text
                else:
                    return "[Adán] Error: Respuesta vacía de Ollama"

        except httpx.ConnectError:
            return "[Adán offline] Ollama no está corriendo. Inicia Ollama o usa otro agente."
        except httpx.TimeoutException:
            return "[Adán] Timeout: El modelo tardó demasiado. Intenta con una tarea más simple."
        except Exception as e:
            return f"[Adán] Error: {str(e)}. Fallback a Lilith."
