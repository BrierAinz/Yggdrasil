"""
Skill Registry
==============
Registro central de skills con hot-reload via watchdog.

Soporta:
- Carga inicial de skills desde directorio
- Hot-reload automatico cuando archivos cambian
- Busqueda por trigger (keywords)
- Priorizacion de skills
"""
import asyncio
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from Lilith.Core.config import SKILLS_DIR, SKILLS_HOT_RELOAD
from Lilith.Core.skill_parser import Skill, SkillParseError, get_parser

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


class SkillRegistry:
    """Registro de skills con hot-reload."""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        hot_reload: bool = True,
    ):
        self.skills_dir = skills_dir or SKILLS_DIR
        self.hot_reload = hot_reload and SKILLS_HOT_RELOAD and WATCHDOG_AVAILABLE
        self.skills: Dict[str, Skill] = {}
        self._parser = get_parser()
        self._observer: Optional[Observer] = None
        self._lock = threading.RLock()
        self._on_reload_callbacks: List[Callable[[List[str]], None]] = []

        # Cargar skills iniciales
        self._load_all()

        # Iniciar watcher si esta habilitado
        if self.hot_reload:
            self._start_watching()

    def _load_all(self) -> List[str]:
        """Carga todos los skills del directorio."""
        loaded = []

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return loaded

        for skill_file in self.skills_dir.rglob("*.md"):
            if skill_file.name.startswith("."):
                continue
            try:
                skill = self._parser.parse_file(skill_file)
                with self._lock:
                    self.skills[skill.name] = skill
                loaded.append(skill.name)
            except SkillParseError as e:
                print(f"[SKILL] Error cargando {skill_file.name}: {e}")
            except Exception as e:
                print(f"[SKILL] Error inesperado en {skill_file.name}: {e}")

        return loaded

    def reload(self) -> List[str]:
        """
        Recarga manual todos los skills.

        Returns:
            Lista de nombres de skills recargados.
        """
        with self._lock:
            old_skills = dict(self.skills)
            self.skills.clear()

        loaded = self._load_all()

        # Notificar callbacks
        for callback in self._on_reload_callbacks:
            try:
                callback(loaded)
            except Exception:
                pass

        return loaded

    def reload_file(self, file_path: Path) -> Optional[str]:
        """
        Recarga un skill especifico desde archivo.

        Returns:
            Nombre del skill recargado, o None si fallo.
        """
        try:
            skill = self._parser.parse_file(file_path)
            with self._lock:
                self.skills[skill.name] = skill
            return skill.name
        except Exception as e:
            print(f"[SKILL] Error recargando {file_path}: {e}")
            return None

    def get(self, name: str) -> Optional[Skill]:
        """Obtiene un skill por nombre."""
        with self._lock:
            return self.skills.get(name)

    def list_skills(self) -> List[Skill]:
        """Lista todos los skills ordenados por prioridad."""
        with self._lock:
            return sorted(self.skills.values(), key=lambda s: (-s.priority, s.name))

    def get_triggered_skills(self, text: str, max_skills: int = 3) -> List[Skill]:
        """
        Devuelve skills que deben activarse para el texto dado.

        Args:
            text: Texto del usuario
            max_skills: Maximo numero de skills a retornar

        Returns:
            Lista de skills ordenados por score de trigger
        """
        with self._lock:
            triggered = []
            for skill in self.skills.values():
                score = skill.trigger_score(text)
                if score > 0:
                    triggered.append((skill, score))

        # Ordenar por score descendente (domina), luego por prioridad descendente
        triggered.sort(key=lambda x: (-x[1], -x[0].priority, x[0].name), reverse=False)
        return [skill for skill, _ in triggered[:max_skills]]

    def add_skill(self, skill: Skill) -> None:
        """Agrega un skill manualmente."""
        with self._lock:
            self.skills[skill.name] = skill

    def remove_skill(self, name: str) -> bool:
        """Elimina un skill por nombre."""
        with self._lock:
            if name in self.skills:
                del self.skills[name]
                return True
            return False

    def on_reload(self, callback: Callable[[List[str]], None]) -> None:
        """Registra un callback para cuando skills se recargan."""
        self._on_reload_callbacks.append(callback)

    def get_stats(self) -> Dict[str, any]:
        """Devuelve estadisticas del registry."""
        with self._lock:
            return {
                "total_skills": len(self.skills),
                "skills_dir": str(self.skills_dir),
                "hot_reload": self.hot_reload,
                "watchdog_available": WATCHDOG_AVAILABLE,
                "skill_names": sorted(self.skills.keys()),
            }

    # ═══════════════════════════════════════════════════════════════════════════
    # HOT-RELOAD (WATCHDOG)
    # ═══════════════════════════════════════════════════════════════════════════

    def _start_watching(self) -> None:
        """Inicia el file watcher para hot-reload."""
        if not WATCHDOG_AVAILABLE:
            print("[SKILL] watchdog no disponible, hot-reload deshabilitado")
            return

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)

        class SkillEventHandler(FileSystemEventHandler):
            def __init__(self, registry: "SkillRegistry"):
                self.registry = registry
                self._last_reload = 0

            def on_modified(self, event):
                if event.is_directory:
                    return
                if not event.src_path.endswith(".md"):
                    return
                # Debounce: ignorar eventos dentro de 300ms del mismo archivo
                now = time.time()
                path = Path(event.src_path)
                key = str(path)
                last = getattr(self, "_last_reload_map", {}).get(key, 0)
                if now - last < 0.3:
                    return
                if not hasattr(self, "_last_reload_map"):
                    self._last_reload_map = {}
                self._last_reload_map[key] = now

                skill_name = self.registry.reload_file(path)
                if skill_name:
                    print(f"[SKILL] Hot-reload: {skill_name}")

            def on_created(self, event):
                if event.is_directory:
                    return
                if not event.src_path.endswith(".md"):
                    return
                # Debounce para created tambien
                now = time.time()
                path = Path(event.src_path)
                key = str(path)
                last = getattr(self, "_last_reload_map", {}).get(key, 0)
                if now - last < 0.3:
                    return
                if not hasattr(self, "_last_reload_map"):
                    self._last_reload_map = {}
                self._last_reload_map[key] = now

                skill_name = self.registry.reload_file(path)
                if skill_name:
                    print(f"[SKILL] Nuevo skill detectado: {skill_name}")

            def on_deleted(self, event):
                if event.is_directory:
                    return
                if not event.src_path.endswith(".md"):
                    return
                # Encontrar skill por source_file y eliminarlo
                path = Path(event.src_path)
                with self.registry._lock:
                    to_remove = [
                        name
                        for name, skill in self.registry.skills.items()
                        if skill.source_file == path
                    ]
                    for name in to_remove:
                        del self.registry.skills[name]
                        print(f"[SKILL] Skill eliminado: {name}")

        handler = SkillEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.skills_dir), recursive=True)
        self._observer.start()
        print(f"[SKILL] Hot-reload activo en: {self.skills_dir}")

    def stop_watching(self) -> None:
        """Detiene el file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            print("[SKILL] Hot-reload detenido")

    def __del__(self):
        """Cleanup al destruir el objeto."""
        self.stop_watching()


# Singleton
_registry: Optional[SkillRegistry] = None


def get_skill_registry(
    skills_dir: Optional[Path] = None,
    hot_reload: bool = True,
) -> SkillRegistry:
    """Devuelve el registry singleton."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry(skills_dir=skills_dir, hot_reload=hot_reload)
    return _registry
