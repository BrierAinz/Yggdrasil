"""
SessionManager - MÃ³dulo de persistencia de sesiones para Lilith

Proporciona:
- Guardado automÃ¡tico de estado de conversaciÃ³n
- SerializaciÃ³n del estado del Core (memoria, contexto)
- RestauraciÃ³n de sesiones al reiniciar
- MÃºltiples sesiones nombradas
- Auto-guardado periÃ³dico
"""

import gzip
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SessionManager")


@dataclass
class SessionMessage:
    """Mensaje de la conversaciÃ³n"""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionState:
    """Estado completo de una sesiÃ³n"""

    session_id: str
    name: str
    created_at: str
    updated_at: str
    messages: List[SessionMessage]
    context: Dict[str, Any]  # Contexto del proyecto, git, etc.
    core_state: Dict[str, Any]  # Estado serializado del Core
    workspace_path: Optional[str]
    project_path: Optional[str]
    git_branch: Optional[str]
    custom_data: Dict[str, Any]  # Datos adicionales

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context,
            "core_state": self.core_state,
            "workspace_path": self.workspace_path,
            "project_path": self.project_path,
            "git_branch": self.git_branch,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionState":
        return cls(
            session_id=data["session_id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=[SessionMessage.from_dict(m) for m in data.get("messages", [])],
            context=data.get("context", {}),
            core_state=data.get("core_state", {}),
            workspace_path=data.get("workspace_path"),
            project_path=data.get("project_path"),
            git_branch=data.get("git_branch"),
            custom_data=data.get("custom_data", {}),
        )


class SessionManager:
    """
    Manager de sesiones para Lilith.

    Permite:
    - Guardar y cargar sesiones de conversaciÃ³n
    - Auto-guardado periÃ³dico
    - MÃºltiples sesiones nombradas
    - CompresiÃ³n de datos para ahorrar espacio
    """

    def __init__(self, storage_path: Optional[str] = None):
        # Use project Memory/sessions directory by default
        project_root = Path(__file__).parent.parent.parent
        default_path = project_root / "Memory" / "sessions"
        self.storage_path = Path(storage_path or default_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.current_session: Optional[SessionState] = None
        self._auto_save_interval = 30  # segundos
        self._auto_save_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

        logger.info(f"SessionManager initialized at {self.storage_path}")

    def _get_session_file(self, session_id: str) -> Path:
        """Obtener ruta del archivo de sesiÃ³n"""
        return self.storage_path / f"{session_id}.json.gz"

    def _get_session_info_file(self, session_id: str) -> Path:
        """Obtener ruta del archivo de info (sin comprimir, para listado rÃ¡pido)"""
        return self.storage_path / f"{session_id}.info.json"

    def create_session(
        self, name: str = "default", workspace_path: Optional[str] = None
    ) -> SessionState:
        """
        Crear una nueva sesiÃ³n

        Args:
            name: Nombre descriptivo de la sesiÃ³n
            workspace_path: Ruta del workspace

        Returns:
            SessionState creada
        """
        now = datetime.now().isoformat()
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"

        session = SessionState(
            session_id=session_id,
            name=name,
            created_at=now,
            updated_at=now,
            messages=[],
            context={},
            core_state={},
            workspace_path=workspace_path,
            project_path=None,
            git_branch=None,
            custom_data={},
        )

        self.current_session = session
        self._save_session(session)

        logger.info(f"Created session: {session_id} ({name})")
        return session

    def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Cargar una sesiÃ³n existente

        Args:
            session_id: ID de la sesiÃ³n

        Returns:
            SessionState o None si no existe
        """
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            # Intentar sin compresiÃ³n (legacy)
            legacy_file = self.storage_path / f"{session_id}.json"
            if legacy_file.exists():
                session_file = legacy_file
            else:
                logger.warning(f"Session not found: {session_id}")
                return None

        try:
            if session_file.suffix == ".gz":
                with gzip.open(session_file, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

            session = SessionState.from_dict(data)
            self.current_session = session

            logger.info(f"Loaded session: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def save_current_session(self, force: bool = False) -> bool:
        """
        Guardar la sesiÃ³n actual

        Args:
            force: Si True, guarda incluso si no hay cambios

        Returns:
            True si se guardÃ³ exitosamente
        """
        if self.current_session is None:
            return False

        with self._lock:
            self.current_session.updated_at = datetime.now().isoformat()
            return self._save_session(self.current_session)

    def _save_session(self, session: SessionState) -> bool:
        """Guardar sesiÃ³n a disco"""
        try:
            session_file = self._get_session_file(session.session_id)
            info_file = self._get_session_info_file(session.session_id)

            # Guardar datos completos (comprimidos)
            data = session.to_dict()
            with gzip.open(session_file, "wt", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Guardar info bÃ¡sica (sin comprimir, para listado rÃ¡pido)
            info = {
                "session_id": session.session_id,
                "name": session.name,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "message_count": len(session.messages),
                "workspace_path": session.workspace_path,
                "project_path": session.project_path,
            }
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False

    def add_message(
        self, role: str, content: str, metadata: Optional[Dict] = None
    ) -> bool:
        """
        AÃ±adir mensaje a la sesiÃ³n actual

        Args:
            role: "user", "assistant", o "system"
            content: Contenido del mensaje
            metadata: Metadatos adicionales

        Returns:
            True si se aÃ±adiÃ³ exitosamente
        """
        if self.current_session is None:
            # Crear sesiÃ³n default si no existe
            self.create_session("default")

        message = SessionMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
        )

        with self._lock:
            self.current_session.messages.append(message)
            # Limitar historial a Ãºltimos 1000 mensajes
            if len(self.current_session.messages) > 1000:
                self.current_session.messages = self.current_session.messages[-1000:]

        return True

    def update_context(self, context_updates: Dict[str, Any]) -> bool:
        """
        Actualizar contexto de la sesiÃ³n

        Args:
            context_updates: Diccionario con actualizaciones de contexto

        Returns:
            True si se actualizÃ³ exitosamente
        """
        if self.current_session is None:
            return False

        with self._lock:
            self.current_session.context.update(context_updates)

        return True

    def update_core_state(self, core_state: Dict[str, Any]) -> bool:
        """
        Actualizar estado del Core

        Args:
            core_state: Estado serializado del Core

        Returns:
            True si se actualizÃ³ exitosamente
        """
        if self.current_session is None:
            return False

        with self._lock:
            self.current_session.core_state = core_state

        return True

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Listar sesiones disponibles

        Args:
            limit: MÃ¡ximo nÃºmero de sesiones a retornar

        Returns:
            Lista de informaciÃ³n de sesiones
        """
        sessions = []
        seen_ids = set()

        try:
            # Buscar archivos .info.json (mÃ¡s rÃ¡pido que cargar todo)
            info_files = sorted(
                self.storage_path.glob("*.info.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for info_file in info_files[:limit]:
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        sessions.append(info)
                        seen_ids.add(info.get("session_id", ""))
                except:
                    continue

            # Also check for .json files from memory/session_manager
            json_files = sorted(
                self.storage_path.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            for json_file in json_files[:limit]:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        session_id = data.get("session_id", "")
                        if session_id and session_id not in seen_ids:
                            # Convert to expected format — usar summary como nombre si está disponible
                            summary = data.get("summary", "").strip()
                            sessions.append(
                                {
                                    "session_id": session_id,
                                    "name": summary or session_id,
                                    "summary": summary,
                                    "created_at": data.get("saved_at", ""),
                                    "updated_at": data.get("saved_at", ""),
                                    "message_count": data.get("message_count", 0),
                                    "workspace_path": None,
                                    "project_path": None,
                                }
                            )
                except:
                    continue

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Eliminar una sesiÃ³n

        Args:
            session_id: ID de la sesiÃ³n

        Returns:
            True si se eliminÃ³ exitosamente
        """
        try:
            session_file = self._get_session_file(session_id)
            info_file = self._get_session_info_file(session_id)

            if session_file.exists():
                session_file.unlink()
            if info_file.exists():
                info_file.unlink()

            # Si es la sesiÃ³n actual, limpiar
            if self.current_session and self.current_session.session_id == session_id:
                self.current_session = None

            logger.info(f"Deleted session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """
        Renombrar una sesiÃ³n

        Args:
            session_id: ID de la sesiÃ³n
            new_name: Nuevo nombre

        Returns:
            True si se renombrÃ³ exitosamente
        """
        session = self.load_session(session_id)
        if session is None:
            return False

        session.name = new_name
        session.updated_at = datetime.now().isoformat()

        return self._save_session(session)

    def start_auto_save(self):
        """Iniciar auto-guardado periÃ³dico"""
        self._schedule_auto_save()

    def stop_auto_save(self):
        """Detener auto-guardado"""
        if self._auto_save_timer:
            self._auto_save_timer.cancel()
            self._auto_save_timer = None

    def _schedule_auto_save(self):
        """Programar prÃ³ximo auto-guardado"""
        self._auto_save_timer = threading.Timer(
            self._auto_save_interval, self._auto_save_callback
        )
        self._auto_save_timer.daemon = True
        self._auto_save_timer.start()

    def _auto_save_callback(self):
        """Callback de auto-guardado"""
        try:
            if self.current_session:
                self.save_current_session()
                logger.debug(f"Auto-saved session: {self.current_session.session_id}")
        except Exception as e:
            logger.error(f"Error in auto-save: {e}")
        finally:
            # Reprogramar
            self._schedule_auto_save()

    def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """Obtener informaciÃ³n de la sesiÃ³n actual"""
        if self.current_session is None:
            return None

        return {
            "session_id": self.current_session.session_id,
            "name": self.current_session.name,
            "created_at": self.current_session.created_at,
            "updated_at": self.current_session.updated_at,
            "message_count": len(self.current_session.messages),
            "workspace_path": self.current_session.workspace_path,
            "project_path": self.current_session.project_path,
            "git_branch": self.current_session.git_branch,
        }

    def export_session(self, session_id: str, format: str = "json") -> Optional[str]:
        """
        Exportar sesiÃ³n a formato legible

        Args:
            session_id: ID de la sesiÃ³n
            format: "json" o "markdown"

        Returns:
            String con la sesiÃ³n exportada
        """
        session = self.load_session(session_id)
        if session is None:
            return None

        if format == "json":
            return json.dumps(session.to_dict(), indent=2, ensure_ascii=False)

        elif format == "markdown":
            lines = [
                f"# Session: {session.name}",
                f"",
                f"**ID:** {session.session_id}",
                f"**Created:** {session.created_at}",
                f"**Updated:** {session.updated_at}",
                f"**Messages:** {len(session.messages)}",
                f"",
                f"## Conversation",
                f"",
            ]

            for msg in session.messages:
                role_emoji = {
                    "user": "ðŸ‘¤",
                    "assistant": "ðŸ¤–",
                    "system": "âš™ï¸",
                }.get(msg.role, "ðŸ’¬")
                lines.append(f"### {role_emoji} {msg.role.title()} ({msg.timestamp})")
                lines.append(f"")
                lines.append(msg.content)
                lines.append(f"")

            return "\n".join(lines)

        return None


# Singleton
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtener instancia singleton"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        _session_manager.start_auto_save()
    return _session_manager


# === Testing ===
if __name__ == "__main__":
    print("=" * 60)
    print("SessionManager - Test Suite")
    print("=" * 60)

    manager = get_session_manager()

    # Test 1: Crear sesiÃ³n
    print("\n[Test 1] Crear sesiÃ³n")
    session = manager.create_session("test-session", "/home/user/project")
    print(f"âœ“ Session created: {session.session_id}")
    print(f"âœ“ Name: {session.name}")

    # Test 2: AÃ±adir mensajes
    print("\n[Test 2] AÃ±adir mensajes")
    manager.add_message("user", "Hola Lilith")
    manager.add_message("assistant", "Â¡Hola! Â¿En quÃ© puedo ayudarte?")
    manager.add_message("user", "Analiza este cÃ³digo")
    print(f"âœ“ Added 3 messages")

    # Test 3: Guardar sesiÃ³n
    print("\n[Test 3] Guardar sesiÃ³n")
    manager.save_current_session()
    print(f"âœ“ Session saved")

    # Test 4: Listar sesiones
    print("\n[Test 4] Listar sesiones")
    sessions = manager.list_sessions()
    print(f"âœ“ Found {len(sessions)} sessions")
    for s in sessions:
        print(f"  - {s['name']} ({s['message_count']} messages)")

    # Test 5: Exportar a markdown
    print("\n[Test 5] Exportar a Markdown")
    export = manager.export_session(session.session_id, "markdown")
    print(export[:500] + "..." if export else "Failed")

    # Test 6: Eliminar sesiÃ³n
    print("\n[Test 6] Eliminar sesiÃ³n")
    manager.delete_session(session.session_id)
    print(f"âœ“ Session deleted")

    # Cleanup
    manager.stop_auto_save()

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
