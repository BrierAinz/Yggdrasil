"""BaseAgent - Clase base para agentes del Panteón en Vanaheim."""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional


class BaseAgent(ABC):
    """Clase base para todos los agentes en Vanaheim."""

    name: str = "BaseAgent"
    description: str = "Agente base"
    version: str = "1.0.0"

    @abstractmethod
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """
        Ejecuta una tarea y retorna el resultado.

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional

        Returns:
            Dict con al menos: {"response": str, "metadata": dict}
        """
        pass

    async def stream_execute(
        self, task: str, context: str = ""
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Ejecuta una tarea en modo streaming.
        Por defecto, ejecuta normalmente y yield el resultado completo.

        Args:
            task: La tarea a ejecutar
            context: Contexto adicional

        Yields:
            Chunks del resultado: {"chunk": str, "done": bool}
        """
        result = await self.execute(task, context)
        response = result.get("response", "")

        # Simular streaming dividiendo en chunks de 50 chars
        chunk_size = 50
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            is_last = i + chunk_size >= len(response)
            yield {"chunk": chunk, "done": is_last}

    def is_available(self) -> bool:
        """Verifica si el agente está disponible para ejecutar."""
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Retorna metadata del agente."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "available": self.is_available(),
        }
