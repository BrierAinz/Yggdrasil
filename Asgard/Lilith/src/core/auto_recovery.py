"""
Lilith 4.1 — A.1 Auto-Recovery Manager.
Monitorea subsistemas críticos y reintenta recuperación automática.
Se ejecuta como job en el TaskScheduler cada N segundos.
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("lilith.auto_recovery")


def _load_config(base_path: Path) -> Dict[str, Any]:
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "auto_recovery.json", default={})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


class AutoRecoveryManager:
    """
    A.1 — Monitorea y auto-recupera subsistemas críticos de Lilith.
    Notifica al owner en caso de fallo o recuperación exitosa.
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._failure_counts: Dict[str, int] = {}  # subsistema → intentos fallidos
        self._last_status: Dict[str, str] = {}  # subsistema → "healthy|unhealthy"

    async def run_check_cycle(self) -> Dict[str, Any]:
        """
        Ejecuta un ciclo de health check y recuperación.
        Retorna resumen de acciones tomadas.
        """
        cfg = _load_config(self.base_path)
        if not cfg.get("enabled", True):
            return {}

        max_retries = int(cfg.get("retry_attempts", 3))
        critical = list(cfg.get("critical_subsystems", ["muninn", "discord_bot"]))

        # Obtener estados actuales via health API
        states = await self._get_health_states()
        actions_taken = []

        for subsystem in critical:
            status = states.get(subsystem, {}).get("status", "unknown")

            if status == "healthy":
                # Recuperado → notificar si antes estaba mal
                if self._last_status.get(subsystem) == "unhealthy":
                    await self._notify_owner(
                        f"✅ Subsistema `{subsystem}` restaurado automáticamente.",
                        level="info",
                    )
                    logger.info("[AutoRecovery] %s restaurado.", subsystem)
                self._failure_counts[subsystem] = 0
                self._last_status[subsystem] = "healthy"
                continue

            if status in ("unhealthy", "degraded"):
                count = self._failure_counts.get(subsystem, 0) + 1
                self._failure_counts[subsystem] = count
                self._last_status[subsystem] = "unhealthy"

                logger.warning(
                    "[AutoRecovery] %s failed → attempting recovery (%d/%d)",
                    subsystem,
                    count,
                    max_retries,
                )

                if count == 1:
                    await self._notify_owner(
                        f"⚠️ Subsistema `{subsystem}` falló. Intentando recuperación automática...",
                        level="warning",
                    )

                # Intentar recuperación
                recovered = await self._attempt_recovery(subsystem)
                if recovered:
                    actions_taken.append(
                        {"subsystem": subsystem, "action": "recovered"}
                    )
                    self._failure_counts[subsystem] = 0
                    await self._notify_owner(
                        f"✅ Subsistema `{subsystem}` restaurado tras recuperación automática.",
                        level="info",
                    )
                elif count >= max_retries:
                    actions_taken.append(
                        {"subsystem": subsystem, "action": "failed_permanent"}
                    )
                    await self._notify_owner(
                        f"❌ Subsistema `{subsystem}` no se pudo recuperar tras {max_retries} intentos. "
                        f"Requiere intervención manual.",
                        level="error",
                    )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions": actions_taken,
        }

    async def _get_health_states(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene estados de subsistemas via health checks internos."""
        try:
            # Importar checks directamente para evitar HTTP overhead
            from src.api.v1.health import (
                _check_discord_bot,
                _check_episodic_db,
                _check_muninn,
                _check_schedulers,
            )

            results = await asyncio.gather(
                _check_muninn(),
                _check_discord_bot(),
                _check_schedulers(),
                _check_episodic_db(),
                return_exceptions=True,
            )
            names = ["muninn", "discord_bot", "schedulers", "episodic_db"]
            states = {}
            for name, result in zip(names, results):
                if isinstance(result, Exception):
                    states[name] = {"status": "unhealthy", "error": str(result)[:80]}
                else:
                    states[name] = result
            return states
        except Exception as e:
            logger.warning("[AutoRecovery] Error obteniendo health states: %s", e)
            return {}

    async def _attempt_recovery(self, subsystem: str) -> bool:
        """
        Intenta recuperar un subsistema. Devuelve True si tuvo éxito.
        """
        try:
            if subsystem == "muninn":
                return await self._recover_muninn()
            elif subsystem == "discord_bot":
                return await self._recover_discord_bot()
            elif subsystem == "schedulers":
                return await self._recover_schedulers()
            else:
                logger.warning(
                    "[AutoRecovery] Sin estrategia de recuperación para: %s", subsystem
                )
                return False
        except Exception as e:
            logger.error("[AutoRecovery] Error en recuperación de %s: %s", subsystem, e)
            return False

    async def _recover_muninn(self) -> bool:
        """Reintenta conexión a MuninnDB."""
        try:
            from src.core.memory.muninn_memory import MuninnMemory

            muninn = MuninnMemory(self.base_path)
            if not muninn.enabled:
                return True
            # Cerrar clientes cacheados y reconectar
            await muninn.close()
            # Intentar query
            result = await asyncio.wait_for(
                muninn.search("recovery_ping", vault="lilith", limit=1),
                timeout=5.0,
            )
            logger.info("[AutoRecovery] Muninn reconectado exitosamente.")
            return True
        except Exception as e:
            logger.warning("[AutoRecovery] Muninn recovery falló: %s", e)
            return False

    async def _recover_discord_bot(self) -> bool:
        """Verifica si el orchestrator de Discord está disponible."""
        try:
            from src.api.dependencies import get_orchestrator

            orch = get_orchestrator()
            return orch is not None
        except Exception:
            return False

    async def _recover_schedulers(self) -> bool:
        """Intenta reiniciar jobs pausados del scheduler."""
        try:
            from src.api.dependencies import get_orchestrator

            orch = get_orchestrator()
            scheduler = getattr(orch, "task_scheduler", None)
            if scheduler and scheduler._scheduler:
                # Reanudar todos los jobs pausados
                for job in scheduler._scheduler.get_jobs() or []:
                    if job.next_run_time is None:
                        scheduler._scheduler.resume_job(job.id)
                        logger.info("[AutoRecovery] Job %s reanudado.", job.id)
            return True
        except Exception as e:
            logger.warning("[AutoRecovery] Scheduler recovery falló: %s", e)
            return False

    async def _notify_owner(self, message: str, level: str = "info") -> None:
        """Envía notificación al owner vía Discord."""
        try:
            from src.core.transport.discord import notify_owner

            await notify_owner(self.base_path, message)
        except Exception as e:
            logger.debug("[AutoRecovery] No se pudo notificar al owner: %s", e)
