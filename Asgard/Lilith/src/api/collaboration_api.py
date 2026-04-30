"""
Collaboration API - Endpoints REST para colaboración multi-usuario

v5.0-Fase4A: Sesiones, permisos y comentarios.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from src.core.collaboration import (
    ActionType,
    CommentPriority,
    CommentStatus,
    ResourceType,
    SessionStatus,
    UserRole,
    get_comments_manager,
    get_permissions,
    get_session_manager,
)

logger = logging.getLogger("lilith.api.collaboration")
router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


# ============= Schemas =============


class CreateSessionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    expires_in_hours: Optional[int] = None


class AddParticipantRequest(BaseModel):
    user_id: str
    role: str = "viewer"
    permissions: Optional[List[str]] = None


class UpdatePresenceRequest(BaseModel):
    status: Optional[str] = None
    current_view: Optional[str] = None
    cursor_position: Optional[dict] = None


class CreateThreadRequest(BaseModel):
    resource_type: str
    resource_id: str
    content: str
    context: Optional[dict] = None
    priority: str = "medium"


class AddCommentRequest(BaseModel):
    content: str
    parent_id: Optional[str] = None


class UpdateCommentRequest(BaseModel):
    content: str


class AddReactionRequest(BaseModel):
    emoji: str


class GrantPermissionRequest(BaseModel):
    user_id: str
    actions: List[str]
    expires_in_hours: Optional[int] = None


# ============= Session Endpoints =============


@router.post("/sessions", response_model=dict)
async def create_session(request: CreateSessionRequest, user_id: str = "current_user"):
    """Crea una nueva sesión colaborativa."""
    manager = get_session_manager()

    role = UserRole.OWNER
    session = await manager.create_session(
        name=request.name,
        owner_id=user_id,
        description=request.description,
        expires_in_hours=request.expires_in_hours,
    )

    return {
        "id": session.id,
        "name": session.name,
        "owner_id": session.owner_id,
        "status": session.status.value,
        "created_at": session.created_at,
        "expires_at": session.expires_at,
    }


@router.get("/sessions")
async def list_sessions(user_id: str = "current_user"):
    """Lista las sesiones del usuario."""
    manager = get_session_manager()
    sessions = manager.get_user_sessions(user_id)

    return {
        "sessions": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "status": s.status.value,
                "participant_count": len(s.participants),
                "created_at": s.created_at,
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = "current_user"):
    """Obtiene detalles de una sesión."""
    manager = get_session_manager()

    if session_id not in manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = manager.sessions[session_id]

    if user_id not in session.participants:
        raise HTTPException(status_code=403, detail="Not a participant")

    return {
        "id": session.id,
        "name": session.name,
        "description": session.description,
        "owner_id": session.owner_id,
        "status": session.status.value,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "expires_at": session.expires_at,
        "participants": [
            {"user_id": p.user_id, "role": p.role.value, "joined_at": p.joined_at}
            for p in session.participants.values()
        ],
        "presence": [
            {
                "user_id": p.user_id,
                "username": p.username,
                "status": p.status,
                "current_view": p.current_view,
                "last_activity": p.last_activity,
            }
            for p in session.presence.values()
        ],
    }


@router.post("/sessions/{session_id}/participants")
async def add_participant(
    session_id: str, request: AddParticipantRequest, user_id: str = "current_user"
):
    """Añade un participante a la sesión."""
    manager = get_session_manager()

    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    success = await manager.add_participant(
        session_id=session_id,
        user_id=request.user_id,
        role=role,
        added_by=user_id,
        permissions=request.permissions,
    )

    if not success:
        raise HTTPException(status_code=403, detail="Cannot add participant")

    return {"success": True}


@router.delete("/sessions/{session_id}/participants/{participant_id}")
async def remove_participant(
    session_id: str, participant_id: str, user_id: str = "current_user"
):
    """Elimina un participante de la sesión."""
    manager = get_session_manager()

    success = await manager.remove_participant(
        session_id=session_id, user_id=participant_id, removed_by=user_id
    )

    if not success:
        raise HTTPException(status_code=403, detail="Cannot remove participant")

    return {"success": True}


@router.post("/sessions/{session_id}/presence")
async def update_presence(
    session_id: str, request: UpdatePresenceRequest, user_id: str = "current_user"
):
    """Actualiza el estado de presencia del usuario."""
    manager = get_session_manager()

    success = await manager.update_presence(
        session_id=session_id,
        user_id=user_id,
        status=request.status,
        current_view=request.current_view,
        cursor_position=request.cursor_position,
    )

    if not success:
        raise HTTPException(
            status_code=404, detail="Session not found or not a participant"
        )

    return {"success": True}


# ============= WebSocket =============


@router.websocket("/sessions/{session_id}/ws")
async def session_websocket(
    websocket: WebSocket, session_id: str, user_id: str = "current_user"
):
    """WebSocket para actualizaciones en tiempo real de la sesión."""
    manager = get_session_manager()

    await websocket.accept()

    success = await manager.join_session_websocket(session_id, user_id, websocket)
    if not success:
        await websocket.close(code=4000, reason="Not a session participant")
        return

    try:
        while True:
            message = await websocket.receive_json()

            # Procesar mensajes del cliente
            msg_type = message.get("type")

            if msg_type == "presence_update":
                await manager.update_presence(
                    session_id=session_id,
                    user_id=user_id,
                    status=message.get("status"),
                    current_view=message.get("current_view"),
                    cursor_position=message.get("cursor_position"),
                )

            elif msg_type == "broadcast":
                # Broadcast a todos los participantes
                await manager.broadcast_to_session(
                    session_id=session_id,
                    message=message.get("data", {}),
                    exclude_user=user_id,
                )

    except WebSocketDisconnect:
        await manager.leave_session_websocket(session_id, user_id)


# ============= Comments Endpoints =============


@router.post("/comments/threads", response_model=dict)
async def create_thread(request: CreateThreadRequest, user_id: str = "current_user"):
    """Crea un nuevo hilo de comentarios."""
    manager = get_comments_manager()

    try:
        priority = CommentPriority(request.priority)
    except ValueError:
        priority = CommentPriority.MEDIUM

    thread = await manager.create_thread(
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        author_id=user_id,
        author_name=user_id,  # TODO: Lookup username
        content=request.content,
        context=request.context,
        priority=priority,
    )

    return {
        "id": thread.id,
        "resource_type": thread.resource_type,
        "resource_id": thread.resource_id,
        "status": thread.status.value,
        "created_at": thread.created_at,
    }


@router.get("/comments/threads")
async def list_threads(
    resource_type: str, resource_id: str, status: Optional[str] = None
):
    """Lista los hilos de comentarios de un recurso."""
    manager = get_comments_manager()

    thread_status = None
    if status:
        try:
            thread_status = CommentStatus(status)
        except ValueError:
            pass

    threads = manager.get_threads_for_resource(
        resource_type, resource_id, thread_status
    )

    return {
        "threads": [
            {
                "id": t.id,
                "status": t.status.value,
                "participant_count": len(t.participants),
                "comment_count": len(t.comments),
                "assigned_to": t.assigned_to,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "first_comment": {
                    "author": t.comments[0].author_name if t.comments else None,
                    "content": t.comments[0].content[:200] if t.comments else None,
                }
                if t.comments
                else None,
            }
            for t in threads
        ]
    }


@router.get("/comments/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Obtiene un hilo con todos sus comentarios."""
    manager = get_comments_manager()

    if thread_id not in manager.threads:
        raise HTTPException(status_code=404, detail="Thread not found")

    thread = manager.threads[thread_id]

    return {
        "id": thread.id,
        "resource_type": thread.resource_type,
        "resource_id": thread.resource_id,
        "context": thread.context,
        "status": thread.status.value,
        "assigned_to": thread.assigned_to,
        "participants": list(thread.participants),
        "created_at": thread.created_at,
        "updated_at": thread.updated_at,
        "resolved_at": thread.resolved_at,
        "comments": [
            {
                "id": c.id,
                "author_id": c.author_id,
                "author_name": c.author_name,
                "content": c.content,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "parent_id": c.parent_id,
                "mentions": c.mentions,
                "reactions": [
                    {"emoji": r.emoji, "user_id": r.user_id} for r in c.reactions
                ],
                "metadata": c.metadata,
            }
            for c in thread.comments
        ],
    }


