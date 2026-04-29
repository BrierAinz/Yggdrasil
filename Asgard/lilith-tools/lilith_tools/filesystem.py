from pathlib import Path
from .base import BaseTool, ToolResult
from .registry import ToolRegistry


@ToolRegistry.register
class FileReadTool(BaseTool):
    name = "file_read"
    description = "Lee contenido de un archivo"
    parameters = {
        "path": {"type": "string", "required": True},
    }

    def execute(self, **kwargs) -> ToolResult:
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
    name = "directory_list"
    description = "Lista archivos en un directorio"
    parameters = {
        "path": {"type": "string", "required": True},
    }

    def execute(self, **kwargs) -> ToolResult:
        path = Path(kwargs.get("path", "."))
        if not path.exists():
            return ToolResult(success=False, data=None, error=f"Directorio no encontrado: {path}")
        try:
            items = []
            for item in sorted(path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return ToolResult(success=True, data=items)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
