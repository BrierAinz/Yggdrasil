"""
Workflows API - Endpoints para gestión de workflows

v4.2.8: CRUD de workflows y ejecución
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from src.core.auth import require_permission
from src.core.auth.permissions import Action, Resource
from src.core.workflows import Workflow, WorkflowStatus, get_workflow_engine

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# Models


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    trigger_config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|paused|disabled)$")
    nodes: Optional[List[Dict[str, Any]]] = None
    trigger_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowRunRequest(BaseModel):
    trigger_data: Dict[str, Any] = Field(default_factory=dict)


class NodeTemplate(BaseModel):
    type: str
    label: str
    description: str
    icon: str
    default_config: Dict[str, Any]
    input_ports: List[str]
    output_ports: List[str]


# Endpoints


@router.get("")
async def list_workflows(
    status: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=100)
):
    """Lista todos los workflows."""
    engine = get_workflow_engine()
    workflows = engine.list_workflows()

    if status:
        workflows = [w for w in workflows if w.status.value == status]

    return {
        "success": True,
        "data": [w.to_dict() for w in workflows[:limit]],
        "count": len(workflows),
    }


@router.post("")
async def create_workflow(request: WorkflowCreateRequest):
    """Crea un nuevo workflow."""
    engine = get_workflow_engine()

    workflow = engine.create_workflow(
        name=request.name,
        description=request.description,
        nodes=request.nodes,
        trigger_config=request.trigger_config,
    )

    return {"success": True, "data": workflow.to_dict(), "message": "Workflow creado"}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Obtiene un workflow por ID."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    return {"success": True, "data": workflow.to_dict()}


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest):
    """Actualiza un workflow."""
    engine = get_workflow_engine()

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    workflow = engine.update_workflow(workflow_id, **update_data)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    return {
        "success": True,
        "data": workflow.to_dict(),
        "message": "Workflow actualizado",
    }


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Elimina un workflow."""
    engine = get_workflow_engine()

    if engine.delete_workflow(workflow_id):
        return {"success": True, "message": "Workflow eliminado"}

    raise HTTPException(status_code=404, detail="Workflow no encontrado")


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, request: WorkflowRunRequest):
    """Ejecuta un workflow manualmente."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    if workflow.status != WorkflowStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow no está activo (estado: {workflow.status.value})",
        )

    execution = await engine.execute_workflow(
        workflow_id, trigger_data=request.trigger_data, triggered_by="manual"
    )

    if not execution:
        raise HTTPException(status_code=500, detail="No se pudo iniciar la ejecución")

    return {
        "success": True,
        "data": execution.to_dict(),
        "message": "Workflow iniciado",
    }


@router.get("/{workflow_id}/runs")
async def list_workflow_runs(workflow_id: str, limit: int = Query(20, ge=1, le=100)):
    """Lista ejecuciones de un workflow."""
    engine = get_workflow_engine()

    workflow = engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    executions = engine.list_executions(workflow_id=workflow_id, limit=limit)

    return {
        "success": True,
        "data": [e.to_dict() for e in executions],
        "count": len(executions),
    }


@router.get("/{workflow_id}/runs/{execution_id}")
async def get_execution(workflow_id: str, execution_id: str):
    """Obtiene detalle de una ejecución."""
    engine = get_workflow_engine()

    execution = engine.get_execution(execution_id)
    if not execution or execution.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    return {"success": True, "data": execution.to_dict()}


@router.post("/{workflow_id}/runs/{execution_id}/cancel")
async def cancel_execution(workflow_id: str, execution_id: str):
    """Cancela una ejecución en curso."""
    engine = get_workflow_engine()

    execution = engine.get_execution(execution_id)
    if not execution or execution.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")

    if engine.cancel_execution(execution_id):
        return {"success": True, "message": "Ejecución cancelada"}

    raise HTTPException(
        status_code=400, detail="No se pudo cancelar (ejecución no está activa)"
    )


# Templates y utilidades


@router.get("/templates/nodes")
async def get_node_templates():
    """Obtiene templates de nodos disponibles."""
    templates = [
        {
            "type": "trigger",
            "label": "Trigger",
            "description": "Inicia el workflow",
            "icon": "play",
            "default_config": {"trigger_type": "manual"},
            "input_ports": [],
            "output_ports": ["out"],
        },
        {
            "type": "action",
            "label": "Acción",
            "description": "Ejecuta una acción",
            "icon": "zap",
            "default_config": {
                "action_type": "log",
                "action_config": {
                    "event_type": "workflow.action",
                    "message": "Acción ejecutada",
                },
            },
            "input_ports": ["in"],
            "output_ports": ["out"],
        },
        {
            "type": "condition",
            "label": "Condición",
            "description": "Bifurca el flujo según condición",
            "icon": "git-branch",
            "default_config": {
                "condition_type": "equals",
                "condition_config": {"left": "data.value", "right": "expected"},
                "true_branch": [],
                "false_branch": [],
            },
            "input_ports": ["in"],
            "output_ports": ["true", "false"],
        },
        {
            "type": "delay",
            "label": "Delay",
            "description": "Pausa la ejecución",
            "icon": "clock",
            "default_config": {"delay_seconds": 5},
            "input_ports": ["in"],
            "output_ports": ["out"],
        },
    ]

    return {"success": True, "data": templates}


@router.get("/templates/actions")
async def get_action_templates():
    """Obtiene tipos de acciones disponibles."""
    actions = [
        {
            "value": "webhook",
            "label": "Enviar Webhook",
            "description": "Envía una petición HTTP",
            "icon": "globe",
            "config_schema": {
                "url": {"type": "string", "required": True},
                "payload": {"type": "object", "default": {}},
            },
        },
        {
            "value": "notification",
            "label": "Notificación",
            "description": "Envía notificación (Discord, etc)",
            "icon": "bell",
            "config_schema": {
                "channel": {"type": "string", "default": "discord"},
                "message": {"type": "string", "required": True},
            },
        },
        {
            "value": "tool",
            "label": "Ejecutar Tool",
            "description": "Ejecuta una herramienta del sistema",
            "icon": "tool",
            "config_schema": {
                "tool_name": {"type": "string", "required": True},
                "params": {"type": "object", "default": {}},
            },
        },
        {
            "value": "cache_update",
            "label": "Actualizar Caché",
            "description": "Actualiza una entrada de caché",
            "icon": "database",
            "config_schema": {
                "key": {"type": "string", "required": True},
                "value": {"type": "any", "required": True},
                "namespace": {"type": "string", "default": "workflows"},
                "ttl": {"type": "integer", "default": 300},
            },
        },
        {
            "value": "create_task",
            "label": "Crear Tarea",
            "description": "Crea una tarea en el sistema",
            "icon": "check-square",
            "config_schema": {
                "title": {"type": "string", "required": True},
                "description": {"type": "string", "default": ""},
                "assignee": {"type": "string"},
            },
        },
        {
            "value": "log",
            "label": "Log Evento",
            "description": "Registra un evento en audit trail",
            "icon": "file-text",
            "config_schema": {
                "event_type": {"type": "string", "default": "workflow.action"},
                "message": {"type": "string", "required": True},
            },
        },
    ]

    return {"success": True, "data": actions}


@router.get("/conditions/operators")
async def get_condition_operators():
    """Obtiene operadores de condición disponibles."""
    from src.core.workflows.conditions import ConditionEvaluator

    evaluator = ConditionEvaluator()

    return {"success": True, "data": evaluator.get_available_operators()}


# Endpoints protegidos


@router.post("/{workflow_id}/activate")
async def activate_workflow(workflow_id: str):
    """Activa un workflow (lo pone en estado 'active')."""
    engine = get_workflow_engine()

    workflow = engine.update_workflow(workflow_id, status="active")
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    return {"success": True, "data": workflow.to_dict(), "message": "Workflow activado"}


@router.post("/{workflow_id}/pause")
async def pause_workflow(workflow_id: str):
    """Pausa un workflow."""
    engine = get_workflow_engine()

    workflow = engine.update_workflow(workflow_id, status="paused")
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")

    return {"success": True, "data": workflow.to_dict(), "message": "Workflow pausado"}
