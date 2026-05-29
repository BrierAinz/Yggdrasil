"""
Custom Metrics - Métricas de negocio personalizadas

v5.0-Fase4C: Métricas custom para dashboards y alerting.
"""
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("lilith.observability.metrics")


class MetricType(Enum):
    """Tipos de métricas."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """Punto de métrica."""

    value: float
    timestamp: str
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """Métrica con series temporales."""

    name: str
    type: MetricType
    description: str
    unit: str = ""
    data: List[MetricPoint] = field(default_factory=list)
    aggregations: Dict[str, float] = field(default_factory=dict)


class MetricsRegistry:
    """
    Registro de métricas custom.

    Features:
    - Múltiples tipos de métricas
    - Labels y dimensiones
    - Agregaciones automáticas
    - Retención configurable
    """

    def __init__(self, retention_hours: int = 24, storage_path: Optional[Path] = None):
        self.metrics: Dict[str, Metric] = {}
        self.retention_hours = retention_hours
        self.storage_path = storage_path or Path("Data/metrics")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_handlers: List[Callable] = []
        self.lock = asyncio.Lock()

    def register_metric(
        self, name: str, metric_type: MetricType, description: str, unit: str = ""
    ) -> Metric:
        """Registra una nueva métrica."""
        if name in self.metrics:
            return self.metrics[name]

        metric = Metric(name=name, type=metric_type, description=description, unit=unit)

        self.metrics[name] = metric
        return metric

    async def record(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Registra un valor de métrica."""
        if name not in self.metrics:
            logger.warning(f"Metric {name} not registered")
            return

        point = MetricPoint(
            value=value, timestamp=datetime.utcnow().isoformat(), labels=labels or {}
        )

        async with self.lock:
            self.metrics[name].data.append(point)
            self._cleanup_old_data(name)
            self._update_aggregations(name)

        # Verificar alertas
        await self._check_alerts(name, value, labels)

    def _cleanup_old_data(self, name: str):
        """Limpia datos antiguos."""
        cutoff = (datetime.utcnow() - timedelta(hours=self.retention_hours)).isoformat()
        self.metrics[name].data = [
            p for p in self.metrics[name].data if p.timestamp > cutoff
        ]

    def _update_aggregations(self, name: str):
        """Actualiza agregaciones de la métrica."""
        metric = self.metrics[name]
        values = [p.value for p in metric.data]

        if not values:
            return

        if metric.type == MetricType.COUNTER:
            metric.aggregations["total"] = sum(values)
        elif metric.type == MetricType.GAUGE:
            metric.aggregations["current"] = values[-1]
            metric.aggregations["min"] = min(values)
            metric.aggregations["max"] = max(values)
            metric.aggregations["avg"] = sum(values) / len(values)
        elif metric.type == MetricType.HISTOGRAM:
            metric.aggregations["count"] = len(values)
            metric.aggregations["sum"] = sum(values)
            metric.aggregations["avg"] = sum(values) / len(values)
            metric.aggregations["p50"] = self._percentile(values, 50)
            metric.aggregations["p95"] = self._percentile(values, 95)
            metric.aggregations["p99"] = self._percentile(values, 99)

    def _percentile(self, values: List[float], p: float) -> float:
        """Calcula percentil."""
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

    def get_metric(self, name: str) -> Optional[Metric]:
        """Obtiene una métrica."""
        return self.metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtiene todas las métricas."""
        return {
            name: {
                "name": m.name,
                "type": m.type.value,
                "description": m.description,
                "unit": m.unit,
                "aggregations": m.aggregations,
                "data_points": len(m.data),
            }
            for name, m in self.metrics.items()
        }

    def query(
        self,
        name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        labels_filter: Optional[Dict[str, str]] = None,
    ) -> List[MetricPoint]:
        """Consulta puntos de métrica."""
        if name not in self.metrics:
            return []

        data = self.metrics[name].data

        if start_time:
            data = [p for p in data if p.timestamp >= start_time]
        if end_time:
            data = [p for p in data if p.timestamp <= end_time]
        if labels_filter:
            data = [
                p
                for p in data
                if all(p.labels.get(k) == v for k, v in labels_filter.items())
            ]

        return data

    async def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,  # "gt", "lt", "eq"
        threshold: float,
        duration_minutes: int = 5,
    ):
        """Añade una regla de alerta."""
        rule = {
            "id": f"alert_{name}_{metric_name}",
            "name": name,
            "metric": metric_name,
            "condition": condition,
            "threshold": threshold,
            "duration_minutes": duration_minutes,
            "created_at": datetime.utcnow().isoformat(),
        }

        self.alert_rules.append(rule)

    async def _check_alerts(
        self, metric_name: str, value: float, labels: Optional[Dict[str, str]]
    ):
        """Verifica si se disparan alertas."""
        for rule in self.alert_rules:
            if rule["metric"] != metric_name:
                continue

            triggered = False
            if rule["condition"] == "gt" and value > rule["threshold"]:
                triggered = True
            elif rule["condition"] == "lt" and value < rule["threshold"]:
                triggered = True
            elif rule["condition"] == "eq" and value == rule["threshold"]:
                triggered = True

            if triggered:
                await self._trigger_alert(rule, value, labels)

    async def _trigger_alert(
        self, rule: Dict[str, Any], value: float, labels: Optional[Dict[str, str]]
    ):
        """Dispara una alerta."""
        alert_data = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "metric": rule["metric"],
            "value": value,
            "threshold": rule["threshold"],
            "condition": rule["condition"],
            "labels": labels,
            "timestamp": datetime.utcnow().isoformat(),
        }

        for handler in self.alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def register_alert_handler(self, handler: Callable):
        """Registra un handler de alertas."""
        self.alert_handlers.append(handler)


# Singleton
_registry_instance: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Obtiene el singleton del MetricsRegistry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = MetricsRegistry()
    return _registry_instance
