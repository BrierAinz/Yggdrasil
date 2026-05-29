"""
TaskTracker - Sistema de planificaciÃ³n y seguimiento de tareas autÃ³nomo
Permite a Lilith crear, ejecutar y monitorear planes multi-paso
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("TaskTracker")


class TaskStatus(str, Enum):
    """Estados de una tarea"""

    PENDING = "pending"  # Esperando para ejecutar
    RUNNING = "running"  # En ejecuciÃ³n
    COMPLETED = "completed"  # Completada exitosamente
    FAILED = "failed"  # FallÃ³
    CANCELLED = "cancelled"  # Cancelada por usuario
    BLOCKED = "blocked"  # Bloqueada por dependencias


class TaskPriority(str, Enum):
    """Prioridades de tarea"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """Representa una tarea individual"""

    id: str
    name: str
    description: str
    tool: str  # Herramienta a usar
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM

    # Dependencias
    depends_on: List[str] = field(default_factory=list)

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    # Resultado
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    progress: int = 0  # 0-100
    notes: List[str] = field(default_factory=list)


@dataclass
class TaskPlan:
    """Plan completo de tareas"""

    id: str
    name: str
    description: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskTracker:
    """
    Sistema autÃ³nomo de seguimiento de tareas.

    Capacidades:
    - Crear planes multi-paso con dependencias
    - Ejecutar tareas secuencialmente o en paralelo
    - Monitorear progreso en tiempo real
    - Manejar reintentos automÃ¡ticos
    - Persistir estado entre sesiones
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.name = "TaskTracker"
        self.description = "PlanificaciÃ³n y seguimiento autÃ³nomo de tareas"
        self.version = "1.0.0"

        # Almacenamiento de planes
        self.plans: Dict[str, TaskPlan] = {}
        self.active_plan: Optional[str] = None

        # Callbacks para notificaciones
        self.on_task_start: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        self.on_task_fail: Optional[Callable] = None
        self.on_progress: Optional[Callable] = None

        # Persistencia
        self.storage_path = storage_path or Path.home() / ".Lilith" / "tasks"
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Cargar planes guardados
        self._load_plans()

        logger.info(f"TaskTracker initialized with storage at {self.storage_path}")

    def check_dependencies(self) -> bool:
        """Verificar dependencias"""
        return True

    # === CRUD de Planes ===

    def create_plan(
        self, name: str, description: str, context: Optional[Dict] = None
    ) -> str:
        """
        Crear un nuevo plan de tareas

        Args:
            name: Nombre del plan
            description: DescripciÃ³n
            context: Contexto adicional

        Returns:
            ID del plan creado
        """
        plan_id = str(uuid.uuid4())[:8]
        plan = TaskPlan(
            id=plan_id, name=name, description=description, context=context or {}
        )

        self.plans[plan_id] = plan
        self._save_plan(plan)

        logger.info(f"Created plan {plan_id}: {name}")
        return plan_id

    def add_task(
        self,
        plan_id: str,
        name: str,
        description: str,
        tool: str,
        parameters: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> str:
        """
        Agregar una tarea a un plan

        Args:
            plan_id: ID del plan
            name: Nombre de la tarea
            description: DescripciÃ³n
            tool: Herramienta a usar
            parameters: ParÃ¡metros para la herramienta
            depends_on: IDs de tareas que deben completarse primero
            priority: Prioridad

        Returns:
            ID de la tarea creada
        """
        if plan_id not in self.plans:
            raise ValueError(f"Plan {plan_id} no encontrado")

        task_id = f"{plan_id}_{len(self.plans[plan_id].tasks)}"
        task = Task(
            id=task_id,
            name=name,
            description=description,
            tool=tool,
            parameters=parameters,
            depends_on=depends_on or [],
            priority=priority,
        )

        self.plans[plan_id].tasks[task_id] = task
        self._save_plan(self.plans[plan_id])

        logger.info(f"Added task {task_id} to plan {plan_id}")
        return task_id

    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Obtener un plan por ID"""
        return self.plans.get(plan_id)

    def get_task(self, plan_id: str, task_id: str) -> Optional[Task]:
        """Obtener una tarea especÃ­fica"""
        plan = self.plans.get(plan_id)
        if plan:
            return plan.tasks.get(task_id)
        return None

    def list_plans(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """Listar todos los planes"""
        plans = []
        for plan_id, plan in self.plans.items():
            if status is None or plan.status == status:
                plans.append(
                    {
                        "id": plan_id,
                        "name": plan.name,
                        "description": plan.description,
                        "status": plan.status.value,
                        "task_count": len(plan.tasks),
                        "created_at": plan.created_at,
                    }
                )
        return plans

    def delete_plan(self, plan_id: str) -> bool:
        """Eliminar un plan"""
        if plan_id in self.plans:
            del self.plans[plan_id]
            # Eliminar archivo
            plan_file = self.storage_path / f"{plan_id}.json"
            if plan_file.exists():
                plan_file.unlink()
            return True
        return False

    # === EjecuciÃ³n ===

    async def execute_plan(
        self, plan_id: str, tool_registry: Optional[Any] = None, sequential: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecutar un plan completo

        Args:
            plan_id: ID del plan
            tool_registry: Registro de herramientas para ejecuciÃ³n
            sequential: Si True, ejecuta secuencialmente; si False, en paralelo donde sea posible

        Returns:
            Resultado de la ejecuciÃ³n
        """
        if plan_id not in self.plans:
            return {"success": False, "error": f"Plan {plan_id} no encontrado"}

        plan = self.plans[plan_id]
        self.active_plan = plan_id
        plan.status = TaskStatus.RUNNING
        plan.started_at = time.time()

        logger.info(f"Executing plan {plan_id}: {plan.name}")

        try:
            if sequential:
                await self._execute_sequential(plan, tool_registry)
            else:
                await self._execute_parallel(plan, tool_registry)

            # Verificar resultado final
            failed_tasks = [
                t for t in plan.tasks.values() if t.status == TaskStatus.FAILED
            ]

            if failed_tasks:
                plan.status = TaskStatus.FAILED
                return {
                    "success": False,
                    "plan_id": plan_id,
                    "failed_tasks": len(failed_tasks),
                    "message": f"Plan completado con {len(failed_tasks)} tareas fallidas",
                }
            else:
                plan.status = TaskStatus.COMPLETED
                plan.completed_at = time.time()
                return {
                    "success": True,
                    "plan_id": plan_id,
                    "completed_tasks": len(plan.tasks),
                    "duration": plan.completed_at - plan.started_at,
                    "message": "Plan completado exitosamente",
                }

        except Exception as e:
            plan.status = TaskStatus.FAILED
            logger.error(f"Error executing plan {plan_id}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            self._save_plan(plan)
            if self.active_plan == plan_id:
                self.active_plan = None

    async def _execute_sequential(self, plan: TaskPlan, tool_registry: Optional[Any]):
        """Ejecutar tareas secuencialmente respetando dependencias"""
        completed = set()

        while len(completed) < len(plan.tasks):
            # Encontrar tareas listas para ejecutar
            ready_tasks = []
            for task_id, task in plan.tasks.items():
                if task_id in completed:
                    continue
                if task.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED]:
                    completed.add(task_id)
                    continue

                # Verificar dependencias
                deps_satisfied = all(
                    dep in completed
                    or plan.tasks.get(dep, Task("", "", "", "")).status
                    == TaskStatus.COMPLETED
                    for dep in task.depends_on
                )

                if deps_satisfied:
                    ready_tasks.append(task)

            if not ready_tasks:
                # Verificar si quedan tareas bloqueadas
                remaining = [t for t in plan.tasks.values() if t.id not in completed]
                if remaining:
                    logger.warning(
                        f"Tasks remaining but none ready: {[t.id for t in remaining]}"
                    )
                    for task in remaining:
                        task.status = TaskStatus.BLOCKED
                break

            # Ordenar por prioridad
            priority_order = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            ready_tasks.sort(key=lambda t: priority_order.get(t.priority, 2))

            # Ejecutar la primera tarea lista
            task = ready_tasks[0]
            await self._execute_task(task, plan, tool_registry)
            completed.add(task.id)

            # Notificar progreso
            progress = int(len(completed) / len(plan.tasks) * 100)
            if self.on_progress:
                await self.on_progress(plan.id, progress)

    async def _execute_parallel(self, plan: TaskPlan, tool_registry: Optional[Any]):
        """Ejecutar tareas en paralelo cuando sea posible"""
        # ImplementaciÃ³n simplificada - ejecuta en batches
        completed = set()
        running = set()

        async def run_task_batch(tasks: List[Task]):
            """Ejecutar un batch de tareas"""
            coroutines = [
                self._execute_task(task, plan, tool_registry) for task in tasks
            ]
            await asyncio.gather(*coroutines, return_exceptions=True)
            for task in tasks:
                completed.add(task.id)
                running.discard(task.id)

        while len(completed) < len(plan.tasks):
            # Encontrar tareas listas
            ready_tasks = []
            for task_id, task in plan.tasks.items():
                if task_id in completed or task_id in running:
                    continue

                deps_satisfied = all(
                    dep in completed
                    or plan.tasks.get(dep, Task("", "", "", "")).status
                    == TaskStatus.COMPLETED
                    for dep in task.depends_on
                )

                if deps_satisfied:
                    ready_tasks.append(task)

            if not ready_tasks:
                # Esperar a que terminen las tareas en ejecuciÃ³n
                if running:
                    await asyncio.sleep(0.1)
                    continue
                break

            # Limitar concurrencia
            batch = ready_tasks[:5]  # MÃ¡ximo 5 tareas simultÃ¡neas
            for task in batch:
                running.add(task.id)

            await run_task_batch(batch)

    async def _execute_task(
        self, task: Task, plan: TaskPlan, tool_registry: Optional[Any]
    ):
        """Ejecutar una tarea individual"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        logger.info(f"Executing task {task.id}: {task.name}")

        # Notificar inicio
        if self.on_task_start:
            await self.on_task_start(plan.id, task.id, task.name)

        try:
            # Ejecutar la herramienta
            if tool_registry:
                tool = tool_registry.get_tool(task.tool)
                if tool:
                    # Ejecutar herramienta
                    if hasattr(tool, "execute"):
                        result = await tool.execute(**task.parameters)
                    else:
                        result = {
                            "success": False,
                            "error": f"Tool {task.tool} no tiene mÃ©todo execute",
                        }
                else:
                    result = {
                        "success": False,
                        "error": f"Tool {task.tool} no encontrada",
                    }
            else:
                # Simular ejecuciÃ³n (para testing)
                await asyncio.sleep(0.5)
                result = {"success": True, "message": f"Task {task.name} simulated"}

            task.result = result

            if result.get("success"):
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                logger.info(f"Task {task.id} completed successfully")

                if self.on_task_complete:
                    await self.on_task_complete(plan.id, task.id, result)
            else:
                raise Exception(result.get("error", "Unknown error"))

        except Exception as e:
            task.error_message = str(e)
            task.retry_count += 1

            if task.retry_count < task.max_retries:
                logger.warning(
                    f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries})"
                )
                task.status = TaskStatus.PENDING
                await asyncio.sleep(1)  # Esperar antes de reintentar
                await self._execute_task(task, plan, tool_registry)
            else:
                task.status = TaskStatus.FAILED
                logger.error(
                    f"Task {task.id} failed after {task.max_retries} retries: {e}"
                )

                if self.on_task_fail:
                    await self.on_task_fail(plan.id, task.id, str(e))

        finally:
            self._save_plan(plan)

    async def execute_single_task(
        self, plan_id: str, task_id: str, tool_registry: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Ejecutar una sola tarea especÃ­fica"""
        task = self.get_task(plan_id, task_id)
        if not task:
            return {"success": False, "error": "Tarea no encontrada"}

        plan = self.plans.get(plan_id)
        await self._execute_task(task, plan, tool_registry)

        return {
            "success": task.status == TaskStatus.COMPLETED,
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
        }

    # === Utilidades ===

    def get_plan_summary(self, plan_id: str) -> Dict[str, Any]:
        """Obtener resumen de un plan"""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"success": False, "error": "Plan no encontrado"}

        tasks_by_status = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "blocked": 0,
        }

        for task in plan.tasks.values():
            tasks_by_status[task.status.value] += 1

        total = len(plan.tasks)
        completed = tasks_by_status["completed"]
        progress = int(completed / total * 100) if total > 0 else 0

        return {
            "success": True,
            "plan_id": plan_id,
            "name": plan.name,
            "description": plan.description,
            "status": plan.status.value,
            "progress": progress,
            "tasks_by_status": tasks_by_status,
            "total_tasks": total,
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
        }

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancelar un plan en ejecuciÃ³n"""
        plan = self.plans.get(plan_id)
        if not plan:
            return False

        plan.status = TaskStatus.CANCELLED
        for task in plan.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.BLOCKED]:
                task.status = TaskStatus.CANCELLED

        self._save_plan(plan)
        return True

    def retry_failed_tasks(self, plan_id: str) -> List[str]:
        """Reintentar tareas fallidas de un plan"""
        plan = self.plans.get(plan_id)
        if not plan:
            return []

        retried = []
        for task in plan.tasks.values():
            if task.status == TaskStatus.FAILED:
                task.status = TaskStatus.PENDING
                task.retry_count = 0
                task.error_message = None
                task.result = None
                retried.append(task.id)

        if retried:
            plan.status = TaskStatus.PENDING
            self._save_plan(plan)

        return retried

    # === Persistencia ===

    def _save_plan(self, plan: TaskPlan):
        """Guardar plan a disco"""
        try:
            plan_file = self.storage_path / f"{plan.id}.json"

            # Convertir a dict serializable
            data = {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status.value,
                "created_at": plan.created_at,
                "started_at": plan.started_at,
                "completed_at": plan.completed_at,
                "context": plan.context,
                "metadata": plan.metadata,
                "tasks": {},
            }

            for task_id, task in plan.tasks.items():
                data["tasks"][task_id] = {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description,
                    "tool": task.tool,
                    "parameters": task.parameters,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "depends_on": task.depends_on,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "result": task.result,
                    "error_message": task.error_message,
                    "retry_count": task.retry_count,
                    "max_retries": task.max_retries,
                    "progress": task.progress,
                    "notes": task.notes,
                }

            with open(plan_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving plan {plan.id}: {e}")

    def _load_plans(self):
        """Cargar planes desde disco"""
        try:
            for plan_file in self.storage_path.glob("*.json"):
                try:
                    with open(plan_file, "r") as f:
                        data = json.load(f)

                    plan = TaskPlan(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"],
                        status=TaskStatus(data["status"]),
                        created_at=data["created_at"],
                        started_at=data.get("started_at"),
                        completed_at=data.get("completed_at"),
                        context=data.get("context", {}),
                        metadata=data.get("metadata", {}),
                    )

                    for task_id, task_data in data.get("tasks", {}).items():
                        task = Task(
                            id=task_data["id"],
                            name=task_data["name"],
                            description=task_data["description"],
                            tool=task_data["tool"],
                            parameters=task_data["parameters"],
                            status=TaskStatus(task_data["status"]),
                            priority=TaskPriority(task_data["priority"]),
                            depends_on=task_data["depends_on"],
                            created_at=task_data["created_at"],
                            started_at=task_data.get("started_at"),
                            completed_at=task_data.get("completed_at"),
                            result=task_data.get("result"),
                            error_message=task_data.get("error_message"),
                            retry_count=task_data.get("retry_count", 0),
                            max_retries=task_data.get("max_retries", 3),
                            progress=task_data.get("progress", 0),
                            notes=task_data.get("notes", []),
                        )
                        plan.tasks[task_id] = task

                    self.plans[plan.id] = plan

                except Exception as e:
                    logger.warning(f"Error loading plan {plan_file}: {e}")

        except Exception as e:
            logger.error(f"Error loading plans: {e}")

    # === MÃ©todo principal ===

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecutar una acciÃ³n del TaskTracker

        Args:
            action: create_plan, add_task, execute_plan, get_summary, list_plans, etc.
            **kwargs: ParÃ¡metros especÃ­ficos
        """
        if action == "create_plan":
            plan_id = self.create_plan(
                kwargs.get("name", "Unnamed Plan"),
                kwargs.get("description", ""),
                kwargs.get("context"),
            )
            return {"success": True, "plan_id": plan_id}

        elif action == "add_task":
            try:
                task_id = self.add_task(
                    kwargs["plan_id"],
                    kwargs["name"],
                    kwargs["description"],
                    kwargs["tool"],
                    kwargs.get("parameters", {}),
                    kwargs.get("depends_on"),
                    TaskPriority(kwargs.get("priority", "medium")),
                )
                return {"success": True, "task_id": task_id}
            except Exception as e:
                return {"success": False, "error": str(e)}

        elif action == "execute_plan":
            return await self.execute_plan(
                kwargs["plan_id"],
                kwargs.get("tool_registry"),
                kwargs.get("sequential", True),
            )

        elif action == "get_summary":
            return self.get_plan_summary(kwargs["plan_id"])

        elif action == "list_plans":
            status = kwargs.get("status")
            if status:
                status = TaskStatus(status)
            return {"success": True, "plans": self.list_plans(status)}

        elif action == "cancel_plan":
            success = self.cancel_plan(kwargs["plan_id"])
            return {"success": success}

        elif action == "retry_failed":
            retried = self.retry_failed_tasks(kwargs["plan_id"])
            return {"success": True, "retried_tasks": retried}

        elif action == "delete_plan":
            success = self.delete_plan(kwargs["plan_id"])
            return {"success": success}

        return {"success": False, "error": f"AcciÃ³n no vÃ¡lida: {action}"}


