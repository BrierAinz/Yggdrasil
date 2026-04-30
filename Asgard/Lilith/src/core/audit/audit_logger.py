"""
Audit Logger - Logger principal de auditoría

v4.2.8: Sistema de logging inmutable con integración al sistema.
"""
import json
import logging
import secrets
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .events import AuditEvent, EventCategory, EventType
from .storage import AuditStorage, StorageConfig

logger = logging.getLogger("lilith.audit")

# Contexto para request_id y actor actual
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_actor: ContextVar[str] = ContextVar("actor", default="system")
_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


class AuditLogger:
    """
    Logger de auditoría principal.

    Features:
    - Logging append-only inmutable
    - Contexto automático (request_id, actor, session)
    - Múltiples niveles de severidad
    - Integración con storage para persistencia
    """

    def __init__(self, storage: Optional[AuditStorage] = None):
        if storage is None:
            # Configuración por defecto
            config = StorageConfig(
                base_path=Path(__file__).resolve().parents[3] / "Config" / "audit"
            )
            storage = AuditStorage(config)

        self.storage = storage
        self._enabled = True

    def set_context(
        self,
        request_id: Optional[str] = None,
        actor: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Establece el contexto actual para logging."""
        if request_id:
            _request_id.set(request_id)
        if actor:
            _actor.set(actor)
        if session_id:
            _session_id.set(session_id)

    def clear_context(self):
        """Limpia el contexto actual."""
        _request_id.set(None)
        _actor.set("system")
        _session_id.set(None)

    def _get_request_id(self) -> str:
        """Obtiene o genera un request_id."""
        req_id = _request_id.get()
        if req_id is None:
            req_id = secrets.token_hex(8)
            _request_id.set(req_id)
        return req_id

    def log(
        self,
        event_type: EventType,
        resource: str,
        action: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Registra un evento de auditoría.

        Args:
            event_type: Tipo de evento
            resource: Recurso afectado
            action: Acción realizada
            status: Estado (success, failure, denied)
            details: Detalles adicionales
            ip_address: IP del cliente
            metadata: Metadata extra

        Returns:
            True si se registró exitosamente
        """
        if not self._enabled:
            return True

        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            actor=_actor.get(),
            resource=resource,
            action=action,
            status=status,
            details=details or {},
            ip_address=ip_address,
            request_id=self._get_request_id(),
            session_id=_session_id.get(),
            metadata=metadata or {},
        )

        # Log a consola también
        level = logging.INFO if status == "success" else logging.WARNING
        logger.log(level, f"[{event_type.value}] {actor} {action} {resource}: {status}")

        return self.storage.append(event)

    # Métodos de conveniencia

    def log_tool_execution(
        self,
        tool_name: str,
        params: Dict[str, Any],
        success: bool = True,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Log de ejecución de herramienta."""
        details = {
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "error": error,
        }
        event_type = EventType.TOOL_SUCCESS if success else EventType.TOOL_FAILURE
        return self.log(
            event_type=event_type,
            resource=f"tool:{tool_name}",
            action="execute",
            status="success" if success else "failure",
            details=details,
        )

    def log_file_access(
        self, file_path: str, action: str, success: bool = True  # read, write, delete
    ) -> bool:
        """Log de acceso a archivo."""
        event_type = (
            EventType.FILE_ACCESS
            if action == "read"
            else EventType.FILE_WRITE
            if action == "write"
            else EventType.FILE_DELETE
        )
        return self.log(
            event_type=event_type,
            resource=f"file:{file_path}",
            action=action,
            status="success" if success else "failure",
        )

    def log_auth(
        self,
        action: str,  # login, logout, failure
        user_id: str,
        success: bool = True,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Log de autenticación."""
        event_type = (
            EventType.AUTH_LOGIN
            if action == "login"
            else EventType.AUTH_LOGOUT
            if action == "logout"
            else EventType.AUTH_FAILURE
        )
        return self.log(
            event_type=event_type,
            resource=f"user:{user_id}",
            action=action,
            status="success" if success else "failure",
            ip_address=ip_address,
        )

    def log_permission(
        self, user_id: str, resource: str, action: str, granted: bool
    ) -> bool:
        """Log de verificación de permisos."""
        event_type = (
            EventType.PERMISSION_GRANTED if granted else EventType.PERMISSION_DENIED
        )
        return self.log(
            event_type=event_type,
            resource=resource,
            action=action,
            status="granted" if granted else "denied",
            details={"user_id": user_id},
        )

    def log_workflow(
        self,
        workflow_id: str,
        action: str,  # created, updated, deleted, executed
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log de operaciones de workflow."""
        event_map = {
            "created": EventType.WORKFLOW_CREATED,
            "updated": EventType.WORKFLOW_UPDATED,
            "deleted": EventType.WORKFLOW_DELETED,
            "executed": EventType.WORKFLOW_EXECUTION,
        }
        event_type = event_map.get(action, EventType.WORKFLOW_EXECUTION)
        return self.log(
            event_type=event_type,
            resource=f"workflow:{workflow_id}",
            action=action,
            details=details or {},
        )

    def log_config_change(
        self, config_key: str, old_value: Any, new_value: Any
    ) -> bool:
        """Log de cambio de configuración."""
        return self.log(
            event_type=EventType.CONFIG_CHANGE,
            resource=f"config:{config_key}",
            action="update",
            details={"old_value": old_value, "new_value": new_value},
        )

    def log_system(self, action: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Log de eventos de sistema."""
        event_type = (
            EventType.SYSTEM_STARTUP
            if action == "startup"
            else EventType.SYSTEM_SHUTDOWN
            if action == "shutdown"
            else EventType.ERROR
            if action == "error"
            else EventType.WARNING
        )
        return self.log(
            event_type=event_type,
            resource="system",
            action=action,
            details=details or {},
        )

    def log_cache(self, action: str, key: str, namespace: str = "default") -> bool:
        """Log de operaciones de caché."""
        event_type = (
            EventType.CACHE_HIT
            if action == "hit"
            else EventType.CACHE_MISS
            if action == "miss"
            else EventType.CACHE_INVALIDATE
        )
        return self.log(
            event_type=event_type, resource=f"cache:{namespace}:{key}", action=action
        )

    # Consultas

    def query(self, **filters) -> List[AuditEvent]:
        """Consulta eventos de auditoría."""
        return self.storage.query(**filters)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema de auditoría."""
        return self.storage.get_stats()

    def export_csv(self, output_path: Path, **filters) -> int:
        """Exporta eventos a CSV."""
        return self.storage.export_to_csv(output_path, **filters)

    def export_json(self, output_path: Path, **filters) -> int:
        """Exporta eventos a JSON."""
        return self.storage.export_to_json(output_path, **filters)

    def compress_old(self):
        """Comprime archivos antiguos."""
        self.storage.compress_old_files()

    def cleanup_old(self):
        """Limpia archivos antiguos según retención."""
        self.storage.cleanup_old_files()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value


# Singleton global
_auditor: Optional[AuditLogger] = None


def get_auditor() -> AuditLogger:
    """Obtiene la instancia singleton del auditor."""
    global _auditor
    if _auditor is None:
        _auditor = AuditLogger()
    return _auditor


def initialize_auditor(storage: Optional[AuditStorage] = None):
    """Inicializa el auditor con configuración personalizada."""
    global _auditor
    _auditor = AuditLogger(storage)


def set_audit_context(
    request_id: Optional[str] = None,
    actor: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Establece contexto para el hilo/request actual."""
    auditor = get_auditor()
    auditor.set_context(request_id, actor, session_id)


def clear_audit_context():
    """Limpia el contexto de auditoría actual."""
    auditor = get_auditor()
    auditor.clear_context()
