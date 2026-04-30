"""
Lilith 3.0 — Tool: reunir contenido de un directorio de forma recursiva (para Odin).
Lee archivos de texto bajo una ruta y concatena hasta un límite de caracteres.
"""
from pathlib import Path
from typing import Any, Dict, Set

from .protocol import LilithTool, ToolResult

# Extensiones que se consideran texto (evitar binarios)
TEXT_EXTENSIONS: Set[str] = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".bat",
    ".ps1",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".vue",
    ".rs",
    ".go",
}


class GatherDirectoryTool(LilithTool):
    """Reúne el contenido de archivos de texto en un directorio (recursivo) para análisis masivo."""

    def __init__(self, project_root: Path) -> None:
        self._root = Path(project_root)

    @property
    def name(self) -> str:
        return "gather_directory"

    def get_description(self) -> str:
        return "Reúne el contenido de archivos de texto en una ruta (recursivo). Para análisis masivo con Odin. Limita por max_chars."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "path": "string (ruta, ej. Backend o Backend/core)",
            "max_chars": "int opcional (default 80000)",
            "max_files": "int opcional (default 100)",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = (params.get("path") or "Backend").strip()
        from src.core.input_sanitizer import validate_path

        ok, err = validate_path(path, self._root)
        if not ok:
            return {"response": err or "Ruta no válida.", "error": True}
        max_chars = int(params.get("max_chars") or 0) or 80_000
        max_files = int(params.get("max_files") or 0) or 100

        try:
            from src.tools.autonomous.file_manager import FileManager

            fm = FileManager(base_path=str(self._root))
            out = fm.list_directory(dir_path=path, pattern=None, recursive=True)
        except Exception as e:
            return {"response": f"Error al listar directorio: {e}", "error": True}

        if not out.get("success"):
            return {"response": out.get("error", "Error listando"), "error": True}

        files = out.get("files", [])
        root_path = Path(self._root)
        parts = []
        total_chars = 0
        files_read = 0

        for f in files:
            if files_read >= max_files or total_chars >= max_chars:
                break
            file_path = f.get("path") or f.get("name")
            if not file_path:
                continue
            p = Path(file_path)
            if p.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            try:
                rel = p.relative_to(root_path)
            except ValueError:
                rel = p if not p.is_absolute() else Path(p.name)
            rel_str = str(rel).replace("\\", "/")
            try:
                read_out = fm.read_file(rel_str, limit_lines=None)
            except Exception:
                continue
            if not read_out.get("success"):
                continue
            content = (read_out.get("content") or "").strip()
            if not content:
                continue
            chunk = f"\n\n--- archivo: {rel_str} ---\n{content}"
            if total_chars + len(chunk) > max_chars:
                chunk = chunk[: max_chars - total_chars].rstrip() + "\n… (truncado)"
            parts.append(chunk)
            total_chars += len(chunk)
            files_read += 1

        if not parts:
            return {
                "response": f"No he encontrado archivos de texto en esa ruta ({path}).",
                "data": {"path": path},
            }
        # A.3: voz de Lilith en la salida
        header = f"He reunido el contenido del directorio para que puedas analizarlo. {path} — {files_read} archivos, ~{total_chars} caracteres.\n\n"
        response = header + "".join(parts)
        return {
            "response": response,
            "data": {
                "path": path,
                "files_read": files_read,
                "total_chars": total_chars,
            },
        }
