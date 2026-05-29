"""
Audit Logger - B.5: Immutable audit trail with HMAC signatures.

Features:
- HMAC-SHA256 signatures for each log entry
- Integrity verification
- Forensic export
- Event categorization
"""
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.audit")


class AuditLogger:
    """
    Logger de auditoría con firmas HMAC para inmutabilidad.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, base_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )

        # Cargar configuración
        self.config = self._load_config()
        self.enabled = self.config.get("enabled", True)
        self.signing_enabled = self.config.get("signing_enabled", True)

        # Paths
        self.log_path = self.base_path / self.config.get(
            "log_path", "Core/Data/audit_trail.jsonl"
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Secret key para HMAC
        self._secret_key = self._load_secret_key()

        # SQLite para metadata y verificación
        self.db_path = self.base_path / "Data" / "audit_metadata.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self._initialized = True
        logger.info("[AuditLogger] Inicializado. Signing: %s", self.signing_enabled)

    def _load_config(self) -> dict:
        """Carga configuración desde audit.json."""
        config_path = self.base_path / "Config" / "audit.json"
        return safe_load(
            config_path,
            default={
                "enabled": True,
                "log_path": "Core/Data/audit_trail.jsonl",
                "signing_enabled": True,
            },
        )

    def _load_secret_key(self) -> bytes:
        """Carga secret key para HMAC."""
        # 1. Intentar desde variable de entorno
        env_key = os.getenv("AUDIT_SECRET_KEY")
        if env_key:
            return env_key.encode()

        # 2. Intentar cargar desde archivo
        key_path = self.base_path / "Config" / ".audit_key"
        if key_path.exists():
            return key_path.read_bytes()

        # 3. Generar nueva key y guardar
        key = os.urandom(32)
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key)
            # Set restrictive permissions (Windows)
            import stat

            os.chmod(str(key_path), stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.warning("[AuditLogger] No se pudo guardar key: %s", e)

        return key

    def _init_db(self) -> None:
        """Inicializa base de datos de metadata."""
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        signature TEXT NOT NULL,
                        entry_hash TEXT NOT NULL
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_time
                    ON audit_entries(timestamp)
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_audit_type
                    ON audit_entries(event_type)
                """
                )
                conn.commit()
        except Exception as e:
            logger.error("[AuditLogger] Error inicializando DB: %s", e)

    def _sign_entry(self, entry: dict) -> str:
        """Genera firma HMAC-SHA256 para una entrada."""
        # Crear string canonicalizado (ordenado por keys)
        entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        signature = hmac.new(
            self._secret_key, entry_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature

    def _hash_entry(self, entry: dict) -> str:
        """Genera hash SHA256 del contenido."""
        entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(entry_str.encode("utf-8")).hexdigest()

    def log(self, event_type: str, details: dict, level: str = "info") -> bool:
        """
        Loguea un evento con firma HMAC.

        Args:
            event_type: Tipo de evento (filesystem_operation, etc.)
            details: Detalles del evento
            level: Nivel de log (debug, info, warning, error)
        """
        if not self.enabled:
            return False

        # Verificar si el evento está habilitado
        events_config = self.config.get("events", {})
        event_config = events_config.get(event_type, {})
        if not event_config.get("enabled", True):
            return False

        try:
            # Crear entrada
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "level": level,
                "details": details,
                "sequence": int(time.time() * 1000000),  # Microseconds para unicidad
            }

            # Firmar si está habilitado
            if self.signing_enabled:
                entry["signature"] = self._sign_entry(entry)
                entry["hash"] = self._hash_entry(entry)

            # Guardar en JSONL
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Guardar metadata en SQLite
            with sqlite3.connect(str(self.db_path), timeout=5) as conn:
                conn.execute(
                    "INSERT INTO audit_entries (timestamp, event_type, signature, entry_hash) VALUES (?, ?, ?, ?)",
                    (
                        time.time(),
                        event_type,
                        entry.get("signature", ""),
                        entry.get("hash", ""),
                    ),
                )
                conn.commit()

            # También loguear al logger estándar
            log_msg = (
                f"[Audit] {event_type}: {json.dumps(details, ensure_ascii=False)[:200]}"
            )
            if level == "error":
                logger.error(log_msg)
            elif level == "warning":
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            return True

        except Exception as e:
            logger.error("[AuditLogger] Error logueando evento: %s", e)
            return False

    def verify_entry(self, entry: dict) -> bool:
        """Verifica la firma de una entrada."""
        if not self.signing_enabled:
            return True

        try:
            stored_signature = entry.pop("signature", None)
            stored_hash = entry.pop("hash", None)

            if not stored_signature:
                return False

            # Verificar firma
            computed_signature = self._sign_entry(entry)

            # Restaurar valores
            entry["signature"] = stored_signature
            if stored_hash:
                entry["hash"] = stored_hash

            return hmac.compare_digest(stored_signature, computed_signature)
        except Exception as e:
            logger.error("[AuditLogger] Error verificando entrada: %s", e)
            return False

    def verify_integrity(
        self, start_time: Optional[float] = None, end_time: Optional[float] = None
    ) -> Tuple[int, int, List[dict]]:
        """
        Verifica la integridad del audit trail.

        Returns:
            Tuple: (total_entries, valid_entries, list_of_invalid)
        """
        if not self.log_path.exists():
            return 0, 0, []

        total = 0
        valid = 0
        invalid = []

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # Filtrar por tiempo si se especificó
                        entry_ts = datetime.fromisoformat(
                            entry.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp()
                        if start_time and entry_ts < start_time:
                            continue
                        if end_time and entry_ts > end_time:
                            continue

                        total += 1

                        if self.verify_entry(entry):
                            valid += 1
                        else:
                            invalid.append(
                                {
                                    "line": line_num,
                                    "timestamp": entry.get("timestamp"),
                                    "event_type": entry.get("event_type"),
                                    "reason": "invalid_signature",
                                }
                            )

                    except json.JSONDecodeError:
                        invalid.append(
                            {"line": line_num, "reason": "json_decode_error"}
                        )
                    except Exception as e:
                        invalid.append({"line": line_num, "reason": str(e)})

            logger.info(
                "[AuditLogger] Integrity check: %d total, %d valid, %d invalid",
                total,
                valid,
                len(invalid),
            )
            return total, valid, invalid

        except Exception as e:
            logger.error("[AuditLogger] Error en verificación de integridad: %s", e)
            return 0, 0, [{"error": str(e)}]

    def export_forensic(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Exporta logs en formato forense.

        Args:
            start_date: Fecha inicio (ISO format)
            end_date: Fecha fin (ISO format)
            event_types: Lista de tipos de evento a incluir
            output_path: Path de salida (opcional)

        Returns:
            Path del archivo ZIP exportado
        """
        if not self.log_path.exists():
            logger.warning("[AuditLogger] No hay logs para exportar")
            return None

        try:
            # Parsear fechas
            start_ts = None
            end_ts = None
            if start_date:
                start_ts = datetime.fromisoformat(
                    start_date.replace("Z", "+00:00")
                ).timestamp()
            if end_date:
                end_ts = datetime.fromisoformat(
                    end_date.replace("Z", "+00:00")
                ).timestamp()

            # Filtrar entradas
            filtered_entries = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)

                        # Filtrar por fecha
                        entry_ts = datetime.fromisoformat(
                            entry.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp()
                        if start_ts and entry_ts < start_ts:
                            continue
                        if end_ts and entry_ts > end_ts:
                            continue

                        # Filtrar por tipo
                        if event_types and entry.get("event_type") not in event_types:
                            continue

                        filtered_entries.append(entry)
                    except:
                        continue

            if not filtered_entries:
                logger.warning("[AuditLogger] No hay entradas para exportar")
                return None

            # Generar nombre de archivo
            if output_path is None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                output_path = self.base_path / "Data" / f"audit_export_{timestamp}.zip"

            # Crear ZIP
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Archivo principal
                audit_content = "\n".join(
                    json.dumps(e, ensure_ascii=False) for e in filtered_entries
                )
                zf.writestr("audit_trail.jsonl", audit_content)

                # Checksums
                checksums = []
                for entry in filtered_entries:
                    entry_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
                    checksum = hashlib.sha256(entry_str.encode()).hexdigest()
                    checksums.append(
                        f"{entry.get('timestamp', 'unknown')} {entry.get('event_type', 'unknown')} {checksum}"
                    )
                zf.writestr("checksums.txt", "\n".join(checksums))

                # Metadata
                metadata = {
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "lilith_version": "4.1",
                    "entries_count": len(filtered_entries),
                    "date_range": {"start": start_date, "end": end_date},
                    "event_types": event_types,
                    "signing_enabled": self.signing_enabled,
                    "export_format": "forensic_v1",
                }
                zf.writestr(
                    "metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False)
                )

            logger.info(
                "[AuditLogger] Export forense creado: %s (%d entradas)",
                output_path,
                len(filtered_entries),
            )
            return output_path

        except Exception as e:
            logger.error("[AuditLogger] Error exportando: %s", e)
            return None

    def get_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Obtiene estadísticas de auditoría."""
        try:
            since = time.time() - (hours * 3600)

            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # Total por tipo
                cursor = conn.execute(
                    "SELECT event_type, COUNT(*) FROM audit_entries WHERE timestamp > ? GROUP BY event_type",
                    (since,),
                )
                by_type = {r[0]: r[1] for r in cursor.fetchall()}

                # Total general
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM audit_entries WHERE timestamp > ?", (since,)
                )
                total = cursor.fetchone()[0]

                return {
                    "total_entries": total,
                    "by_event_type": by_type,
                    "period_hours": hours,
                }
        except Exception as e:
            logger.error("[AuditLogger] Error obteniendo stats: %s", e)
            return {}

    def cleanup_old_entries(self, days: int = 365) -> int:
        """Limpia entradas antiguas."""
        try:
            cutoff = time.time() - (days * 24 * 3600)

            # Leer entradas recientes
            if not self.log_path.exists():
                return 0

            recent_entries = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        entry_ts = datetime.fromisoformat(
                            entry.get("timestamp", "").replace("Z", "+00:00")
                        ).timestamp()
                        if entry_ts > cutoff:
                            recent_entries.append(entry)
                    except:
                        continue

            # Reescribir archivo
            with open(self.log_path, "w", encoding="utf-8") as f:
                for entry in recent_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Limpiar SQLite
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                conn.execute("DELETE FROM audit_entries WHERE timestamp < ?", (cutoff,))
                conn.commit()

            logger.info(
                "[AuditLogger] Cleanup completado. Entradas conservadas: %d",
                len(recent_entries),
            )
            return len(recent_entries)

        except Exception as e:
            logger.error("[AuditLogger] Error en cleanup: %s", e)
            return 0


# Singleton
_audit_logger_instance: Optional[AuditLogger] = None


def get_audit_logger(base_path: Optional[Path] = None) -> AuditLogger:
    """Obtiene instancia singleton del AuditLogger."""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger(base_path)
    return _audit_logger_instance


# Funciones conveniencia
def audit_log(event_type: str, details: dict, level: str = "info") -> bool:
    """Loguea un evento de auditoría."""
    logger = get_audit_logger()
    return logger.log(event_type, details, level)


__all__ = ["AuditLogger", "get_audit_logger", "audit_log"]
