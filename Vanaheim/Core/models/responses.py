"""Modelos de respuestas para la API de Vanaheim."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Respuesta de health check."""

    agent_id: str
    name: str
    state: str
    available: bool
    model: str
    provider: str
    version: str = "1.0.0"


class InvokeResponse(BaseModel):
    """Respuesta de invocación síncrona."""

    agent_id: str
    result: str
    tokens_used: int | None = None
    execution_time_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Respuesta de error."""

    error: str
    detail: str | None = None
    agent_id: str | None = None
