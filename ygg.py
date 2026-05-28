#!/usr/bin/env python3
"""
BrierStudios Nordic - Yggdrasil CLI
The World Tree command-line interface
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import cyclopts
from cyclopts import App
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# ── Configuration ──────────────────────────────────────────────
logger = logging.getLogger(__name__)
YGGDRASIL_ROOT = Path(__file__).parent.resolve()

# ── Nordic Frost Theme ────────────────────────────────────────
nordic_theme = Theme(
    {
        "realm": "bold #c9a55a",
        "frost": "#7eb8c4",
        "amethyst": "#8b6cc7",
        "snow": "#c8d0e0",
        "ember": "#c94f4f",
        "pine": "#5b8a72",
        "gold": "#c9a55a",
        "steel": "#3d4162",
        "error": "bold #c94f4f",
        "success": "bold #5b8a72",
        "warning": "bold #c9a55a",
        "info": "#7eb8c4",
        "primary": "#7eb8c4",
        "secondary": "#8b6cc7",
        "muted": "#3d4162",
    }
)
console = Console(theme=nordic_theme)

# ── ASCII Art Banner ──────────────────────────────────────────
YGGDRASIL_BANNER = """[bold #7eb8c4]
          ╦ ╦ ╔═╗ ╔═╗ ╔╗╗ ╔═╗ ╦   ╔═╗
          ╚╦╝ ║╣  ║ ╦ ║║║ ║╣  ║   ╚═╗
           ╩  ╚═╝ ╚═╝ ╝╚╝ ╚═╝ ╩═╝ ╚═╝[/bold #7eb8c4]
[dim #3d4162]          ───────────────────────────────[/dim #3d4162]
[bold #c9a55a]          ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ[/bold #c9a55a]  [dim #3d4162]|[/dim #3d4162]  [#c8d0e0]Nine Realms[/#c8d0e0]

[bold #c9a55a]◈[/bold #c9a55a] [#8b6cc7]Asgard[/#8b6cc7]    [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#7eb8c4]Vanaheim[/#7eb8c4]  [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#5b8a72]Alfheim[/#5b8a72]   [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#c94f4f]Muspelheim[/#c94f4f]
[bold #c9a55a]◈[/bold #c9a55a] [#7eb8c4]Svartalf[/#7eb8c4]  [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#c9a55a]Jotunheim[/#c9a55a] [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#8b6cc7]Niflheim[/#8b6cc7]  [dim]──[/dim]  [bold #c9a55a]◈[/bold #c9a55a] [#c8d0e0]Midgard[/#c8d0e0]

[dim #3d4162]  ᚨ[/dim #3d4162] [#5b8a72]Systems Active[/#5b8a72]  [dim #3d4162]ᚦ[/dim #3d4162] [#7eb8c4]Agents Ready[/#7eb8c4]  [dim #3d4162]ᚱ[/dim #3d4162] [#c9a55a]Tree Healthy[/#c9a55a]"""

# ── Global State ──────────────────────────────────────────────
app = App(
    name="ygg",
    version="5.1.0",
    help="BrierStudios Nordic - Yggdrasil CLI",
)

# ── Helper Functions ──────────────────────────────────────────
def print_banner():
    """Print Nordic banner"""
    console.print()
    console.print(Panel.fit(
        YGGDRASIL_BANNER,
        border_style="#1a1d35",
        title="[bold #7eb8c4]ᛒ[/bold #7eb8c4] YGGDRASIL",
        title_align="left",
        subtitle=f"[dim #3d4162]v{app.version}[/dim #3d4162]",
    ))
    console.print(Rule(style="#1a1d35"))
    now = datetime.now()
    console.print(f"  [#7eb8c4]{now.strftime('%H:%M')}[/#7eb8c4]  [dim #3d4162]{now.strftime('%A, %d %B %Y')}[/dim #3d4162]")
    console.print()

def validate_path(path: str):
    """Validate path exists"""
    p = Path(path)
    if not p.exists():
        raise cyclopts.ValidationError(f"Path '{path}' does not exist")
    return p

# ── Core Commands ─────────────────────────────────────────────
@app.command
def help():
    """Show help information"""
    print_banner()
    console.print("  [bold #c9a55a]Commands:[/bold #c9a55a]")
    console.print()
    console.print(app.help())

@app.command
def status():
    """Show Yggdrasil status and health"""
    print_banner()
    console.print("  [#7eb8c4]Scanning the Nine Realms...[/#7eb8c4]")

    try:
        from yggdrasil_cli import health_check
        health_check()
    except ImportError:
        console.print("  [warning]Basic scan...[/warning]")
        console.print()

        root_dir = Path.cwd()
        config_file = root_dir / ".env"

        table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
        table.add_column("  Realm", style="bold")
        table.add_column("  Status", style="bold")
        table.add_column("  Path")

        realms = {
            "Asgard": "#8b6cc7", "Vanaheim": "#7eb8c4", "Alfheim": "#5b8a72",
            "Muspelheim": "#c94f4f", "Niflheim": "#8b6cc7", "Svartalfheim": "#7eb8c4",
            "Midgard": "#c8d0e0", "Helheim": "#3d4162", "Jotunheim": "#c9a55a",
        }

        for realm, color in realms.items():
            realm_dir = root_dir / realm
            exists = realm_dir.exists()
            status_icon = "[bold #5b8a72]✓[/bold #5b8a72]" if exists else "[bold #c94f4f]✗[/bold #c94f4f]"
            details = str(realm_dir) if exists else "[dim]Not found[/dim]"
            table.add_row(f"[{color}]{realm}[/{color}]", status_icon, details)

        table.add_row(
            "  Config",
            "[bold #5b8a72]✓[/bold #5b8a72]" if config_file.exists() else "[bold #c94f4f]✗[/bold #c94f4f]",
            str(config_file) if config_file.exists() else "[dim]Not found[/dim]"
        )

        console.print(table)
        console.print()

@app.command
def chat():
    """Start interactive chat with Yggdrasil"""
    print_banner()
    console.print("  [#7eb8c4]Initializing Yggdrasil connection...[/#7eb8c4]")
    try:
        from yggdrasil_cli import chat as start_chat
        start_chat()
    except ImportError:
        console.print("  [warning]Chat module not available[/warning]")

@app.command
def run(command: str, description: str = None):
    """
    Run custom commands

    Args:
        command: Command to execute
        description: Description of what the command does
    """
    print_banner()
    if description:
        console.print(f"  [bold #c8d0e0]{description}[/bold #c8d0e0]")
    console.print(f"  [#7eb8c4]ᚨ {command}[/#7eb8c4]")

    try:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=str(YGGDRASIL_ROOT))

        if result.stdout:
            console.print("  [bold #c8d0e0]Output:[/bold #c8d0e0]")
            console.print(result.stdout)
        if result.stderr:
            console.print("  [bold #c94f4f]Error:[/bold #c94f4f]")
            console.print(result.stderr)

        code_color = "#5b8a72" if result.returncode == 0 else "#c94f4f"
        console.print(f"  [bold {code_color}]Exit: {result.returncode}[/bold {code_color}]")
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

# ── File System Commands ──────────────────────────────────────
@app.command
def ls(directory: str = "."):
    """List files in a directory"""
    print_banner()
    try:
        p = validate_path(directory)
        if not p.is_dir():
            raise cyclopts.ValidationError(f"'{directory}' is not a directory")

        console.print(f"  [bold #c8d0e0]{p}:[/bold #c8d0e0]")
        console.print()

        table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
        table.add_column("  Name", style="bold")
        table.add_column("  Type")
        table.add_column("  Size")
        table.add_column("  Modified")

        for item in sorted(p.iterdir()):
            if item.is_file():
                item_type = "[#7eb8c4]file[/#7eb8c4]"
                size = f"{item.stat().st_size:,}"
            else:
                item_type = "[#c9a55a]dir[/#c9a55a]"
                size = "—"
            mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(f"  {item.name}", item_type, size, mtime)

        console.print(table)
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

@app.command
def cd(directory: str):
    """Change working directory"""
    print_banner()
    try:
        p = validate_path(directory)
        if not p.is_dir():
            raise cyclopts.ValidationError(f"'{directory}' is not a directory")
        os.chdir(str(p))
        console.print(f"  [#5b8a72]→ {p}[/#5b8a72]")
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

@app.command
def cat(file: str):
    """Show file contents"""
    print_banner()
    try:
        p = validate_path(file)
        if not p.is_file():
            raise cyclopts.ValidationError(f"'{file}' is not a file")
        console.print(f"  [bold #c8d0e0]{p.name}:[/bold #c8d0e0]")
        console.print(Rule(style="#1a1d35"))
        console.print(p.read_text())
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

# ── Service Management ────────────────────────────────────────
@app.command
def start(service: str = "all"):
    """Start Yggdrasil services"""
    print_banner()
    console.print(f"  [#7eb8c4]Starting: {service}[/#7eb8c4]")
    try:
        import subprocess
        if service == "all":
            for cmd in ["uv run poe dashboard", "uv run poe api", "uv run poe agent"]:
                subprocess.run(cmd, shell=True, cwd=str(YGGDRASIL_ROOT))
            console.print("  [#5b8a72]All services started[/#5b8a72]")
        else:
            subprocess.run(f"uv run poe {service}", shell=True, cwd=str(YGGDRASIL_ROOT))
            console.print(f"  [#5b8a72]{service} started[/#5b8a72]")
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

@app.command
def stop(service: str = "all"):
    """Stop Yggdrasil services"""
    print_banner()
    console.print(f"  [#c9a55a]Stopping: {service}[/#c9a55a]")
    try:
        import subprocess
        if service == "all":
            for proc in ["uvicorn", "python -m uvicorn", "poe", "dashboard"]:
                subprocess.run(f"pkill -f '{proc}'", shell=True)
            console.print("  [#5b8a72]All services stopped[/#5b8a72]")
        else:
            subprocess.run(f"pkill -f '{service}'", shell=True)
            console.print(f"  [#5b8a72]{service} stopped[/#5b8a72]")
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")

# ── Log Management ────────────────────────────────────────────
@app.command
def logs(service: str = "all", lines: int = 50):
    """Show log files"""
    print_banner()
    log_dir = YGGDRASIL_ROOT / "logs"
    if not log_dir.exists():
        console.print("  [warning]No logs directory[/warning]")
        return

    services = {"api": "api.log", "dashboard": "dashboard.log", "agent": "agent.log"}
    if service == "all":
        for name, filename in services.items():
            log_file = log_dir / filename
            if log_file.exists():
                console.print()
                console.print(f"  [bold #7eb8c4]── {name} ──[/bold #7eb8c4]")
                with open(log_file) as f:
                    console.print("".join(f.readlines()[-lines:]))
    else:
        if service not in services:
            console.print(f"  [#c94f4f]Unknown: {service}[/#c94f4f]")
            return
        log_file = log_dir / services[service]
        if log_file.exists():
            console.print(f"  [bold #7eb8c4]── {service} ({lines} lines) ──[/bold #7eb8c4]")
            with open(log_file) as f:
                console.print("".join(f.readlines()[-lines:]))

# ── Main Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print()
        console.print("  [#c9a55a]ᛟ Interrupted[/#c9a55a]")
    except Exception as e:
        console.print(f"  [#c94f4f]Error: {e}[/#c94f4f]")
        if os.getenv("DEBUG"):
            import traceback
            console.print(traceback.format_exc())
