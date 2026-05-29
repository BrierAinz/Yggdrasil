"""
Permissions - Definición de permisos del sistema

v4.2.8: Permisos basados en recursos y acciones
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Set


class Resource(Enum):
    """Recursos del sistema protegidos por RBAC."""

    TOOLS = "tools"
    FILES = "files"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    ANALYTICS = "analytics"
    HEALTH = "health"
    CONFIG = "config"
    CHAT = "chat"
    WEBHOOKS = "webhooks"
    CACHE = "cache"
    MEMORY = "memory"
    TASKS = "tasks"
    PLUGINS = "plugins"


class Action(Enum):
    """Acciones posibles sobre los recursos."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"  # Para ejecutar herramientas/agentes
    LIST = "list"  # Para listar colecciones
    ADMIN = "admin"  # Acciones administrativas


@dataclass(frozen=True)
class Permission:
    """
    Un permiso se define como recurso + acción.

    Ejemplo: Permission(Resource.TOOLS, Action.EXECUTE)
    """

    resource: Resource
    action: Action

    def __str__(self) -> str:
        return f"{self.resource.value}:{self.action.value}"

    @classmethod
    def from_string(cls, permission_str: str) -> "Permission":
        """Crea un permiso desde string formato 'resource:action'."""
        parts = permission_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Formato inválido: {permission_str}")
        return cls(resource=Resource(parts[0]), action=Action(parts[1]))


# Permisos predefinidos comunes
class Permissions:
    """Constantes de permisos frecuentemente usados."""

    # Tools
    TOOLS_EXECUTE = Permission(Resource.TOOLS, Action.EXECUTE)
    TOOLS_READ = Permission(Resource.TOOLS, Action.READ)
    TOOLS_CREATE = Permission(Resource.TOOLS, Action.CREATE)

    # Files
    FILES_READ = Permission(Resource.FILES, Action.READ)
    FILES_WRITE = Permission(Resource.FILES, Action.UPDATE)
    FILES_DELETE = Permission(Resource.FILES, Action.DELETE)

    # Agents
    AGENTS_DELEGATE = Permission(Resource.AGENTS, Action.EXECUTE)
    AGENTS_READ = Permission(Resource.AGENTS, Action.READ)
    AGENTS_CREATE = Permission(Resource.AGENTS, Action.CREATE)

    # Workflows
    WORKFLOWS_EXECUTE = Permission(Resource.WORKFLOWS, Action.EXECUTE)
    WORKFLOWS_READ = Permission(Resource.WORKFLOWS, Action.READ)
    WORKFLOWS_CREATE = Permission(Resource.WORKFLOWS, Action.CREATE)

    # Analytics
    ANALYTICS_VIEW = Permission(Resource.ANALYTICS, Action.READ)

    # Health
    HEALTH_VIEW = Permission(Resource.HEALTH, Action.READ)

    # Config
    CONFIG_READ = Permission(Resource.CONFIG, Action.READ)
    CONFIG_WRITE = Permission(Resource.CONFIG, Action.UPDATE)

    # Chat
    CHAT_SEND = Permission(Resource.CHAT, Action.CREATE)
    CHAT_RECEIVE = Permission(Resource.CHAT, Action.READ)

    # Webhooks
    WEBHOOKS_MANAGE = Permission(Resource.WEBHOOKS, Action.ADMIN)

    # Cache
    CACHE_MANAGE = Permission(Resource.CACHE, Action.ADMIN)

    # Admin (todos los permisos)
    ALL = "*"


def get_all_permissions() -> List[Permission]:
    """Genera todas las combinaciones posibles de permisos."""
    permissions = []
    for resource in Resource:
        for action in Action:
            permissions.append(Permission(resource, action))
    return permissions