# === Testing ===
if __name__ == "__main__":

    async def test():
        print("=" * 60)
        print("TaskTracker - Test Suite")
        print("=" * 60)

        tracker = TaskTracker()

        # Test 1: Crear plan
        print("\n[Test 1] Crear plan")
        result = await tracker.execute(
            "create_plan",
            name="Setup Project",
            description="Configurar un nuevo proyecto Python",
            context={"project_name": "MyApp"},
        )
        plan_id = result["plan_id"]
        print(f"âœ“ Plan creado: {plan_id}")

        # Test 2: Agregar tareas
        print("\n[Test 2] Agregar tareas")

        task1 = await tracker.execute(
            "add_task",
            plan_id=plan_id,
            name="Crear directorio",
            description="Crear estructura de directorios",
            tool="FileManager",
            parameters={"action": "mkdir", "dir_path": "myapp"},
            priority="high",
        )
        print(f"âœ“ Tarea 1 agregada: {task1['task_id']}")

        task2 = await tracker.execute(
            "add_task",
            plan_id=plan_id,
            name="Crear README",
            description="Crear archivo README.md",
            tool="FileManager",
            parameters={
                "action": "write",
                "file_path": "README.md",
                "content": "# MyApp",
            },
            priority="medium",
        )
        print(f"âœ“ Tarea 2 agregada: {task2['task_id']}")

        task3 = await tracker.execute(
            "add_task",
            plan_id=plan_id,
            name="Inicializar git",
            description="Inicializar repositorio git",
            tool="GitTools",
            parameters={"command": "init"},
            priority="low",
        )
        print(f"âœ“ Tarea 3 agregada: {task3['task_id']}")

        # Test 3: Obtener resumen
        print("\n[Test 3] Resumen del plan")
        summary = await tracker.execute("get_summary", plan_id=plan_id)
        print(f"âœ“ Total tareas: {summary['total_tasks']}")
        print(f"âœ“ Progreso: {summary['progress']}%")

        # Test 4: Listar planes
        print("\n[Test 4] Listar planes")
        plans = await tracker.execute("list_plans")
        print(f"âœ“ Total planes: {len(plans['plans'])}")

        # Test 5: Eliminar plan
        print("\n[Test 5] Eliminar plan")
        result = await tracker.execute("delete_plan", plan_id=plan_id)
        print(f"âœ“ Plan eliminado: {result['success']}")

        print("\n" + "=" * 60)
        print("Tests completados!")
        print("=" * 60)

    asyncio.run(test())
