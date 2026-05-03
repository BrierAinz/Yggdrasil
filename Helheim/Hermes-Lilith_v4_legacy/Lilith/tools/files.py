"""
File Tools
==========
Tools para operaciones de archivo.
"""
import subprocess
from pathlib import Path


def get_tools():
    """Retorna lista de definiciones de tools para archivos."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Lee el contenido de un archivo de texto. Especifica la ruta absoluta del archivo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Ruta absoluta del archivo a leer",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Escribe contenido a un archivo. Crea el archivo si no existe.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Ruta absoluta del archivo",
                        },
                        "content": {
                            "type": "string",
                            "description": "Contenido a escribir",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "Lista el contenido de un directorio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del directorio"}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_exists",
                "description": "Verifica si un archivo o directorio existe.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta a verificar"}
                    },
                    "required": ["path"],
                },
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de archivo."""
    args = args or {}

    if name == "read_file":
        return execute_read_file(args.get("path"))
    elif name == "write_file":
        return execute_write_file(args.get("path"), args.get("content"))
    elif name == "list_directory":
        return execute_list_directory(args.get("path"))
    elif name == "file_exists":
        return execute_file_exists(args.get("path"))
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_read_file(path: str) -> dict:
    """Lee contenido de archivo."""
    try:
        filepath = Path(path)
        if not filepath.exists():
            return {"success": False, "error": f"Archivo no existe: {path}"}

        if filepath.stat().st_size > 100_000:  # > 100KB
            return {"success": False, "error": "Archivo muy grande (>100KB)"}

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "success": True,
            "path": path,
            "content": content[:5000],  # Limitar output
            "truncated": len(content) > 5000,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_write_file(path: str, content: str) -> dict:
    """Escribe contenido a archivo."""
    try:
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Archivo escrito: {path}",
            "bytes": len(content),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_list_directory(path: str) -> dict:
    """Lista contenido de directorio."""
    try:
        dirpath = Path(path)
        if not dirpath.exists():
            return {"success": False, "error": f"Directorio no existe: {path}"}

        items = []
        for item in dirpath.iterdir():
            items.append(
                {
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                }
            )

        return {"success": True, "path": path, "items": items, "count": len(items)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_file_exists(path: str) -> dict:
    """Verifica existencia de archivo."""
    path = Path(path)
    return {
        "success": True,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "path": str(path),
    }
