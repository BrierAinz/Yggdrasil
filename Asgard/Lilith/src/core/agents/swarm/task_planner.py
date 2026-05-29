"""
Task Planner - Descomposición de tareas complejas

v5.0: Divide tareas complejas en subtareas ejecutables por agentes especializados.
"""
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.agents.planner")


class SubTaskStatus(Enum):
    """Estados de una subtarea."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    """Subtarea individual."""

    id: str
    description: str
    task_type: str  # Tipo de tarea (research, code, review, etc.)
    dependencies: List[str] = field(
        default_factory=list
    )  # IDs de subtareas dependientes
    status: SubTaskStatus = SubTaskStatus.PENDING
    assigned_to: Optional[str] = None  # Nombre del agente asignado
    result: Any = None
    error: Optional[str] = None
    estimated_effort: int = 1  # 1-10 escala de complejidad
    required_capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_execute(self, completed_tasks: set) -> bool:
        """Verifica si la subtarea puede ejecutarse (todas las dependencias completadas)."""
        return all(dep in completed_tasks for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "task_type": self.task_type,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "estimated_effort": self.estimated_effort,
            "required_capabilities": self.required_capabilities,
        }


class TaskPlanner:
    """
    Planificador de tareas.

    Descompone tareas complejas en subtareas ejecutables.
    """

    # Mapeo de tipos de tarea a capacidades requeridas
    TASK_CAPABILITIES = {
        "research": ["web_search", "information_gathering", "analysis"],
        "code": ["coding", "programming", "debugging"],
        "review": ["code_review", "analysis", "validation"],
        "document": ["documentation", "writing"],
        "test": ["testing", "validation"],
        "plan": ["planning", "architecture"],
        "execute": ["execution", "implementation"],
    }

    def __init__(self):
        self._plans: Dict[str, List[SubTask]] = {}

    async def plan(
        self, task_description: str, context: Optional[Dict[str, Any]] = None
    ) -> List[SubTask]:
        """
        Crea un plan de subtareas para una tarea compleja.

        Args:
            task_description: Descripción de la tarea
            context: Contexto adicional

        Returns:
            Lista de subtareas
        """
        # Análisis simple basado en keywords
        # En una implementación completa, esto usaría un LLM

        subtasks = []

        # Detectar tipo de tarea
        task_lower = task_description.lower()

        if any(kw in task_lower for kw in ["investiga", "busca", "research", "find"]):
            subtasks.append(
                self._create_subtask(
                    "research", f"Investigar: {task_description}", ["research"]
                )
            )

        if any(
            kw in task_lower
            for kw in ["code", "implementa", "crea", "write", "programa"]
        ):
            # Agregar planificación si es complejo
            if len(task_description) > 100:
                subtasks.append(
                    self._create_subtask("plan", "Planificar implementación", ["plan"])
                )

            subtasks.append(
                self._create_subtask(
                    "implement",
                    f"Implementar: {task_description}",
                    ["code"],
                    dependencies=[subtasks[-1].id] if subtasks else [],
                )
            )

            subtasks.append(
                self._create_subtask(
                    "test",
                    "Validar implementación",
                    ["test"],
                    dependencies=[subtasks[-1].id],
                )
            )

            subtasks.append(
                self._create_subtask(
                    "review",
                    "Revisar código",
                    ["review"],
                    dependencies=[subtasks[-2].id],
                )
            )

        elif any(kw in task_lower for kw in ["review", "revisa", "check"]):
            subtasks.append(
                self._create_subtask(
                    "review", f"Revisar: {task_description}", ["review"]
                )
            )

        elif any(kw in task_lower for kw in ["documenta", "docs"]):
            subtasks.append(
                self._create_subtask(
                    "document", f"Documentar: {task_description}", ["document"]
                )
            )

        else:
            # Tarea genérica
            subtasks.append(
                self._create_subtask("execute", task_description, ["execute"])
            )

        plan_id = f"plan_{len(self._plans)}"
        self._plans[plan_id] = subtasks

        logger.info(f"Plan creado con {len(subtasks)} subtareas")
        return subtasks

    def _create_subtask(
        self,
        task_type: str,
        description: str,
        capabilities: List[str],
        dependencies: List[str] = None,
    ) -> SubTask:
        """Crea una subtarea."""
        import secrets

        task_id = f"task_{secrets.token_hex(4)}"

        return SubTask(
            id=task_id,
            description=description,
            task_type=task_type,
            dependencies=dependencies or [],
            required_capabilities=capabilities,
            estimated_effort=self._estimate_effort(description),
        )

    def _estimate_effort(self, description: str) -> int:
        """Estima el esfuerzo de una tarea (1-10)."""
        # Heurística simple basada en longitud y complejidad
        effort = 1

        # Palabras que indican complejidad
        complex_indicators = [
            "complex",
            "complicated",
            "architecture",
            "refactor",
            "integrate",
        ]
        if any(ind in description.lower() for ind in complex_indicators):
            effort += 3

        # Longitud
        if len(description) > 200:
            effort += 2
        elif len(description) > 100:
            effort += 1

        return min(effort, 10)

    def get_next_executable(
        self, subtasks: List[SubTask], completed: set
    ) -> Optional[SubTask]:
        """
        Obtiene la siguiente subtarea ejecutable.

        Args:
            subtasks: Lista de subtareas
            completed: Set de IDs completados

        Returns:
            Subtarea siguiente o None
        """
        pending = [st for st in subtasks if st.status == SubTaskStatus.PENDING]

        for task in pending:
            if task.can_execute(completed):
                return task

        return None

    def get_execution_order(self, subtasks: List[SubTask]) -> List[SubTask]:
        """
        Obtiene el orden de ejecución topológico.

        Args:
            subtasks: Lista de subtareas

        Returns:
            Lista ordenada
        """
        # Algoritmo de ordenamiento topológico simple
        result = []
        completed = set()
        remaining = set(st.id for st in subtasks)

        while remaining:
            # Encontrar subtarea sin dependencias pendientes
            found = False
            for task in subtasks:
                if task.id in remaining and task.can_execute(completed):
                    result.append(task)
                    completed.add(task.id)
                    remaining.remove(task.id)
                    found = True
                    break

            if not found:
                # Ciclo de dependencias o error
                logger.error("Ciclo de dependencias detectado")
                break

        return result

    def update_status(
        self,
        subtasks: List[SubTask],
        task_id: str,
        status: SubTaskStatus,
        result: Any = None,
        error: str = None,
    ):
        """Actualiza el estado de una subtarea."""
        for task in subtasks:
            if task.id == task_id:
                task.status = status
                task.result = result
                task.error = error
                break

    def get_plan_summary(self, subtasks: List[SubTask]) -> Dict[str, Any]:
        """Obtiene resumen del plan."""
        total = len(subtasks)
        by_status = {}

        for task in subtasks:
            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1

        total_effort = sum(st.estimated_effort for st in subtasks)
        completed_effort = sum(
            st.estimated_effort
            for st in subtasks
            if st.status == SubTaskStatus.COMPLETED
        )

        return {
            "total_tasks": total,
            "by_status": by_status,
            "total_effort": total_effort,
            "completed_effort": completed_effort,
            "progress_pct": (completed_effort / total_effort * 100)
            if total_effort > 0
            else 0,
        }
