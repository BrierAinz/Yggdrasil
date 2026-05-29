"""
Lilith 3.0 — Modelos de memoria episódica.
Registro de interacciones para aprendizaje y análisis.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class InteractionLog:
    """Registro de una interacción completa (mensaje → plan → respuesta)."""

    timestamp: datetime
    user_id: str
    message: str
    plan: List[Dict[str, Any]]  # Lista de pasos serializados
    final_response: str
    outcome: str  # "success", "failure", "user_corrected"
