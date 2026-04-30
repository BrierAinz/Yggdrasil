"""
Sistema de Health Checks Unificado para Lilith v4.2.4

Módulo centralizado para verificar el estado de todos los servicios
y dependencias del ecosistema Lilith.

Uso:
    from core.health_monitor import HealthMonitor, health_check

    # Check completo
    status = await HealthMonitor.check_all()

    # Check individual
    db_status = await HealthMonitor.check_muninndb()
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil


class HealthStatus(Enum):
    """Estados posibles de un componente de salud."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Resultado de un health check individual."""

    name: str
    status: HealthStatus
    response_time_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "response_time_ms": round(self.response_time_ms, 2),
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SystemHealth:
    """Estado completo del sistema."""

    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthMonitor:
    """
    Monitor de salud unificado para Lilith.

    Verifica:
    - MuninnDB (conectividad y respuesta)
    - APIs de terceros (Kimi, OpenRouter)
    - Recursos del sistema (disco, RAM, CPU)
    - Servicios internos (Discord Bot, Telegram Bot)

    v4.2.8: Agregado caché de resultados (TTL 30s)
    """

    _check_registry: Dict[str, Callable[[], Any]] = {}
    _timeout_seconds: float = 5.0
    _cache_ttl_seconds: int = 30  # TTL para caché de health checks

    @classmethod
    def register(cls, name: str, check_func: Callable[[], Any]) -> None:
        """Registrar un nuevo check personalizado."""
        cls._check_registry[name] = check_func

    @classmethod
    async def check_all(cls) -> SystemHealth:
        """Ejecutar todos los health checks disponibles."""
        # v4.2.8: Verificar caché primero
        try:
            from src.core.cache import get_cache

            cache = get_cache()
            cached_health = await cache.get(
                "health_check:all", namespace="health_checks"
            )
            if cached_health:
                logger.debug(
                    "HealthMonitor: Cache hit (TTL %ds)", cls._cache_ttl_seconds
                )
                # Reconstruir SystemHealth desde caché
                checks = [
                    HealthCheckResult(
                        name=c["name"],
                        status=HealthStatus(c["status"]),
                        response_time_ms=c["response_time_ms"],
                        message=c["message"],
                        details=c.get("details", {}),
                        timestamp=datetime.fromisoformat(c["timestamp"]),
                    )
                    for c in cached_health["checks"]
                ]
                return SystemHealth(
                    overall_status=HealthStatus(cached_health["overall_status"]),
                    checks=checks,
                    metadata=cached_health.get("metadata", {}),
                    timestamp=datetime.fromisoformat(cached_health["timestamp"]),
                )
        except Exception as e:
            logger.debug("HealthMonitor: Cache lookup failed: %s", e)

        checks = []

        # Checks paralelos
        tasks = [
            cls.check_muninndb(),
            cls.check_kimi_api(),
            cls.check_openrouter_api(),
            cls.check_system_resources(),
            cls.check_disk_space(),
            cls.check_environment(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                checks.append(
                    HealthCheckResult(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message=f"Error: {str(result)}",
                    )
                )
            else:
                checks.append(result)

        # Checks personalizados registrados
        for name, check_func in cls._check_registry.items():
            try:
                start = time.time()
                result = await asyncio.wait_for(
                    check_func()
                    if asyncio.iscoroutinefunction(check_func)
                    else asyncio.to_thread(check_func),
                    timeout=cls._timeout_seconds,
                )
                response_time = (time.time() - start) * 1000

                checks.append(
                    HealthCheckResult(
                        name=name,
                        status=HealthStatus.HEALTHY
                        if result
                        else HealthStatus.UNHEALTHY,
                        response_time_ms=response_time,
                        message="OK" if result else "Failed",
                    )
                )
            except Exception as e:
                checks.append(
                    HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message=f"Error: {str(e)}",
                    )
                )

        # Determinar estado general
        overall = cls._determine_overall_status(checks)

        # Metadata del sistema
        metadata = {
            "hostname": os.environ.get("COMPUTERNAME", "unknown"),
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "lilith_version": "4.2.8",
            "checks_count": len(checks),
            "cached": False,
        }

        health = SystemHealth(overall_status=overall, checks=checks, metadata=metadata)

        # v4.2.8: Guardar en caché
        try:
            from src.core.cache import get_cache

            cache = get_cache()
            await cache.set(
                "health_check:all",
                health.to_dict(),
                namespace="health_checks",
                ttl=cls._cache_ttl_seconds,
                tags={"health", "system_status"},
            )
            logger.debug(
                "HealthMonitor: Results cached (TTL %ds)", cls._cache_ttl_seconds
            )
        except Exception as e:
            logger.debug("HealthMonitor: Cache store failed: %s", e)

        return health

    @classmethod
    def _determine_overall_status(cls, checks: List[HealthCheckResult]) -> HealthStatus:
        """Determinar el estado general basado en todos los checks."""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in checks]

        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    @classmethod
    async def check_muninndb(cls) -> HealthCheckResult:
        """Verificar conectividad con MuninnDB."""
        start = time.time()

        try:
            from core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory()
            # Intentar una operación simple de ping
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: muninn.get_recent_events(limit=1))

            response_time = (time.time() - start) * 1000

            return HealthCheckResult(
                name="muninndb",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message="MuninnDB responde correctamente",
                details={
                    "db_path": str(muninn.db_path)
                    if hasattr(muninn, "db_path")
                    else "unknown"
                },
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            return HealthCheckResult(
                name="muninndb",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"MuninnDB no disponible: {str(e)}",
                details={"error_type": type(e).__name__},
            )

    @classmethod
    async def check_kimi_api(cls) -> HealthCheckResult:
        """Verificar disponibilidad de Kimi API."""
        start = time.time()

        try:
            import httpx

            api_key = os.environ.get("CRYSTAL_KIMI_API_KEY") or os.environ.get(
                "KIMI_API_KEY"
            )

            if not api_key:
                response_time = (time.time() - start) * 1000
                return HealthCheckResult(
                    name="kimi_api",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    message="API key no configurada (CRYSTAL_KIMI_API_KEY)",
                    details={"configured": False},
                )

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.kimi.com/coding/v1/models",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                )

            response_time = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "unknown") for m in data.get("data", [])]

                return HealthCheckResult(
                    name="kimi_api",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=f"API responde ({len(models)} modelos disponibles)",
                    details={"configured": True, "models": models[:3]},
                )
            else:
                return HealthCheckResult(
                    name="kimi_api",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    message=f"API error: HTTP {response.status_code}",
                    details={"status_code": response.status_code},
                )

        except Exception as e:
            response_time = (time.time() - start) * 1000
            return HealthCheckResult(
                name="kimi_api",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Error conectando a Kimi: {str(e)}",
                details={"error_type": type(e).__name__},
            )

    @classmethod
    async def check_openrouter_api(cls) -> HealthCheckResult:
        """Verificar disponibilidad de OpenRouter (fallback)."""
        start = time.time()

        try:
            import httpx

            api_key = os.environ.get("OPENROUTER_API_KEY")

            if not api_key:
                response_time = (time.time() - start) * 1000
                return HealthCheckResult(
                    name="openrouter_api",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=response_time,
                    message="API key no configurada (no es crítico - es fallback)",
                    details={"configured": False, "is_fallback": True},
                )

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )

            response_time = (time.time() - start) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    name="openrouter_api",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message="OpenRouter disponible (fallback)",
                    details={"configured": True, "is_fallback": True},
                )
            else:
                return HealthCheckResult(
                    name="openrouter_api",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    message=f"OpenRouter error: HTTP {response.status_code}",
                    details={"status_code": response.status_code, "is_fallback": True},
                )

        except Exception as e:
            response_time = (time.time() - start) * 1000
            return HealthCheckResult(
                name="openrouter_api",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                message=f"OpenRouter no disponible: {str(e)}",
                details={"error_type": type(e).__name__, "is_fallback": True},
            )

    @classmethod
    async def check_system_resources(cls) -> HealthCheckResult:
        """Verificar uso de CPU y RAM."""
        start = time.time()

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # RAM
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            ram_available_gb = memory.available / (1024**3)
            ram_total_gb = memory.total / (1024**3)

            response_time = (time.time() - start) * 1000

            # Determinar estado
            if cpu_percent > 90 or ram_percent > 95:
                status = HealthStatus.UNHEALTHY
                message = f"CRÍTICO: CPU {cpu_percent}%, RAM {ram_percent}%"
            elif cpu_percent > 70 or ram_percent > 85:
                status = HealthStatus.DEGRADED
                message = f"Alto uso: CPU {cpu_percent}%, RAM {ram_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Normal: CPU {cpu_percent}%, RAM {ram_percent}%"

            return HealthCheckResult(
                name="system_resources",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "cpu_count": cpu_count,
                    "ram_percent": ram_percent,
                    "ram_available_gb": round(ram_available_gb, 2),
                    "ram_total_gb": round(ram_total_gb, 2),
                },
            )

        except Exception as e:
            response_time = (time.time() - start) * 1000
            return HealthCheckResult(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Error leyendo recursos: {str(e)}",
                details={"error_type": type(e).__name__},
            )

    @classmethod
    async def check_disk_space(cls) -> HealthCheckResult:
        """Verificar espacio disponible en disco."""
        start = time.time()

        try:
            disk = psutil.disk_usage("/")
            percent_used = disk.percent
            free_gb = disk.free / (1024**3)
            total_gb = disk.total / (1024**3)

            response_time = (time.time() - start) * 1000

            # Determinar estado
            if percent_used > 95 or free_gb < 1:
                status = HealthStatus.UNHEALTHY
                message = f"CRÍTICO: {free_gb:.1f}GB libre ({percent_used}% usado)"
            elif percent_used > 85 or free_gb < 5:
                status = HealthStatus.DEGRADED
                message = f"Bajo espacio: {free_gb:.1f}GB libre"
            else:
                status = HealthStatus.HEALTHY
                message = f"OK: {free_gb:.1f}GB libre ({percent_used}% usado)"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "percent_used": percent_used,
                },
            )

        except Exception as e:
            response_time = (time.time() - start) * 1000
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Error leyendo disco: {str(e)}",
                details={"error_type": type(e).__name__},
            )

    @classmethod
    async def check_environment(cls) -> HealthCheckResult:
        """Verificar variables de entorno críticas."""
        start = time.time()

        critical_vars = [
            "DISCORD_TOKEN",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_OWNER_CHAT_ID",
            "LILITH_INTERNAL_TOKEN",
        ]

        optional_vars = ["CRYSTAL_KIMI_API_KEY", "KIMI_API_KEY", "OPENROUTER_API_KEY"]

        missing_critical = [v for v in critical_vars if not os.environ.get(v)]
        missing_optional = [v for v in optional_vars if not os.environ.get(v)]

        response_time = (time.time() - start) * 1000

        if missing_critical:
            return HealthCheckResult(
                name="environment",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Variables críticas faltantes: {', '.join(missing_critical)}",
                details={
                    "missing_critical": missing_critical,
                    "missing_optional": missing_optional,
                    "configured": False,
                },
            )

        return HealthCheckResult(
            name="environment",
            status=HealthStatus.HEALTHY,
            response_time_ms=response_time,
            message="Todas las variables críticas configuradas",
            details={
                "missing_critical": [],
                "missing_optional": missing_optional,
                "configured": True,
            },
        )

    @classmethod
    async def check_all_with_alerts(cls, alert_manager=None) -> SystemHealth:
        """
        Ejecutar todos los health checks y enviar alertas si es necesario.

        Args:
            alert_manager: Instancia de AlertManager (opcional)

        Returns:
            SystemHealth con el estado del sistema
        """
        # Ejecutar checks
        health = await cls.check_all()

        # Enviar alertas si hay alert manager
        if alert_manager:
            try:
                await alert_manager.check_and_alert(health)
            except Exception as e:
                logger.error(f"Failed to process alerts: {e}")

        return health


# Instancia global para uso rápido
health_check = HealthMonitor()