@router.post("/comments/threads/{thread_id}/comments")
async def add_comment(
    thread_id: str, request: AddCommentRequest, user_id: str = "current_user"
):
    """Añade un comentario a un hilo."""
    manager = get_comments_manager()

    comment = await manager.add_comment(
        thread_id=thread_id,
        author_id=user_id,
        author_name=user_id,  # TODO: Lookup username
        content=request.content,
        parent_id=request.parent_id,
    )

    if not comment:
        raise HTTPException(status_code=404, detail="Thread not found or closed")

    return {"id": comment.id, "created_at": comment.created_at}


@router.put("/comments/{comment_id}")
async def update_comment(
    comment_id: str, request: UpdateCommentRequest, user_id: str = "current_user"
):
    """Actualiza un comentario."""
    manager = get_comments_manager()

    success = await manager.update_comment(comment_id, request.content, user_id)

    if not success:
        raise HTTPException(status_code=403, detail="Cannot update comment")

    return {"success": True}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str, user_id: str = "current_user", is_admin: bool = False
):
    """Elimina un comentario."""
    manager = get_comments_manager()

    success = await manager.delete_comment(comment_id, user_id, is_admin)

    if not success:
        raise HTTPException(status_code=403, detail="Cannot delete comment")

    return {"success": True}


