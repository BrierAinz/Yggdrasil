"""
Dashboard API v2 - Analytics Avanzado y Visualización

Endpoints:
- /api/dashboard/ - HTML SPA
- /api/dashboard/overview - Resumen del sistema
- /api/dashboard/analytics - Gráficos de uso
- /api/dashboard/memory - Estadísticas de memoria
- /api/dashboard/agents - Métricas de agentes
- /api/dashboard/graph - Grafo de ejecución
- /api/dashboard/sessions - Resúmenes de sesión
- /api/dashboard/audit - Auditoría PC Agent
- /api/dashboard/export - Export de datos
"""

import io
import json
import logging
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardService:
    """Servicio central del dashboard con todos los analytics"""

    def __init__(
        self,
        data_dir: Path,
        agent_metrics_module,
        episodic_store_module,
        muninn_edges_module,
        session_summarizer_module,
        decision_auditor_module,
    ):
        """
        Args:
            data_dir: Directorio Data/
            agent_metrics_module: Módulo agent_metrics
            episodic_store_module: Módulo episodic_store
            muninn_edges_module: Módulo muninn_edges
            session_summarizer_module: Módulo session_summarizer
            decision_auditor_module: Módulo decision_auditor_v2
        """
        self.data_dir = data_dir
        self.agent_metrics = agent_metrics_module
        self.episodic_store = episodic_store_module
        self.muninn_edges = muninn_edges_module
        self.session_summarizer = session_summarizer_module
        self.decision_auditor = decision_auditor_module

    def get_overview(self) -> Dict[str, Any]:
        """
        Resumen general del sistema

        Returns:
            Dict con métricas clave
        """
        try:
            # Métricas de agentes
            agent_stats = self.agent_metrics.get_metrics().get_summary()

            # Conteo de episodios
            try:
                episodes = self.episodic_store.get_recent(limit=1000)
                episode_count = len(episodes)
            except:
                episode_count = 0

            # Conteo de edges
            try:
                edges = self.muninn_edges.get_edge_manager().get_all_edges()
                edge_count = len(edges)
            except:
                edge_count = 0

            # Conteo de sesiones resumidas
            try:
                summaries = self.session_summarizer.get_all_summaries()
                session_count = len(summaries)
            except:
                session_count = 0

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agents": {
                    "total_calls": agent_stats.get("total_calls", 0),
                    "success_rate": agent_stats.get("success_rate", 0.0),
                    "avg_latency_ms": agent_stats.get("avg_latency_ms", 0.0),
                },
                "memory": {
                    "episodes": episode_count,
                    "edges": edge_count,
                    "sessions": session_count,
                },
                "health": {
                    "status": "healthy"
                    if agent_stats.get("success_rate", 0) > 0.8
                    else "degraded",
                    "uptime_hours": self._get_uptime_hours(),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get overview: {e}")
            return {"error": str(e)}

    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Analytics de uso (últimos N días)

        Args:
            days: Días de historial

        Returns:
            Dict con datos para gráficos
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            # Obtener episodios recientes
            episodes = self.episodic_store.get_recent(limit=5000)

            # Filtrar por fecha
            recent_episodes = [
                ep
                for ep in episodes
                if datetime.fromisoformat(ep.get("timestamp", "2000-01-01")) > cutoff
            ]

            # Análisis 1: Intents más usados
            intent_counts = {}
            for ep in recent_episodes:
                intent = ep.get("intent") or ep.get("matched_intent") or "unknown"
                intent_counts[intent] = intent_counts.get(intent, 0) + 1

            top_intents = sorted(
                intent_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]

            # Análisis 2: Distribución de confidence (de auditoría)
            confidence_dist = {"high": 0, "medium": 0, "low": 0, "unknown": 0}

            try:
                audit_events = (
                    self.decision_auditor.get_decision_auditor().get_recent_decisions(
                        limit=500
                    )
                )
                for event in audit_events:
                    conf = event.get("confidence")
                    if conf is None:
                        confidence_dist["unknown"] += 1
                    elif conf >= 0.8:
                        confidence_dist["high"] += 1
                    elif conf >= 0.5:
                        confidence_dist["medium"] += 1
                    else:
                        confidence_dist["low"] += 1
            except:
                pass

            # Análisis 3: Latencia por herramienta
            agent_metrics = self.agent_metrics.get_metrics()
            tool_latencies = []

            for tool_name, stats in agent_metrics.tool_stats.items():
                if stats.call_count > 0:
                    tool_latencies.append(
                        {
                            "tool": tool_name,
                            "avg_latency_ms": round(stats.avg_latency_ms(), 1),
                            "calls": stats.call_count,
                        }
                    )

            tool_latencies.sort(key=lambda x: x["avg_latency_ms"], reverse=True)

            # Análisis 4: Tasa de éxito por agente
            agent_success = []

            for agent_name in ["eva", "odin", "adan", "lucifer", "crystal"]:
                agent_stats = agent_metrics.get_agent_stats(agent_name)
                if agent_stats and agent_stats.call_count > 0:
                    agent_success.append(
                        {
                            "agent": agent_name,
                            "success_rate": round(agent_stats.success_rate() * 100, 1),
                            "calls": agent_stats.call_count,
                        }
                    )

            return {
                "period_days": days,
                "total_episodes": len(recent_episodes),
                "top_intents": [
                    {"intent": intent, "count": count} for intent, count in top_intents
                ],
                "confidence_distribution": confidence_dist,
                "tool_latencies": tool_latencies[:10],
                "agent_success_rates": agent_success,
            }

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {"error": str(e)}

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Estadísticas de memoria (ChromaDB, Muninn, Episódica)

        Returns:
            Dict con stats de cada capa
        """
        try:
            stats = {
                "chromadb": self._get_chromadb_stats(),
                "muninn": self._get_muninn_stats(),
                "episodic": self._get_episodic_stats(),
                "working_memory": {"status": "not_available"},
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    def _get_chromadb_stats(self) -> Dict[str, Any]:
        """Stats de ChromaDB (mock - requiere integración real)"""
        return {"total_chunks": "N/A", "avg_score": "N/A", "last_purge": "N/A"}

    def _get_muninn_stats(self) -> Dict[str, Any]:
        """Stats de MuninnDB"""
        try:
            edges = self.muninn_edges.get_edge_manager().get_all_edges()

            # Agrupar por tipo
            edge_types = {}
            for edge in edges:
                edge_type = edge.get("edge_type", "unknown")
                edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

            return {"total_edges": len(edges), "edge_types": edge_types}
        except:
            return {"total_edges": 0, "edge_types": {}}

    def _get_episodic_stats(self) -> Dict[str, Any]:
        """Stats de memoria episódica"""
        try:
            episodes = self.episodic_store.get_recent(limit=10000)

            # Calcular tamaño aproximado
            total_size_bytes = sum(len(json.dumps(ep)) for ep in episodes)

            return {
                "total_episodes": len(episodes),
                "size_mb": round(total_size_bytes / (1024 * 1024), 2),
            }
        except:
            return {"total_episodes": 0, "size_mb": 0.0}

    def get_execution_graph(self, limit: int = 100) -> Dict[str, Any]:
        """
        Grafo de ejecución (edges de Muninn)

        Args:
            limit: Máximo de edges

        Returns:
            Dict con nodes y edges para visualización
        """
        try:
            edges = self.muninn_edges.get_edge_manager().get_all_edges()
            edges = edges[:limit]

            # Construir nodes y links
            nodes_set = set()
            links = []

            for edge in edges:
                source = edge.get("source")
                target = edge.get("target")
                edge_type = edge.get("edge_type", "unknown")

                if source and target:
                    nodes_set.add(source)
                    nodes_set.add(target)

                    links.append(
                        {
                            "source": source,
                            "target": target,
                            "type": edge_type,
                            "timestamp": edge.get("timestamp"),
                        }
                    )

            nodes = [{"id": node_id, "label": node_id} for node_id in nodes_set]

            return {"nodes": nodes, "links": links, "total_edges": len(edges)}

        except Exception as e:
            logger.error(f"Failed to get execution graph: {e}")
            return {"nodes": [], "links": [], "error": str(e)}

    def get_session_summaries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Resúmenes de sesión recientes

        Args:
            limit: Máximo de resúmenes

        Returns:
            Lista de summaries
        """
        try:
            summaries = self.session_summarizer.get_all_summaries()
            summaries.sort(key=lambda s: s.get("summary_created_at", ""), reverse=True)
            return summaries[:limit]

        except Exception as e:
            logger.error(f"Failed to get session summaries: {e}")
            return []

    def get_audit_recent(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Auditoría reciente de PC Agent

        Args:
            days: Días de historial
            limit: Máximo de eventos

        Returns:
            Lista de eventos de auditoría
        """
        try:
            events = self.decision_auditor.get_decision_auditor().get_recent_decisions(
                limit=limit, decision_type="step_executed"
            )

            # Filtrar por días
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = [
                ev
                for ev in events
                if datetime.fromisoformat(ev.get("timestamp", "2000-01-01")) > cutoff
            ]

            return filtered

        except Exception as e:
            logger.error(f"Failed to get audit: {e}")
            return []

    def export_data(self) -> bytes:
        """
        Exportar todos los datos en un ZIP

        Returns:
            Bytes del ZIP
        """
        try:
            buffer = io.BytesIO()

            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # Agregar episodios
                episodes = self.episodic_store.get_recent(limit=5000)
                zf.writestr(
                    "episodes.json", json.dumps(episodes, indent=2, ensure_ascii=False)
                )

                # Agregar edges
                edges = self.muninn_edges.get_edge_manager().get_all_edges()
                zf.writestr(
                    "edges.json", json.dumps(edges, indent=2, ensure_ascii=False)
                )

                # Agregar summaries
                summaries = self.session_summarizer.get_all_summaries()
                zf.writestr(
                    "session_summaries.json",
                    json.dumps(summaries, indent=2, ensure_ascii=False),
                )

                # Agregar analytics
                analytics = self.get_analytics(days=30)
                zf.writestr(
                    "analytics.json",
                    json.dumps(analytics, indent=2, ensure_ascii=False),
                )

            buffer.seek(0)
            return buffer.read()

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            raise

    def _get_uptime_hours(self) -> float:
        """Calcular uptime aproximado (mock)"""
        # TODO: Implementar tracking real de uptime
        return 0.0


# Singleton global
_dashboard_service: Optional[DashboardService] = None


def initialize_dashboard_service(
    data_dir: Path,
    agent_metrics_module,
    episodic_store_module,
    muninn_edges_module,
    session_summarizer_module,
    decision_auditor_module,
):
    """Inicializar el dashboard service global"""
    global _dashboard_service
    _dashboard_service = DashboardService(
        data_dir=data_dir,
        agent_metrics_module=agent_metrics_module,
        episodic_store_module=episodic_store_module,
        muninn_edges_module=muninn_edges_module,
        session_summarizer_module=session_summarizer_module,
        decision_auditor_module=decision_auditor_module,
    )


def get_dashboard_service() -> DashboardService:
    """Obtener instancia singleton del dashboard service"""
    if _dashboard_service is None:
        raise ValueError("Dashboard service not initialized")
    return _dashboard_service


# Endpoints FastAPI


@router.get("/", response_class=HTMLResponse)
async def dashboard_html():
    """Dashboard SPA (HTML completo en próximo archivo)"""
    html = get_dashboard_html()
    return HTMLResponse(content=html)


@router.get("/overview")
async def get_overview():
    """GET /api/dashboard/overview - Resumen general"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_overview())


@router.get("/analytics")
async def get_analytics(days: int = 7):
    """GET /api/dashboard/analytics?days=7 - Analytics de uso"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_analytics(days=days))


@router.get("/memory")
async def get_memory():
    """GET /api/dashboard/memory - Stats de memoria"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_memory_stats())


@router.get("/graph")
async def get_graph(limit: int = 100):
    """GET /api/dashboard/graph?limit=100 - Grafo de ejecución"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_execution_graph(limit=limit))


@router.get("/sessions")
async def get_sessions(limit: int = 20):
    """GET /api/dashboard/sessions?limit=20 - Resúmenes de sesión"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_session_summaries(limit=limit))


@router.get("/audit")
async def get_audit(days: int = 7, limit: int = 50):
    """GET /api/dashboard/audit?days=7&limit=50 - Auditoría reciente"""
    service = get_dashboard_service()
    return JSONResponse(content=service.get_audit_recent(days=days, limit=limit))


@router.get("/export")
async def export_data():
    """GET /api/dashboard/export - Exportar datos como ZIP"""
    service = get_dashboard_service()

    try:
        zip_bytes = service.export_data()

        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=lilith_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_dashboard_html() -> str:
    """HTML del dashboard (placeholder - se crea en próximo archivo)"""
    return "<html><body><h1>Dashboard loading...</h1></body></html>"
