"""
Telegram Bot Heartbeat & Health Monitoring

Sistema de heartbeat para verificar que el bot está vivo y saludable.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """
    Monitor de heartbeat para el bot

    Escribe timestamp cada 60s a un archivo.
    Un proceso externo puede leer el archivo para verificar que está vivo.
    """

    def __init__(self, heartbeat_file: Path, interval_seconds: int = 60):
        """
        Args:
            heartbeat_file: Archivo para escribir timestamp
            interval_seconds: Intervalo entre beats (default: 60s)
        """
        self.heartbeat_file = heartbeat_file
        self.interval_seconds = interval_seconds
        self.should_stop = False
        self.thread: Optional[threading.Thread] = None
        self.last_beat: Optional[float] = None

    def start(self):
        """Iniciar heartbeat en thread daemon"""
        if self.thread and self.thread.is_alive():
            logger.warning("Heartbeat already running")
            return

        self.should_stop = False
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info(f"Heartbeat started (interval={self.interval_seconds}s)")

    def stop(self):
        """Detener heartbeat"""
        self.should_stop = True
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("Heartbeat stopped")

    def _heartbeat_loop(self):
        """Loop de heartbeat"""
        while not self.should_stop:
            try:
                self._beat()
                time.sleep(self.interval_seconds)

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(self.interval_seconds)

    def _beat(self):
        """Escribir un beat"""
        now = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            with open(self.heartbeat_file, "w", encoding="utf-8") as f:
                f.write(f"{timestamp}\n{now}\n")

            self.last_beat = now
            logger.debug(f"Heartbeat: {timestamp}")

        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    def is_healthy(self, max_age_seconds: int = 120) -> bool:
        """
        Verificar si el bot está saludable

        Args:
            max_age_seconds: Edad máxima del último beat (default: 120s)

        Returns:
            True si está saludable
        """
        if not self.last_beat:
            return False

        age = time.time() - self.last_beat
        return age < max_age_seconds


class HealthChecker:
    """
    Verificador de salud externo

    Lee el archivo de heartbeat para verificar si el bot está vivo.
    """

    def __init__(self, heartbeat_file: Path):
        """
        Args:
            heartbeat_file: Archivo de heartbeat a leer
        """
        self.heartbeat_file = heartbeat_file

    def check(self, max_age_seconds: int = 120) -> dict:
        """
        Verificar salud del bot

        Args:
            max_age_seconds: Edad máxima del último beat

        Returns:
            Dict con status, last_beat, age_seconds
        """
        if not self.heartbeat_file.exists():
            return {
                "status": "unhealthy",
                "reason": "heartbeat file not found",
                "last_beat": None,
                "age_seconds": None,
            }

        try:
            with open(self.heartbeat_file, "r", encoding="utf-8") as f:
                lines = f.read().strip().split("\n")

            if len(lines) < 2:
                return {
                    "status": "unhealthy",
                    "reason": "invalid heartbeat format",
                    "last_beat": None,
                    "age_seconds": None,
                }

            timestamp_iso = lines[0]
            timestamp_unix = float(lines[1])

            age = time.time() - timestamp_unix

            if age < max_age_seconds:
                status = "healthy"
            else:
                status = "unhealthy"

            return {
                "status": status,
                "last_beat": timestamp_iso,
                "age_seconds": round(age, 1),
                "max_age_seconds": max_age_seconds,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": f"error reading heartbeat: {e}",
                "last_beat": None,
                "age_seconds": None,
            }


# Singleton global
_heartbeat_monitor: Optional[HeartbeatMonitor] = None


def initialize_heartbeat(heartbeat_file: Path, interval_seconds: int = 60):
    """Inicializar el heartbeat monitor global"""
    global _heartbeat_monitor
    _heartbeat_monitor = HeartbeatMonitor(
        heartbeat_file=heartbeat_file, interval_seconds=interval_seconds
    )
    _heartbeat_monitor.start()


def get_heartbeat_monitor() -> HeartbeatMonitor:
    """Obtener instancia singleton del heartbeat monitor"""
    if _heartbeat_monitor is None:
        raise ValueError("Heartbeat monitor not initialized")
    return _heartbeat_monitor
