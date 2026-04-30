"""
Audit Storage - Almacenamiento de eventos de auditoría

v4.2.8: Almacenamiento append-only con rotación de archivos.
"""
import gzip
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .events import AuditEvent, EventType

logger = logging.getLogger("lilith.audit.storage")


@dataclass
class StorageConfig:
    """Configuración del almacenamiento."""

    base_path: Path
    retention_days: int = 90
    max_file_size_mb: int = 100
    compression_after_days: int = 30
    max_events_per_query: int = 10000


class AuditStorage:
    """
    Almacenamiento append-only para eventos de auditoría.

    Características:
    - Escritura append-only (sin modificación de eventos existentes)
    - Rotación por fecha y tamaño
    - Compresión automática de archivos antiguos
    - Retención configurable
    """

    def __init__(self, config: StorageConfig):
        self.config = config
        self._current_file: Optional[Path] = None
        self._current_size: int = 0
        self._ensure_directories()

    def _ensure_directories(self):
        """Crea los directorios necesarios."""
        self.config.base_path.mkdir(parents=True, exist_ok=True)
        (self.config.base_path / "compressed").mkdir(exist_ok=True)
        (self.config.base_path / "archive").mkdir(exist_ok=True)

    def _get_current_file(self) -> Path:
        """Obtiene el archivo actual para escritura."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.config.base_path / f"audit_{today}.jsonl"

    def _should_rotate(self) -> bool:
        """Determina si se debe rotar el archivo actual."""
        current = self._get_current_file()
        if not current.exists():
            return False

        size_mb = current.stat().st_size / (1024 * 1024)
        return size_mb >= self.config.max_file_size_mb

    def _rotate_if_needed(self):
        """Rota el archivo si es necesario."""
        if self._should_rotate():
            current = self._get_current_file()
            timestamp = datetime.utcnow().strftime("%H%M%S")
            new_name = current.stem + f"_{timestamp}.jsonl"
            current.rename(self.config.base_path / new_name)
            logger.info(f"Archivo de auditoría rotado: {new_name}")

    def append(self, event: AuditEvent) -> bool:
        """
        Añade un evento al log (append-only).

        Args:
            event: Evento a registrar

        Returns:
            True si se guardó exitosamente
        """
        try:
            self._rotate_if_needed()

            current_file = self._get_current_file()
            jsonl_line = event.to_jsonl() + "\n"

            with open(current_file, "a", encoding="utf-8") as f:
                f.write(jsonl_line)

            return True

        except Exception as e:
            logger.error(f"Error guardando evento de auditoría: {e}")
            return False

    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[EventType]] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """
        Consulta eventos con filtros.

        Args:
            start_date: Fecha inicial
            end_date: Fecha final
            event_types: Tipos de evento a filtrar
            actor: Filtrar por actor
            resource: Filtrar por recurso
            status: Filtrar por status
            limit: Máximo de resultados
            offset: Offset para paginación

        Returns:
            Lista de eventos que coinciden
        """
        events = []
        skipped = 0

        for event in self._iter_events(start_date, end_date):
            # Aplicar filtros
            if event_types and event.event_type not in event_types:
                continue
            if actor and event.actor != actor:
                continue
            if resource and event.resource != resource:
                continue
            if status and event.status != status:
                continue

            # Paginación
            if skipped < offset:
                skipped += 1
                continue

            events.append(event)

            if len(events) >= limit:
                break

        return events

    def _iter_events(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Iterator[AuditEvent]:
        """Itera sobre todos los eventos en orden cronológico inverso."""
        files = sorted(self.config.base_path.glob("audit_*.jsonl*"), reverse=True)

        for file_path in files:
            # Verificar si está en el rango de fechas
            file_date = self._extract_date_from_filename(file_path.name)
            if file_date:
                if start_date and file_date < start_date.date():
                    continue
                if end_date and file_date > end_date.date():
                    continue

            # Leer archivo (descomprimir si es necesario)
            if file_path.suffix == ".gz":
                yield from self._read_gzipped(file_path)
            else:
                yield from self._read_plain(file_path)

    def _extract_date_from_filename(self, filename: str) -> Optional[datetime.date]:
        """Extrae la fecha del nombre de archivo."""
        try:
            # Formato: audit_YYYY-MM-DD.jsonl o audit_YYYY-MM-DD_HHMMSS.jsonl
            date_str = filename.replace("audit_", "").split(".")[0].split("_")[0]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, IndexError):
            return None

    def _read_plain(self, file_path: Path) -> Iterator[AuditEvent]:
        """Lee un archivo plano línea por línea."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        yield AuditEvent.from_dict(data)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Línea corrupta en {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {e}")

    def _read_gzipped(self, file_path: Path) -> Iterator[AuditEvent]:
        """Lee un archivo comprimido."""
        try:
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                for line in reversed(list(f)):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        yield AuditEvent.from_dict(data)
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Línea corrupta en {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {e}")

    def compress_old_files(self):
        """Comprime archivos antiguos."""
        cutoff_date = datetime.utcnow() - timedelta(
            days=self.config.compression_after_days
        )

        for file_path in self.config.base_path.glob("audit_*.jsonl"):
            file_date = self._extract_date_from_filename(file_path.name)
            if file_date and file_date < cutoff_date.date():
                compressed_path = (
                    self.config.base_path / "compressed" / f"{file_path.name}.gz"
                )
                try:
                    with open(file_path, "rb") as f_in:
                        with gzip.open(compressed_path, "wb") as f_out:
                            f_out.writelines(f_in)
                    file_path.unlink()
                    logger.info(f"Archivo comprimido: {file_path.name}")
                except Exception as e:
                    logger.error(f"Error comprimiendo {file_path}: {e}")

    def cleanup_old_files(self):
        """Elimina archivos antiguos según retención configurada."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)

        for subdir in ["", "compressed", "archive"]:
            path = self.config.base_path / subdir
            for file_path in path.glob("audit_*"):
                file_date = self._extract_date_from_filename(file_path.name)
                if file_date and file_date < cutoff_date.date():
                    try:
                        file_path.unlink()
                        logger.info(
                            f"Archivo eliminado por retención: {file_path.name}"
                        )
                    except Exception as e:
                        logger.error(f"Error eliminando {file_path}: {e}")

    def export_to_csv(self, output_path: Path, **filters) -> int:
        """
        Exporta eventos a CSV.

        Returns:
            Número de eventos exportados
        """
        import csv

        count = 0
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "event_type",
                    "actor",
                    "resource",
                    "action",
                    "status",
                    "details",
                    "ip_address",
                    "request_id",
                ]
            )

            for event in self.query(limit=self.config.max_events_per_query, **filters):
                writer.writerow(
                    [
                        event.timestamp.isoformat(),
                        event.event_type.value,
                        event.actor,
                        event.resource,
                        event.action,
                        event.status,
                        json.dumps(event.details, ensure_ascii=False),
                        event.ip_address or "",
                        event.request_id or "",
                    ]
                )
                count += 1

        return count

    def export_to_json(self, output_path: Path, **filters) -> int:
        """
        Exporta eventos a JSON.

        Returns:
            Número de eventos exportados
        """
        events = self.query(limit=self.config.max_events_per_query, **filters)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, indent=2, ensure_ascii=False)

        return len(events)

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del almacenamiento."""
        total_files = len(list(self.config.base_path.glob("audit_*")))
        total_size = sum(
            f.stat().st_size for f in self.config.base_path.rglob("audit_*")
        )

        # Contar eventos de hoy
        today = datetime.utcnow().date()
        today_count = len(
            self.query(
                start_date=datetime.combine(today, datetime.min.time()), limit=10000
            )
        )

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "today_events": today_count,
            "retention_days": self.config.retention_days,
            "base_path": str(self.config.base_path),
        }
