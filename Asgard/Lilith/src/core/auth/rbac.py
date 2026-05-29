"""
RBAC Manager - Gestión de roles y permisos

v4.2.8: Control de acceso basado en roles
"""
import asyncio
import functools
import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel
from src.core.json_safe import safe_load

from .permissions import Action, Permission, Permissions, Resource, get_all_permissions

logger = logging.getLogger("lilith.rbac")


class Role(Enum):
    """Roles predefinidos del sistema."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    AGENT_ONLY = "agent-only"


# Definición de permisos por rol
ROLE_PERMISSIONS: Dict[Role, Set[str]] = {
    Role.ADMIN: {"*"},  # Todos los permisos
    Role.DEVELOPER: {
        # Tools
        "tools:execute",
        "tools:read",
        "tools:create",
        # Files
        "files:read",
        "files:update",
        "files:delete",
        # Agents
        "agents:execute",
        "agents:read",
        "agents:create",
        # Workflows
        "workflows:execute",
        "workflows:read",
        "workflows:create",
        # Analytics
        "analytics:read",
        # Health
        "health:read",
        # Config (solo lectura)
        "config:read",
        # Chat
        "chat:create",
        "chat:read",
        # Memory
        "memory:read",
        "memory:update",
        # Tasks
        "tasks:execute",
        "tasks:read",
    },
    Role.VIEWER: {
        # Solo lectura
        "tools:read",
        "files:read",
        "agents:read",
        "workflows:read",
        "analytics:read",
        "health:read",
        "config:read",
        "chat:read",
        "memory:read",
        "tasks:read",
    },
    Role.AGENT_ONLY: {
        # Solo chat básico
        "chat:create",
        "chat:read",
    },
}


@dataclass
class User:
    """Usuario del sistema RBAC."""

    id: str
    name: str
    role: Role
    api_key: str
    created_at: datetime
    last_access: Optional[datetime] = None
    is_active: bool = True
    custom_permissions: Set[str] = field(default_factory=set)

    def to_dict(self, include_api_key: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "last_access": self.last_access.isoformat() if self.last_access else None,
            "is_active": self.is_active,
            "custom_permissions": list(self.custom_permissions),
        }
        if include_api_key:
            result["api_key"] = self.api_key
        return result

    def has_permission(self, permission: Permission) -> bool:
        """Verifica si el usuario tiene un permiso específico."""
        # Admin tiene todos los permisos
        if self.role == Role.ADMIN:
            return True

        perm_str = str(permission)

        # Verificar permisos personalizados
        if perm_str in self.custom_permissions:
            return True

        # Verificar permisos del rol
        role_perms = ROLE_PERMISSIONS.get(self.role, set())
        return perm_str in role_perms or "*" in role_perms


class RBACManager:
    """
    Gestor de control de acceso basado en roles.

    Features:
    - 4 roles predefinidos (admin, developer, viewer, agent-only)
    - API keys para autenticación
    - Permisos personalizados por usuario
    - Middleware de autorización
    """

    _instance: Optional["RBACManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.config_path = self.base_path / "Config" / "rbac.json"

        # Usuarios indexados por ID y por API key
        self._users_by_id: Dict[str, User] = {}
        self._users_by_key: Dict[str, User] = {}

        self._load_config()

        # Asegurar que existe al menos un admin
        if not any(u.role == Role.ADMIN for u in self._users_by_id.values()):
            self._create_default_admin()

        self._initialized = True
        logger.info("RBACManager: Inicializado con %d usuarios", len(self._users_by_id))

    def _load_config(self):
        """Carga configuración de usuarios."""
        config = safe_load(self.config_path, default={"users": []})

        for user_data in config.get("users", []):
            try:
                user = User(
                    id=user_data["id"],
                    name=user_data["name"],
                    role=Role(user_data["role"]),
                    api_key=user_data["api_key"],
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                    last_access=datetime.fromisoformat(user_data["last_access"])
                    if user_data.get("last_access")
                    else None,
                    is_active=user_data.get("is_active", True),
                    custom_permissions=set(user_data.get("custom_permissions", [])),
                )
                self._users_by_id[user.id] = user
                self._users_by_key[user.api_key] = user
            except Exception as e:
                logger.warning("Error cargando usuario: %s", e)

    def _save_config(self):
        """Guarda configuración de usuarios."""
        config = {
            "users": [
                u.to_dict(include_api_key=True) for u in self._users_by_id.values()
            ],
            "roles": {
                role.value: list(perms) for role, perms in ROLE_PERMISSIONS.items()
            },
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Error guardando RBAC config: %s", e)

    def _create_default_admin(self):
        """Crea un usuario admin por defecto."""
        api_key = "lilith-admin-" + secrets.token_urlsafe(16)
        admin = User(
            id="admin",
            name="Administrator",
            role=Role.ADMIN,
            api_key=api_key,
            created_at=datetime.utcnow(),
        )
        self._users_by_id[admin.id] = admin
        self._users_by_key[admin.api_key] = admin
        self._save_config()

        logger.warning(
            "RBAC: Creado admin por defecto con API key: %s", api_key[:20] + "..."
        )

    # CRUD Usuarios

    def create_user(
        self, name: str, role: Role, custom_permissions: Optional[Set[str]] = None
    ) -> User:
        """
        Crea un nuevo usuario.

        Args:
            name: Nombre del usuario
            role: Rol del usuario
            custom_permissions: Permisos adicionales específicos

        Returns:
            Usuario creado
        """
        api_key = "lk-" + secrets.token_urlsafe(32)

        user = User(
            id=secrets.token_hex(8),
            name=name,
            role=role,
            api_key=api_key,
            created_at=datetime.utcnow(),
            custom_permissions=custom_permissions or set(),
        )

        self._users_by_id[user.id] = user
        self._users_by_key[user.api_key] = user
        self._save_config()

        logger.info("RBAC: Creado usuario %s (%s)", user.id, role.value)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene un usuario por ID."""
        return self._users_by_id.get(user_id)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Obtiene un usuario por API key."""
        return self._users_by_key.get(api_key)

    def list_users(self) -> List[User]:
        """Lista todos los usuarios."""
        return list(self._users_by_id.values())

    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Actualiza un usuario."""
        user = self._users_by_id.get(user_id)
        if not user:
            return None

        allowed = {"name", "role", "is_active", "custom_permissions"}
        for key, value in kwargs.items():
            if key in allowed:
                if key == "role" and isinstance(value, str):
                    value = Role(value)
                setattr(user, key, value)

        self._save_config()
        return user

    def delete_user(self, user_id: str) -> bool:
        """Elimina un usuario."""
        user = self._users_by_id.get(user_id)
        if not user:
            return False

        del self._users_by_id[user_id]
        del self._users_by_key[user.api_key]
        self._save_config()
        return True

    def regenerate_api_key(self, user_id: str) -> Optional[str]:
        """Regenera la API key de un usuario."""
        user = self._users_by_id.get(user_id)
        if not user:
            return None

        # Eliminar referencia vieja
        del self._users_by_key[user.api_key]

        # Generar nueva key
        user.api_key = "lk-" + secrets.token_urlsafe(32)
        self._users_by_key[user.api_key] = user

        self._save_config()
        return user.api_key

    # Autorización

    def authenticate(self, api_key: str) -> Optional[User]:
        """
        Autentica un usuario por API key.

        Args:
            api_key: API key a verificar

        Returns:
            Usuario autenticado o None
        """
        user = self._users_by_key.get(api_key)
        if user and user.is_active:
            user.last_access = datetime.utcnow()
            return user
        return None

    def check_permission(self, user: User, resource: Resource, action: Action) -> bool:
        """
        Verifica si un usuario tiene un permiso.

        Args:
            user: Usuario a verificar
            resource: Recurso a acceder
            action: Acción a realizar

        Returns:
            True si tiene permiso
        """
        return user.has_permission(Permission(resource, action))

    def require(self, resource: Resource, action: Action) -> Callable:
        """
        Decorador para requerir permiso en una función.

        Args:
            resource: Recurso requerido
            action: Acción requerida
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Buscar usuario en kwargs o en request
                user = kwargs.get("user") or kwargs.get("current_user")
                if not user:
                    raise HTTPException(status_code=401, detail="No autenticado")

                if not self.check_permission(user, resource, action):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permiso denegado: {resource.value}:{action.value}",
                    )

                return await func(*args, **kwargs)

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                user = kwargs.get("user") or kwargs.get("current_user")
                if not user:
                    raise HTTPException(status_code=401, detail="No autenticado")

                if not self.check_permission(user, resource, action):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permiso denegado: {resource.value}:{action.value}",
                    )

                return func(*args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    # Información de roles

    def get_role_permissions(self, role: Role) -> List[str]:
        """Obtiene los permisos de un rol."""
        perms = ROLE_PERMISSIONS.get(role, set())
        if "*" in perms:
            return [str(p) for p in get_all_permissions()]
        return sorted(list(perms))

    def list_roles(self) -> List[Dict[str, Any]]:
        """Lista todos los roles con sus permisos."""
        return [
            {
                "value": role.value,
                "name": role.value.replace("-", " ").title(),
                "permissions": self.get_role_permissions(role),
            }
            for role in Role
        ]


# Singleton
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager(base_path: Optional[Path] = None) -> RBACManager:
    """Obtiene instancia del RBACManager."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager(base_path)
    return _rbac_manager


# FastAPI dependency
async def get_current_user(request: Request) -> Optional[User]:
    """
    Dependency de FastAPI para obtener usuario actual.

    Lee API key del header X-API-Key o Authorization Bearer.
    """
    # Intentar X-API-Key
    api_key = request.headers.get("X-API-Key")

    # Intentar Authorization: Bearer <token>
    if not api_key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            api_key = auth[7:]

    if not api_key:
        return None

    rbac = get_rbac_manager()
    return rbac.authenticate(api_key)


# Decorador helper para endpoints
def require_permission(resource: Resource, action: Action):
    """Decorator para requerir permiso en endpoints FastAPI."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar request en args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise HTTPException(status_code=500, detail="Request no disponible")

            user = await get_current_user(request)
            if not user:
                raise HTTPException(
                    status_code=401, detail="API key inválida o no proporcionada"
                )

            rbac = get_rbac_manager()
            if not rbac.check_permission(user, resource, action):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permiso denegado: {resource.value}:{action.value}",
                )

            # Agregar usuario a kwargs
            kwargs["current_user"] = user
            return await func(*args, **kwargs)

        return wrapper

    return decorator
