"""
Sovereign State - Tracking del estado soberano de Lilith.

Features:
- Tracking de proyectos masivos en curso
- Detección de estado "busy" de Lilith
- Métricas de carga y capacidad
- Auto-delegate decisions
"""
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .json_safe import safe_load, safe_save

logger = logging.getLogger("lilith.sovereign")


class SovereignStatus(Enum):
    """Estados de soberanía de Lilith."""

    IDLE = "idle"  # Libre, puede orquestar
    BUSY_PROJECT = "busy_project"  # Ocupada con proyecto masivo
    BUSY_DAG = "busy_dag"  # Ejecutando DAG complejo
    BUSY_INVESTIGATING = "busy_investigating"  # Investigando
    OVERLOADED = "overloaded"  # Sobrecargada, delegar todo


@dataclass
class ProjectInfo:
    """Información de un proyecto en curso."""

    project_id: str
    name: str
    started_at: float
    estimated_nodes: int
    current_nodes: int = 0
    status: str = "active"


@dataclass
class SovereignStateSnapshot:
    """Snapshot del estado soberano."""

    status: SovereignStatus
    active_projects: List[ProjectInfo]
    active_dags: int
    total_nodes_executing: int
    last_updated: float
    metrics: Dict[str, Any] = field(default_factory=dict)


