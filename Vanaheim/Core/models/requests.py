"""Modelos de requests para la API de Vanaheim."""
from typing import Any

from pydantic import BaseModel, Field


class InvokeRequest(BaseModel):
    """Request para invocar un agente."""

    task: str = Field(..., description="Tarea a ejecutar")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Contexto adicional"
    )
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    user_id: str | None = None
    channel: str = "api"
    session_id: str | None = None
    stream: bool = False


class StreamRequest(BaseModel):
    """Request para streaming de respuesta."""

    task: str = Field(..., description="Tarea a ejecutar")
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    user_id: str | None = None
    channel: str = "api"
    session_id: str | None = None
