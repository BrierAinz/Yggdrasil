"""
RBAC Module - Sistema de Control de Acceso Basado en Roles

v4.2.8: Sistema de permisos granular para Lilith
"""
from .permissions import Action, Permission, Resource
from .rbac import RBACManager, get_rbac_manager, require_permission

__all__ = [
    "Permission",
    "Resource",
    "Action",
    "RBACManager",
    "get_rbac_manager",
    "require_permission",
]
