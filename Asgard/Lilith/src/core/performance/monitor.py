"""
Performance Monitor - Sistema de métricas y optimización

v5.0: Monitoreo de rendimiento, métricas en tiempo real y auto-optimización.
"""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.performance")


@dataclass
class MetricPoint:
    """Punto de métrica individual."""

    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Métricas de performance."""

    response_time_ms: float
    tokens_per_second: float
    memory_mb: float
    cpu_percent: float
    queue_size: int
    active_requests: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PerformanceMonitor:
    """
    Monitor de performance del sistema.

    Features:
    - Métricas en tiempo real
    - Alertas por umbrales
    - Historial de métricas
    - Auto-ajuste de parámetros
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history

        # Históricos
        self._response_times: deque = deque(maxlen=max_history)
        self._token_rates: deque = deque(maxlen=max_history)
        self._memory_usage: deque = deque(maxlen=max_history)
        self._request_counts: Dict[str, int] = {}

        # Estado actual
        self._active_requests = 0
        self._total_requests = 0
        self._error_count = 0

        # Alertas
        self._thresholds = {
            "response_time_ms": 5000,  # 5 segundos
            "memory_mb": 1024,  # 1GB
            "cpu_percent": 80,
            "error_rate": 0.1,  # 10%
        }
        self._alert_handlers: List[Callable] = []

        # Auto-optimización
        self._auto_tune = True
        self._concurrency_limit = 10

    def record_request_start(self) -> str:
        """Registra inicio de request."""
        import secrets

        request_id = secrets.token_hex(8)
        self._active_requests += 1
        self._total_requests += 1
        return request_id

    def record_request_end(
        self,
        request_id: str,
        success: bool,
        response_time_ms: float,
        tokens_used: int = 0,
    ):
        """Registra fin de request."""
        self._active_requests = max(0, self._active_requests - 1)

        if not success:
            self._error_count += 1

        # Guardar métricas
        self._response_times.append(response_time_ms)

        if tokens_used > 0 and response_time_ms > 0:
            tps = (tokens_used / response_time_ms) * 1000
            self._token_rates.append(tps)

        # Verificar umbrales
        self._check_thresholds(response_time_ms)

    def _check_thresholds(self, response_time_ms: float):
        """Verifica si se exceden umbrales."""
        alerts = []

        if response_time_ms > self._thresholds["response_time_ms"]:
            alerts.append(f"Response time {response_time_ms:.0f}ms excede umbral")

        # Calcular error rate
        if self._total_requests > 10:
            error_rate = self._error_count / self._total_requests
            if error_rate > self._thresholds["error_rate"]:
                alerts.append(f"Error rate {error_rate:.1%} excede umbral")

        # Notificar alertas
        for alert in alerts:
            self._notify_alert(alert)

        # Auto-ajuste
        if self._auto_tune and alerts:
            self._auto_tune_params()

    def _notify_alert(self, message: str):
        """Notifica alerta a handlers."""
        logger.warning(f"Performance alert: {message}")
        for handler in self._alert_handlers:
            try:
                handler(message)
            except Exception:
                pass

    def _auto_tune_params(self):
        """Ajusta parámetros automáticamente."""
        # Si hay muchos requests activos, aumentar concurrencia
        if self._active_requests > self._concurrency_limit * 0.8:
            self._concurrency_limit = min(50, self._concurrency_limit + 2)
            logger.info(
                f"Auto-tune: concurrencia aumentada a {self._concurrency_limit}"
            )

        # Si los tiempos de respuesta son altos, reducir
        if self._response_times:
            avg_response = sum(self._response_times) / len(self._response_times)
            if avg_response > 3000 and self._concurrency_limit > 5:
                self._concurrency_limit = max(5, self._concurrency_limit - 2)
                logger.info(
                    f"Auto-tune: concurrencia reducida a {self._concurrency_limit}"
                )

    def record_memory(self, memory_mb: float):
        """Registra uso de memoria."""
        self._memory_usage.append(memory_mb)

        if memory_mb > self._thresholds["memory_mb"]:
            self._notify_alert(f"Memory usage {memory_mb:.0f}MB excede umbral")

    def get_current_metrics(self) -> PerformanceMetrics:
        """Obtiene métricas actuales."""
        import psutil

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        avg_response = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times
            else 0
        )

        avg_tps = (
            sum(self._token_rates) / len(self._token_rates) if self._token_rates else 0
        )

        return PerformanceMetrics(
            response_time_ms=avg_response,
            tokens_per_second=avg_tps,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            queue_size=len(self._response_times),
            active_requests=self._active_requests,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas completas."""
        if not self._response_times:
            return {
                "total_requests": self._total_requests,
                "active_requests": self._active_requests,
                "error_count": self._error_count,
                "error_rate": 0,
                "avg_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
            }

        times = sorted(self._response_times)
        n = len(times)

        return {
            "total_requests": self._total_requests,
            "active_requests": self._active_requests,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._total_requests),
            "avg_response_time_ms": sum(times) / n,
            "p95_response_time_ms": times[int(n * 0.95)],
            "p99_response_time_ms": times[int(n * 0.99)],
            "min_response_time_ms": min(times),
            "max_response_time_ms": max(times),
            "concurrency_limit": self._concurrency_limit,
            "auto_tune_enabled": self._auto_tune,
        }

    def on_alert(self, handler: Callable[[str], None]):
        """Registra handler de alertas."""
        self._alert_handlers.append(handler)

    def set_threshold(self, metric: str, value: float):
        """Configura umbral de alerta."""
        self._thresholds[metric] = value

    def reset(self):
        """Reinicia métricas."""
        self._response_times.clear()
        self._token_rates.clear()
        self._memory_usage.clear()
        self._request_counts.clear()
        self._active_requests = 0
        self._total_requests = 0
        self._error_count = 0


class TimingContext:
    """Context manager para medir tiempo de ejecución."""

    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
        self.operation = operation
        self.request_id = None
        self.start_time = None

    async def __aenter__(self):
        self.request_id = self.monitor.record_request_start()
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.time() - self.start_time) * 1000
        success = exc_type is None
        self.monitor.record_request_end(self.request_id, success, elapsed)


# Singleton global
_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Obtiene instancia singleton del monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor
