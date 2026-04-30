"""Modelos de datos para agentes en Vanaheim."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Estados posibles de un agente."""

    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class AgentCapabilities(BaseModel):
    """Capacidades de un agente."""

    can_stream: bool = True
    supports_tools: bool = False
    max_context_tokens: int = 8192
    specialties: List[str] = Field(default_factory=list)
    supported_tasks: List[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Configuración de un agente."""

    agent_id: str
    name: str
    description: str
    model: str
    provider: str  # grok, ollama, kimi, venice
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    timeout: int = 120
    temperature: float = 0.7
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    persona_key: Optional[str] = None
    fallback_agent: Optional[str] = None


class AgentInfo(BaseModel):
    """Información completa de un agente registrado."""

    agent_id: str
    name: str
    description: str
    state: AgentState = AgentState.IDLE
    config: AgentConfig
    capabilities: AgentCapabilities
    current_task: Optional[str] = None
    last_heartbeat: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
