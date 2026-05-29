"""
Sistema de Alertas - Notificaciones automáticas para eventos críticos

Módulo para enviar alertas cuando:
- Un subsistema falla (health check)
- Recursos del sistema están críticos (CPU, disco, RAM)
- Se detectan anomalías en el uso

v4.2.4: Sistema de alertas integrado con HealthMonitor

Uso:
    from core.alerts import AlertManager, AlertSeverity

    alert_manager = AlertManager()
    await alert_manager.check_and_alert(health_status)
"""
import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Niveles de severidad de alertas."""

    INFO = "info"  # Informativo, no requiere acción
    WARNING = "warning"  # Atención recomendada
    CRITICAL = "critical"  # Acción inmediata requerida


class AlertChannel(Enum):
    """Canales de notificación disponibles."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    CONSOLE = "console"
    FILE = "file"


@dataclass
class Alert:
    """Una alerta individual."""

    id: str
    severity: AlertSeverity
    title: str
    message: str
    source: str  # Sistema/componente que generó la alerta
    timestamp: datetime
    acknowledged: bool = False
    channels_sent: List[AlertChannel] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.channels_sent is None:
            self.channels_sent = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "channels_sent": [c.value for c in self.channels_sent],
            "metadata": self.metadata,
        }


@dataclass
class AlertThreshold:
    """Umbral para generar alertas automáticas."""

    metric: str  # cpu_percent, memory_percent, disk_percent, etc.
    warning_threshold: float
    critical_threshold: float
    duration_seconds: int = 0  # Tiempo que debe superar el umbral
    cooldown_minutes: int = 30  # Tiempo entre alertas repetidas


