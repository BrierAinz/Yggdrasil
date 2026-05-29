"""
TelegramSessionManager — Gestión de sesiones persistentes por usuario en Telegram.

Features:
- Historial conversacional por usuario
- Estado de confirmaciones pendientes
- Estado de macros en ejecución
- TTL de 24 horas para sesiones inactivas
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.telegram.session")


@dataclass
class SessionContext:
    """Contexto de sesión para un usuario de Telegram."""

    user_id: str
    chat_id: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    active_confirmations: Dict[str, Any] = field(default_factory=dict)
    pc_agent_state: Optional[Dict[str, Any]] = None
    macro_state: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def touch(self):
        """Actualiza timestamp de última actividad."""
        self.last_activity = time.time()

    def add_message(self, role: str, content: str, max_history: int = 10):
        """Añade mensaje al historial."""
        self.conversation_history.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )
        # Mantener solo últimos N mensajes
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        self.touch()

    def is_expired(self, ttl_hours: int = 24) -> bool:
        """Verifica si la sesión expiró por inactividad."""
        expiration = self.last_activity + (ttl_hours * 3600)
        return time.time() > expiration

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "conversation_history": self.conversation_history,
            "active_confirmations": self.active_confirmations,
            "pc_agent_state": self.pc_agent_state,
            "macro_state": self.macro_state,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionContext":
        ctx = cls(
            user_id=data["user_id"],
            chat_id=data["chat_id"],
        )
        ctx.conversation_history = data.get("conversation_history", [])
        ctx.active_confirmations = data.get("active_confirmations", {})
        ctx.pc_agent_state = data.get("pc_agent_state")
        ctx.macro_state = data.get("macro_state")
        ctx.created_at = data.get("created_at", time.time())
        ctx.last_activity = data.get("last_activity", time.time())
        return ctx


class TelegramSessionManager:
    """
    Gestor de sesiones para usuarios de Telegram.
    - Aislamiento de contexto por usuario
    - Persistencia en disco
    - TTL automático
    """

    _instance = None

    def __new__(cls, base_path: Optional[Path] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path)
            if base_path
            else Path(__file__).resolve().parent.parent.parent
        )
        self.sessions: Dict[str, SessionContext] = {}
        self.ttl_hours = 24
        self.max_history = 10
        self._sessions_file = self.base_path / "Data" / "telegram_sessions.json"
        self._sessions_file.parent.mkdir(parents=True, exist_ok=True)

        # Cargar sesiones persistidas
        self._load_sessions()

        self._initialized = True
        logger.info(
            "[TelegramSessionManager] Inicializado. Sessions file: %s",
            self._sessions_file,
        )

    def _load_sessions(self):
        """Carga sesiones desde disco."""
        try:
            if self._sessions_file.exists():
                data = json.loads(self._sessions_file.read_text(encoding="utf-8"))
                for user_id, session_data in data.items():
                    try:
                        session = SessionContext.from_dict(session_data)
                        # Solo cargar si no expiró
                        if not session.is_expired(self.ttl_hours):
                            self.sessions[user_id] = session
                        else:
                            logger.debug(
                                "[TelegramSessionManager] Sesión %s expirada, descartada",
                                user_id,
                            )
                    except Exception as e:
                        logger.warning(
                            "[TelegramSessionManager] Error cargando sesión %s: %s",
                            user_id,
                            e,
                        )
                logger.info(
                    "[TelegramSessionManager] Cargadas %d sesiones activas",
                    len(self.sessions),
                )
        except Exception as e:
            logger.warning("[TelegramSessionManager] Error cargando sesiones: %s", e)

    def _save_sessions(self):
        """Persiste sesiones a disco."""
        try:
            data = {
                user_id: session.to_dict() for user_id, session in self.sessions.items()
            }
            self._sessions_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error("[TelegramSessionManager] Error guardando sesiones: %s", e)

    def get_session(self, user_id: str, chat_id: str = "") -> SessionContext:
        """Obtiene o crea sesión para un usuario."""
        # Limpiar sesiones expiradas periódicamente
        if len(self.sessions) > 100:
            self._cleanup_expired()

        if user_id not in self.sessions:
            logger.info(
                "[TelegramSessionManager] Nueva sesión para usuario %s", user_id
            )
            self.sessions[user_id] = SessionContext(
                user_id=user_id, chat_id=chat_id or user_id
            )
            self._save_sessions()
        else:
            # Actualizar chat_id si cambió
            if chat_id and self.sessions[user_id].chat_id != chat_id:
                self.sessions[user_id].chat_id = chat_id
            self.sessions[user_id].touch()

        return self.sessions[user_id]

    def update_session(self, session: SessionContext):
        """Actualiza una sesión en el manager."""
        session.touch()
        self.sessions[session.user_id] = session
        # Guardar periódicamente (cada 10 cambios podría optimizarse)
        self._save_sessions()

    def add_message(self, user_id: str, chat_id: str, role: str, content: str):
        """Añade mensaje al historial de un usuario."""
        session = self.get_session(user_id, chat_id)
        session.add_message(role, content, max_history=self.max_history)
        self.update_session(session)

    def get_history(
        self, user_id: str, chat_id: str, limit: int = 10
    ) -> List[Dict[str, str]]:
        """Obtiene historial conversacional de un usuario."""
        session = self.get_session(user_id, chat_id)
        return session.conversation_history[-limit:]

    def format_history_for_prompt(
        self, user_id: str, chat_id: str, limit: int = 5
    ) -> str:
        """Formatea historial para inyectar en prompt."""
        history = self.get_history(user_id, chat_id, limit)
        if not history:
            return ""

        lines = ["\n[Historial de conversación reciente]"]
        for msg in history:
            role_label = "Ainz" if msg["role"] == "user" else "Lilith"
            content = msg.get("content", "")[:200]  # Truncar mensajes largos
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)

    def set_pending_confirmation(
        self, user_id: str, chat_id: str, token: str, data: dict
    ):
        """Guarda confirmación pendiente para un usuario."""
        session = self.get_session(user_id, chat_id)
        session.active_confirmations[token] = {**data, "created_at": time.time()}
        self.update_session(session)

    def get_pending_confirmation(self, user_id: str, token: str) -> Optional[dict]:
        """Obtiene confirmación pendiente."""
        session = self.get_session(user_id, "")
        return session.active_confirmations.get(token)

    def remove_pending_confirmation(self, user_id: str, token: str):
        """Elimina confirmación pendiente."""
        session = self.get_session(user_id, "")
        session.active_confirmations.pop(token, None)
        self.update_session(session)

    def set_macro_state(self, user_id: str, chat_id: str, macro_name: str, state: dict):
        """Guarda estado de macro en ejecución."""
        session = self.get_session(user_id, chat_id)
        session.macro_state = {
            "name": macro_name,
            "state": state,
            "started_at": time.time(),
        }
        self.update_session(session)

    def get_macro_state(self, user_id: str) -> Optional[dict]:
        """Obtiene estado de macro en ejecución."""
        session = self.get_session(user_id, "")
        return session.macro_state

    def clear_macro_state(self, user_id: str):
        """Limpia estado de macro."""
        session = self.get_session(user_id, "")
        session.macro_state = None
        self.update_session(session)

    def _cleanup_expired(self):
        """Limpia sesiones expiradas."""
        expired = [
            user_id
            for user_id, session in self.sessions.items()
            if session.is_expired(self.ttl_hours)
        ]
        for user_id in expired:
            logger.info(
                "[TelegramSessionManager] Eliminando sesión expirada: %s", user_id
            )
            del self.sessions[user_id]

        if expired:
            self._save_sessions()
            logger.info(
                "[TelegramSessionManager] Limpiadas %d sesiones expiradas", len(expired)
            )

    def get_stats(self) -> dict:
        """Estadísticas del manager."""
        return {
            "total_sessions": len(self.sessions),
            "active_today": sum(
                1
                for s in self.sessions.values()
                if time.time() - s.last_activity < 86400
            ),
            "with_pending_confirmations": sum(
                1 for s in self.sessions.values() if s.active_confirmations
            ),
            "with_active_macros": sum(
                1 for s in self.sessions.values() if s.macro_state is not None
            ),
        }


# Singleton getter
def get_session_manager(base_path: Optional[Path] = None) -> TelegramSessionManager:
    """Obtiene instancia singleton del SessionManager."""
    return TelegramSessionManager(base_path)
