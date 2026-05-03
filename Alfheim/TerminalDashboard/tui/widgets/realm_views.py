"""Realm detail views for all 9 Yggdrasil realms.

Each realm has a dedicated render method that produces a Rich renderable
showing common information (projects, git status, test status, last commit)
plus realm-specific details, file count, total size, key files, and recent
git activity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from tui.git_utils import get_git_activity
from tui.scanner import (
    GitStatus,
    HealthStatus,
    ProjTestStatus,
    RealmScanner,
    RealmStatus,
)


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Emjoji / icon shortcuts (avoid heavy dependency on emoji fonts)
# ---------------------------------------------------------------------------
_HEALTH_ICON = {
    HealthStatus.HEALTHY: "[green]●[/]",
    HealthStatus.DEGRADED: "[yellow]●[/]",
    HealthStatus.DOWN: "[red]●[/]",
}

_GIT_ICON = {
    GitStatus.CLEAN: "[green]clean[/]",
    GitStatus.DIRTY: "[yellow]dirty[/]",
    GitStatus.NO_REPO: "[dim]no repo[/]",
}

_TEST_ICON = {
    ProjTestStatus.PASS: "[green]pass[/]",
    ProjTestStatus.FAIL: "[red]fail[/]",
    ProjTestStatus.UNKNOWN: "[dim]unknown[/]",
}

# Key files to look for in each project directory
_KEY_FILE_NAMES = ["README.md", "REGLAS.md", "pyproject.toml", "README.rst", "setup.py"]


def _count_files(directory: Path) -> int:
    """Count all files recursively in a directory (excluding hidden dirs)."""
    if not directory.is_dir():
        return 0
    count = 0
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and not any(
                p.startswith(".") or p == "__pycache__" for p in entry.relative_to(directory).parts
            ):
                count += 1
    except OSError:
        pass
    return count


def _total_size(directory: Path) -> int:
    """Calculate total file size in bytes recursively (excluding hidden dirs)."""
    if not directory.is_dir():
        return 0
    total = 0
    try:
        for entry in directory.rglob("*"):
            if entry.is_file() and not any(
                p.startswith(".") or p == "__pycache__" for p in entry.relative_to(directory).parts
            ):
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _find_key_files(directory: Path) -> list[str]:
    """Find key configuration files in a directory."""
    found: list[str] = []
    if not directory.is_dir():
        return found
    for name in _KEY_FILE_NAMES:
        if (directory / name).is_file():
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Helper: colour per realm
# ---------------------------------------------------------------------------
REALM_STYLES: dict[str, dict[str, str]] = {
    "Asgard": {"color": "gold1", "border": "gold1"},
    "Vanaheim": {"color": "cyan", "border": "cyan"},
    "Midgard": {"color": "green", "border": "green"},
    "Svartalfheim": {"color": "magenta", "border": "magenta"},
    "Alfheim": {"color": "bright_magenta", "border": "bright_magenta"},
    "Muspelheim": {"color": "red", "border": "red"},
    "Niflheim": {"color": "bright_blue", "border": "bright_blue"},
    "Jotunheim": {"color": "dark_orange", "border": "dark_orange"},
    "Helheim": {"color": "grey50", "border": "grey50"},
}


class RealmDetailView(Static):
    """A Textual Static widget that renders a detailed view of a single realm.

    The widget receives a ``RealmScanner`` instance upon construction.  Call
    ``set_realm(realm_name)`` to (re-)render the view for a specific realm.
    """

    DEFAULT_CSS = """
    RealmDetailView {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        scanner: RealmScanner | None = None,
        realm_name: str | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._scanner = scanner or RealmScanner()
        self._realm_name: str | None = None
        self._status: RealmStatus | None = None
        if realm_name is not None:
            self.set_realm(realm_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def realm_name(self) -> str | None:
        """Return the currently displayed realm name."""
        return self._realm_name

    @property
    def status(self) -> RealmStatus | None:
        """Return the cached RealmStatus (None until first set_realm call)."""
        return self._status

    def set_realm(self, realm_name: str) -> None:
        """Scan the given realm and re-render the detail view."""
        self._realm_name = realm_name
        self._status = self._scanner.scan_realm(realm_name)
        self._render_view()

    def refresh_data(self) -> None:
        """Re-scan the current realm and update the view."""
        if self._realm_name is not None:
            self.set_realm(self._realm_name)

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _render_view(self) -> None:
        """Build the Rich renderable and update the widget content.

        Safe to call even when the widget is not yet mounted; in that
        case the renderable is stored and will appear once the widget
        is composed.
        """
        if self._status is None:
            self._content = "[dim]No realm selected[/]"
        else:
            self._content = self._build_renderable(self._status)

        try:
            self.update(self._content)
        except Exception:
            # Widget not yet mounted – the content will be rendered on
            # the first mount via ``render()``.
            pass

    def render(self) -> object:
        """Render the widget content (called by Textual on mount)."""
        return getattr(self, "_content", "[dim]No realm selected[/]")

    def _build_renderable(self, status: RealmStatus) -> Panel:
        """Construct the full Rich Panel for a realm."""
        style = REALM_STYLES.get(status.name, {"color": "white", "border": "white"})
        color = style["color"]

        # Header line: realm name + health dot
        health_icon = _HEALTH_ICON.get(status.health, "?")
        header = Text.from_markup(
            f"[bold {color}]{escape(status.name)}[/]  {health_icon}  "
            f"[dim]{escape(status.description)}[/]"
        )

        # Common info table (projects, git, tests, last commit)
        table = self._build_common_table(status, color)

        # Realm overview panel (description, file count, total size, key files)
        overview = self._build_realm_overview(status, color)

        # Realm-specific section
        specific = self._build_realm_specific(status, color)

        # Git activity section
        git_section = self._build_git_activity(status, color)

        # Assemble panel content
        panel_content_items: list = [header, table]
        if overview is not None:
            panel_content_items.append(overview)
        if specific is not None:
            panel_content_items.append(specific)
        if git_section is not None:
            panel_content_items.append(git_section)

        panel = Panel(
            Group(*panel_content_items),
            title=f"[{color}]⬥ {escape(status.name)}[/{color}]",
            border_style=style["border"],
            padding=(1, 2),
        )
        return panel

    # ------------------------------------------------------------------
    # Common table (all realms share this)
    # ------------------------------------------------------------------

    def _build_common_table(self, status: RealmStatus, color: str) -> Table:
        """Build a table with projects, git status, test status, last commit."""
        table = Table(
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
            padding=(0, 1),
        )
        table.add_column("Project", ratio=2)
        table.add_column("Branch", ratio=1)
        table.add_column("Git", ratio=1)
        table.add_column("Test", ratio=1)
        table.add_column("Last Commit", ratio=1)

        for proj in status.projects:
            git_label = (
                _GIT_ICON.get(
                    GitStatus.DIRTY if proj.uncommitted_changes else GitStatus.CLEAN,
                    "[dim]?[/]",
                )
                if proj.branch
                else _GIT_ICON[GitStatus.NO_REPO]
            )

            test_label = _TEST_ICON.get(status.test_status, "[dim]?[/]")

            table.add_row(
                escape(proj.name),
                escape(proj.branch or "—"),
                Text.from_markup(git_label),
                Text.from_markup(test_label),
                escape(proj.last_commit or "—"),
            )

        if not status.projects:
            table.add_row("[dim]No projects found[/]", "", "", "", "")

        return table

    # ------------------------------------------------------------------
    # Realm overview (description, file count, total size, key files)
    # ------------------------------------------------------------------

    def _build_realm_overview(self, status: RealmStatus, color: str) -> Table | None:
        """Build a table showing realm description, file count, total size, and key files."""
        realm_path = status.path
        if not realm_path.is_dir():
            return None

        # Count files and total size in the realm directory
        file_count = _count_files(realm_path)
        total_size = _total_size(realm_path)
        size_str = _format_size(total_size)

        # Find key files at the realm root level
        key_files = _find_key_files(realm_path)

        table = Table(
            title="Overview",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Metric", ratio=1)
        table.add_column("Value", ratio=2)

        table.add_row("Description", escape(status.description))
        table.add_row("File Count", str(file_count))
        table.add_row("Total Size", size_str)
        table.add_row("Key Files", ", ".join(key_files) if key_files else "[dim]none[/]")
        return table

    # ------------------------------------------------------------------
    # Git activity (recent commits, status)
    # ------------------------------------------------------------------

    def _build_git_activity(self, status: RealmStatus, color: str) -> Table | None:
        """Build a table showing recent git activity for the realm directory."""
        realm_path = status.path
        if not realm_path.is_dir():
            return None

        activity = get_git_activity(realm_path)
        if not activity.is_git_repo:
            return None

        table = Table(
            title="Git Activity",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Hash", style="cyan", width=8)
        table.add_column("Message", ratio=3)

        if activity.recent_commits:
            for commit in activity.recent_commits[:10]:
                table.add_row(
                    escape(commit.hash[:8] if len(commit.hash) >= 8 else commit.hash),
                    escape(commit.message),
                )
        else:
            table.add_row("[dim]—[/]", "[dim]No commits[/]")

        # Add status line if dirty
        if activity.dirty:
            # Show up to 5 status lines
            for line in activity.status_lines[:5]:
                table.add_row("", Text.from_markup(f"[yellow]{escape(line)}[/]"))
            if len(activity.status_lines) > 5:
                table.add_row("", f"[dim]… and {len(activity.status_lines) - 5} more[/]")

        return table

    # ------------------------------------------------------------------
    # Realm-specific sections
    # ------------------------------------------------------------------

    def _build_realm_specific(self, status: RealmStatus, color: str) -> Table | None:
        """Dispatch to the realm-specific render method."""
        dispatch: dict[str, str] = {
            "Asgard": "_render_asgard",
            "Vanaheim": "_render_vanaheim",
            "Midgard": "_render_midgard",
            "Svartalfheim": "_render_svartalfheim",
            "Alfheim": "_render_alfheim",
            "Muspelheim": "_render_muspelheim",
            "Niflheim": "_render_niflheim",
            "Jotunheim": "_render_jotunheim",
            "Helheim": "_render_helheim",
        }
        method_name = dispatch.get(status.name)
        if method_name is None:
            return None
        method = getattr(self, method_name)
        return method(status, color)

    # --- Asgard: Lilith status, providers --------------------------------

    def _render_asgard(self, status: RealmStatus, color: str) -> Table:
        """Asgard-specific: Lilith core status and provider count."""
        table = Table(
            title="Asgard Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        # Lilith status: check for a Lilith project
        lilith_projects = [p for p in status.projects if "lilith" in p.name.lower()]
        if lilith_projects:
            lilith = lilith_projects[0]
            lilith_status = "active" if lilith.branch else "dormant"
            lilith_branch = lilith.branch or "—"
        else:
            lilith_status = "not found"
            lilith_branch = "—"

        # Provider count: count projects that look like provider modules
        provider_projects = [
            p for p in status.projects if "provider" in p.name.lower() or "api" in p.name.lower()
        ]

        table.add_row("Lilith Status", escape(lilith_status))
        table.add_row("Lilith Branch", escape(lilith_branch))
        table.add_row("Provider Modules", str(len(provider_projects)))
        table.add_row("Total Projects", str(status.project_count))
        return table

    # --- Vanaheim: agents, running tasks ---------------------------------

    def _render_vanaheim(self, status: RealmStatus, color: str) -> Table:
        """Vanaheim-specific: AI agent projects and potential running tasks."""
        table = Table(
            title="Vanaheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        agent_projects = [p for p in status.projects if "agent" in p.name.lower()]
        task_projects = [p for p in status.projects if "task" in p.name.lower()]

        # Running tasks: projects with uncommitted changes hint at active work
        active_count = sum(1 for p in status.projects if p.uncommitted_changes)

        table.add_row("Agent Projects", str(len(agent_projects)))
        table.add_row("Task Projects", str(len(task_projects)))
        table.add_row("Active (uncommitted)", str(active_count))
        table.add_row("Total Projects", str(status.project_count))
        return table

    # --- Midgard: app dashboards -----------------------------------------

    def _render_midgard(self, status: RealmStatus, color: str) -> Table:
        """Midgard-specific: personal app dashboards."""
        table = Table(
            title="Midgard Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        app_projects = [
            p for p in status.projects if "app" in p.name.lower() or "dashboard" in p.name.lower()
        ]

        table.add_row("App/Dashboard Projects", str(len(app_projects)))
        table.add_row("Total Projects", str(status.project_count))

        # List app names
        if app_projects:
            app_names = ", ".join(escape(p.name) for p in app_projects)
            table.add_row("Apps", app_names)
        return table

    # --- Svartalfheim: wiki stats, docs ----------------------------------

    def _render_svartalfheim(self, status: RealmStatus, color: str) -> Table:
        """Svartalfheim-specific: docs/knowledge/wiki projects."""
        table = Table(
            title="Svartalfheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        doc_projects = [
            p
            for p in status.projects
            if any(kw in p.name.lower() for kw in ("wiki", "doc", "knowledge", "guide"))
        ]

        table.add_row("Wiki/Doc Projects", str(len(doc_projects)))
        table.add_row("Total Projects", str(status.project_count))

        if doc_projects:
            doc_names = ", ".join(escape(p.name) for p in doc_projects)
            table.add_row("Docs", doc_names)
        return table

    # --- Alfheim: UI prototypes -------------------------------------------

    def _render_alfheim(self, status: RealmStatus, color: str) -> Table:
        """Alfheim-specific: UI prototypes and front-end projects."""
        table = Table(
            title="Alfheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        ui_projects = [
            p
            for p in status.projects
            if any(
                kw in p.name.lower() for kw in ("ui", "tui", "dashboard", "prototype", "frontend")
            )
        ]

        table.add_row("UI Prototype Projects", str(len(ui_projects)))
        table.add_row("Total Projects", str(status.project_count))

        if ui_projects:
            ui_names = ", ".join(escape(p.name) for p in ui_projects)
            table.add_row("UI Projects", ui_names)
        return table

    # --- Muspelheim: WIP, branches ----------------------------------------

    def _render_muspelheim(self, status: RealmStatus, color: str) -> Table:
        """Muspelheim-specific: WIP / active development / branch info."""
        table = Table(
            title="Muspelheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        wip_projects = [p for p in status.projects if p.uncommitted_changes]
        # Collect unique branches
        branches = sorted({p.branch for p in status.projects if p.branch})

        table.add_row("WIP (uncommitted)", str(len(wip_projects)))
        table.add_row("Unique Branches", str(len(branches)))
        table.add_row("Total Projects", str(status.project_count))

        if branches:
            branch_list = ", ".join(escape(b) for b in branches)
            table.add_row("Branches", branch_list)
        return table

    # --- Niflheim: resources, models, disk --------------------------------

    def _render_niflheim(self, status: RealmStatus, color: str) -> Table:
        """Niflheim-specific: resources, models, and disk."""
        table = Table(
            title="Niflheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        resource_projects = [
            p
            for p in status.projects
            if any(kw in p.name.lower() for kw in ("resource", "model", "asset", "data"))
        ]

        table.add_row("Resource/Model Projects", str(len(resource_projects)))
        table.add_row("Total Projects", str(status.project_count))

        if resource_projects:
            res_names = ", ".join(escape(p.name) for p in resource_projects)
            table.add_row("Resources", res_names)
        return table

    # --- Jotunheim: large projects ----------------------------------------

    def _render_jotunheim(self, status: RealmStatus, color: str) -> Table:
        """Jotunheim-specific: large/massive projects."""
        table = Table(
            title="Jotunheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        table.add_row("Total Projects", str(status.project_count))

        # List all projects with branch info
        if status.projects:
            project_lines = []
            for p in status.projects:
                branch_info = f" ({escape(p.branch)})" if p.branch else ""
                project_lines.append(f"{escape(p.name)}{branch_info}")
            table.add_row("Projects", "\n".join(project_lines))
        return table

    # --- Helheim: archived items ------------------------------------------

    def _render_helheim(self, status: RealmStatus, color: str) -> Table:
        """Helheim-specific: archived / dead projects."""
        table = Table(
            title="Helheim Details",
            title_style=f"bold {color}",
            show_header=True,
            header_style=f"bold {color}",
            expand=True,
        )
        table.add_column("Detail", ratio=1)
        table.add_column("Value", ratio=2)

        table.add_row("Archived Projects", str(status.project_count))

        # Show all archived with their status
        if status.projects:
            for p in status.projects:
                clean_status = "clean" if not p.uncommitted_changes else "dirty"
                table.add_row(
                    escape(p.name),
                    f"[dim]{escape(clean_status)} · {escape(p.branch or 'no branch')}[/]",
                )
        return table
