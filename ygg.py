#!/usr/bin/env python3
"""
BrierStudios Nordic - Yggdrasil CLI
The World Tree command-line interface
"""

import json
import logging
import os
import subprocess
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
from rich.tree import Tree


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

# ── Realms ────────────────────────────────────────────────────
REALMS = {
    "Asgard":       {"color": "#8b6cc7", "desc": "Core packages (lilith-*)", "icon": "◈"},
    "Vanaheim":     {"color": "#7eb8c4", "desc": "AI agents", "icon": "◈"},
    "Alfheim":      {"color": "#5b8a72", "desc": "UI projects", "icon": "◈"},
    "Svartalfheim": {"color": "#7eb8c4", "desc": "Documentation", "icon": "◈"},
    "Muspelheim":   {"color": "#c94f4f", "desc": "Dev / WIP / Fire", "icon": "◈"},
    "Niflheim":     {"color": "#8b6cc7", "desc": "Assets / Frost", "icon": "◈"},
    "Helheim":      {"color": "#3d4162", "desc": "Archive / Dead", "icon": "◈"},
    "Jotunheim":    {"color": "#c9a55a", "desc": "Massive projects", "icon": "◈"},
    "Midgard":      {"color": "#c8d0e0", "desc": "Personal", "icon": "◈"},
}

# ── ASCII Art Banner ──────────────────────────────────────────
YGGDRASIL_BANNER = """[bold #7eb8c4]
          ╦ ╦ ╔═╗ ╔═╗ ╔╗╗ ╔═╗ ╦   ╔═╗
          ╚╦╝ ║╣  ║ ╦ ║║║ ║╣  ║   ╚═╗
           ╩  ╚═╝ ╚═╝ ╝╚╝ ╚═╝ ╩═╝ ╚═╝[/bold #7eb8c4]
[dim #3d4162]          ───────────────────────────────[/dim #3d4162]
[bold #c9a55a]          ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ[/bold #c9a55a]  [dim #3d4162]|[/dim #3d4162]  [#c8d0e0]Nine Realms[/#c8d0e0]"""

