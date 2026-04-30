"""
Lilith 3.0 — Tool: listar directorio (wrapper de FileManager).
"""
import json
from pathlib import Path
from typing import Any, Dict

from ..security_guard import SecurityGuard
from .protocol import LilithTool, ToolResult


class ListDirectoryTool(LilithTool):
    """Lista archivos y carpetas en una ruta del proyecto."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "list_directory"

    def get_description(self) -> str:
        return "Listar archivos y directorios en una ruta. Usar cuando pidan listar, ver contenido de carpeta o explorar."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "path": "string (ruta, default '.')",
            "pattern": "string opcional (ej. *.py)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = (params.get("path") or ".").strip()
        pattern = (params.get("pattern") or "").strip() or None
        decision = SecurityGuard(self._root).check_path("list", path)
        if not decision.allowed:
            return {
                "response": json.dumps(decision.response, ensure_ascii=False),
                "error": True,
            }

        try:
            from src.tools.autonomous.file_manager import FileManager

            fm = FileManager(base_path=str(self._root))
            out = fm.list_directory(dir_path=path, pattern=pattern, recursive=False)
        except Exception as e:
            return {"response": f"Error al listar: {e}", "error": True}

        if not out.get("success"):
            return {
                "response": out.get("error", "Error listando directorio"),
                "error": True,
            }
        files = out.get("files", [])
        dirs = out.get("directories", [])
        lines = [f"📁 {d.get('name', '')}" for d in dirs] + [
            f"📄 {f.get('name', '')}" for f in files
        ]
        raw = "\n".join(lines) if lines else "(vacío)"
        # A.3: voz de Lilith en la salida
        response = f"He explorado el directorio. Aquí están los archivos y carpetas encontrados:\n\n{raw}"
        return {
            "response": response,
            "data": {"path": path, "count_files": len(files), "count_dirs": len(dirs)},
        }
