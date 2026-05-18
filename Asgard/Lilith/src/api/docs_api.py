"""
API endpoints para consulta de documentación.

Archivero agent has been removed. These endpoints now use
a simple file-based fallback until a replacement agent is implemented.

Endpoints:
- POST /api/docs/query  : Consulta la Knowledge Base
- GET  /api/docs/index  : Lista documentos disponibles
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/docs", tags=["documentation"])

# Path a Knowledge Base
# Vault dedicado para documentación — resolved from project root
VAULT_NAME = "docs"
_MODULE_DIR = Path(__file__).resolve().parent
_YGGDRASIL_ROOT = Path(os.environ.get("YGGDRASIL_ROOT", str(_MODULE_DIR.parents[4])))
KB_ROOT = _YGGDRASIL_ROOT / "Svartalfheim" / "Knowledge_Base"


class DocsQueryRequest(BaseModel):
    question: str
    context: Optional[str] = ""


class DocsQueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float


class DocsIndexResponse(BaseModel):
    total_documents: int
    documents: List[Dict]


@router.post("/query", response_model=DocsQueryResponse)
async def query_docs(request: DocsQueryRequest):
    """
    Consulta la Knowledge Base en Svartalfheim.

    NOTE: Archivero agent removed. Returns placeholder response
    until a replacement agent is implemented.
    """
    raise HTTPException(
        status_code=501,
        detail="Archivero agent removed. Docs query endpoint pending replacement agent.",
    )


@router.get("/index", response_model=DocsIndexResponse)
async def get_docs_index():
    """
    Retorna índice de documentos disponibles en la Knowledge Base.
    """
    index_path = KB_ROOT / "index.json"

    if not index_path.exists():
        raise HTTPException(
            status_code=404, detail="Índice no encontrado. Ejecuta indexación primero."
        )

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        return DocsIndexResponse(
            total_documents=index_data.get("total_documents", 0),
            documents=index_data.get("documents", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo índice: {str(e)}")


@router.get("/stats")
async def get_docs_stats():
    """
    Retorna estadísticas de la Knowledge Base.
    """
    stats_path = KB_ROOT / "index_stats.json"

    if not stats_path.exists():
        return {
            "status": "not_indexed",
            "message": "La Knowledge Base no ha sido indexada aún",
        }

    try:
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error leyendo estadísticas: {str(e)}"
        )