"""
Analytics & Usage Tracking - Métricas de uso del sistema

Sistema para trackear y analizar el uso de Lilith:
- Uso por agente (tokens, llamadas, latencia)
- Queries más frecuentes
- Métricas de rendimiento por endpoint
- Historial temporal

v4.2.4: Sistema de analytics

Uso:
    from core.analytics import AnalyticsManager

    analytics = AnalyticsManager()
    analytics.record_agent_usage("eva", tokens_used=150, response_time_ms=250)

    # Obtener estadísticas
    stats = analytics.get_agent_stats("eva", days=7)
"""
import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AgentUsageEvent:
    """Evento de uso de un agente."""

    timestamp: datetime
    agent_name: str
    user_id: Optional[str]
    session_id: Optional[str]
    tokens_input: int
    tokens_output: int
    response_time_ms: float
    backend: str
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "response_time_ms": self.response_time_ms,
            "backend": self.backend,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class QueryEvent:
    """Evento de query del usuario."""

    timestamp: datetime
    query_hash: str
    query_preview: str  # Primeros 100 caracteres
    agent_used: str
    response_time_ms: float
    tokens_total: int
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "query_hash": self.query_hash,
            "query_preview": self.query_preview,
            "agent_used": self.agent_used,
            "response_time_ms": self.response_time_ms,
            "tokens_total": self.tokens_total,
            "cached": self.cached,
        }


@dataclass
class EndpointMetric:
    """Métricas de un endpoint API."""

    endpoint: str
    method: str
    call_count: int = 0
    total_response_time_ms: float = 0.0
    error_count: int = 0
    last_called: Optional[datetime] = None

    @property
    def average_response_time_ms(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.total_response_time_ms / self.call_count

    @property
    def error_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "call_count": self.call_count,
            "average_response_time_ms": round(self.average_response_time_ms, 2),
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 4),
            "last_called": self.last_called.isoformat() if self.last_called else None,
        }


