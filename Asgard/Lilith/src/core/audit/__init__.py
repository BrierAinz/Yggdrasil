"""
Audit Trail - Sistema de auditoría completo

v4.2.8: Registro inmutable de todas las acciones críticas del sistema.
"""
from .audit_logger import AuditLogger, get_auditor
from .events import AuditEvent, EventType
from .storage import AuditStorage

__all__ = ["AuditLogger", "get_auditor", "AuditEvent", "EventType", "AuditStorage"]
