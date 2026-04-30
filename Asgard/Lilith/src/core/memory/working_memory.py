"""
Mejora-5 — Working Memory con importancia, decay por mensaje y pins.
Contexto de trabajo activo que se inyecta en el system prompt de cada canal.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("lilith.working_memory")

# Patrones que activan "añadir a working memory"
_REMEMBER_PATTERNS = [
    r"recuerda\s+que\b",
    r"ten\s+en\s+cuenta\s+que\b",
    r"no\s+olvides\s+que\b",
    r"importante[:\s]+",
    r"anota\s+que\b",
    r"nota[:\s]+",
]
_REMEMBER_RE = re.compile("|".join(_REMEMBER_PATTERNS), re.IGNORECASE)

_DEFAULT_DECAY = 0.15  # importancia pierde X por mensaje
_DEFAULT_MIN = 0.05  # umbral bajo el cual el item expira
_DEFAULT_MAX_ITEMS = 20


@dataclass
class WorkingItem:
    key: str
    text: str
    importance: float = 1.0
    pinned: bool = False
    added_at: float = field(default_factory=time.time)

    def tick(self, decay: float) -> None:
        """Reduce importancia en cada mensaje procesado (no afecta pins)."""
        if not self.pinned:
            self.importance = max(0.0, self.importance - decay)

    def is_alive(self, min_importance: float) -> bool:
        return self.pinned or self.importance >= min_importance


class WorkingMemory:
    """
    Memoria de trabajo por canal. Thread-unsafe (un canal = un hilo / event loop).
    Uso:
        wm = WorkingMemory()
        wm.add("nombre_sesion", "Estamos trabajando en el módulo X")
        wm.pin("nombre_sesion")
        prompt_extra = wm.format_for_prompt()
        wm.tick()          # llamar tras cada mensaje procesado
    """

    def __init__(
        self,
        decay_per_message: float = _DEFAULT_DECAY,
        min_importance: float = _DEFAULT_MIN,
        max_items: int = _DEFAULT_MAX_ITEMS,
    ):
        self._items: Dict[str, WorkingItem] = {}
        self._decay = decay_per_message
        self._min = min_importance
        self._max = max_items

    # ── API pública ─────────────────────────────────────────────────────────

    def add(
        self, key: str, text: str, importance: float = 1.0, pinned: bool = False
    ) -> None:
        """Añade o actualiza un ítem de working memory."""
        self._items[key] = WorkingItem(
            key=key,
            text=text.strip(),
            importance=min(max(0.0, importance), 2.0),
            pinned=pinned,
        )
        self._evict()
        logger.debug(
            "WorkingMemory.add: %s (importance=%.2f, pinned=%s)",
            key,
            importance,
            pinned,
        )

    def pin(self, key: str) -> bool:
        """Fija un ítem para que nunca expire por decay."""
        if key in self._items:
            self._items[key].pinned = True
            return True
        return False

    def unpin(self, key: str) -> bool:
        if key in self._items:
            self._items[key].pinned = False
            return True
        return False

    def remove(self, key: str) -> bool:
        return bool(self._items.pop(key, None))

    def tick(self) -> None:
        """Decay + purga de ítems expirados. Llamar una vez por mensaje procesado."""
        for item in list(self._items.values()):
            item.tick(self._decay)
        self._items = {k: v for k, v in self._items.items() if v.is_alive(self._min)}

    def format_for_prompt(self, max_items: int = 10) -> str:
        """Devuelve bloque de texto para inyectar en el system prompt."""
        alive = sorted(
            (v for v in self._items.values() if v.is_alive(self._min)),
            key=lambda x: (-x.importance, x.added_at),
        )[:max_items]
        if not alive:
            return ""
        lines = ["[Contexto activo de trabajo:]"]
        for item in alive:
            pin_mark = " 📌" if item.pinned else ""
            lines.append(f"  · {item.text}{pin_mark}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return not any(v.is_alive(self._min) for v in self._items.values())

    # ── Detección automática desde mensaje ─────────────────────────────────

    @staticmethod
    def extract_from_message(text: str) -> Optional[str]:
        """
        Si el mensaje contiene un patrón tipo "recuerda que X", devuelve X.
        Devuelve None si no hay coincidencia.
        """
        m = _REMEMBER_RE.search(text)
        if not m:
            return None
        after = text[m.end() :].strip()
        # Tomar hasta punto/salto de línea o 200 chars
        end = min(len(after), 200)
        for sep in (".", "\n", "!"):
            idx = after.find(sep)
            if 0 < idx < end:
                end = idx
                break
        extracted = after[:end].strip()
        return extracted if len(extracted) > 3 else None

    # ── Helpers internos ────────────────────────────────────────────────────

    def _evict(self) -> None:
        """Si hay demasiados ítems, elimina los menos importantes (no pinned)."""
        if len(self._items) <= self._max:
            return
        unpinned = sorted(
            [(k, v) for k, v in self._items.items() if not v.pinned],
            key=lambda x: x[1].importance,
        )
        to_remove = len(self._items) - self._max
        for k, _ in unpinned[:to_remove]:
            del self._items[k]


# ── Singleton por canal ──────────────────────────────────────────────────────

_channel_memories: Dict[str, WorkingMemory] = {}


def get_working_memory(channel: str = "discord") -> WorkingMemory:
    """Devuelve (o crea) la WorkingMemory singleton para el canal dado."""
    if channel not in _channel_memories:
        _channel_memories[channel] = WorkingMemory()
    return _channel_memories[channel]
