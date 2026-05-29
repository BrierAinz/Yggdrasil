"""
Swarm - Gestión del colectivo de agentes

v5.0: Mantiene el registro de agentes y facilita comunicación entre ellos.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from .agent_base import Agent, AgentConfig, AgentRole

logger = logging.getLogger("lilith.agents.swarm")


@dataclass
class SwarmConfig:
    """Configuración del swarm."""

    max_parallel_executions: int = 5
    enable_broadcast: bool = True
    shared_context: bool = True


class Swarm:
    """
    Colectivo de agentes.

    Gestiona:
    - Registro de agentes
    - Descubrimiento de capacidades
    - Comunicación entre agentes
    - Contexto compartido
    """

    def __init__(self, config: Optional[SwarmConfig] = None):
        self.config = config or SwarmConfig()
        self._agents: Dict[str, Agent] = {}
        self._agents_by_role: Dict[AgentRole, List[str]] = {}
        self._shared_context: Dict[str, Any] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def register(self, agent: Agent) -> bool:
        """
        Registra un agente en el swarm.

        Args:
            agent: Agente a registrar

        Returns:
            True si se registró
        """
        if agent.config.name in self._agents:
            logger.warning(f"Agente {agent.config.name} ya registrado")
            return False

        self._agents[agent.config.name] = agent

        # Indexar por rol
        role = agent.config.role
        if role not in self._agents_by_role:
            self._agents_by_role[role] = []
        self._agents_by_role[role].append(agent.config.name)

        logger.info(f"Agente registrado: {agent.config.name} ({role.value})")
        return True

    def unregister(self, agent_name: str) -> bool:
        """Desregistra un agente."""
        if agent_name not in self._agents:
            return False

        agent = self._agents[agent_name]
        role = agent.config.role

        del self._agents[agent_name]

        if role in self._agents_by_role:
            if agent_name in self._agents_by_role[role]:
                self._agents_by_role[role].remove(agent_name)

        logger.info(f"Agente desregistrado: {agent_name}")
        return True

    def get_agent(self, name: str) -> Optional[Agent]:
        """Obtiene un agente por nombre."""
        return self._agents.get(name)

    def get_agents_by_role(self, role: AgentRole) -> List[Agent]:
        """Obtiene agentes por rol."""
        names = self._agents_by_role.get(role, [])
        return [self._agents[n] for n in names if n in self._agents]

    def find_agents_by_capability(self, capability: str) -> List[Agent]:
        """Encuentra agentes que tienen una capacidad."""
        return [
            agent
            for agent in self._agents.values()
            if capability in agent.config.capabilities
        ]

    def get_available_agents(self) -> List[Agent]:
        """Obtiene agentes disponibles (no ocupados)."""
        from .agent_base import AgentStatus

        return [
            agent for agent in self._agents.values() if agent.status == AgentStatus.IDLE
        ]

    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agentes con su estado."""
        return [agent.to_dict() for agent in self._agents.values()]

    def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """
        Envía un mensaje a todos los agentes.

        Args:
            message: Mensaje a enviar
            exclude: Nombres de agentes a excluir
        """
        if not self.config.enable_broadcast:
            return

        exclude = exclude or []
        for name, agent in self._agents.items():
            if name not in exclude:
                # Los agentes pueden escuchar broadcasts
                # Implementación específica depende del agente
                pass

    def set_shared_context(self, key: str, value: Any):
        """Establece valor en contexto compartido."""
        if self.config.shared_context:
            self._shared_context[key] = value

    def get_shared_context(self, key: str) -> Optional[Any]:
        """Obtiene valor del contexto compartido."""
        return self._shared_context.get(key)

    def get_all_shared_context(self) -> Dict[str, Any]:
        """Obtiene todo el contexto compartido."""
        return self._shared_context.copy()

    async def execute_parallel(
        self, tasks: List[tuple[str, Dict[str, Any]]]
    ) -> List[Any]:
        """
        Ejecuta múltiples tareas en paralelo.

        Args:
            tasks: Lista de (agent_name, task_dict)

        Returns:
            Lista de resultados
        """
        semaphore = asyncio.Semaphore(self.config.max_parallel_executions)

        async def execute_with_limit(agent_name: str, task: Dict):
            async with semaphore:
                agent = self.get_agent(agent_name)
                if not agent:
                    return None
                result = await agent.execute(task, self._shared_context)
                return result

        tasks_coros = [execute_with_limit(name, task) for name, task in tasks]

        return await asyncio.gather(*tasks_coros, return_exceptions=True)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del swarm."""
        total = len(self._agents)
        by_role = {
            role.value: len(names) for role, names in self._agents_by_role.items()
        }

        available = len(self.get_available_agents())

        return {
            "total_agents": total,
            "available_agents": available,
            "busy_agents": total - available,
            "by_role": by_role,
            "shared_context_keys": list(self._shared_context.keys()),
        }


# Singleton global
_swarm: Optional[Swarm] = None


def get_swarm() -> Swarm:
    """Obtiene instancia singleton del swarm."""
    global _swarm
    if _swarm is None:
        _swarm = Swarm()
    return _swarm
