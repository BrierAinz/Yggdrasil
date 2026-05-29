"""
Fase 4.2 — Cuaderno de Lilith: notebook_add, notebook_search, notebook_set_important.
JSONL en Data/lilith_notebook.jsonl; ítems important=true sincronizados a Muninn (vault lilith).
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from .store import NotebookStore

_DEFAULT_STORE: Optional[NotebookStore] = None


def get_notebook_store(base_path: Optional[Path] = None) -> NotebookStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = NotebookStore(base_path)
    elif base_path is not None:
        _DEFAULT_STORE = NotebookStore(base_path)
    return _DEFAULT_STORE


def notebook_add(
    content: str,
    important: bool,
    source: str = "",
    source_detail: str = "",
    tags: Optional[List[str]] = None,
    base_path: Optional[Path] = None,
) -> str:
    """Añade entrada al cuaderno. Si important=true, sincroniza a Muninn. Devuelve el id de la entrada."""
    store = get_notebook_store(base_path)
    return store.add(
        content=content,
        important=important,
        source=source,
        source_detail=source_detail,
        tags=tags,
    )


def notebook_search(
    query: Optional[str] = None,
    important_only: bool = False,
    source: Optional[str] = None,
    limit: int = 50,
    base_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Busca en el cuaderno por texto y/o important/source. Devuelve lista de entradas."""
    store = get_notebook_store(base_path)
    return store.search(
        query=query,
        important_only=important_only,
        source=source,
        limit=limit,
    )


def notebook_set_important(
    entry_id: str,
    important: bool,
    base_path: Optional[Path] = None,
) -> bool:
    """Cambia la marca important de una entrada. Si pasa a false, borra el engrama en Muninn."""
    store = get_notebook_store(base_path)
    return store.set_important(entry_id, important)
