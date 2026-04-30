"""
Lilith v2.3 — Fase C: Monitor de tareas auto_mode.
Persiste estado en Memory/auto_mode/tasks.json.
Estados: pending | planning | running | paused | done | failed
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TaskMonitor")

VALID_STATES = {"pending", "planning", "running", "paused", "done", "failed"}


class TaskMonitor:
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        self.base_path = Path(base_path)
        for name in ("Memory", "memory"):
            self._dir = self.base_path / name / "auto_mode"
            if self.base_path.joinpath(name).exists():
                break
        else:
            self._dir = self.base_path / "Memory" / "auto_mode"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "tasks.json"

    def _load(self) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("TaskMonitor load: %s", e)
            return []

    def _save(self, tasks: List[Dict[str, Any]]) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("TaskMonitor save: %s", e)

    def create_task(self, objetivo: str, session_id: Optional[str] = None) -> str:
        """Crea una tarea en estado pending. Retorna task_id."""
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "objetivo": objetivo,
            "session_id": session_id or "",
            "estado": "pending",
            "plan": None,
            "resultados": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        tasks = self._load()
        tasks.append(task)
        self._save(tasks)
        return task_id

    def update_task(
        self,
        task_id: str,
        estado: Optional[str] = None,
        plan: Optional[Dict] = None,
        resultados: Optional[List] = None,
        **kwargs,
    ) -> bool:
        """Actualiza campos de la tarea. estado debe ser uno de VALID_STATES."""
        tasks = self._load()
        for t in tasks:
            if t.get("task_id") == task_id:
                if estado and estado in VALID_STATES:
                    t["estado"] = estado
                if plan is not None:
                    t["plan"] = plan
                if resultados is not None:
                    t["resultados"] = resultados
                for k, v in kwargs.items():
                    t[k] = v
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(tasks)
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        tasks = self._load()
        for t in tasks:
            if t.get("task_id") == task_id:
                return t
        return None

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Tareas en planning, running o paused."""
        tasks = self._load()
        return [
            t for t in tasks if t.get("estado") in ("planning", "running", "paused")
        ]

    def pause_task(self, task_id: str) -> bool:
        return self.update_task(task_id, estado="paused")

    def resume_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task and task.get("estado") == "paused":
            return self.update_task(task_id, estado="running")
        return False
