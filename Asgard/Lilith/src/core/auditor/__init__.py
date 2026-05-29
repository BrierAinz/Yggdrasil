"""Auditoría de decisiones (Misión 3.4 E.3 + v2 rotación por fecha, Lock, append_decision)."""
from .decision_auditor import (
    append_decision,
    get_audit_events,
    get_audit_file_path,
    log_plan_decision,
)

__all__ = [
    "append_decision",
    "get_audit_events",
    "get_audit_file_path",
    "log_plan_decision",
]
