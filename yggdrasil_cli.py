#!/usr/bin/env python3
"""
Yggdrasil CLI - Comando central del ecosistema
Uso: python yggdrasil_cli.py [comando]

Comandos:
  status      - Estado de salud de todos los reinos
  clean       - Limpiar basura regenerable (pycache, node_modules, etc.)
  backup      - Crear backup de Svartalfheim + configs
  purge       - Purgar cuarentena de Helheim
  size        - Mostrar tamano por reino
  tree        - Arbol de proyectos
  test        - Ejecutar pytest
  sync        - Ejecutar sincronizacion
  api         - Levantar API de Lilith
  health      - Verificar README.md en cada reino
  migrate     - Migrar proyecto entre reinos (interactivo)
"""

import shutil
import subprocess
import sys
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

# ── Cyclopts App ────────────────────────────────────────────────
app = App(
    name="yggdrasil",
    help="Yggdrasil CLI - El Arbol Sagrado que conecta los nueve reinos",
)


# ── Banner ───────────────────────────────────────────────────────
def print_banner():
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

    console.print()
    console.print(
        Panel(
            tree_art,
            title="[bold red]⚔ Yggdrasil ⚔[/]",
            subtitle="[dim]v2.0 — The Sacred Tree[/]",
            border_style="gold1",
            expand=False,
        )
    )
    console.print()


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
        return len([l for l in out.splitlines() if l.strip()])
    except Exception:
        return 0


# ── Commands ────────────────────────────────────────────────────
@app.command
def status():
    """Estado de salud de todos los reinos."""
    console.print(Rule("[bold realm]⚔ Realm Status Report ⚔[/]", style="gold1"))

    table = Table(
        title="Nine Realms of Yggdrasil",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
        title_style="bold red",
    )
    table.add_column("Reino", style="realm", min_width=14)
    table.add_column("Estado", min_width=10)
    table.add_column("Tamaño", justify="right", min_width=10)
    table.add_column("Barra", min_width=22)
    table.add_column("Archivos", justify="right", min_width=8)
    table.add_column("py/js", justify="center", min_width=7)

    max_size = 0
    realm_data = []

    # First pass: compute data and find max size
    for realm in REALMS:
        rpath = YGGDRASIL_ROOT / realm
        if not rpath.exists():
            realm_data.append((realm, "NO EXISTE", 0, 0, 0, 0))
            continue

        size_bytes = _du_bytes(rpath)
        fcount = _count_files(rpath)
        py_count = _count_files(rpath, "*.py")
        js_count = _count_files(rpath, "*.js")

        max_size = max(max_size, size_bytes)

        if fcount > 2:
            status_str = "ACTIVO"
        elif realm in ("Jotunheim", "Midgard") and fcount <= 2:
            status_str = "RESERVADO"
        elif realm == "Helheim":
            status_str = "ARCHIVO"
        else:
            status_str = "VACIO"

        realm_data.append((realm, status_str, size_bytes, fcount, py_count, js_count))

    # Second pass: render
    total_size = 0
    total_files = 0

    for realm, status_str, size_bytes, fcount, py_count, js_count in realm_data:
        color = REALM_COLORS.get(realm, "white")

        if status_str == "ACTIVO":
            status_style = "success"
        elif status_str == "VACIO":
            status_style = "warning"
        elif status_str == "RESERVADO":
            status_style = "info"
        elif status_str == "ARCHIVO":
            status_style = "dim"
        elif status_str == "NO EXISTE":
            status_style = "error"
        else:
            status_style = "white"

        # Size progress bar
        if max_size > 0 and size_bytes > 0:
            ratio = size_bytes / max_size
            bar_len = int(ratio * 20)
            bar_str = "[gold1]█[/]" * bar_len + "[dim]░[/]" * (20 - bar_len)
        else:
            bar_str = "[dim]░[/]" * 20

        size_display = _human_size(size_bytes) if size_bytes else "—"
        fcount_display = f"{fcount:,}" if fcount else "—"
        pyjs_display = f"{py_count}/{js_count}" if fcount else "—"

        table.add_row(
            f"[{color}]{realm}[/]",
            f"[{status_style}]{status_str}[/]",
            size_display,
            bar_str,
            fcount_display,
            pyjs_display,
        )

        total_size += size_bytes
        total_files += fcount

    console.print(table)
    console.print(Rule(style="gold1"))

    # Total line
    console.print(
        f"  [bold realm]TOTAL[/]  │  "
        f"[bold]{_human_size(total_size)}[/]  │  "
        f"[bold]{total_files:,}[/] archivos"
    )
    console.print(Rule(style="gold1"))

    # Quarantine check
    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if q.exists():
        qs = _du_bytes(q)
        console.print()
        console.print(
            f"[bold error]⚠ CUARENTENA[/]: {_human_size(qs)} en Helheim/Quarantine_2026-04-29/"
        )
        console.print("  Ejecuta: [bold]yggdrasil purge[/] para eliminar")


