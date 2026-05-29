"""Persona Engine v2 — YAML templates, dynamic context, and persona switching."""

from .engine import PersonaEngine
from .models import PersonaContext, PersonaSwitchResult, PersonaTemplate
from .switcher import PersonaSwitcher


__all__ = [
    "PersonaContext",
    "PersonaEngine",
    "PersonaSwitchResult",
    "PersonaSwitcher",
    "PersonaTemplate",
]
