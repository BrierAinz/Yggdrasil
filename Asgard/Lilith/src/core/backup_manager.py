"""
Lilith 4.1 — A.3 Backup Manager.
Snapshots automáticos de MuninnDB, episodios y Config con retención y restauración.
"""
import glob as _glob
import hashlib
import json
import logging
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("lilith.backup")


def _load_config(base_path: Path) -> Dict[str, Any]:
    try:
        from src.core.json_safe import safe_load

        cfg = safe_load(base_path / "Config" / "backups.json", default={})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


class BackupManager:
    """
    A.3 — Crea, restaura y verifica snapshots de Lilith.
    Incluye retención automática (N diarios + M semanales).
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def _backup_dir(self) -> Path:
        cfg = _load_config(self.base_path)
        d = Path(cfg.get("backup_dir", "D:/Backups/Lilith"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _resolve_includes(self) -> List[Path]:
        """Expande los patrones glob de include en archivos concretos."""
        cfg = _load_config(self.base_path)
        patterns = cfg.get(
            "include",
            [
                str(self.base_path / "Data" / "*.jsonl"),
                str(self.base_path / "Config" / "*.json"),
            ],
        )
        files: List[Path] = []
        for pattern in patterns:
            # Resolver relative patterns respecto a base_path
            if not Path(pattern).is_absolute():
                pattern = str(self.base_path / pattern)
            for match in _glob.glob(pattern, recursive=True):
                p = Path(match)
                if p.is_file():
                    files.append(p)
            # También incluir directorios completos (MuninnDB)
            p = Path(pattern)
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        files.append(f)
        return list(dict.fromkeys(files))  # dedup

    def create_snapshot(self) -> Dict[str, Any]:
        """
        Crea un snapshot ZIP con todos los archivos configurados.
        Incluye checksums.json para verificación de integridad.
        Retorna {'path': str, 'size_bytes': int, 'files': int, 'ok': bool}.
        """
        cfg = _load_config(self.base_path)
        if not cfg.get("enabled", True):
            return {"ok": False, "reason": "backups desactivados"}

        backup_dir = self._backup_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"lilith_backup_{timestamp}.zip"
        zip_path = backup_dir / zip_name

        files = self._resolve_includes()
        if not files:
            logger.warning("[BackupManager] Sin archivos para incluir en snapshot.")
            return {"ok": False, "reason": "sin archivos"}

        checksums: Dict[str, str] = {}
        file_count = 0

        try:
            with zipfile.ZipFile(
                zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
            ) as zf:
                for fpath in files:
                    try:
                        # Ruta relativa dentro del zip
                        try:
                            arc_name = fpath.relative_to(self.base_path.parent)
                        except ValueError:
                            arc_name = Path(fpath.name)
                        arc_str = arc_name.as_posix()  # Siempre forward slashes en ZIP
                        zf.write(fpath, arc_str)
                        checksums[arc_str] = _sha256_file(fpath)
                        file_count += 1
                    except Exception as e:
                        logger.warning(
                            "[BackupManager] Error añadiendo %s: %s", fpath, e
                        )

                # Escribir checksums.json dentro del zip
                checksums_json = json.dumps(checksums, indent=2, ensure_ascii=False)
                zf.writestr("checksums.json", checksums_json)

            size_bytes = zip_path.stat().st_size
            logger.info(
                "[BackupManager] Snapshot created: %s (%.1f MB, %d files)",
                zip_name,
                size_bytes / 1_048_576,
                file_count,
            )

            # Aplicar política de retención
            self._apply_retention(backup_dir, cfg)

            return {
                "path": str(zip_path),
                "size_bytes": size_bytes,
                "files": file_count,
                "ok": True,
            }

        except Exception as e:
            logger.error("[BackupManager] Error creando snapshot: %s", e)
            if zip_path.exists():
                zip_path.unlink()
            return {"ok": False, "reason": str(e)}

    def _apply_retention(self, backup_dir: Path, cfg: Dict[str, Any]) -> None:
        """Elimina snapshots fuera de la política de retención."""
        retention = cfg.get("retention", {})
        daily_keep = int(retention.get("daily_backups", 7))
        weekly_keep = int(retention.get("weekly_backups", 4))

        snapshots = sorted(backup_dir.glob("lilith_backup_*.zip"), reverse=True)
        if not snapshots:
            return

        # Clasificar: diarios (últimos daily_keep) + domingos (últimos weekly_keep)
        to_keep = set()
        daily_count = 0
        weekly_seen: set = set()

        for snap in snapshots:
            try:
                # Extraer fecha del nombre: lilith_backup_YYYY-MM-DD_HH-MM-SS.zip
                date_str = snap.stem.split("_", 2)[2][:10]  # YYYY-MM-DD
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                to_keep.add(snap)
                continue

            if daily_count < daily_keep:
                to_keep.add(snap)
                daily_count += 1

            # Semanales: domingos
            if dt.weekday() == 6:  # domingo
                week_key = f"{dt.year}-{dt.isocalendar()[1]}"
                if week_key not in weekly_seen and len(weekly_seen) < weekly_keep:
                    to_keep.add(snap)
                    weekly_seen.add(week_key)

        # Eliminar los que no están en to_keep
        removed = 0
        for snap in snapshots:
            if snap not in to_keep:
                snap.unlink()
                removed += 1
                logger.debug(
                    "[BackupManager] Snapshot expirado eliminado: %s", snap.name
                )

        if removed:
            logger.info("[BackupManager] Retención: %d snapshots eliminados.", removed)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lista snapshots disponibles con metadata."""
        backup_dir = self._backup_dir()
        snapshots = sorted(backup_dir.glob("lilith_backup_*.zip"), reverse=True)
        result = []
        for snap in snapshots:
            try:
                size_mb = snap.stat().st_size / 1_048_576
                result.append(
                    {
                        "name": snap.name,
                        "path": str(snap),
                        "size_mb": round(size_mb, 1),
                        "created": snap.stem.split("_", 2)[2].replace("_", " ")
                        if "_" in snap.stem
                        else "?",
                    }
                )
            except Exception:
                continue
        return result

    def verify_snapshot(self, snapshot_path: Path) -> Tuple[bool, str]:
        """
        Verifica integridad de un snapshot comparando checksums.
        Devuelve (ok, message).
        """
        snapshot_path = Path(snapshot_path)
        if not snapshot_path.exists():
            return False, f"Snapshot no encontrado: {snapshot_path}"
        try:
            with zipfile.ZipFile(snapshot_path, "r") as zf:
                if "checksums.json" not in zf.namelist():
                    return False, "checksums.json no encontrado en el snapshot"
                checksums = json.loads(zf.read("checksums.json"))
                errors = []
                for arc_name, expected_sha in checksums.items():
                    if arc_name == "checksums.json":
                        continue
                    if arc_name not in zf.namelist():
                        errors.append(f"Archivo faltante: {arc_name}")
                        continue
                    data = zf.read(arc_name)
                    actual_sha = hashlib.sha256(data).hexdigest()
                    if actual_sha != expected_sha:
                        errors.append(f"Checksum mismatch: {arc_name}")
                if errors:
                    return False, f"Integridad comprometida: {'; '.join(errors[:3])}"
                return True, f"Snapshot íntegro ({len(checksums)} archivos verificados)"
        except Exception as e:
            return False, f"Error verificando snapshot: {e}"

    def restore_snapshot(
        self, snapshot_path: Path, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Restaura un snapshot.
        1. Verifica integridad
        2. Crea backup de seguridad (rollback)
        3. Extrae archivos a ubicaciones originales
        """
        snapshot_path = Path(snapshot_path)

        # 1. Verificar integridad
        ok, msg = self.verify_snapshot(snapshot_path)
        if not ok:
            return {"ok": False, "reason": f"Verificación fallida: {msg}"}

        if dry_run:
            return {"ok": True, "dry_run": True, "message": msg}

        # 2. Backup de seguridad previo (rollback)
        rollback = self.create_snapshot()
        if not rollback.get("ok"):
            logger.warning(
                "[BackupManager] No se pudo crear backup de rollback: %s",
                rollback.get("reason"),
            )

        # 3. Restaurar
        restored_files = 0
        errors = []
        try:
            with zipfile.ZipFile(snapshot_path, "r") as zf:
                for arc_name in zf.namelist():
                    if arc_name == "checksums.json":
                        continue
                    try:
                        # Reconstruir ruta absoluta: arc_name es relativo a parent de base_path
                        target = self.base_path.parent / arc_name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with open(target, "wb") as f:
                            f.write(zf.read(arc_name))
                        restored_files += 1
                    except Exception as e:
                        errors.append(f"{arc_name}: {e}")

            logger.info(
                "[BackupManager] Restored from %s (%d files, %d errors)",
                snapshot_path.name,
                restored_files,
                len(errors),
            )
            return {
                "ok": True,
                "restored_files": restored_files,
                "errors": errors[:5],
                "rollback_snapshot": rollback.get("path"),
            }
        except Exception as e:
            logger.error("[BackupManager] Error restaurando: %s", e)
            return {"ok": False, "reason": str(e)}

    def verify_all_snapshots(self) -> Dict[str, Any]:
        """Verifica integridad de todos los snapshots. Notifica si hay corruptos."""
        backup_dir = self._backup_dir()
        snapshots = list(backup_dir.glob("lilith_backup_*.zip"))
        results = {}
        corrupted = []
        for snap in snapshots:
            ok, msg = self.verify_snapshot(snap)
            results[snap.name] = {"ok": ok, "message": msg}
            if not ok:
                corrupted.append(snap.name)
        if corrupted:
            logger.error("[BackupManager] Snapshots corruptos: %s", corrupted)
        return {"total": len(snapshots), "corrupted": corrupted, "results": results}
