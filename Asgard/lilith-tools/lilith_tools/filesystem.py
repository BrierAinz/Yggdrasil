"""Filesystem tools for reading files and listing directories."""

from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult
from .registry import ToolRegistry


@ToolRegistry.register
class FileReadTool(BaseTool):
    """Tool that reads the text content of a file from the filesystem."""

    name = "file_read"
    description = "Lee contenido de un archivo"
    parameters = {
        "path": {"type": "string", "required": True},
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Lee el contenido de un archivo."""
        path = Path(kwargs.get("path", ""))
        if not path.exists():
            return ToolResult(success=False, data=None, error=f"Archivo no encontrado: {path}")
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return ToolResult(success=True, data=content)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


@ToolRegistry.register
class DirectoryListTool(BaseTool):
    """Tool that lists files and subdirectories in a given directory path."""

    name = "directory_list"
    description = "Lista archivos en un directorio"
    parameters = {
        "path": {"type": "string", "required": True},
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        """Lista archivos y subdirectorios en un directorio."""
        path = Path(kwargs.get("path", "."))
        if not path.exists():
            return ToolResult(success=False, data=None, error=f"Directorio no encontrado: {path}")
        try:
            items = []
            for item in sorted(path.iterdir()):
                items.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
            return ToolResult(success=True, data=items)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
