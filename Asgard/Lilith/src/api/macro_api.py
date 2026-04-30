"""
Lilith v5.2 — Macro API
=======================

API REST para gestión de macros custom y aprendizaje automático.

Endpoints:
- POST /macros/suggest - Analizar historial y sugerir macros
- POST /macros/create - Crear macro custom
- POST /macros/accept_suggestion - Aceptar sugerencia y crear macro
- GET /macros/list - Listar todas las macros (custom + predefinidas)
- DELETE /macros/{macro_name} - Eliminar macro custom
- GET /macros/stats - Estadísticas de uso
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger("lilith.macro_api")
router = APIRouter(prefix="/api/macros", tags=["macros"])


# =============================================================================
# Helpers
# =============================================================================


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _internal_token() -> str:
    import os

    return (os.getenv("LILITH_INTERNAL_TOKEN", "") or "").strip()


def _verify(request: Request):
    """Verifica el token interno."""
    token = _internal_token()
    got = (request.headers.get("X-Lilith-Token") or "").strip()
    if not token or got != token:
        raise HTTPException(status_code=403, detail="Token inválido.")


def _json_response(data: dict, status_code: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
    )


def _get_macro_manager():
    """Obtiene instancia del CustomMacroManager."""
    from src.core.custom_macro_manager import get_custom_macro_manager

    return get_custom_macro_manager(base_path=_project_root())


def _get_predefined_macros() -> Dict[str, Any]:
    """Obtiene macros predefinidas del sistema."""
    try:
        from src.core.pc_macro_engine import MacroLibrary

        library = MacroLibrary()
        return library.list_macros()
    except Exception as e:
        logger.warning("[MacroAPI] Error cargando macros predefinidas: %s", e)
        return {}


# =============================================================================
# Pydantic Models
# =============================================================================


class SuggestMacrosRequest(BaseModel):
    """Request para sugerir macros desde historial."""

    user_id: Optional[str] = Field(
        default=None, description="Filtrar por usuario específico"
    )
    min_frequency: int = Field(
        default=3, ge=2, le=10, description="Mínimo de ocurrencias para sugerir"
    )
    similarity_threshold: float = Field(
        default=0.8, ge=0.5, le=1.0, description="Umbral de similitud"
    )
    hours_window: int = Field(
        default=168, ge=24, le=720, description="Ventana de tiempo en horas"
    )


class SuggestMacrosResponse(BaseModel):
    """Response con sugerencias de macros."""

    suggestions: List[Dict[str, Any]]
    total_found: int
    high_confidence_count: int


class CreateMacroRequest(BaseModel):
    """Request para crear macro custom."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre único de la macro"
    )
    description: str = Field(
        ..., min_length=1, max_length=500, description="Descripción legible"
    )
    operations: List[Dict[str, Any]] = Field(..., description="Lista de operaciones")
    user_id: str = Field(..., description="ID del usuario creador")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Definición de parámetros"
    )
    tags: Optional[List[str]] = Field(default=None, description="Tags opcionales")


class CreateMacroResponse(BaseModel):
    """Response de creación de macro."""

    success: bool
    macro: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AcceptSuggestionRequest(BaseModel):
    """Request para aceptar una sugerencia y crear macro."""

    suggestion: Dict[str, Any] = Field(..., description="Sugerencia del MacroLearner")
    user_id: str = Field(..., description="ID del usuario")
    custom_name: Optional[str] = Field(
        default=None, description="Nombre personalizado opcional"
    )


class ListMacrosResponse(BaseModel):
    """Response con lista de macros."""

    custom_macros: List[Dict[str, Any]]
    predefined_macros: List[Dict[str, Any]]
    total_custom: int
    total_predefined: int


