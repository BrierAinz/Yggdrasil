"""
Coordinator - Orquestador del swarm

v5.0: Coordina la ejecución de tareas, asignando agentes y manejando dependencias.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .agent_base import Agent, AgentResult, AgentRole
from .swarm import Swarm, get_swarm
from .task_planner import SubTask, SubTaskStatus, TaskPlanner

logger = logging.getLogger("lilith.agents.coordinator")


@dataclass
class CoordinationResult:
    """Resultado de coordinación de una tarea."""

    success: bool
    task_id: str
    subtask_results: List[AgentResult]
    final_output: Any
    execution_time_ms: float
    agents_used: List[str]
    error: Optional[str] = None


class Coordinator:
    """
    Coordinador de ejecución multi-agente.

    Responsabilidades:
    - Planificar tareas complejas
    - Asignar subtareas a agentes apropiados
    - Manejar dependencias entre subtareas
    - Agregar resultados
    """

    def __init__(
        self, swarm: Optional[Swarm] = None, planner: Optional[TaskPlanner] = None
    ):
        self.swarm = swarm or get_swarm()
        self.planner = planner or TaskPlanner()
        self._execution_history: List[Dict] = []

    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_agents: Optional[List[str]] = None,
    ) -> CoordinationResult:
        """
        Ejecuta una tarea coordinando múltiples agentes.

        Args:
            task_description: Descripción de la tarea
            context: Contexto compartido
            preferred_agents: Agentes preferidos para la tarea

        Returns:
            Resultado de la coordinación
        """
        import time

        start_time = time.time()

        # 1. Planificar
        subtasks = await self.planner.plan(task_description, context)

        if not subtasks:
            return CoordinationResult(
                success=True,
                task_id=f"task_{len(self._execution_history)}",
                subtask_results=[],
                final_output="No se requieren subtareas",
                execution_time_ms=0,
                agents_used=[],
            )

        # 2. Ejecutar subtareas respetando dependencias
        results = []
        completed = set()
        agents_used = set()
        failed = False

        # Obtener orden de ejecución
        execution_order = self.planner.get_execution_order(subtasks)

        for subtask in execution_order:
            if failed:
                # Marcar como fallidas las subtareas pendientes
                subtask.status = SubTaskStatus.FAILED
                subtask.error = "Dependencia fallida"
                continue

            # Encontrar agente apropiado
            agent = self._select_agent_for_subtask(subtask, preferred_agents)

            if not agent:
                failed = True
                subtask.status = SubTaskStatus.FAILED
                subtask.error = "No se encontró agente disponible"
                results.append(
                    AgentResult(
                        success=False,
                        output=None,
                        agent_name="unknown",
                        task_id=subtask.id,
                        execution_time_ms=0,
                        error="No agent available",
                    )
                )
                continue

            # Asignar y ejecutar
            subtask.assigned_to = agent.config.name
            subtask.status = SubTaskStatus.IN_PROGRESS
            agents_used.add(agent.config.name)

            task_def = {
                "id": subtask.id,
                "description": subtask.description,
                "type": subtask.task_type,
                "context": context,
            }

            result = await agent.execute(task_def, context)
            results.append(result)

            if result.success:
                subtask.status = SubTaskStatus.COMPLETED
                subtask.result = result.output
                completed.add(subtask.id)
            else:
                subtask.status = SubTaskStatus.FAILED
                subtask.error = result.error
                failed = True

        execution_time_ms = (time.time() - start_time) * 1000

        # Agregar resultados
        final_output = self._aggregate_results(subtasks, results)

        # Guardar en historial
        self._execution_history.append(
            {
                "task": task_description,
                "subtasks": len(subtasks),
                "agents_used": list(agents_used),
                "execution_time_ms": execution_time_ms,
                "success": not failed,
            }
        )

        return CoordinationResult(
            success=not failed,
            task_id=f"task_{len(self._execution_history) - 1}",
            subtask_results=results,
            final_output=final_output,
            execution_time_ms=execution_time_ms,
            agents_used=list(agents_used),
            error="Algunas subtareas fallaron" if failed else None,
        )

    def _select_agent_for_subtask(
        self, subtask: SubTask, preferred_agents: Optional[List[str]] = None
    ) -> Optional[Agent]:
        """
        Selecciona el mejor agente para una subtarea.

        Args:
            subtask: Subtarea a ejecutar
            preferred_agents: Agentes preferidos

        Returns:
            Agente seleccionado o None
        """
        # 1. Buscar en preferidos
        if preferred_agents:
            for agent_name in preferred_agents:
                agent = self.swarm.get_agent(agent_name)
                if agent and agent.status.value == "idle":
                    if any(
                        cap in agent.config.capabilities
                        for cap in subtask.required_capabilities
                    ):
                        return agent

        # 2. Buscar por capacidades
        for capability in subtask.required_capabilities:
            agents = self.swarm.find_agents_by_capability(capability)
            for agent in agents:
                if agent.status.value == "idle":
                    return agent

        # 3. Buscar por rol
        role_mapping = {
            "research": AgentRole.RESEARCHER,
            "code": AgentRole.EXECUTOR,
            "plan": AgentRole.PLANNER,
            "review": AgentRole.REVIEWER,
        }

        task_role = role_mapping.get(subtask.task_type)
        if task_role:
            agents = self.swarm.get_agents_by_role(task_role)
            for agent in agents:
                if agent.status.value == "idle":
                    return agent

        # 4. Cualquier agente disponible
        available = self.swarm.get_available_agents()
        if available:
            return available[0]

        return None

    def _aggregate_results(
        self, subtasks: List[SubTask], results: List[AgentResult]
    ) -> str:
        """
        Agrega resultados de subtareas en output final.

        Args:
            subtasks: Lista de subtareas
            results: Lista de resultados

        Returns:
            Output agregado
        """
        parts = []

        for subtask, result in zip(subtasks, results):
            if subtask.status == SubTaskStatus.COMPLETED:
                parts.append(f"## {subtask.description}\n\n{result.output}")
            else:
                parts.append(
                    f"## {subtask.description}\n\n"
                    f"*[Error: {subtask.error or 'Falló'}]*"
                )

        return "\n\n---\n\n".join(parts)

    async def execute_simple(
        self,
        agent_name: str,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentResult]:
        """
        Ejecuta una tarea simple en un agente específico.

        Args:
            agent_name: Nombre del agente
            task: Definición de tarea
            context: Contexto

        Returns:
            Resultado o None
        """
        agent = self.swarm.get_agent(agent_name)
        if not agent:
            return None

        return await agent.execute(task, context)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del coordinador."""
        total = len(self._execution_history)
        successful = sum(1 for h in self._execution_history if h["success"])

        return {
            "total_tasks": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "swarm_stats": self.swarm.get_stats(),
        }


# Singleton global
_coordinator: Optional[Coordinator] = None


def get_coordinator() -> Coordinator:
    """Obtiene instancia singleton del coordinador."""
    global _coordinator
    if _coordinator is None:
        _coordinator = Coordinator()
    return _coordinator
