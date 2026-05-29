"""
Sovereign Metrics - Métricas y monitoreo del modo Soberano.

Features:
- Tracking del ratio DELEGATE/ORCHESTRATE
- Métricas de latencia por modo
- Detección de desviaciones del target 70/30
- Alertas cuando el sistema no cumple objetivos
"""
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .json_safe import safe_load, safe_save

logger = logging.getLogger("lilith.sovereign.metrics")


@dataclass
class ExecutionRecord:
    """Registro de una ejecución."""

    timestamp: float
    mode: str  # "delegate" | "orchestrate"
    latency_ms: float
    success: bool
    agent: Optional[str] = None
    complexity_score: Optional[int] = None
    channel: str = "unknown"


@dataclass
class DailyMetrics:
    """Métricas de un día."""

    date: str
    delegate_count: int = 0
    orchestrate_count: int = 0
    delegate_latency_sum: float = 0.0
    orchestrate_latency_sum: float = 0.0
    delegate_failures: int = 0
    orchestrate_failures: int = 0


class SovereignMetrics:
    """
    Sistema de métricas para el modo Soberano.

    Target: 70% DELEGATE, 30% ORCHESTRATE
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )

        # Archivo de métricas
        self._metrics_file = self.base_path / "Memory" / "sovereign_metrics.jsonl"
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # Configuración
        self.target_delegate_ratio = 0.70
        self.tolerance = 0.10  # ±10%

        # Estado en memoria
        self._today = datetime.now().strftime("%Y-%m-%d")
        self._daily: Dict[str, DailyMetrics] = {}
        self._recent_records: List[ExecutionRecord] = []
        self._max_recent = 1000

        # Cargar datos previos
        self._load_metrics()

        self._initialized = True
        logger.info("[SovereignMetrics] Inicializado")

    def record_execution(
        self,
        mode: str,
        latency_ms: float,
        success: bool = True,
        agent: Optional[str] = None,
        complexity_score: Optional[int] = None,
        channel: str = "unknown",
    ):
        """
        Registra una ejecución.

        Args:
            mode: "delegate" | "orchestrate"
            latency_ms: Tiempo de respuesta en ms
            success: Si la ejecución fue exitosa
            agent: Agente usado (para DELEGATE)
            complexity_score: Score de complejidad
            channel: Canal de origen
        """
        record = ExecutionRecord(
            timestamp=time.time(),
            mode=mode,
            latency_ms=latency_ms,
            success=success,
            agent=agent,
            complexity_score=complexity_score,
            channel=channel,
        )

        # Guardar en archivo
        self._append_record(record)

        # Actualizar en memoria
        self._recent_records.append(record)
        if len(self._recent_records) > self._max_recent:
            self._recent_records = self._recent_records[-self._max_recent :]

        # Actualizar métricas diarias
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily:
            self._daily[today] = DailyMetrics(date=today)

        daily = self._daily[today]
        if mode == "delegate":
            daily.delegate_count += 1
            daily.delegate_latency_sum += latency_ms
            if not success:
                daily.delegate_failures += 1
        else:
            daily.orchestrate_count += 1
            daily.orchestrate_latency_sum += latency_ms
            if not success:
                daily.orchestrate_failures += 1

    def _append_record(self, record: ExecutionRecord):
        """Agrega registro al archivo."""
        try:
            with open(self._metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("[SovereignMetrics] Error guardando métrica: %s", e)

    def _load_metrics(self):
        """Carga métricas previas."""
        if not self._metrics_file.exists():
            return

        try:
            with open(self._metrics_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        record = ExecutionRecord(**data)

                        # Agregar a recientes (últimos 1000)
                        self._recent_records.append(record)

                        # Actualizar daily
                        date = datetime.fromtimestamp(record.timestamp).strftime(
                            "%Y-%m-%d"
                        )
                        if date not in self._daily:
                            self._daily[date] = DailyMetrics(date=date)

                        daily = self._daily[date]
                        if record.mode == "delegate":
                            daily.delegate_count += 1
                            daily.delegate_latency_sum += record.latency_ms
                            if not record.success:
                                daily.delegate_failures += 1
                        else:
                            daily.orchestrate_count += 1
                            daily.orchestrate_latency_sum += record.latency_ms
                            if not record.success:
                                daily.orchestrate_failures += 1

                    except Exception:
                        pass
            # Mantener solo últimos 1000
            self._recent_records = self._recent_records[-self._max_recent :]

        except Exception as e:
            logger.error("[SovereignMetrics] Error cargando métricas: %s", e)

    def get_current_ratio(self) -> Dict[str, Any]:
        """
        Retorna el ratio actual DELEGATE/ORCHESTRATE.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self._daily.get(today, DailyMetrics(date=today))

        total = daily.delegate_count + daily.orchestrate_count
        if total == 0:
            return {
                "delegate_ratio": 0.0,
                "orchestrate_ratio": 0.0,
                "delegate_count": 0,
                "orchestrate_count": 0,
                "total": 0,
                "target": self.target_delegate_ratio,
                "within_tolerance": True,
            }

        delegate_ratio = daily.delegate_count / total
        orchestrate_ratio = daily.orchestrate_count / total

        # Verificar si está dentro de tolerancia
        diff = abs(delegate_ratio - self.target_delegate_ratio)
        within_tolerance = diff <= self.tolerance

        if not within_tolerance:
            logger.warning(
                "[SovereignMetrics] Ratio desviado: %.2f (target: %.2f, diff: %.2f)",
                delegate_ratio,
                self.target_delegate_ratio,
                diff,
            )

        return {
            "delegate_ratio": delegate_ratio,
            "orchestrate_ratio": orchestrate_ratio,
            "delegate_count": daily.delegate_count,
            "orchestrate_count": daily.orchestrate_count,
            "total": total,
            "target": self.target_delegate_ratio,
            "within_tolerance": within_tolerance,
            "deviation": diff,
        }

    def get_latency_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas de latencia por modo.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        daily = self._daily.get(today, DailyMetrics(date=today))

        delegate_avg = (
            daily.delegate_latency_sum / daily.delegate_count
            if daily.delegate_count > 0
            else 0
        )
        orchestrate_avg = (
            daily.orchestrate_latency_sum / daily.orchestrate_count
            if daily.orchestrate_count > 0
            else 0
        )

        return {
            "delegate": {
                "avg_ms": delegate_avg,
                "count": daily.delegate_count,
                "failures": daily.delegate_failures,
            },
            "orchestrate": {
                "avg_ms": orchestrate_avg,
                "count": daily.orchestrate_count,
                "failures": daily.orchestrate_failures,
            },
        }

    def get_health_report(self) -> Dict[str, Any]:
        """
        Retorna reporte de salud completo.
        """
        ratio = self.get_current_ratio()
        latency = self.get_latency_stats()

        # Determinar estado
        status = "healthy"
        issues = []

        if not ratio["within_tolerance"]:
            status = "warning"
            issues.append(
                f"Delegate ratio {ratio['delegate_ratio']:.2f} deviated from target {ratio['target']:.2f}"
            )

        if latency["delegate"]["avg_ms"] > 2000:
            status = "warning"
            issues.append(
                f"High delegate latency: {latency['delegate']['avg_ms']:.0f}ms"
            )

        if latency["orchestrate"]["avg_ms"] > 10000:
            status = "critical"
            issues.append(
                f"High orchestrate latency: {latency['orchestrate']['avg_ms']:.0f}ms"
            )

        failure_rate = 0
        total = ratio["total"]
        if total > 0:
            failures = (
                latency["delegate"]["failures"] + latency["orchestrate"]["failures"]
            )
            failure_rate = failures / total

        if failure_rate > 0.05:
            status = "critical"
            issues.append(f"High failure rate: {failure_rate:.2%}")

        return {
            "status": status,
            "ratio": ratio,
            "latency": latency,
            "failure_rate": failure_rate,
            "issues": issues,
            "timestamp": time.time(),
        }

    def get_recommendations(self) -> List[str]:
        """
        Retorna recomendaciones basadas en métricas.
        """
        recommendations = []
        ratio = self.get_current_ratio()
        latency = self.get_latency_stats()

        # Recomendaciones de ratio
        if ratio["delegate_ratio"] < self.target_delegate_ratio - self.tolerance:
            recommendations.append(
                "Increase DELEGATE threshold: too many tasks going to ORCHESTRATE"
            )
        elif ratio["delegate_ratio"] > self.target_delegate_ratio + self.tolerance:
            recommendations.append(
                "Decrease DELEGATE threshold: too many tasks being delegated"
            )

        # Recomendaciones de latencia
        if latency["delegate"]["avg_ms"] > 2000:
            recommendations.append(
                "Delegate latency is high - check Vanaheim agent performance"
            )

        if latency["orchestrate"]["avg_ms"] > 10000:
            recommendations.append(
                "Orchestrate latency is high - consider optimizing DAG execution"
            )

        return recommendations


# Singleton
_metrics_instance: Optional[SovereignMetrics] = None


def get_sovereign_metrics(base_path: Optional[Path] = None) -> SovereignMetrics:
    """Obtiene instancia singleton."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = SovereignMetrics(base_path)
    return _metrics_instance


def record_sovereign_execution(
    mode: str,
    latency_ms: float,
    success: bool = True,
    agent: Optional[str] = None,
    complexity_score: Optional[int] = None,
    channel: str = "unknown",
):
    """Función helper para registrar ejecución."""
    metrics = get_sovereign_metrics()
    metrics.record_execution(
        mode, latency_ms, success, agent, complexity_score, channel
    )
