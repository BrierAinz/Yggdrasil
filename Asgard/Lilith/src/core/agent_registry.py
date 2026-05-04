"""
Lilith 4.0 Fase 1 — AgentRegistry: registro de agentes como entidades de primera clase.

Cada agente tiene agent_id, tool_name (para compatibilidad con Planner/Steps), descripción
y execute(params) -> ToolResult. El AgentCaller usa el registry para ejecutar delegate_*
cuando está disponible; si no, delega al ToolRegistryV3.

Los agentes actuales (Eva, Adán, Lucifer, Odín) se registran como wrappers sobre las
tools existentes (DelegateEvaTool, etc.) para no duplicar lógica.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tools_v3.protocol import ToolResult


class Agent(ABC):
    """
    Agente del ecosistema 4.0: entidad con identidad, tool_name (paso del plan) y ejecución.
    Futuro: memoria y tools propias por agente.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Identificador único del agente (eva, adan, lucifer, odin)."""
        ...

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Nombre de la tool con la que el Planner genera pasos (ej. delegate_eva)."""
        ...

    @property
    def description(self) -> str:
        """Descripción breve del agente para listados y futura selección automática."""
        return ""

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecuta la tarea con los params del Step. Devuelve ToolResult (dict con response/error)."""
        ...


class AgentRegistry:
    """
    Registro de agentes por agent_id y por tool_name.
    Permite resolver un paso (tool_name) al agente que lo ejecuta.
    """

    def __init__(self) -> None:
        self._by_id: Dict[str, Agent] = {}
        self._by_tool_name: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        """Registra un agente por agent_id y por tool_name."""
        self._by_id[agent.agent_id] = agent
        self._by_tool_name[agent.tool_name] = agent

    def get(self, agent_id: str) -> Optional[Agent]:
        """Devuelve el agente por agent_id o None."""
        return self._by_id.get(agent_id)

    def get_by_tool_name(self, tool_name: str) -> Optional[Agent]:
        """Devuelve el agente cuya tool_name coincide, o None."""
        return self._by_tool_name.get(tool_name)

    def list_agents(self) -> List[Agent]:
        """Lista todos los agentes registrados."""
        return list(self._by_id.values())

    def list_tool_names(self) -> List[str]:
        """Lista los tool_name de todos los agentes (para saber si un paso es un agente)."""
        return list(self._by_tool_name.keys())


# --- Agentes registrados: wrappers sobre las tools existentes ---


class _DelegateToolAgent(Agent):
    """Base para agentes que delegan en una LilithTool existente (DelegateEvaTool, etc.)."""

    def __init__(
        self,
        agent_id: str,
        tool_name: str,
        description: str,
        tool_instance: Any,
    ) -> None:
        self._agent_id = agent_id
        self._tool_name = tool_name
        self._description = description
        self._tool = tool_instance

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        return self._tool.execute(params)


def create_default_agent_registry(base_path: Optional[Path] = None) -> AgentRegistry:
    """
    Crea un AgentRegistry con Eva, Adán, Lucifer, Odín y WebScraper (4.0 Fase 2).
    Usa las tools existentes (DelegateEvaTool, etc.) para no duplicar lógica.
    base_path: opcional, para tools y agentes que lo requieran (config, etc.).
    """
    from .content_cleaner_agent import ContentCleanerAgent
    from .data_structurer_agent import DataStructurerAgent
    from .quality_filter_agent import QualityFilterAgent
    from .tools_v3.agent_tools import (
        DelegateAdanTool,
        DelegateEvaTool,
        DelegateLuciferTool,
        DelegateOdinTool,
    )
    # Archivero removed — pending replacement
    from .web_scraper_agent import WebScraperAgent

    reg = AgentRegistry()
    root = Path(base_path) if base_path else None
    reg.register(
        _DelegateToolAgent(
            "eva",
            "delegate_eva",
            "Eva: análisis, documentación, insights (Grok).",
            DelegateEvaTool(),
        )
    )
    reg.register(
        _DelegateToolAgent(
            "adan",
            "delegate_adan",
            "Adán: código, refactor, tests (Qwen).",
            DelegateAdanTool(),
        )
    )
    reg.register(
        _DelegateToolAgent(
            "lucifer",
            "delegate_lucifer",
            "Lucifer: creativo, conversacional (Kimi).",
            DelegateLuciferTool(),
        )
    )
    reg.register(
        _DelegateToolAgent(
            "odin",
            "delegate_odin",
            "Odín: análisis masivo, contexto 262k (Kimi).",
            DelegateOdinTool(),
        )
    )
# Archivero registration removed
    reg.register(WebScraperAgent(root))
    reg.register(ContentCleanerAgent(root))
    reg.register(QualityFilterAgent(root))
    reg.register(DataStructurerAgent(root))
    return reg
