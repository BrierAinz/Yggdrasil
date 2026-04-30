"""
Desktop Tools
=============
Tools para control de desktop (screenshot, mouse, etc.)
"""
import datetime
import json
import subprocess
from pathlib import Path


def get_tools():
    """Retorna lista de definiciones de tools para desktop."""
    return [
        {
            "type": "function",
            "function": {
                "name": "screenshot",
                "description": "Captura una screenshot de la pantalla completa",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_cursor_position",
                "description": "Obtiene la posicion actual del cursor del mouse",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_windows",
                "description": "Lista las ventanas abiertas actualmente",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de desktop."""
    args = args or {}

    if name == "screenshot":
        return execute_screenshot()
    elif name == "get_cursor_position":
        return execute_get_cursor_position()
    elif name == "list_windows":
        return execute_list_windows()
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_screenshot() -> dict:
    """Captura pantalla usando PowerShell."""
    try:
        screenshot_dir = Path("D:/Proyectos/Midgard/Lilith/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = screenshot_dir / filename

        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save("{filepath}")
        $graphics.Dispose()
        $bitmap.Dispose()
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and filepath.exists():
            return {
                "success": True,
                "message": "Screenshot guardada",
                "path": str(filepath),
            }
        else:
            return {"success": False, "error": result.stderr or "Error desconocido"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_get_cursor_position() -> dict:
    """Obtiene posicion del cursor."""
    try:
        script = """
        Add-Type System.Windows.Forms
        $pos = [System.Windows.Forms.Cursor]::Position
        @{{x=$pos.X; y=$pos.Y}} | ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            pos = json.loads(result.stdout.strip())
            return {"success": True, "x": pos["x"], "y": pos["y"]}
        else:
            return {"success": False, "error": result.stderr}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_list_windows() -> dict:
    """Lista ventanas abiertas."""
    try:
        script = """
        Get-Process | Where-Object {$_.MainWindowTitle} |
        Select-Object Name, MainWindowTitle |
        ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output.startswith("["):
                windows = json.loads(output)
            else:
                windows = [json.loads(output)] if output else []

            return {
                "success": True,
                "windows": [
                    {"name": w["Name"], "title": w["MainWindowTitle"]} for w in windows
                ],
            }
        else:
            return {"success": False, "error": result.stderr}

    except Exception as e:
        return {"success": False, "error": str(e)}
