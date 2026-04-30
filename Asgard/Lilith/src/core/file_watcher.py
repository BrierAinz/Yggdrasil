"""
FileWatcher - MÃ³dulo de observaciÃ³n de archivos para Lilith

Detecta cambios en tiempo real:
- Archivos modificados
- Nuevos archivos
- Archivos eliminados
- Cambios en dependencias

Integra con ProactiveSuggestions para disparar sugerencias automÃ¡ticamente.
"""

import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from watchdog.events import (
        FileCreatedEvent,
        FileDeletedEvent,
        FileModifiedEvent,
        FileSystemEventHandler,
    )
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger = logging.getLogger("FileWatcher")
    logger.warning("watchdog not available, using fallback polling")

logger = logging.getLogger("FileWatcher")


class ChangeType(str, Enum):
    """Tipo de cambio detectado"""

    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChange:
    """Representa un cambio en un archivo"""

    path: str
    change_type: ChangeType
    timestamp: str
    file_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp,
            "file_type": self.file_type,
        }


class FileWatcherHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Handler para eventos de archivo"""

    def __init__(self, callback: Callable[[FileChange], None]):
        self.callback = callback
        self._last_modified: Dict[str, float] = {}
        self._debounce_seconds = 1.0  # Evitar mÃºltiples eventos por segundo

    def _should_process(self, path: str) -> bool:
        """Verificar si debemos procesar este evento (debounce)"""
        now = time.time()
        last = self._last_modified.get(path, 0)

        if now - last < self._debounce_seconds:
            return False

        self._last_modified[path] = now
        return True

    def _get_file_type(self, path: str) -> Optional[str]:
        """Obtener tipo de archivo"""
        ext = Path(path).suffix.lower()
        type_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".txt": "text",
        }
        return type_map.get(ext)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            change = FileChange(
                path=event.src_path,
                change_type=ChangeType.MODIFIED,
                timestamp=datetime.now().isoformat(),
                file_type=self._get_file_type(event.src_path),
            )
            self.callback(change)

    def on_created(self, event):
        if event.is_directory:
            return
        if self._should_process(event.src_path):
            change = FileChange(
                path=event.src_path,
                change_type=ChangeType.CREATED,
                timestamp=datetime.now().isoformat(),
                file_type=self._get_file_type(event.src_path),
            )
            self.callback(change)

    def on_deleted(self, event):
        if event.is_directory:
            return
        change = FileChange(
            path=event.src_path,
            change_type=ChangeType.DELETED,
            timestamp=datetime.now().isoformat(),
            file_type=self._get_file_type(event.src_path),
        )
        self.callback(change)


class FileWatcher:
    """
    Observador de archivos para Lilith.

    Detecta cambios en tiempo real y dispara sugerencias proactivas.
    """

    def __init__(self):
        self.observer: Optional[Observer] = None
        self.watched_paths: Set[str] = set()
        self._callbacks: List[Callable[[FileChange], None]] = []
        self._change_buffer: List[FileChange] = []
        self._buffer_lock = threading.Lock()
        self._is_running = False

        # Patrones a ignorar
        self.ignore_patterns = [
            "*.pyc",
            "*.pyo",
            "__pycache__/*",
            ".git/*",
            ".svn/*",
            "node_modules/*",
            ".venv/*",
            "venv/*",
            ".env/*",
            "*.log",
            "*.tmp",
            ".DS_Store",
            "Thumbs.db",
            ".pytest_cache/*",
            ".mypy_cache/*",
            ".coverage",
            "*.swp",
            "*.swo",
            "*~",  # Vim swap files
        ]

        # IntegraciÃ³n con ProactiveSuggestions
        self._suggestions_enabled = True
        self._file_stats: Dict[str, Dict[str, Any]] = {}

    def _on_file_change(self, change: FileChange):
        """Callback interno para cambios de archivo"""
        with self._buffer_lock:
            self._change_buffer.append(change)

        # Notificar a suscriptores
        for callback in self._callbacks:
            try:
                callback(change)
            except Exception as e:
                logger.error(f"Error in file change callback: {e}")

        # Analizar para sugerencias proactivas
        if self._suggestions_enabled:
            self._analyze_for_suggestions(change)

    def _analyze_for_suggestions(self, change: FileChange):
        """Analizar cambio para generar sugerencias"""
        try:
            from src.core.proactive_suggestions import get_proactive_suggestions

            suggestions = get_proactive_suggestions()
            path = change.path
            filename = Path(path).name

            # Sugerir docstring para nuevos archivos Python
            if (
                change.change_type == ChangeType.CREATED
                and change.file_type == "python"
            ):
                # Verificar si tiene docstring
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if (
                            "def " in content
                            and '"""' not in content
                            and "'''" not in content
                        ):
                            # Buscar primera funciÃ³n
                            match = re.search(r"def\s+(\w+)", content)
                            if match:
                                func_name = match.group(1)
                                suggestions.suggest_docstring(path, func_name)
                except:
                    pass

            # Sugerir instalar dependencias si cambiÃ³ requirements/package.json
            if change.change_type == ChangeType.MODIFIED:
                if filename in ["requirements.txt", "requirements-dev.txt"]:
                    suggestions.suggest_install_dependencies(filename)
                elif filename == "package.json":
                    suggestions.suggest_install_dependencies(filename)

            # Sugerir tests si se modificÃ³ archivo de tests
            if change.file_type == "python" and "test" in filename.lower():
                suggestions.suggest_run_tests([filename])

            # Detectar posibles problemas de seguridad
            if change.file_type == "python" and change.change_type in [
                ChangeType.CREATED,
                ChangeType.MODIFIED,
            ]:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                        # Detectar eval/exec
                        if re.search(r"\beval\s*\(", content) or re.search(
                            r"\bexec\s*\(", content
                        ):
                            suggestions.suggest_security_scan(path, "uso de eval/exec")

                        # Detectar SQL injection potencial
                        if re.search(r"\.execute\s*\(.*%s", content) or re.search(
                            r'f["\'].*SELECT.*{', content
                        ):
                            suggestions.suggest_security_scan(
                                path, "posible SQL injection"
                            )

                        # Detectar secrets hardcodeados
                        if re.search(
                            r'(password|secret|token|key)\s*=\s*["\'][^"\']{8,}["\']',
                            content,
                            re.IGNORECASE,
                        ):
                            suggestions.suggest_security_scan(
                                path, "posible secret hardcodeado"
                            )
                except:
                    pass

            # Actualizar estadÃ­sticas
            self._file_stats[path] = {
                "last_change": change.timestamp,
                "change_type": change.change_type.value,
                "change_count": self._file_stats.get(path, {}).get("change_count", 0)
                + 1,
            }

        except Exception as e:
            logger.error(f"Error analyzing for suggestions: {e}")

    def start_watching(self, path: str, recursive: bool = True) -> bool:
        """
        Comenzar a observar un directorio

        Args:
            path: Ruta a observar
            recursive: Si True, observa subdirectorios

        Returns:
            True si se iniciÃ³ correctamente
        """
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not available, file watching disabled")
            return False

        if path in self.watched_paths:
            return True

        try:
            if self.observer is None:
                self.observer = Observer()

            handler = FileWatcherHandler(self._on_file_change)
            self.observer.schedule(handler, path, recursive=recursive)
            self.watched_paths.add(path)

            if not self._is_running:
                self.observer.start()
                self._is_running = True

            logger.info(f"Started watching: {path}")
            return True

        except Exception as e:
            logger.error(f"Error starting file watcher: {e}")
            return False

    def stop_watching(self, path: Optional[str] = None):
        """Detener observaciÃ³n"""
        if not WATCHDOG_AVAILABLE or self.observer is None:
            return

        try:
            if path is None:
                # Detener todo
                self.observer.stop()
                self.observer.join()
                self._is_running = False
                self.watched_paths.clear()
                logger.info("Stopped all file watchers")
            else:
                # Nota: watchdog no soporta de-schedule fÃ¡cilmente
                # Se requiere recrear el observer
                pass
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")

    def on_change(self, callback: Callable[[FileChange], None]):
        """Registrar callback para cambios de archivo"""
        self._callbacks.append(callback)

    def get_recent_changes(self, seconds: int = 60) -> List[FileChange]:
        """Obtener cambios recientes"""
        with self._buffer_lock:
            cutoff = datetime.now().timestamp() - seconds
            return [
                c
                for c in self._change_buffer
                if datetime.fromisoformat(c.timestamp).timestamp() > cutoff
            ]

    def get_file_stats(self) -> Dict[str, Any]:
        """Obtener estadÃ­sticas de archivos"""
        return {
            "watched_paths": list(self.watched_paths),
            "file_stats": self._file_stats,
            "recent_changes_count": len(self._change_buffer),
        }

    def enable_suggestions(self, enabled: bool = True):
        """Habilitar/deshabilitar sugerencias proactivas"""
        self._suggestions_enabled = enabled


