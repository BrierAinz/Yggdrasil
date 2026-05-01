"""
MessageBus - Sistema de mensajeria para Swarm
=============================================
Cola thread-safe para comunicacion entre agentes.
"""
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class MessageType(Enum):
    """Tipos de mensajes en el bus."""

    TASK_COMPLETE = "task_complete"
    CODE_SHIFT = "code_shift"
    CODE_SHIFT_NOTICE = "code_shift_notice"
    LOCK_REQUEST = "lock_request"
    LOCK_RELEASE = "lock_release"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    BROADCAST = "broadcast"


@dataclass
class Message:
    """Mensaje en el bus."""

    msg_type: MessageType
    from_id: str
    to_id: Optional[str] = None  # None = broadcast
    data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "type": self.msg_type.value,
            "from": self.from_id,
            "to": self.to_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class MessageBus:
    """Bus de mensajes thread-safe para comunicacion entre agentes."""

    def __init__(self, max_size: int = 1000):
        self._queue: queue.Queue[Message] = queue.Queue(maxsize=max_size)
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Set[str]] = {}  # agent_id -> {msg_types}
        self._history: List[Message] = []
        self._max_history = 100

    def subscribe(self, agent_id: str, msg_types: Optional[List[str]] = None):
        """Suscribe un agente a tipos de mensajes."""
        with self._lock:
            if agent_id not in self._subscribers:
                self._subscribers[agent_id] = set()
            if msg_types:
                for mt in msg_types:
                    self._subscribers[agent_id].add(mt)
            else:
                # Suscribirse a todos
                for mt in MessageType:
                    self._subscribers[agent_id].add(mt.value)

    def unsubscribe(self, agent_id: str):
        """Desuscribe un agente."""
        with self._lock:
            self._subscribers.pop(agent_id, None)

    def send(self, msg: Message) -> bool:
        """Envia un mensaje al bus. Retorna True si se encolo."""
        try:
            self._queue.put_nowait(msg)
            with self._lock:
                self._history.append(msg)
                if len(self._history) > self._max_history:
                    self._history.pop(0)
            return True
        except queue.Full:
            return False

    def broadcast(self, from_id: str, msg_type: MessageType, data: Dict) -> bool:
        """Broadcast a todos los agentes."""
        msg = Message(
            msg_type=msg_type,
            from_id=from_id,
            to_id=None,
            data=data,
        )
        return self.send(msg)

    def get_messages(
        self,
        agent_id: str,
        msg_types: Optional[List[str]] = None,
        block: bool = False,
        timeout: float = 0.5,
    ) -> List[Message]:
        """Obtiene mensajes para un agente."""
        messages = []
        skipped = []  # Mensajes que no son para este agente

        # Primero: drenar la cola
        while True:
            try:
                if block and not messages and not skipped:
                    msg = self._queue.get(timeout=timeout)
                else:
                    msg = self._queue.get_nowait()

                # Filtrar por destinatario y tipo
                if msg.to_id is not None and msg.to_id != agent_id:
                    # Privado para otro agente, guardar para re-encolar
                    skipped.append(msg)
                    continue

                # Filtrar por tipo si se especifico
                if msg_types and msg.msg_type.value not in msg_types:
                    skipped.append(msg)
                    continue

                messages.append(msg)
            except queue.Empty:
                break

        # Re-encolar mensajes que no correspondian a este agente
        for msg in skipped:
            try:
                self._queue.put_nowait(msg)
            except queue.Full:
                break

        return messages

    def get_all_messages(self, clear: bool = False) -> List[Message]:
        """Obtiene todos los mensajes (para debugging)."""
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if not clear:
            # Re-encolar
            for msg in messages:
                self._queue.put_nowait(msg)
        return messages

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Retorna historial de mensajes."""
        with self._lock:
            return [m.to_dict() for m in self._history[-limit:]]

    def clear(self):
        """Limpia el bus."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        with self._lock:
            self._history.clear()

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)
