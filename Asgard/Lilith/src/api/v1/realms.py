"""
Realms API - Dashboard de Reinos de Yggdrasil (Ojo de Hrafnsmál)

Telemetría unificada de Asgard y Vanaheim para el dashboard de reinos.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/realms", tags=["realms"])
logger = logging.getLogger(__name__)

BASE_PATH = Path(__file__).resolve().parent.parent.parent


@router.get("/")
async def get_realms_summary():
    """Resumen unificado de Asgard + Vanaheim."""
    try:
        from src.api.asgard_api import get_ecosystem_status

        asgard_data = await get_ecosystem_status()
    except Exception as e:
        logger.warning("RealmsAPI: fallback asgard status: %s", e)
        asgard_data = {"error": str(e)}

    try:
        from src.core.agent_metrics import get_metrics

        vanaheim_agents = get_metrics().get_stats_with_status()
    except Exception as e:
        logger.warning("RealmsAPI: fallback vanaheim status: %s", e)
        vanaheim_agents = {"error": str(e)}

    return {
        "asgard": asgard_data,
        "vanaheim": vanaheim_agents,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/agents")
async def get_realm_agents():
    """Lista de agentes vanir con estado live."""
    try:
        from src.core.agent_metrics import get_metrics
        from src.core.agent_registry import create_default_agent_registry

        registry = create_default_agent_registry(BASE_PATH)
        metrics = get_metrics()
        agents = []
        for agent in registry.list_agents():
            tool = f"delegate_{agent.agent_id}"
            stats = metrics.get_stats_with_status(tool)
            agents.append(
                {
                    "agent_id": agent.agent_id,
                    "description": agent.description,
                    "status": stats.get("status", "idle"),
                    "active_calls": stats.get("active_calls", 0),
                    **stats,
                }
            )
        return {"agents": agents, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.exception("RealmsAPI agents error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_name}")
async def get_realm_agent_detail(agent_name: str):
    """Detalle histórico de un agente vanir."""
    try:
        from src.core.agent_metrics import get_metrics
        from src.core.analytics import get_analytics_manager
        from src.core.memory.legacy_adapter import EpisodicStore

        tool_name = f"delegate_{agent_name}"
        metrics = get_metrics().get_stats_with_status(tool_name)
        analytics = get_analytics_manager().get_agent_stats(agent_name, days=7)
        episodes = EpisodicStore(BASE_PATH).search(tool_used=tool_name, limit=10)

        return {
            "agent_id": agent_name,
            "metrics": metrics,
            "analytics": analytics,
            "recent_episodes": episodes,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.exception("RealmsAPI agent detail error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traffic")
async def get_realm_traffic():
    """Datos agregados para diagrama Sankey de tráfico."""
    try:
        from src.core.traffic_tracker import get_traffic_tracker

        data = get_traffic_tracker().get_sankey_data(window_seconds=300)
        return {"data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.exception("RealmsAPI traffic error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_realm_metrics():
    """Métricas Prometheus-like de agentes vanir."""
    try:
        from src.core.agent_metrics import get_metrics
        from src.core.performance.monitor import get_performance_monitor

        lines: list[str] = []
        stats = get_metrics().get_stats_with_status()
        for tool in stats.get("tools", []):
            name = tool["tool"]
            lines.append(f'agent_calls_total{{agent="{name}"}} {tool.get("calls", 0)}')
            lines.append(
                f'agent_latency_avg_ms{{agent="{name}"}} {tool.get("avg_latency_ms", 0)}'
            )
            status_val = (
                1
                if tool.get("status") == "idle"
                else 2
                if tool.get("status") == "processing"
                else 0
            )
            lines.append(f'agent_status{{agent="{name}"}} {status_val}')
            lines.append(
                f'agent_active_calls{{agent="{name}"}} {tool.get("active_calls", 0)}'
            )

        try:
            pm = get_performance_monitor()
            pstats = pm.get_stats()
            lines.append(f'system_active_requests {pstats.get("active_requests", 0)}')
            lines.append(f'system_total_requests {pstats.get("total_requests", 0)}')
        except Exception:
            pass

        return PlainTextResponse(
            content="\n".join(lines) + "\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    except Exception as e:
        logger.exception("RealmsAPI metrics error")
        raise HTTPException(status_code=500, detail=str(e))
