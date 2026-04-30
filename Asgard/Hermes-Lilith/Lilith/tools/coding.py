"""
Coding Tools
===========
Tools para desarrollo de software.
"""
import subprocess
from pathlib import Path


def get_tools():
    """Retorna lista de definiciones de tools de coding."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run_git",
                "description": "Ejecutar comando git en un repositorio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Comando git (status, log, diff, etc)",
                        },
                        "repo_path": {
                            "type": "string",
                            "description": "Ruta al repositorio (opcional)",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_npm",
                "description": "Ejecutar comando npm en un proyecto Node",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Comando npm (install, run dev, build, etc)",
                        },
                        "path": {
                            "type": "string",
                            "description": "Ruta al proyecto (opcional)",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_python_script",
                "description": "Ejecutar un script Python",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "Script o ruta al archivo .py",
                        },
                        "args": {
                            "type": "string",
                            "description": "Argumentos para el script (opcional)",
                        },
                    },
                    "required": ["script"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_in_files",
                "description": "Buscar texto en archivos de un directorio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Texto a buscar"},
                        "path": {
                            "type": "string",
                            "description": "Directorio a buscar",
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Patron de archivos (ej: *.py)",
                        },
                    },
                    "required": ["query", "path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_git_status",
                "description": "Obtener estado de un repositorio git",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {
                            "type": "string",
                            "description": "Ruta al repositorio",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_git_branches",
                "description": "Listar ramas de un repositorio git",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_path": {
                            "type": "string",
                            "description": "Ruta al repositorio",
                        }
                    },
                },
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de coding."""
    args = args or {}

    if name == "run_git":
        return execute_run_git(args.get("command"), args.get("repo_path"))
    elif name == "run_npm":
        return execute_run_npm(args.get("command"), args.get("path"))
    elif name == "run_python_script":
        return execute_run_python(args.get("script"), args.get("args"))
    elif name == "search_in_files":
        return execute_search_in_files(
            args.get("query"), args.get("path"), args.get("file_pattern")
        )
    elif name == "get_git_status":
        return execute_git_status(args.get("repo_path"))
    elif name == "list_git_branches":
        return execute_git_branches(args.get("repo_path"))
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_run_git(command: str, repo_path: str = None) -> dict:
    """Ejecuta comando git."""
    try:
        args = ["git"] + command.split()

        if repo_path:
            result = subprocess.run(
                args, cwd=repo_path, capture_output=True, text=True, timeout=30
            )
        else:
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)

        return {
            "success": result.returncode == 0,
            "command": f"git {command}",
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000] if result.stderr else "",
            "returncode": result.returncode,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_run_npm(command: str, path: str = None) -> dict:
    """Ejecuta comando npm."""
    try:
        args = ["npm"] + command.split()

        if path:
            result = subprocess.run(
                args, cwd=path, capture_output=True, text=True, timeout=120
            )
        else:
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)

        return {
            "success": result.returncode == 0,
            "command": f"npm {command}",
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000] if result.stderr else "",
            "returncode": result.returncode,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_run_python(script: str, args: str = None) -> dict:
    """Ejecuta script Python."""
    try:
        cmd = ["python", script]
        if args:
            cmd.extend(args.split())

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        return {
            "success": result.returncode == 0,
            "script": script,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000] if result.stderr else "",
            "returncode": result.returncode,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_search_in_files(query: str, path: str, file_pattern: str = "*") -> dict:
    """Busca texto en archivos."""
    try:
        script = f"""
        Get-ChildItem -Path "{path}" -Recurse -Include "{file_pattern}" |
        Select-String -Pattern "{query}" |
        Select-Object Path, LineNumber, Line |
        ConvertTo-Json -Depth 2
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {
            "success": result.returncode == 0,
            "query": query,
            "path": path,
            "results": result.stdout[:5000],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_git_status(repo_path: str) -> dict:
    """Obtiene estado de git."""
    return execute_run_git("status", repo_path)


def execute_git_branches(repo_path: str) -> dict:
    """Lista ramas de git."""
    return execute_run_git("branch -a", repo_path)
