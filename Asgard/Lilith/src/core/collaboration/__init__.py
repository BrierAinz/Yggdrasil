"""
Collaboration Module - Sistema de colaboración multi-usuario

v5.0-Fase4A: Sesiones compartidas, permisos granulares y comentarios.
"""

from .comments import (
    Comment,
    CommentPriority,
    CommentReaction,
    CommentsManager,
    CommentStatus,
    CommentThread,
    get_comments_manager,
)
from .permissions_granular import (
    ActionType,
    GranularPermissions,
    PermissionGrant,
    PermissionPolicy,
    ResourceACL,
    ResourceType,
    get_permissions,
)
from .session_manager import (
    SessionManager,
    SessionParticipant,
    SessionStatus,
    SharedSession,
    UserPresence,
    UserRole,
    get_session_manager,
)

__all__ = [
    # Session Manager
    "SessionManager",
    "SharedSession",
    "SessionParticipant",
    "UserPresence",
    "UserRole",
    "SessionStatus",
    "get_session_manager",
    # Permissions
    "GranularPermissions",
    "PermissionGrant",
    "ResourceACL",
    "ResourceType",
    "ActionType",
    "PermissionPolicy",
    "get_permissions",
    # Comments
    "CommentsManager",
    "Comment",
    "CommentThread",
    "CommentStatus",
    "CommentPriority",
    "CommentReaction",
    "get_comments_manager",
]
