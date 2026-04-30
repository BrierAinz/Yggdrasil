"""
Registro de proyectos para seguimiento orquestado desde Discord.
Almacena en Data/projects.json: proyectos con nombre, descripción, tareas y estado.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("projects_registry")

_DEFAULT = {"projects": []}


def _path(base_path: Path) -> Path:
    return Path(base_path) / "Data" / "projects.json"


def _load(base_path: Path) -> dict:
    p = _path(base_path)
    if not p.exists():
        return _DEFAULT.copy()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return (
            data if isinstance(data, dict) and "projects" in data else _DEFAULT.copy()
        )
    except Exception as e:
        logger.debug("projects_registry load: %s", e)
        return _DEFAULT.copy()


def _save(base_path: Path, data: dict) -> None:
    p = _path(base_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_project(base_path: Path, name: str, description: str = "") -> Dict[str, Any]:
    """Crea un proyecto y devuelve {project_id, name, message}."""
    name = (name or "").strip()
    if not name:
        return {"error": True, "response": "Indica el nombre del proyecto."}
    data = _load(base_path)
    projects = data.get("projects") or []
    for p in projects:
        if (p.get("name") or "").strip().lower() == name.lower():
            return {
                "error": True,
                "response": f"Ya existe un proyecto llamado «{name}».",
            }
    now = datetime.now(timezone.utc).isoformat()
    project_id = uuid.uuid4().hex[:12]
    project = {
        "id": project_id,
        "name": name,
        "description": (description or "").strip()[:2000],
        "status": "active",
        "tasks": [],
        "created_at": now,
        "updated_at": now,
    }
    projects.append(project)
    data["projects"] = projects
    _save(base_path, data)
    return {
        "response": f"Proyecto «{name}» creado. ID: {project_id}. Puedes añadir tareas o pedir que avance con él.",
        "data": {"project_id": project_id, "name": name},
    }


def list_projects(
    base_path: Path, status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Lista proyectos. status_filter: active|paused|done|None (todos)."""
    data = _load(base_path)
    projects = data.get("projects") or []
    if status_filter:
        projects = [
            p
            for p in projects
            if (p.get("status") or "").lower() == status_filter.lower()
        ]
    lines = []
    for p in projects:
        name = p.get("name") or "Sin nombre"
        status = p.get("status") or "active"
        tasks = p.get("tasks") or []
        pending = sum(1 for t in tasks if (t.get("status") or "pending") == "pending")
        lines.append(
            f"• **{name}** ({status}) — {len(tasks)} tareas, {pending} pendientes"
        )
    if not lines:
        return {
            "response": "No hay proyectos. Di «iniciar proyecto [nombre]» o «crear proyecto [nombre]» para crear uno.",
            "data": [],
        }
    return {"response": "\n".join(lines), "data": projects}


def get_project(
    base_path: Path, project_id: Optional[str] = None, name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Busca por id o por nombre (case-insensitive)."""
    data = _load(base_path)
    projects = data.get("projects") or []
    if project_id:
        for p in projects:
            if (p.get("id") or "").strip() == project_id.strip():
                return p
    if name:
        n = name.strip().lower()
        for p in projects:
            if (p.get("name") or "").strip().lower() == n:
                return p
    return None


def project_status(
    base_path: Path, project_id: Optional[str] = None, name: Optional[str] = None
) -> Dict[str, Any]:
    """Devuelve estado de un proyecto: nombre, tareas pendientes/en curso/terminadas."""
    proj = get_project(base_path, project_id=project_id, name=name)
    if not proj:
        return {
            "error": True,
            "response": "No encontré ese proyecto. Di «mis proyectos» para listar.",
        }
    tasks = proj.get("tasks") or []
    pending = [t for t in tasks if (t.get("status") or "pending") == "pending"]
    in_progress = [t for t in tasks if (t.get("status") or "").lower() == "in_progress"]
    done = [t for t in tasks if (t.get("status") or "").lower() == "done"]
    lines = [f"**{proj.get('name')}** — {proj.get('status', 'active')}", ""]
    if proj.get("description"):
        lines.append(
            proj["description"][:300] + ("…" if len(proj["description"]) > 300 else "")
        )
    lines.append(
        f"\nTareas: {len(pending)} pendientes, {len(in_progress)} en curso, {len(done)} hechas."
    )
    for t in pending[:15]:
        lines.append(f"  ○ {t.get('title', '?')}")
    return {"response": "\n".join(lines), "data": proj}


def add_task(
    base_path: Path,
    project_id: Optional[str],
    project_name: Optional[str],
    task_title: str,
) -> Dict[str, Any]:
    """Añade una tarea a un proyecto."""
    proj = get_project(base_path, project_id=project_id, name=project_name)
    if not proj:
        return {"error": True, "response": "No encontré ese proyecto."}
    task_title = (task_title or "").strip()
    if not task_title:
        return {"error": True, "response": "Indica el título de la tarea."}
    data = _load(base_path)
    projects = data.get("projects") or []
    for i, p in enumerate(projects):
        if p.get("id") == proj.get("id"):
            tasks = p.get("tasks") or []
            tasks.append(
                {
                    "id": len(tasks) + 1,
                    "title": task_title,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            projects[i] = {
                **p,
                "tasks": tasks,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            break
    data["projects"] = projects
    _save(base_path, data)
    return {
        "response": f"Tarea añadida a «{proj.get('name')}»: {task_title}",
        "data": {"project": proj.get("name")},
    }


def get_next_pending_task(
    base_path: Path, project_id: Optional[str], project_name: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Devuelve la primera tarea pendiente del proyecto, o None."""
    proj = get_project(base_path, project_id=project_id, name=project_name)
    if not proj:
        return None
    tasks = proj.get("tasks") or []
    for t in tasks:
        if (t.get("status") or "pending") == "pending":
            return {"project": proj, "task": t}
    return None


def advance_project_mark_done(base_path: Path, project_id: str, task_id: Any) -> None:
    """Marca una tarea como hecha (por id numérico o índice)."""
    data = _load(base_path)
    projects = data.get("projects") or []
    for p in projects:
        if p.get("id") != project_id:
            continue
        tasks = p.get("tasks") or []
        for t in tasks:
            if t.get("id") == task_id or str(t.get("id")) == str(task_id):
                t["status"] = "done"
                t["completed_at"] = datetime.now(timezone.utc).isoformat()
                break
        p["updated_at"] = datetime.now(timezone.utc).isoformat()
        break
    data["projects"] = projects
    _save(base_path, data)
