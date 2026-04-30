"""
Vanaheim Orchestrator - Orquestador local del reino de Vanaheim.

Recibe tareas desde Asgard (Lilith) vía Bifrost y las ejecuta
usando los agentes locales de Vanaheim.
"""
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.json_safe import safe_load, safe_save

logger = logging.getLogger("vanaheim.orchestrator")


@dataclass
class VanaheimTask:
    """Tarea recibida desde Asgard."""

    task_id: str
    agent: str
    task: str
    context: str
    timestamp: float
    priority: int = 5  # 1-10, menor = más prioritario


@dataclass
class VanaheimResult:
    """Resultado de ejecución en Vanaheim."""

    success: bool
    response: str
    agent_used: str
    latency_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VanaheimOrchestrator:
    """
    Orquestador de Vanaheim.

    Gestiona:
    - Recepción de tareas desde Asgard
    - Routing a agentes locales
    - Ejecución de tareas simples y flujos
    - Métricas y health checks
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).resolve().parents[3]
        self.config = self._load_config()

        # Agentes disponibles
        self._agents: Dict[str, Any] = {}
        self._agent_stats: Dict[str, Dict] = {}

        # Cola de tareas
        self._task_queue: List[VanaheimTask] = []
        self._max_concurrent = self.config.get("max_concurrent", 3)
        self._current_tasks = 0

        # Callbacks
        self._on_task_complete: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # Estado
        self._running = False
        self._metrics = {
            "tasks_received": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_latency_ms": 0,
        }

        logger.info("[VanaheimOrchestrator] Inicializado")

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración."""
        config_path = self.base_path / "Config" / "vanaheim.json"
        try:
            return safe_load(config_path, default={})
        except Exception as e:
            logger.error("[VanaheimOrchestrator] Error cargando config: %s", e)
            return {"max_concurrent": 3}

    async def execute_task(
        self, agent: str, task: str, context: str = ""
    ) -> VanaheimResult:
        """
        Ejecuta una tarea en un agente de Vanaheim.

        Args:
            agent: Nombre del agente (freya, heimdall, eir, balder)
            task: Tarea a ejecutar
            context: Contexto adicional

        Returns:
            VanaheimResult con el resultado
        """
        start_time = time.time()
        self._metrics["tasks_received"] += 1

        try:
            # Obtener o crear agente
            agent_instance = self._get_agent(agent)

            if not agent_instance:
                return VanaheimResult(
                    success=False,
                    response="",
                    agent_used=agent,
                    latency_ms=0,
                    error=f"Agente {agent} no disponible",
                )

            # Ejecutar
            result = await self._run_agent(agent_instance, task, context)

            latency = (time.time() - start_time) * 1000
            self._metrics["tasks_completed"] += 1
            self._metrics["total_latency_ms"] += latency

            # Actualizar stats del agente
            if agent not in self._agent_stats:
                self._agent_stats[agent] = {"calls": 0, "latency_ms": 0}
            self._agent_stats[agent]["calls"] += 1
            self._agent_stats[agent]["latency_ms"] += latency

            logger.info(
                "[VanaheimOrchestrator] Task completed by %s in %.2fms", agent, latency
            )

            return VanaheimResult(
                success=True, response=result, agent_used=agent, latency_ms=latency
            )

        except Exception as e:
            self._metrics["tasks_failed"] += 1
            logger.error("[VanaheimOrchestrator] Task failed: %s", e)

            return VanaheimResult(
                success=False,
                response="",
                agent_used=agent,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    def _get_agent(self, agent_name: str) -> Optional[Any]:
        """Obtiene o crea instancia de agente."""
        if agent_name in self._agents:
            return self._agents[agent_name]

        # Crear agente según nombre
        try:
            if agent_name == "freya":
                from ..Agents.freya_agent import get_freya_agent

                agent = get_freya_agent()
            elif agent_name == "heimdall":
                from ..Agents.heimdall_agent import get_heimdall_agent

                agent = get_heimdall_agent()
            elif agent_name == "eir":
                from ..Agents.eir_agent import get_eir_agent

                agent = get_eir_agent()
            elif agent_name == "balder":
                from ..Agents.balder_agent import get_balder_agent

                agent = get_balder_agent()
            else:
                logger.warning("[VanaheimOrchestrator] Unknown agent: %s", agent_name)
                return None

            self._agents[agent_name] = agent
            return agent

        except Exception as e:
            logger.error(
                "[VanaheimOrchestrator] Error creating agent %s: %s", agent_name, e
            )
            return None

    async def _run_agent(self, agent: Any, task: str, context: str) -> str:
        """Ejecuta agente (async wrapper)."""
        import asyncio

        loop = asyncio.get_event_loop()

        # Ejecutar en thread pool para agentes bloqueantes
        return await loop.run_in_executor(
            None,
            agent.execute_task,
            task,
            None,  # complexity_level
            {"context": context} if context else {},
        )

    def get_health(self) -> Dict[str, Any]:
        """Retorna estado de salud del orquestador."""
        return {
            "status": "healthy"
            if self._metrics["tasks_failed"] < self._metrics["tasks_completed"]
            else "degraded",
            "agents_available": list(self._agents.keys()),
            "tasks_in_queue": len(self._task_queue),
            "current_tasks": self._current_tasks,
            "metrics": self._metrics.copy(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas detalladas."""
        total = self._metrics["tasks_completed"] + self._metrics["tasks_failed"]
        avg_latency = (
            self._metrics["total_latency_ms"] / self._metrics["tasks_completed"]
            if self._metrics["tasks_completed"] > 0
            else 0
        )

        return {
            "total_tasks": total,
            "completed": self._metrics["tasks_completed"],
            "failed": self._metrics["tasks_failed"],
            "success_rate": self._metrics["tasks_completed"] / total
            if total > 0
            else 0,
            "avg_latency_ms": avg_latency,
            "agent_stats": self._agent_stats.copy(),
        }

    def reset_stats(self):
        """Resetea estadísticas."""
        self._metrics = {
            "tasks_received": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_latency_ms": 0,
        }
        self._agent_stats = {}


# Singleton
_orchestrator_instance: Optional[VanaheimOrchestrator] = None


def get_vanaheim_orchestrator(base_path: Optional[Path] = None) -> VanaheimOrchestrator:
    """Obtiene instancia singleton."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = VanaheimOrchestrator(base_path)
    return _orchestrator_instance


async def execute_in_vanaheim(
    agent: str, task: str, context: str = "", base_path: Optional[Path] = None
) -> VanaheimResult:
    """Función helper para ejecutar en Vanaheim."""
    orch = get_vanaheim_orchestrator(base_path)
    return await orch.execute_task(agent, task, context)
