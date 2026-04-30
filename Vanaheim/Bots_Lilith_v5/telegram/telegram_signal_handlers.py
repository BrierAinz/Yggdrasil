"""
Signal Handlers para Telegram Bot

Manejo de señales SIGTERM, SIGINT, SIGHUP para cierre limpio del bot.
"""

import json
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BotShutdownManager:
    """
    Gestor de cierre limpio del bot

    Funciones:
    - Registrar handlers de señales
    - Guardar estado antes de apagar
    - Cerrar conexiones limpiamente
    """

    def __init__(self, state_file: Path):
        """
        Args:
            state_file: Archivo para guardar último estado (update_id, etc.)
        """
        self.state_file = state_file
        self.should_stop = False
        self.cleanup_callbacks: list[Callable] = []

    def register_cleanup(self, callback: Callable):
        """
        Registrar callback para ejecutar en cleanup

        Args:
            callback: Función sin args a ejecutar en shutdown
        """
        self.cleanup_callbacks.append(callback)

    def setup_signal_handlers(self):
        """Configurar handlers para SIGTERM, SIGINT, SIGHUP"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # SIGHUP solo en Unix
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._signal_handler)

        logger.info("Signal handlers configured")

    def _signal_handler(self, signum, frame):
        """Handler de señales"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}, initiating graceful shutdown")

        self.should_stop = True
        self.shutdown()

    def shutdown(self):
        """Ejecutar cierre limpio"""
        logger.info("Starting graceful shutdown")

        # Ejecutar callbacks de cleanup
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")

        # Guardar estado
        self.save_state()

        logger.info("Graceful shutdown complete")
        sys.exit(0)

    def save_state(self, update_id: Optional[int] = None):
        """
        Guardar estado del bot

        Args:
            update_id: Último update_id procesado
        """
        state = {
            "last_shutdown": datetime.now(timezone.utc).isoformat(),
            "last_update_id": update_id,
        }

        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            logger.info(f"State saved to {self.state_file}")

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_state(self) -> Optional[dict]:
        """
        Cargar estado previo

        Returns:
            Dict con estado, o None
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            logger.info(f"State loaded from {self.state_file}")
            return state

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None


# Singleton global
_shutdown_manager: Optional[BotShutdownManager] = None


def initialize_shutdown_manager(state_file: Path):
    """Inicializar el shutdown manager global"""
    global _shutdown_manager
    _shutdown_manager = BotShutdownManager(state_file=state_file)
    _shutdown_manager.setup_signal_handlers()


def get_shutdown_manager() -> BotShutdownManager:
    """Obtener instancia singleton del shutdown manager"""
    if _shutdown_manager is None:
        raise ValueError("Shutdown manager not initialized")
    return _shutdown_manager
