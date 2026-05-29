#!/usr/bin/env python3
"""
Lilith CLI - AI-Powered Command Line Interface for Yggdrasil
Interactúa con Yggdrasil usando lenguaje natural, como en el chat.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from cyclopts import App
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ── Configuration ──────────────────────────────────────────────
logger = logging.getLogger(__name__)
YGGDRASIL_ROOT = Path(__file__).parent.resolve()
LILITH_API_URL = "http://localhost:8000"

# ── Theme & Style ──────────────────────────────────────────────
yggdrasil_theme = Theme(
    {
        "realm": "gold1",
        "error": "red",
        "success": "green",
        "warning": "yellow",
        "info": "cyan",
        "primary": "blue",
        "secondary": "magenta",
        "muted": "dim",
    }
)
console = Console(theme=yggdrasil_theme)

# ── ASCII Art Banner ────────────────────────────────────────────
LILITH_BANNER = """╭─────────────────────────────────────────────────────────────────╮
│                 🌙 LILITH CLI 🌙                              │
│                                                                 │
│  Interactúa con Yggdrasil usando lenguaje natural              │
│  Lilith te ayudará a gestionar tu ecosistema AI                │
│                                                                 │
│  [bold red]⚔[/] [magenta]Odin[/]    → [bold red]⚔[/] [cyan]Eva[/]     → [bold red]⚔[/] [green]Mimir[/]    → [bold red]⚔[/] [orange]Adán[/]     │
│  [bold red]⚔[/] [blue]Shalltear[/] → [bold red]⚔[/] [yellow]Ainz[/]    → [bold red]⚔[/] [cyan]Gandalf[/]  → [bold red]⚔[/] [white]Midgard[/]   │
│                                                                 │
│  [bold green]✓[/] Lilith Ready   [bold blue]✓[/] API Connected   [bold yellow]✓[/] System Healthy │
╰─────────────────────────────────────────────────────────────────╯"""

# ── Global State ────────────────────────────────────────────────
app = App(
    name="lilith",
    version="3.0.0",
    help="Lilith CLI - AI-Powered interface for Yggdrasil",
)


# ── Helper Functions ────────────────────────────────────────────
def print_banner():
    """Print ASCII art banner"""
    console.print()
    console.print(Panel.fit(Text(LILITH_BANNER, style="red")))
    console.print(Rule(style="dim"))
    console.print(
        Text(
            f"[bold green]Version[/] {app.version} · [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]",
            style="dim",
        )
    )
    console.print()


def validate_api_connection():
    """Validate connection to Lilith API"""
    try:
        import requests

        response = requests.get(f"{LILITH_API_URL}/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def call_lilith_api(prompt: str) -> dict[str, Any]:
    """Call Lilith API for processing"""
    try:
        import requests

        payload = {"query": prompt}
        response = requests.post(
            f"{LILITH_API_URL}/api/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "response": f"Error en la API: {response.status_code}",
                "command": None,
                "confidence": 0.0,
            }

    except Exception as e:
        return {"response": f"Error de conexión: {e!s}", "command": None, "confidence": 0.0}


def execute_command(cmd: str, description: str | None = None) -> str:
    """Execute command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=str(YGGDRASIL_ROOT)
        )

        output = []
        if description:
            output.append(f"🔍 {description}")

        if result.stdout:
            output.append("📄 Salida:")
            output.append(result.stdout.strip())

        if result.stderr:
            output.append("❌ Error:")
            output.append(result.stderr.strip())

        output.append(f"💻 Código: {result.returncode}")

        return "\n".join(output)
    except Exception as e:
        return f"❌ Error al ejecutar: {e!s}"


# ── Command Handlers ───────────────────────────────────────────
def handle_health_check():
    """Check Yggdrasil health"""
    output = []

    # Check API
    api_healthy = validate_api_connection()
    output.append(f"API: {'✅' if api_healthy else '❌'}")

    # Check directories
    realms = [
        "Asgard",
        "Vanaheim",
        "Alfheim",
        "Svartalfheim",
        "Muspelheim",
        "Helheim",
        "Niflheim",
        "Jotunheim",
        "Midgard",
    ]

    for realm in realms:
        realm_dir = YGGDRASIL_ROOT / realm
        exists = realm_dir.exists()
        output.append(f"{realm}: {'✅' if exists else '❌'}")

    return "\n".join(output)


