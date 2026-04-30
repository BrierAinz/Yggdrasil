"""
Lilith 3.0 — Modelos de memoria procedimental.
Patrones y recetas aprendidos para uso futuro.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class LearnedPattern:
    """Patrón o receta aprendido (ej. 'si pide X, usar tool Y')."""

    pattern_id: str
    description: str
    trigger: str  # Condición o keywords
    action: Dict[str, Any]  # tool_name, params sugeridos, etc.
    created_at: datetime
    use_count: int = 0
