"""
Lilith — Sistema de prioridad de canales.
Telegram > Discord DM > Discord público (Crystal independiente).
"""
import time
from typing import Optional


class ChannelPriority:
    """Gestiona prioridad entre canales de comunicación."""

    PRIORITY = {
        "telegram": 3,
        "discord_dm": 2,
        "discord_public": 1,
    }
    TTL = 300  # 5 minutos sin actividad → se libera

    def __init__(self):
        self._active: Optional[str] = None
        self._last_activity: float = 0.0

    def touch(self, channel: str) -> None:
        """Registra actividad en un canal. Telegram siempre toma prioridad."""
        # Solo actualiza si el canal tiene prioridad >= al actual
        current = self.get_active()
        if current is None or self.PRIORITY.get(channel, 0) >= self.PRIORITY.get(
            current, 0
        ):
            self._active = channel
            self._last_activity = time.monotonic()

    def get_active(self) -> Optional[str]:
        """Retorna el canal activo, o None si expiró."""
        if self._active and (time.monotonic() - self._last_activity) < self.TTL:
            return self._active
        self._active = None
        return None

    def should_defer(self, channel: str) -> bool:
        """True si este canal debería esperar (hay uno de mayor prioridad activo)."""
        active = self.get_active()
        if active is None:
            return False
        if channel == active:
            return False
        if channel == "discord_public":
            return False  # Crystal siempre procesa — es independiente
        return self.PRIORITY.get(channel, 0) < self.PRIORITY.get(active, 0)


# Singleton global (compartido por todos los endpoints del servidor)
channel_priority = ChannelPriority()
