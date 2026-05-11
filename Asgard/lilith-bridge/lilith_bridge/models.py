"""Pydantic models for the Hermes Bridge API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Inbound: Hermes → Yggdrasil ─────────────────────────────────────


class BridgeChatRequest(BaseModel):
    """A chat message from Hermes to Lilith."""

    message: str
    session_id: str | None = None
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeChatResponse(BaseModel):
    """Lilith's response back to Hermes."""

    response: str
    session_id: str
    latency_ms: float
    tools_used: list[str] = Field(default_factory=list)
    usage: dict[str, int] | None = None


class BridgeMemoryQuery(BaseModel):
    """Query Lilith's memory store."""

    query: str
    k: int = 5


class BridgeMemoryStore(BaseModel):
    """Store something in Lilith's memory."""

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeSkillSearch(BaseModel):
    """Search Lilith's skill knowledge base."""

    query: str
    category: str | None = None
    limit: int = 10


# ── Outbound: Yggdrasil → Hermes ────────────────────────────────────


class HermesChatRequest(BaseModel):
    """Delegate a message to Hermes Agent."""

    message: str
    context: str | None = None
    toolsets: list[str] | None = None
    model: str | None = None
    stream: bool = False


class HermesChatResponse(BaseModel):
    """Hermes Agent's response."""

    response: str
    model: str = ""
    usage: dict[str, int] | None = None
    tools_used: list[str] = Field(default_factory=list)


class HermesToolExecute(BaseModel):
    """Execute a tool via Hermes Agent."""

    tool: str
    params: dict[str, Any] = Field(default_factory=dict)


class HermesToolResult(BaseModel):
    """Result from a Hermes tool execution."""

    tool: str
    success: bool
    result: Any = None
    error: str | None = None


# ── Shared ──────────────────────────────────────────────────────────


class BridgeHealth(BaseModel):
    """Health check response."""

    status: str = "healthy"
    bridge_version: str = "1.0.0"
    lilith_engine: bool = False
    hermes_connected: bool = False
    memory_available: bool = False
    skills_loaded: int = 0
    uptime_seconds: float = 0.0
