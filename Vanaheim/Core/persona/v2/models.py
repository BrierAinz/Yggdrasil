"""Pydantic models for Persona Engine v2."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PersonaIdentity(BaseModel):
    """Identity definition for a persona."""

    name: str = ""
    role: str = ""
    description: str = ""
    tone: str = ""
    vocabulary: str = ""
    rules: list[str] = Field(default_factory=list)
    format_spec: str = ""


class PersonaContext(BaseModel):
    """Runtime context that modifies persona behaviour."""

    user_mood: str = "neutral"
    project_type: str = ""
    time_of_day: str = ""
    complexity: str = "normal"
    language: str = "es"


class PersonaTemplate(BaseModel):
    """A complete persona template loaded from YAML."""

    id: str
    version: str = "1.0"
    identity: PersonaIdentity = Field(default_factory=PersonaIdentity)
    context_modifiers: dict[str, dict] = Field(default_factory=dict)
    inherits: str | None = None
    metadata: dict = Field(default_factory=dict)


class PersonaSwitchResult(BaseModel):
    """Result of a persona switch operation."""

    template_id: str
    system_prompt: str
    context_applied: PersonaContext
    timestamp: float
