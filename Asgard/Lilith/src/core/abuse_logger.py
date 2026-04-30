"""
Abuse Logger - Registra intentos sospechosos de usuarios públicos.
Detecta:
- Intentos de usar tools prohibidas
- Intentos de inyección de prompt
- Tasa de mensajes anormalmente alta
- Otros comportamientos sospechosos
"""
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.abuse_logger")


class ViolationType(str, Enum):
    """Tipos de violaciones."""

    FORBIDDEN_TOOL_ATTEMPT = "forbidden_tool_attempt"
    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class AbuseLogger:
    """
    Logger especializado para prevención de abuso.
    Almacena en SQLite y provee dashboard de abuso.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, base_path: Optional[Path] = None, db_name: str = "abuse_logs.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self, base_path: Optional[Path] = None, db_name: str = "abuse_logs.db"
    ):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self.db_path = self.base_path / "Data" / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # También log a archivo JSONL para fácil inspección
        self.jsonl_path = self.base_path / "Data" / "public_abuse_logs.jsonl"

        self._local_lock = threading.RLock()
        self._init_db()
        self._initialized = True

        logger.info("[AbuseLogger] Inicializado en %s", self.db_path)

    def _init_db(self) -> None:
        """Inicializa tabla de logs de abuso."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS abuse_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        user_id TEXT NOT NULL,
                        guild_id TEXT,
                        violation_type TEXT NOT NULL,
                        details TEXT,
                        severity TEXT DEFAULT 'medium',
                        resolved BOOLEAN DEFAULT FALSE
                    )
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_abuse_user_time
                    ON abuse_logs(user_id, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_abuse_type_time
                    ON abuse_logs(violation_type, timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_abuse_unresolved
                    ON abuse_logs(resolved) WHERE resolved = FALSE
                """
                )

                conn.commit()
        except Exception as e:
            logger.error("[AbuseLogger] Error inicializando DB: %s", e)

    def log(
        self,
        user_id: str,
        violation_type: ViolationType,
        details: Dict[str, Any],
        guild_id: Optional[str] = None,
        severity: str = "medium",
    ) -> bool:
        """
        Registra una violación.

        Args:
            user_id: ID del usuario
            violation_type: Tipo de violación
            details: Detalles específicos
            guild_id: ID del servidor
            severity: low, medium, high, critical

        Returns:
            True si se registró correctamente
        """
        timestamp = time.time()

        # Crear entrada
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "guild_id": guild_id,
            "violation_type": violation_type.value,
            "details": details,
            "severity": severity,
        }

        try:
            with self._local_lock:
                # Guardar en SQLite
                with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                    conn.execute(
                        """
                        INSERT INTO abuse_logs
                        (timestamp, user_id, guild_id, violation_type, details, severity)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp,
                            user_id,
                            guild_id,
                            violation_type.value,
                            json.dumps(details, ensure_ascii=False),
                            severity,
                        ),
                    )
                    conn.commit()

                # Guardar en JSONL para fácil lectura
                with open(self.jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            logger.warning(
                "[AbusePrevention] User %s | %s | Severity: %s | %s",
                user_id,
                violation_type.value,
                severity,
                json.dumps(details, ensure_ascii=False)[:200],
            )

            return True
        except Exception as e:
            logger.error("[AbuseLogger] Error guardando log: %s", e)
            return False

    def log_forbidden_tool_attempt(
        self,
        user_id: str,
        tool_name: str,
        input_data: str,
        guild_id: Optional[str] = None,
    ) -> bool:
        """Log específico para intento de usar tool prohibida."""
        return self.log(
            user_id=user_id,
            violation_type=ViolationType.FORBIDDEN_TOOL_ATTEMPT,
            details={
                "tool": tool_name,
                "input_preview": input_data[:500],
            },
            guild_id=guild_id,
            severity="high",
        )

    def log_prompt_injection(
        self,
        user_id: str,
        pattern_found: str,
        message_preview: str,
        guild_id: Optional[str] = None,
    ) -> bool:
        """Log específico para intento de inyección de prompt."""
        return self.log(
            user_id=user_id,
            violation_type=ViolationType.PROMPT_INJECTION_ATTEMPT,
            details={
                "pattern": pattern_found,
                "message_preview": message_preview[:500],
            },
            guild_id=guild_id,
            severity="high",
        )

    def log_rate_limit_violation(
        self,
        user_id: str,
        limit_type: str,
        current_usage: int,
        limit: int,
        guild_id: Optional[str] = None,
    ) -> bool:
        """Log específico para violación de rate limit."""
        return self.log(
            user_id=user_id,
            violation_type=ViolationType.RATE_LIMIT_VIOLATION,
            details={
                "limit_type": limit_type,
                "current_usage": current_usage,
                "limit": limit,
            },
            guild_id=guild_id,
            severity="medium",
        )

    def get_recent_violations(
        self,
        limit: int = 100,
        violation_type: Optional[ViolationType] = None,
        severity: Optional[str] = None,
        unresolved_only: bool = False,
    ) -> List[Dict]:
        """
        Obtiene violaciones recientes.

        Args:
            limit: Máximo de resultados
            violation_type: Filtrar por tipo
            severity: Filtrar por severidad
            unresolved_only: Solo no resueltas

        Returns:
            Lista de violaciones
        """
        try:
            query = "SELECT * FROM abuse_logs WHERE 1=1"
            params = []

            if violation_type:
                query += " AND violation_type = ?"
                params.append(violation_type.value)

            if severity:
                query += " AND severity = ?"
                params.append(severity)

            if unresolved_only:
                query += " AND resolved = FALSE"

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)

                return [
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "datetime": datetime.fromtimestamp(
                            row["timestamp"], timezone.utc
                        ).isoformat(),
                        "user_id": row["user_id"],
                        "guild_id": row["guild_id"],
                        "violation_type": row["violation_type"],
                        "details": json.loads(row["details"]) if row["details"] else {},
                        "severity": row["severity"],
                        "resolved": bool(row["resolved"]),
                    }
                    for row in cursor
                ]
        except Exception as e:
            logger.error("[AbuseLogger] Error obteniendo violaciones: %s", e)
            return []

    def get_user_violations(
        self,
        user_id: str,
        days: int = 30,
    ) -> List[Dict]:
        """Obtiene violaciones de un usuario específico."""
        cutoff = time.time() - (days * 24 * 60 * 60)

        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT * FROM abuse_logs
                    WHERE user_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    """,
                    (user_id, cutoff),
                )

                return [
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "violation_type": row["violation_type"],
                        "details": json.loads(row["details"]) if row["details"] else {},
                        "severity": row["severity"],
                    }
                    for row in cursor
                ]
        except Exception as e:
            logger.error("[AbuseLogger] Error obteniendo violaciones de usuario: %s", e)
            return []

    def get_user_risk_score(self, user_id: str) -> Dict:
        """
        Calcula un score de riesgo para un usuario.

        Returns:
            Dict con score y detalles
        """
        try:
            violations = self.get_user_violations(user_id, days=7)

            if not violations:
                return {
                    "user_id": user_id,
                    "risk_score": 0,
                    "level": "low",
                    "violations_count": 0,
                }

            # Ponderar por severidad
            severity_weights = {
                "low": 1,
                "medium": 3,
                "high": 10,
                "critical": 50,
            }

            total_score = sum(
                severity_weights.get(v["severity"], 1) for v in violations
            )

            # Factor de recencia (violaciones más recientes pesan más)
            now = time.time()
            for v in violations:
                days_ago = (now - v["timestamp"]) / 86400
                if days_ago < 1:
                    total_score *= 1.5
                elif days_ago < 3:
                    total_score *= 1.2

            # Determinar nivel
            if total_score >= 100:
                level = "critical"
            elif total_score >= 50:
                level = "high"
            elif total_score >= 20:
                level = "medium"
            else:
                level = "low"

            return {
                "user_id": user_id,
                "risk_score": round(total_score, 2),
                "level": level,
                "violations_count": len(violations),
                "violations_by_type": self._count_by_type(violations),
            }
        except Exception as e:
            logger.error("[AbuseLogger] Error calculando risk score: %s", e)
            return {
                "user_id": user_id,
                "risk_score": 0,
                "level": "unknown",
                "error": str(e),
            }

    def _count_by_type(self, violations: List[Dict]) -> Dict[str, int]:
        """Cuenta violaciones por tipo."""
        counts = {}
        for v in violations:
            vtype = v["violation_type"]
            counts[vtype] = counts.get(vtype, 0) + 1
        return counts

    def mark_resolved(self, log_id: int) -> bool:
        """Marca una violación como resuelta."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    "UPDATE abuse_logs SET resolved = TRUE WHERE id = ?",
                    (log_id,),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error("[AbuseLogger] Error marcando como resuelto: %s", e)
            return False

    def cleanup_old_logs(self, days: int = 90) -> int:
        """Limpia logs antiguos. Retorna número eliminado."""
        try:
            cutoff = time.time() - (days * 24 * 60 * 60)
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                cursor = conn.execute(
                    "DELETE FROM abuse_logs WHERE timestamp < ?",
                    (cutoff,),
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error("[AbuseLogger] Error limpiando logs: %s", e)
            return 0


# Singleton global
_logger_instance: Optional[AbuseLogger] = None


def get_abuse_logger(base_path: Optional[Path] = None) -> AbuseLogger:
    """Obtiene instancia singleton del AbuseLogger."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AbuseLogger(base_path)
    return _logger_instance


__all__ = [
    "AbuseLogger",
    "ViolationType",
    "get_abuse_logger",
]