def handle_list_projects():
    """List Yggdrasil projects"""
    output = []

    # Check all Yggdrasil realms
    realms = [
        "Asgard",
        "Vanaheim",
        "Alfheim",
        "Svartalfheim",
        "Muspelheim",
        "Helheim",
        "Niflheim",
        "Jotunheim",
        "Midgard",
    ]

    projects_found = False

    for realm in realms:
        realm_dir = YGGDRASIL_ROOT / realm

        if realm_dir.exists() and realm_dir.is_dir():
            # Look for project-like directories (containing .py, .js, etc.)
            for item in realm_dir.iterdir():
                if item.is_dir():
                    # Check if it's a project (contains common project files)
                    project_files = (
                        list(item.glob("*.py"))
                        + list(item.glob("*.js"))
                        + list(item.glob("*.ts"))
                        + list(item.glob("*.json"))
                        + list(item.glob("*.md"))
                    )

                    if project_files:
                        projects_found = True
                        output.append(f"📁 {realm}/{item.name}")

    if not projects_found:
        return "No se encontraron proyectos en Yggdrasil"

    return "\n".join(output)


def handle_dashboard_status():
    """Check dashboard status"""
    try:
        import requests

        response = requests.get(f"{LILITH_API_URL}/", timeout=5)
        return f"Dashboard: {'✅' if response.status_code == 200 else '❌'}"
    except Exception as e:
        return f"Dashboard: ❌ {e!s}"


