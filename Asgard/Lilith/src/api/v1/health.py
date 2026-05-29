"""
Lilith 4.2.4 — Sistema de Health Checks Unificado.
Endpoint GET /health con diagnóstico completo de subsistemas.
Código 200 = healthy, 207 = degraded, 503 = unhealthy.

v4.2.4: Integrado HealthMonitor con checks de APIs externas,
        recursos del sistema y variables de entorno.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("lilith.api.health")

router = APIRouter(tags=["health"])

_BASE_PATH = Path(__file__).resolve().parent.parent.parent

# Subsistemas críticos (su fallo → 503)
_CRITICAL = {"muninn", "schedulers", "environment"}


# ── Checks individuales (legacy) ─────────────────────────────────────────────


async def _check_muninn() -> Dict[str, Any]:
    try:
        from src.core.memory.muninn_memory import MuninnMemory

        start = time.perf_counter()
        muninn = MuninnMemory(_BASE_PATH)
        if not muninn.enabled:
            return {"status": "disabled", "latency_ms": 0}
        # Query simple al vault lilith
        results = await asyncio.wait_for(
            muninn.search("health_check_ping", vault="lilith", limit=1),
            timeout=3.0,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.debug("[HealthCheck] muninn: healthy (%dms)", latency_ms)
        return {"status": "healthy", "latency_ms": latency_ms}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "timeout >3s"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_schedulers() -> Dict[str, Any]:
    try:
        from src.api.dependencies import get_orchestrator

        orch = get_orchestrator()
        scheduler = getattr(orch, "task_scheduler", None) or getattr(
            orch, "scheduler", None
        )
        if scheduler is None:
            # Intentar obtenerlo desde el estado global de la app
            return {"status": "unknown", "note": "scheduler no accesible"}
        jobs_json = scheduler.list_jobs()
        import json as _json

        jobs_data = _json.loads(jobs_json)
        active_jobs = jobs_data.get("count", 0)
        return {"status": "healthy", "active_jobs": active_jobs}
    except Exception as e:
        return {"status": "degraded", "error": str(e)[:100]}


async def _check_discord_bot() -> Dict[str, Any]:
    try:
        from src.api.dependencies import get_orchestrator

        orch = get_orchestrator()
        if orch is None:
            return {"status": "unhealthy", "error": "orchestrator no disponible"}
        return {"status": "healthy", "orchestrator": "up"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)[:100]}


async def _check_telegram_bot() -> Dict[str, Any]:
    try:
        from src.api.v1.bots.telegram import get_bot_status

        status = get_bot_status()
        if status:
            return {"status": "healthy"}
        return {"status": "degraded", "note": "bot inactivo"}
    except Exception:
        return {"status": "unknown", "note": "telegram_api no cargado"}


async def _check_episodic_db() -> Dict[str, Any]:
    try:
        start = time.perf_counter()
        log_path = _BASE_PATH / "Data" / "episodic_log.jsonl"
        if not log_path.exists():
            return {"status": "healthy", "note": "log vacío (primer arranque)"}
        size_bytes = log_path.stat().st_size
        # Contar líneas de forma rápida (últimas 10)
        count = 0
        with open(log_path, "rb") as f:
            # Contar newlines rápidamente
            count = sum(1 for _ in f)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "status": "healthy",
            "entries": count,
            "size_bytes": size_bytes,
            "query_time_ms": latency_ms,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


# ── Nuevos checks v4.2.4 (HealthMonitor Integration) ─────────────────────────


async def _check_kimi_api() -> Dict[str, Any]:
    """Verificar disponibilidad de Kimi API (Crystal)."""
    try:
        from src.core.health_monitor import HealthMonitor

        result = await HealthMonitor.check_kimi_api()
        return {
            "status": result.status.value,
            "latency_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_system_resources() -> Dict[str, Any]:
    """Verificar CPU y RAM."""
    try:
        from src.core.health_monitor import HealthMonitor

        result = await HealthMonitor.check_system_resources()
        return {
            "status": result.status.value,
            "latency_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_disk_space() -> Dict[str, Any]:
    """Verificar espacio en disco."""
    try:
        from src.core.health_monitor import HealthMonitor

        result = await HealthMonitor.check_disk_space()
        return {
            "status": result.status.value,
            "latency_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_environment() -> Dict[str, Any]:
    """Verificar variables de entorno críticas."""
    try:
        from src.core.health_monitor import HealthMonitor

        result = await HealthMonitor.check_environment()
        return {
            "status": result.status.value,
            "latency_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)[:100]}


async def _check_openrouter_api() -> Dict[str, Any]:
    """Verificar OpenRouter (fallback)."""
    try:
        from src.core.health_monitor import HealthMonitor

        result = await HealthMonitor.check_openrouter_api()
        return {
            "status": result.status.value,
            "latency_ms": result.response_time_ms,
            "message": result.message,
            "details": result.details,
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)[:100]}


# ── Endpoint principal ─────────────────────────────────────────────────────────


@router.get("/health")
async def health_check():
    """
    Diagnóstico completo de subsistemas de Lilith.
    - 200: todos healthy
    - 207: algunos degraded
    - 503: subsistemas críticos caídos
    """
    start = time.perf_counter()

    # Ejecutar todos los checks en paralelo
    results = await asyncio.gather(
        _check_muninn(),
        _check_schedulers(),
        _check_discord_bot(),
        _check_telegram_bot(),
        _check_episodic_db(),
        _check_kimi_api(),
        _check_system_resources(),
        _check_disk_space(),
        _check_environment(),
        _check_openrouter_api(),
        return_exceptions=True,
    )

    subsystems = {}
    check_names = [
        "muninn",
        "schedulers",
        "discord_bot",
        "telegram_bot",
        "episodic_db",
        "kimi_api",
        "system_resources",
        "disk_space",
        "environment",
        "openrouter_api",
    ]
    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            subsystems[name] = {"status": "unhealthy", "error": str(result)[:100]}
        else:
            subsystems[name] = result

    # Actualizar métricas
    try:
        from src.telemetry.metrics import set_subsystem_health

        for name, data in subsystems.items():
            set_subsystem_health(name, data.get("status") == "healthy")
    except Exception:
        pass

    # Calcular estado global
    statuses = [v.get("status", "unknown") for v in subsystems.values()]
    critical_healthy = all(
        subsystems.get(c, {}).get("status") in ("healthy", "disabled", "unknown")
        for c in _CRITICAL
    )

    if all(s in ("healthy", "disabled", "unknown") for s in statuses):
        overall = "healthy"
        http_code = 200
    elif not critical_healthy or any(
        s == "unhealthy"
        for s in [subsystems.get(c, {}).get("status") for c in _CRITICAL]
    ):
        overall = "unhealthy"
        http_code = 503
    else:
        overall = "degraded"
        http_code = 207

    total_ms = int((time.perf_counter() - start) * 1000)
    logger.info("[HealthCheck] status=%s total_ms=%d", overall, total_ms)

    body = {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_latency_ms": total_ms,
        "lilith_version": "4.2.4",
        "subsystems": subsystems,
    }
    return JSONResponse(content=body, status_code=http_code)


@router.get("/health/subsystem/{name}")
async def health_subsystem(name: str):
    """Check de un subsistema individual."""
    checks = {
        "muninn": _check_muninn,
        "schedulers": _check_schedulers,
        "discord_bot": _check_discord_bot,
        "telegram_bot": _check_telegram_bot,
        "episodic_db": _check_episodic_db,
        "kimi_api": _check_kimi_api,
        "system_resources": _check_system_resources,
        "disk_space": _check_disk_space,
        "environment": _check_environment,
        "openrouter_api": _check_openrouter_api,
    }
    fn = checks.get(name)
    if fn is None:
        return JSONResponse(
            {"error": f"Subsistema desconocido: {name}"}, status_code=404
        )
    result = await fn()
    code = 200 if result.get("status") in ("healthy", "disabled", "unknown") else 503
    return JSONResponse(result, status_code=code)


@router.get("/health/extended")
async def health_extended():
    """
    Health check extendido usando HealthMonitor completo.
    Incluye todos los checks detallados con metadata.
    """
    try:
        from src.core.health_monitor import HealthMonitor

        system_health = await HealthMonitor.check_all()

        body = {
            "status": system_health.overall_status.value,
            "timestamp": system_health.timestamp.isoformat(),
            "metadata": system_health.metadata,
            "checks": [c.to_dict() for c in system_health.checks],
        }

        # Determinar código HTTP
        if system_health.overall_status.value == "healthy":
            code = 200
        elif system_health.overall_status.value == "degraded":
            code = 207
        else:
            code = 503

        return JSONResponse(content=body, status_code=code)
    except Exception as e:
        logger.error("[HealthCheck] Error en health_extended: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