class MacroStatsResponse(BaseModel):
    """Response con estadísticas de macros."""

    total_macros: int
    active_macros: int
    inactive_macros: int
    by_source: Dict[str, int]
    by_user: Dict[str, int]
    total_usage: int


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/suggest", response_model=SuggestMacrosResponse)
async def suggest_macros(request: Request) -> Response:
    """
    Analiza el historial de operaciones y sugiere macros basadas en patrones detectados.

    Requiere episodios en el body o usa el EpisodeStore si no se proporcionan.
    """
    _verify(request)

    try:
        data = await request.json()
    except Exception as e:
        return _json_response({"error": f"JSON inválido: {e}"}, status_code=400)

    req = SuggestMacrosRequest(**data)

    try:
        # Importar y configurar MacroLearner
        from src.core.macro_learner import MacroLearner

        learner = MacroLearner(
            similarity_threshold=req.similarity_threshold,
            min_frequency=req.min_frequency,
            window_hours=req.hours_window,
        )

        # Obtener episodios (del body o del store)
        episodes_data = data.get("episodes", [])

        if episodes_data:
            from src.core.macro_learner import Episode

            episodes = [
                Episode(
                    id=ep.get("id", f"ep_{i}"),
                    user_id=ep.get("user_id", "unknown"),
                    tool=ep.get("tool", "pc_operation"),
                    operation=ep.get("operation", ""),
                    params=ep.get("params", {}),
                    timestamp=ep.get("timestamp", 0.0),
                    context=ep.get("context", {}),
                )
                for i, ep in enumerate(episodes_data)
            ]
        else:
            # Usar EpisodeStore si existe
            try:
                from src.core.macro_learner import EpisodeStore

                store = EpisodeStore(_project_root())
                episodes = store.get_recent(
                    user_id=req.user_id,
                    hours=req.hours_window,
                )
            except Exception as e:
                logger.warning("[MacroAPI] Error accediendo EpisodeStore: %s", e)
                episodes = []

        if not episodes:
            return _json_response(
                {
                    "suggestions": [],
                    "total_found": 0,
                    "high_confidence_count": 0,
                }
            )

        # Analizar y generar sugerencias
        suggestions = await learner.analyze_recent_history(episodes, req.user_id)

        # Filtrar alta confianza
        high_confidence = learner.filter_high_confidence(suggestions, threshold=0.7)

        return _json_response(
            {
                "suggestions": [s.to_dict() for s in suggestions],
                "total_found": len(suggestions),
                "high_confidence_count": len(high_confidence),
            }
        )

    except Exception as e:
        logger.exception("[MacroAPI] Error sugiriendo macros")
        return _json_response({"error": str(e)}, status_code=500)


@router.post("/create", response_model=CreateMacroResponse)
async def create_macro(request: Request) -> Response:
    """
    Crea una nueva macro custom.

    Valida operaciones permitidas, límites por usuario, y persiste la macro.
    """
    _verify(request)

    try:
        data = await request.json()
    except Exception as e:
        return _json_response({"error": f"JSON inválido: {e}"}, status_code=400)

    try:
        req = CreateMacroRequest(**data)
    except Exception as e:
        return _json_response({"error": f"Datos inválidos: {e}"}, status_code=400)

    try:
        manager = _get_macro_manager()

        macro = await manager.create_macro(
            name=req.name,
            description=req.description,
            operations=req.operations,
            user_id=req.user_id,
            params=req.params,
            tags=req.tags,
            source="manual",
        )

        return _json_response(
            {
                "success": True,
                "macro": macro.to_dict(),
            }
        )

    except ValueError as e:
        return _json_response(
            {
                "success": False,
                "error": str(e),
            },
            status_code=400,
        )
    except Exception as e:
        logger.exception("[MacroAPI] Error creando macro")
        return _json_response({"error": str(e)}, status_code=500)


@router.post("/accept_suggestion", response_model=CreateMacroResponse)
async def accept_suggestion(request: Request) -> Response:
    """
    Acepta una sugerencia del MacroLearner y crea la macro.

    Similar a /create pero usando una sugerencia pre-generada.
    """
    _verify(request)

    try:
        data = await request.json()
    except Exception as e:
        return _json_response({"error": f"JSON inválido: {e}"}, status_code=400)

    try:
        req = AcceptSuggestionRequest(**data)
    except Exception as e:
        return _json_response({"error": f"Datos inválidos: {e}"}, status_code=400)

    try:
        manager = _get_macro_manager()

        macro = await manager.create_from_suggestion(
            suggestion=req.suggestion,
            user_id=req.user_id,
            custom_name=req.custom_name,
        )

        return _json_response(
            {
                "success": True,
                "macro": macro.to_dict(),
            }
        )

    except ValueError as e:
        return _json_response(
            {
                "success": False,
                "error": str(e),
            },
            status_code=400,
        )
    except Exception as e:
        logger.exception("[MacroAPI] Error aceptando sugerencia")
        return _json_response({"error": str(e)}, status_code=500)


