"""ForgeMaster CLI — Typer application with Rich output."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.tree import Tree

from forgemaster.logging import configure_logging


app = typer.Typer(
    name="forgemaster",
    help="⚒️  ForgeMaster — Muspelheim resource manager for LLM models, VRAM, and disk.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug-level logging"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress info-level logs (warnings only)"
    ),
) -> None:
    """ForgeMaster — Muspelheim resource manager for LLM models, VRAM, and disk."""
    configure_logging(verbose=verbose, quiet=quiet)


# Default scan paths for the user's system
DEFAULT_PATHS = [
    Path.home() / ".cache" / "huggingface",
    Path.home() / ".cache" / "lm-studio",
    Path(os.environ.get("COMFYUI_MODELS_DIR", "models")),
]


def _format_size(size_bytes: int | float) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


# ─── Scan Command ────────────────────────────────────────────────────────────


@app.command()
def scan(
    paths: list[str] | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Paths to scan (default: HF cache, LM Studio, ComfyUI)",
    ),
    catalog: bool = typer.Option(False, "--catalog", "-c", help="Save results to catalog database"),
) -> None:
    """Scan directories for model files (GGUF, safetensors, PyTorch)."""
    from forgemaster.scanner import ModelScanner

    scan_paths = [Path(p) for p in paths] if paths else DEFAULT_PATHS
    # Filter to existing paths only
    scan_paths = [p for p in scan_paths if p.exists()]

    if not scan_paths:
        console.print(
            "[bold red]No valid paths to scan.[/] Specify --path or ensure defaults exist."
        )
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]Scanning..."),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning", total=None)
        scanner = ModelScanner()
        result = scanner.scan(scan_paths)
        progress.update(task, completed=True)

    # Display results as a Rich table
    table = Table(title="🔍 Model Scan Results", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Format", style="green")
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Architecture", style="magenta")
    table.add_column("Quantization", style="blue")
    table.add_column("Path", style="dim")

    for model in sorted(result.models, key=lambda m: m.size_bytes or 0, reverse=True):
        table.add_row(
            model.name,
            model.format or "unknown",
            _format_size(model.size_bytes) if model.size_bytes else "N/A",
            model.architecture or "unknown",
            model.quantization or "unknown",
            str(model.path)[:60] + "..."
            if model.path and len(str(model.path)) > 60
            else str(model.path or ""),
        )

    console.print(table)
    console.print(f"\n[bold]{len(result.models)}[/] models found across {len(scan_paths)} path(s)")

    if catalog:
        from forgemaster.catalog import Catalog

        db = Catalog()
        added = 0
        for model in result.models:
            db.add_model(model)
            added += 1
        console.print(f"[green]Saved {added} models to catalog.[/]")


# ─── List Command ────────────────────────────────────────────────────────────


@app.command(name="list")
def list_models(
    fmt: str = typer.Option(
        "all", "--format", "-f", help="Filter by format: gguf, safetensors, pt, all"
    ),
    architecture: str = typer.Option("all", "--arch", "-a", help="Filter by architecture"),
) -> None:
    """List all cataloged models with Rich table output."""
    from forgemaster.catalog import Catalog

    db = Catalog()
    models = db.list_models()

    if not models:
        console.print(
            "[yellow]No models in catalog. Run [bold]forgemaster scan --catalog[/] first.[/]"
        )
        return

    fmt_filter = None if fmt == "all" else fmt
    if fmt_filter:
        models = [m for m in models if m["format"] == fmt_filter]

    if architecture != "all":
        models = [m for m in models if m["architecture"] == architecture]

    table = Table(title="📋 Cataloged Models", show_lines=True)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Name", style="bold cyan")
    table.add_column("Format", style="green")
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Architecture", style="magenta")
    table.add_column("Quantization", style="blue")
    table.add_column("Last Scanned", style="dim")

    for model in models:
        table.add_row(
            str(model["id"]) if "id" in model else "-",
            model["name"],
            model["format"] or "unknown",
            _format_size(model["size_bytes"]) if model["size_bytes"] else "N/A",
            model["architecture"] or "unknown",
            model["quantization"] or "unknown",
            str(model["scanned_at"])[:19] if model.get("scanned_at") else "-",
        )

    console.print(table)
    console.print(f"\n[bold]{len(models)}[/] model(s) shown")


# ─── Stats Command ───────────────────────────────────────────────────────────


@app.command()
def stats(
    paths: list[str] | None = typer.Option(None, "--path", "-p", help="Paths to analyze"),
) -> None:
    """Show disk usage statistics and model distribution."""
    from forgemaster.disk import DiskScanner

    scan_paths = [Path(p) for p in paths] if paths else DEFAULT_PATHS
    scan_paths = [p for p in scan_paths if p.exists()]

    if not scan_paths:
        console.print("[bold red]No valid paths to analyze.[/]")
        raise typer.Exit(1)

    disk = DiskScanner()
    usage = disk.scan_usage(scan_paths)

    # Overview panel
    overview = Panel(
        f"[bold]Total:[/]{_format_size(usage.total_bytes):>12}    "
        f"[green]Used:[/]{_format_size(usage.used_bytes):>12}    "
        f"[blue]Free:[/]{_format_size(usage.free_bytes):>12}\n"
        f"[yellow]Models:[/]{_format_size(usage.model_bytes):>12} ({usage.model_percent:.1f}%)    "
        f"[red]Other:[/]{_format_size(usage.other_bytes):>12} ({usage.other_percent:.1f}%)",
        title="💾 Disk Usage",
        border_style="bright_blue",
    )
    console.print(overview)

    # Per-directory breakdown
    dir_usage = disk.scan_directory_usage(scan_paths)
    if dir_usage:
        table = Table(title="📁 Per-Directory Breakdown")
        table.add_column("Directory", style="cyan")
        table.add_column("Model Size", justify="right", style="yellow")
        for dir_path, size in sorted(dir_usage.items(), key=lambda x: x[1], reverse=True):
            table.add_row(str(dir_path), _format_size(size))
        console.print(table)


# ─── Check Command ───────────────────────────────────────────────────────────


@app.command()
def check(
    model_name: str = typer.Argument(..., help="Model name to check VRAM compatibility"),
    gpu_vram: int | None = typer.Option(
        None, "--gpu-vram", "-g", help="GPU VRAM in MB (default: auto-detect)"
    ),
) -> None:
    """Check if a model can run on the current GPU."""
    from forgemaster.gpu import GPUMonitor
    from forgemaster.scanner import ModelScanner
    from forgemaster.vram import GPUProfile, VRAMCalculator

    # Determine GPU VRAM
    if gpu_vram:
        total_vram_gb = gpu_vram / 1024  # Convert MB input to GB
    else:
        monitor = GPUMonitor()
        gpu_infos = monitor.get_gpu_info()
        if gpu_infos:
            total_vram_gb = gpu_infos[0].vram_total_mb / 1024
        else:
            # Default to RTX 3060 12GB
            total_vram_gb = 12.0
            console.print("[dim]No GPU detected, assuming RTX 3060 12GB[/]")

    gpu = GPUProfile(name="Current GPU", vram_total_gb=total_vram_gb)

    # Find the model
    scanner = ModelScanner()
    scan_result = scanner.scan(DEFAULT_PATHS)
    matching = [m for m in scan_result.models if model_name.lower() in m.name.lower()]

    calc = VRAMCalculator()

    if not matching:
        console.print(f"[yellow]Model '{model_name}' not found locally.[/]")
        console.print("[dim]Install it first, then run check again.[/]")
        raise typer.Exit(1)

    model = matching[0]
    est = calc.calculate(model)

    # Can it run?
    can_run = calc.can_run(model, gpu)
    can_run_str = "[green]✓ CAN RUN[/]" if can_run else "[red]✗ CANNOT RUN[/]"
    offload_str = ""
    if not can_run:
        strategy = calc.suggest_offload(model, gpu)
        if strategy.gpu_layers > 0:
            offload_str = (
                f"\n[dim]  Partial offload: {strategy.gpu_layers} GPU layers, "
                f"{strategy.cpu_layers} CPU layers[/]"
            )
        else:
            offload_str = "\n[dim]  Requires full CPU offload[/]"

    panel = Panel(
        f"[bold]{model.name}[/]\n"
        f"Format:          {model.format or 'unknown'}\n"
        f"Size:            {_format_size(model.size_bytes) if model.size_bytes else 'N/A'}\n"
        f"Model Weights:   {est.model_weights_gb:.2f} GB\n"
        f"KV Cache (4k):   {est.kv_cache_gb:.2f} GB\n"
        f"Overhead:        {est.overhead_gb:.2f} GB\n"
        f"Total Required:  {est.total_gb:.2f} GB\n"
        f"GPU VRAM:        {gpu.vram_total_gb:.1f} GB\n"
        f"\n{can_run_str}{offload_str}",
        title="🎮 VRAM Check",
        border_style="green" if can_run else "red",
    )
    console.print(panel)


# ─── GPU Command ──────────────────────────────────────────────────────────────


@app.command()
def gpu() -> None:
    """Show GPU information and current utilization."""
    from forgemaster.gpu import GPUMonitor

    monitor = GPUMonitor()
    gpu_infos = monitor.get_gpu_info()

    if not gpu_infos:
        console.print("[bold red]No GPU detected.[/]")
        console.print(monitor.get_fallback_message())
        raise typer.Exit(1)

    for info in gpu_infos:
        # VRAM bar
        vram_used_pct = info.vram_used_mb / info.vram_total_mb * 100 if info.vram_total_mb else 0
        bar_len = 30
        filled = int(bar_len * vram_used_pct / 100)
        bar = f"[green]{'█' * filled}[/][dim]{'░' * (bar_len - filled)}[/]"

        # GPU type badge
        type_badge = {
            "nvidia": "[green]NVIDIA[/]",
            "amd": "[red]AMD[/]",
            "apple": "[magenta]Apple Silicon[/]",
        }.get(info.gpu_type, "")

        panel = Panel(
            f"[bold]{info.name}[/] {type_badge}\n\n"
            f"VRAM:   {bar} {_format_size(info.vram_used_mb * 1024 * 1024)} "
            f"/ {_format_size(info.vram_total_mb * 1024 * 1024)} "
            f"({vram_used_pct:.0f}%)\n"
            f"Temp:   {info.temperature}°C\n"
            f"Util:   {info.utilization_pct}%\n"
            f"Driver: {info.driver_version or 'unknown'}",
            title="🎮 GPU Status",
            border_style="bright_cyan",
        )
        console.print(panel)

    # Only show processes for NVIDIA GPUs
    nvidia_gpus = [g for g in gpu_infos if g.gpu_type == "nvidia"]
    if nvidia_gpus:
        processes = monitor.get_gpu_processes()
        if processes:
            table = Table(title="🔥 GPU Processes")
            table.add_column("PID", style="dim", justify="right")
            table.add_column("Name", style="cyan")
            table.add_column("GPU Memory", justify="right", style="yellow")
            for proc in processes:
                table.add_row(
                    str(proc.pid),
                    proc.name,
                    _format_size(proc.gpu_memory_mb * 1024 * 1024),
                )
            console.print(table)


# ─── Duplicates Command ──────────────────────────────────────────────────────


@app.command(name="dupes")
def find_duplicates(
    paths: list[str] | None = typer.Option(
        None, "--path", "-p", help="Paths to scan for duplicates"
    ),
    cleanup: bool = typer.Option(False, "--cleanup", "-c", help="Generate cleanup recommendations"),
) -> None:
    """Find duplicate or similar model files."""
    from forgemaster.disk import DuplicateFinder

    scan_paths = [Path(p) for p in paths] if paths else DEFAULT_PATHS
    scan_paths = [p for p in scan_paths if p.exists()]

    if not scan_paths:
        console.print("[bold red]No valid paths to scan.[/]")
        raise typer.Exit(1)

    finder = DuplicateFinder()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        scan_task = progress.add_task("Scanning files...", total=None)
        dupes = finder.find_duplicates(scan_paths)
        progress.update(scan_task, completed=True, total=1)

        if dupes:
            hash_task = progress.add_task("Computing hashes...", total=len(dupes))
            progress.update(hash_task, advance=len(dupes))

    if not dupes:
        console.print("[green]No duplicates found![/]")
        return

    table = Table(title="🔁 Duplicate Models", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Copies", justify="right", style="yellow")
    table.add_column("Wasted Space", justify="right", style="red")

    for group in dupes:
        table.add_row(
            group.name,
            str(len(group.files)),
            _format_size(group.total_wasted_bytes),
        )

    console.print(table)
    total_wasted = sum(g.total_wasted_bytes for g in dupes)
    console.print(
        f"\n[bold red]{len(dupes)} duplicate group(s) — {_format_size(total_wasted)} wasted[/]"
    )

    if cleanup:
        report = finder.generate_cleanup_report(scan_paths)
        console.print("\n[bold]Cleanup recommendations:[/]")
        for action in report.actions:
            console.print(
                f"  • [yellow]{action.reason}[/]: {action.path} ({_format_size(action.size_bytes)})"
            )
        console.print(
            f"\n[green]Total reclaimable: {_format_size(report.total_reclaimable_bytes)}[/]"
        )


# ─── Download Command ─────────────────────────────────────────────────────────


@app.command()
def download(
    model_id: str = typer.Argument(
        ..., help="HuggingFace model ID (e.g. 'TheBloke/Llama-2-7B-GGUF')"
    ),
    revision: str = typer.Option("main", "--revision", "-r", help="Model revision/branch"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force re-download even if file exists"
    ),
    list_only: bool = typer.Option(
        False, "--list-only", "-l", help="List available files without downloading"
    ),
) -> None:
    """Download a model from HuggingFace Hub."""
    import logging

    from forgemaster.downloader import DownloadConfig, ModelDownloader

    log = logging.getLogger("forgemaster.cli")
    config = DownloadConfig(
        model_id=model_id,
        revision=revision,
        cache_dir=str(Path(output))
        if output
        else str(Path("~").expanduser() / ".cache" / "huggingface" / "hub"),
        force_download=force,
    )

    downloader = ModelDownloader()

    # Fetch available files
    console.print(f"[bold]Fetching file list for [cyan]{model_id}[/]...")
    try:
        files = downloader.list_model_files(config)
    except Exception as e:
        console.print(f"[red]Error listing files: {e}[/]")
        raise typer.Exit(1) from None

    if not files:
        console.print("[yellow]No files found for this model.[/]")
        raise typer.Exit(1)

    # Display file tree
    console.print(f"[green]Found {len(files)} file(s)[/]")
    tree = Tree(f"[bold cyan]{model_id}[/] [dim](revision: {revision})[/]")
    for f in files:
        tree.add(f"[green]{f}[/]")
    console.print(tree)

    # If --list-only, stop here
    if list_only:
        log.debug("--list-only requested, skipping download")
        return

    # Download with progress — show total size if available
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading", total=None)

        def on_progress(p):
            """Update the Rich progress bar with bytes downloaded so far."""
            total = int(p.total_bytes) if p.total_bytes else None
            downloaded = int(p.downloaded_bytes) if p.downloaded_bytes else 0
            progress.update(task, completed=downloaded, total=total)
            if total and not progress.tasks[0].description.endswith(""):
                progress.update(task, description=f"Downloading {model_id}")

        try:
            results = downloader.download_model(config, progress_callback=on_progress)
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/]")
            raise typer.Exit(1) from None

    console.print("[bold green]Download complete![/]")
    for r in results:
        console.print(f"  ✓ {r} ({_format_size(r.stat().st_size) if r.exists() else 'N/A'})")


# ─── Version Command ──────────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Show ForgeMaster version."""
    from forgemaster import __version__

    console.print(f"⚒️  ForgeMaster v{__version__}")


