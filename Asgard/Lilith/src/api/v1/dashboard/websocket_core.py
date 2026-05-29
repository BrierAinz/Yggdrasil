"""
Dashboard WebSocket Live - Métricas del sistema en tiempo real

Extensión del WebSocket handler para transmitir métricas del sistema
al dashboard del frontend de forma continua.

v4.2.4: Sistema de métricas live para Dashboard
"""
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Métricas del sistema para transmisión live."""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_free_gb: float

    # Health status
    health_status: str  # healthy, degraded, unhealthy
    health_checks: Dict[str, Any]

    # Actividad
    active_sessions: int
    total_messages: int
    messages_per_minute: float

    # Agentes
    active_agents: list
    agent_activity: Dict[str, int]  # Contador de acciones por agente

    # Rendimiento
    avg_response_time_ms: float
    requests_in_flight: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DashboardWebSocketManager:
    """
    Manager para métricas live del Dashboard vía WebSocket.

    Responsabilidades:
    - Recolectar métricas del sistema periódicamente
    - Transmitir a todos los clientes conectados
    - Mantener historial de métricas para gráficos
    """

    def __init__(
        self,
        update_interval_seconds: float = 2.0,
        max_history_points: int = 300,  # 10 minutos a 2 segundos
    ):
        self.update_interval = update_interval_seconds
        self.max_history = max_history_points

        # Clientes suscritos (websocket -> metadata)
        self.clients: Dict[Any, Dict] = {}

        # Historial de métricas para gráficos
        self.metrics_history: list = []

        # Task de broadcast
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False

        # Métricas acumuladas
        self._message_count = 0
        self._message_timestamps: list = []
        self._response_times: list = []
        self._agent_activity: Dict[str, int] = {}

        # Providers de datos de reinos (Ojo de Hrafnsmál)
        self._realm_providers: List[Callable[[], Dict[str, Any]]] = []

        # Referencia al health monitor (se establece externamente)
        self.health_monitor = None

    async def start(self):
        """Iniciar el manager y el loop de broadcast."""
        if self._running:
            return

        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("DashboardWebSocketManager: Started")

    async def stop(self):
        """Detener el manager."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("DashboardWebSocketManager: Stopped")

    def subscribe(self, websocket, client_info: Dict = None):
        """
        Suscribir un cliente WebSocket a las métricas live.

        Args:
            websocket: Objeto WebSocket
            client_info: Metadata del cliente (user_id, etc.)
        """
        self.clients[websocket] = {
            "subscribed_at": datetime.now().isoformat(),
            "info": client_info or {},
            "last_ping": time.time(),
        }
        logger.debug(
            f"DashboardWebSocket: Client subscribed (total: {len(self.clients)})"
        )

        # Enviar historial inicial al nuevo cliente
        asyncio.create_task(self._send_initial_history(websocket))

    def unsubscribe(self, websocket):
        """Desuscribir un cliente."""
        if websocket in self.clients:
            del self.clients[websocket]
            logger.debug(
                f"DashboardWebSocket: Client unsubscribed (total: {len(self.clients)})"
            )

    def record_message(self, agent: str = None, response_time_ms: float = None):
        """
        Registrar una interacción para métricas.

        Args:
            agent: Nombre del agente que procesó el mensaje
            response_time_ms: Tiempo de respuesta en ms
        """
        self._message_count += 1
        now = time.time()

        # Guardar timestamp para cálculo de mensajes/minuto
        self._message_timestamps.append(now)

        # Limpiar timestamps antiguos (> 1 minuto)
        cutoff = now - 60
        self._message_timestamps = [t for t in self._message_timestamps if t > cutoff]

        # Guardar tiempo de respuesta
        if response_time_ms:
            self._response_times.append(response_time_ms)
            # Mantener solo últimos 100
            self._response_times = self._response_times[-100:]

        # Contador por agente
        if agent:
            self._agent_activity[agent] = self._agent_activity.get(agent, 0) + 1

    def register_realm_provider(self, provider: Callable[[], Dict[str, Any]]) -> None:
        """Registrar un proveedor de datos de reinos para broadcast vía WS."""
        self._realm_providers.append(provider)

    def update_health_monitor(self, health_monitor):
        """Actualizar referencia al health monitor."""
        self.health_monitor = health_monitor

    async def _broadcast_loop(self):
        """Loop principal de broadcast de métricas."""
        while self._running:
            try:
                if self.clients:
                    metrics = await self._collect_metrics()
                    await self._broadcast_metrics(metrics)
                    await self._broadcast_realm_update()

                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"DashboardWebSocket broadcast error: {e}")
                await asyncio.sleep(self.update_interval)

    async def _collect_metrics(self) -> SystemMetrics:
        """Recolectar métricas actuales del sistema."""
        try:
            # Recursos del sistema (psutil si está disponible)
            (
                cpu_percent,
                memory_percent,
                memory_used_gb,
                memory_total_gb,
            ) = await self._get_system_resources()
            disk_percent, disk_free_gb = await self._get_disk_info()

            # Health checks
            health_status, health_checks = await self._get_health_status()

            # Calcular métricas de actividad
            messages_per_minute = len(self._message_timestamps)
            avg_response_time = (
                sum(self._response_times) / len(self._response_times)
                if self._response_times
                else 0
            )

            metrics = SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_gb=memory_used_gb,
                memory_total_gb=memory_total_gb,
                disk_percent=disk_percent,
                disk_free_gb=disk_free_gb,
                health_status=health_status,
                health_checks=health_checks,
                active_sessions=len(self.clients),
                total_messages=self._message_count,
                messages_per_minute=messages_per_minute,
                active_agents=self._get_active_agents(),
                agent_activity=self._agent_activity.copy(),
                avg_response_time_ms=avg_response_time,
                requests_in_flight=0,  # TODO: trackear requests en vuelo
            )

            # Guardar en historial
            self.metrics_history.append(metrics.to_dict())
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history :]

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            # Retornar métricas vacías en caso de error
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_gb=0,
                memory_total_gb=0,
                disk_percent=0,
                disk_free_gb=0,
                health_status="unknown",
                health_checks={},
                active_sessions=len(self.clients),
                total_messages=self._message_count,
                messages_per_minute=0,
                active_agents=[],
                agent_activity={},
                avg_response_time_ms=0,
                requests_in_flight=0,
            )

    async def _get_system_resources(self):
        """Obtener recursos del sistema."""
        try:
            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)

            return cpu_percent, memory_percent, memory_used_gb, memory_total_gb

        except ImportError:
            # psutil no disponible
            return 0, 0, 0, 0
        except Exception as e:
            logger.debug(f"Error getting system resources: {e}")
            return 0, 0, 0, 0

    async def _get_disk_info(self):
        """Obtener información de disco."""
        try:
            import psutil

            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)

            return disk_percent, disk_free_gb

        except ImportError:
            return 0, 0
        except Exception as e:
            logger.debug(f"Error getting disk info: {e}")
            return 0, 0

    async def _get_health_status(self):
        """Obtener estado de salud de los subsistemas."""
        if not self.health_monitor:
            return "unknown", {}

        try:
            # Usar HealthMonitor si está disponible
            health = await self.health_monitor.check_all()

            status = health.overall_status.value
            checks = {}
            for check in health.checks:
                checks[check.name] = {
                    "status": check.status.value,
                    "latency_ms": check.latency_ms,
                    "message": check.message,
                }

            return status, checks

        except Exception as e:
            logger.debug(f"Error getting health status: {e}")
            return "unknown", {}

    def _get_active_agents(self) -> list:
        """Obtener lista de agentes activos."""
        # Basado en la actividad reciente
        agents = []
        for agent, count in self._agent_activity.items():
            if count > 0:
                agents.append({"name": agent, "actions": count})
        return agents

    async def _broadcast_metrics(self, metrics: SystemMetrics):
        """Transmitir métricas a todos los clientes conectados."""
        if not self.clients:
            return

        message = {"type": "dashboard_metrics", "data": metrics.to_dict()}

        # Enviar a todos los clientes
        disconnected = []
        for websocket, client_data in self.clients.items():
            try:
                # Verificar si el WebSocket sigue abierto
                if hasattr(websocket, "client_state"):
                    from starlette.websockets import WebSocketState

                    if websocket.client_state != WebSocketState.CONNECTED:
                        disconnected.append(websocket)
                        continue

                await websocket.send_json(message)
                client_data["last_ping"] = time.time()

            except Exception as e:
                logger.debug(f"Failed to send metrics to client: {e}")
                disconnected.append(websocket)

        # Limpiar clientes desconectados
        for ws in disconnected:
            self.unsubscribe(ws)

    async def _broadcast_realm_update(self):
        """Transmitir datos de reinos a todos los clientes conectados."""
        if not self.clients or not self._realm_providers:
            return

        realm_data: Dict[str, Any] = {}
        for provider in self._realm_providers:
            try:
                result = provider()
                if asyncio.iscoroutine(result):
                    result = await result
                if isinstance(result, dict):
                    realm_data.update(result)
            except Exception as e:
                logger.debug(f"DashboardWebSocket realm provider error: {e}")

        if not realm_data:
            return

        message = {"type": "realm_update", "data": realm_data}

        disconnected = []
        for websocket, client_data in self.clients.items():
            try:
                if hasattr(websocket, "client_state"):
                    from starlette.websockets import WebSocketState

                    if websocket.client_state != WebSocketState.CONNECTED:
                        disconnected.append(websocket)
                        continue

                await websocket.send_json(message)
                client_data["last_ping"] = time.time()

            except Exception as e:
                logger.debug(f"Failed to send realm_update to client: {e}")
                disconnected.append(websocket)

        for ws in disconnected:
            self.unsubscribe(ws)

    async def _send_initial_history(self, websocket):
        """Enviar historial inicial a un cliente nuevo."""
        try:
            message = {
                "type": "dashboard_history",
                "data": {
                    "metrics": self.metrics_history[-60:],  # Últimos 60 puntos
                    "total_messages": self._message_count,
                    "agent_activity": self._agent_activity.copy(),
                },
            }
            await websocket.send_json(message)

        except Exception as e:
            logger.debug(f"Failed to send initial history: {e}")

    def get_current_metrics(self) -> Optional[Dict]:
        """Obtener métricas más recientes."""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del manager."""
        return {
            "connected_clients": len(self.clients),
            "metrics_history_points": len(self.metrics_history),
            "total_messages_recorded": self._message_count,
            "update_interval_seconds": self.update_interval,
            "is_running": self._running,
        }


# Singleton global
_dashboard_manager: Optional[DashboardWebSocketManager] = None


def get_dashboard_manager() -> DashboardWebSocketManager:
    """Obtener instancia singleton del DashboardWebSocketManager."""
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardWebSocketManager()
    return _dashboard_manager


async def start_dashboard_websocket():
    """Iniciar el WebSocket de dashboard."""
    manager = get_dashboard_manager()
    await manager.start()

    # Intentar vincular con HealthMonitor si existe
    try:
        from src.core.health_monitor import HealthMonitor

        manager.update_health_monitor(HealthMonitor)
    except ImportError:
        pass

    return manager


async def stop_dashboard_websocket():
    """Detener el WebSocket de dashboard."""
    global _dashboard_manager
    if _dashboard_manager:
        await _dashboard_manager.stop()
        _dashboard_manager = None
