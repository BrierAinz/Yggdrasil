"""
APIs de telemetría para Asgard Command Center.
Dashboard web en tiempo real del ecosistema Yggdrasil.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/asgard", tags=["asgard"])

# Ruta raíz de Yggdrasil
YGGDRASIL_ROOT = Path("D:/Proyectos/Yggdrasil")


@router.get("/ecosystem/status")
async def get_ecosystem_status():
    """
    Estado completo del ecosistema Yggdrasil.
    Retorna estado de los 9 reinos + Lilith.
    """
    # Estado de los 9 reinos
    reinos = {}
    reinos_nombres = [
        "Asgard",
        "Alfheim",
        "Midgard",
        "Svartalfheim",
        "Vanaheim",
        "Jotunheim",
        "Muspelheim",
        "Niflheim",
        "Helheim",
    ]

    for reino in reinos_nombres:
        reino_path = YGGDRASIL_ROOT / reino

        if reino_path.exists():
            try:
                file_count = sum(1 for _ in reino_path.rglob("*") if _.is_file())
                dir_count = sum(1 for _ in reino_path.rglob("*") if _.is_dir())

                # Determinar status
                if file_count == 0:
                    status = "empty"
                elif (reino_path / "README.md").exists():
                    status = "active"
                else:
                    status = "initialized"

                reinos[reino.lower()] = {
                    "status": status,
                    "file_count": file_count,
                    "dir_count": dir_count,
                    "has_rules": (reino_path / "REGLAS.md").exists(),
                }
            except Exception as e:
                reinos[reino.lower()] = {
                    "status": "error",
                    "error": str(e),
                    "file_count": 0,
                    "dir_count": 0,
                }
        else:
            reinos[reino.lower()] = {
                "status": "not_created",
                "file_count": 0,
                "dir_count": 0,
            }

    # Estado de Lilith (simulado - en producción hacer healthcheck real)
    lilith_status = {
        "backend_running": True,
        "discord_bot": True,
        "telegram_bot": True,
        "version": "4.2.2",
        "location": "Asgard/Lilith/",
    }

    return {
        "yggdrasil": {
            "reinos": reinos,
            "root_path": str(YGGDRASIL_ROOT),
            "total_files": sum(r.get("file_count", 0) for r in reinos.values()),
        },
        "lilith": lilith_status,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/pantheon/status")
async def get_pantheon_status():
    """
    Estado de todos los agentes del Panteón.
    """
    # Agentes del Panteón
    agentes_nombres = [
        "eva",
        "adan",
        "odin",
        "lucifer",
        "shalltear",
    ]

    agents = {}

    # Intentar obtener métricas reales
    try:
        from src.core.agent_metrics import get_metrics

        metrics = get_metrics()

        for agent_name in agentes_nombres:
            tool_name = f"delegate_{agent_name}"
            stats = metrics.get_stats(tool_name)

            if stats and stats.total_calls > 0:
                agents[agent_name] = {
                    "status": "online",
                    "total_calls": stats.total_calls,
                    "success_rate": round(stats.success_rate, 3),
                    "avg_latency_ms": round(stats.avg_latency_ms, 2),
                    "p95_latency_ms": round(stats.p95_latency_ms, 2),
                    "errors": stats.errors,
                }
            else:
                agents[agent_name] = {
                    "status": "standby",
                    "total_calls": 0,
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "p95_latency_ms": 0.0,
                    "errors": 0,
                }
    except Exception as e:
        # Fallback si metrics no está disponible
        for agent_name in agentes_nombres:
            agents[agent_name] = {
                "status": "unknown",
                "total_calls": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "error": str(e),
            }

    return {
        "agents": agents,
        "total_agents": len(agents),
        "online_count": sum(1 for a in agents.values() if a["status"] == "online"),
    }


@router.get("/memory/stats")
async def get_memory_stats():
    """
    Estadísticas de los sistemas de memoria.
    """
    stats = {
        "semantic": {"count": 0, "status": "unknown"},
        "episodic": {"count": 0, "status": "unknown"},
        "muninn": {"count": 0, "status": "unknown"},
    }

    # Semantic Memory
    try:
        from src.core.memory.semantic_store import SemanticStore

        semantic = SemanticStore()
        stats["semantic"] = {
            "count": len(semantic.facts) if hasattr(semantic, "facts") else 0,
            "status": "active",
        }
    except Exception as e:
        stats["semantic"]["error"] = str(e)

    # Episodic Memory
    try:
        from src.core.memory.legacy_adapter import EpisodicStore

        episodic = EpisodicStore()
        stats["episodic"] = {
            "count": len(episodic.entries) if hasattr(episodic, "entries") else 0,
            "status": "active",
        }
    except Exception as e:
        stats["episodic"]["error"] = str(e)

    # MuninnDB
    try:
        # Estimación basada en archivos
        muninn_path = Path("D:/MuninnDB")
        if muninn_path.exists():
            vaults = [d for d in muninn_path.iterdir() if d.is_dir()]
            stats["muninn"] = {
                "count": len(vaults),
                "vaults": [v.name for v in vaults],
                "status": "active",
            }
        else:
            stats["muninn"]["status"] = "not_found"
    except Exception as e:
        stats["muninn"]["error"] = str(e)

    total = sum(
        s.get("count", 0) for s in stats.values() if isinstance(s.get("count"), int)
    )

    return {
        "memory_systems": stats,
        "total_memories": total,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/dags/active")
async def get_active_dags():
    """
    DAGs actualmente en ejecución o historial reciente.
    """
    # TODO: Integrar con executor real cuando esté implementado
    return {
        "active_dags": [],
        "recent_executions": [],
        "total_executed": 0,
        "avg_execution_time_ms": 0,
    }


@router.get("/logs/recent")
async def get_recent_logs(limit: int = 50):
    """
    Logs recientes del sistema.
    """
    # Leer desde archivo de log si existe
    log_files = [
        Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Logs/lilith.log"),
        Path("D:/Proyectos/Yggdrasil/Asgard/Lilith/lilith.log"),
    ]

    logs = []
    for log_file in log_files:
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8").split("\n")
                for line in lines[-limit:]:
                    if line.strip():
                        logs.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "level": "INFO",
                                "message": line.strip(),
                            }
                        )
                break
            except Exception:
                continue

    return {"logs": logs[-limit:]}


@router.websocket("/ws/logs")
async def logs_websocket(websocket: WebSocket):
    """
    Stream de logs en tiempo real via WebSocket.
    """
    await websocket.accept()

    try:
        while True:
            # Simular logs (en producción, leer de fuente real)
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "source": "lilith.core",
                "message": "System operational",
            }

            await websocket.send_json(log_entry)
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        print("[AsgardAPI] WebSocket client disconnected")
    except Exception as e:
        print(f"[AsgardAPI] WebSocket error: {e}")


@router.get("/automode/tasks")
async def get_automode_tasks():
    """
    Tareas Auto-Mode activas.
    """
    muspelheim_active = Path("D:/Proyectos/Yggdrasil/Muspelheim/AutoMode/active")

    tasks = []
    if muspelheim_active.exists():
        for task_dir in muspelheim_active.iterdir():
            if task_dir.is_dir():
                # Leer config si existe
                config_file = task_dir / "config.json"
                if config_file.exists():
                    try:
                        import json

                        config = json.loads(config_file.read_text())
                        tasks.append(
                            {
                                "task_id": task_dir.name,
                                "title": config.get("title", "Unknown"),
                                "status": "running",
                                "created_at": config.get("created_at"),
                            }
                        )
                    except Exception:
                        pass
                else:
                    tasks.append(
                        {
                            "task_id": task_dir.name,
                            "title": "Unknown",
                            "status": "running",
                        }
                    )

    return {"active_tasks": tasks, "count": len(tasks)}


@router.get("/health")
async def health_check():
    """
    Health check del dashboard.
    """
    return {
        "status": "healthy",
        "service": "asgard-dashboard",
        "timestamp": datetime.now().isoformat(),
    }
