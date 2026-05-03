"""
System Tools
============
Tools para ejecutar comandos de sistema.
"""
import subprocess


def get_tools():
    """Retorna lista de definiciones de tools de sistema."""
    return [
        {
            "type": "function",
            "function": {
                "name": "run_terminal",
                "description": "Ejecuta un comando en PowerShell. Útil para instalar packages, ejecutar scripts, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Comando PowerShell a ejecutar",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout en segundos (default: 30)",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_vscode",
                "description": "Abre Visual Studio Code. Puede abrir una carpeta específica o un archivo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Ruta de carpeta o archivo a abrir (opcional)",
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_application",
                "description": "Abre una aplicación de Windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre de la aplicación (ej: 'notepad', 'calc', 'chrome')",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de sistema."""
    args = args or {}

    if name == "run_terminal":
        return execute_run_terminal(args.get("command"), args.get("timeout", 30))
    elif name == "open_vscode":
        return execute_open_vscode(args.get("path"))
    elif name == "open_application":
        return execute_open_application(args.get("name"))
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_run_terminal(command: str, timeout: int = 30) -> dict:
    """Ejecuta comando en PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "command": command,
            "stdout": result.stdout[:3000] if result.stdout else "",
            "stderr": result.stderr[:1000] if result.stderr else "",
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout después de {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_open_vscode(path: str = None) -> dict:
    """Abre VS Code."""
    try:
        import os

        if path:
            cmd = f'code "{path}"'
        else:
            cmd = "code ."

        subprocess.Popen(cmd, shell=True)
        return {
            "success": True,
            "message": f"VS Code abierto: {path or 'carpeta actual'}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_open_application(name: str) -> dict:
    """Abre aplicación de Windows."""
    try:
        subprocess.Popen(name, shell=True)
        return {"success": True, "message": f"Aplicación iniciada: {name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
