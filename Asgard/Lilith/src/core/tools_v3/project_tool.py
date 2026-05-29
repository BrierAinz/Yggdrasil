"""
Lilith 3.0 — Tool: gestión y seguimiento de proyectos (orquestación desde Discord).
Acciones: create, list, status, add_task, advance.
"""
from pathlib import Path
from typing import Any, Dict

from ..projects_registry import (
    add_task,
    advance_project_mark_done,
    create_project,
    get_next_pending_task,
    list_projects,
    project_status,
)
from .protocol import LilithTool, ToolResult


class ProjectTool(LilithTool):
    """Crea, lista, consulta estado y avanza proyectos (seguimiento orquestado)."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "project"

    def get_description(self) -> str:
        return "Gestionar proyectos: crear, listar, ver estado, añadir tareas, avanzar con la siguiente tarea."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "action": "create | list | status | add_task | advance",
            "name": "nombre del proyecto (para create, status, add_task, advance)",
            "description": "descripción (solo create)",
            "task_title": "título de la tarea (solo add_task)",
            "project_id": "id del proyecto (opcional, alternativo a name)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        action = (params.get("action") or "list").strip().lower()
        name = (params.get("name") or "").strip()
        description = (params.get("description") or "").strip()
        task_title = (params.get("task_title") or "").strip()
        project_id = (params.get("project_id") or "").strip() or None

        if action == "create":
            return create_project(self._root, name, description)
        if action == "list":
            return list_projects(self._root, status_filter=params.get("status"))
        if action == "status":
            return project_status(self._root, project_id=project_id, name=name or None)
        if action == "add_task":
            return add_task(self._root, project_id, name or None, task_title)
        if action == "advance":
            next_info = get_next_pending_task(self._root, project_id, name or None)
            if not next_info:
                proj_name = name or project_id or "?"
                return {
                    "response": f"No hay tareas pendientes en «{proj_name}» o el proyecto no existe. Añade tareas o comprueba el estado.",
                    "data": None,
                }
            proj = next_info["project"]
            task = next_info["task"]
            task_title = task.get("title", "Sin título")
            # Respuesta para el usuario y para encadenar al siguiente paso (ej. delegate_lucifer)
            msg = (
                f"Siguiente tarea del proyecto **{proj.get('name')}**: {task_title}. "
                "Puedo desarrollarla o desglosarla con el agente."
            )
            return {
                "response": msg,
                "data": {
                    "project_id": proj.get("id"),
                    "project_name": proj.get("name"),
                    "task_id": task.get("id"),
                    "task_title": task_title,
                },
            }
        return {
            "response": f"Acción «{action}» no reconocida. Usa: create, list, status, add_task, advance.",
            "error": True,
        }
