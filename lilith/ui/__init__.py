"""Lilith Agent — UI components (themes, banners, formatters)."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.theme import Theme


# ── Nordic Frost Theme ────────────────────────────────────────
NORDIC_THEME = Theme(
    {
        "frost": "#7eb8c4",
        "amethyst": "#8b6cc7",
        "snow": "#c8d0e0",
        "ember": "#c94f4f",
        "pine": "#5b8a72",
        "gold": "#c9a55a",
        "steel": "#3d4162",
        "lilith": "bold #8b6cc7",
        "user": "bold #7eb8c4",
        "tool": "#c9a55a",
        "muted": "#3d4162",
        "think": "italic #5b8a72",
        "error": "bold #c94f4f",
        "ok": "bold #5b8a72",
        "warn": "bold #c9a55a",
    }
)

console = Console(theme=NORDIC_THEME)

# ── Banner ────────────────────────────────────────────────────
BANNER = """[lilith]
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ᛚ        LILITH         ᛚ                                ║
    ║                                                               ║
    ║     Dark Goddess of Yggdrasil Digital                         ║
    ║                                                               ║
    ║     ᛏ Coding Agent    ᛒ Memory       ᚨ Skills                ║
    ║     ᛟ Safety          ᚱ Parallel     ᛊ Web                   ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝[/lilith]"""


def print_banner(version: str = "4.0.0"):
    """Print the Lilith banner."""
    console.print()
    console.print(
        Panel.fit(
            BANNER,
            border_style="#1a1d35",
            title=f"[lilith]ᛒ LILITH v{version}[/lilith]",
            title_align="left",
        )
    )
    console.print()


def print_status_table(
    provider: str, model: str, session_id: str, tools: int, skills: int, knowledge: int
):
    """Print startup status table."""
    status = Table(show_header=False, box=None, padding=(0, 2), border_style="#1a1d35")
    status.add_column(style="gold", width=12)
    status.add_column(style="frost")
    status.add_row("ᛥ Provider", provider)
    status.add_row("ᛥ Model", model)
    status.add_row("ᛥ Session", session_id)
    status.add_row("ᛥ Tools", f"{tools} available")
    status.add_row("ᛥ Skills", f"{skills} saved")
    status.add_row("ᛥ Knowledge", f"{knowledge} facts")
    console.print(status)
    console.print()


def print_tool_call(name: str, args_preview: str):
    """Print a tool call indicator."""
    console.print(f"  [tool]ᛥ {name}[/tool] [muted]{args_preview}[/muted]")


def print_thinking(thought: str):
    """Print thinking output."""
    console.print("\n  [think]💭 Thinking:[/think]")
    for line in thought.split("\n"):
        console.print(f"  [think]  {line}[/think]")


def print_response(content: str):
    """Print a markdown response."""
    console.print(Markdown(content))


def print_separator():
    """Print a visual separator."""
    console.print(Rule(style="#1a1d35"))
    console.print()


def print_error(message: str):
    """Print an error message."""
    console.print(f"\n  [error]Error: {message}[/error]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"\n  [warn]⚠ {message}[/warn]")


def print_muted(message: str):
    """Print muted text."""
    console.print(f"  [muted]{message}[/muted]")
