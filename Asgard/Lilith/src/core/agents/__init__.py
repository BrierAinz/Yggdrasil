"""
Panteón de Agentes - Lilith v5.0
Arquitectura Multi-Agente con Swarm Orchestration

Agentes activos (en panteon/):
- Eva (Grok): Análisis, documentación, contexto largo
- Adán (Qwen local): Código puro, sin internet
- Odín (Kimi): Investigación, contexto masivo, creativo
- Shalltear (Venice): Clasificación, parsing NL, triaje

Agentes eliminados:
- Crystal (Discord desactivado)
- Albedo (over-engineering)
- Archivero (absorbido por Eva/Odín)

Swarm v5.0:
- Orquestación multi-agente
- Task planner para descomposición
- Coordinator para asignación dinámica
"""

# Agentes del panteón (vivos)
from .panteon.adan import AdanAgent
from .panteon.eva import EvaAgent
from .panteon.odin import OdinAgent
from .panteon.shalltear import ShalltearAgent

# Base
from .base import BaseAgent

# Swarm v5.0
from .swarm.base import Agent, AgentConfig, AgentRole, AgentStatus
from .swarm.coordinator import Coordinator, get_coordinator
from .swarm.swarm import Swarm, get_swarm
from .swarm.task_planner import SubTask, TaskPlanner

# Integraciones
from .crystal_functions import (
    CrystalFunctionIntegration,
    CrystalFunctionResult,
    get_crystal_function_integration,
)

__all__ = [
    # Agentes del panteón
    "BaseAgent",
    "EvaAgent",
    "AdanAgent",
    "OdinAgent",
    "ShalltearAgent",
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
    # Integraciones
    "CrystalFunctionIntegration",
    "get_crystal_function_integration",
    "CrystalFunctionResult",
]