class AlertManager:
    """
    Manager central de alertas.

    Responsabilidades:
    - Evaluar condiciones y generar alertas
    - Enviar a múltiples canales (Telegram, Discord, etc.)
    - Rate limiting de alertas (evitar spam)
    - Persistencia de alertas históricas
    """

    # Umbrales por defecto
    DEFAULT_THRESHOLDS = [
        AlertThreshold("cpu_percent", 70, 90, duration_seconds=60, cooldown_minutes=30),
        AlertThreshold(
            "memory_percent", 80, 95, duration_seconds=60, cooldown_minutes=30
        ),
        AlertThreshold("disk_percent", 80, 90, duration_seconds=0, cooldown_minutes=60),
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """
        Inicializar el AlertManager.

        Args:
            config_path: Ruta al archivo de configuración de alertas
        """
        self.config = self._load_config(config_path)
        self.thresholds = self._load_thresholds()

        # Estado interno
        self._alert_history: List[Alert] = []
        self._last_alert_time: Dict[str, datetime] = {}  # Para cooldowns
        self._metric_history: Dict[str, List[tuple]] = {}  # Para duración

        # Handlers de canales
        self._channel_handlers: Dict[AlertChannel, Callable] = {}
        self._setup_default_handlers()

        # Referencia al health monitor
        self._health_monitor = None

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """Cargar configuración desde archivo o usar defaults."""
        default_config = {
            "enabled": True,
            "channels": ["telegram", "console"],  # Canales activos
            "telegram": {
                "enabled": True,
                "chat_id": None,  # Usa TELEGRAM_OWNER_CHAT_ID por defecto
                "min_severity": "warning",
            },
            "discord": {
                "enabled": False,
                "webhook_url": None,
                "min_severity": "warning",
            },
            "file": {"enabled": True, "path": "Data/alerts.jsonl"},
            "rate_limiting": {"max_alerts_per_hour": 20, "group_similar": True},
        }

        if config_path and config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge con defaults
                    default_config.update(loaded)
            except Exception as e:
                logger.warning(f"Failed to load alert config: {e}, using defaults")

        return default_config

    def _load_thresholds(self) -> List[AlertThreshold]:
        """Cargar umbrales desde config o usar defaults."""
        thresholds = []
        config_thresholds = self.config.get("thresholds", [])

        if config_thresholds:
            for t in config_thresholds:
                thresholds.append(
                    AlertThreshold(
                        metric=t["metric"],
                        warning_threshold=t["warning"],
                        critical_threshold=t["critical"],
                        duration_seconds=t.get("duration_seconds", 0),
                        cooldown_minutes=t.get("cooldown_minutes", 30),
                    )
                )
        else:
            thresholds = self.DEFAULT_THRESHOLDS.copy()

        return thresholds

    def _setup_default_handlers(self):
        """Configurar handlers por defecto para cada canal."""
        self._channel_handlers[AlertChannel.CONSOLE] = self._send_console
        self._channel_handlers[AlertChannel.FILE] = self._send_file
        self._channel_handlers[AlertChannel.TELEGRAM] = self._send_telegram
        self._channel_handlers[AlertChannel.DISCORD] = self._send_discord

    def register_channel_handler(self, channel: AlertChannel, handler: Callable):
        """
        Registrar un handler custom para un canal.

        Args:
            channel: Canal a registrar
            handler: Función async que recibe (alert: Alert) -> bool
        """
        self._channel_handlers[channel] = handler

    def set_health_monitor(self, health_monitor):
        """Establecer referencia al health monitor."""
        self._health_monitor = health_monitor

    async def check_and_alert(self, health_status=None):
        """
        Verificar condiciones de alerta y enviar si es necesario.

        Args:
            health_status: Estado de salud del sistema (opcional)
        """
        if not self.config.get("enabled", True):
            return

        # Si no se proporciona health_status, obtener del monitor
        if health_status is None and self._health_monitor:
            try:
                health_status = await self._health_monitor.check_all()
            except Exception as e:
                logger.error(f"Failed to get health status: {e}")
                return

        if not health_status:
            return

        # Verificar cada subsistema
        for check in health_status.checks:
            await self._evaluate_health_check(check)

        # Verificar umbrales de recursos
        await self._evaluate_resource_thresholds(health_status)

    async def _evaluate_health_check(self, check):
        """Evaluar si un health check debe generar alerta."""
        # Solo alertar si está unhealthy
        from core.health_monitor import HealthStatus

        if check.status == HealthStatus.HEALTHY:
            return

        severity = (
            AlertSeverity.WARNING
            if check.status == HealthStatus.DEGRADED
            else AlertSeverity.CRITICAL
        )

        alert = Alert(
            id=f"health_{check.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            severity=severity,
            title=f"Health Check Failed: {check.name}",
            message=check.message
            or f"El subsistema {check.name} reporta estado: {check.status.value}",
            source=f"health_check.{check.name}",
            timestamp=datetime.now(),
            metadata={
                "status": check.status.value,
                "latency_ms": check.latency_ms,
                "details": check.details,
            },
        )

        await self._send_alert(alert)

    async def _evaluate_resource_thresholds(self, health_status):
        """Evaluar umbrales de recursos del sistema."""
        # Extraer métricas de recursos si están disponibles
        for threshold in self.thresholds:
            # Buscar métrica en los checks de health
            value = self._extract_metric(health_status, threshold.metric)

            if value is None:
                continue

            # Registrar métrica para análisis de duración
            await self._record_metric(threshold.metric, value)

            # Determinar severidad
            if value >= threshold.critical_threshold:
                severity = AlertSeverity.CRITICAL
            elif value >= threshold.warning_threshold:
                severity = AlertSeverity.WARNING
            else:
                continue

            # Verificar duración si aplica
            if threshold.duration_seconds > 0:
                if not self._check_duration(
                    threshold.metric, threshold.duration_seconds
                ):
                    continue

            # Verificar cooldown
            if self._is_in_cooldown(threshold.metric, threshold.cooldown_minutes):
                continue

            # Crear alerta
            alert = Alert(
                id=f"resource_{threshold.metric}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                severity=severity,
                title=f"Recurso crítico: {threshold.metric}",
                message=f"{threshold.metric} está en {value:.1f}% (umbral: {threshold.warning_threshold}%)",
                source=f"resource.{threshold.metric}",
                timestamp=datetime.now(),
                metadata={
                    "metric": threshold.metric,
                    "value": value,
                    "warning_threshold": threshold.warning_threshold,
                    "critical_threshold": threshold.critical_threshold,
                },
            )

            await self._send_alert(alert)

    def _extract_metric(self, health_status, metric_name: str) -> Optional[float]:
        """Extraer valor de métrica del estado de salud."""
        # Buscar en detalles de los checks
        for check in health_status.checks:
            if metric_name.replace("_", "") in check.name.lower():
                # Intentar extraer de details
                if hasattr(check, "details") and check.details:
                    for key in ["percent", "value", "usage", metric_name]:
                        if key in check.details:
                            return float(check.details[key])
        return None

    async def _record_metric(self, metric: str, value: float):
        """Registrar métrica para análisis de duración."""
        now = datetime.now()
        if metric not in self._metric_history:
            self._metric_history[metric] = []

        self._metric_history[metric].append((now, value))

        # Limpiar entradas antiguas (> 5 minutos)
        cutoff = now - timedelta(minutes=5)
        self._metric_history[metric] = [
            (t, v) for t, v in self._metric_history[metric] if t > cutoff
        ]

    def _check_duration(self, metric: str, duration_seconds: int) -> bool:
        """Verificar si la condición se mantiene por la duración requerida."""
        if metric not in self._metric_history:
            return False

        history = self._metric_history[metric]
        if len(history) < 2:
            return False

        # Verificar si el tiempo transcurrido cubre la duración
        first_time = history[0][0]
        last_time = history[-1][0]
        elapsed = (last_time - first_time).total_seconds()

        return elapsed >= duration_seconds

    def _is_in_cooldown(self, source: str, cooldown_minutes: int) -> bool:
        """Verificar si una fuente está en período de cooldown."""
        if source not in self._last_alert_time:
            return False

        last_time = self._last_alert_time[source]
        elapsed = (datetime.now() - last_time).total_seconds() / 60

        return elapsed < cooldown_minutes

    async def _send_alert(self, alert: Alert):
        """Enviar alerta a todos los canales configurados."""
        channels_config = self.config.get("channels", ["console"])

        for channel_name in channels_config:
            try:
                channel = AlertChannel(channel_name)

                # Verificar si el canal está habilitado
                channel_config = self.config.get(channel_name, {})
                if not channel_config.get("enabled", True):
                    continue

                # Verificar severidad mínima
                min_severity = channel_config.get("min_severity", "info")
                severity_order = {"info": 0, "warning": 1, "critical": 2}

                if severity_order.get(alert.severity.value, 0) < severity_order.get(
                    min_severity, 0
                ):
                    continue

                # Enviar
                handler = self._channel_handlers.get(channel)
                if handler:
                    success = await handler(alert)
                    if success:
                        alert.channels_sent.append(channel)

            except Exception as e:
                logger.error(f"Failed to send alert to {channel_name}: {e}")

        # Guardar en historial
        self._alert_history.append(alert)
        self._last_alert_time[alert.source] = datetime.now()

        # Persistir alerta importante
        if alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
            await self._persist_alert(alert)

    async def _send_console(self, alert: Alert) -> bool:
        """Enviar alerta a consola."""
        emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}

        print(
            f"\n{emoji.get(alert.severity.value, '🔔')} [{alert.severity.value.upper()}] {alert.title}"
        )
        print(f"   {alert.message}")
        print(
            f"   Source: {alert.source} | Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        return True

    async def _send_file(self, alert: Alert) -> bool:
        """Guardar alerta en archivo."""
        try:
            file_path = self.config.get("file", {}).get("path", "Data/alerts.jsonl")
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")

            return True
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")
            return False

    async def _send_telegram(self, alert: Alert) -> bool:
        """Enviar alerta por Telegram."""
        try:
            # Obtener chat_id
            chat_id = self.config.get("telegram", {}).get("chat_id")
            if not chat_id:
                chat_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID")

            if not chat_id:
                logger.warning("No Telegram chat_id configured for alerts")
                return False

            # Emoji según severidad
            emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
            icon = emoji.get(alert.severity.value, "🔔")

            # Construir mensaje
            text = f"{icon} *Alerta {alert.severity.value.upper()}*\n\n"
            text += f"*{alert.title}*\n"
            text += f"{alert.message}\n\n"
            text += f"🕐 {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"📍 {alert.source}"

            # Enviar (usar función de telegram_bot si está disponible)
            try:
                from Telegram.telegram_bot import TelegramBot

                bot = TelegramBot()
                await bot.send_message(
                    chat_id=chat_id, text=text, parse_mode="Markdown"
                )
                return True
            except ImportError:
                # Fallback: usar requests directo
                import aiohttp

                token = os.environ.get("TELEGRAM_BOT_TOKEN")
                if not token:
                    return False

                url = f"https://api.telegram.org/bot{token}/sendMessage"
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json={
                            "chat_id": chat_id,
                            "text": text,
                            "parse_mode": "Markdown",
                        },
                    ) as response:
                        return response.status == 200

        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

    async def _send_discord(self, alert: Alert) -> bool:
        """Enviar alerta por Discord webhook."""
        try:
            webhook_url = self.config.get("discord", {}).get("webhook_url")
            if not webhook_url:
                logger.warning("No Discord webhook configured for alerts")
                return False

            # Color según severidad
            colors = {
                "info": 3447003,  # Azul
                "warning": 16776960,  # Amarillo
                "critical": 15158332,  # Rojo
            }

            embed = {
                "title": alert.title,
                "description": alert.message,
                "color": colors.get(alert.severity.value, 0),
                "timestamp": alert.timestamp.isoformat(),
                "footer": {"text": f"Source: {alert.source}"},
                "fields": [],
            }

            # Agregar metadata como fields
            for key, value in alert.metadata.items():
                if isinstance(value, (str, int, float)):
                    embed["fields"].append(
                        {
                            "name": key.replace("_", " ").title(),
                            "value": str(value),
                            "inline": True,
                        }
                    )

            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url, json={"embeds": [embed]}
                ) as response:
                    return response.status == 204

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    async def _persist_alert(self, alert: Alert):
        """Persistir alerta en MuninnDB si está disponible."""
        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()
            muninn.add_event(
                content=json.dumps(alert.to_dict(), ensure_ascii=False),
                event_type="system_alert",
                tags=["alert", alert.severity.value, alert.source],
                metadata={
                    "severity": alert.severity.value,
                    "source": alert.source,
                    "acknowledged": alert.acknowledged,
                },
            )
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to persist alert to Muninn: {e}")

    def get_recent_alerts(
        self, limit: int = 50, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Obtener alertas recientes."""
        alerts = self._alert_history

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marcar una alerta como reconocida."""
        for alert in self._alert_history:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de alertas."""
        total = len(self._alert_history)
        by_severity = {
            "info": len(
                [a for a in self._alert_history if a.severity == AlertSeverity.INFO]
            ),
            "warning": len(
                [a for a in self._alert_history if a.severity == AlertSeverity.WARNING]
            ),
            "critical": len(
                [a for a in self._alert_history if a.severity == AlertSeverity.CRITICAL]
            ),
        }
        unacknowledged = len([a for a in self._alert_history if not a.acknowledged])

        return {
            "total_alerts": total,
            "by_severity": by_severity,
            "unacknowledged": unacknowledged,
            "channels_configured": self.config.get("channels", []),
            "thresholds_configured": len(self.thresholds),
        }


# Singleton global
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(config_path: Optional[Path] = None) -> AlertManager:
    """Obtener instancia singleton del AlertManager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(config_path=config_path)
    return _alert_manager
