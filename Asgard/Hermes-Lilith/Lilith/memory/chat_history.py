"""
Chat History
============
Sistema de persistencia de historial de chat.
"""
import json
from datetime import datetime
from pathlib import Path


class ChatHistory:
    """Maneja historial de chat persistente."""

    def __init__(
        self, storage_path: str = "D:/Proyectos/Midgard/Lilith/memory/history.json"
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions = self._load()

    def _load(self) -> list:
        """Carga historial desde archivo."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save(self):
        """Guarda historial a archivo."""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)

    def add_message(self, role: str, content: str, session_id: str = "default"):
        """Agrega mensaje al historial."""
        # Buscar o crear sesión
        session = None
        for s in self.sessions:
            if s["session_id"] == session_id:
                session = s
                break

        if not session:
            session = {
                "session_id": session_id,
                "created": datetime.now().isoformat(),
                "messages": [],
            }
            self.sessions.append(session)

        session["messages"].append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        self._save()

    def get_session(self, session_id: str = "default") -> list:
        """Obtiene mensajes de una sesión."""
        for s in self.sessions:
            if s["session_id"] == session_id:
                return s["messages"]
        return []

    def list_sessions(self) -> list:
        """Lista todas las sesiones."""
        return [
            {
                "session_id": s["session_id"],
                "created": s["created"],
                "message_count": len(s["messages"]),
            }
            for s in self.sessions
        ]

    def clear_session(self, session_id: str = "default"):
        """Limpia una sesión."""
        self.sessions = [s for s in self.sessions if s["session_id"] != session_id]
        self._save()