class AnalyticsManager:
    """
    Manager central de analytics y métricas.

    Responsabilidades:
    - Registrar eventos de uso (agentes, queries, endpoints)
    - Agregar métricas temporales
    - Persistencia en MuninnDB
    - Queries analíticas
    """

    def __init__(
        self, max_events_in_memory: int = 1000, persist_interval_seconds: int = 60
    ):
        self.max_events = max_events_in_memory
        self.persist_interval = persist_interval_seconds

        # Buffer de eventos en memoria
        self._agent_events: List[AgentUsageEvent] = []
        self._query_events: List[QueryEvent] = []
        self._endpoint_metrics: Dict[str, EndpointMetric] = {}

        # Agregaciones en memoria
        self._daily_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "agent_calls": defaultdict(int),
                "total_tokens": 0,
                "unique_users": set(),
                "queries": 0,
            }
        )

        # Configuración
        self._persist_task: Optional[asyncio.Task] = None
        self._running = False
        self._muninn_available = False

        # Iniciar
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        """Inicializar el manager."""
        try:
            from src.core.memory.muninn_memory import MuninnMemory

            self._muninn_available = True
            self._running = True
            self._persist_task = asyncio.create_task(self._persist_loop())
            logger.info("AnalyticsManager: Initialized")
        except ImportError:
            logger.warning(
                "AnalyticsManager: MuninnMemory not available, running without persistence"
            )
            self._muninn_available = False

    async def _persist_loop(self):
        """Loop de persistencia periódica."""
        while self._running:
            try:
                await asyncio.sleep(self.persist_interval)
                await self._persist_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analytics persist error: {e}")

    async def _persist_buffer(self):
        """Persistir eventos acumulados a MuninnDB."""
        if not self._muninn_available:
            return

        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()

            # Persistir eventos de agentes
            events_to_persist = []

            for event in self._agent_events[-100:]:  # Últimos 100
                events_to_persist.append(
                    {
                        "type": "agent_usage",
                        "content": json.dumps(event.to_dict(), ensure_ascii=False),
                        "tags": ["analytics", "agent", event.agent_name],
                        "metadata": {
                            "agent": event.agent_name,
                            "user_id": event.user_id,
                            "timestamp": event.timestamp.isoformat(),
                        },
                    }
                )

            for event in self._query_events[-100:]:
                events_to_persist.append(
                    {
                        "type": "query",
                        "content": json.dumps(event.to_dict(), ensure_ascii=False),
                        "tags": ["analytics", "query"],
                        "metadata": {
                            "query_hash": event.query_hash,
                            "cached": event.cached,
                        },
                    }
                )

            # Batch insert
            if events_to_persist:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: [muninn.add_event(**e) for e in events_to_persist]
                )

            logger.debug(f"AnalyticsManager: Persisted {len(events_to_persist)} events")

        except Exception as e:
            logger.error(f"Failed to persist analytics: {e}")

    def record_agent_usage(
        self,
        agent_name: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        response_time_ms: float = 0.0,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        backend: str = "unknown",
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Registrar uso de un agente.

        Args:
            agent_name: Nombre del agente (eva, adan, lilith, etc.)
            tokens_input: Tokens de entrada
            tokens_output: Tokens de salida
            response_time_ms: Tiempo de respuesta en milisegundos
            user_id: ID del usuario
            session_id: ID de sesión
            backend: Backend utilizado (kimi, openrouter, ollama)
            success: Si la operación fue exitosa
            error_message: Mensaje de error si falló
            metadata: Metadata adicional
        """
        event = AgentUsageEvent(
            timestamp=datetime.now(),
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            response_time_ms=response_time_ms,
            backend=backend,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        self._agent_events.append(event)

        # Actualizar agregaciones diarias
        day_key = event.timestamp.strftime("%Y-%m-%d")
        self._daily_stats[day_key]["agent_calls"][agent_name] += 1
        self._daily_stats[day_key]["total_tokens"] += tokens_input + tokens_output
        self._daily_stats[day_key]["queries"] += 1
        if user_id:
            self._daily_stats[day_key]["unique_users"].add(user_id)

        # Limitar buffer
        if len(self._agent_events) > self.max_events:
            self._agent_events = self._agent_events[-self.max_events :]

        logger.debug(
            f"Analytics: Recorded {agent_name} usage ({tokens_input + tokens_output} tokens)"
        )

    def record_query(
        self,
        query: str,
        agent_used: str,
        response_time_ms: float,
        tokens_total: int,
        cached: bool = False,
    ):
        """
        Registrar una query del usuario.

        Args:
            query: Texto de la consulta
            agent_used: Agente que respondió
            response_time_ms: Tiempo de respuesta
            tokens_total: Tokens totales usados
            cached: Si usó cache
        """
        # Hash de la query para anonimización
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        query_preview = query[:100] + "..." if len(query) > 100 else query

        event = QueryEvent(
            timestamp=datetime.now(),
            query_hash=query_hash,
            query_preview=query_preview,
            agent_used=agent_used,
            response_time_ms=response_time_ms,
            tokens_total=tokens_total,
            cached=cached,
        )

        self._query_events.append(event)

        if len(self._query_events) > self.max_events:
            self._query_events = self._query_events[-self.max_events :]

    def record_endpoint_call(
        self, endpoint: str, method: str, response_time_ms: float, error: bool = False
    ):
        """
        Registrar llamada a endpoint API.

        Args:
            endpoint: Ruta del endpoint
            method: Método HTTP
            response_time_ms: Tiempo de respuesta
            error: Si hubo error
        """
        key = f"{method}:{endpoint}"

        if key not in self._endpoint_metrics:
            self._endpoint_metrics[key] = EndpointMetric(
                endpoint=endpoint, method=method
            )

        metric = self._endpoint_metrics[key]
        metric.call_count += 1
        metric.total_response_time_ms += response_time_ms
        metric.last_called = datetime.now()
        if error:
            metric.error_count += 1

    # ==================== Queries Analíticas ====================

    def get_agent_stats(self, agent_name: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener estadísticas de un agente.

        Args:
            agent_name: Nombre del agente
            days: Días hacia atrás

        Returns:
            Dict con estadísticas
        """
        since = datetime.now() - timedelta(days=days)

        relevant_events = [
            e
            for e in self._agent_events
            if e.agent_name == agent_name and e.timestamp >= since
        ]

        if not relevant_events:
            return {
                "agent": agent_name,
                "period_days": days,
                "total_calls": 0,
                "total_tokens": 0,
                "average_response_time_ms": 0,
                "success_rate": 0,
            }

        total_calls = len(relevant_events)
        total_tokens = sum(e.tokens_input + e.tokens_output for e in relevant_events)
        avg_response_time = (
            sum(e.response_time_ms for e in relevant_events) / total_calls
        )
        success_count = sum(1 for e in relevant_events if e.success)

        return {
            "agent": agent_name,
            "period_days": days,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "average_response_time_ms": round(avg_response_time, 2),
            "success_rate": round(success_count / total_calls, 4),
            "tokens_per_call": round(total_tokens / total_calls, 2),
        }

    def get_top_queries(self, limit: int = 10, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtener queries más frecuentes.

        Args:
            limit: Máximo de queries a retornar
            days: Días hacia atrás

        Returns:
            Lista de queries con frecuencia
        """
        since = datetime.now() - timedelta(days=days)

        query_counts = defaultdict(lambda: {"count": 0, "preview": "", "agent": ""})

        for event in self._query_events:
            if event.timestamp >= since:
                query_counts[event.query_hash]["count"] += 1
                query_counts[event.query_hash]["preview"] = event.query_preview
                query_counts[event.query_hash]["agent"] = event.agent_used

        # Ordenar por frecuencia
        sorted_queries = sorted(
            query_counts.items(), key=lambda x: x[1]["count"], reverse=True
        )[:limit]

        return [
            {
                "query_hash": qh,
                "count": data["count"],
                "preview": data["preview"],
                "agent": data["agent"],
            }
            for qh, data in sorted_queries
        ]

    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Obtener estadísticas de endpoints."""
        return [metric.to_dict() for metric in self._endpoint_metrics.values()]

    def get_daily_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtener resumen diario.

        Args:
            days: Número de días

        Returns:
            Lista de resúmenes diarios
        """
        result = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            day_key = date.strftime("%Y-%m-%d")
            stats = self._daily_stats[day_key]

            result.append(
                {
                    "date": day_key,
                    "total_queries": stats["queries"],
                    "total_tokens": stats["total_tokens"],
                    "unique_users": len(stats["unique_users"]),
                    "agent_calls": dict(stats["agent_calls"]),
                }
            )

        return result

    def get_global_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtener estadísticas globales.

        Args:
            days: Período en días

        Returns:
            Dict con estadísticas globales
        """
        since = datetime.now() - timedelta(days=days)

        # Agente más usado
        agent_calls = defaultdict(int)
        total_tokens = 0
        total_response_time = 0.0
        total_calls = 0

        for event in self._agent_events:
            if event.timestamp >= since:
                agent_calls[event.agent_name] += 1
                total_tokens += event.tokens_input + event.tokens_output
                total_response_time += event.response_time_ms
                total_calls += 1

        most_used_agent = (
            max(agent_calls.items(), key=lambda x: x[1])[0] if agent_calls else None
        )

        return {
            "period_days": days,
            "total_agent_calls": total_calls,
            "total_tokens_consumed": total_tokens,
            "average_response_time_ms": round(total_response_time / total_calls, 2)
            if total_calls
            else 0,
            "most_used_agent": most_used_agent,
            "agent_distribution": dict(agent_calls),
            "events_in_memory": len(self._agent_events),
        }

    async def load_historical_data(self, days: int = 30) -> int:
        """
        Cargar datos históricos desde MuninnDB.

        Args:
            days: Días hacia atrás a cargar

        Returns:
            Número de eventos cargados
        """
        if not self._muninn_available:
            return 0

        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()

            since = datetime.now() - timedelta(days=days)

            # Buscar eventos de analytics
            events = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: muninn.search(query="analytics", vault="lilith", limit=1000),
            )

            loaded = 0
            for event in events:
                try:
                    event_time = datetime.fromisoformat(
                        event.get("timestamp", "1970-01-01")
                    )
                    if event_time < since:
                        continue

                    content = json.loads(event.get("content", "{}"))
                    event_type = event.get("event_type")

                    if event_type == "agent_usage":
                        self._agent_events.append(AgentUsageEvent(**content))
                    elif event_type == "query":
                        self._query_events.append(QueryEvent(**content))

                    loaded += 1

                except Exception as e:
                    logger.debug(f"Failed to load historical event: {e}")
                    continue

            logger.info(f"AnalyticsManager: Loaded {loaded} historical events")
            return loaded

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del manager."""
        return {
            "events_in_memory": len(self._agent_events) + len(self._query_events),
            "agent_events": len(self._agent_events),
            "query_events": len(self._query_events),
            "endpoint_metrics": len(self._endpoint_metrics),
            "daily_stats_days": len(self._daily_stats),
            "muninn_available": self._muninn_available,
            "persist_interval_seconds": self.persist_interval,
        }


# Singleton global
_analytics_manager: Optional[AnalyticsManager] = None


def get_analytics_manager() -> AnalyticsManager:
    """Obtener instancia singleton del AnalyticsManager."""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager
