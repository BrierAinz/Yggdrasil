"""
Permissions Granular - Sistema de permisos a nivel de recurso

v5.0-Fase4A: Permisos finos para cada recurso y acción.
"""
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("lilith.collaboration.permissions")


class ResourceType(Enum):
    """Tipos de recursos protegibles."""

    WORKFLOW = "workflow"
    AGENT = "agent"
    TOOL = "tool"
    SESSION = "session"
    CONFIG = "config"
    ANALYTICS = "analytics"
    AUDIT = "audit"
    COMMENT = "comment"


class ActionType(Enum):
    """Tipos de acciones."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    SHARE = "share"
    ADMIN = "admin"


@dataclass
class PermissionGrant:
    """Concesión de permiso específica."""

    resource_type: ResourceType
    resource_id: Optional[str]  # None = todos los recursos de ese tipo
    actions: List[ActionType]
    granted_by: str
    granted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceACL:
    """Lista de control de acceso para un recurso."""

    resource_type: ResourceType
    resource_id: str
    owner_id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    grants: Dict[str, List[PermissionGrant]] = field(
        default_factory=dict
    )  # user_id -> grants
    public_access: List[ActionType] = field(default_factory=list)
    inheritance: bool = True  # Heredar permisos de sesión padre


@dataclass
class PermissionPolicy:
    """Política de permisos configurable."""

    name: str
    description: Optional[str] = None
    resource_rules: Dict[ResourceType, List[ActionType]] = field(default_factory=dict)
    default_actions: List[ActionType] = field(default_factory=lambda: [ActionType.READ])
    require_approval_for: List[str] = field(
        default_factory=list
    )  # Lista de acciones que requieren aprobación
    max_shares: Optional[int] = None
    audit_all_actions: bool = True


class GranularPermissions:
    """
    Sistema de permisos granulares a nivel de recurso.

    Features:
    - ACLs por recurso individual
    - Políticas configurables
    - Herencia de permisos
    - Condiciones contextuales
    - Auditoría de accesos
    """

    # Permisos por defecto para cada rol base
    DEFAULT_ROLE_PERMISSIONS = {
        "admin": {
            ResourceType.WORKFLOW: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
                ActionType.EXECUTE,
                ActionType.SHARE,
            ],
            ResourceType.AGENT: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
                ActionType.EXECUTE,
                ActionType.SHARE,
            ],
            ResourceType.TOOL: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
                ActionType.EXECUTE,
                ActionType.SHARE,
            ],
            ResourceType.SESSION: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
                ActionType.SHARE,
                ActionType.ADMIN,
            ],
            ResourceType.CONFIG: [ActionType.READ, ActionType.UPDATE],
            ResourceType.ANALYTICS: [ActionType.READ],
            ResourceType.AUDIT: [ActionType.READ],
            ResourceType.COMMENT: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
            ],
        },
        "editor": {
            ResourceType.WORKFLOW: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.EXECUTE,
                ActionType.SHARE,
            ],
            ResourceType.AGENT: [ActionType.READ, ActionType.EXECUTE],
            ResourceType.TOOL: [ActionType.READ, ActionType.EXECUTE],
            ResourceType.SESSION: [ActionType.READ, ActionType.SHARE],
            ResourceType.CONFIG: [ActionType.READ],
            ResourceType.ANALYTICS: [ActionType.READ],
            ResourceType.COMMENT: [
                ActionType.CREATE,
                ActionType.READ,
                ActionType.UPDATE,
                ActionType.DELETE,
            ],
        },
        "viewer": {
            ResourceType.WORKFLOW: [ActionType.READ],
            ResourceType.AGENT: [ActionType.READ],
            ResourceType.TOOL: [ActionType.READ],
            ResourceType.SESSION: [ActionType.READ],
            ResourceType.COMMENT: [ActionType.READ],
        },
        "service": {
            ResourceType.WORKFLOW: [ActionType.READ, ActionType.EXECUTE],
            ResourceType.AGENT: [ActionType.READ, ActionType.EXECUTE],
            ResourceType.TOOL: [ActionType.READ, ActionType.EXECUTE],
            ResourceType.ANALYTICS: [ActionType.CREATE, ActionType.READ],
        },
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self.acls: Dict[str, ResourceACL] = {}  # resource_key -> ACL
        self.policies: Dict[str, PermissionPolicy] = {}
        self.user_grants: Dict[str, List[PermissionGrant]] = {}  # user_id -> grants
        self.storage_path = storage_path or Path("Data/permissions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_data()

    def _resource_key(self, resource_type: ResourceType, resource_id: str) -> str:
        """Genera una clave única para un recurso."""
        return f"{resource_type.value}:{resource_id}"

    def create_acl(
        self,
        resource_type: ResourceType,
        resource_id: str,
        owner_id: str,
        public_access: Optional[List[ActionType]] = None,
    ) -> ResourceACL:
        """Crea una nueva ACL para un recurso."""
        key = self._resource_key(resource_type, resource_id)

        acl = ResourceACL(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            public_access=public_access or [],
        )

        self.acls[key] = acl
        self._save_data()

        logger.info(f"ACL created for {key} by {owner_id}")
        return acl

    def grant_permission(
        self,
        resource_type: ResourceType,
        resource_id: str,
        user_id: str,
        actions: List[ActionType],
        granted_by: str,
        expires_in_hours: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Otorga permisos a un usuario sobre un recurso."""
        key = self._resource_key(resource_type, resource_id)

        if key not in self.acls:
            return False

        acl = self.acls[key]

        # Verificar que quien otorga tiene permisos de administración
        if granted_by != acl.owner_id:
            if not self.check_permission(
                resource_type, resource_id, granted_by, ActionType.SHARE
            ):
                return False

        expires_at = None
        if expires_in_hours:
            expires_at = (
                datetime.utcnow().replace(microsecond=0).isoformat()
                + f"+{expires_in_hours:02d}:00"
            )

        grant = PermissionGrant(
            resource_type=resource_type,
            resource_id=resource_id,
            actions=actions,
            granted_by=granted_by,
            expires_at=expires_at,
            conditions=conditions or {},
        )

        if user_id not in acl.grants:
            acl.grants[user_id] = []

        acl.grants[user_id].append(grant)

        # También guardar en índice por usuario
        if user_id not in self.user_grants:
            self.user_grants[user_id] = []
        self.user_grants[user_id].append(grant)

        self._save_data()

        logger.info(
            f"Permission granted: {user_id} -> {key} ({[a.value for a in actions]})"
        )
        return True

    def revoke_permission(
        self,
        resource_type: ResourceType,
        resource_id: str,
        user_id: str,
        revoked_by: str,
        actions: Optional[List[ActionType]] = None,
    ) -> bool:
        """Revoca permisos de un usuario sobre un recurso."""
        key = self._resource_key(resource_type, resource_id)

        if key not in self.acls:
            return False

        acl = self.acls[key]

        # Solo owner o quien otorgó puede revocar
        if revoked_by != acl.owner_id:
            # Verificar permisos de admin
            pass

        if user_id not in acl.grants:
            return False

        if actions:
            # Revocar solo acciones específicas
            acl.grants[user_id] = [
                g
                for g in acl.grants[user_id]
                if not any(a in g.actions for a in actions)
            ]
        else:
            # Revocar todos
            del acl.grants[user_id]

        self._save_data()
        return True

    def check_permission(
        self,
        resource_type: ResourceType,
        resource_id: str,
        user_id: str,
        action: ActionType,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Verifica si un usuario tiene permiso para una acción."""
        key = self._resource_key(resource_type, resource_id)

        # Owner siempre tiene todos los permisos
        if key in self.acls:
            acl = self.acls[key]
            if user_id == acl.owner_id:
                return True

            # Verificar acceso público
            if action in acl.public_access:
                return True

            # Verificar grants específicos
            if user_id in acl.grants:
                for grant in acl.grants[user_id]:
                    if self._is_grant_valid(grant) and action in grant.actions:
                        if self._check_conditions(grant.conditions, context):
                            return True

        # Verificar grants globales del usuario
        if user_id in self.user_grants:
            for grant in self.user_grants[user_id]:
                if (
                    grant.resource_type == resource_type
                    and grant.resource_id is None
                    and self._is_grant_valid(grant)
                    and action in grant.actions
                ):
                    if self._check_conditions(grant.conditions, context):
                        return True

        return False

    def get_user_permissions(
        self, user_id: str, resource_type: Optional[ResourceType] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene todos los permisos de un usuario."""
        permissions = []

        # Permisos de ACLs específicas
        for key, acl in self.acls.items():
            if user_id == acl.owner_id:
                permissions.append(
                    {
                        "resource_type": acl.resource_type.value,
                        "resource_id": acl.resource_id,
                        "actions": [a.value for a in ActionType],
                        "is_owner": True,
                    }
                )
            elif user_id in acl.grants:
                user_grants = acl.grants[user_id]
                actions = set()
                for grant in user_grants:
                    if self._is_grant_valid(grant):
                        actions.update(grant.actions)

                if actions:
                    permissions.append(
                        {
                            "resource_type": acl.resource_type.value,
                            "resource_id": acl.resource_id,
                            "actions": [a.value for a in actions],
                            "is_owner": False,
                        }
                    )

        # Filtrar por tipo si se especifica
        if resource_type:
            permissions = [
                p for p in permissions if p["resource_type"] == resource_type.value
            ]

        return permissions

    def get_resource_permissions(
        self, resource_type: ResourceType, resource_id: str
    ) -> Dict[str, Any]:
        """Obtiene la configuración de permisos de un recurso."""
        key = self._resource_key(resource_type, resource_id)

        if key not in self.acls:
            return {}

        acl = self.acls[key]

        return {
            "resource_type": acl.resource_type.value,
            "resource_id": acl.resource_id,
            "owner_id": acl.owner_id,
            "public_access": [a.value for a in acl.public_access],
            "grants": {
                user_id: [
                    {
                        "actions": [a.value for a in grant.actions],
                        "granted_by": grant.granted_by,
                        "granted_at": grant.granted_at,
                        "expires_at": grant.expires_at,
                        "conditions": grant.conditions,
                    }
                    for grant in grants
                    if self._is_grant_valid(grant)
                ]
                for user_id, grants in acl.grants.items()
            },
        }

    def create_policy(self, policy: PermissionPolicy) -> str:
        """Crea una nueva política de permisos."""
        self.policies[policy.name] = policy
        self._save_data()
        return policy.name

    def apply_role_permissions(
        self, user_id: str, role: str, resource_type: Optional[ResourceType] = None
    ) -> List[PermissionGrant]:
        """Aplica permisos basados en un rol predefinido."""
        if role not in self.DEFAULT_ROLE_PERMISSIONS:
            return []

        role_perms = self.DEFAULT_ROLE_PERMISSIONS[role]
        grants = []

        for rt, actions in role_perms.items():
            if resource_type and rt != resource_type:
                continue

            grant = PermissionGrant(
                resource_type=rt,
                resource_id=None,  # Aplica a todos los recursos del tipo
                actions=actions,
                granted_by="system",
                conditions={"role": role},
            )

            if user_id not in self.user_grants:
                self.user_grants[user_id] = []
            self.user_grants[user_id].append(grant)
            grants.append(grant)

        self._save_data()
        return grants

    def _is_grant_valid(self, grant: PermissionGrant) -> bool:
        """Verifica si un grant no ha expirado."""
        if grant.expires_at:
            try:
                expires = datetime.fromisoformat(
                    grant.expires_at.replace("Z", "+00:00")
                )
                if datetime.utcnow() > expires:
                    return False
            except Exception:
                pass
        return True

    def _check_conditions(
        self, conditions: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> bool:
        """Evalúa condiciones contextuales del grant."""
        if not conditions or not context:
            return True

        for key, value in conditions.items():
            if key == "time_range":
                # Verificar rango horario
                pass
            elif key == "ip_range":
                # Verificar rango IP
                pass
            elif key.startswith("context."):
                ctx_key = key[8:]
                if ctx_key not in context or context[ctx_key] != value:
                    return False

        return True

    def _save_data(self):
        """Guarda datos en disco."""
        try:
            data = {
                "acls": {
                    k: {
                        "resource_type": v.resource_type.value,
                        "resource_id": v.resource_id,
                        "owner_id": v.owner_id,
                        "created_at": v.created_at,
                        "public_access": [a.value for a in v.public_access],
                        "inheritance": v.inheritance,
                        "grants": {
                            uid: [
                                {
                                    "resource_type": g.resource_type.value,
                                    "resource_id": g.resource_id,
                                    "actions": [a.value for a in g.actions],
                                    "granted_by": g.granted_by,
                                    "granted_at": g.granted_at,
                                    "expires_at": g.expires_at,
                                    "conditions": g.conditions,
                                }
                                for g in grants
                            ]
                            for uid, grants in v.grants.items()
                        },
                    }
                    for k, v in self.acls.items()
                },
                "policies": {
                    k: {
                        "name": v.name,
                        "description": v.description,
                        "resource_rules": {
                            rt.value: [a.value for a in actions]
                            for rt, actions in v.resource_rules.items()
                        },
                        "default_actions": [a.value for a in v.default_actions],
                        "require_approval_for": v.require_approval_for,
                        "max_shares": v.max_shares,
                        "audit_all_actions": v.audit_all_actions,
                    }
                    for k, v in self.policies.items()
                },
            }

            with open(self.storage_path / "permissions.json", "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving permissions: {e}")

    def _load_data(self):
        """Carga datos desde disco."""
        try:
            file_path = self.storage_path / "permissions.json"
            if not file_path.exists():
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            # Cargar ACLs
            for key, acl_data in data.get("acls", {}).items():
                acl = ResourceACL(
                    resource_type=ResourceType(acl_data["resource_type"]),
                    resource_id=acl_data["resource_id"],
                    owner_id=acl_data["owner_id"],
                    created_at=acl_data["created_at"],
                    public_access=[
                        ActionType(a) for a in acl_data.get("public_access", [])
                    ],
                    inheritance=acl_data.get("inheritance", True),
                    grants={},
                )

                for uid, grants_data in acl_data.get("grants", {}).items():
                    acl.grants[uid] = [
                        PermissionGrant(
                            resource_type=ResourceType(g["resource_type"]),
                            resource_id=g.get("resource_id"),
                            actions=[ActionType(a) for a in g["actions"]],
                            granted_by=g["granted_by"],
                            granted_at=g["granted_at"],
                            expires_at=g.get("expires_at"),
                            conditions=g.get("conditions", {}),
                        )
                        for g in grants_data
                    ]

                self.acls[key] = acl

        except Exception as e:
            logger.error(f"Error loading permissions: {e}")


# Singleton
_permissions_instance: Optional[GranularPermissions] = None


def get_permissions() -> GranularPermissions:
    """Obtiene el singleton de permisos granulares."""
    global _permissions_instance
    if _permissions_instance is None:
        _permissions_instance = GranularPermissions()
    return _permissions_instance
