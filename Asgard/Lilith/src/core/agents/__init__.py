"""
Panteón de Agentes - Lilith v5.0
Arquitectura Multi-Agente con Swarm Orchestration

Agentes:
- Eva (Grok): Análisis, documentación, contexto largo
- Adán (Qwen local): Código puro, sin internet
- Odín (Kimi): Investigación, contexto masivo, creativo
- Crystal (Claude): Ejecutor principal

Swarm v5.0:
- Orquestación multi-agente
- Task planner para descomposición
- Coordinator para asignación dinámica
"""

from .adan_agent import AdanAgent

# Swarm v5.0
from .agent_base import Agent, AgentConfig, AgentRole, AgentStatus
from .base_agent import BaseAgent
from .coordinator import Coordinator, get_coordinator

# Integraciones v5.0
from .crystal_functions import (
    CrystalFunctionIntegration,
    CrystalFunctionResult,
    get_crystal_function_integration,
)
from .eva_agent import EvaAgent
from .odin_agent import OdinAgent
from .swarm import Swarm, get_swarm
from .task_planner import SubTask, TaskPlanner

__all__ = [
    # Agentes clásicos
    "BaseAgent",
    "EvaAgent",
    "AdanAgent",
    "OdinAgent",
    # Swarm v5.0
    "Agent",
    "AgentRole",
    "AgentStatus",
    "AgentConfig",
    "Swarm",
    "get_swarm",
    "TaskPlanner",
    "SubTask",
    "Coordinator",
    "get_coordinator",
    # Integraciones v5.0
    "CrystalFunctionIntegration",
    "get_crystal_function_integration",
    "CrystalFunctionResult",
]
