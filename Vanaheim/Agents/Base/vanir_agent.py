"""Clase base abstracta para todos los agentes de Vanaheim."""
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

from Core.models.agent import AgentCapabilities, AgentConfig, AgentState


class VanirAgent(ABC):
    """Agente base del Panteón en Vanaheim.

    Todos los agentes deben heredar de esta clase e implementar
    los métodos abstractos.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.state = AgentState.IDLE
        self._current_task: Optional[str] = None
        self._start_time: Optional[float] = None

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador único del agente."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> AgentCapabilities:
        """Capacidades del agente."""
        pass

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> str:
        """Ejecutar una tarea de forma síncrona.

        Args:
            task: Descripción de la tarea
            context: Contexto adicional (memoria, historial, etc.)

        Returns:
            Resultado de la ejecución
        """
        pass

    @abstractmethod
    async def stream(
        self, task: str, context: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Ejecutar una tarea con streaming de respuesta.

        Args:
            task: Descripción de la tarea
            context: Contexto adicional

        Yields:
            Chunks de la respuesta
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Verificar si el agente está disponible.

        Returns:
            True si el backend (API/local) responde
        """
        pass

    async def health(self) -> Dict[str, Any]:
        """Obtener estado de salud del agente."""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "state": self.state.value,
            "available": await self.is_available(),
            "model": self.config.model,
            "provider": self.config.provider,
            "current_task": self._current_task,
        }

    def _set_busy(self, task: str) -> None:
        """Marcar agente como ocupado."""
        self.state = AgentState.BUSY
        self._current_task = task
        self._start_time = time.time()

    def _set_idle(self) -> None:
        """Marcar agente como disponible."""
        self.state = AgentState.IDLE
        self._current_task = None
        self._start_time = None

    def _set_error(self, error: str) -> None:
        """Marcar agente en estado de error."""
        self.state = AgentState.ERROR
        self._current_task = None

    def _get_execution_time_ms(self) -> Optional[float]:
        """Obtener tiempo de ejecución en ms."""
        if self._start_time:
            return (time.time() - self._start_time) * 1000
        return None
