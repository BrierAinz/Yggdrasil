"""
Swarm — Sistema multi-agente de Lilith v5.0

Re-exports públicos del subpaquete swarm. Los módulos opcionales
(fallback_chain, review_chain, output_validator, complexity_router)
se importan con try/except para no romper la cadena si faltan dependencias.
"""

# ── Módulos fundamentales (siempre presentes) ──────────────────────────────────
from .base import Agent, AgentConfig, AgentResult, AgentRole, AgentStatus
from .coordinator import Coordinator, CoordinationResult, get_coordinator
from .swarm import Swarm, SwarmConfig, get_swarm
from .task_planner import SubTask, SubTaskStatus, TaskPlanner

# ── Módulos opcionales (pueden no estar disponibles) ──────────────────────────
try:
    from .fallback_chain import FallbackChain
except ImportError:
    FallbackChain = None  # type: ignore[assignment,misc]

try:
    from .review_chain import ReviewChain
except ImportError:
    ReviewChain = None  # type: ignore[assignment,misc]

try:
    from .output_validator import OutputValidator, ValidationResult
except ImportError:
    OutputValidator = None  # type: ignore[assignment,misc]
    ValidationResult = None  # type: ignore[assignment,misc]

try:
    from .complexity_router import ComplexityRouter, classify_complexity, route_code_task
except ImportError:
    ComplexityRouter = None  # type: ignore[assignment,misc]
    classify_complexity = None  # type: ignore[assignment,misc]
    route_code_task = None  # type: ignore[assignment,misc]

try:
    from .conflict_resolver import ConflictConfig, ConflictResolution, ConflictResolver
except ImportError:
    ConflictConfig = None  # type: ignore[assignment,misc]
    ConflictResolution = None  # type: ignore[assignment,misc]
    ConflictResolver = None  # type: ignore[assignment,misc]

__all__ = [
    # Base
    "Agent",
    "AgentConfig",
    "AgentResult",
    "AgentRole",
    "AgentStatus",
    # Swarm
    "Swarm",
    "SwarmConfig",
    "get_swarm",
    # Coordinator
    "Coordinator",
    "CoordinationResult",
    "get_coordinator",
    # Task planner
    "TaskPlanner",
    "SubTask",
    "SubTaskStatus",
    # Opcionales
    "FallbackChain",
    "ReviewChain",
    "OutputValidator",
    "ValidationResult",
    "ComplexityRouter",
    "classify_complexity",
    "route_code_task",
    "ConflictConfig",
    "ConflictResolution",
    "ConflictResolver",
]