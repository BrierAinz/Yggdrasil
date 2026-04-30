"""
API endpoints para AutoMode.
Endpoints:
- POST /api/automode/start    : Iniciar tarea autónoma
- GET  /api/automode/status   : Listar tareas activas
- GET  /api/automode/status/{task_id} : Ver tarea específica
- POST /api/automode/control/{task_id} : Controlar tarea (pause/resume/stop)
"""
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/automode", tags=["automode"])

# Store de ejecutores activos (en producción usar Redis/db)
_active_executors: Dict[str, any] = {}


class AutoModeStartRequest(BaseModel):
    objective: str
    config: Dict
    plan_steps: Optional[List[Dict]] = None


class AutoModeStartResponse(BaseModel):
    task_id: str
    status: str
    message: str


class AutoModeStatusResponse(BaseModel):
    task_id: str
    status: str
    current_step: int
    total_steps: int
    progress_pct: float
    created_at: str


@router.post("/start", response_model=AutoModeStartResponse)
async def start_automode(
    request: AutoModeStartRequest, background_tasks: BackgroundTasks
):
    """
    Inicia una nueva tarea en modo autónomo.
    """
    try:
        from src.core.automode import AutoExecutor

        task_id = request.config.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id requerido en config")

        # Crear plan si no se proporcionó
        plan_steps = request.plan_steps
        if not plan_steps:
            # Generar plan básico (en producción, usar Planner)
            plan_steps = [
                {
                    "tool": "analyze",
                    "description": "Analizar objetivo",
                    "params": {"objective": request.objective},
                },
                {
                    "tool": "execute",
                    "description": "Ejecutar tarea",
                    "params": {"objective": request.objective},
                },
                {"tool": "verify", "description": "Verificar resultado", "params": {}},
            ]

        # Crear executor
        executor = AutoExecutor(task_id, request.config)
        _active_executors[task_id] = executor

        # Ejecutar en background
        background_tasks.add_task(executor.execute_task, request.objective, plan_steps)

        return AutoModeStartResponse(
            task_id=task_id,
            status="started",
            message=f"Task {task_id} iniciada en Auto-Mode",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=List[AutoModeStatusResponse])
async def list_automode_tasks():
    """
    Lista todas las tareas Auto-Mode activas.
    """
    tasks = []

    for task_id, executor in _active_executors.items():
        status = executor.get_status()
        tasks.append(
            AutoModeStatusResponse(
                task_id=task_id,
                status="running" if status["is_running"] else "stopped",
                current_step=status["current_step"],
                total_steps=status["total_steps"],
                progress_pct=status["progress_pct"],
                created_at=datetime.now().isoformat(),
            )
        )

    return tasks


@router.get("/status/{task_id}", response_model=AutoModeStatusResponse)
async def get_automode_status(task_id: str):
    """
    Obtiene estado de una tarea específica.
    """
    if task_id not in _active_executors:
        raise HTTPException(status_code=404, detail="Task not found")

    executor = _active_executors[task_id]
    status = executor.get_status()

    return AutoModeStatusResponse(
        task_id=task_id,
        status="running" if status["is_running"] else "stopped",
        current_step=status["current_step"],
        total_steps=status["total_steps"],
        progress_pct=status["progress_pct"],
        created_at=datetime.now().isoformat(),
    )


@router.post("/control/{task_id}")
async def control_automode(task_id: str, action: Dict):
    """
    Controla una tarea (pause/resume/stop/approve).
    """
    if task_id not in _active_executors:
        raise HTTPException(status_code=404, detail="Task not found")

    executor = _active_executors[task_id]
    action_type = action.get("action")

    if action_type == "pause":
        executor.pause()
        return {"task_id": task_id, "action": "paused"}

    elif action_type == "resume":
        executor.resume()
        return {"task_id": task_id, "action": "resumed"}

    elif action_type == "stop":
        executor.stop()
        del _active_executors[task_id]
        return {"task_id": task_id, "action": "stopped"}

    elif action_type == "approve":
        # Marcar paso como aprobado
        return {"task_id": task_id, "action": "approved"}

    else:
        raise HTTPException(
            status_code=400, detail=f"Acción desconocida: {action_type}"
        )


@router.get("/tasks/{task_id}/checkpoints")
async def list_checkpoints(task_id: str):
    """
    Lista checkpoints de una tarea.
    """
    try:
        from src.core.automode import CheckpointManager

        manager = CheckpointManager(task_id)
        checkpoints = manager.list_all_checkpoints()

        return {"task_id": task_id, "checkpoints": checkpoints}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
