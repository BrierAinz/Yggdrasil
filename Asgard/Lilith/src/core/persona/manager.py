"""
Personality Mode Manager - Sistema de modos contextuales

Gestiona modos de personalidad que adaptan el estilo de Lilith:
- Activación manual (/modo)
- Detección automática por triggers
- Modo sticky (persiste por tiempo configurado)
- Persistencia en SQLite
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModeInfo:
    """Información de un modo de personalidad"""

    id: str
    name: str
    description: str
    emoji: str
    color: str
    tone: str
    overlay: str
    triggers: List[str]
    sticky_minutes: int


@dataclass
class ActiveMode:
    """Estado de modo activo en una sesión"""

    session_id: str
    mode_id: str
    activated_at: str
    expires_at: str
    activation_method: str  # 'manual' o 'auto'


class PersonalityModeManager:
    """
    Gestor de modos de personalidad

    Funciones:
    - set_mode: Cambiar modo manualmente
    - detect_and_set_mode: Detectar por triggers
    - get_current_mode_info: Info del modo activo
    - get_mode_overlay: Overlay para prompt
    """

    def __init__(self, config_path: Path, db_path: Path):
        """
        Args:
            config_path: Ruta a personality_modes.json
            db_path: Ruta a attention_stack.db (misma DB)
        """
        self.config_path = config_path
        self.db_path = db_path

        # Cargar configuración
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.modes: Dict[str, ModeInfo] = {}
        self._load_modes()

        self.default_mode = self.config.get("default_mode", "arquitecto")
        self.auto_detection_enabled = self.config["auto_detection"]["enabled"]
        self.min_trigger_matches = self.config["auto_detection"]["min_trigger_matches"]
        self.sticky_enabled = self.config["auto_detection"]["sticky_mode_enabled"]
        self.case_insensitive = self.config["auto_detection"]["case_insensitive"]

        self._ensure_db()

    def _load_modes(self):
        """Cargar modos desde config"""
        for mode_id, mode_data in self.config["modes"].items():
            self.modes[mode_id] = ModeInfo(
                id=mode_id,
                name=mode_data["name"],
                description=mode_data["description"],
                emoji=mode_data["emoji"],
                color=mode_data["color"],
                tone=mode_data["tone"],
                overlay=mode_data["overlay"],
                triggers=mode_data["triggers"],
                sticky_minutes=mode_data["sticky_minutes"],
            )

    def _ensure_db(self):
        """Crear tabla de modos si no existe"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_modes (
                    session_id TEXT PRIMARY KEY,
                    mode_id TEXT NOT NULL,
                    activated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    activation_method TEXT NOT NULL
                )
            """
            )
            conn.commit()

    def set_mode(self, session_id: str, mode_id: str, method: str = "manual") -> bool:
        """
        Cambiar modo manualmente

        Args:
            session_id: ID de sesión
            mode_id: ID del modo (ej: 'arquitecto')
            method: 'manual' o 'auto'

        Returns:
            True si exitoso
        """
        if mode_id not in self.modes:
            logger.warning(f"Unknown mode: {mode_id}")
            return False

        mode = self.modes[mode_id]
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=mode.sticky_minutes)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO active_modes
                (session_id, mode_id, activated_at, expires_at, activation_method)
                VALUES (?, ?, ?, ?, ?)
            """,
                (session_id, mode_id, now.isoformat(), expires.isoformat(), method),
            )
            conn.commit()

        logger.info(f"Set mode {mode_id} for session {session_id}, method={method}")
        return True

    def detect_and_set_mode(self, message: str, session_id: str) -> Optional[str]:
        """
        Detectar modo por triggers en el mensaje

        Args:
            message: Mensaje del usuario
            session_id: ID de sesión

        Returns:
            ID del modo detectado, o None
        """
        if not self.auto_detection_enabled:
            return None

        # Verificar si ya hay un modo activo no expirado
        current = self._get_active_mode(session_id)
        if current and not self._is_expired(current.expires_at):
            # Modo sticky todavía válido
            return None

        # Preparar mensaje para comparación
        msg_compare = message.lower() if self.case_insensitive else message

        # Buscar matches
        best_mode = None
        max_matches = 0

        for mode_id, mode in self.modes.items():
            matches = 0

            for trigger in mode.triggers:
                trigger_compare = trigger.lower() if self.case_insensitive else trigger

                if trigger_compare in msg_compare:
                    matches += 1

            if matches >= self.min_trigger_matches and matches > max_matches:
                max_matches = matches
                best_mode = mode_id

        # Activar modo detectado
        if best_mode:
            self.set_mode(session_id, best_mode, method="auto")
            logger.info(f"Auto-detected mode {best_mode} with {max_matches} matches")
            return best_mode

        return None

    def _get_active_mode(self, session_id: str) -> Optional[ActiveMode]:
        """Obtener modo activo de la DB"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT session_id, mode_id, activated_at, expires_at, activation_method
                FROM active_modes
                WHERE session_id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()

        if not row:
            return None

        return ActiveMode(
            session_id=row[0],
            mode_id=row[1],
            activated_at=row[2],
            expires_at=row[3],
            activation_method=row[4],
        )

    def _is_expired(self, expires_at_iso: str) -> bool:
        """Verificar si un modo expiró"""
        expires = datetime.fromisoformat(expires_at_iso)
        now = datetime.now(timezone.utc)
        return now >= expires

    def get_current_mode_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información del modo actual

        Args:
            session_id: ID de sesión

        Returns:
            Dict con info del modo, o None si no hay modo activo
        """
        active = self._get_active_mode(session_id)

        if not active:
            return None

        # Verificar expiración
        if self._is_expired(active.expires_at):
            # Expirado, limpiar
            self._clear_mode(session_id)
            return None

        mode = self.modes.get(active.mode_id)
        if not mode:
            return None

        return {
            "id": mode.id,
            "name": mode.name,
            "description": mode.description,
            "emoji": mode.emoji,
            "color": mode.color,
            "tone": mode.tone,
            "activated_at": active.activated_at,
            "expires_at": active.expires_at,
            "activation_method": active.activation_method,
        }

    def get_mode_overlay(self, session_id: str) -> str:
        """
        Obtener overlay del modo activo para inyectar en prompt

        Args:
            session_id: ID de sesión

        Returns:
            String con overlay, o "" si no hay modo activo
        """
        active = self._get_active_mode(session_id)

        if not active or self._is_expired(active.expires_at):
            return ""

        mode = self.modes.get(active.mode_id)
        if not mode:
            return ""

        return mode.overlay

    def _clear_mode(self, session_id: str):
        """Limpiar modo expirado"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM active_modes WHERE session_id = ?
            """,
                (session_id,),
            )
            conn.commit()

    def list_all_modes(self) -> List[Dict[str, Any]]:
        """Listar todos los modos disponibles"""
        return [
            {
                "id": mode.id,
                "name": mode.name,
                "description": mode.description,
                "emoji": mode.emoji,
                "tone": mode.tone,
            }
            for mode in self.modes.values()
        ]


