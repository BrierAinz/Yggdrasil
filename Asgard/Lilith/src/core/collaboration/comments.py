"""
Comments System - Comentarios y anotaciones colaborativas

v5.0-Fase4A: Comentarios en workflows, threads, menciones y resolución.
"""
import asyncio
import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("lilith.collaboration.comments")


class CommentStatus(Enum):
    """Estado de un comentario."""

    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"
    PINNED = "pinned"


class CommentPriority(Enum):
    """Prioridad de un comentario."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CommentReaction:
    """Reacción a un comentario."""

    emoji: str
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Comment:
    """Comentario individual."""

    id: str
    thread_id: str
    author_id: str
    author_name: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_id: Optional[str] = None  # Para replies
    status: CommentStatus = CommentStatus.OPEN
    priority: CommentPriority = CommentPriority.MEDIUM
    reactions: List[CommentReaction] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)  # user_ids mencionados
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    edit_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CommentThread:
    """Hilo de comentarios sobre un recurso."""

    id: str
    resource_type: str  # workflow, agent, tool, etc.
    resource_id: str
    context: Dict[str, Any] = field(
        default_factory=dict
    )  # nodo específico, línea de código, etc.
    comments: List[Comment] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    participants: Set[str] = field(default_factory=set)
    status: CommentStatus = CommentStatus.OPEN
    assigned_to: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


@dataclass
class NotificationRule:
    """Regla de notificación para comentarios."""

    user_id: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    notify_on: List[str] = field(
        default_factory=lambda: ["mention", "reply", "assignment"]
    )
    email: bool = True
    in_app: bool = True
    webhook: Optional[str] = None


class CommentsManager:
    """
    Sistema de comentarios y anotaciones colaborativas.

    Features:
    - Threads anidados por recurso
    - Replies y menciones (@usuario)
    - Estados y resolución
    - Reacciones (emoji)
    - Notificaciones
    - Búsqueda y filtrado
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.threads: Dict[str, CommentThread] = {}
        self.comments: Dict[str, Comment] = {}  # Índice por ID
        self.resource_threads: Dict[str, Set[str]] = {}  # resource_key -> thread_ids
        self.user_notifications: Dict[str, List[Dict[str, Any]]] = {}
        self.notification_rules: Dict[str, NotificationRule] = {}
        self.storage_path = storage_path or Path("Data/comments")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        self._load_data()

    def _resource_key(self, resource_type: str, resource_id: str) -> str:
        """Genera clave de recurso."""
        return f"{resource_type}:{resource_id}"

    async def create_thread(
        self,
        resource_type: str,
        resource_id: str,
        author_id: str,
        author_name: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        priority: CommentPriority = CommentPriority.MEDIUM,
    ) -> CommentThread:
        """Crea un nuevo hilo de comentarios."""
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"

        async with self.lock:
            thread = CommentThread(
                id=thread_id,
                resource_type=resource_type,
                resource_id=resource_id,
                context=context or {},
                status=CommentStatus.OPEN,
                participants={author_id},
            )

            # Crear el primer comentario
            comment = await self._create_comment_internal(
                thread_id=thread_id,
                author_id=author_id,
                author_name=author_name,
                content=content,
                priority=priority,
            )

            thread.comments.append(comment)

            self.threads[thread_id] = thread

            # Indexar por recurso
            key = self._resource_key(resource_type, resource_id)
            if key not in self.resource_threads:
                self.resource_threads[key] = set()
            self.resource_threads[key].add(thread_id)

            self._save_data()

        # Procesar menciones y notificar
        await self._process_mentions(comment, thread)

        logger.info(f"Thread {thread_id} created on {resource_type}:{resource_id}")
        return thread

    async def add_comment(
        self,
        thread_id: str,
        author_id: str,
        author_name: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> Optional[Comment]:
        """Añade un comentario a un hilo."""
        async with self.lock:
            if thread_id not in self.threads:
                return None

            thread = self.threads[thread_id]

            # Verificar que el thread esté abierto
            if thread.status == CommentStatus.CLOSED:
                return None

            comment = await self._create_comment_internal(
                thread_id=thread_id,
                author_id=author_id,
                author_name=author_name,
                content=content,
                parent_id=parent_id,
            )

            thread.comments.append(comment)
            thread.participants.add(author_id)
            thread.updated_at = datetime.utcnow().isoformat()

            self.comments[comment.id] = comment
            self._save_data()

        await self._process_mentions(comment, thread)
        await self._notify_participants(thread, comment)

        return comment

    async def update_comment(
        self, comment_id: str, new_content: str, user_id: str
    ) -> bool:
        """Actualiza el contenido de un comentario."""
        async with self.lock:
            if comment_id not in self.comments:
                return False

            comment = self.comments[comment_id]

            # Solo el autor puede editar
            if comment.author_id != user_id:
                return False

            # Guardar en historial
            comment.edit_history.append(
                {"content": comment.content, "edited_at": datetime.utcnow().isoformat()}
            )

            comment.content = new_content
            comment.updated_at = datetime.utcnow().isoformat()

            # Re-procesar menciones
            comment.mentions = self._extract_mentions(new_content)

            self._save_data()

        return True

    async def delete_comment(
        self, comment_id: str, user_id: str, is_admin: bool = False
    ) -> bool:
        """Elimina (soft-delete) un comentario."""
        async with self.lock:
            if comment_id not in self.comments:
                return False

            comment = self.comments[comment_id]

            if comment.author_id != user_id and not is_admin:
                return False

            comment.content = "[deleted]"
            comment.metadata["deleted"] = True
            comment.metadata["deleted_by"] = user_id
            comment.metadata["deleted_at"] = datetime.utcnow().isoformat()

            self._save_data()

        return True

    async def resolve_thread(
        self, thread_id: str, user_id: str, resolution_note: Optional[str] = None
    ) -> bool:
        """Marca un hilo como resuelto."""
        async with self.lock:
            if thread_id not in self.threads:
                return False

            thread = self.threads[thread_id]
            thread.status = CommentStatus.RESOLVED
            thread.resolved_at = datetime.utcnow().isoformat()
            thread.resolved_by = user_id
            thread.updated_at = datetime.utcnow().isoformat()

            if resolution_note:
                thread.metadata["resolution_note"] = resolution_note

            self._save_data()

        # Notificar
        await self._notify_thread_resolved(thread, user_id)

        return True

    async def reopen_thread(self, thread_id: str, user_id: str) -> bool:
        """Reabre un hilo resuelto."""
        async with self.lock:
            if thread_id not in self.threads:
                return False

            thread = self.threads[thread_id]
            thread.status = CommentStatus.OPEN
            thread.resolved_at = None
            thread.resolved_by = None
            thread.updated_at = datetime.utcnow().isoformat()

            self._save_data()

        return True

    async def add_reaction(self, comment_id: str, emoji: str, user_id: str) -> bool:
        """Añade una reacción a un comentario."""
        async with self.lock:
            if comment_id not in self.comments:
                return False

            comment = self.comments[comment_id]

            # Remover reacción previa del mismo usuario con mismo emoji
            comment.reactions = [
                r
                for r in comment.reactions
                if not (r.user_id == user_id and r.emoji == emoji)
            ]

            # Añadir nueva reacción
            reaction = CommentReaction(emoji=emoji, user_id=user_id)
            comment.reactions.append(reaction)

            self._save_data()

        return True

    async def remove_reaction(self, comment_id: str, emoji: str, user_id: str) -> bool:
        """Remueve una reacción de un comentario."""
        async with self.lock:
            if comment_id not in self.comments:
                return False

            comment = self.comments[comment_id]

            comment.reactions = [
                r
                for r in comment.reactions
                if not (r.user_id == user_id and r.emoji == emoji)
            ]

            self._save_data()

        return True

    async def assign_thread(
        self, thread_id: str, assigned_to: str, assigned_by: str
    ) -> bool:
        """Asigna un hilo a un usuario."""
        async with self.lock:
            if thread_id not in self.threads:
                return False

            thread = self.threads[thread_id]
            thread.assigned_to = assigned_to
            thread.updated_at = datetime.utcnow().isoformat()

            self._save_data()

        # Notificar asignación
        await self._notify_assignment(thread, assigned_to, assigned_by)

        return True

    def get_threads_for_resource(
        self,
        resource_type: str,
        resource_id: str,
        status: Optional[CommentStatus] = None,
    ) -> List[CommentThread]:
        """Obtiene los hilos de un recurso."""
        key = self._resource_key(resource_type, resource_id)
        thread_ids = self.resource_threads.get(key, set())

        threads = [self.threads[tid] for tid in thread_ids if tid in self.threads]

        if status:
            threads = [t for t in threads if t.status == status]

        # Ordenar por fecha de actualización descendente
        threads.sort(key=lambda t: t.updated_at, reverse=True)

        return threads

    def search_comments(
        self,
        query: str,
        resource_type: Optional[str] = None,
        author_id: Optional[str] = None,
        status: Optional[CommentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Busca comentarios."""
        results = []

        for comment in self.comments.values():
            if query.lower() not in comment.content.lower():
                continue

            if author_id and comment.author_id != author_id:
                continue

            # Encontrar el thread
            thread = self.threads.get(comment.thread_id)
            if not thread:
                continue

            if resource_type and thread.resource_type != resource_type:
                continue

            if status and comment.status != status:
                continue

            results.append(
                {
                    "comment": comment,
                    "thread": thread,
                    "resource": {
                        "type": thread.resource_type,
                        "id": thread.resource_id,
                        "context": thread.context,
                    },
                }
            )

        return results

    def get_user_notifications(
        self, user_id: str, unread_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Obtiene notificaciones de un usuario."""
        notifications = self.user_notifications.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n.get("read")]

        return sorted(notifications, key=lambda n: n["created_at"], reverse=True)

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Marca una notificación como leída."""
        if user_id not in self.user_notifications:
            return False

        for n in self.user_notifications[user_id]:
            if n["id"] == notification_id:
                n["read"] = True
                n["read_at"] = datetime.utcnow().isoformat()
                return True

        return False

    async def _create_comment_internal(
        self,
        thread_id: str,
        author_id: str,
        author_name: str,
        content: str,
        parent_id: Optional[str] = None,
        priority: CommentPriority = CommentPriority.MEDIUM,
    ) -> Comment:
        """Crea un comentario internamente."""
        comment_id = f"cmt_{uuid.uuid4().hex[:12]}"

        mentions = self._extract_mentions(content)

        comment = Comment(
            id=comment_id,
            thread_id=thread_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            parent_id=parent_id,
            mentions=mentions,
            priority=priority,
        )

        self.comments[comment_id] = comment
        return comment

    def _extract_mentions(self, content: str) -> List[str]:
        """Extrae menciones @usuario del contenido."""
        pattern = r"@([a-zA-Z0-9_-]+)"
        return re.findall(pattern, content)

    async def _process_mentions(self, comment: Comment, thread: CommentThread):
        """Procesa menciones y crea notificaciones."""
        for mentioned_user in comment.mentions:
            await self._create_notification(
                user_id=mentioned_user,
                type="mention",
                title=f"Mención en {thread.resource_type}",
                message=f"{comment.author_name} te mencionó en un comentario",
                data={
                    "thread_id": thread.id,
                    "comment_id": comment.id,
                    "resource_type": thread.resource_type,
                    "resource_id": thread.resource_id,
                },
            )

    async def _notify_participants(self, thread: CommentThread, new_comment: Comment):
        """Notifica a participantes del thread."""
        for participant_id in thread.participants:
            if participant_id == new_comment.author_id:
                continue  # No notificar al autor

            await self._create_notification(
                user_id=participant_id,
                type="reply",
                title=f"Nuevo comentario en {thread.resource_type}",
                message=f"{new_comment.author_name} comentó en un hilo que sigues",
                data={
                    "thread_id": thread.id,
                    "comment_id": new_comment.id,
                    "resource_type": thread.resource_type,
                    "resource_id": thread.resource_id,
                },
            )

    async def _notify_assignment(
        self, thread: CommentThread, assigned_to: str, assigned_by: str
    ):
        """Notifica asignación."""
        await self._create_notification(
            user_id=assigned_to,
            type="assignment",
            title=f"Asignación en {thread.resource_type}",
            message=f"Un hilo te fue asignado por {assigned_by}",
            data={
                "thread_id": thread.id,
                "resource_type": thread.resource_type,
                "resource_id": thread.resource_id,
            },
        )

    async def _notify_thread_resolved(self, thread: CommentThread, resolved_by: str):
        """Notifica resolución de thread."""
        for participant_id in thread.participants:
            if participant_id == resolved_by:
                continue

            await self._create_notification(
                user_id=participant_id,
                type="resolved",
                title=f"Hilo resuelto en {thread.resource_type}",
                message=f"Un hilo que sigues fue marcado como resuelto",
                data={
                    "thread_id": thread.id,
                    "resource_type": thread.resource_type,
                    "resource_id": thread.resource_id,
                    "resolved_by": resolved_by,
                },
            )

    async def _create_notification(
        self, user_id: str, type: str, title: str, message: str, data: Dict[str, Any]
    ):
        """Crea una notificación para un usuario."""
        if user_id not in self.user_notifications:
            self.user_notifications[user_id] = []

        notification = {
            "id": f"notif_{uuid.uuid4().hex[:12]}",
            "type": type,
            "title": title,
            "message": message,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
            "read": False,
        }

        self.user_notifications[user_id].append(notification)

        # Limitar a 100 notificaciones por usuario
        if len(self.user_notifications[user_id]) > 100:
            self.user_notifications[user_id] = self.user_notifications[user_id][-100:]

    def _save_data(self):
        """Guarda datos en disco."""
        try:
            data = {
                "threads": {
                    k: {
                        "id": v.id,
                        "resource_type": v.resource_type,
                        "resource_id": v.resource_id,
                        "context": v.context,
                        "created_at": v.created_at,
                        "updated_at": v.updated_at,
                        "participants": list(v.participants),
                        "status": v.status.value,
                        "assigned_to": v.assigned_to,
                        "labels": v.labels,
                        "resolved_at": v.resolved_at,
                        "resolved_by": v.resolved_by,
                        "comments": [
                            {
                                "id": c.id,
                                "thread_id": c.thread_id,
                                "author_id": c.author_id,
                                "author_name": c.author_name,
                                "content": c.content,
                                "created_at": c.created_at,
                                "updated_at": c.updated_at,
                                "parent_id": c.parent_id,
                                "status": c.status.value,
                                "priority": c.priority.value,
                                "reactions": [
                                    {"emoji": r.emoji, "user_id": r.user_id}
                                    for r in c.reactions
                                ],
                                "mentions": c.mentions,
                                "attachments": c.attachments,
                                "metadata": c.metadata,
                                "edit_history": c.edit_history,
                            }
                            for c in v.comments
                        ],
                    }
                    for k, v in self.threads.items()
                }
            }

            with open(self.storage_path / "comments.json", "w") as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving comments: {e}")

    def _load_data(self):
        """Carga datos desde disco."""
        try:
            file_path = self.storage_path / "comments.json"
            if not file_path.exists():
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            for thread_id, thread_data in data.get("threads", {}).items():
                thread = CommentThread(
                    id=thread_data["id"],
                    resource_type=thread_data["resource_type"],
                    resource_id=thread_data["resource_id"],
                    context=thread_data.get("context", {}),
                    comments=[],
                    created_at=thread_data["created_at"],
                    updated_at=thread_data["updated_at"],
                    participants=set(thread_data.get("participants", [])),
                    status=CommentStatus(thread_data["status"]),
                    assigned_to=thread_data.get("assigned_to"),
                    labels=thread_data.get("labels", []),
                    resolved_at=thread_data.get("resolved_at"),
                    resolved_by=thread_data.get("resolved_by"),
                )

                for comment_data in thread_data.get("comments", []):
                    comment = Comment(
                        id=comment_data["id"],
                        thread_id=comment_data["thread_id"],
                        author_id=comment_data["author_id"],
                        author_name=comment_data["author_name"],
                        content=comment_data["content"],
                        created_at=comment_data["created_at"],
                        updated_at=comment_data["updated_at"],
                        parent_id=comment_data.get("parent_id"),
                        status=CommentStatus(comment_data.get("status", "open")),
                        priority=CommentPriority(
                            comment_data.get("priority", "medium")
                        ),
                        reactions=[
                            CommentReaction(emoji=r["emoji"], user_id=r["user_id"])
                            for r in comment_data.get("reactions", [])
                        ],
                        mentions=comment_data.get("mentions", []),
                        attachments=comment_data.get("attachments", []),
                        metadata=comment_data.get("metadata", {}),
                        edit_history=comment_data.get("edit_history", []),
                    )

                    thread.comments.append(comment)
                    self.comments[comment.id] = comment

                self.threads[thread_id] = thread

                key = self._resource_key(thread.resource_type, thread.resource_id)
                if key not in self.resource_threads:
                    self.resource_threads[key] = set()
                self.resource_threads[key].add(thread_id)

        except Exception as e:
            logger.error(f"Error loading comments: {e}")


# Singleton
_comments_manager: Optional[CommentsManager] = None


def get_comments_manager() -> CommentsManager:
    """Obtiene el singleton del CommentsManager."""
    global _comments_manager
    if _comments_manager is None:
        _comments_manager = CommentsManager()
    return _comments_manager