@router.post("/comments/threads/{thread_id}/resolve")
async def resolve_thread(
    thread_id: str, user_id: str = "current_user", resolution_note: Optional[str] = None
):
    """Marca un hilo como resuelto."""
    manager = get_comments_manager()

    success = await manager.resolve_thread(thread_id, user_id, resolution_note)

    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")

    return {"success": True}


@router.post("/comments/threads/{thread_id}/reopen")
async def reopen_thread(thread_id: str, user_id: str = "current_user"):
    """Reabre un hilo resuelto."""
    manager = get_comments_manager()

    success = await manager.reopen_thread(thread_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")

    return {"success": True}


@router.post("/comments/{comment_id}/reactions")
async def add_reaction(
    comment_id: str, request: AddReactionRequest, user_id: str = "current_user"
):
    """Añade una reacción a un comentario."""
    manager = get_comments_manager()

    success = await manager.add_reaction(comment_id, request.emoji, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {"success": True}


@router.delete("/comments/{comment_id}/reactions/{emoji}")
async def remove_reaction(comment_id: str, emoji: str, user_id: str = "current_user"):
    """Remueve una reacción de un comentario."""
    manager = get_comments_manager()

    success = await manager.remove_reaction(comment_id, emoji, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {"success": True}


@router.get("/comments/search")
async def search_comments(
    query: str, resource_type: Optional[str] = None, author_id: Optional[str] = None
):
    """Busca comentarios."""
    manager = get_comments_manager()

    results = manager.search_comments(query, resource_type, author_id)

    return {
        "results": [
            {
                "comment_id": r["comment"].id,
                "content": r["comment"].content[:200],
                "author": r["comment"].author_name,
                "thread_id": r["thread"].id,
                "resource": r["resource"],
            }
            for r in results
        ]
    }


# ============= Permissions Endpoints =============


@router.post("/permissions/{resource_type}/{resource_id}/grant")
async def grant_permission(
    resource_type: str,
    resource_id: str,
    request: GrantPermissionRequest,
    granted_by: str = "current_user",
):
    """Otorga permisos sobre un recurso."""
    perms = get_permissions()

    try:
        rt = ResourceType(resource_type)
        actions = [ActionType(a) for a in request.actions]
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid resource type or action: {e}"
        )

    success = perms.grant_permission(
        resource_type=rt,
        resource_id=resource_id,
        user_id=request.user_id,
        actions=actions,
        granted_by=granted_by,
        expires_in_hours=request.expires_in_hours,
    )

    if not success:
        raise HTTPException(status_code=403, detail="Cannot grant permission")

    return {"success": True}


@router.get("/permissions/{resource_type}/{resource_id}")
async def get_resource_permissions(resource_type: str, resource_id: str):
    """Obtiene los permisos de un recurso."""
    perms = get_permissions()

    try:
        rt = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resource type")

    return perms.get_resource_permissions(rt, resource_id)


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str, resource_type: Optional[str] = None):
    """Obtiene los permisos de un usuario."""
    perms = get_permissions()

    rt = None
    if resource_type:
        try:
            rt = ResourceType(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resource type")

    return {"permissions": perms.get_user_permissions(user_id, rt)}