# ── Global State ──────────────────────────────────────────────
app = App(
    name="ygg",
    version="6.0.0",
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


def run_cmd(cmd, cwd=None):
    """Run shell command and return output"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or str(YGGDRASIL_ROOT), timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def get_dir_size(path):
    """Get directory size in human-readable format"""
    try:
        result = run_cmd(f"du -sh '{path}' 2>/dev/null | cut -f1")
        return result or "—"
    except Exception:
        return "—"


def count_files(path, pattern="*"):
    """Count files matching pattern in directory"""
    try:
        result = run_cmd(f"find '{path}' -name '{pattern}' -type f 2>/dev/null | wc -l")
        return int(result) if result else 0
    except Exception:
        return 0


def git_status(path):
    """Get git status of a directory"""
    if not (Path(path) / ".git").exists():
        return None
    branch = run_cmd("git branch --show-current", cwd=str(path))
    dirty = run_cmd("git status --porcelain 2>/dev/null | wc -l", cwd=str(path))
    last_commit = run_cmd("git log -1 --format='%cr' 2>/dev/null", cwd=str(path))
    return {"branch": branch, "dirty": int(dirty) if dirty else 0, "last_commit": last_commit}


# ── Core Commands ─────────────────────────────────────────────
@app.command
def status():
    """Show Yggdrasil status — all realms, projects, and health"""
    print_banner()
    console.print("  [bold #c9a55a]Nine Realms[/bold #c9a55a]")
    console.print()

    table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35", padding=(0, 1))
    table.add_column("Realm", style="bold", min_width=14)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Projects", style="#c8d0e0", min_width=20)
    table.add_column("Size", style="#7eb8c4", justify="right", width=8)
    table.add_column("Git", style="#8b6cc7", min_width=15)

    for realm, info in REALMS.items():
        realm_dir = YGGDRASIL_ROOT / realm
        exists = realm_dir.exists()

        if exists:
            # Count projects (subdirs with files)
            projects = []
            for d in sorted(realm_dir.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    file_count = count_files(d)
                    if file_count > 0:
                        projects.append(f"{d.name} ({file_count})")

            size = get_dir_size(realm_dir)
            g = git_status(realm_dir)
            git_info = ""
            if g:
                dirty_mark = f" [+{g['dirty']}]" if g["dirty"] > 0 else ""
                git_info = f"[dim]{g['branch']}[/dim]{dirty_mark}"

            status_icon = "[bold #5b8a72]✓[/bold #5b8a72]"
            proj_str = ", ".join(projects[:3])
            if len(projects) > 3:
                proj_str += f" +{len(projects)-3}"

            table.add_row(
                f"[{info['color']}]{realm}[/{info['color']}]",
                status_icon,
                proj_str or "[dim]empty[/dim]",
                size,
                git_info,
            )
        else:
            table.add_row(
                f"[{info['color']}]{realm}[/{info['color']}]",
                "[bold #c94f4f]✗[/bold #c94f4f]",
                "[dim]not found[/dim]",
                "—",
                "—",
            )

    console.print(table)
    console.print()

    # Summary
    total_files = count_files(YGGDRASIL_ROOT, "*.py")
    total_size = get_dir_size(YGGDRASIL_ROOT)
    console.print(f"  [#7eb8c4]Python files:[/#7eb8c4] {total_files}  [dim #3d4162]|[/dim #3d4162]  [#7eb8c4]Total size:[/#7eb8c4] {total_size}")
    console.print()


@app.command
def realms():
    """List all realms with descriptions"""
    print_banner()
    console.print("  [bold #c9a55a]The Nine Realms of Yggdrasil[/bold #c9a55a]")
    console.print()

    for realm, info in REALMS.items():
        realm_dir = YGGDRASIL_ROOT / realm
        exists = realm_dir.exists()
        icon = f"[bold {info['color']}]{info['icon']}[/bold {info['color']}]" if exists else "[dim]○[/dim]"
        status = "[#5b8a72]✓[/#5b8a72]" if exists else "[#c94f4f]✗[/#c94f4f]"
        console.print(f"  {icon} [{info['color']}]{realm:14s}[/{info['color']}] {status}  [dim #3d4162]{info['desc']}[/dim #3d4162]")

    console.print()


@app.command
def realm(name: str):
    """Show details of a specific realm

    Args:
        name: Realm name (e.g. Asgard, Muspelheim)
    """
    if name not in REALMS:
        console.print(f"  [#c94f4f]Unknown realm: {name}[/#c94f4f]")
        console.print(f"  [dim]Available: {', '.join(REALMS.keys())}[/dim]")
        return

    info = REALMS[name]
    realm_dir = YGGDRASIL_ROOT / name

    print_banner()
    console.print(f"  [bold {info['color']}]{info['icon']} {name}[/bold {info['color']}]  [dim #3d4162]— {info['desc']}[/dim #3d4162]")
    console.print()

    if not realm_dir.exists():
        console.print(f"  [#c94f4f]Realm directory not found: {realm_dir}[/#c94f4f]")
        return

    # Git info
    g = git_status(realm_dir)
    if g:
        console.print(f"  [#7eb8c4]Git:[/#7eb8c4] {g['branch']}  [dim]|[/dim]  Last commit: {g['last_commit']}")
        if g["dirty"] > 0:
            console.print(f"  [#c9a55a]Uncommitted changes: {g['dirty']}[/#c9a55a]")
        console.print()

    # Projects table
    table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
    table.add_column("Project", style="bold", min_width=25)
    table.add_column("Files", justify="right", width=6)
    table.add_column("Size", justify="right", width=8)
    table.add_column("Modified", style="#7eb8c4", width=16)
    table.add_column("Description", style="#c8d0e0")

    for d in sorted(realm_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            fc = count_files(d)
            size = get_dir_size(d)
            mtime = datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

            # Try to read README for description
            readme = d / "README.md"
            desc = ""
            if readme.exists():
                try:
                    first_lines = readme.read_text()[:200].split("\n")
                    for line in first_lines:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("```"):
                            desc = line[:60]
                            break
                except Exception:
                    pass

            table.add_row(f"  {d.name}", str(fc), size, mtime, desc)
        elif d.is_file() and d.suffix in (".py", ".md", ".toml", ".json"):
            size = f"{d.stat().st_size:,}"
            mtime = datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(f"  [dim]{d.name}[/dim]", "1", size, mtime, "")

    console.print(table)
    console.print()


@app.command
def project(name: str):
    """Show detailed info about a project across all realms

    Args:
        name: Project name to search for
    """
    print_banner()
    console.print(f"  [#7eb8c4]Searching for:[/#7eb8c4] [bold #c8d0e0]{name}[/bold #c8d0e0]")
    console.print()

    found = False
    for realm_name in REALMS:
        realm_dir = YGGDRASIL_ROOT / realm_name
        if not realm_dir.exists():
            continue

        for d in realm_dir.iterdir():
            if d.is_dir() and name.lower() in d.name.lower():
                found = True
                info = REALMS[realm_name]
                console.print(f"  [bold {info['color']}]{realm_name}[/bold {info['color']}] / [bold #c8d0e0]{d.name}[/bold #c8d0e0]")
                console.print(f"  [#7eb8c4]Path:[/#7eb8c4] {d}")
                console.print(f"  [#7eb8c4]Size:[/#7eb8c4] {get_dir_size(d)}")
                console.print(f"  [#7eb8c4]Files:[/#7eb8c4] {count_files(d)}")

                g = git_status(d)
                if g:
                    console.print(f"  [#7eb8c4]Git:[/#7eb8c4] {g['branch']} ({g['last_commit']})")

                # Show README if exists
                readme = d / "README.md"
                if readme.exists():
                    console.print()
                    console.print(f"  [bold #c9a55a]README:[/bold #c9a55a]")
                    lines = readme.read_text()[:500].split("\n")
                    for line in lines[:15]:
                        console.print(f"    {line}")
                    if len(lines) > 15:
                        console.print("    [dim]...[/dim]")

                # Show key files
                console.print()
                console.print(f"  [bold #c9a55a]Key files:[/bold #c9a55a]")
                for f in sorted(d.rglob("*")):
                    if f.is_file() and f.suffix in (".py", ".toml", ".json", ".md") and ".venv" not in str(f) and ".git" not in str(f):
                        rel = f.relative_to(d)
                        console.print(f"    [#7eb8c4]{rel}[/#7eb8c4]  ({f.stat().st_size:,} bytes)")
                console.print()

    if not found:
        console.print(f"  [#c94f4f]No project matching '{name}' found across all realms[/#c94f4f]")


@app.command
def dataset():
    """Show dataset status for Horror GameMaster"""
    print_banner()

    base = YGGDRASIL_ROOT / "Muspelheim" / "Horror-GameMaster" / "data"
    if not base.exists():
        console.print("  [#c94f4f]Horror GameMaster data not found[/#c94f4f]")
        return

    console.print("  [bold #c94f4f]Horror GameMaster Dataset[/bold #c94f4f]")
    console.print()

    # Count entries in each file
    table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
    table.add_column("File", style="bold", min_width=30)
    table.add_column("Entries", justify="right", width=8)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Modified", style="#7eb8c4", width=16)

    total_entries = 0
    for f in sorted(base.glob("*.jsonl")):
        lines = sum(1 for _ in open(f))
        total_entries += lines
        size = f"{f.stat().st_size:,}"
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(f"  {f.name}", str(lines), size, mtime)

    console.print(table)
    console.print()

    # Count unique entries
    seen = set()
    unified = base / "dataset_unified.jsonl"
    if unified.exists():
        import json
        with open(unified) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    seen.add(obj.get("output", "")[:100])
                except Exception:
                    pass

    console.print(f"  [#7eb8c4]Total lines:[/#7eb8c4] {total_entries}")
    console.print(f"  [#7eb8c4]Unique entries:[/#7eb8c4] {len(seen)}")
    console.print(f"  [#7eb8c4]Target:[/#7eb8c4] 5,000")
    progress = len(seen) / 5000 * 100
    bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
    console.print(f"  [#7eb8c4]Progress:[/#7eb8c4] [{bar}] {progress:.0f}%")
    console.print()


@app.command
def search(query: str):
    """Search across all Yggdrasil files

    Args:
        query: Search term
    """
    print_banner()
    console.print(f"  [#7eb8c4]Searching:[/#7eb8c4] [bold #c8d0e0]{query}[/bold #c8d0e0]")
    console.print()

    result = run_cmd(f"grep -rli '{query}' --include='*.py' --include='*.md' --include='*.json' --include='*.toml' --include='*.yaml' --include='*.conf' . 2>/dev/null | grep -v '.venv' | grep -v '.git' | grep -v node_modules | head -20")

    if result:
        for line in result.split("\n"):
            if line.strip():
                console.print(f"  [#7eb8c4]{line.strip()}[/#7eb8c4]")
    else:
        console.print("  [dim]No results found[/dim]")
    console.print()


@app.command
def git():
    """Show git status across all realms"""
    print_banner()
    console.print("  [bold #c9a55a]Git Status — All Realms[/bold #c9a55a]")
    console.print()

    table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
    table.add_column("Realm", style="bold", min_width=14)
    table.add_column("Branch", style="#8b6cc7", min_width=12)
    table.add_column("Dirty", justify="right", width=6)
    table.add_column("Last Commit", style="#7eb8c4", min_width=20)

    for realm_name in REALMS:
        realm_dir = YGGDRASIL_ROOT / realm_name
        if not realm_dir.exists():
            continue

        g = git_status(realm_dir)
        if g:
            info = REALMS[realm_name]
            dirty = f"[#c9a55a]{g['dirty']}[/#c9a55a]" if g["dirty"] > 0 else "[#5b8a72]0[/#5b8a72]"
            table.add_row(
                f"[{info['color']}]{realm_name}[/{info['color']}]",
                g["branch"] or "[dim]—[/dim]",
                dirty,
                g["last_commit"] or "[dim]—[/dim]",
            )

    console.print(table)
    console.print()


@app.command
def info():
    """Show system info and Yggdrasil environment"""
    print_banner()

    console.print("  [bold #c9a55a]System[/bold #c9a55a]")
    console.print(f"  [#7eb8c4]Root:[/#7eb8c4] {YGGDRASIL_ROOT}")
    console.print(f"  [#7eb8c4]Python:[/#7eb8c4] {run_cmd('python3 --version')}")
    console.print(f"  [#7eb8c4]OS:[/#7eb8c4] {run_cmd('uname -sr')}")
    console.print(f"  [#7eb8c4]Shell:[/#7eb8c4] {os.environ.get('SHELL', '?')}")
    console.print(f"  [#7eb8c4]GPU:[/#7eb8c4] {run_cmd('nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null') or 'N/A'}")
    console.print()

    console.print("  [bold #c9a55a]Venv[/bold #c9a55a]")
    venv = YGGDRASIL_ROOT / ".venv"
    if venv.exists():
        console.print(f"  [#7eb8c4]Path:[/#7eb8c4] {venv}")
        console.print(f"  [#7eb8c4]Python:[/#7eb8c4] {run_cmd(f'{venv}/bin/python3 --version')}")
        pkg_count = run_cmd(f"{venv}/bin/pip list 2>/dev/null | wc -l")
        console.print(f"  [#7eb8c4]Packages:[/#7eb8c4] {pkg_count}")
    else:
        console.print("  [dim]No .venv found[/dim]")
    console.print()

    console.print("  [bold #c9a55a]Git[/bold #c9a55a]")
    g = git_status(YGGDRASIL_ROOT)
    if g:
        console.print(f"  [#7eb8c4]Branch:[/#7eb8c4] {g['branch']}")
        console.print(f"  [#7eb8c4]Dirty:[/#7eb8c4] {g['dirty']} files")
        console.print(f"  [#7eb8c4]Last commit:[/#7eb8c4] {g['last_commit']}")
    console.print()


@app.command
def tree():
    """Show project tree"""
    print_banner()
    console.print("  [bold #c9a55a]Yggdrasil Tree[/bold #c9a55a]")
    console.print()

    t = Tree("[bold #7eb8c4]Yggdrasil[/bold #7eb8c4]")

    for realm_name, info in REALMS.items():
        realm_dir = YGGDRASIL_ROOT / realm_name
        if not realm_dir.exists():
            continue

        realm_node = t.add(f"[{info['color']}]{info['icon']} {realm_name}[/{info['color']}]")

        for d in sorted(realm_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                fc = count_files(d)
                if fc > 0:
                    realm_node.add(f"[#c8d0e0]{d.name}[/#c8d0e0] [dim #3d4162]({fc} files)[/dim #3d4162]")

    console.print(t)
    console.print()


# ── Legacy Commands ───────────────────────────────────────────
@app.command
def chat(provider: str = "mimo"):
    """Start Lilith — interactive AI agent with tool use

    Args:
        provider: LLM provider (mimo, byteplus)
    """
    from lilith_agent import start_agent
    start_agent(provider)


@app.command
def run(command: str, description: str = None):
    """Run custom commands in Yggdrasil root"""
    if description:
        console.print(f"  [bold #c8d0e0]{description}[/bold #c8d0e0]")
    console.print(f"  [#7eb8c4]ᚨ {command}[/#7eb8c4]")

    result = run_cmd(command)
    if result:
        console.print(result)
    console.print()


@app.command
def ls(directory: str = "."):
    """List files in a directory"""
    p = YGGDRASIL_ROOT / directory
    if not p.exists():
        console.print(f"  [#c94f4f]Not found: {directory}[/#c94f4f]")
        return

    table = Table(show_header=True, header_style="bold #7eb8c4", border_style="#1a1d35")
    table.add_column("Name", style="bold", min_width=25)
    table.add_column("Type", width=6)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Modified", style="#7eb8c4", width=16)

    for item in sorted(p.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_file():
            size = f"{item.stat().st_size:,}"
            ftype = "[#7eb8c4]file[/#7eb8c4]"
        else:
            size = get_dir_size(item)
            ftype = "[#c9a55a]dir[/#c9a55a]"
        mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(f"  {item.name}", ftype, size, mtime)

    console.print(table)


@app.command
def cat(file: str):
    """Show file contents"""
    p = YGGDRASIL_ROOT / file
    if not p.exists():
        console.print(f"  [#c94f4f]Not found: {file}[/#c94f4f]")
        return

    console.print(f"  [bold #c8d0e0]{p.name}:[/bold #c8d0e0]")
    console.print(Rule(style="#1a1d35"))
    console.print(p.read_text()[:10000])


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
