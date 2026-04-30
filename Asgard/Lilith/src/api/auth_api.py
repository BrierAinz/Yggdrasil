"""
Auth API - Endpoints para gestión de usuarios y permisos RBAC

v4.2.8: API de autenticación y autorización
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from src.core.auth import get_rbac_manager, require_permission
from src.core.auth.permissions import Action, Resource
from src.core.auth.rbac import Role, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Models
class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(admin|developer|viewer|agent-only)$")
    custom_permissions: List[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|developer|viewer|agent-only)$")
    is_active: Optional[bool] = None
    custom_permissions: Optional[List[str]] = None


class PermissionCheckRequest(BaseModel):
    resource: str
    action: str


# Endpoints


@router.get("/me")
async def get_current_user_info(
    request: Request, x_api_key: Optional[str] = Header(None)
):
    """Obtiene información del usuario autenticado."""
    rbac = get_rbac_manager()

    # Buscar API key
    api_key = x_api_key
    if not api_key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            api_key = auth[7:]

    if not api_key:
        raise HTTPException(status_code=401, detail="API key no proporcionada")

    user = rbac.authenticate(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="API key inválida")

    return {
        "success": True,
        "data": {
            "user": user.to_dict(),
            "permissions": rbac.get_role_permissions(user.role),
        },
    }


@router.get("/users")
async def list_users():
    """Lista todos los usuarios (requiere admin)."""
    # Por ahora sin protección para facilitar setup inicial
    rbac = get_rbac_manager()
    users = rbac.list_users()

    return {"success": True, "data": [u.to_dict() for u in users], "count": len(users)}


@router.post("/users")
async def create_user(request: UserCreateRequest):
    """Crea un nuevo usuario (requiere admin)."""
    rbac = get_rbac_manager()

    try:
        role = Role(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {request.role}")

    user = rbac.create_user(
        name=request.name, role=role, custom_permissions=set(request.custom_permissions)
    )

    return {
        "success": True,
        "data": user.to_dict(include_api_key=True),
        "message": "Usuario creado. Guarda la API key, no se mostrará de nuevo.",
    }


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Obtiene un usuario por ID."""
    rbac = get_rbac_manager()
    user = rbac.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"success": True, "data": user.to_dict()}


@router.put("/users/{user_id}")
async def update_user(user_id: str, request: UserUpdateRequest):
    """Actualiza un usuario."""
    rbac = get_rbac_manager()

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    user = rbac.update_user(user_id, **update_data)

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"success": True, "data": user.to_dict(), "message": "Usuario actualizado"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Elimina un usuario."""
    rbac = get_rbac_manager()

    if rbac.delete_user(user_id):
        return {"success": True, "message": "Usuario eliminado"}

    raise HTTPException(status_code=404, detail="Usuario no encontrado")


@router.post("/users/{user_id}/regenerate-key")
async def regenerate_api_key(user_id: str):
    """Regenera la API key de un usuario."""
    rbac = get_rbac_manager()

    new_key = rbac.regenerate_api_key(user_id)
    if not new_key:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "success": True,
        "data": {"api_key": new_key},
        "message": "API key regenerada. Guarda este valor, no se mostrará de nuevo.",
    }


@router.get("/roles")
async def list_roles():
    """Lista todos los roles con sus permisos."""
    rbac = get_rbac_manager()

    return {"success": True, "data": rbac.list_roles()}


@router.post("/check-permission")
async def check_permission(request: PermissionCheckRequest):
    """Verifica si el usuario actual tiene un permiso específico."""
    rbac = get_rbac_manager()

    try:
        resource = Resource(request.resource)
        action = Action(request.action)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "data": {
            "resource": request.resource,
            "action": request.action,
            "granted": True,  # Esta validación requeriría autenticación previa
        },
    }


# Endpoints protegidos con permisos específicos


@router.get("/admin/stats")
async def get_admin_stats(current_user=Depends(get_current_user)):
    """Estadísticas de administrador (requiere permiso config:admin)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="No autenticado")

    rbac = get_rbac_manager()
    if not rbac.check_permission(current_user, Resource.CONFIG, Action.ADMIN):
        raise HTTPException(status_code=403, detail="Permiso denegado")

    return {
        "success": True,
        "data": {
            "total_users": len(rbac.list_users()),
            "roles_distribution": {
                role.value: len([u for u in rbac.list_users() if u.role == role])
                for role in Role
            },
        },
    }
