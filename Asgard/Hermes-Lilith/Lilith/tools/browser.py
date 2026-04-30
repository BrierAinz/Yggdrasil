"""
Browser & Clipboard Tools
=========================
Tools para browser y clipboard.
"""
import subprocess


def get_tools():
    """Retorna lista de definiciones de tools de browser y clipboard."""
    return [
        {
            "type": "function",
            "function": {
                "name": "open_url",
                "description": "Abrir una URL en el navegador default",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL a abrir"}
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_google",
                "description": "Buscar en Google",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Busqueda a realizar",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clipboard_read",
                "description": "Leer el contenido del portapapeles",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clipboard_write",
                "description": "Escribir al portapapeles",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Texto a copiar"}
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "type_text",
                "description": "Escribir texto usando el teclado",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Texto a escribir"},
                        "delay": {
                            "type": "integer",
                            "description": "Delay entre caracteres en ms (default: 50)",
                        },
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "press_key",
                "description": "Presionar una tecla especial",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Tecla (enter, tab, escape, ctrl, alt, win, etc)",
                        }
                    },
                    "required": ["key"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "copy_to_clipboard",
                "description": "Copiar un archivo al portapapeles (para pegar en explorador)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Ruta del archivo"}
                    },
                    "required": ["path"],
                },
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de browser o clipboard."""
    args = args or {}

    if name == "open_url":
        return execute_open_url(args.get("url"))
    elif name == "search_google":
        return execute_search_google(args.get("query"))
    elif name == "clipboard_read":
        return execute_clipboard_read()
    elif name == "clipboard_write":
        return execute_clipboard_write(args.get("text"))
    elif name == "type_text":
        return execute_type_text(args.get("text"), args.get("delay", 50))
    elif name == "press_key":
        return execute_press_key(args.get("key"))
    elif name == "copy_to_clipboard":
        return execute_copy_file(args.get("path"))
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_open_url(url: str) -> dict:
    """Abre URL en navegador."""
    try:
        import webbrowser

        webbrowser.open(url)
        return {"success": True, "url": url, "message": "URL abierta en navegador"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_search_google(query: str) -> dict:
    """Busca en Google."""
    try:
        import urllib.parse

        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded}"
        import webbrowser

        webbrowser.open(url)
        return {"success": True, "query": query, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_clipboard_read() -> dict:
    """Lee clipboard."""
    try:
        script = """
        Get-Clipboard -Raw
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return {"success": True, "content": result.stdout[:1000]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_clipboard_write(text: str) -> dict:
    """Escribe al clipboard."""
    try:
        script = f"""
        Set-Clipboard -Value "{text.replace('"', '`"')}"
        "OK"
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return {"success": result.returncode == 0, "text": text[:100]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_type_text(text: str, delay: int = 50) -> dict:
    """Escribe texto usando teclado."""
    try:
        # Escapar comillas y caracteres especiales
        escaped = text.replace('"', '`"').replace("'", "''")

        script = f"""
        Add-Type System.Windows.Forms
        Start-Sleep -Milliseconds 100
        [System.Windows.Forms.SendKeys]::SendWait("{escaped}")
        "OK"
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        return {"success": result.returncode == 0, "text": text[:50]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_press_key(key: str) -> dict:
    """Presiona tecla especial."""
    key_map = {
        "enter": "{ENTER}",
        "tab": "{TAB}",
        "escape": "{ESC}",
        "esc": "{ESC}",
        "ctrl": "^",
        "alt": "%",
        "win": "^{ESC}",
        "backspace": "{BACKSPACE}",
        "delete": "{DELETE}",
        "home": "{HOME}",
        "end": "{END}",
        "pageup": "{PGUP}",
        "pagedown": "{PGDN}",
        "up": "{UP}",
        "down": "{DOWN}",
        "left": "{LEFT}",
        "right": "{RIGHT}",
    }

    try:
        key_code = key_map.get(key.lower(), f"{{{key}}}")

        script = f"""
        Add-Type System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait("{key_code}")
        "OK"
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=5,
        )

        return {"success": result.returncode == 0, "key": key}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_copy_file(path: str) -> dict:
    """Copia archivo al clipboard."""
    try:
        script = f"""
        $file = Get-Item -Path "{path}"
        if ($file) {{
            $file | Set-Clipboard
            "OK"
        }} else {{
            throw "File not found"
        }}
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {"success": result.returncode == 0, "path": path}

    except Exception as e:
        return {"success": False, "error": str(e)}