# Singleton global
_mode_manager: Optional[PersonalityModeManager] = None


def initialize_mode_manager(config_path: Path, db_path: Path):
    """Inicializar el mode manager global"""
    global _mode_manager
    _mode_manager = PersonalityModeManager(config_path=config_path, db_path=db_path)


def get_personality_mode_manager() -> PersonalityModeManager:
    """Obtener instancia singleton del mode manager"""
    if _mode_manager is None:
        raise ValueError(
            "Mode manager not initialized, call initialize_mode_manager() first"
        )
    return _mode_manager


def detect_and_set_mode(message: str, session_id: str) -> Optional[str]:
    """
    Función de conveniencia para detectar y activar modo

    Args:
        message: Mensaje del usuario
        session_id: ID de sesión

    Returns:
        ID del modo detectado, o None
    """
    manager = get_personality_mode_manager()
    return manager.detect_and_set_mode(message, session_id)


# Aliases para compatibilidad con imports existentes
PersonalityMode = ModeInfo
ModeTransition = ActiveMode


def get_mode_for_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Obtener modo actual para una sesión"""
    manager = get_personality_mode_manager()
    return manager.get_current_mode_info(session_id)


def set_mode_for_session(session_id: str, mode_id: str) -> bool:
    """Establecer modo para una sesión"""
    manager = get_personality_mode_manager()
    return manager.set_mode(session_id, mode_id)
