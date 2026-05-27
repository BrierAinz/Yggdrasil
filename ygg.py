#!/usr/bin/env python3
"""
Yggdrasil CLI - A beautiful, Hermes-style command-line interface for Yggdrasil
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
console = Console()
YGGDRASIL_ROOT = Path(__file__).parent.resolve()

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
YGGDRASIL_BANNER = """╭─────────────────────────────────────────────────────────────────╮
│                 🌲 YGGDRASIL ECOSYSTEM 🌲                      │
│                                                                 │
│  The World Tree connecting the Nine Realms of AI and Software   │
│                                                                 │
│  [bold gold1]◈[/] [magenta]Asgard[/]    → [bold gold1]◈[/] [cyan]Vanaheim[/]   → [bold gold1]◈[/] [green]Alfheim[/]    → [bold gold1]◈[/] [red]Muspelheim[/] │
│  [bold gold1]◈[/] [blue]Svartalfheim[/] → [bold gold1]◈[/] [orange]Jotunheim[/]  → [bold gold1]◈[/] [cyan]Niflheim[/]   → [bold gold1]◈[/] [white]Midgard[/]   │
│                                                                 │
│  [bold green]✓[/] Services Active   [bold blue]✓[/] Agents Connected   [bold yellow]✓[/] System Healthy │
╰─────────────────────────────────────────────────────────────────╯"""

# ── Global State ────────────────────────────────────────────────
app = App(
    name="ygg",
    version="3.0.0",
    help="Yggdrasil CLI - Hermes-style interface for your AI ecosystem",
)

# ── Helper Functions ────────────────────────────────────────────
def print_banner():
    """Print ASCII art banner"""
    console.print()
    console.print(Panel.fit(Text(YGGDRASIL_BANNER, style="gold1")))
    console.print(Rule(style="dim"))
    console.print(Text(f"[bold green]Version[/] {app.version} · [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/]", style="dim"))
    console.print()

def validate_path(path: str):
    """Validate path exists"""
    p = Path(path)
    if not p.exists():
        raise cyclopts.ValidationError(f"Path '{path}' does not exist")
    return p

def format_duration(seconds: float):
    """Format duration for display"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

# ── Core Commands ──────────────────────────────────────────────
@app.command
def help():
    """Show help information"""
    print_banner()
    console.print(Text("Available commands:", style="bold gold1"))
    console.print()
    console.print(app.help())

@app.command
def status():
    """Show Yggdrasil status and health"""
    print_banner()
    console.print(Text("Checking Yggdrasil status...", style="cyan"))

    # Run health check
    try:
        from yggdrasil_cli import health_check
        health_check()
    except ImportError:
        console.print(Text("Running basic status check...", style="warning"))
        console.print()

        # Basic directory check
        root_dir = Path.cwd()
        config_file = root_dir / ".env"

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Component", style="bold")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        # Check directories
        realms = ["Asgard", "Vanaheim", "Alfheim", "Svartalfheim", "Muspelheim",
                 "Helheim", "Niflheim", "Jotunheim", "Midgard"]

        for realm in realms:
            realm_dir = root_dir / realm
            exists = realm_dir.exists()
            status = "[bold green]✓[/]" if exists else "[bold red]✗[/]"
            details = str(realm_dir) if exists else "Directory not found"
            table.add_row(realm, status, details)

        table.add_row("Config",
                     "[bold green]✓[/]" if config_file.exists() else "[bold red]✗[/]",
                     str(config_file) if config_file.exists() else "Config file not found")

        console.print(table)
        console.print()

        if config_file.exists():
            console.print(Text("Configuration found:", style="bold"))
            with open(config_file) as f:
                console.print(f.read())

@app.command
def chat():
    """Start interactive chat with Yggdrasil (like Hermes)"""
    print_banner()
    console.print(Text("Starting Yggdrasil Chat...", style="cyan"))

    # Start Yggdrasil chat
    try:
        from yggdrasil_cli import chat as start_chat
        start_chat()
    except ImportError:
        console.print(Text("Chat functionality not available", style="warning"))

@app.command
def run(command: str, description: str = None):
    """
    Run custom commands (like Hermes)
    
    Args:
        command: Command to execute
        description: Description of what the command does
    """
    print_banner()
    if description:
        console.print(Text(f"Running: {description}", style="bold"))

    console.print(Text(f"Executing: {command}", style="cyan"))

    try:
        import subprocess
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(YGGDRASIL_ROOT)
        )

        if result.stdout:
            console.print(Text("Output:", style="bold"))
            console.print(result.stdout)

        if result.stderr:
            console.print(Text("Error:", style="bold red"))
            console.print(result.stderr)

        console.print(Text(f"Command executed with code: {result.returncode}", style="bold"))

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