# Fallback polling si watchdog no estÃ¡ disponible
class PollingFileWatcher:
    """File watcher basado en polling (fallback)"""

    def __init__(self, interval: int = 5):
        self.interval = interval
        self._snapshots: Dict[str, Dict[str, float]] = {}
        self._watched_paths: Set[str] = set()
        self._callbacks: List[Callable[[FileChange], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _take_snapshot(self, path: str) -> Dict[str, float]:
        """Tomar snapshot de directorio"""
        snapshot = {}
        for root, dirs, files in os.walk(path):
            # Ignorar directorios ocultos
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                if file.startswith("."):
                    continue
                filepath = os.path.join(root, file)
                try:
                    stat = os.stat(filepath)
                    snapshot[filepath] = stat.st_mtime
                except:
                    pass
        return snapshot

    def _check_changes(self, path: str):
        """Verificar cambios"""
        new_snapshot = self._take_snapshot(path)
        old_snapshot = self._snapshots.get(path, {})

        # Detectar modificados
        for filepath, mtime in new_snapshot.items():
            if filepath in old_snapshot:
                if old_snapshot[filepath] != mtime:
                    change = FileChange(
                        path=filepath,
                        change_type=ChangeType.MODIFIED,
                        timestamp=datetime.now().isoformat(),
                    )
                    for callback in self._callbacks:
                        callback(change)
            else:
                # Nuevo archivo
                change = FileChange(
                    path=filepath,
                    change_type=ChangeType.CREATED,
                    timestamp=datetime.now().isoformat(),
                )
                for callback in self._callbacks:
                    callback(change)

        # Detectar eliminados
        for filepath in old_snapshot:
            if filepath not in new_snapshot:
                change = FileChange(
                    path=filepath,
                    change_type=ChangeType.DELETED,
                    timestamp=datetime.now().isoformat(),
                )
                for callback in self._callbacks:
                    callback(change)

        self._snapshots[path] = new_snapshot

    def _poll_loop(self):
        """Loop de polling"""
        while self._running:
            for path in self._watched_paths:
                try:
                    self._check_changes(path)
                except Exception as e:
                    logger.error(f"Error checking changes: {e}")

            time.sleep(self.interval)

    def start_watching(self, path: str, recursive: bool = True) -> bool:
        """Comenzar a observar"""
        if path in self._watched_paths:
            return True

        self._watched_paths.add(path)
        self._snapshots[path] = self._take_snapshot(path)

        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()

        return True

    def stop_watching(self, path: Optional[str] = None):
        """Detener observaciÃ³n"""
        if path is None:
            self._running = False
            self._watched_paths.clear()
        else:
            self._watched_paths.discard(path)

    def on_change(self, callback: Callable[[FileChange], None]):
        """Registrar callback"""
        self._callbacks.append(callback)


# Factory para obtener el watcher apropiado
def get_file_watcher():
    """Obtener instancia de file watcher"""
    if WATCHDOG_AVAILABLE:
        return FileWatcher()
    else:
        return PollingFileWatcher()


# Singleton
_file_watcher = None


def get_watcher():
    """Obtener singleton de file watcher"""
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = get_file_watcher()
    return _file_watcher


# === Testing ===
if __name__ == "__main__":
    print("=" * 60)
    print("FileWatcher - Test Suite")
    print("=" * 60)

    import tempfile
    import time

    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n[Test] Observando: {tmpdir}")

        watcher = get_file_watcher()

        changes = []

        def on_change(change):
            changes.append(change)
            print(f"  Change: {change.change_type} - {Path(change.path).name}")

        watcher.on_change(on_change)

        # Iniciar observaciÃ³n
        watcher.start_watching(tmpdir)
        print("âœ“ Watcher started")

        # Crear archivo
        time.sleep(1)
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello")
        print("âœ“ Created test.txt")

        # Modificar archivo
        time.sleep(1)
        test_file.write_text("Hello World")
        print("âœ“ Modified test.txt")

        # Esperar eventos
        time.sleep(2)

        print(f"\nâœ“ Detected {len(changes)} changes")

        # Detener
        watcher.stop_watching()
        print("âœ“ Watcher stopped")

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
