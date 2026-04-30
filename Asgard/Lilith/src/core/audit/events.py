"""
Audit Events - Definición de eventos auditables

v4.2.8: Tipos de eventos y estructura de datos
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Tipos de eventos auditables."""

    # Tool execution
    TOOL_EXECUTION = "tool_execution"
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILURE = "tool_failure"

    # File operations
    FILE_ACCESS = "file_access"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"

    # Agent operations
    AGENT_DELEGATION = "agent_delegation"
    AGENT_RESPONSE = "agent_response"

    # Configuration changes
    CONFIG_CHANGE = "config_change"
    CONFIG_READ = "config_read"

    # Authentication
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILURE = "auth_failure"

    # Permissions
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_GRANTED = "permission_granted"

    # Workflow operations
    WORKFLOW_EXECUTION = "workflow_execution"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"

    # Cache operations
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_INVALIDATE = "cache_invalidate"

    # System
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class AuditEvent:
    """Evento de auditoría individual."""

    timestamp: datetime
    event_type: EventType
    actor: str  # user_id, agent_id, o "system"
    resource: str  # qué recurso se afectó
    action: str  # qué acción se realizó
    status: str  # "success", "failure", "denied"
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Crea un evento desde un diccionario."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=EventType(data["event_type"]),
            actor=data["actor"],
            resource=data["resource"],
            action=data["action"],
            status=data["status"],
            details=data.get("details", {}),
            ip_address=data.get("ip_address"),
            request_id=data.get("request_id"),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
        )

    def to_jsonl(self) -> str:
        """Convierte el evento a formato JSONL (una línea)."""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


class EventCategory:
    """Categorías de eventos para agrupamiento."""

    SECURITY = [
        EventType.AUTH_LOGIN,
        EventType.AUTH_LOGOUT,
        EventType.AUTH_FAILURE,
        EventType.PERMISSION_DENIED,
        EventType.PERMISSION_GRANTED,
    ]
    OPERATIONAL = [
        EventType.TOOL_EXECUTION,
        EventType.AGENT_DELEGATION,
        EventType.WORKFLOW_EXECUTION,
    ]
    DATA = [
        EventType.FILE_ACCESS,
        EventType.FILE_WRITE,
        EventType.FILE_DELETE,
        EventType.CONFIG_CHANGE,
    ]
    SYSTEM = [
        EventType.SYSTEM_STARTUP,
        EventType.SYSTEM_SHUTDOWN,
        EventType.ERROR,
        EventType.WARNING,
    ]

    @classmethod
    def get_category(cls, event_type: EventType) -> str:
        """Obtiene la categoría de un tipo de evento."""
        if event_type in cls.SECURITY:
            return "security"
        elif event_type in cls.OPERATIONAL:
            return "operational"
        elif event_type in cls.DATA:
            return "data"
        elif event_type in cls.SYSTEM:
            return "system"
        return "other"
