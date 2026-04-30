"""Modelos de requests para la API de Vanaheim."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InvokeRequest(BaseModel):
    """Request para invocar un agente."""

    task: str = Field(..., description="Tarea a ejecutar")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Contexto adicional"
    )
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_id: Optional[str] = None
    channel: str = "api"
    session_id: Optional[str] = None
    stream: bool = False


class StreamRequest(BaseModel):
    """Request para streaming de respuesta."""

    task: str = Field(..., description="Tarea a ejecutar")
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_id: Optional[str] = None
    channel: str = "api"
    session_id: Optional[str] = None
