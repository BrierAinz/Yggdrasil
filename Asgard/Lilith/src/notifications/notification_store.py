"""
Lilith v2.3 — Fase B: Almacén de notificaciones.
Memory/notifications.json, max 50 (FIFO). Campos: id, tipo, mensaje, fecha, leida, accion_url, ref_id (opcional).
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NotificationStore")

MAX_NOTIFICATIONS = 50


class NotificationStore:
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        for name in ("Memory", "memory"):
            self._dir = self.base_path / name
            if self._dir.exists():
                break
        else:
            self._dir = self.base_path / "Memory"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "notifications.json"

    def _load(self) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Failed to load notifications: %s", e)
            return []

    def _save(self, items: List[Dict[str, Any]]) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to save notifications: %s", e)

    def add(
        self,
        tipo: str,
        mensaje: str,
        accion_url: Optional[str] = None,
        ref_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "id": str(uuid.uuid4()),
            "tipo": tipo,
            "mensaje": mensaje,
            "fecha": now,
            "leida": False,
            "accion_url": accion_url or "",
            "ref_id": ref_id or "",
        }
        items = self._load()
        items.append(item)
        if len(items) > MAX_NOTIFICATIONS:
            items = items[-MAX_NOTIFICATIONS:]
        self._save(items)
        return item

    def get_all(self) -> List[Dict[str, Any]]:
        """Lista todas; no leídas primero."""
        items = self._load()
        return sorted(
            items,
            key=lambda x: (x.get("leida", False), x.get("fecha", "")),
            reverse=False,
        )

    def get_unread_count(self) -> int:
        return sum(1 for x in self._load() if not x.get("leida", False))

    def mark_read(self, notification_id: str) -> bool:
        items = self._load()
        for i in items:
            if i.get("id") == notification_id:
                i["leida"] = True
                self._save(items)
                return True
        return False

    def clear(self) -> None:
        self._save([])

    def already_notified_today(self, ref_id: str) -> bool:
        """True si ya existe una notificación con este ref_id hoy."""
        if not ref_id:
            return False
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for item in self._load():
            if item.get("ref_id") == ref_id and (item.get("fecha") or "").startswith(
                today
            ):
                return True
        return False
