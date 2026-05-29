"""
Session Manager - Gestión de sesiones compartidas y colaborativas

v5.0-Fase4A: Multi-user sessions, presence tracking, real-time collaboration.
"""
import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import aiohttp
from fastapi import WebSocket

logger = logging.getLogger("lilith.collaboration.session")


class UserRole(Enum):
    """Roles en una sesión colaborativa."""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class SessionStatus(Enum):
    """Estado de una sesión."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    LOCKED = "locked"


@dataclass
class UserPresence:
    """Estado de presencia de un usuario."""

    user_id: str
    username: str
    avatar: Optional[str] = None
    status: str = "online"  # online, away, busy, offline
    current_view: Optional[str] = None  # workflow_id, page, etc.
    cursor_position: Optional[Dict[str, Any]] = None
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    joined_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SessionParticipant:
    """Participante de una sesión."""

    user_id: str
    role: UserRole
    permissions: List[str] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    added_by: Optional[str] = None


@dataclass
class SharedSession:
    """Sesión colaborativa compartida."""

    id: str
    name: str
    description: Optional[str] = None
    owner_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    participants: Dict[str, SessionParticipant] = field(default_factory=dict)
    presence: Dict[str, UserPresence] = field(default_factory=dict)
    shared_resources: List[str] = field(default_factory=list)  # workflow_ids
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Gestor de sesiones colaborativas multi-usuario.

    Features:
    - Crear y gestionar sesiones compartidas
    - Control de presencia en tiempo real
    - Permisos granulares por sesión
    - WebSockets para actualizaciones en vivo
    """

    def __init__(self):
        self.sessions: Dict[str, SharedSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set(session_ids)
        self.websockets: Dict[
            str, Dict[str, WebSocket]
        ] = {}  # session_id -> {user_id: ws}
        self.presence_callbacks: List[Callable] = []
        self.lock = asyncio.Lock()

    async def create_session(
        self,
        name: str,
        owner_id: str,
        description: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> SharedSession:
        """Crea una nueva sesión colaborativa."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        expires_at = None
        if expires_in_hours:
            expires_at = (
                datetime.utcnow() + timedelta(hours=expires_in_hours)
            ).isoformat()

        session = SharedSession(
            id=session_id,
            name=name,
            description=description,
            owner_id=owner_id,
            expires_at=expires_at,
            participants={
                owner_id: SessionParticipant(
                    user_id=owner_id,
                    role=UserRole.OWNER,
                    permissions=["*"],
                    added_by=owner_id,
                )
            },
        )

        async with self.lock:
            self.sessions[session_id] = session
            if owner_id not in self.user_sessions:
                self.user_sessions[owner_id] = set()
            self.user_sessions[owner_id].add(session_id)
            self.websockets[session_id] = {}

        logger.info(f"Session {session_id} created by {owner_id}")
        return session

    async def add_participant(
        self,
        session_id: str,
        user_id: str,
        role: UserRole = UserRole.VIEWER,
        added_by: str = "",
        permissions: Optional[List[str]] = None,
    ) -> bool:
        """Añade un participante a una sesión."""
        async with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            # Solo owner/admin pueden añadir participantes
            if added_by != session.owner_id:
                if added_by not in session.participants:
                    return False
                if session.participants[added_by].role not in [
                    UserRole.OWNER,
                    UserRole.ADMIN,
                ]:
                    return False

            session.participants[user_id] = SessionParticipant(
                user_id=user_id,
                role=role,
                permissions=permissions or self._default_permissions(role),
                added_by=added_by,
            )

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

            session.updated_at = datetime.utcnow().isoformat()

        await self._notify_session_update(
            session_id,
            "participant_added",
            {"user_id": user_id, "role": role.value, "added_by": added_by},
        )

        return True

    async def remove_participant(
        self, session_id: str, user_id: str, removed_by: str
    ) -> bool:
        """Elimina un participante de una sesión."""
        async with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            # No se puede eliminar al owner
            if user_id == session.owner_id:
                return False

            # Verificar permisos
            if removed_by != session.owner_id:
                remover = session.participants.get(removed_by)
                if not remover or remover.role not in [UserRole.OWNER, UserRole.ADMIN]:
                    return False

            if user_id in session.participants:
                del session.participants[user_id]

            if user_id in session.presence:
                del session.presence[user_id]

            if user_id in self.websockets.get(session_id, {}):
                del self.websockets[session_id][user_id]

            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)

            session.updated_at = datetime.utcnow().isoformat()

        await self._notify_session_update(
            session_id,
            "participant_removed",
            {"user_id": user_id, "removed_by": removed_by},
        )

        return True

    async def update_presence(
        self,
        session_id: str,
        user_id: str,
        status: Optional[str] = None,
        current_view: Optional[str] = None,
        cursor_position: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Actualiza el estado de presencia de un usuario."""
        async with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]

            if user_id not in session.participants:
                return False

            if user_id not in session.presence:
                session.presence[user_id] = UserPresence(
                    user_id=user_id,
                    username=user_id,  # Se puede mejorar con lookup de perfil
                )

            presence = session.presence[user_id]

            if status:
                presence.status = status
            if current_view:
                presence.current_view = current_view
            if cursor_position:
                presence.cursor_position = cursor_position

            presence.last_activity = datetime.utcnow().isoformat()

        await self._broadcast_presence(session_id, user_id)
        return True

    async def join_session_websocket(
        self, session_id: str, user_id: str, websocket: WebSocket
    ) -> bool:
        """Conecta un WebSocket para una sesión."""
        async with self.lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]
            if user_id not in session.participants:
                return False

            self.websockets[session_id][user_id] = websocket

        # Notificar a otros que el usuario se conectó
        await self._notify_session_update(
            session_id,
            "user_joined",
            {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
        )

        return True

    async def leave_session_websocket(self, session_id: str, user_id: str):
        """Desconecta el WebSocket de un usuario."""
        async with self.lock:
            if session_id in self.websockets:
                if user_id in self.websockets[session_id]:
                    del self.websockets[session_id][user_id]

            if session_id in self.sessions:
                if user_id in self.sessions[session_id].presence:
                    self.sessions[session_id].presence[user_id].status = "offline"

        await self._notify_session_update(
            session_id,
            "user_left",
            {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
        )

    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[str] = None,
    ):
        """Envía un mensaje a todos los usuarios de una sesión."""
        if session_id not in self.websockets:
            return

        tasks = []
        for user_id, ws in self.websockets[session_id].items():
            if user_id != exclude_user:
                try:
                    tasks.append(ws.send_json(message))
                except Exception:
                    pass

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_user_sessions(self, user_id: str) -> List[SharedSession]:
        """Obtiene todas las sesiones de un usuario."""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]

    def get_session_participants(self, session_id: str) -> List[SessionParticipant]:
        """Obtiene los participantes de una sesión."""
        if session_id not in self.sessions:
            return []
        return list(self.sessions[session_id].participants.values())

    def get_session_presence(self, session_id: str) -> List[UserPresence]:
        """Obtiene la presencia de usuarios en una sesión."""
        if session_id not in self.sessions:
            return []
        return list(self.sessions[session_id].presence.values())

    def check_permission(self, session_id: str, user_id: str, permission: str) -> bool:
        """Verifica si un usuario tiene un permiso específico."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        participant = session.participants.get(user_id)

        if not participant:
            return False

        if "*" in participant.permissions:
            return True

        return permission in participant.permissions

    def _default_permissions(self, role: UserRole) -> List[str]:
        """Permisos por defecto según el rol."""
        permissions = {
            UserRole.OWNER: ["*"],
            UserRole.ADMIN: [
                "session:read",
                "session:update",
                "session:delete",
                "participant:add",
                "participant:remove",
                "participant:update",
                "resource:read",
                "resource:write",
                "resource:delete",
                "comment:read",
                "comment:write",
                "comment:delete",
            ],
            UserRole.EDITOR: [
                "session:read",
                "resource:read",
                "resource:write",
                "comment:read",
                "comment:write",
            ],
            UserRole.VIEWER: ["session:read", "resource:read", "comment:read"],
        }
        return permissions.get(role, ["session:read"])

    async def _notify_session_update(
        self, session_id: str, event_type: str, data: Dict[str, Any]
    ):
        """Notifica una actualización de sesión a todos los participantes."""
        message = {
            "type": "session_update",
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_session(session_id, message)

    async def _broadcast_presence(self, session_id: str, user_id: str):
        """Transmite actualización de presencia."""
        if session_id not in self.sessions:
            return

        presence = self.sessions[session_id].presence.get(user_id)
        if not presence:
            return

        message = {
            "type": "presence_update",
            "user_id": user_id,
            "presence": {
                "status": presence.status,
                "current_view": presence.current_view,
                "cursor_position": presence.cursor_position,
                "last_activity": presence.last_activity,
            },
        }

        await self.broadcast_to_session(session_id, message, exclude_user=user_id)

    async def cleanup_expired_sessions(self) -> int:
        """Limpia sesiones expiradas. Retorna cantidad eliminada."""
        now = datetime.utcnow()
        expired = []

        async with self.lock:
            for session_id, session in self.sessions.items():
                if session.expires_at:
                    expires = datetime.fromisoformat(session.expires_at)
                    if now > expires:
                        expired.append(session_id)

            for session_id in expired:
                await self._delete_session_internal(session_id)

        return len(expired)

    async def _delete_session_internal(self, session_id: str):
        """Elimina una sesión internamente (sin lock)."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # Desconectar todos los WebSockets
        if session_id in self.websockets:
            for ws in self.websockets[session_id].values():
                try:
                    await ws.close()
                except Exception:
                    pass
            del self.websockets[session_id]

        # Remover de user_sessions
        for user_id in session.participants:
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)

        del self.sessions[session_id]
        logger.info(f"Session {session_id} deleted")


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtiene el singleton del SessionManager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
