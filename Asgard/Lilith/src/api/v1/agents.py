"""
API — Endpoints de métricas y salud de agentes.
GET /api/agents/health — Resumen de salud de todos los agentes/tools.
GET /api/agents/stats  — Estadísticas detalladas.
"""
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter(prefix="/api/agents", tags=["agents"])
logger = logging.getLogger("lilith.agents_api")


def _json_response(data: dict, status_code: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
    )


@router.get("/health")
async def agents_health(request: Request) -> Response:
    """Resumen de salud: herramientas degradadas, agentes locales y Vanaheim."""
    try:
        from src.core.agent_metrics import get_metrics

        result = {"ok": True, **get_metrics().health_summary()}

        # Parte 5: Health check específico para Shalltear (Venice API)
        try:
            from src.core.agents.panteon.shalltear import ShalltearAgent

            shalltear = ShalltearAgent()
            result["shalltear"] = {
                "available": shalltear.is_available(),
                "backend": "venice",
                "model": "llama-3.3-70b",
            }
        except Exception as se:
            result["shalltear"] = {"available": False, "error": str(se)}

        # Vanaheim integration: health check del servicio remoto
        try:
            from src.core.vanaheim_client import get_vanaheim_client

            vanaheim = get_vanaheim_client()
            vanaheim_health = await vanaheim.health()
            result["vanaheim"] = {
                "available": vanaheim_health.get("status") == "healthy",
                "agents_registered": vanaheim_health.get("agents_registered", 0),
                "agents_available": vanaheim_health.get("agents_available", 0),
                "url": vanaheim.base_url,
            }

            # Si Vanaheim está disponible, incluir estado de sus agentes
            if vanaheim_health.get("status") == "healthy":
                vanaheim_agents = await vanaheim.list_agents()
                result["vanaheim_agents"] = {
                    a["agent_id"]: {
                        "available": a.get("state") in ("idle", "busy"),
                        "model": a.get("model"),
                        "provider": a.get("provider"),
                    }
                    for a in vanaheim_agents
                }
        except Exception as ve:
            result["vanaheim"] = {"available": False, "error": str(ve)}

        return _json_response(result)
    except Exception as e:
        return _json_response({"ok": False, "error": str(e)}, 500)


@router.get("/stats")
async def agents_stats(request: Request) -> Response:
    """Estadísticas detalladas de todas las herramientas."""
    try:
        from src.core.agent_metrics import get_metrics

        return _json_response({"ok": True, **get_metrics().get_stats()})
    except Exception as e:
        return _json_response({"ok": False, "error": str(e)}, 500)


@router.get("/stats/{tool_name}")
async def agent_stats_tool(tool_name: str, request: Request) -> Response:
    """Estadísticas de una herramienta concreta."""
    try:
        from src.core.agent_metrics import get_metrics

        return _json_response({"ok": True, **get_metrics().get_stats(tool_name)})
    except Exception as e:
        return _json_response({"ok": False, "error": str(e)}, 500)
