"""Modelos de datos para agentes en Vanaheim."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentState(StrEnum):
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
    specialties: list[str] = Field(default_factory=list)
    supported_tasks: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Configuración de un agente."""

    agent_id: str
    name: str
    description: str
    model: str
    provider: str  # grok, ollama, kimi, venice
    base_url: str | None = None
    api_key_env: str | None = None
    timeout: int = 120
    temperature: float = 0.7
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    persona_key: str | None = None
    fallback_agent: str | None = None


class AgentInfo(BaseModel):
    """Información completa de un agente registrado."""

    agent_id: str
    name: str
    description: str
    state: AgentState = AgentState.IDLE
    config: AgentConfig
    capabilities: AgentCapabilities
    current_task: str | None = None
    last_heartbeat: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
