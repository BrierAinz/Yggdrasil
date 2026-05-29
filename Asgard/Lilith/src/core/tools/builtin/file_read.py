"""
Lilith 3.0 — Tool: leer archivo (wrapper de FileManager).
"""
import json
from pathlib import Path
from typing import Any, Dict

from ..security_guard import SecurityGuard
from .protocol import LilithTool, ToolResult


class FileReadTool(LilithTool):
    """Lee y devuelve el contenido (o resumen) de un archivo del proyecto."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "read_file"

    def get_description(self) -> str:
        return "Leer contenido de un archivo del proyecto. Usar cuando el usuario pida ver, leer o abrir un archivo."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "path": "string (ruta relativa al proyecto)",
            "max_chars": "int opcional",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = (params.get("path") or "").strip()
        if not path:
            return {
                "response": "Indica la ruta del archivo (ej. Backend/main.py).",
                "error": True,
            }
        decision = SecurityGuard(self._root).check_path("read", path)
        if not decision.allowed:
            return {
                "response": json.dumps(decision.response, ensure_ascii=False),
                "error": True,
            }
        from src.core.input_sanitizer import validate_path

        ok, err = validate_path(path, self._root)
        if not ok:
            return {"response": err or "Ruta no válida.", "error": True}
        max_chars = params.get("max_chars") or 0
        limit_lines = params.get("limit_lines")

        try:
            from src.tools.autonomous.file_manager import FileManager

            fm = FileManager(base_path=str(self._root))
            out = fm.read_file(path, limit_lines=limit_lines)
        except Exception as e:
            return {"response": f"Error al leer: {e}", "error": True}

        if not out.get("success"):
            return {
                "response": out.get("error", "Error leyendo archivo"),
                "error": True,
            }
        content = out.get("content") or ""
        if max_chars and len(content) > max_chars:
            content = content[:max_chars].rstrip() + "\n… (truncado)"
        lines = out.get("lines", 0)
        return {
            "response": content or "(archivo vacío)",
            "data": {
                "path": path,
                "lines": lines,
                "truncated": out.get("truncated", False),
            },
        }