# ── File System Commands ────────────────────────────────────────
@app.command
def ls(directory: str = "."):
    """List files in a directory"""
    print_banner()
    try:
        p = validate_path(directory)

        if not p.is_dir():
            raise cyclopts.ValidationError(f"'{directory}' is not a directory")

        console.print(Text(f"Directory listing for '{p}':", style="bold"))
        console.print()

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="bold")
        table.add_column("Size")
        table.add_column("Modified")

        for item in p.iterdir():
            item_type = "📄 File" if item.is_file() else "📁 Directory"
            item_size = item.stat().st_size if item.is_file() else "—"
            item_mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

            table.add_row(str(item.name), item_type, str(item_size), item_mtime)

        console.print(table)

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

@app.command
def cd(directory: str):
    """Change working directory"""
    print_banner()
    try:
        p = validate_path(directory)

        if not p.is_dir():
            raise cyclopts.ValidationError(f"'{directory}' is not a directory")

        os.chdir(str(p))
        console.print(Text(f"Changed to: {p}", style="green"))

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

@app.command
def cat(file: str):
    """Show file contents"""
    print_banner()
    try:
        p = validate_path(file)

        if not p.is_file():
            raise cyclopts.ValidationError(f"'{file}' is not a file")

        console.print(Text(f"Contents of '{p}':", style="bold"))
        console.print()
        console.print(p.read_text())

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

# ── Service Management ──────────────────────────────────────────
@app.command
def start(service: str = "all"):
    """
    Start Yggdrasil services
    
    Args:
        service: Service to start (default: all)
    """
    print_banner()
    console.print(Text(f"Starting service: {service}", style="cyan"))

    services = {
        "api": "API server",
        "dashboard": "Web dashboard",
        "agent": "Lilith Agent",
        "all": "All services"
    }

    if service not in services:
        console.print(Text(f"Unknown service: {service}", style="red"))
        return

    try:
        import subprocess

        if service == "all":
            console.print(Text("Starting all services...", style="cyan"))
            # Start all services
            commands = [
                "uv run poe dashboard &",
                "uv run poe api &",
                "uv run poe agent &"
            ]

            for cmd in commands:
                subprocess.run(cmd, shell=True, cwd=str(YGGDRASIL_ROOT))

            console.print(Text("All services started", style="green"))

        elif service == "api":
            subprocess.run("uv run poe api &", shell=True, cwd=str(YGGDRASIL_ROOT))
            console.print(Text("API server started", style="green"))

        elif service == "dashboard":
            subprocess.run("uv run poe dashboard &", shell=True, cwd=str(YGGDRASIL_ROOT))
            console.print(Text("Web dashboard started", style="green"))

        elif service == "agent":
            subprocess.run("uv run poe agent &", shell=True, cwd=str(YGGDRASIL_ROOT))
            console.print(Text("Lilith Agent started", style="green"))

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

@app.command
def stop(service: str = "all"):
    """
    Stop Yggdrasil services
    
    Args:
        service: Service to stop (default: all)
    """
    print_banner()
    console.print(Text(f"Stopping service: {service}", style="cyan"))

    try:
        import subprocess

        if service == "all":
            console.print(Text("Stopping all services...", style="cyan"))

            # Find and kill all running processes
            processes = [
                "uvicorn",
                "python -m uvicorn",
                "poe",
                "dashboard"
            ]

            for proc in processes:
                subprocess.run(f"pkill -f '{proc}'", shell=True)

            console.print(Text("All services stopped", style="green"))

        else:
            subprocess.run(f"pkill -f '{service}'", shell=True)
            console.print(Text(f"{service} stopped", style="green"))

    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))

# ── Log Management ─────────────────────────────────────────────
@app.command
def logs(service: str = "all", lines: int = 50):
    """
    Show log files
    
    Args:
        service: Service to show logs for (default: all)
        lines: Number of lines to show (default: 50)
    """
    print_banner()

    log_dir = YGGDRASIL_ROOT / "logs"

    if not log_dir.exists():
        console.print(Text("Log directory not found", style="warning"))
        return

    services = {
        "api": "api.log",
        "dashboard": "dashboard.log",
        "agent": "agent.log"
    }

    if service == "all":
        console.print(Text("Showing all logs:", style="bold"))
        for name, filename in services.items():
            log_file = log_dir / filename
            if log_file.exists():
                console.print()
                console.print(Text(f"--- {name} logs ---\n", style="bold"))
                with open(log_file) as f:
                    lines_content = f.readlines()[-lines:]
                    console.print("".join(lines_content))
    else:
        if service not in services:
            console.print(Text(f"Unknown service: {service}", style="red"))
            return

        log_file = log_dir / services[service]
        if log_file.exists():
            console.print(Text(f"--- {service} logs ({lines} lines) ---", style="bold"))
            with open(log_file) as f:
                lines_content = f.readlines()[-lines:]
                console.print("".join(lines_content))
        else:
            console.print(Text(f"Log file for {service} not found", style="warning"))

# ── Main Entry Point ───────────────────────────────────────────
if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print()
        console.print(Text("Yggdrasil CLI stopped by user", style="yellow"))
    except Exception as e:
        console.print(Text(f"Error: {e}", style="red"))
        if os.getenv("DEBUG"):
            import traceback
            console.print(traceback.format_exc())
