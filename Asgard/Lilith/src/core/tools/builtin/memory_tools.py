"""
Lilith 3.0 — Tools de memoria (Fase 3).
SearchSemanticMemoryTool y StoreInteractionTool para el Planner/Orchestrator.
"""
from typing import Any, Dict, Optional

from .protocol import LilithTool, ToolResult


class SearchSemanticMemoryTool(LilithTool):
    """Busca en la memoria semántica (perfil, proyectos, decisiones)."""

    def __init__(self, base_path: Optional[Any] = None):
        self._base_path = base_path

    @property
    def name(self) -> str:
        return "search_semantic_memory"

    def get_description(self) -> str:
        return "Busca información relevante en la memoria semántica a largo plazo (proyectos, decisiones, preferencias del usuario)."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "La consulta de búsqueda."},
            },
            "required": ["query"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        query = (params.get("query") or "").strip()
        if not query:
            return {
                "response": "Indica la consulta para buscar en memoria.",
                "error": True,
            }
        from pathlib import Path

        from ..memory import MemoryManager

        root = Path(self._base_path) if self._base_path is not None else None
        manager = MemoryManager(root)
        results = manager.search_semantic(query)
        if not results:
            return {
                "response": "No hay resultados en la memoria semántica para esa consulta."
            }
        lines = [r.get("text", "").strip() for r in results if r.get("text")]
        response = (
            "\n".join(f"- {t}" for t in lines if t) if lines else "Sin resultados."
        )
        return {"response": response}


class StoreInteractionTool(LilithTool):
    """Guarda el resumen de una interacción en la memoria episódica."""

    def __init__(self, base_path: Optional[Any] = None):
        self._base_path = base_path

    @property
    def name(self) -> str:
        return "store_interaction"

    def get_description(self) -> str:
        return "Guarda el resumen de una interacción completa en la memoria episódica para aprendizaje futuro."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_message": {"type": "string"},
                "plan": {"type": "array", "items": {"type": "object"}},
                "final_response": {"type": "string"},
                "outcome": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["user_message", "plan", "final_response"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        from pathlib import Path

        from ..memory import MemoryManager

        root = Path(self._base_path) if self._base_path is not None else None
        manager = MemoryManager(root)
        manager.store_episodic(
            user_message=params.get("user_message", ""),
            plan=params.get("plan") or [],
            final_response=params.get("final_response", ""),
            outcome=params.get("outcome", "success"),
            user_id=params.get("user_id", ""),
        )
        return {"response": "Interacción guardada."}


class StoreSemanticFactTool(LilithTool):
    """Guarda un hecho en la memoria semántica (minería web: salida de DataStructurerAgent)."""

    def __init__(self, base_path: Optional[Any] = None):
        self._base_path = base_path

    @property
    def name(self) -> str:
        return "store_semantic_fact"

    def get_description(self) -> str:
        return "Guarda el texto indicado como hecho en la memoria semántica (p. ej. resultado estructurado de minería web)."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "Texto del hecho a guardar."},
                "context": {
                    "type": "string",
                    "description": "Alternativa: hecho a guardar (inyectado por el plan).",
                },
                "source_id": {
                    "type": "string",
                    "description": "4.0: ID de origen para chunking/diversidad.",
                },
                "topic": {
                    "type": "string",
                    "description": "4.0: dominio/taxonomía (ej. rol_lore, gamedev) para filtrar búsqueda vectorial.",
                },
            },
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        text = (params.get("fact") or params.get("context") or "").strip()
        if not text:
            return {
                "response": "No hay texto que guardar como hecho (pasa 'fact' o 'context').",
                "error": True,
            }
        source_id = (params.get("source_id") or "").strip() or None
        topic = (params.get("topic") or "").strip() or None
        from pathlib import Path

        from ..memory import MemoryManager

        root = Path(self._base_path) if self._base_path is not None else None
        if not root or not root.exists():
            return {"response": "Ruta del proyecto no configurada.", "error": True}
        try:
            manager = MemoryManager(root)
            manager.add_fact(text, source_id=source_id, topic=topic)
            preview = text[:500] + "…" if len(text) > 500 else text

            # MuninnDB (memoria cognitiva): espejo de hechos semánticos
            try:
                from src.core.memory.muninn_memory import (
                    MuninnMemory,
                    _run_coro_fire_and_forget,
                )

                _run_coro_fire_and_forget(
                    MuninnMemory(root).write_fact(
                        concept=text[:200],
                        content=text,
                        tags=params.get("tags") or [],
                    )
                )
            except Exception:
                pass

            # Grafo (mínimo): guardar relaciones como engrams rel:*
            try:
                from src.core.graph_relations import extract_edges, save_edges_to_muninn
                from src.core.memory.muninn_memory import _run_coro_fire_and_forget

                edges = extract_edges(
                    concept=text[:120],
                    content=text,
                    tags=params.get("tags") or [],
                    url=source_id or "",
                    topic=topic or "",
                )
                _run_coro_fire_and_forget(save_edges_to_muninn(edges, root))
            except Exception:
                pass

            return {"response": f"Hecho guardado en la memoria semántica.\n\n{preview}"}
        except Exception as e:
            return {"response": f"Error al guardar el hecho: {e}", "error": True}
