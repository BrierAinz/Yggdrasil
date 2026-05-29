"""
Decision Auditor - Sistema de auditoría de decisiones con rotación por fecha

Registra todas las decisiones (Planner, Clasificador, Executor) en archivos
JSONL por día para trazabilidad y debugging.

Features:
- Rotación por fecha (decision_audit_YYYY-MM-DD.jsonl)
- threading.Lock para escritura concurrente
- Sanitización de payloads (anti-bloat)
- Retención configurable (días)
- Reason heurístico
"""

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Límites de sanitización
MAX_PAYLOAD_STRING_CHARS = 2000
MAX_PAYLOAD_DEPTH = 6
MAX_PAYLOAD_LIST_LEN = 50

# Lock global para escritura concurrente
_WRITE_LOCK = threading.Lock()

# Estado de poda (para ejecutarla solo 1 vez por día)
_LAST_PRUNE_DATE: Optional[str] = None


class DecisionAuditor:
    """
    Auditor de decisiones con rotación por fecha

    Métodos:
    - append_decision: Escribir decisión
    - get_audit_for_date: Leer auditoría de un día
    """

    def __init__(self, audit_dir: Path, retention_days: int = 30):
        """
        Args:
            audit_dir: Directorio para archivos de auditoría
            retention_days: Días de retención (default: 30)
        """
        self.audit_dir = audit_dir
        self.retention_days = retention_days

        # Crear directorio si no existe
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def append_decision(
        self,
        decision_type: str,
        decision_source: str,
        payload: Dict[str, Any],
        reason: Optional[str] = None,
        confidence: Optional[float] = None,
    ):
        """
        Registrar una decisión

        Args:
            decision_type: Tipo (ej: 'plan_generated', 'step_executed')
            decision_source: Fuente (ej: 'planner', 'executor')
            payload: Datos de la decisión
            reason: Razón heurística (opcional)
            confidence: Nivel de confianza 0.0-1.0 (opcional)
        """
        with _WRITE_LOCK:
            # Construir evento
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "decision_type": decision_type,
                "decision_source": decision_source,
                "payload": self._sanitize_payload(payload),
                "confidence": confidence,
            }

            if reason:
                event["reason"] = reason[:500]  # Truncar reason a 500 chars

            # Archivo del día (UTC)
            file_path = self._audit_path_for_today()

            # Escribir línea
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")

                logger.debug(f"Logged decision: {decision_type} from {decision_source}")

            except Exception as e:
                logger.error(f"Failed to write audit: {e}")

            # Poda de archivos viejos (1 vez por día)
            self._maybe_prune_once_per_day()

    def _audit_path_for_today(self) -> Path:
        """Obtener ruta del archivo de auditoría para hoy (UTC)"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.audit_dir / f"decision_audit_{today}.jsonl"

    def _sanitize_payload(self, payload: Any, depth: int = 0) -> Any:
        """
        Sanitizar payload para evitar bloat

        Reglas:
        - Truncar strings a MAX_PAYLOAD_STRING_CHARS
        - Limitar profundidad a MAX_PAYLOAD_DEPTH
        - Limitar listas a MAX_PAYLOAD_LIST_LEN
        """
        if depth >= MAX_PAYLOAD_DEPTH:
            return "<max_depth_reached>"

        if isinstance(payload, str):
            if len(payload) > MAX_PAYLOAD_STRING_CHARS:
                return (
                    payload[:MAX_PAYLOAD_STRING_CHARS]
                    + f"...<truncated {len(payload) - MAX_PAYLOAD_STRING_CHARS} chars>"
                )
            return payload

        elif isinstance(payload, (int, float, bool, type(None))):
            return payload

        elif isinstance(payload, dict):
            return {k: self._sanitize_payload(v, depth + 1) for k, v in payload.items()}

        elif isinstance(payload, (list, tuple)):
            if len(payload) > MAX_PAYLOAD_LIST_LEN:
                sanitized = [
                    self._sanitize_payload(item, depth + 1)
                    for item in payload[:MAX_PAYLOAD_LIST_LEN]
                ]
                sanitized.append(
                    f"<truncated {len(payload) - MAX_PAYLOAD_LIST_LEN} more>"
                )
                return sanitized
            else:
                return [self._sanitize_payload(item, depth + 1) for item in payload]

        else:
            return str(payload)[:MAX_PAYLOAD_STRING_CHARS]

    def _maybe_prune_once_per_day(self):
        """
        Ejecutar poda de archivos viejos 1 vez por día

        Borra archivos con fecha < hoy - retention_days
        """
        global _LAST_PRUNE_DATE

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if _LAST_PRUNE_DATE == today:
            return  # Ya se ejecutó hoy

        _LAST_PRUNE_DATE = today

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.retention_days
            )

            # Listar archivos decision_audit_*.jsonl
            pattern = "decision_audit_*.jsonl"
            files = list(self.audit_dir.glob(pattern))

            deleted_count = 0

            for file_path in files:
                # Extraer fecha del nombre
                try:
                    date_str = file_path.stem.replace("decision_audit_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    # Comparar con cutoff
                    if file_date.replace(tzinfo=timezone.utc) < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old audit file: {file_path.name}")

                except (ValueError, OSError, FileNotFoundError) as e:
                    logger.warning(f"Error processing audit file {file_path}: {e}")

            if deleted_count > 0:
                logger.info(f"Pruned {deleted_count} old audit files")

        except Exception as e:
            logger.error(f"Failed to prune audit files: {e}")

    def get_audit_for_date(
        self, date: str, decision_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Leer auditoría de un día específico

        Args:
            date: Fecha en formato YYYY-MM-DD (UTC)
            decision_type: Filtrar por tipo (opcional)

        Returns:
            Lista de eventos
        """
        file_path = self.audit_dir / f"decision_audit_{date}.jsonl"

        if not file_path.exists():
            return []

        events = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        event = json.loads(line)

                        # Filtrar por tipo si se especifica
                        if (
                            decision_type
                            and event.get("decision_type") != decision_type
                        ):
                            continue

                        events.append(event)

        except Exception as e:
            logger.error(f"Failed to read audit file {file_path}: {e}")

        return events

    def get_recent_decisions(
        self, limit: int = 50, decision_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener decisiones recientes (últimos N días)

        Args:
            limit: Máximo de eventos a devolver
            decision_type: Filtrar por tipo (opcional)

        Returns:
            Lista de eventos (más recientes primero)
        """
        events = []

        # Buscar en los últimos 7 días
        for i in range(7):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            day_events = self.get_audit_for_date(date, decision_type=decision_type)
            events.extend(day_events)

            if len(events) >= limit:
                break

        # Ordenar por timestamp descendente
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        return events[:limit]


# Singleton global
_decision_auditor: Optional[DecisionAuditor] = None


def initialize_auditor(audit_dir: Path, retention_days: int = 30):
    """Inicializar el auditor global"""
    global _decision_auditor
    _decision_auditor = DecisionAuditor(
        audit_dir=audit_dir, retention_days=retention_days
    )


def get_decision_auditor() -> DecisionAuditor:
    """Obtener instancia singleton del auditor"""
    if _decision_auditor is None:
        raise ValueError("Auditor not initialized, call initialize_auditor() first")
    return _decision_auditor


def log_decision(
    decision_type: str,
    decision_source: str,
    payload: Dict[str, Any],
    reason: Optional[str] = None,
    confidence: Optional[float] = None,
):
    """
    Función de conveniencia para log de decisiones

    Args:
        decision_type: Tipo de decisión
        decision_source: Fuente (planner, executor, etc.)
        payload: Datos
        reason: Razón heurística (opcional)
        confidence: Confianza 0.0-1.0 (opcional)
    """
    auditor = get_decision_auditor()
    auditor.append_decision(
        decision_type=decision_type,
        decision_source=decision_source,
        payload=payload,
        reason=reason,
        confidence=confidence,
    )
