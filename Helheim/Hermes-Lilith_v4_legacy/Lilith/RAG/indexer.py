"""
File Indexer
============
Indexador de archivos para RAG.
"""
from pathlib import Path
from typing import Dict, List, Optional

from .rag_engine import RAGEngine, get_rag_engine


class FileIndexer:
    """
    Indexador simplificado para archivos.
    """

    def __init__(self, rag_engine: Optional[RAGEngine] = None):
        self.rag = rag_engine or get_rag_engine()

    def index_project(self, project_path: str) -> Dict:
        """Indexa un proyecto completo."""
        return self.rag.index_directory(project_path, recursive=True)

    def index_codebase(self, paths: List[str]) -> Dict:
        """Indexa múltiples rutas."""
        stats = {"indexed": 0, "skipped": 0, "errors": 0}

        for path in paths:
            result = self.rag.index_directory(path, recursive=True)
            stats["indexed"] += result["indexed"]
            stats["skipped"] += result["skipped"]
            stats["errors"] += result["errors"]

        return stats

    def index_lilith(self) -> Dict:
        """Indexa el propio proyecto Lilith."""
        lilith_path = Path(__file__).parent.parent.parent
        return self.rag.index_directory(str(lilith_path), recursive=True)

    def search_context(self, query: str, max_chars: int = 1500) -> str:
        """Obtiene contexto para una query."""
        return self.rag.get_context_for_query(query, max_chars)
