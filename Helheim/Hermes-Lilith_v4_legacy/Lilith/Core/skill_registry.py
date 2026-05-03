"""
Skill Registry v2
=================
Registro central de skills con hot-reload via watchdog.

Soporta:
- Carga inicial de skills desde directorio (*.md, *.yaml, *.yml)
- Hot-reload automatico cuando archivos cambian
- Busqueda por trigger (keywords + regex + intent)
- Priorizacion de skills
- Enable/disable de skills
- Estadisticas de uso (times_triggered, last_triggered)
- Validacion de tools_required contra DynamicToolRegistry
"""
import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from Lilith.Core.config import SKILLS_DIR, SKILLS_HOT_RELOAD
from Lilith.Core.skill_parser import Skill, SkillParseError, get_parser

logger = logging.getLogger("Lilith.SkillRegistry")

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

    # Extensiones de archivo soportadas
    SKILL_EXTENSIONS = {".md", ".yaml", ".yml"}

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        hot_reload: bool = True,
        tool_registry=None,
    ):
        self.skills_dir = skills_dir or SKILLS_DIR
        self.hot_reload = hot_reload and SKILLS_HOT_RELOAD and WATCHDOG_AVAILABLE
        self.skills: Dict[str, Skill] = {}
        self._parser = get_parser()
        self._observer: Optional[Observer] = None
        self._lock = threading.RLock()
        self._on_reload_callbacks: List[Callable[[List[str]], None]] = []
        self._tool_registry = tool_registry  # DynamicToolRegistry (lazy)

        # Cargar skills iniciales
        self._load_all()

        # Validar tools_required contra DynamicToolRegistry
        if self._tool_registry:
            self._validate_tools_required()

        # Iniciar watcher si esta habilitado
        if self.hot_reload:
            self._start_watching()

    # ═══════════════════════════════════════════════════════════════════════════
    # Enable / Disable
    # ═══════════════════════════════════════════════════════════════════════════

    def enable_skill(self, name: str) -> bool:
        """Habilita un skill por nombre.

        Returns:
            True si el skill existe y fue habilitado, False si no existe.
        """
        with self._lock:
            skill = self.skills.get(name)
            if skill is None:
                return False
            skill.enabled = True
            logger.info(f"[SKILL] Skill habilitado: {name}")
            return True

    def disable_skill(self, name: str) -> bool:
        """Deshabilita un skill por nombre.

        Returns:
            True si el skill existe y fue deshabilitado, False si no existe.
        """
        with self._lock:
            skill = self.skills.get(name)
            if skill is None:
                return False
            skill.enabled = False
            logger.info(f"[SKILL] Skill deshabilitado: {name}")
            return True

    def is_enabled(self, name: str) -> bool:
        """Retorna si el skill esta habilitado.

        Returns:
            True si el skill existe y esta habilitado, False si no existe o esta deshabilitado.
        """
        with self._lock:
            skill = self.skills.get(name)
            return skill.enabled if skill else False

    # ═══════════════════════════════════════════════════════════════════════════
    # Usage Stats
    # ═══════════════════════════════════════════════════════════════════════════

    def record_trigger(self, name: str) -> None:
        """Incrementa el counter y actualiza last_triggered para un skill."""
        with self._lock:
            skill = self.skills.get(name)
            if skill is not None:
                skill._times_triggered += 1
                skill._last_triggered = time.time()
                logger.debug(f"[SKILL] Trigger registrado: {name} (total: {skill._times_triggered})")

    def get_usage_stats(self) -> Dict[str, Dict]:
        """Returns estadisticas de uso para todos los skills.

        Returns:
            {name: {times_triggered: int, last_triggered: float|None}} for all skills.
        """
        with self._lock:
            stats = {}
            for name, skill in self.skills.items():
                stats[name] = {
                    "times_triggered": skill._times_triggered,
                    "last_triggered": skill._last_triggered,
                }
            return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # Tools Required Validation
    # ═══════════════════════════════════════════════════════════════════════════

    def _validate_tools_required(self) -> None:
        """Valida tools_required contra DynamicToolRegistry.

        Si una skill requiere herramientas que no estan disponibles,
        se loguea un warning pero NO se deshabilita (solo se baja prioridad).
        """
        if not self._tool_registry:
            return

        available_tools = set(self._tool_registry._tools.keys())

        with self._lock:
            for name, skill in self.skills.items():
                if not skill.tools_required:
                    continue

                missing = set(skill.tools_required) - available_tools
                if missing:
                    logger.warning(
                        f"[SKILL] Skill '{name}' requiere tools no disponibles: "
                        f"{missing}. Bajando prioridad de {skill.priority} a "
                        f"{max(skill.priority // 2, 1)}."
                    )
                    skill.priority = max(skill.priority // 2, 1)

    def set_tool_registry(self, tool_registry) -> None:
        """Establece el DynamicToolRegistry y valida tools_required."""
        self._tool_registry = tool_registry
        self._validate_tools_required()

    # ═══════════════════════════════════════════════════════════════════════════
    # Loading
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_all(self) -> List[str]:
        """Carga todos los skills del directorio (*.md, *.yaml, *.yml)."""
        loaded = []

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return loaded

        for ext in self.SKILL_EXTENSIONS:
            for skill_file in self.skills_dir.rglob(f"*{ext}"):
                if skill_file.name.startswith("."):
                    continue
                try:
                    skill = self._parser.parse_file(skill_file)
                    with self._lock:
                        self.skills[skill.name] = skill
                    loaded.append(skill.name)
                except SkillParseError as e:
                    logger.warning(f"[SKILL] Error cargando {skill_file.name}: {e}")
                except Exception as e:
                    logger.warning(f"[SKILL] Error inesperado en {skill_file.name}: {e}")

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

        # Validar tools_required si hay tool_registry
        if self._tool_registry:
            self._validate_tools_required()

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

            # Validar tools_required para este skill
            if self._tool_registry and skill.tools_required:
                available_tools = set(self._tool_registry._tools.keys())
                missing = set(skill.tools_required) - available_tools
                if missing:
                    logger.warning(
                        f"[SKILL] Skill '{skill.name}' requiere tools no disponibles: "
                        f"{missing}. Bajando prioridad."
                    )
                    skill.priority = max(skill.priority // 2, 1)

            return skill.name
        except Exception as e:
            logger.warning(f"[SKILL] Error recargando {file_path}: {e}")
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
        Devuelve skills habilitados que deben activarse para el texto dado.

        Args:
            text: Texto del usuario
            max_skills: Maximo numero de skills a retornar

        Returns:
            Lista de skills habilitados ordenados por score de trigger
        """
        with self._lock:
            triggered = []
            for skill in self.skills.values():
                if not skill.enabled:
                    continue
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
                "enabled_skills": sum(1 for s in self.skills.values() if s.enabled),
                "disabled_skills": sum(1 for s in self.skills.values() if not s.enabled),
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
            logger.info("[SKILL] watchdog no disponible, hot-reload deshabilitado")
            return

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)

        class SkillEventHandler(FileSystemEventHandler):
            def __init__(self, registry: "SkillRegistry"):
                self.registry = registry
                self._last_reload = 0

            def _should_process(self, event) -> bool:
                """Check if event should be processed."""
                if event.is_directory:
                    return False
                path = Path(event.src_path)
                return path.suffix.lower() in SkillRegistry.SKILL_EXTENSIONS

            def _debounce(self, path: Path) -> bool:
                """Debounce: ignorar eventos dentro de 300ms del mismo archivo."""
                now = time.time()
                key = str(path)
                last = getattr(self, "_last_reload_map", {}).get(key, 0)
                if now - last < 0.3:
                    return True  # skip
                if not hasattr(self, "_last_reload_map"):
                    self._last_reload_map = {}
                self._last_reload_map[key] = now
                return False

            def on_modified(self, event):
                if not self._should_process(event):
                    return
                if self._debounce(Path(event.src_path)):
                    return

                skill_name = self.registry.reload_file(Path(event.src_path))
                if skill_name:
                    logger.info(f"[SKILL] Hot-reload: {skill_name}")

            def on_created(self, event):
                if not self._should_process(event):
                    return
                if self._debounce(Path(event.src_path)):
                    return

                skill_name = self.registry.reload_file(Path(event.src_path))
                if skill_name:
                    logger.info(f"[SKILL] Nuevo skill detectado: {skill_name}")

            def on_deleted(self, event):
                if event.is_directory:
                    return
                path = Path(event.src_path)
                if path.suffix.lower() not in SkillRegistry.SKILL_EXTENSIONS:
                    return
                # Encontrar skill por source_file y eliminarlo
                with self.registry._lock:
                    to_remove = [
                        name
                        for name, skill in self.registry.skills.items()
                        if skill.source_file == path
                    ]
                    for name in to_remove:
                        del self.registry.skills[name]
                        logger.info(f"[SKILL] Skill eliminado: {name}")

        handler = SkillEventHandler(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.skills_dir), recursive=True)
        self._observer.start()
        logger.info(f"[SKILL] Hot-reload activo en: {self.skills_dir}")

    def stop_watching(self) -> None:
        """Detiene el file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("[SKILL] Hot-reload detenido")

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