@router.get("/list")
async def list_macros(
    request: Request,
    user_id: Optional[str] = None,
    include_inactive: bool = False,
    include_predefined: bool = True,
) -> Response:
    """
    Lista todas las macros disponibles.

    Args:
        user_id: Filtrar por usuario (None = todos)
        include_inactive: Incluir macros desactivadas
        include_predefined: Incluir macros del sistema
    """
    _verify(request)

    try:
        manager = _get_macro_manager()

        # Obtener macros custom
        custom = manager.get_all_macros(
            user_id=user_id,
            include_inactive=include_inactive,
        )

        response = {
            "custom_macros": [m.to_dict() for m in custom],
            "total_custom": len(custom),
        }

        # Incluir predefinidas si se solicita
        if include_predefined:
            predefined = _get_predefined_macros()
            response["predefined_macros"] = [
                {"name": name, **data} for name, data in predefined.items()
            ]
            response["total_predefined"] = len(predefined)

        return _json_response(response)

    except Exception as e:
        logger.exception("[MacroAPI] Error listando macros")
        return _json_response({"error": str(e)}, status_code=500)


@router.delete("/{macro_name}")
async def delete_macro(macro_name: str, request: Request) -> Response:
    """
    Elimina una macro custom.

    Solo el creador o admin pueden eliminar.
    """
    _verify(request)

    try:
        data = await request.json()
    except Exception:
        data = {}

    user_id = str(data.get("user_id", ""))

    if not user_id:
        return _json_response(
            {"error": "user_id requerido en el body"}, status_code=400
        )

    try:
        manager = _get_macro_manager()

        deleted = await manager.delete_macro(macro_name, user_id)

        if deleted:
            return _json_response(
                {
                    "success": True,
                    "message": f"Macro '{macro_name}' eliminada",
                }
            )
        else:
            return _json_response(
                {
                    "success": False,
                    "error": f"Macro '{macro_name}' no encontrada",
                },
                status_code=404,
            )

    except ValueError as e:
        return _json_response(
            {
                "success": False,
                "error": str(e),
            },
            status_code=403,
        )
    except Exception as e:
        logger.exception("[MacroAPI] Error eliminando macro")
        return _json_response({"error": str(e)}, status_code=500)


@router.get("/stats")
async def get_stats(request: Request) -> Response:
    """Obtiene estadísticas de uso de macros custom."""
    _verify(request)

    try:
        manager = _get_macro_manager()
        stats = manager.get_stats()

        return _json_response(stats)

    except Exception as e:
        logger.exception("[MacroAPI] Error obteniendo estadísticas")
        return _json_response({"error": str(e)}, status_code=500)


@router.post("/{macro_name}/execute")
async def execute_macro(macro_name: str, request: Request) -> Response:
    """
    Ejecuta una macro (custom o predefinida).

    Requiere confirmación si la macro lo indica.
    """
    _verify(request)

    try:
        data = await request.json()
    except Exception:
        data = {}

    user_id = str(data.get("user_id", ""))
    params = data.get("params", {})
    confirmed = data.get("confirmed", False)

    try:
        manager = _get_macro_manager()

        # Buscar en custom primero
        custom_macro = manager.get_macro(macro_name)

        if custom_macro:
            macro = custom_macro.to_macro()
        else:
            # Buscar en predefinidas
            from src.core.pc_macro_engine import MacroLibrary

            library = MacroLibrary()
            macro = library.get_macro(macro_name)

            if not macro:
                return _json_response(
                    {
                        "error": f"Macro '{macro_name}' no encontrada",
                    },
                    status_code=404,
                )

        # Verificar si requiere confirmación
        if macro.requires_confirmation and not confirmed:
            return _json_response(
                {
                    "requires_confirmation": True,
                    "macro_name": macro_name,
                    "description": macro.description,
                    "steps_count": len(macro.steps),
                    "message": "Esta macro requiere confirmación antes de ejecutarse",
                }
            )

        # Ejecutar la macro
        from src.core.pc_macro_engine import PCMacroEngine

        engine = PCMacroEngine(_project_root())

        result = await engine.execute_macro(macro, params)

        # Registrar uso si es custom
        if custom_macro:
            await manager.record_usage(macro_name)

        return _json_response(
            {
                "success": result.success,
                "message": result.message,
                "results": result.results,
                "execution_time_ms": result.execution_time_ms,
            }
        )

    except Exception as e:
        logger.exception("[MacroAPI] Error ejecutando macro")
        return _json_response({"error": str(e)}, status_code=500)
