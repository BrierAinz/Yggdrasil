#!/usr/bin/env python3
"""
Yggdrasil CLI - El Arbol Sagrado que conecta los nueve reinos

Uso:
  python yggdrasil_cli.py           # Menu interactivo (launch)
  python yggdrasil_cli.py launch     # Menu interactivo
  python yggdrasil_cli.py status     # Estado de salud de los reinos
  python yggdrasil_cli.py clean      # Limpiar basura regenerable
  python yggdrasil_cli.py backup     # Crear backup de Svartalfheim + configs
  python yggdrasil_cli.py purge      - Purgar cuarentena de Helheim
  python yggdrasil_cli.py size       - Mostrar tamano por reino
  python yggdrasil_cli.py tree       - Arbol de proyectos
  python yggdrasil_cli.py test       - Ejecutar pytest
  python yggdrasil_cli.py sync       - Ejecutar sincronizacion
  python yggdrasil_cli.py api        - Levantar API de Lilith
  python yggdrasil_cli.py health     - Verificar README.md en cada reino
python yggdrasil_cli.py migrate    # Migrar proyecto entre reinos (interactivo)
  python yggdrasil_cli.py update    # Actualizar Yggdrasil (git pull + deps)
"""

import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from cyclopts import App
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree


# ── Theme & Console ──────────────────────────────────────────────
yggdrasil_theme = Theme(
    {
        "realm": "gold1",
        "error": "red",
        "success": "green",
        "warning": "yellow",
        "info": "cyan",
    }
)

console = Console(theme=yggdrasil_theme)

# ── Constants ────────────────────────────────────────────────────
YGGDRASIL_ROOT = Path(__file__).parent.resolve()

REALMS = [
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

JUNK_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    "node_modules",
    ".npm",
    ".next",
    "dist",
    "build",
    "*.map",
    ".turbo",
    ".parcel-cache",
    ".cache",
]

REALM_COLORS = {
    "Asgard": "gold1",
    "Vanaheim": "green",
    "Alfheim": "bright_blue",
    "Svartalfheim": "dark_orange",
    "Muspelheim": "red",
    "Helheim": "grey50",
    "Niflheim": "cyan",
    "Jotunheim": "magenta",
    "Midgard": "white",
}

# ── Service definitions ──────────────────────────────────────────
# Each service: key, display name, emoji, description, check callable (returns bool if running)
# start callable: launches the service