@app.command
def size():
    """Mostrar tamano por reino en formato legible."""
    console.print(Rule("[bold realm]⚔ Realm Sizes ⚔[/]", style="gold1"))

    table = Table(
        title="Realm Disk Usage",
        show_header=True,
        header_style="bold gold1",
        border_style="gold1",
    )
    table.add_column("Reino", style="realm", min_width=14)
    table.add_column("Tamaño", justify="right", min_width=12)
    table.add_column("Tamaño Humano", justify="right", min_width=12)

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
    console.print(Rule("[bold realm]⚔ Realm Hierarchy ⚔[/]", style="gold1"))

    world_tree = Tree(
        "[bold gold1]🌍 Yggdrasil[/]",
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
                marker = "📜" if has_readme else "📁"
                label = f"[link={item}]{item.name}[/]" if has_readme else item.name
                realm_branch.add(f"{marker} {label}")

    console.print(world_tree)


@app.command
def clean():
    """Limpiar basura regenerable (pycache, node_modules, etc.)."""
    console.print(Rule("[bold realm]⚔ Cleansing the Realms ⚔[/]", style="gold1"))

    cleaned = 0
    removed_items = []

    with Progress(
        SpinnerColumn("🗡 "),
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
            console.print(f"  [error]✗[/] [dim]{item}[/]")
        if len(removed_items) > 20:
            console.print(f"  [dim]... and {len(removed_items) - 20} more[/]")

    console.print(f"\n[bold success]✓ {cleaned}[/] items purged from the nine realms")


@app.command
def purge():
    """Purgar la cuarentena de Helheim (eliminacion permanente)."""
    q = YGGDRASIL_ROOT / "Helheim" / "Quarantine_2026-04-29"
    if not q.exists():
        console.print("[info]No hay cuarentena para purgar.[/]")
        return

    qs = _du_bytes(q)
    console.print(f"[bold error]⚠ PURGE[/]: Cuarentena detectada en {_human_size(qs)}")
    console.print(f"  Ruta: [dim]{q}[/]")

    if Confirm.ask("[bold warning]¿Eliminar permanentemente la cuarentena?[/]"):
        try:
            shutil.rmtree(q)
            console.print("[bold success]✓ Cuarentena eliminada del inframundo[/]")
        except Exception as e:
            console.print(f"[bold error]✗ Error: {e}[/]")
    else:
        console.print("[warning]Purga cancelada.[/]")


@app.command
def backup():
    """Crear backup de Svartalfheim + configs."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = YGGDRASIL_ROOT / f"backup_{ts}"
    backup_dir.mkdir(exist_ok=True)

    console.print(Rule("[bold realm]⚔ Creating Realm Backup ⚔[/]", style="gold1"))
    console.print(f"[info]Destino:[/] [dim]{backup_dir}[/]")

    backed_up = []

    with Progress(
        SpinnerColumn("⛏ "),
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
        console.print(f"  [success]✓[/] [{kind}] {name}")

    console.print(f"\n[bold success]✓ Backup completo:[/] [dim]{backup_dir}[/]")


@app.command
def test():
    """Ejecutar pytest en la raiz de Yggdrasil."""
    console.print(Rule("[bold realm]⚔ Running Tests ⚔[/]", style="gold1"))
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(YGGDRASIL_ROOT),
    )
    if result.returncode == 0:
        console.print("[bold success]✓ Tests passed[/]")
    else:
        console.print("[bold error]✗ Tests failed[/]")


@app.command
def sync():
    """Ejecutar sincronizacion de Yggdrasil."""
    console.print(Rule("[bold realm]⚔ Syncing Realms ⚔[/]", style="gold1"))
    subprocess.run([sys.executable, str(YGGDRASIL_ROOT / "sync.py")])


@app.command
def api():
    """Levantar la API de Lilith con uvicorn."""
    console.print(Rule("[bold realm]⚔ Awakening the API ⚔[/]", style="gold1"))
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
    console.print(Rule("[bold realm]⚔ Realm Health Check ⚔[/]", style="gold1"))

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
                "[error]—[/]",
                "[error]NO EXISTE[/]",
            )
            continue

        readme = rpath / "README.md"
        if readme.exists():
            size = readme.stat().st_size
            table.add_row(
                f"[{color}]{realm}[/]",
                f"[success]✓ presente[/] ({size} B)",
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
def migrate():
    """Migrar un proyecto entre reinos (interactivo)."""
    console.print(Rule("[bold realm]⚔ Realm Migration Ritual ⚔[/]", style="gold1"))

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
        has_readme = "📜" if (p / "README.md").exists() else "📁"
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

    if not Confirm.ask("[bold]¿Proceder con la migracion?[/]"):
        console.print("[warning]Migracion cancelada.[/]")
        return

    # Execute migration
    try:
        new_location = dest_path / project.name
        if new_location.exists():
            console.print(f"[error]Ya existe un proyecto llamado '{project.name}' en {dest}.[/]")
            return

        shutil.move(str(project), str(new_location))
        console.print("\n[bold success]✓ Migracion completada:[/]")
        console.print(
            f"  [realm]{project.name}[/] movido de "
            f"[{REALM_COLORS.get(source, 'white')}]{source}[/] "
            f"a [{REALM_COLORS.get(dest, 'white')}]{dest}[/]"
        )
    except Exception as e:
        console.print(f"[bold error]✗ Error durante migracion: {e}[/]")


# ── Main ────────────────────────────────────────────────────────
def main():
    print_banner()
    app()


if __name__ == "__main__":
    main()
