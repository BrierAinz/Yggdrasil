"""
Lilith v5.2 — CustomMacroManager
================================

Gestión de macros custom creadas por usuarios o aprendidas automáticamente.

Features:
- CRUD completo de macros custom
- Validación de templates y operaciones
- Merge con macros predefinidas
- Persistencia en JSON
- Versionado de macros
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.json_safe import safe_load
from src.core.pc_macro_engine import Macro, MacroStep

logger = logging.getLogger("lilith.macro.custom_manager")


@dataclass
class CustomMacro:
    """Macro custom con metadata adicional."""

    name: str
    description: str
    steps: List[MacroStep]
    params: Dict[str, Any]
    created_by: str
    created_at: str
    updated_at: str
    source: str  # 'manual', 'learned', 'suggested', 'imported'
    version: int = 1
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    usage_count: int = 0
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario serializable."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [{"operation": s.operation, **s.params} for s in self.steps],
            "params": self.params,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "version": self.version,
            "tags": self.tags,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "CustomMacro":
        """Crea CustomMacro desde diccionario."""
        steps_data = data.get("steps", data.get("operations", []))
        steps = [
            MacroStep(
                operation=s.get("operation", s.get("op", "")),
                params={k: v for k, v in s.items() if k not in ("operation", "op")},
            )
            for s in steps_data
        ]

        return cls(
            name=name,
            description=data.get("description", ""),
            steps=steps,
            params=data.get("params", {}),
            created_by=data.get("created_by", "unknown"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            source=data.get("source", "manual"),
            version=data.get("version", 1),
            tags=data.get("tags", []),
            is_active=data.get("is_active", True),
            usage_count=data.get("usage_count", 0),
            last_used=data.get("last_used"),
        )

    def to_macro(self) -> Macro:
        """Convierte a Macro estándar."""
        return Macro(
            name=self.name,
            description=self.description,
            requires_confirmation=True,  # Las custom siempre requieren confirmación
            steps=self.steps,
            params=self.params,
        )


class CustomMacroManager:
    """
    Gestiona macros custom creadas por usuarios.

    Features:
    - CRUD completo
    - Validación de operaciones permitidas
    - Persistencia automática
    - Merge con macros predefinidas
    """

    # Operaciones permitidas en macros custom
    ALLOWED_OPERATIONS = {
        "mkdir",
        "copy",
        "move",
        "delete",
        "exec",
        "write_file",
        "append_file",
        "list",
    }

    # Parámetros requeridos por operación
    REQUIRED_PARAMS = {
        "mkdir": ["path"],
        "copy": ["source", "destination"],
        "move": ["source", "destination"],
        "delete": ["path"],
        "exec": ["command"],
        "write_file": ["path", "content"],
        "append_file": ["path", "content"],
        "list": ["path"],
    }

    def __init__(
        self,
        storage_path: Path,
        max_per_user: int = 50,
        require_approval: bool = False,
    ):
        """
        Inicializa el manager.

        Args:
            storage_path: Ruta al archivo JSON de storage
            max_per_user: Máximo de macros por usuario
            require_approval: Si requiere aprobación manual
        """
        self.storage_path = Path(storage_path)
        self.max_per_user = max_per_user
        self.require_approval = require_approval

        self.custom_macros: Dict[str, CustomMacro] = {}
        self.predefined_macros: Dict[str, Macro] = {}
        self._user_counts: Dict[str, int] = {}  # Conteo por usuario

        self._ensure_storage()
        self._load_custom_macros()

    def _ensure_storage(self):
        """Asegura que existe el directorio de storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_custom_macros(self):
        """Carga macros custom desde archivo."""
        data = safe_load(self.storage_path, default={"macros": {}})

        macros_data = data.get("macros", {})
        for name, macro_data in macros_data.items():
            try:
                macro = CustomMacro.from_dict(name, macro_data)
                self.custom_macros[name] = macro
                self._user_counts[macro.created_by] = (
                    self._user_counts.get(macro.created_by, 0) + 1
                )
            except Exception as e:
                logger.warning(
                    "[CustomMacroManager] Error cargando macro %s: %s", name, e
                )

        logger.info(
            "[CustomMacroManager] Cargadas %d macros custom", len(self.custom_macros)
        )

    async def _persist(self):
        """Persiste macros custom a archivo."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "macros": {
                name: macro.to_dict() for name, macro in self.custom_macros.items()
            },
        }

        # Backup del archivo existente
        if self.storage_path.exists():
            backup_path = self.storage_path.with_suffix(
                f".json.backup.{int(time.time())}"
            )
            try:
                self.storage_path.rename(backup_path)
                # Mantener solo últimos 5 backups
                self._cleanup_old_backups()
            except Exception as e:
                logger.warning("[CustomMacroManager] Error creando backup: %s", e)

        # Guardar nuevo archivo
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _cleanup_old_backups(self, keep: int = 5):
        """Limpia backups antiguos manteniendo solo los más recientes."""
        backup_pattern = f"{self.storage_path.stem}.json.backup.*"
        backups = sorted(self.storage_path.parent.glob(backup_pattern))

        for old_backup in backups[:-keep]:
            try:
                old_backup.unlink()
            except Exception:
                pass

    async def create_macro(
        self,
        name: str,
        description: str,
        operations: List[Dict[str, Any]],
        user_id: str,
        params: Optional[Dict[str, Any]] = None,
        source: str = "manual",
        tags: Optional[List[str]] = None,
    ) -> CustomMacro:
        """
        Crea una nueva macro custom.

        Args:
            name: Nombre único de la macro
            description: Descripción legible
            operations: Lista de operaciones
            user_id: ID del usuario creador
            params: Definición de parámetros
            source: Origen ('manual', 'learned', 'suggested')
            tags: Tags opcionales

        Returns:
            CustomMacro creada

        Raises:
            ValueError: Si nombre existe, operaciones inválidas, o límite alcanzado
        """
        # Validar nombre único
        if name in self.custom_macros:
            raise ValueError(f"Macro custom '{name}' ya existe")
        if name in self.predefined_macros:
            raise ValueError(f"Nombre '{name}' está reservado para macro predefinida")

        # Validar límite por usuario
        user_count = self._user_counts.get(user_id, 0)
        if user_count >= self.max_per_user:
            raise ValueError(
                f"Límite de {self.max_per_user} macros alcanzado para usuario {user_id}"
            )

        # Validar operaciones
        self._validate_operations(operations)

        # Convertir operaciones a steps
        steps = [
            MacroStep(
                operation=op.get("operation", op.get("op", "")),
                params={k: v for k, v in op.items() if k not in ("operation", "op")},
            )
            for op in operations
        ]

        # Crear macro
        now = datetime.now().isoformat()
        macro = CustomMacro(
            name=name,
            description=description,
            steps=steps,
            params=params or {},
            created_by=user_id,
            created_at=now,
            updated_at=now,
            source=source,
            version=1,
            tags=tags or [],
        )

        # Guardar
        self.custom_macros[name] = macro
        self._user_counts[user_id] = user_count + 1
        await self._persist()

        logger.info("[CustomMacroManager] Macro '%s' creada por %s", name, user_id)
        return macro

    async def create_from_suggestion(
        self,
        suggestion: Dict[str, Any],
        user_id: str,
        custom_name: Optional[str] = None,
    ) -> CustomMacro:
        """
        Crea macro desde una sugerencia del MacroLearner.

        Args:
            suggestion: Sugerencia generada por MacroLearner
            user_id: ID del usuario
            custom_name: Nombre personalizado (opcional)

        Returns:
            CustomMacro creada
        """
        name = custom_name or suggestion["name"]

        # Asegurar nombre único
        base_name = name
        counter = 1
        while name in self.custom_macros or name in self.predefined_macros:
            name = f"{base_name}_{counter}"
            counter += 1

        return await self.create_macro(
            name=name,
            description=suggestion["description"],
            operations=suggestion["operations"],
            user_id=user_id,
            params=suggestion.get("params", {}),
            source="suggested",
        )

    def _validate_operations(self, operations: List[Dict[str, Any]]):
        """
        Valida que las operaciones sean permitidas y tengan parámetros requeridos.

        Raises:
            ValueError: Si hay operaciones inválidas
        """
        if not operations:
            raise ValueError("La macro debe tener al menos una operación")

        if len(operations) > 20:  # Límite de seguridad
            raise ValueError("Máximo 20 operaciones por macro")

        for i, op in enumerate(operations):
            op_type = op.get("operation", op.get("op", ""))

            if op_type not in self.ALLOWED_OPERATIONS:
                raise ValueError(f"Operación '{op_type}' no permitida (paso {i+1})")

            # Validar parámetros requeridos
            required = self.REQUIRED_PARAMS.get(op_type, [])
            for param in required:
                if param not in op:
                    raise ValueError(
                        f"Parámetro '{param}' requerido para '{op_type}' (paso {i+1})"
                    )

            # Validar que no hay parámetros peligrosos
            for key, value in op.items():
                if key in ("operation", "op"):
                    continue
                if isinstance(value, str):
                    dangerous = [";", "&&", "||", "|", "`", "$("]
                    for d in dangerous:
                        if d in value:
                            raise ValueError(
                                f"Caracteres no permitidos en parámetro '{key}' (paso {i+1})"
                            )

    def get_macro(self, name: str) -> Optional[CustomMacro]:
        """Obtiene una macro custom por nombre."""
        return self.custom_macros.get(name)

    def get_all_macros(
        self,
        user_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[CustomMacro]:
        """
        Lista macros custom.

        Args:
            user_id: Filtrar por usuario (None = todos)
            include_inactive: Incluir macros desactivadas

        Returns:
            Lista de macros ordenadas por uso reciente
        """
        macros = list(self.custom_macros.values())

        if user_id:
            macros = [m for m in macros if m.created_by == user_id]

        if not include_inactive:
            macros = [m for m in macros if m.is_active]

        # Ordenar por último uso (más reciente primero)
        macros.sort(key=lambda m: (m.last_used or "", m.usage_count), reverse=True)

        return macros

    async def update_macro(
        self,
        name: str,
        user_id: str,
        description: Optional[str] = None,
        operations: Optional[List[Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> CustomMacro:
        """
        Actualiza una macro custom existente.

        Args:
            name: Nombre de la macro
            user_id: Usuario que actualiza (debe ser el creador)
            description: Nueva descripción
            operations: Nuevas operaciones
            params: Nuevos parámetros
            tags: Nuevos tags
            is_active: Nuevo estado activo/inactivo

        Returns:
            CustomMacro actualizada
        """
        macro = self.custom_macros.get(name)
        if not macro:
            raise ValueError(f"Macro '{name}' no encontrada")

        # Solo el creador puede modificar (o admin)
        if macro.created_by != user_id and user_id != "admin":
            raise ValueError("No tienes permiso para modificar esta macro")

        # Actualizar campos
        if description is not None:
            macro.description = description

        if operations is not None:
            self._validate_operations(operations)
            macro.steps = [
                MacroStep(
                    operation=op.get("operation", op.get("op", "")),
                    params={
                        k: v for k, v in op.items() if k not in ("operation", "op")
                    },
                )
                for op in operations
            ]

        if params is not None:
            macro.params = params

        if tags is not None:
            macro.tags = tags

        if is_active is not None:
            macro.is_active = is_active

        macro.updated_at = datetime.now().isoformat()
        macro.version += 1

        await self._persist()

        logger.info("[CustomMacroManager] Macro '%s' actualizada por %s", name, user_id)
        return macro

    async def delete_macro(self, name: str, user_id: str) -> bool:
        """
        Elimina una macro custom.

        Args:
            name: Nombre de la macro
            user_id: Usuario que elimina

        Returns:
            True si se eliminó, False si no existía
        """
        macro = self.custom_macros.get(name)
        if not macro:
            return False

        # Solo creador o admin pueden eliminar
        if macro.created_by != user_id and user_id != "admin":
            raise ValueError("No tienes permiso para eliminar esta macro")

        del self.custom_macros[name]
        self._user_counts[macro.created_by] = max(
            0, self._user_counts.get(macro.created_by, 1) - 1
        )

        await self._persist()

        logger.info("[CustomMacroManager] Macro '%s' eliminada por %s", name, user_id)
        return True

    async def record_usage(self, name: str):
        """Registra uso de una macro."""
        macro = self.custom_macros.get(name)
        if macro:
            macro.usage_count += 1
            macro.last_used = datetime.now().isoformat()
            await self._persist()

    def merge_with_predefined(self, predefined: Dict[str, Macro]) -> Dict[str, Macro]:
        """
        Combina macros custom con predefinidas.

        Las custom tienen prioridad sobre predefinidas en caso de conflicto
        (aunque esto no debería pasar por la validación de nombres).

        Args:
            predefined: Diccionario de macros predefinidas

        Returns:
            Diccionario combinado
        """
        merged = dict(predefined)

        for name, custom_macro in self.custom_macros.items():
            if custom_macro.is_active:
                merged[name] = custom_macro.to_macro()

        return merged

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de macros custom."""
        total = len(self.custom_macros)
        active = sum(1 for m in self.custom_macros.values() if m.is_active)
        by_source: Dict[str, int] = {}
        by_user: Dict[str, int] = {}

        for macro in self.custom_macros.values():
            by_source[macro.source] = by_source.get(macro.source, 0) + 1
            by_user[macro.created_by] = by_user.get(macro.created_by, 0) + 1

        total_usage = sum(m.usage_count for m in self.custom_macros.values())

        return {
            "total_macros": total,
            "active_macros": active,
            "inactive_macros": total - active,
            "by_source": by_source,
            "by_user": by_user,
            "total_usage": total_usage,
        }


# Singleton
_custom_macro_manager: Optional[CustomMacroManager] = None


def get_custom_macro_manager(
    base_path: Optional[Path] = None,
    max_per_user: int = 50,
) -> CustomMacroManager:
    """Obtiene instancia singleton del manager."""
    global _custom_macro_manager

    if _custom_macro_manager is None:
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent

        storage_path = Path(base_path) / "Data" / "custom_macros.json"
        _custom_macro_manager = CustomMacroManager(
            storage_path=storage_path,
            max_per_user=max_per_user,
        )

    return _custom_macro_manager