class SovereignState:
    """
    Gestiona el estado soberano de Lilith.
    Determina cuándo debe delegar automáticamente por estar ocupada.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[2]
        )
        self.config = self._load_config()

        # Estado interno
        self._status = SovereignStatus.IDLE
        self._active_projects: Dict[str, ProjectInfo] = {}
        self._active_dags: Dict[str, Dict] = {}
        self._total_nodes = 0
        self._last_updated = time.time()
        self._metrics_history: List[Dict] = []

        # Configuración
        limits = self.config.get("busy_detection", {})
        self.max_concurrent_projects = limits.get("max_concurrent_projects", 2)
        self.max_dag_nodes_busy = limits.get("max_dag_nodes_busy", 10)
        self.auto_delegate_when_busy = limits.get("auto_delegate_when_busy", True)
        self.busy_timeout_seconds = limits.get("busy_timeout_seconds", 3600)  # 1 hora

        # Persistencia
        self._state_file = self.base_path / "Memory" / "sovereign_state.json"
        self._load_state()

        self._initialized = True
        logger.info(
            "[SovereignState] Inicializado. Max projects: %d, Max nodes: %d",
            self.max_concurrent_projects,
            self.max_dag_nodes_busy,
        )

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración desde sovereign_config.json."""
        config_path = self.base_path / "Config" / "sovereign_config.json"
        try:
            return safe_load(config_path, default={})
        except Exception as e:
            logger.error("[SovereignState] Error cargando config: %s", e)
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto."""
        return {
            "busy_detection": {
                "max_concurrent_projects": 2,
                "max_dag_nodes_busy": 10,
                "auto_delegate_when_busy": True,
                "busy_timeout_seconds": 3600,
            }
        }

    def _load_state(self):
        """Carga estado previo desde disco."""
        try:
            if self._state_file.exists():
                state = safe_load(self._state_file, default={})
                # Restaurar proyectos activos (si no han expirado)
                now = time.time()
                for proj_data in state.get("active_projects", []):
                    if now - proj_data.get("started_at", 0) < self.busy_timeout_seconds:
                        project = ProjectInfo(**proj_data)
                        self._active_projects[project.project_id] = project
                logger.debug(
                    "[SovereignState] Estado cargado: %d proyectos",
                    len(self._active_projects),
                )
        except Exception as e:
            logger.error("[SovereignState] Error cargando estado: %s", e)

    def _save_state(self):
        """Guarda estado actual a disco."""
        try:
            state = {
                "active_projects": [asdict(p) for p in self._active_projects.values()],
                "status": self._status.value,
                "last_saved": time.time(),
            }
            safe_save(self._state_file, state)
        except Exception as e:
            logger.error("[SovereignState] Error guardando estado: %s", e)

    def is_lilith_busy(self, complexity_score: Optional[int] = None) -> bool:
        """
        Determina si Lilith está ocupada y debería delegar.

        Args:
            complexity_score: Score de complejidad de la tarea entrante

        Returns:
            True si Lilith está ocupada y debería delegar
        """
        with self._lock:
            # Caso 1: Proyectos masivos en curso
            if len(self._active_projects) >= self.max_concurrent_projects:
                logger.debug(
                    "[SovereignState] Busy: %d proyectos activos",
                    len(self._active_projects),
                )
                return True

            # Caso 2: Muchos nodos DAG ejecutándose
            if self._total_nodes >= self.max_dag_nodes_busy:
                logger.debug(
                    "[SovereignState] Busy: %d nodos ejecutando", self._total_nodes
                )
                return True

            # Caso 3: Estado explícito de sobrecarga
            if self._status == SovereignStatus.OVERLOADED:
                logger.debug("[SovereignState] Busy: estado OVERLOADED")
                return True

            # Caso 4: Busy con proyecto y tarea entrante es simple
            if (
                self._status == SovereignStatus.BUSY_PROJECT
                and complexity_score is not None
                and complexity_score < 70
            ):
                logger.debug("[SovereignState] Busy: proyecto activo + tarea simple")
                return True

            return False

    def get_status(self) -> SovereignStatus:
        """Retorna estado actual de soberanía."""
        with self._lock:
            return self._status

    def set_status(self, status: SovereignStatus):
        """Actualiza estado de soberanía."""
        with self._lock:
            old_status = self._status
            self._status = status
            self._last_updated = time.time()
            logger.info(
                "[SovereignState] Status: %s -> %s", old_status.value, status.value
            )

    def start_project(
        self, project_id: str, name: str, estimated_nodes: int = 10
    ) -> bool:
        """
        Registra inicio de proyecto masivo.

        Returns:
            True si se pudo iniciar, False si Lilith está ocupada
        """
        with self._lock:
            if len(self._active_projects) >= self.max_concurrent_projects:
                logger.warning(
                    "[SovereignState] No se puede iniciar proyecto '%s': límite alcanzado",
                    name,
                )
                return False

            project = ProjectInfo(
                project_id=project_id,
                name=name,
                started_at=time.time(),
                estimated_nodes=estimated_nodes,
            )
            self._active_projects[project_id] = project
            self._update_status_from_projects()
            self._save_state()

            logger.info(
                "[SovereignState] Proyecto iniciado: %s (estimado: %d nodes)",
                name,
                estimated_nodes,
            )
            return True

    def end_project(self, project_id: str):
        """Registra fin de proyecto."""
        with self._lock:
            if project_id in self._active_projects:
                project = self._active_projects.pop(project_id)
                self._update_status_from_projects()
                self._save_state()
                logger.info("[SovereignState] Proyecto finalizado: %s", project.name)

    def update_project_progress(self, project_id: str, current_nodes: int):
        """Actualiza progreso de proyecto."""
        with self._lock:
            if project_id in self._active_projects:
                self._active_projects[project_id].current_nodes = current_nodes

    def start_dag(self, dag_id: str, node_count: int):
        """Registra inicio de ejecución DAG."""
        with self._lock:
            self._active_dags[dag_id] = {
                "started_at": time.time(),
                "node_count": node_count,
                "completed_nodes": 0,
            }
            self._total_nodes += node_count
            logger.debug(
                "[SovereignState] DAG iniciado: %s (%d nodes)", dag_id, node_count
            )

    def end_dag(self, dag_id: str):
        """Registra fin de ejecución DAG."""
        with self._lock:
            if dag_id in self._active_dags:
                dag_info = self._active_dags.pop(dag_id)
                self._total_nodes = max(
                    0, self._total_nodes - dag_info.get("node_count", 0)
                )
                logger.debug("[SovereignState] DAG finalizado: %s", dag_id)

    def _update_status_from_projects(self):
        """Actualiza estado basado en proyectos activos."""
        if len(self._active_projects) >= self.max_concurrent_projects:
            self._status = SovereignStatus.BUSY_PROJECT
        elif len(self._active_projects) > 0:
            self._status = SovereignStatus.BUSY_PROJECT
        elif len(self._active_dags) > 0:
            self._status = SovereignStatus.BUSY_DAG
        else:
            self._status = SovereignStatus.IDLE

    def get_snapshot(self) -> SovereignStateSnapshot:
        """Retorna snapshot del estado actual."""
        with self._lock:
            return SovereignStateSnapshot(
                status=self._status,
                active_projects=list(self._active_projects.values()),
                active_dags=len(self._active_dags),
                total_nodes_executing=self._total_nodes,
                last_updated=self._last_updated,
                metrics={
                    "max_projects": self.max_concurrent_projects,
                    "max_nodes": self.max_dag_nodes_busy,
                    "can_accept_new": len(self._active_projects)
                    < self.max_concurrent_projects,
                },
            )

    def should_delegate_task(
        self, complexity_score: int, task_description: str = ""
    ) -> tuple[bool, str]:
        """
        Decide si una tarea específica debe ser delegada.

        Returns:
            Tuple de (should_delegate, reason)
        """
        # Siempre delegar si está sobrecargada
        if self._status == SovereignStatus.OVERLOADED:
            return True, "Lilith en estado OVERLOADED"

        # Delegar si está busy y la tarea es simple
        if self.is_lilith_busy(complexity_score):
            if complexity_score < self.config.get("thresholds", {}).get(
                "lilith_busy_threshold", 70
            ):
                return (
                    True,
                    f"Lilith ocupada + tarea simple (score: {complexity_score})",
                )

        # No delegar tareas complejas incluso si está busy
        if complexity_score >= 80:
            return False, "Tarea compleja requiere atención de Lilith"

        return False, "Lilith disponible para orquestar"

    def record_metric(self, metric_name: str, value: Any):
        """Registra métrica para análisis posterior."""
        self._metrics_history.append(
            {"timestamp": time.time(), "metric": metric_name, "value": value}
        )
        # Mantener solo últimas 1000 métricas
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]

    def get_metrics(self, limit: int = 100) -> List[Dict]:
        """Retorna métricas recientes."""
        return self._metrics_history[-limit:]


# Funciones de conveniencia
_state_instance: Optional[SovereignState] = None


def get_sovereign_state(base_path: Optional[Path] = None) -> SovereignState:
    """Obtiene instancia singleton de SovereignState."""
    global _state_instance
    if _state_instance is None:
        _state_instance = SovereignState(base_path)
    return _state_instance


def is_lilith_busy(complexity_score: Optional[int] = None) -> bool:
    """Función conveniencia para verificar si Lilith está ocupada."""
    state = get_sovereign_state()
    return state.is_lilith_busy(complexity_score)


__all__ = [
    "SovereignStatus",
    "ProjectInfo",
    "SovereignStateSnapshot",
    "SovereignState",
    "get_sovereign_state",
    "is_lilith_busy",
]