def handle_memory_stats():
    """Get memory statistics"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return (
            f"🖥️ Memoria RAM: {memory.percent}% usado\n"
            f"📊 Total: {round(memory.total / 1024 / 1024 / 1024, 1)} GB\n"
            f"✅ Disponible: {round(memory.available / 1024 / 1024 / 1024, 1)} GB\n"
            f"🔄 Uso: {round(memory.used / 1024 / 1024 / 1024, 1)} GB"
        )
    except Exception as e:
        return f"Error al obtener estadísticas de memoria: {e!s}"


def handle_system_info():
    """Get complete system information"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage("/")

        return (
            f"🖥️ Información del Sistema:\n"
            f"  💻 CPU: {cpu_percent}% usado, {psutil.cpu_count(logical=True)} núcleos\n"
            f"  📊 Memoria RAM: {memory.percent}% usado ({memory.used / 1024 / 1024:.0f}MB/{memory.total / 1024 / 1024:.0f}MB)\n"
            f"  💾 Disco: {disk_usage.percent}% usado ({disk_usage.used / 1024 / 1024 / 1024:.1f}GB/{disk_usage.total / 1024 / 1024 / 1024:.1f}GB)\n"
            f"  📱 Red: {len(psutil.net_if_addrs())} interfaces\n"
            f"  🌐 Python: {sys.version}\n"
            f"  🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        return f"Error al obtener información del sistema: {e!s}"
    """Get complete system information"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage("/")

        return (
            f"🖥️ Información del Sistema:\n"
            f"  💻 CPU: {cpu_percent}% usado, {psutil.cpu_count(logical=True)} núcleos\n"
            f"  📊 Memoria RAM: {memory.percent}% usado ({memory.used / 1024 / 1024:.0f}MB/{memory.total / 1024 / 1024:.0f}MB)\n"
            f"  💾 Disco: {disk_usage.percent}% usado ({disk_usage.used / 1024 / 1024 / 1024:.1f}GB/{disk_usage.total / 1024 / 1024 / 1024:.1f}GB)\n"
            f"  📱 Red: {len(psutil.net_if_addrs())} interfaces\n"
            f"  🌐 Python: {sys.version}\n"
            f"  🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        return f"Error al obtener información del sistema: {e!s}"


def handle_directory_content(directory: str):
    """List directory contents"""
    try:
        # Handle Windows paths
        if directory.startswith("D:") or directory.startswith("d:"):
            directory = "/mnt/d" + directory[2:].replace("\\", "/")

        p = Path(directory)
        if not p.exists():
            return f"El directorio {directory} no existe"

        if not p.is_dir():
            return f"{directory} no es un directorio"

        output = []
        output.append(f"📁 Contenido de {p}:")

        for item in p.iterdir():
            item_type = "📄" if item.is_file() else "📁"
            item_name = str(item.name)
            item_size = f" ({item.stat().st_size / 1024:.1f}KB)" if item.is_file() else ""
            item_mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%H:%M:%S")

            output.append(f"{item_type} {item_name}{item_size} ({item_mtime})")

        return "\n".join(output)
    except Exception as e:
        return f"Error: {e!s}"


def handle_run_command(cmd: str):
    """Run custom command"""
    try:
        import subprocess

        # Handle Windows paths
        cmd = cmd.replace("D:\\", "/mnt/d/").replace("\\", "/")

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=str(YGGDRASIL_ROOT)
        )

        output = []
        if result.stdout:
            output.append("📄 Salida:")
            output.append(result.stdout.strip())

        if result.stderr:
            output.append("❌ Error:")
            output.append(result.stderr.strip())

        output.append(f"💻 Código: {result.returncode}")

        return "\n".join(output)
    except Exception as e:
        return f"Error al ejecutar: {e!s}"


def handle_view_file(file: str):
    """View file contents"""
    try:
        # Handle Windows paths
        if file.startswith("D:") or file.startswith("d:"):
            file = "/mnt/d" + file[2:].replace("\\", "/")

        p = Path(file)
        if not p.exists():
            return f"El archivo {file} no existe"

        if not p.is_file():
            return f"{file} no es un archivo"

        content = p.read_text(encoding="utf-8")

        if len(content) > 5000:
            return f"📄 Contenido de {file} (truncado a 5000 caracteres):\n" + content[:5000]
        else:
            return f"📄 Contenido de {file}:\n" + content
    except Exception as e:
        return f"Error: {e!s}"
    """Get memory statistics"""
    try:
        import psutil

        memory = psutil.virtual_memory()
        return (
            f"🖥️ Memoria RAM: {memory.percent}% usado\n"
            f"📊 Total: {round(memory.total / 1024 / 1024 / 1024, 1)} GB\n"
            f"✅ Disponible: {round(memory.available / 1024 / 1024 / 1024, 1)} GB\n"
            f"🔄 Uso: {round(memory.used / 1024 / 1024 / 1024, 1)} GB"
        )
    except Exception as e:
        return f"Error al obtener estadísticas de memoria: {e!s}"


def handle_cpu_info():
    """Get CPU information"""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        return (
            f"⚡ Uso CPU: {cpu_percent}%\n"
            f"🧠 Núcleos: {cpu_count} núcleos\n"
            f"🏢 Frecuencia: {psutil.cpu_freq().current:.0f} MHz"
        )
    except Exception as e:
        return f"Error al obtener información de CPU: {e!s}"


def handle_start_services():
    """Start Yggdrasil services"""
    commands = ["uv run poe dashboard &", "uv run poe api &", "uv run poe agent &"]

    results = []
    for cmd in commands:
        try:
            subprocess.run(cmd, shell=True, cwd=str(YGGDRASIL_ROOT))
            results.append(f"✅ Comando ejecutado: {cmd}")
        except Exception as e:
            results.append(f"❌ Error: {e!s}")

    return "\n".join(results)


def handle_stop_services():
    """Stop Yggdrasil services"""
    processes = ["uvicorn", "python -m uvicorn", "poe", "dashboard"]

    results = []
    for proc in processes:
        try:
            subprocess.run(f"pkill -f '{proc}'", shell=True)
            results.append(f"✅ Proceso terminado: {proc}")
        except Exception as e:
            results.append(f"❌ Error: {e!s}")

    return "\n".join(results)


# ── Command Matching ───────────────────────────────────────────
COMMANDS = {
    "health": handle_health_check,
    "status": handle_health_check,
    "projects": handle_list_projects,
    "dashboard": handle_dashboard_status,
    "memory": handle_memory_stats,
    "cpu": handle_cpu_info,
    "system": handle_system_info,
    "info": handle_system_info,
    "dir": handle_directory_content,
    "list": handle_directory_content,
    "view": handle_view_file,
    "cat": handle_view_file,
    "run": handle_run_command,
    "execute": handle_run_command,
    "start": handle_start_services,
    "stop": handle_stop_services,
}


def find_command(text: str) -> str:
    """Find command in user input"""
    text = text.lower()

    if any(keyword in text for keyword in ["health", "estado", "status"]):
        return "health"
    elif any(keyword in text for keyword in ["proyectos", "projects"]):
        return "projects"
    elif any(keyword in text for keyword in ["dashboard", "panel"]):
        return "dashboard"
    elif any(keyword in text for keyword in ["memoria", "memory"]):
        return "memory"
    elif any(keyword in text for keyword in ["cpu", "processor", "procesador"]):
        return "cpu"
    elif any(keyword in text for keyword in ["sistema", "system", "info"]):
        return "system"
    elif any(keyword in text for keyword in ["dir", "listar", "contenido"]):
        return "dir"
    elif any(keyword in text for keyword in ["ver", "cat", "leer"]):
        return "view"
    elif any(keyword in text for keyword in ["run", "ejecutar"]):
        return "run"
    elif any(keyword in text for keyword in ["start", "iniciar"]):
        return "start"
    elif any(keyword in text for keyword in ["stop", "detener"]):
        return "stop"

    return None


# ── Core Commands ──────────────────────────────────────────────
@app.command
def help():
    """Show help information"""
    print_banner()
    console.print(Text("Comandos disponibles (Lilith-style):", style="bold red"))
    console.print()

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Comando", style="bold")
    table.add_column("Descripción")
    table.add_column("Ejemplo")

    commands = [
        ("health", "Verifica estado de Yggdrasil", "¿Cuál es el estado de Yggdrasil?"),
        ("status", "Muestra estado completo", "Muestra el estado del sistema"),
        ("projects", "Lista proyectos en Midgard", "¿Qué proyectos hay en Midgard?"),
        ("dashboard", "Verifica dashboard web", "¿El dashboard está corriendo?"),
        ("memory", "Estadísticas de memoria RAM", "¿Cuánta memoria se está usando?"),
        ("cpu", "Información de CPU", "¿Cuál es el uso del procesador?"),
        ("start", "Inicia servicios", "Inicia los servicios de Yggdrasil"),
        ("stop", "Detiene servicios", "Detiene los servicios"),
    ]

    for cmd, desc, example in commands:
        table.add_row(cmd, desc, example)

    console.print(table)
    console.print()
    console.print(Text("O puedes usar comandos en lenguaje natural!", style="yellow"))


@app.command
def interactive():
    """Start interactive chat with Lilith CLI"""
    print_banner()
    console.print(Text("¡Bienvenido al CLI de Lilith!", style="bold red"))
    console.print(Text("Pregunta lo que quieras sobre Yggdrasil o tu sistema...", style="dim"))
    console.print(Rule())

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]Lilith>[/] ")

            if user_input.lower() in ["salir", "exit", "quit"]:
                console.print(Text("¡Hasta luego! 👋", style="green"))
                break

            if user_input.lower() in ["ayuda", "help"]:
                help()
                continue

            console.print()
            console.print(Text("🔍 Analizando...", style="yellow"))

            # Find command
            command = find_command(user_input)

            if command:
                console.print(Text(f"⚡ Ejecutando: {command}", style="cyan"))

                # Extract parameters from input
                if command == "dir":
                    # Find directory path in input (Windows or Linux)
                    import re

                    path_match = re.search(r'"([^"]+)"|([^\s]+)', user_input)
                    if path_match:
                        result = handle_directory_content(
                            path_match.group(1) or path_match.group(2)
                        )
                    else:
                        result = handle_directory_content("/mnt/d/Proyectos")

                elif command == "view":
                    # Find file path in input
                    import re

                    path_match = re.search(r'"([^"]+)"|([^\s]+)', user_input)
                    if path_match:
                        result = handle_view_file(path_match.group(1) or path_match.group(2))
                    else:
                        result = "Debes especificar un archivo para ver"

                elif command == "run":
                    # Find command to execute
                    import re

                    cmd_match = re.search(r'(?<=\s|^)(run|ejecutar)?\s*["]?([^"]+)["]?', user_input)
                    if cmd_match and cmd_match.group(2):
                        result = handle_run_command(cmd_match.group(2))
                    else:
                        result = "Debes especificar un comando para ejecutar"

                else:
                    # No parameters needed
                    result = COMMANDS[command]()
            else:
                console.print(
                    Text("🤖 No reconozco el comando. Pidiendo a Lilith...", style="yellow")
                )
                api_response = call_lilith_api(user_input)

                if api_response.get("command"):
                    result = execute_command(api_response["command"], api_response["response"])
                else:
                    result = api_response["response"]

            console.print()
            console.print(Text(result, style="white"))
            console.print(Rule())

        except KeyboardInterrupt:
            console.print()
            console.print(Text("¡Hasta luego! 👋", style="green"))
            break
        except Exception as e:
            console.print(Text(f"❌ Error: {e}", style="red"))
            console.print(Rule())
    """Start interactive chat with Lilith CLI"""
    print_banner()
    console.print(Text("¡Bienvenido al CLI de Lilith!", style="bold red"))
    console.print(Text("Pregunta lo que quieras sobre Yggdrasil...", style="dim"))
    console.print(Rule())

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]Lilith>[/] ")

            if user_input.lower() in ["salir", "exit", "quit"]:
                console.print(Text("¡Hasta luego! 👋", style="green"))
                break

            if user_input.lower() in ["ayuda", "help"]:
                help()
                continue

            console.print()
            console.print(Text("🔍 Analizando...", style="yellow"))

            # Find command
            command = find_command(user_input)

            if command:
                console.print(Text(f"⚡ Ejecutando: {command}", style="cyan"))
                result = COMMANDS[command]()
            else:
                console.print(
                    Text("🤖 No reconozco el comando. Pidiendo a Lilith...", style="yellow")
                )
                api_response = call_lilith_api(user_input)

                if api_response.get("command"):
                    result = execute_command(api_response["command"], api_response["response"])
                else:
                    result = api_response["response"]

            console.print()
            console.print(Text(result, style="white"))
            console.print(Rule())

        except KeyboardInterrupt:
            console.print()
            console.print(Text("¡Hasta luego! 👋", style="green"))
            break
        except Exception as e:
            console.print(Text(f"❌ Error: {e}", style="red"))
            console.print(Rule())


@app.command
def ask(prompt: str):
    """Ask Lilith a question (non-interactive mode)"""
    print_banner()

    if not prompt:
        console.print(Text("Debes proporcionar una pregunta", style="red"))
        return

    console.print(Text(f"🔍 Pregunta: {prompt}", style="cyan"))
    console.print()

    command = find_command(prompt)

    if command:
        console.print(Text(f"⚡ Ejecutando: {command}", style="cyan"))
        result = COMMANDS[command]()
    else:
        api_response = call_lilith_api(prompt)

        if api_response.get("command"):
            result = execute_command(api_response["command"], api_response["response"])
        else:
            result = api_response["response"]

    console.print(result)


@app.command
def run(cmd: str):
    """Run a specific command"""
    print_banner()

    if cmd in COMMANDS:
        console.print(Text(f"⚡ Ejecutando: {cmd}", style="cyan"))
        result = COMMANDS[cmd]()
        console.print(result)
    else:
        console.print(Text(f"Comando desconocido: {cmd}", style="red"))


# ── Main Entry Point ───────────────────────────────────────────
if __name__ == "__main__":
    try:
        # Try to import psutil for system monitoring
        try:
            import psutil
        except ImportError:
            console.print(Text("⚠️ psutil no está instalado. Instalando...", style="yellow"))
            import subprocess

            subprocess.run("uv pip install psutil", shell=True)

        app()
    except KeyboardInterrupt:
        console.print()
        console.print(Text("Lilith CLI stopped by user", style="yellow"))
    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))
        if os.getenv("DEBUG"):
            import traceback

            console.print(traceback.format_exc())
