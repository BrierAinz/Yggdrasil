"""
Lilith 3.0 — Store de memoria semántica (Core).
Consulta la memoria semántica existente (Backend.memory.semantic_memory) y expone
resultados en formato lista para el Planner y las tools.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("SemanticStore")


class SemanticStore:
    """
    Acceso a la memoria semántica (perfil, proyectos, decisiones).
    Por ahora delega en Backend.memory.semantic_memory.SemanticMemory.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Busca información relevante en la memoria semántica.
        Devuelve lista de {"text": str}. D.3a: si hay vector store, hechos por similitud a query.
        """
        try:
            from src.core.memory.semantic_memory import SemanticMemory

            sem = SemanticMemory(self.base_path)
            context = sem.get_context_for_prompt(query=query or "")
            if not context or context.strip() == "No hay perfil de usuario cargado.":
                return []
            return [{"text": context.strip()}]
        except Exception as e:
            logger.warning("SemanticStore.search failed: %s", e)
            return []

    def add_fact(self, text: str, source_id: Any = None, topic: Any = None) -> None:
        """Misión 3.2 (D.2): añade un hecho reciente. 4.0: source_id y topic opcionales (diversidad y taxonomía)."""
        if not (text or str(text).strip()):
            return
        try:
            from src.core.memory.semantic_memory import SemanticMemory

            sem = SemanticMemory(self.base_path)
            sem.add_fact(str(text).strip(), source_id=source_id, topic=topic)
        except Exception as e:
            logger.warning("SemanticStore.add_fact failed: %s", e)
