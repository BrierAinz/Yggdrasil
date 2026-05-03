"""
Lilith Notifications - Sistema de notificaciones Windows
========================================================
Toast notifications y alertas del sistema.
"""
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

# Solo funciona en Windows
try:
    import winrt.windows.data.xml.dom as dom
    import winrt.windows.ui.notifications as notifications

    HAS_WINRT = True
except ImportError:
    HAS_WINRT = False


class NotificationLevel(Enum):
    """Nivel de notificación."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationManager:
    """
    Gestor de notificaciones para Lilith.

    Soporta:
    - Toast notifications de Windows
    - Log de notificaciones
    - Handlers custom
    """

    def __init__(self):
        self.enabled = HAS_WINRT
        self.handlers: List[Callable] = []
        self.notification_log: List[dict] = []

        # Crear directorio de logs
        self.log_dir = Path(__file__).parent / "Data" / "notifications"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "history.json"

        self._load_history()

    def _load_history(self):
        """Carga historial de notificaciones."""
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    self.notification_log = json.load(f)
            except Exception:
                self.notification_log = []

    def _save_history(self):
        """Guarda historial de notificaciones."""
        # Mantener últimos 100
        if len(self.notification_log) > 100:
            self.notification_log = self.notification_log[-100:]

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self.notification_log, f, indent=2)

    def _create_toast_xml(
        self, title: str, message: str, level: NotificationLevel
    ) -> str:
        """Crea XML para toast notification."""
        icon_map = {
            NotificationLevel.INFO: "info",
            NotificationLevel.SUCCESS: "success",
            NotificationLevel.WARNING: "warning",
            NotificationLevel.ERROR: "error",
        }

        return f"""
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"""

    def send(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
    ):
        """
        Envía una notificación.

        Args:
            title: Título de la notificación
            message: Mensaje
            level: Nivel (info, success, warning, error)
        """
        timestamp = datetime.now().isoformat()

        # Registrar
        entry = {
            "timestamp": timestamp,
            "title": title,
            "message": message,
            "level": level.value,
        }
        self.notification_log.append(entry)
        self._save_history()

        # Enviar toast en Windows
        if self.enabled and HAS_WINRT:
            try:
                app_id = "Lilith.Assistant"
                toast_xml = self._create_toast_xml(title, message, level)
                xml = dom.XmlDocument()
                xml.LoadXml(toast_xml)

                notifier = notifications.ToastNotificationManager.CreateToastNotifier(
                    app_id
                )
                toast = notifications.ToastNotification(xml)
                notifier.Show(toast)
            except Exception as e:
                print(f"Toast notification error: {e}")

        # Notificar handlers custom
        for handler in self.handlers:
            try:
                handler(title, message, level)
            except Exception:
                pass

        # Print a consola si no hay winrt
        if not HAS_WINRT:
            print(f"[{level.value.upper()}] {title}: {message}")

    def info(self, title: str, message: str):
        """Envía notificación informativa."""
        self.send(title, message, NotificationLevel.INFO)

    def success(self, title: str, message: str):
        """Envía notificación de éxito."""
        self.send(title, message, NotificationLevel.SUCCESS)

    def warning(self, title: str, message: str):
        """Envía notificación de advertencia."""
        self.send(title, message, NotificationLevel.WARNING)

    def error(self, title: str, message: str):
        """Envía notificación de error."""
        self.send(title, message, NotificationLevel.ERROR)

    def register_handler(self, handler: Callable):
        """Registra un handler custom para notificaciones."""
        self.handlers.append(handler)

    def get_history(self, limit: int = 20) -> List[dict]:
        """Obtiene historial de notificaciones."""
        return self.notification_log[-limit:]

    def clear_history(self):
        """Limpia el historial de notificaciones."""
        self.notification_log = []
        self._save_history()


# Instancia global
_notification_manager: Optional[NotificationManager] = None


def get_notifications() -> NotificationManager:
    """Obtiene la instancia global del gestor de notificaciones."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
