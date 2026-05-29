"""
PC Agent Tools — Wrappers de PCAgent para el ToolRegistryV3.
Exponen las operaciones del PC Agent como LilithTools estándar,
manejando la respuesta de confirmación de PCAgentResult.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("lilith.pc_agent_tools")

# PATH_ALIASES: resolución de nombres cortos comunes
PATH_ALIASES: Dict[str, str] = {
    "proyectos": r"D:\Proyectos",
    "projects": r"D:\Proyectos",
    "lilith": r"D:\Proyectos\Yggdrasil\Asgard\Lilith",
    "yggdrasil": r"D:\Proyectos\Yggdrasil",
    "ragnarok": r"D:\Proyectos\Ragnarok",
    "core": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core",
    "backend": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Backend",
    "config": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Config",
    "docs": r"D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Docs",
    "desktop": r"%USERPROFILE%\Desktop",
    "escritorio": r"%USERPROFILE%\Desktop",
    "downloads": r"%USERPROFILE%\Downloads",
    "descargas": r"%USERPROFILE%\Downloads",
    "documents": r"%USERPROFILE%\Documents",
    "documentos": r"%USERPROFILE%\Documents",
}


def _resolve_alias(path: str) -> str:
    import os

    if not path:
        return path
    lower = path.lower().strip()
    for alias, real in PATH_ALIASES.items():
        if (
            lower == alias
            or lower.startswith(alias + "/")
            or lower.startswith(alias + "\\")
        ):
            # Expandir variables de entorno como %USERPROFILE%
            expanded = os.path.expandvars(real)
            return expanded + path[len(alias) :]
    # También expandir variables si el path no es un alias
    return os.path.expandvars(path)


def _pc_result_to_tool_result(pc_result) -> ToolResult:
    """Convierte PCAgentResult → ToolResult estándar."""
    if pc_result.requires_confirm:
        return {
            "response": pc_result.output or "(requiere confirmación)",
            "requires_confirmation": True,
            "confirm_token": pc_result.confirm_token,
            "error": False,
        }
    if not pc_result.success:
        return {"response": pc_result.output or "(error)", "error": True}
    return {"response": pc_result.output or "(OK)", "error": False}


def _get_pc(project_root: Path):
    from src.core.pc_agent import PCAgent

    return PCAgent(project_root)


# ─── Tool: pc_list ────────────────────────────────────────────────────────────


class PCListTool(LilithTool):
    """Lista el contenido de una carpeta del sistema."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_list"

    def get_description(self) -> str:
        return "Lista el contenido de una carpeta del sistema del owner."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"path": "string — ruta de la carpeta a listar"}

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = _resolve_alias(str(params.get("path") or "").strip())
        if not path:
            return {"response": "Falta el parámetro 'path'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).list_dir(path))
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_mkdir ───────────────────────────────────────────────────────────


class PCMkdirTool(LilithTool):
    """Crea una carpeta en el sistema del owner."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_mkdir"

    def get_description(self) -> str:
        return "Crea una carpeta (o árbol de carpetas) en el sistema del owner."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"path": "string — ruta completa de la carpeta a crear"}

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = _resolve_alias(str(params.get("path") or "").strip())
        if not path:
            return {"response": "Falta el parámetro 'path'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).make_dir(path))
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_move ────────────────────────────────────────────────────────────


class PCMoveTool(LilithTool):
    """Mueve un archivo o carpeta."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_move"

    def get_description(self) -> str:
        return "Mueve un archivo o carpeta de source a destination."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "source": "string — ruta origen",
            "destination": "string — ruta destino",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        src = _resolve_alias(
            str(params.get("source") or params.get("src") or "").strip()
        )
        dst = _resolve_alias(
            str(params.get("destination") or params.get("dst") or "").strip()
        )
        if not src or not dst:
            return {"response": "Faltan 'source' y/o 'destination'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).move_path(src, dst))
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_copy ────────────────────────────────────────────────────────────


class PCCopyTool(LilithTool):
    """Copia un archivo o carpeta."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_copy"

    def get_description(self) -> str:
        return "Copia un archivo o carpeta de source a destination."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "source": "string — ruta origen",
            "destination": "string — ruta destino",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        src = _resolve_alias(
            str(params.get("source") or params.get("src") or "").strip()
        )
        dst = _resolve_alias(
            str(params.get("destination") or params.get("dst") or "").strip()
        )
        if not src or not dst:
            return {"response": "Faltan 'source' y/o 'destination'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).copy_path(src, dst))
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_delete ──────────────────────────────────────────────────────────


class PCDeleteTool(LilithTool):
    """Elimina un archivo o carpeta (requiere confirmación del owner)."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_delete"

    def get_description(self) -> str:
        return "Elimina un archivo o carpeta. Siempre requiere confirmación del owner."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {"path": "string — ruta del archivo o carpeta a eliminar"}

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = _resolve_alias(str(params.get("path") or "").strip())
        if not path:
            return {"response": "Falta el parámetro 'path'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).delete_path(path))
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_write_file ──────────────────────────────────────────────────────


class PCWriteFileTool(LilithTool):
    """Crea o sobreescribe un archivo de texto en el sistema del owner."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_write_file"

    def get_description(self) -> str:
        return "Crea o escribe un archivo de texto en el sistema del owner."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "path": "string — ruta del archivo",
            "content": "string — contenido a escribir",
            "overwrite": "bool (opcional, default false) — sobreescribir si existe",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = _resolve_alias(str(params.get("path") or "").strip())
        content = str(params.get("content") or "")
        overwrite = bool(params.get("overwrite", False))
        if not path:
            return {"response": "Falta el parámetro 'path'.", "error": True}
        try:
            return _pc_result_to_tool_result(
                _get_pc(self._root).write_file(path, content, overwrite=overwrite)
            )
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_exec ────────────────────────────────────────────────────────────


class PCExecTool(LilithTool):
    """Ejecuta un comando del sistema (requiere confirmación del owner)."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_exec"

    def get_description(self) -> str:
        return "Ejecuta un comando del sistema en el PC del owner. Siempre requiere confirmación."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "command": "string — comando a ejecutar",
            "cwd": "string (opcional) — directorio de trabajo",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        command = str(params.get("command") or params.get("cmd") or "").strip()
        cwd = _resolve_alias(str(params.get("cwd") or "").strip())
        if not command:
            return {"response": "Falta el parámetro 'command'.", "error": True}
        try:
            return _pc_result_to_tool_result(
                _get_pc(self._root).exec_command(command, cwd=cwd)
            )
        except Exception as e:
            return {"response": str(e), "error": True}


# ─── Tool: pc_batch ───────────────────────────────────────────────────────────


class PCBatchTool(LilithTool):
    """Ejecuta múltiples operaciones de filesystem en un solo batch (1 confirmación)."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "pc_batch"

    def get_description(self) -> str:
        return "Ejecuta múltiples operaciones de archivo/directorio en lote con una sola confirmación."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "steps": "list[dict] — [{op: 'mkdir'|'move'|'copy'|'delete'|'exec'|'write_file', ...params}]"
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        steps = params.get("steps") or []
        if not steps:
            return {"response": "Falta la lista de 'steps'.", "error": True}
        try:
            return _pc_result_to_tool_result(_get_pc(self._root).batch(steps))
        except Exception as e:
            return {"response": str(e), "error": True}
