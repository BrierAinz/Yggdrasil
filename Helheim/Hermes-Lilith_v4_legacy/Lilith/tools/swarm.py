"""
Swarm Tools - Tools para Lilith Swarm
=====================================
Expone funciones para spawn, status y control del swarm.
"""
import time
from typing import Dict, List, Optional

from Lilith.Swarm.agent import AgentStatus
from Lilith.Swarm.manager import get_swarm_manager


def spawn_swarm(
    task: str,
    num_agents: int = 2,
    capabilities: Optional[List[str]] = None,
) -> Dict:
    """
    Spawnea un swarm de agentes para una tarea.

    Args:
        task: Descripcion de la tarea
        num_agents: Numero de agentes (default 2)
        capabilities: Capabilities de los agentes

    Returns:
        Dict con agent_ids y status inicial
    """
    mgr = get_swarm_manager()
    agent_ids = mgr.spawn_swarm(
        task=task,
        num_agents=num_agents,
        capabilities=capabilities or ["coding"],
    )

    return {
        "success": True,
        "agent_ids": agent_ids,
        "task": task,
        "num_agents": num_agents,
        "status": "spawned",
    }


def swarm_status() -> Dict:
    """
    Obtiene estado completo del swarm.

    Returns:
        Dict con agentes, locks, mensajes y conflictos
    """
    mgr = get_swarm_manager()
    return mgr.get_status_report()


def swarm_kill(agent_id: str) -> Dict:
    """
    Mata un agente del swarm.

    Args:
        agent_id: ID del agente a matar

    Returns:
        Dict con resultado
    """
    mgr = get_swarm_manager()
    result = mgr.kill_agent(agent_id)
    return {
        "success": result,
        "agent_id": agent_id,
        "message": "Agente eliminado" if result else "Agente no encontrado",
    }


def swarm_kill_all() -> Dict:
    """
    Mata todos los agentes del swarm.

    Returns:
        Dict con resultado
    """
    mgr = get_swarm_manager()
    mgr.kill_all()
    return {
        "success": True,
        "message": "Todos los agentes eliminados",
    }


def swarm_wait(
    agent_ids: Optional[List[str]] = None,
    timeout: float = 30.0,
) -> Dict:
    """
    Espera a que agentes completen su trabajo.

    Args:
        agent_ids: IDs a esperar (None = todos)
        timeout: Timeout en segundos

    Returns:
        Dict con resultado de la espera
    """
    mgr = get_swarm_manager()
    completed = mgr.wait_for_completion(agent_ids, timeout)

    return {
        "success": completed,
        "completed": completed,
        "timeout": not completed,
        "message": "Completado" if completed else f"Timeout despues de {timeout}s",
    }


def swarm_result(agent_id: str) -> Dict:
    """
    Obtiene resultado de un agente.

    Args:
        agent_id: ID del agente

    Returns:
        Dict con resultado o error
    """
    mgr = get_swarm_manager()
    result = mgr.get_agent_results(agent_id)

    if result is None:
        return {
            "success": False,
            "error": f"Agente {agent_id} no encontrado",
        }

    return {
        "success": True,
        "agent_id": agent_id,
        "result": result,
    }


def swarm_conflicts() -> Dict:
    """
    Obtiene conflictos pendientes del swarm.

    Returns:
        Dict con lista de conflictos
    """
    mgr = get_swarm_manager()
    pending = [c.to_dict() for c in mgr.conflicts if not c.resolved]

    return {
        "success": True,
        "count": len(pending),
        "conflicts": pending,
    }


def get_tools():
    """Retorna lista de definiciones de tools del swarm."""
    return [
        {
            "type": "function",
            "function": {
                "name": "spawn_swarm",
                "description": "Crear un swarm de agentes para ejecutar una tarea en paralelo. Los agentes trabajan simultaneamente y se coordinan automaticamente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Descripcion de la tarea a ejecutar",
                        },
                        "num_agents": {
                            "type": "integer",
                            "description": "Numero de agentes (default 2, max 5)",
                        },
                        "capabilities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Capabilities de los agentes (ej: ['coding', 'testing'])",
                        },
                    },
                    "required": ["task"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "swarm_status",
                "description": "Obtener estado completo del swarm: agentes activos, completados, locks de archivos, mensajes pendientes y conflictos.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "swarm_kill",
                "description": "Eliminar un agente del swarm por su ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID del agente a eliminar",
                        },
                    },
                    "required": ["agent_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "swarm_result",
                "description": "Obtener resultado de un agente especifico del swarm.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID del agente",
                        },
                    },
                    "required": ["agent_id"],
                },
            },
        },
    ]
