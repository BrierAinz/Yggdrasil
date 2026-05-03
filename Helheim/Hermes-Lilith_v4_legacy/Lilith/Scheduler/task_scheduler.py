"""
Lilith Task Scheduler - Sistema de tareas programadas estilo cron
Autor: Matrix Agent
"""
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from croniter import croniter

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SCHEDULER_DIR = Path(__file__).parent.parent / "Data" / "scheduler"
SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)

TASKS_FILE = SCHEDULER_DIR / "tasks.json"
HISTORY_FILE = SCHEDULER_DIR / "history.json"


class TaskStatus(Enum):
    """Estado de una tarea"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class TaskPriority(Enum):
    """Prioridad de ejecución"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class Task:
    """Representa una tarea programada"""

    def __init__(
        self,
        name: str,
        description: str,
        command: str,
        schedule: str,  # Cron expression
        enabled: bool = True,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: int = 3600,  # 1 hora por defecto
        notification_on_complete: bool = False,
        notification_on_fail: bool = True,
        task_id: Optional[str] = None,
    ):
        self.id = task_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.command = command
        self.schedule = schedule
        self.enabled = enabled
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.notification_on_complete = notification_on_complete
        self.notification_on_fail = notification_on_fail
        self.created_at = datetime.now().isoformat()
        self.last_run: Optional[str] = None
        self.next_run: Optional[str] = None
        self.last_status: Optional[TaskStatus] = None
        self.last_error: Optional[str] = None
        self.run_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "command": self.command,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "priority": self.priority.value,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "notification_on_complete": self.notification_on_complete,
            "notification_on_fail": self.notification_on_fail,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "last_status": self.last_status.value if self.last_status else None,
            "last_error": self.last_error,
            "run_count": self.run_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task = cls(
            name=data["name"],
            description=data["description"],
            command=data["command"],
            schedule=data["schedule"],
            enabled=data.get("enabled", True),
            priority=TaskPriority(data.get("priority", 2)),
            max_retries=data.get("max_retries", 3),
            timeout=data.get("timeout", 3600),
            notification_on_complete=data.get("notification_on_complete", False),
            notification_on_fail=data.get("notification_on_fail", True),
            task_id=data.get("id"),
        )
        task.created_at = data.get("created_at", datetime.now().isoformat())
        task.last_run = data.get("last_run")
        task.next_run = data.get("next_run")
        task.last_status = (
            TaskStatus(data["last_status"]) if data.get("last_status") else None
        )
        task.last_error = data.get("last_error")
        task.run_count = data.get("run_count", 0)
        return task

    def get_next_run(self) -> Optional[datetime]:
        """Calcula la próxima ejecución basada en cron"""
        try:
            cron = croniter(self.schedule, datetime.now())
            return cron.get_next(datetime)
        except Exception:
            return None

    def update_next_run(self):
        """Actualiza la próxima ejecución"""
        next_run = self.get_next_run()
        self.next_run = next_run.isoformat() if next_run else None


class TaskHistory:
    """Historial de ejecuciones de tareas"""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def add_entry(
        self,
        task_id: str,
        task_name: str,
        status: TaskStatus,
        started_at: str,
        ended_at: str,
        output: Optional[str] = None,
        error: Optional[str] = None,
        duration: float = 0.0,
    ):
        """Agrega una entrada al historial"""
        entry = {
            "task_id": task_id,
            "task_name": task_name,
            "status": status.value,
            "started_at": started_at,
            "ended_at": ended_at,
            "output": output,
            "error": error,
            "duration": duration,
        }
        self.history.insert(0, entry)  # Más reciente primero

        # Mantener solo los últimos 1000 registros
        if len(self.history) > 1000:
            self.history = self.history[:1000]

        self._save()

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene las últimas N ejecuciones"""
        return self.history[:limit]

    def get_task_history(self, task_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene el historial de una tarea específica"""
        return [h for h in self.history if h["task_id"] == task_id][:limit]