# ─── Config Command ──────────────────────────────────────────────────────────


config_app = typer.Typer(
    name="config",
    help="⚙️  View and edit ForgeMaster configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


@config_app.command(name="show")
def config_show() -> None:
    """Show current configuration."""
    from forgemaster.config import load_config

    cfg = load_config()

    table = Table(title="⚙️  ForgeMaster Configuration", show_lines=True)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="green")

    table.add_row("yggdrasil_root", cfg.yggdrasil_root or "(not set)")
    table.add_row("gpu_profile", cfg.gpu_profile)
    table.add_row("catalog_path", cfg.catalog_path)
    for i, d in enumerate(cfg.scan_dirs):
        label = f"scan_dirs[{i}]"
        table.add_row(label, d)

    console.print(table)

    if cfg.yggdrasil_root:
        console.print(
            "\n[dim]YGGDRASIL_ROOT is set — scan_dirs and catalog_path may be overridden.[/]"
        )


@config_app.command(name="set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g. gpu_profile, scan_dirs.0)"),
    value: str = typer.Argument(help="New value"),
) -> None:
    """Set a configuration value and save to disk."""
    from forgemaster.config import set_config_value

    try:
        cfg = set_config_value(key, value)
        console.print(f"[green]Set {key} = {value}[/]")
        console.print(f"[dim]Config saved to {cfg.catalog_path}[/]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