def _is_port_open(port: int, host: str = "localhost") -> bool:
    """Check if a port is in use (service running)."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def _is_wsl() -> bool:
    """Check if running under WSL."""
    return platform.system() == "Linux" and "microsoft" in platform.release().lower()


def _run_in_new_terminal(title: str, cmd: str, cwd: str):
    """Launch a command in a new terminal window (cross-platform)."""
    system = platform.system()

    if system == "Windows":
        # Windows: use 'start' to open a new cmd window
        bat_content = f'''@echo off
chcp 65001 >nul
title {title}
cd /d "{cwd}"
{cmd}
echo.
echo Presiona una tecla para cerrar...
pause >nul
'''
        bat_path = YGGDRASIL_ROOT / f"_launch_{title.replace(' ', '_')}.bat"
        bat_path.write_text(bat_content, encoding="utf-8")
        subprocess.Popen(["cmd", "/c", "start", f'"{title}"', str(bat_path)])
    elif _is_wsl():
        # WSL: use cmd.exe /c start to open a Windows terminal
        win_cwd = _wsl_to_windows_path(cwd)
        bat_content = f'''@echo off
chcp 65001 >nul
title {title}
cd /d "{win_cwd}"
wsl -e bash -c "cd {cwd} && {cmd}"
echo.
echo Presiona una tecla para cerrar...
pause >nul
'''
        bat_path = YGGDRASIL_ROOT / f"_launch_{title.replace(' ', '_')}.bat"
        bat_path.write_text(bat_content, encoding="utf-8")
        subprocess.Popen(
            ["cmd.exe", "/c", "start", f'"{title}"', str(bat_path)],
            cwd=str(YGGDRASIL_ROOT),
        )
    else:
        # Linux/Mac: try x-terminal-emulator, xterm, etc.
        for term_cmd in [
            ["gnome-terminal", "--", "bash", "-c", f"cd '{cwd}'; {cmd}; exec bash"],
            ["x-terminal-emulator", "-e", f"bash -c 'cd {cwd}; {cmd}; exec bash'"],
            ["xterm", "-e", f"bash -c 'cd {cwd}; {cmd}; exec bash'"],
        ]:
            try:
                subprocess.Popen(term_cmd)
                return
            except FileNotFoundError:
                continue
        console.print("[error]No se encontro un terminal compatible.[/]")


def _wsl_to_windows_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path."""
    try:
        result = subprocess.run(
            ["wslpath", "-w", wsl_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        # Fallback: manual conversion
        if wsl_path.startswith("/mnt/"):
            drive = wsl_path[5].upper()
            rest = wsl_path[6:]
            return f"{drive}:{rest}".replace("/", "\\")
        return wsl_path


SERVICES = {
    "studio": {
        "name": "YggdrasilStudio",
        "emoji": "\U0001f33f",
        "desc": "AI Image Generation Studio (FastAPI :8080 + Vite :5173)",
        "port": 8080,
        "frontend_port": 5173,
        "realm": "Alfheim/YggdrasilStudio",
        "check_cmd": "backend/main.py",
        "wsl_cmd": "cd Alfheim/YggdrasilStudio && bash start.sh",
        "win_cmd": "scripts/start_studio.bat",
    },
    "forge": {
        "name": "YggdrasilForge",
        "emoji": "\u2692\ufe0f",
        "desc": "3D Asset Studio (FastAPI :8081 + Vite :5174)",
        "port": 8081,
        "frontend_port": 5174,
        "realm": "Alfheim/YggdrasilForge",
        "check_cmd": "backend/main.py",
        "wsl_cmd": "cd Alfheim/YggdrasilForge && bash start.sh all",
        "win_cmd": "",
    },
    "lilith": {
        "name": "Lilith Agent",
        "emoji": "\U0001f916",
        "desc": "AI Agent Ecosystem (FastAPI :8000)",
        "port": 8000,
        "realm": "Asgard/Lilith",
        "check_cmd": "Core/Backend/main.py",
        "wsl_cmd": (
            "cd Asgard/Lilith && bash -c "
            "'python3 -m uvicorn lilith_api.main:app --reload --port 8000'"
        ),
        "win_cmd": "scripts/bats/Lilith_Launcher.bat",
    },
    "dashboard": {
        "name": "Terminal Dashboard",
        "emoji": "\U0001f4ca",
        "desc": "Hermes Metrics Dashboard",
        "port": 3000,
        "realm": "Alfheim/TerminalDashboard",
        "check_cmd": "package.json",
        "wsl_cmd": "cd Alfheim/TerminalDashboard && npm run dev",
        "win_cmd": "",
    },
    "comfyui": {
        "name": "ComfyUI",
        "emoji": "\U0001f3a8",
        "desc": "Stable Diffusion Workflow Engine (:8188)",
        "port": 8188,
        "realm": "Muspelheim/ComfyUI",
        "check_cmd": "main.py",
        "wsl_cmd": "cd Muspelheim/ComfyUI && python3 main.py --listen 0.0.0.0 --port 8188",
        "win_cmd": "",
    },
}

# ── Cyclopts App ────────────────────────────────────────────────
app = App(
    name="yggdrasil",
    help="Yggdrasil CLI - El Arbol Sagrado que conecta los nueve reinos",
)


# ── Banner ───────────────────────────────────────────────────────
def print_banner():
    """Imprimir el banner principal de Yggdrasil con animación."""
    # Animación de aparición gradual
    tree_art = Text()
    tree_art.append("        ┌───•   ", style="bold gold1")
    tree_art.append("YGGDRASIL", style="bold red on grey15")
    tree_art.append("   •───┐\n", style="bold gold1")
    tree_art.append("        │  ", style="green")
    tree_art.append("The World Tree CLI", style="italic gold1")
    tree_art.append("  │\n", style="green")
    tree_art.append("    ╔═══╧═══════════════╧═══╗\n", style="bold gold1")
    tree_art.append("    ║  Roots deep in code   ║\n", style="gold1")
    tree_art.append("    ║  Branches reach all   ║\n", style="gold1")
    tree_art.append("    ║  Nine Realms below    ║\n", style="gold1")
    tree_art.append("    ╚═══════════════════════╝", style="bold gold1")

    # Animación de aparición
    console.print()
    with Progress(
        SpinnerColumn(spinner_name="dots12"),
        TextColumn("[dim]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description="Conectando con los nueve reinos...", total=None)
        time.sleep(0.3)
        progress.update(task, description="Cargando el Árbol del Mundo...")
        time.sleep(0.3)
        progress.update(task, description="Desbloqueando las runas de poder...")
        time.sleep(0.4)

    # Imprimir el banner
    console.print(
        Panel(
            tree_art,
            title="[bold red]⚔ Yggdrasil ⚔[/]",
            subtitle="[dim]v3.0 — The Sacred Tree[/]",
            border_style="gold1",
            expand=False,
        )
    )

    # Línea decorativa con runas
    runes = Text()
    runes.append("ᛈ ", style="red")
    runes.append("ᛉ ", style="green")
    runes.append("ᛊ ", style="blue")
    runes.append("ᛏ ", style="yellow")
    runes.append("ᛒ ", style="cyan")
    runes.append("ᛖ ", style="magenta")
    runes.append("ᛗ ", style="bold white")
    console.print(runes)
    console.print()


# ── Service status helper ────────────────────────────────────────
def get_service_status(key: str) -> dict:
    """Get detailed status of a service."""
    svc = SERVICES[key]
    realm_path = YGGDRASIL_ROOT / svc["realm"]
    port = svc["port"]

    exists = realm_path.exists()
    if not exists:
        return {
            "key": key,
            "name": svc["name"],
            "emoji": svc["emoji"],
            "installed": False,
            "running": False,
            "port": port,
            "desc": svc["desc"],
        }

    running = _is_port_open(port)
    frontend_running = False
    if "frontend_port" in svc:
        frontend_running = _is_port_open(svc["frontend_port"])

    return {
        "key": key,
        "name": svc["name"],
        "emoji": svc["emoji"],
        "installed": True,
        "running": running,
        "frontend_running": frontend_running,
        "port": port,
        "desc": svc["desc"],
        "realm": svc["realm"],
    }


@app.command
def chat():
    """Chat interactivo con el agente Lilith. Si se ejecuta sin comandos, este es el predeterminado."""
    print_banner()
    console.print("[bold gold1]╭──────────────────────────────────────────────────────────────╮[/]")
    console.print("[bold gold1]│                                                              │[/]")
    console.print(
        "[bold gold1]│[/] [bold red]⚔[/] [bold gold1]Bienvenido al Chat con Lilith, la diosa de Yggdrasil[/] [bold red]⚔[/] [bold gold1]│[/]"
    )
    console.print("[bold gold1]│                                                              │[/]")
    console.print(
        "[bold gold1]│[/] [dim]Escribe 'salir' o 'quit' para terminar la conversación[/] [bold gold1]│[/]"
    )
    console.print(
        "[bold gold1]│[/] [dim]Escribe 'ayuda' para ver los comandos disponibles[/] [bold gold1]│[/]"
    )
    console.print("[bold gold1]╰──────────────────────────────────────────────────────────────╯[/]")
    console.print()

    try:
        # Cargar variables de entorno desde .env
        if os.path.exists(".env"):
            with open(".env", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        from lilith_core.config import Config
        from lilith_memory.store import MemoryStore
        from lilith_orchestrator.engine import LilithEngine

        config = Config()
        memory = MemoryStore(config.root / "chat_memory.db")
        engine = LilithEngine(config, memory)

        # Animación de bienvenida
        welcome_text = Text(
            "Lilith está despertando desde las profundidades de Yggdrasil...", style="italic gold1"
        )
        console.print(welcome_text)
        time.sleep(0.5)

        # Indicator de conectividad
        with Progress(
            SpinnerColumn(spinner_name="arc"),
            TextColumn("[dim]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(
                description="Conectando con las raíces de Yggdrasil...", total=None
            )
            time.sleep(0.8)
            progress.update(task, description="Cargando conocimientos de los nueve reinos...")
            time.sleep(0.5)
            progress.update(task, description="Estableciendo conexión con el Mundo Profundo...")
            time.sleep(0.3)

        console.print()
        console.print(
            "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )
        console.print("[success]✅[/] [bold realm]Lilith está lista para ayudarte[/]")
        console.print("[info]ℹ️[/] [dim]Modelo activo: BytePlus/ark-code-latest[/]")
        console.print("[info]ℹ️[/] [dim]Perfil: byteplus-lite[/]")
        console.print(
            "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )
        console.print()

        while True:
            # Prompt personalizado con emblema de Yggdrasil
            user_input = Prompt.ask("[bold cyan]╭───•[/] [bold white]Tú[/] [bold cyan]•───╮[/]")

            if user_input.lower() in ["salir", "quit", "exit", "q"]:
                console.print()
                console.print("[dim]Odin te guie. Hasta la próxima conversación![/]")
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                break

            if user_input.lower() == "ayuda":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Comandos disponibles:[/]")
                console.print("  [cyan]salir/quit/exit/q[/] - Terminar la conversación")
                console.print("  [cyan]ayuda[/] - Mostrar esta ayuda")
                console.print("  [cyan]resumen[/] - Ver resumen de la conversación")
                console.print("  [cyan]memoria[/] - Ver las ultimas entradas de memoria")
                console.print("  [cyan]buscar[/] - Búsqueda semántica en la memoria")
                console.print("  [cyan]analizar[/] - Analizar patrones de conversación")
                console.print("  [cyan]skills[/] - Gestionar skills (crear/actualizar/listar)")
                console.print("  [cyan]mejora[/] - Automejora inteligente")
                console.print("  [cyan]exportar[/] - Exportar memoria")
                console.print("  [cyan]importar[/] - Importar memoria")
                console.print("  [cyan]borrar[/] - Borrar la memoria")
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "buscar":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Búsqueda Semántica[/]")

                query = Prompt.ask("[bold cyan]Consulta[/]")
                limit = int(Prompt.ask("[bold cyan]Número máximo de resultados[/]", default="5"))

                try:
                    from advanced_memory import AdvancedMemoryStore

                    adv_memory = AdvancedMemoryStore()
                    results = adv_memory.search_semantic(query, limit=limit)

                    if results:
                        console.print()
                        for i, result in enumerate(results, 1):
                            similarity = result["similarity"] * 100
                            clean_content = (
                                result["content"].replace("Usuario: ", "").replace("Lilith: ", "")
                            )
                            if len(clean_content) > 100:
                                clean_content = clean_content[:100] + "..."
                            console.print(
                                f"[cyan]{i}.[/] [dim][{similarity:.1f}%][/] {clean_content}"
                            )
                    else:
                        console.print("[dim]No se encontraron resultados relevantes[/]")

                except Exception as e:
                    console.print(f"[error]❌ Error en búsqueda semántica: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "analizar":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Análisis de Patrones[/]")

                limit = int(
                    Prompt.ask("[bold cyan]Número de conversaciones a analizar[/]", default="50")
                )

                try:
                    from advanced_memory import AdvancedMemoryStore

                    adv_memory = AdvancedMemoryStore()
                    analysis = adv_memory.analyze_conversation_patterns(limit=limit)

                    console.print()
                    console.print(f"[info]ℹ️[/] [dim]Total entradas: {analysis['total_entries']}[/]")
                    console.print(
                        f"[info]ℹ️[/] [dim]Entradas de usuario: {analysis['user_entries']}[/]"
                    )
                    console.print(
                        f"[info]ℹ️[/] [dim]Entradas de asistente: {analysis['assistant_entries']}[/]"
                    )
                    console.print(
                        f"[info]ℹ️[/] [dim]Longitud promedio: {analysis['avg_length']:.1f} caracteres[/]"
                    )

                    if analysis["topics"]:
                        console.print(
                            f"[info]ℹ️[/] [dim]Temas detectados: {', '.join(analysis['topics'])}[/]"
                        )

                    if analysis["frequent_words"]:
                        console.print("\n[bold gold1]Palabras frecuentes:[/]")
                        for word, count in analysis["frequent_words"].items():
                            console.print(f"  [cyan]{word}[/]: {count}")

                except Exception as e:
                    console.print(f"[error]❌ Error en análisis de patrones: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "skills":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Gestionar Skills[/]")

                subchoice = Prompt.ask(
                    "[bold cyan]Acción[/]", choices=["crear", "actualizar", "listar", "eliminar"]
                )

                try:
                    from skill_creator import SkillCreator

                    creator = SkillCreator()

                    if subchoice == "crear":
                        category = Prompt.ask("[bold cyan]Categoría[/]", default="general")
                        limit = int(
                            Prompt.ask("[bold cyan]Número de conversaciones[/]", default="100")
                        )
                        created = creator.create_skills_from_conversations(
                            category=category, limit=limit
                        )
                        console.print(f"[success]✅[/] Skills creados: {len(created)}")

                    elif subchoice == "actualizar":
                        limit = int(
                            Prompt.ask("[bold cyan]Número de conversaciones[/]", default="50")
                        )
                        updated = creator.update_existing_skills(limit=limit)
                        console.print(f"[success]✅[/] Skills actualizados: {len(updated)}")

                    elif subchoice == "listar":
                        skills = creator.list_skills()
                        console.print()
                        for skill in skills:
                            console.print(f"[cyan]{skill['name']}[/] ({skill['category']})")
                            if "description" in skill["metadata"]:
                                console.print(f"  {skill['metadata']['description']}")
                        console.print(f"Total: {len(skills)} skills")

                    elif subchoice == "eliminar":
                        skill_name = Prompt.ask("[bold cyan]Nombre del skill[/]")
                        if creator.delete_skill(skill_name):
                            console.print("[success]✅[/] Skill eliminado")
                        else:
                            console.print("[error]❌ Skill no encontrado[/]")

                except Exception as e:
                    console.print(f"[error]❌ Error en gestión de skills: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "mejora":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Automejora Inteligente[/]")

                subchoice = Prompt.ask(
                    "[bold cyan]Acción[/]", choices=["analizar", "ejecutar", "ver_informe"]
                )

                try:
                    from auto_improvement import AutoImprovement

                    auto = AutoImprovement()

                    if subchoice == "analizar":
                        limit = int(
                            Prompt.ask("[bold cyan]Número de conversaciones[/]", default="100")
                        )
                        improvements = auto.analyze_conversations(limit=limit)

                        if improvements:
                            console.print()
                            for i, improvement in enumerate(improvements, 1):
                                type_name = auto._get_type_name(improvement["type"])
                                console.print(
                                    f"[cyan]{i}.[/] [{type_name}] {improvement['content']}"
                                )
                        else:
                            console.print("[dim]No se encontraron oportunidades de mejora[/]")

                    elif subchoice == "ejecutar":
                        report = auto.run_complete_analysis()

                        console.print()
                        auto.print_simple_report(report)

                    elif subchoice == "ver_informe":
                        from pathlib import Path

                        reports_dir = Path("/mnt/d/Proyectos/Yggdrasil")
                        reports = list(reports_dir.glob("autoimprovement_report_*.json"))

                        if reports:
                            latest_report = max(reports, key=lambda x: x.stat().st_mtime)
                            with open(latest_report, encoding="utf-8") as f:
                                import json

                                report = json.load(f)
                            console.print()
                            auto.print_simple_report(report)
                        else:
                            console.print("[dim]No hay informes de automejora disponibles[/]")

                except Exception as e:
                    console.print(f"[error]❌ Error en automejora: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "exportar":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Exportar Memoria[/]")

                format = Prompt.ask(
                    "[bold cyan]Formato[/]", choices=["json", "csv", "markdown"], default="json"
                )

                try:
                    from advanced_memory import AdvancedMemoryStore

                    adv_memory = AdvancedMemoryStore()
                    file_path = adv_memory.export_memory(format=format)
                    console.print(f"[success]✅[/] Memoria exportada: {file_path}")

                except Exception as e:
                    console.print(f"[error]❌ Error en exportación: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "importar":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Importar Memoria[/]")

                file_path = Prompt.ask("[bold cyan]Ruta del archivo[/]")

                try:
                    from advanced_memory import AdvancedMemoryStore

                    adv_memory = AdvancedMemoryStore()
                    imported = adv_memory.import_memory(file_path)
                    console.print(f"[success]✅[/] Entradas importadas: {imported}")

                except Exception as e:
                    console.print(f"[error]❌ Error en importación: {e}[/]")

                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "resumen":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Resumen de la Conversación[/]")
                summary = memory.summary()
                console.print(f"[info]ℹ️[/] [dim]Total mensajes: {summary['total_entries']}[/]")
                console.print(f"[info]ℹ️[/] [dim]Total tokens: {summary['total_tokens']}[/]")
                console.print(
                    f"[info]ℹ️[/] [dim]Tokens promedio por entrada: {summary['avg_tokens_per_entry']}[/]"
                )
                if summary["duration_minutes"] > 0:
                    console.print(
                        f"[info]ℹ️[/] [dim]Duración: ~{summary['duration_minutes']} minutos[/]"
                    )
                if summary["topics"]:
                    console.print(f"[info]ℹ️[/] [dim]Temas clave: {', '.join(summary['topics'])}[/]")
                console.print()
                console.print(f"[dim]{summary['summary_text']}[/]")
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "memoria":
                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print("[bold gold1]Últimas Entradas de Memoria[/]")
                recent = memory.recent(limit=10)
                if recent:
                    for entry in recent:
                        timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
                        content = entry["content"]
                        if len(content) > 100:
                            content = content[:100] + "..."
                        console.print(f"[dim]{timestamp}[/] - {content}")
                else:
                    console.print("[dim]No hay entradas de memoria.[/]")
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                console.print()
                continue

            if user_input.lower() == "borrar":
                console.print()
                if Confirm.ask("¿Estás seguro de que quieres borrar toda la memoria?"):
                    memory.clear()
                    console.print("[success]✅[/] Memoria borrada correctamente")
                else:
                    console.print("[info]ℹ️[/] Operación cancelada")
                console.print()
                continue

            if not user_input.strip():
                continue

            try:
                console.print()
                # Animación de procesamiento con detalles
                with Progress(
                    SpinnerColumn(spinner_name="pong"),
                    TextColumn("[dim]{task.description}"),
                    transient=True,
                ) as progress:
                    task = progress.add_task(
                        description="Lilith está consultando el Bosque de los Conocimientos...",
                        total=None,
                    )
                    time.sleep(0.5)
                    progress.update(task, description="Analizando el fluido de la Norn...")
                    time.sleep(0.8)
                    progress.update(task, description="Interpretando runas en el viento...")
                    result = engine.process(user_input)

                console.print()
                console.print(
                    "[bold gold1]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
                )
                # Animación de escritura para la respuesta
                lilith_response = Text("[bold red]Lilith[/]: ", style="bold red")
                lilith_response.append(result["response"], style="italic white")
                console.print(lilith_response)
                console.print()

                # Indicador visual de tokens usados (simulado para efecto)
                tokens_used = len(result["response"]) * 1.2  # Simulación
                tokens_percent = min(int(tokens_used / 256 * 100), 100)
                progress_bar = Text()
                progress_bar.append("Tokens usados: ", style="dim")
                progress_bar.append(
                    f"{'█' * (tokens_percent // 10)}{'░' * (10 - (tokens_percent // 10))}",
                    style="cyan",
                )
                progress_bar.append(f" {tokens_percent}%", style="dim")
                console.print(progress_bar)
                console.print()

            except Exception as e:
                console.print()
                console.print(f"[error]❌ Error: {e}[/]")
                console.print()

    except Exception as e:
        console.print(f"[error]❌ No se pudo iniciar Lilith: {e}[/]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/]")


# ── Make chat the default command ──────────────────────────────────
@app.default
def default():
    """Comando predeterminado: chat interactivo con Lilith."""
    chat()


@app.command
def launch():
    """Abrir menu interactivo para lanzar servicios de Yggdrasil."""
    print_banner()

    while True:
        # Gather statuses
        statuses = [get_service_status(key) for key in SERVICES]

        # Build menu table
        table = Table(
            title="\U0001f332 Yggdrasil Launcher",
            show_header=True,
            header_style="bold gold1",
            border_style="gold1",
            title_style="bold red",
            expand=True,
        )
        table.add_column("#", style="bold", width=3)
        table.add_column("Servicio", style="bold", min_width=18)
        table.add_column("Estado", min_width=12)
        table.add_column("Puerto", justify="center", min_width=14)
        table.add_column("Descripcion", style="dim", min_width=30)

        for i, svc in enumerate(statuses, 1):
            if not svc["installed"]:
                status_str = "[dim]NO INSTALADO[/]"
                port_str = "[dim]—[/]"
            elif svc["running"]:
                if svc.get("frontend_running"):
                    status_str = "[bold green]\u25cf ACTIVO (full)[/]"
                else:
                    status_str = "[green]\u25cf ACTIVO[/]"
                port_str = f"[green]:{svc['port']}[/]"
            else:
                status_str = "[yellow]\u25cb DETENIDO[/]"
                port_str = f":{svc['port']}"

            table.add_row(
                str(i),
                f"{svc['emoji']} {svc['name']}",
                status_str,
                port_str,
                svc["desc"],
            )

        console.print(table)
        console.print()

        # Additional options
        console.print("  [bold gold1]0.[/] Salir")
        console.print("  [bold gold1]R.[/] Refrescar estado")
        console.print("  [bold gold1]S.[/] Detener todos los servicios")
        console.print("  [bold gold1]A.[/] Lanzar todos los instalados")
        console.print()

        choice = Prompt.ask(
            "[bold realm]\u2694 Selecciona[/]",
            default="0",
        )

        if choice.lower() == "0":
            console.print("[dim]Odin te guie. Hasta la proxima.[/]")
            break

        if choice.lower() == "r":
            console.print("[info]Refrescando...[/]\n")
            continue

        if choice.lower() == "s":
            _stop_all_services()
            console.print()
            continue

        if choice.lower() == "a":
            _start_all_installed()
            console.print()
            continue

        # Numeric choice
        try:
            idx = int(choice) - 1
        except ValueError:
            console.print("[error]Opcion invalida.[/]\n")
            continue

        if idx < 0 or idx >= len(statuses):
            console.print("[error]Opcion invalida.[/]\n")
            continue

        svc = statuses[idx]
        if not svc["installed"]:
            console.print(
                f"[warning]{svc['name']} no esta instalado en {svc.get('realm', '?')}.[/]\n"
            )
            continue

        if svc["running"]:
            # Already running — offer to stop or restart
            console.print(
                f"\n[info]{svc['emoji']} {svc['name']} ya esta corriendo en :{svc['port']}[/]"
            )
            action = Prompt.ask(
                "Que hacer?",
                choices=["r", "s", "c"],
                default="c",
            )
            if action == "r":
                _stop_service(svc["key"])
                console.print("[info]Detenido. Reiniciando...[/]")
                _start_service(svc["key"])
            elif action == "s":
                _stop_service(svc["key"])
            else:
                pass
        else:
            _start_service(svc["key"])

        console.print()


def _start_service(key: str):
    """Start a single service."""
    svc = SERVICES[key]
    console.print(f"\n[bold realm]\u2692 Iniciando {svc['emoji']} {svc['name']}...[/]")

    realm_path = YGGDRASIL_ROOT / svc["realm"]
    cmd = svc.get("wsl_cmd", "")

    if _is_wsl():
        # In WSL, we launch in a new Windows terminal
        _run_in_new_terminal(
            title=f"Yggdrasil - {svc['name']}",
            cmd=cmd,
            cwd=str(realm_path),
        )
        console.print(f"[success]\u2713 {svc['name']} lanzado en nueva ventana[/]")
    # Native: try to launch
    elif platform.system() == "Windows":
        # Windows native
        _run_in_new_terminal(
            title=f"Yggdrasil - {svc['name']}",
            cmd=f"python {svc.get('check_cmd', '')}",
            cwd=str(realm_path),
        )
    else:
        # Linux/Mac - just tell the user
        console.print("[info]Ejecuta en otro terminal:[/]")
        console.print(f"[bold]  cd {realm_path} && {cmd}[/]")

    # Wait a moment and check
    time.sleep(2)
    if _is_port_open(svc["port"]):
        console.print(f"[success]\u2713 {svc['name']} esta activo en :{svc['port']}[/]")
        if "frontend_port" in svc and _is_port_open(svc["frontend_port"]):
            console.print(f"[success]\u2713 Frontend activo en :{svc['frontend_port']}[/]")
    else:
        console.print(f"[warning]  Esperando a que {svc['name']} levante en :{svc['port']}...[/]")
        console.print("[dim]  Puede tardar unos segundos en estar listo.[/]")


def _stop_service(key: str):
    """Stop a service by killing processes on its port."""

    svc = SERVICES[key]
    port = svc["port"]
    console.print(f"[warning]Deteniendo {svc['name']} en :{port}...[/]")

    if _is_wsl() or platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid.strip():
                    subprocess.run(["kill", pid.strip()], timeout=5)
            console.print(f"[success]\u2713 {svc['name']} detenido[/]")
        except Exception:
            try:
                # Try fuser
                subprocess.run(["fuser", "-k", f"{port}/tcp"], timeout=5)
                console.print(f"[success]\u2713 {svc['name']} detenido[/]")
            except Exception:
                console.print(
                    f"[warning]No se pudo detener automaticamente. Busca procesos en :{port}[/]"
                )
    else:
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], timeout=5)
            console.print(f"[success]\u2713 {svc['name']} detenido[/]")
        except Exception:
            console.print("[warning]No se pudo detener automaticamente.[/]")


def _start_all_installed():
    """Start all installed services that aren't running."""
    console.print("[bold realm]\u2692 Iniciando todos los servicios instalados...[/]\n")
    for key in SERVICES:
        svc = get_service_status(key)
        if svc["installed"] and not svc["running"]:
            _start_service(key)
            console.print()
        elif not svc["installed"]:
            console.print(f"[dim]\u25cb {svc['name']} no instalado — saltando[/]")
        else:
            console.print(f"[green]\u25cf {svc['name']} ya activo[/]")


def _stop_all_services():
    """Stop all running services."""
    console.print("[bold warning]Deteniendo todos los servicios...[/]\n")
    for key in SERVICES:
        svc = get_service_status(key)
        if svc["running"]:
            _stop_service(key)
    console.print("[success]\u2713 Todos los servicios detenidos.[/]")


# ── Helpers ──────────────────────────────────────────────────────
def _human_size(size_bytes: int) -> str:
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.1f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.0f} MB"
    else:
        return f"{size_bytes / 1024:.0f} KB"


def _du_bytes(path: Path) -> int:
    try:
        out = subprocess.run(
            ["du", "-sb", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
        return int(out.split()[0])
    except Exception:
        return 0


def _count_files(path: Path, pattern: str = "") -> int:
    cmd = ["find", str(path), "-type", "f"]
    if pattern:
        cmd += ["-name", pattern]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout
        return len([line for line in out.splitlines() if line.strip()])
    except Exception:
        return 0


# ── Commands ────────────────────────────────────────────────────
@app.command
def status():
    """Estado de salud de todos los reinos y servicios."""
    console.print(Rule("[bold realm]\u2694 Realm Status Report \u2694[/]", style="gold1"))

    table = Table(
        title="Nine Realms of Yggdrasil",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
        title_style="bold red",
    )
    table.add_column("Reino", style="realm", min_width=14)
    table.add_column("Estado", min_width=10)
    table.add_column("Tama\u00f1o", justify="right", min_width=10)
    table.add_column("Proyectos", justify="center", min_width=10)

    total_size = 0

    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        color = REALM_COLORS.get(realm, "white")

        if not rpath.exists():
            table.add_row(
                f"[{color}]{realm}[/]",
                "[error]NO EXISTE[/]",
                "\u2014",
                "\u2014",
            )
            continue

        size_bytes = _du_bytes(rpath)
        total_size += size_bytes

        # Count projects (dirs, not hidden)
        projects = [d for d in rpath.iterdir() if d.is_dir() and not d.name.startswith(".")]
        proj_count = len(projects)

        if proj_count > 2:
            status_str = "ACTIVO"
            status_style = "success"
        elif realm in ("Jotunheim", "Midgard") and proj_count <= 2:
            status_str = "RESERVADO"
            status_style = "info"
        elif realm == "Helheim":
            status_str = "ARCHIVO"
            status_style = "dim"
        else:
            status_str = "VACIO"
            status_style = "warning"

        size_display = _human_size(size_bytes) if size_bytes else "\u2014"
        proj_display = str(proj_count) if proj_count else "\u2014"

        table.add_row(
            f"[{color}]{realm}[/]",
            f"[{status_style}]{status_str}[/]",
            size_display,
            proj_display,
        )

    console.print(table)
    console.print(Rule(style="gold1"))

    # Total line
    console.print(f"  [bold realm]TOTAL[/]  \u2502  [bold]{_human_size(total_size)}[/]")
    console.print(Rule(style="gold1"))

    # Services status
    console.print("\n[bold realm]\u2694 Servicios[/]")
    for key in SERVICES:
        svc = get_service_status(key)
        if svc["installed"]:
            if svc["running"]:
                status = f"[bold green]\u25cf ACTIVO[/] :{svc['port']}"
            else:
                status = f"[yellow]\u25cb DETENIDO[/] :{svc['port']}"
        else:
            status = "[dim]\u25cb No instalado[/]"
        console.print(f"  {svc['emoji']} {svc['name']}: {status}")

    # Quarantine check
    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if q.exists():
        qs = _du_bytes(q)
        console.print()
        console.print(
            f"[bold error]\u26a0 CUARENTENA[/]: {_human_size(qs)} en Helheim/Quarantine_2026-04-29/"
        )
        console.print("  Ejecuta: [bold]yggdrasil purge[/] para eliminar")


@app.command
def size():
    """Mostrar tamano por reino en formato legible."""
    console.print(Rule("[bold realm]\u2694 Realm Sizes \u2694[/]", style="gold1"))

    table = Table(
        title="Realm Disk Usage",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
    )
    table.add_column("Reino", style="realm", min_width=14)
    table.add_column("Tama\u00f1o", justify="right", min_width=12)
    table.add_column("Tama\u00f1o Humano", justify="right", min_width=12)

    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue
        size_bytes = _du_bytes(rpath)
        color = REALM_COLORS.get(realm, "white")
        table.add_row(
            f"[{color}]{realm}[/]",
            f"{size_bytes:,} B",
            _human_size(size_bytes),
        )

    console.print(table)


@app.command
def tree():
    """Arbol de proyectos organizados por reino."""
    console.print(Rule("[bold realm]\u2694 Realm Hierarchy \u2694[/]", style="gold1"))

    world_tree = Tree(
        "[bold gold1]\U0001f30d Yggdrasil[/]",
        guide_style="gold1",
    )

    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            continue

        color = REALM_COLORS.get(realm, "white")
        realm_branch = world_tree.add(f"[{color}]{realm}[/]")

        for item in sorted(rpath.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                has_readme = (item / "README.md").exists()
                marker = "\U0001f4dc" if has_readme else "\U0001f4c1"
                label = f"[link={item}]{item.name}[/]" if has_readme else item.name
                realm_branch.add(f"{marker} {label}")

    console.print(world_tree)


@app.command
def clean():
    """Limpiar basura regenerable (pycache, node_modules, etc.)."""
    console.print(Rule("[bold realm]\u2694 Cleansing the Realms \u2694[/]", style="gold1"))

    cleaned = 0
    removed_items = []

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold realm]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Purging corruption...", total=None)
        for realm in REALMS:
            rpath = YGGDRASIL_ROOT / realm
            if not rpath.exists():
                continue
            for pattern in JUNK_PATTERNS:
                if pattern.startswith("*"):
                    for fpath in rpath.rglob(pattern[1:]):
                        if fpath.is_file():
                            try:
                                fpath.unlink()
                                cleaned += 1
                                removed_items.append(str(fpath.relative_to(YGGDRASIL_ROOT)))
                            except Exception:
                                pass
                    for dpath in rpath.rglob(pattern[1:]):
                        if dpath.is_dir() and dpath.name == pattern[1:]:
                            try:
                                shutil.rmtree(dpath)
                                cleaned += 1
                                removed_items.append(str(dpath.relative_to(YGGDRASIL_ROOT)))
                            except Exception:
                                pass
                else:
                    for dpath in rpath.rglob(pattern):
                        if dpath.is_dir():
                            try:
                                shutil.rmtree(dpath)
                                cleaned += 1
                                removed_items.append(str(dpath.relative_to(YGGDRASIL_ROOT)))
                            except Exception:
                                pass

    if removed_items:
        console.print("[dim]Removed:[/]")
        for item in removed_items[:20]:
            console.print(f"  [error]\u2717[/] [dim]{item}[/]")
        if len(removed_items) > 20:
            console.print(f"  [dim]... and {len(removed_items) - 20} more[/]")

    console.print(f"\n[bold success]\u2713 {cleaned}[/] items purged from the nine realms")


@app.command
def purge():
    """Purgar la cuarentena de Helheim (eliminacion permanente)."""
    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if not q.exists():
        console.print("[info]No hay cuarentena para purgar.[/]")
        return

    qs = _du_bytes(q)
    console.print(f"[bold error]\u26a0 PURGE[/]: Cuarentena detectada en {_human_size(qs)}")
    console.print(f"  Ruta: [dim]{q}[/]")

    if Confirm.ask("[bold warning]\u00bfEliminar permanentemente la cuarentena?[/]"):
        try:
            shutil.rmtree(q)
            console.print("[bold success]\u2713 Cuarentena eliminada del inframundo[/]")
        except Exception as e:
            console.print(f"[bold error]\u2717 Error: {e}[/]")
    else:
        console.print("[warning]Purga cancelada.[/]")


@app.command
def backup():
    """Crear backup de Svartalfheim + configs."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = YGGDRASIL_ROOT / f"backup_{ts}"
    backup_dir.mkdir(exist_ok=True)

    console.print(Rule("[bold realm]\u2694 Creating Realm Backup \u2694[/]", style="gold1"))
    console.print(f"[info]Destino:[/] [dim]{backup_dir}[/]")

    backed_up = []

    with Progress(
        SpinnerColumn("line"),
        TextColumn("[bold realm]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Archiving Svartalfheim...", total=None)

        # Backup Svartalfheim (docs)
        src = YGGDRASIL_ROOT / "Svartalfheim"
        dst = backup_dir / "Svartalfheim"
        if src.exists():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
            backed_up.append(("Svartalfheim", "realm"))

        # Backup configs
        env = YGGDRASIL_ROOT / ".env"
        if env.exists():
            shutil.copy2(env, backup_dir / ".env")
            backed_up.append((".env", "config"))

        # Backup reglas
        progress.update(task, description="Archiving configs...")
        for f in ["REGLAS_YGGDRASIL.md", "setup_yggdrasil.py", "yggdrasil_cli.py"]:
            srcf = YGGDRASIL_ROOT / f
            if srcf.exists():
                shutil.copy2(srcf, backup_dir / f)
                backed_up.append((f, "file"))

    console.print()
    for name, kind in backed_up:
        console.print(f"  [success]\u2713[/] [{kind}] {name}")

    console.print(f"\n[bold success]\u2713 Backup completo:[/] [dim]{backup_dir}[/]")


@app.command
def test():
    """Ejecutar pytest en la raiz de Yggdrasil."""
    console.print(Rule("[bold realm]\u2694 Running Tests \u2694[/]", style="gold1"))
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(YGGDRASIL_ROOT),
    )
    if result.returncode == 0:
        console.print("[bold success]\u2713 Tests passed[/]")
    else:
        console.print("[bold error]\u2717 Tests failed[/]")


@app.command
def sync():
    """Ejecutar sincronizacion de Yggdrasil."""
    console.print(Rule("[bold realm]\u2694 Syncing Realms \u2694[/]", style="gold1"))
    subprocess.run([sys.executable, str(YGGDRASIL_ROOT / "sync.py")])


@app.command
def api():
    """Levantar la API de Lilith con uvicorn."""
    console.print(Rule("[bold realm]\u2694 Awakening the API \u2694[/]", style="gold1"))
    console.print("[info]Starting Lilith API on http://localhost:8000[/]")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "lilith_api.main:app",
            "--reload",
            "--port",
            "8000",
        ],
    )


@app.command
def health():
    """Verificar que cada reino tiene su README.md."""
    console.print(Rule("[bold realm]\u2694 Realm Health Check \u2694[/]", style="gold1"))

    table = Table(
        title="Realm Readme Status",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
    )
    table.add_column("Reino", style="realm", min_width=14)
    table.add_column("README.md", min_width=12)
    table.add_column("Estado", min_width=12)

    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        color = REALM_COLORS.get(realm, "white")

        if not rpath.exists():
            table.add_row(
                f"[{color}]{realm}[/]",
                "[error]\u2014[/]",
                "[error]NO EXISTE[/]",
            )
            continue

        readme = rpath / "README.md"
        if readme.exists():
            size = readme.stat().st_size
            table.add_row(
                f"[{color}]{realm}[/]",
                f"[success]\u2713 presente[/] ({size} B)",
                "[success]SANO[/]",
            )
        else:
            table.add_row(
                f"[{color}]{realm}[/]",
                "[warning]ausente[/]",
                "[warning]SIN README[/]",
            )

    console.print(table)


@app.command
def update():
    """Actualizar Yggdrasil: git pull + instalar dependencias."""
    console.print(Rule("[bold realm]\u2694 Updating the World Tree \u2694[/]", style="gold1"))
    console.print()

    steps = [
        ("Git stash (si hay cambios locales)", ["git", "-C", str(YGGDRASIL_ROOT), "stash"]),
        ("Git pull (descargar cambios)", ["git", "-C", str(YGGDRASIL_ROOT), "pull"]),
        (
            "Git stash pop (restaurar cambios locales)",
            ["git", "-C", str(YGGDRASIL_ROOT), "stash", "pop"],
        ),
    ]

    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, timeout=5)
        steps.append(
            (
                "Instalando deps Python (uv pip install)",
                ["uv", "pip", "install", "-q", "rich", "cyclopts"],
            )
        )
        steps.append(
            (
                "Sincronizando paquetes (uv sync)",
                ["uv", "sync", "--all-packages", "--directory", str(YGGDRASIL_ROOT)],
            )
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        steps.append(
            (
                "Instalando deps Python (pip --user)",
                [sys.executable, "-m", "pip", "install", "--user", "-q", "rich", "cyclopts"],
            )
        )

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold realm]{task.description}"),
        console=console,
    ) as progress:
        for desc, cmd in steps:
            task = progress.add_task(desc, total=None)
            try:
                # git stash pop may fail if no stash — that's OK
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(YGGDRASIL_ROOT),
                )
                if (
                    "stash" in desc
                    and "pop" in desc
                    and result.returncode != 0
                    and ("No stash entries" in result.stderr or "does not exist" in result.stderr)
                ):
                    # No stash to pop is fine
                    progress.update(task, completed=True)
                    results.append((desc, "OK (no stash)", None))
                    continue
                if result.returncode != 0:
                    progress.update(task, completed=True)
                    results.append((desc, "FAIL", result.stderr[:200]))
                else:
                    progress.update(task, completed=True)
                    short_out = result.stdout.strip()[:100] if result.stdout.strip() else None
                    results.append((desc, "OK", short_out))
            except Exception as e:
                progress.update(task, completed=True)
                results.append((desc, "FAIL", str(e)[:200]))

    # Print summary
    console.print()
    table = Table(
        title="Update Summary",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
    )
    table.add_column("Paso", min_width=40)
    table.add_column("Resultado", min_width=12)
    table.add_column("Detalle", style="dim", min_width=30)

    for desc, status, detail in results:
        if status == "OK" or status.startswith("OK"):
            status_str = f"[success]{status}[/]"
        else:
            status_str = f"[error]{status}[/]"
        detail_str = (detail or "")[:60]
        table.add_row(desc, status_str, detail_str)

    console.print(table)
    console.print()
    console.print(
        "[bold realm]\u2713 Yggdrasil actualizado.[/] "
        "Ejecuta [bold]yggdrasil status[/] para verificar."
    )


@app.command
def migrate():
    """Migrar un proyecto entre reinos (interactivo)."""
    console.print(Rule("[bold realm]\u2694 Realm Migration Ritual \u2694[/]", style="gold1"))

    # Discover available source realms
    available_realms = [r for r in REALMS if (YGGDRASIL_ROOT / r).exists()]

    if not available_realms:
        console.print("[error]No hay reinos disponibles para migrar.[/]")
        return

    # Show available realms
    console.print("\n[bold]Reinos disponibles:[/]")
    for r in available_realms:
        color = REALM_COLORS.get(r, "white")
        rpath = YGGDRASIL_ROOT / r
        projects = [
            d.name for d in sorted(rpath.iterdir()) if d.is_dir() and not d.name.startswith(".")
        ]
        proj_str = ", ".join(projects[:5]) + ("..." if len(projects) > 5 else "")
        console.print(f"  [{color}]{r}[/]  [dim]({len(projects)} proyectos: {proj_str})[/]")

    # Source realm
    source = Prompt.ask(
        "\n[bold]Reino de origen[/]",
        choices=[r.lower() for r in available_realms],
    ).title()

    if source not in REALMS:
        console.print(f"[error]Reino desconocido: {source}[/]")
        return

    src_path = YGGDRASIL_ROOT / source
    projects = [d for d in sorted(src_path.iterdir()) if d.is_dir() and not d.name.startswith(".")]

    if not projects:
        console.print(f"[warning]{source} no tiene proyectos para migrar.[/]")
        return

    # Project selection
    console.print(f"\n[bold]Proyectos en {source}:[/]")
    for i, p in enumerate(projects, 1):
        has_readme = "\U0001f4dc" if (p / "README.md").exists() else "\U0001f4c1"
        console.print(f"  {i}. {has_readme} {p.name}")

    proj_idx = Prompt.ask(
        "[bold]Numero de proyecto[/]",
        choices=[str(i) for i in range(1, len(projects) + 1)],
    )
    project = projects[int(proj_idx) - 1]

    # Destination realm
    dest = Prompt.ask(
        "\n[bold]Reino de destino[/]",
        choices=[r.lower() for r in REALMS],
    ).title()

    if dest not in REALMS:
        console.print(f"[error]Reino desconocido: {dest}[/]")
        return

    if dest == source:
        console.print("[warning]El reino de origen y destino son el mismo.[/]")
        return

    dest_path = YGGDRASIL_ROOT / dest

    # Confirm
    console.print()
    console.print(
        Panel(
            f"[bold]Migrar[/] [realm]{project.name}[/]\n"
            f"  [dim]de[/] [warning]{source}[/]\n"
            f"  [dim]a[/]  [success]{dest}[/]",
            title="Confirmar migracion",
            border_style="gold1",
        )
    )

    if not Confirm.ask("[bold]\u00bfProceder con la migracion?[/]"):
        console.print("[warning]Migracion cancelada.[/]")
        return

    # Execute migration
    try:
        new_location = dest_path / project.name
        if new_location.exists():
            console.print(f"[error]Ya existe un proyecto llamado '{project.name}' en {dest}.[/]")
            return

        shutil.move(str(project), str(new_location))
        console.print("\n[bold success]\u2713 Migracion completada:[/]")
        console.print(
            f"  [realm]{project.name}[/] movido de "
            f"[{REALM_COLORS.get(source, 'white')}]{source}[/] "
            f"a [{REALM_COLORS.get(dest, 'white')}]{dest}[/]"
        )
    except Exception as e:
        console.print(f"[bold error]\u2717 Error durante migracion: {e}[/]")


# ── Main ────────────────────────────────────────────────────────
def main():
    print_banner()
    app()


if __name__ == "__main__":
    main()
