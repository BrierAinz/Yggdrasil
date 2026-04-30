"""
ProgressManager — Singleton para streaming de progreso de tareas via WebSocket.
Permite que el backend publique eventos de progreso que el frontend/Discord consumen.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.progress_manager")

# ─── Evento de progreso ───────────────────────────────────────────────────────


@dataclass
class ProgressEvent:
    request_id: str
    step: str  # nombre del step/tool actual
    status: str  # "started" | "running" | "done" | "error"
    message: str = ""
    pct: float = 0.0  # 0.0–1.0
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── ProgressManager ──────────────────────────────────────────────────────────


class ProgressManager:
    """
    Singleton que mantiene colas de eventos de progreso por request_id.
    Los WebSocket consumers suscriben a un request_id y consumen eventos.
    """

    def __init__(self) -> None:
        # request_id → lista de asyncio.Queue (una por suscriptor)
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        # request_id → buffer de últimos 50 eventos (para nuevos suscriptores que conectan tarde)
        self._history: Dict[str, List[ProgressEvent]] = {}
        self._MAX_HISTORY = 50

    def create_request(self) -> str:
        """Crea un nuevo request_id y retorna el ID."""
        rid = uuid.uuid4().hex
        self._subscribers[rid] = []
        self._history[rid] = []
        return rid

    def subscribe(self, request_id: str) -> asyncio.Queue:
        """Suscribe a los eventos de un request_id. Retorna la Queue del suscriptor."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        if request_id not in self._subscribers:
            self._subscribers[request_id] = []
            self._history[request_id] = []
        # Replay de historia para el nuevo suscriptor
        for evt in self._history.get(request_id, []):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                pass
        self._subscribers[request_id].append(q)
        return q

    def unsubscribe(self, request_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(request_id, [])
        try:
            subs.remove(queue)
        except ValueError:
            pass

    def publish(self, event: ProgressEvent) -> None:
        """Publica un evento (sync). Llamar desde código sync o desde thread."""
        rid = event.request_id

        # Guardar en historia
        hist = self._history.setdefault(rid, [])
        hist.append(event)
        if len(hist) > self._MAX_HISTORY:
            self._history[rid] = hist[-self._MAX_HISTORY :]

        # Distribuir a suscriptores
        for q in list(self._subscribers.get(rid, [])):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("progress queue full for request_id=%s", rid)

    async def apublish(self, event: ProgressEvent) -> None:
        """Publica un evento (async)."""
        self.publish(event)

    def cleanup(self, request_id: str) -> None:
        """Limpia estado de un request_id completado."""
        self._subscribers.pop(request_id, None)
        self._history.pop(request_id, None)

    def step_callback(self, request_id: str, total_steps: int):
        """
        Retorna una función callback(step_index, tool_name, status, message)
        que publica ProgressEvents para el request_id dado.
        Usar en execute_steps como progress_callback.
        """

        def _cb(
            step_index: int, tool_name: str, status: str, message: str = ""
        ) -> None:
            pct = (step_index + (1 if status == "done" else 0)) / max(total_steps, 1)
            self.publish(
                ProgressEvent(
                    request_id=request_id,
                    step=tool_name,
                    status=status,
                    message=message,
                    pct=min(pct, 1.0),
                )
            )

        return _cb


# ─── Singleton ────────────────────────────────────────────────────────────────

_pm: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    global _pm
    if _pm is None:
        _pm = ProgressManager()
    return _pm
