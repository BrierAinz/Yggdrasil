"""
Attention Stack - Sistema de prioridades persistentes por sesión

Mantiene lista de tareas/pendientes que no se pierden entre mensajes.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Estados de una tarea en el stack"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


# Alias para compatibilidad con imports existentes
ItemStatus = TaskStatus


class TaskPriority(int, Enum):
    """Niveles de prioridad (1-5)"""

    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5


@dataclass
class AttentionItem:
    """Item individual en el attention stack"""

    id: str
    session_id: str
    description: str
    priority: int
    status: str
    created_at: str
    updated_at: str
    dependencies: List[str]
    metadata: Dict[str, Any]


class AttentionStack:
    """
    Stack de atención por sesión

    Permite:
    - push: Añadir tarea
    - pop: Marcar como done
    - get_active: Obtener pendientes + in_progress
    - to_context_block: Bloque para LLM
    """

    def __init__(self, session_id: str, db_path: Path):
        """
        Args:
            session_id: ID de sesión (channel_id, chat_id, etc.)
            db_path: Ruta a attention_stack.db
        """
        self.session_id = session_id
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Crear tabla si no existe"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attention_stack (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    dependencies TEXT,
                    metadata TEXT
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_status
                ON attention_stack(session_id, status)
            """
            )
            conn.commit()

    def push(
        self,
        description: str,
        priority: int = 3,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttentionItem:
        """
        Añadir tarea al stack

        Args:
            description: Descripción de la tarea
            priority: 1-5, donde 5 es máxima
            dependencies: IDs de tareas de las que depende
            metadata: Metadata adicional

        Returns:
            AttentionItem creado
        """
        item_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        if dependencies is None:
            dependencies = []

        if metadata is None:
            metadata = {}

        # Clamp priority to valid range 1-5
        priority = max(1, min(5, priority))

        # Determinar status inicial
        status = TaskStatus.PENDING
        if dependencies:
            # Verificar si alguna dependencia no está done
            blocked = any(not self._is_done(dep_id) for dep_id in dependencies)
            if blocked:
                status = TaskStatus.BLOCKED

        item = AttentionItem(
            id=item_id,
            session_id=self.session_id,
            description=description,
            priority=priority,
            status=status.value,
            created_at=now,
            updated_at=now,
            dependencies=dependencies,
            metadata=metadata,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO attention_stack
                (id, session_id, description, priority, status, created_at, updated_at, dependencies, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    item.id,
                    item.session_id,
                    item.description,
                    item.priority,
                    item.status,
                    item.created_at,
                    item.updated_at,
                    json.dumps(item.dependencies),
                    json.dumps(item.metadata),
                ),
            )
            conn.commit()

        logger.info(f"Pushed task {item_id} to stack: {description[:50]}")
        return item

    def pop(self, item_id: str) -> bool:
        """
        Marcar tarea como done

        Args:
            item_id: ID del item

        Returns:
            True si exitoso
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE attention_stack
                SET status = ?, updated_at = ?
                WHERE id = ? AND session_id = ?
            """,
                (TaskStatus.DONE.value, now, item_id, self.session_id),
            )

            conn.commit()
            success = cursor.rowcount > 0

        if success:
            logger.info(f"Marked task {item_id} as done")
            # Desbloquear tareas que dependían de esta
            self._unblock_dependents(item_id)

        return success

    def _is_done(self, item_id: str) -> bool:
        """Verificar si un item está done"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT status FROM attention_stack
                WHERE id = ? AND session_id = ?
            """,
                (item_id, self.session_id),
            )

            row = cursor.fetchone()
            return row and row[0] == TaskStatus.DONE.value

    def _unblock_dependents(self, completed_id: str):
        """Desbloquear tareas que dependían del ID completado"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, dependencies FROM attention_stack
                WHERE session_id = ? AND status = ?
            """,
                (self.session_id, TaskStatus.BLOCKED.value),
            )

            blocked_items = cursor.fetchall()

            for item_id, deps_json in blocked_items:
                deps = json.loads(deps_json)

                if completed_id not in deps:
                    continue

                # Verificar si todas las dependencias están done
                all_done = all(self._is_done(dep) for dep in deps)

                if all_done:
                    now = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        """
                        UPDATE attention_stack
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    """,
                        (TaskStatus.PENDING.value, now, item_id),
                    )
                    logger.info(f"Unblocked task {item_id}")

            conn.commit()

    def get_active(self) -> List[AttentionItem]:
        """
        Obtener tareas activas (pending + in_progress)

        Returns:
            Lista de AttentionItem ordenadas por prioridad
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id, session_id, description, priority, status,
                       created_at, updated_at, dependencies, metadata
                FROM attention_stack
                WHERE session_id = ? AND status IN (?, ?)
                ORDER BY priority DESC, created_at ASC
            """,
                (
                    self.session_id,
                    TaskStatus.PENDING.value,
                    TaskStatus.IN_PROGRESS.value,
                ),
            )

            rows = cursor.fetchall()

        items = []
        for row in rows:
            items.append(
                AttentionItem(
                    id=row[0],
                    session_id=row[1],
                    description=row[2],
                    priority=row[3],
                    status=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    dependencies=json.loads(row[7]),
                    metadata=json.loads(row[8]),
                )
            )

        return items

    def get_all(self, include_done: bool = False) -> List[AttentionItem]:
        """Obtener todas las tareas de la sesión"""
        statuses = [
            TaskStatus.PENDING.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.BLOCKED.value,
        ]

        if include_done:
            statuses.extend([TaskStatus.DONE.value, TaskStatus.CANCELLED.value])

        with sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join("?" * len(statuses))
            cursor = conn.execute(
                f"""
                SELECT id, session_id, description, priority, status,
                       created_at, updated_at, dependencies, metadata
                FROM attention_stack
                WHERE session_id = ? AND status IN ({placeholders})
                ORDER BY priority DESC, created_at ASC
            """,
                [self.session_id] + statuses,
            )

            rows = cursor.fetchall()

        items = []
        for row in rows:
            items.append(
                AttentionItem(
                    id=row[0],
                    session_id=row[1],
                    description=row[2],
                    priority=row[3],
                    status=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    dependencies=json.loads(row[7]),
                    metadata=json.loads(row[8]),
                )
            )

        return items

    def clear(self, status_filter: Optional[str] = None):
        """
        Limpiar stack

        Args:
            status_filter: Si se especifica, solo borrar items con ese status (ej: 'done')
        """
        with sqlite3.connect(self.db_path) as conn:
            if status_filter:
                conn.execute(
                    """
                    DELETE FROM attention_stack
                    WHERE session_id = ? AND status = ?
                """,
                    (self.session_id, status_filter),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM attention_stack
                    WHERE session_id = ?
                """,
                    (self.session_id,),
                )

            conn.commit()

        logger.info(
            f"Cleared stack for session {self.session_id}, filter={status_filter}"
        )

    def to_context_block(self) -> str:
        """
        Generar bloque de contexto para el LLM

        Returns:
            String formateado con emojis y prioridades
        """
        items = self.get_active()

        if not items:
            return ""

        lines = ["📋 TAREAS PENDIENTES DE ESTA SESIÓN:", ""]

        emoji_map = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔨",
            TaskStatus.DONE: "✅",
            TaskStatus.BLOCKED: "🚫",
            TaskStatus.CANCELLED: "🗑️",
        }

        priority_emoji = {
            5: "🔴",  # HIGHEST
            4: "🟠",  # HIGH
            3: "🟡",  # MEDIUM
            2: "🔵",  # LOW
            1: "⚪",  # LOWEST
        }

        for idx, item in enumerate(items, 1):
            status_emoji = emoji_map.get(TaskStatus(item.status), "❓")
            prio_emoji = priority_emoji.get(item.priority, "🟡")

            lines.append(f"{idx}. {status_emoji} {prio_emoji} {item.description}")

        lines.append("")
        lines.append("Recuerda completar estas tareas antes de finalizar la sesión.")

        return "\n".join(lines)


# Cache de stacks por sesión
_stack_cache: Dict[str, AttentionStack] = {}
_db_path: Optional[Path] = None


def set_db_path(path: Path):
    """Configurar ruta global de la DB"""
    global _db_path
    _db_path = path


def get_attention_stack(session_id: str) -> AttentionStack:
    """
    Obtener stack para una sesión (con cache)

    Args:
        session_id: ID de sesión

    Returns:
        AttentionStack para esa sesión
    """
    if session_id not in _stack_cache:
        if _db_path is None:
            raise ValueError("DB path not set, call set_db_path() first")

        _stack_cache[session_id] = AttentionStack(
            session_id=session_id, db_path=_db_path
        )

    return _stack_cache[session_id]


def format_stack_for_prompt(session_id: str) -> str:
    """
    Formatear el stack de una sesión para incluir en prompts.

    Args:
        session_id: ID de la sesión

    Returns:
        String formateado con las tareas pendientes
    """
    if _db_path is None:
        return ""

    stack = get_attention_stack(session_id)
    return stack.to_context_block()
