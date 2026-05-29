"""
Agent Base - Clase base para agentes del swarm

v5.0: Base class que define la interfaz común para todos los agentes.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.agents")


class AgentRole(Enum):
    """Roles de agentes en el swarm."""

    PLANNER = "planner"  # Planifica tareas
    EXECUTOR = "executor"  # Ejecuta acciones
    RESEARCHER = "researcher"  # Busca información
    REVIEWER = "reviewer"  # Revisa calidad
    COORDINATOR = "coordinator"  # Coordina el swarm
    SPECIALIST = "specialist"  # Especialista en área específica
    ORCHESTRATOR = "orchestrator"  # Orquesta flujos complejos


class AgentStatus(Enum):
    """Estados de un agente."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentConfig:
    """Configuración de un agente."""

    name: str
    role: AgentRole
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    timeout_seconds: float = 60.0
    retry_on_failure: bool = True
    max_retries: int = 2


@dataclass
class AgentResult:
    """Resultado de ejecución de un agente."""

    success: bool
    output: Any
    agent_name: str
    task_id: str
    execution_time_ms: float
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class Agent:
    """
    Agente base del sistema swarm.

    Todos los agentes especializados heredan de esta clase.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.status = AgentStatus.IDLE
        self._current_task: Optional[str] = None
        self._task_history: List[Dict] = []
        self._metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time_ms": 0,
        }

    async def execute(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        Ejecuta una tarea.

        Args:
            task: Definición de la tarea
            context: Contexto compartido

        Returns:
            Resultado de la ejecución
        """
        if self.status == AgentStatus.BUSY:
            return AgentResult(
                success=False,
                output=None,
                agent_name=self.config.name,
                task_id=task.get("id", "unknown"),
                execution_time_ms=0,
                error="Agent is busy",
            )

        self.status = AgentStatus.BUSY
        self._current_task = task.get("id")

        start_time = datetime.utcnow()

        try:
            # Ejecutar implementación específica
            result = await self._execute_impl(task, context or {})

            # Actualizar métricas
            self._metrics["tasks_completed"] += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._metrics["total_execution_time_ms"] += execution_time

            # Guardar en historial
            self._task_history.append(
                {
                    "task_id": task.get("id"),
                    "timestamp": start_time.isoformat(),
                    "success": True,
                    "execution_time_ms": execution_time,
                }
            )

            self.status = AgentStatus.IDLE
            self._current_task = None

            return AgentResult(
                success=True,
                output=result,
                agent_name=self.config.name,
                task_id=task.get("id", "unknown"),
                execution_time_ms=execution_time,
            )

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            self._task_history.append(
                {
                    "task_id": task.get("id"),
                    "timestamp": start_time.isoformat(),
                    "success": False,
                    "error": str(e),
                }
            )

            self.status = AgentStatus.ERROR
            self._current_task = None

            logger.error(f"Agent {self.config.name} failed: {e}")

            return AgentResult(
                success=False,
                output=None,
                agent_name=self.config.name,
                task_id=task.get("id", "unknown"),
                execution_time_ms=execution_time,
                error=str(e),
            )

    async def _execute_impl(self, task: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Implementación específica de ejecución.

        Las subclases deben sobrescribir este método.
        """
        raise NotImplementedError("Subclasses must implement _execute_impl")

    def can_handle(self, task_type: str) -> bool:
        """Verifica si el agente puede manejar un tipo de tarea."""
        return task_type in self.config.capabilities

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del agente."""
        total_tasks = self._metrics["tasks_completed"] + self._metrics["tasks_failed"]
        avg_time = (
            self._metrics["total_execution_time_ms"] / total_tasks
            if total_tasks > 0
            else 0
        )

        return {
            "name": self.config.name,
            "role": self.config.role.value,
            "status": self.status.value,
            "tasks_completed": self._metrics["tasks_completed"],
            "tasks_failed": self._metrics["tasks_failed"],
            "success_rate": (
                self._metrics["tasks_completed"] / total_tasks * 100
                if total_tasks > 0
                else 0
            ),
            "avg_execution_time_ms": avg_time,
            "current_task": self._current_task,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el agente."""
        return {
            "name": self.config.name,
            "role": self.config.role.value,
            "description": self.config.description,
            "capabilities": self.config.capabilities,
            "status": self.status.value,
            "stats": self.get_stats(),
        }