class TaskScheduler:
    """
    Scheduler principal de tareas

    Soporta expresiones cron para scheduling flexible.
    Inspirado en el sistema de cron del Yggdrasil.
    """

    # Patrones cron predefinidos
    PRESETS = {
        "minutely": "* * * * *",
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "daily_noon": "0 12 * * *",
        "daily_midnight": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "weekly_monday": "0 0 * * 1",
        "monthly": "0 0 1 * *",
        "yearly": "0 0 1 1 *",
    }

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.history = TaskHistory()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, TaskStatus, Optional[str]], None]] = []

        self._load_tasks()
        # Actualizar próximas ejecuciones
        for task in self.tasks.values():
            task.update_next_run()

    def _load_tasks(self):
        """Carga tareas desde archivo"""
        if TASKS_FILE.exists():
            try:
                with open(TASKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = Task.from_dict(task_data)
                        self.tasks[task.id] = task
            except Exception as e:
                print(f"Error cargando tareas: {e}")

    def _save_tasks(self):
        """Guarda tareas en archivo"""
        with self._lock:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"tasks": [t.to_dict() for t in self.tasks.values()]},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

    def add_task(self, task: Task) -> str:
        """Agrega una nueva tarea"""
        task.update_next_run()
        with self._lock:
            self.tasks[task.id] = task
        self._save_tasks()
        return task.id

    def create_task(
        self, name: str, description: str, command: str, schedule: str, **kwargs
    ) -> str:
        """Crea y agrega una tarea"""
        # Validar expresión cron
        try:
            croniter(schedule, datetime.now())
        except Exception as e:
            raise ValueError(f"Cron expression inválida: {e}")

        task = Task(name, description, command, schedule, **kwargs)
        return self.add_task(task)

    def remove_task(self, task_id: str) -> bool:
        """Elimina una tarea"""
        with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                self._save_tasks()
                return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """Habilita una tarea"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].enabled = True
                self.tasks[task_id].update_next_run()
                self._save_tasks()
                return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Deshabilita una tarea"""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].enabled = False
                self._save_tasks()
                return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtiene una tarea por ID"""
        return self.tasks.get(task_id)

    def list_tasks(
        self, enabled_only: bool = False, sort_by: str = "next_run"
    ) -> List[Task]:
        """Lista todas las tareas"""
        tasks = list(self.tasks.values())

        if enabled_only:
            tasks = [t for t in tasks if t.enabled]

        # Ordenar
        if sort_by == "next_run":
            tasks.sort(key=lambda t: t.next_run or "")
        elif sort_by == "name":
            tasks.sort(key=lambda t: t.name)
        elif sort_by == "priority":
            tasks.sort(key=lambda t: t.priority.value, reverse=True)

        return tasks

    def run_task_now(self, task_id: str) -> bool:
        """Ejecuta una tarea inmediatamente"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        self._execute_task(task)
        return True

    def _execute_task(self, task: Task) -> bool:
        """Ejecuta una tarea"""
        started_at = datetime.now()
        started_str = started_at.isoformat()

        # Actualizar estado
        with self._lock:
            task.last_run = started_str
            task.last_status = TaskStatus.RUNNING

        output = None
        error = None
        success = False

        try:
            # Ejecutar comando
            result = subprocess.run(
                task.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=task.timeout,
            )

            output = result.stdout
            error = result.stderr
            success = result.returncode == 0

        except subprocess.TimeoutExpired:
            error = f"Tarea excedió el timeout de {task.timeout}s"
        except Exception as e:
            error = str(e)

        # Actualizar resultado
        ended_at = datetime.now()
        ended_str = ended_at.isoformat()
        duration = (ended_at - started_at).total_seconds()

        with self._lock:
            task.last_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.last_error = error
            task.run_count += 1
            task.update_next_run()

        # Registrar en historial
        self.history.add_entry(
            task_id=task.id,
            task_name=task.name,
            status=task.last_status,
            started_at=started_str,
            ended_at=ended_str,
            output=output,
            error=error,
            duration=duration,
        )

        # Notificar callbacks
        self._notify_callbacks(task.id, task.last_status, error)

        return success

    def register_callback(
        self, callback: Callable[[str, TaskStatus, Optional[str]], None]
    ):
        """Registra un callback para notificaciones de tareas"""
        self._callbacks.append(callback)

    def _notify_callbacks(self, task_id: str, status: TaskStatus, error: Optional[str]):
        """Notifica a los callbacks registrados"""
        for callback in self._callbacks:
            try:
                callback(task_id, status, error)
            except Exception:
                pass

    def start(self):
        """Inicia el scheduler en background"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Detiene el scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        """Loop principal del scheduler"""
        while self._running:
            now = datetime.now()

            with self._lock:
                tasks_to_run = []

                for task in self.tasks.values():
                    if not task.enabled:
                        continue

                    if task.next_run:
                        try:
                            next_run = datetime.fromisoformat(task.next_run)
                            if next_run <= now:
                                tasks_to_run.append(task)
                        except Exception:
                            continue

            # Ejecutar tareas en threads separados
            for task in tasks_to_run:
                thread = threading.Thread(
                    target=self._execute_task, args=(task,), daemon=True
                )
                thread.start()

            # Dormir 30 segundos antes de la próxima verificación
            time.sleep(30)

    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado del scheduler"""
        total_tasks = len(self.tasks)
        enabled_tasks = len([t for t in self.tasks.values() if t.enabled])
        running_tasks = len(
            [t for t in self.tasks.values() if t.last_status == TaskStatus.RUNNING]
        )

        return {
            "running": self._running,
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "running_tasks": running_tasks,
            "pending_tasks": enabled_tasks - running_tasks,
            "last_check": datetime.now().isoformat(),
        }

    def format_schedule(self, schedule: str) -> str:
        """Convierte expresión cron a formato legible"""
        if schedule in self.PRESETS.values():
            for name, pattern in self.PRESETS.items():
                if pattern == schedule:
                    return name.replace("_", " ").title()

        try:
            cron = croniter(schedule, datetime.now())
            return f"Next: {cron.get_next(datetime).strftime('%Y-%m-%d %H:%M')}"
        except Exception:
            return schedule


# Instancia global
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Obtiene la instancia global del scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
