"""Yggdrasil CLI v6.0 — Unified entry point.

Usage:
  yggdrasil              # Launch interactive REPL
  yggdrasil "prompt"     # One-shot mode
  yggdrasil chat          # Explicit REPL mode
  yggdrasil status        # Show realm status
  yggdrasil launch        # Launch services
  yggdrasil config        # Show/edit configuration
"""

from __future__ import annotations

import asyncio
import platform
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import App, Parameter

from .config import CONFIG_DIR, YggdrasilConfig, load_config, save_config


if TYPE_CHECKING:
    import types


# ── Version ─────────────────────────────────────────────────────────

__version__ = "3.0.0"

# ── Cyclopts app ────────────────────────────────────────────────────

app = App(
    name="yggdrasil",
    help="Yggdrasil CLI v6.0 — Where Ancient Meets Digital",
    version=__version__,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _is_wsl() -> bool:
    """Check if running under WSL."""
    return platform.system() == "Linux" and "microsoft" in platform.release().lower()


def _resolve_yggdrasil_root() -> Path:
    """Find the Yggdrasil workspace root."""
    return Path(__file__).resolve().parents[3]


def _lazy_import_yggdrasil_cli() -> types.ModuleType:
    """Import the existing yggdrasil_cli module, adding the root to sys.path."""
    root = str(_resolve_yggdrasil_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    import yggdrasil_cli

    return yggdrasil_cli


def _apply_overrides(
    cfg: YggdrasilConfig,
    *,
    model: str | None = None,
    provider: str | None = None,
    local: bool = False,
    no_tools: bool = False,
) -> None:
    """Apply CLI flag overrides to a loaded config."""
    if model:
        cfg.model = model
    if provider:
        cfg.provider = provider
    if local:
        cfg.provider = "local"
        if cfg.base_url is None:
            cfg.base_url = "http://localhost:1234/v1"
        if cfg.model == "gpt-4o-mini":
            cfg.model = "local-model"
    if no_tools:
        cfg.tools.filesystem = False
        cfg.tools.coding = False
        cfg.tools.web_search = False
        cfg.tools.browser = False
        cfg.tools.system = False


# ── Commands ────────────────────────────────────────────────────────


@app.command
def chat(
    model: Annotated[str | None, Parameter(name=["--model", "-m"], help="Override model")] = None,
    provider: Annotated[
        str | None, Parameter(name=["--provider", "-p"], help="Override provider")
    ] = None,
    local: Annotated[bool, Parameter(name="--local", help="Use local LM Studio")] = False,
    no_tools: Annotated[bool, Parameter(name="--no-tools", help="Disable tools")] = False,
    verbose: Annotated[bool, Parameter(name=["--verbose", "-v"], help="Debug output")] = False,
    config_path: Annotated[str | None, Parameter(name="--config", help="Config file path")] = None,
) -> None:
    """Iniciar el REPL interactivo de Yggdrasil Agent."""
    import logging

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    cfg = load_config(config_path)
    _apply_overrides(cfg, model=model, provider=provider, local=local, no_tools=no_tools)

    from .agent import AgentSession
    from .repl import run_repl

    session = AgentSession(cfg)
    asyncio.run(run_repl(session))


@app.command
def prompt(
    text: Annotated[str, Parameter(help="Prompt para enviar al agente")],
    model: Annotated[str | None, Parameter(name=["--model", "-m"], help="Override model")] = None,
    provider: Annotated[
        str | None, Parameter(name=["--provider", "-p"], help="Override provider")
    ] = None,
    local: Annotated[bool, Parameter(name="--local", help="Use local LM Studio")] = False,
    no_tools: Annotated[bool, Parameter(name="--no-tools", help="Disable tools")] = False,
    config_path: Annotated[str | None, Parameter(name="--config", help="Config file path")] = None,
) -> None:
    """Modo one-shot: enviar un prompt y mostrar la respuesta."""
    cfg = load_config(config_path)
    _apply_overrides(cfg, model=model, provider=provider, local=local, no_tools=no_tools)

    from .agent import AgentSession
    from .repl import run_one_shot

    session = AgentSession(cfg)
    asyncio.run(run_one_shot(session, text))


@app.command
def status() -> None:
    """Mostrar estado de salud de los reinos y servicios de Yggdrasil."""
    try:
        ygg_cli = _lazy_import_yggdrasil_cli()
        ygg_cli.status()
    except (ImportError, ModuleNotFoundError):
        from .render import console

        console.print("[error]No se pudo importar yggdrasil_cli. Verifica la instalación.[/]")


@app.command
def launch() -> None:
    """Abrir menú interactivo para lanzar servicios de Yggdrasil."""
    try:
        ygg_cli = _lazy_import_yggdrasil_cli()
        ygg_cli.launch()
    except (ImportError, ModuleNotFoundError):
        from .render import console

        console.print("[error]No se pudo importar yggdrasil_cli. Verifica la instalación.[/]")


@app.command
def config(
    show: Annotated[bool, Parameter(name="--show", help="Mostrar configuración")] = True,
    edit: Annotated[bool, Parameter(name="--edit", help="Abrir configuración en editor")] = False,
    reset: Annotated[
        bool, Parameter(name="--reset", help="Restablecer configuración por defecto")
    ] = False,
    config_path: Annotated[
        str | None, Parameter(name="--path", help="Ruta del archivo de config")
    ] = None,
) -> None:
    """Mostrar o editar la configuración de Yggdrasil."""
    from .render import console

    if reset:
        path = Path(config_path) if config_path else CONFIG_DIR / "config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        save_config(YggdrasilConfig(), config_path=str(path))
        console.print(f"[success]✓ Configuración restablecida en: {path}[/]")
        return

    if edit:
        path = Path(config_path) if config_path else CONFIG_DIR / "config.yaml"
        if not path.exists():
            load_config(str(path))  # bootstrap
        editor = "nano" if _is_wsl() else ("notepad" if platform.system() == "Windows" else "vi")
        try:
            subprocess.run([editor, str(path)])
        except FileNotFoundError:
            console.print(f"[error]Editor '{editor}' no encontrado. Edita manualmente: {path}[/]")
        return

    # Default: show.
    cfg = load_config(config_path)
    console.print(cfg.model_dump_json(indent=2))


# ── Default handler (no subcommand) ────────────────────────────────


@app.default
def default_command(
    args: Annotated[tuple[str, ...] | None, Parameter(show=False)] = (),
    model: Annotated[str | None, Parameter(name=["--model", "-m"])] = None,
    provider: Annotated[str | None, Parameter(name=["--provider", "-p"])] = None,
    local: Annotated[bool, Parameter(name="--local")] = False,
    no_tools: Annotated[bool, Parameter(name="--no-tools")] = False,
    verbose: Annotated[bool, Parameter(name=["--verbose", "-v"])] = False,
    config_path: Annotated[str | None, Parameter(name="--config")] = None,
    version: Annotated[bool, Parameter(name=["--version"])] = False,
) -> None:
    """Punto de entrada por defecto — lanza REPL o procesa un prompt directo."""
    from .render import console

    if version:
        console.print(f"Yggdrasil CLI v{__version__}")
        return

    # If positional args look like a prompt, go one-shot.
    if args:
        prompt_text = " ".join(args)
        cfg = load_config(config_path)
        _apply_overrides(cfg, model=model, provider=provider, local=local, no_tools=no_tools)

        from .agent import AgentSession
        from .repl import run_one_shot

        session = AgentSession(cfg)
        asyncio.run(run_one_shot(session, prompt_text))
        return

    # No args → interactive REPL.
    chat(
        model=model,
        provider=provider,
        local=local,
        no_tools=no_tools,
        verbose=verbose,
        config_path=config_path,
    )


# ── Entry point ─────────────────────────────────────────────────────


def main() -> None:
    """CLI entry point."""
    app()
