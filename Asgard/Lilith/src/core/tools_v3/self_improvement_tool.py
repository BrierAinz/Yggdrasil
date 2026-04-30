"""
Lilith 3.0 — Tool de auto-mejora (Fase 4).
Inicia un proceso de auto-análisis sobre la memoria episódica para detectar patrones y sugerir mejoras.
"""
from pathlib import Path
from typing import Any, Dict, Optional

from .protocol import LilithTool, ToolResult


class SelfImproveTool(LilithTool):
    """Ejecuta análisis de la memoria episódica y devuelve sugerencias de patrones fuertes."""

    def __init__(self, base_path: Optional[Path] = None):
        self._base_path = base_path

    @property
    def name(self) -> str:
        return "self_improve"

    def get_description(self) -> str:
        return "Inicia un proceso de auto-análisis para encontrar patrones en las interacciones y sugerir mejoras."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de interacciones a analizar (por defecto 500).",
                },
            },
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        from ..learning import LearningEngine
        from ..memory import MemoryManager

        root = Path(self._base_path) if self._base_path is not None else None
        memory_manager = MemoryManager(root)
        learning_engine = LearningEngine(memory_manager)
        limit = int(params.get("limit", 500)) if params else 500
        limit = max(1, min(limit, 2000))

        suggestions = learning_engine.analyze_and_suggest_patterns(limit=limit)

        if not suggestions:
            response = "No se encontraron patrones lo suficientemente fuertes para sugerir mejoras (umbral: 5 repeticiones). Analiza más interacciones o reduce el umbral en el LearningEngine."
        else:
            response = "Análisis de auto-mejora completado. Sugerencias:\n" + "\n".join(
                f"- {s}" for s in suggestions
            )

        return {"response": response}
