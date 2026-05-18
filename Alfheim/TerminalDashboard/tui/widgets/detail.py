"""Realm detail view widget – shows full information for the selected realm."""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

from tui.scanner import REALMS, GitStatus, HealthStatus, ProjTestStatus, RealmStatus
from tui.widgets.sidebar import REALM_ICONS


def _health_label(health: HealthStatus) -> str:
    c = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "yellow",
        HealthStatus.DOWN: "red",
    }
    l = {
        HealthStatus.HEALTHY: "HEALTHY",
        HealthStatus.DEGRADED: "DEGRADED",
        HealthStatus.DOWN: "DOWN",
    }
    colour = c.get(health, "white")
    label = l.get(health, "UNKNOWN")
    return f"[bold {colour}]{label}[/]"


def _git_label(gs: GitStatus) -> str:
    c = {GitStatus.CLEAN: "green", GitStatus.DIRTY: "yellow", GitStatus.NO_REPO: "red"}
    l = {
        GitStatus.CLEAN: "CLEAN",
        GitStatus.DIRTY: "DIRTY",
        GitStatus.NO_REPO: "NO REPO",
    }
    colour = c.get(gs, "white")
    label = l.get(gs, "UNKNOWN")
    return f"[bold {colour}]{label}[/]"


def _test_label(ts: ProjTestStatus) -> str:
    c = {
        ProjTestStatus.PASS: "green",
        ProjTestStatus.FAIL: "red",
        ProjTestStatus.UNKNOWN: "dim",
    }
    l = {
        ProjTestStatus.PASS: "PASS",
        ProjTestStatus.FAIL: "FAIL",
        ProjTestStatus.UNKNOWN: "UNKNOWN",
    }
    colour = c.get(ts, "white")
    label = l.get(ts, "UNKNOWN")
    return f"[bold {colour}]{label}[/]"


class RealmDetailView(Static):
    """Displays detailed information about the currently selected realm."""

    DEFAULT_CSS = """
    RealmDetailView {
        height: auto;
        padding: 1 2;
    }
    """

    realm_data: reactive[dict[str, RealmStatus]] = reactive({}, layout=True)
    selected_realm: reactive[str] = reactive("Asgard")

    def watch_selected_realm(self, new_realm: str) -> None:
        """Re-render when the selected realm changes."""
        self._update()

    def watch_realm_data(self, new_data: dict[str, RealmStatus]) -> None:
        """Re-render when realm data is refreshed."""
        self._update()

    def on_mount(self) -> None:
        """Inicializar contenido del panel de detalle al montar."""
        self._update()

    def _update(self) -> None:
        """Rebuild the detail content."""
        realm_name = self.selected_realm
        statuses: dict[str, RealmStatus] = self.realm_data
        status = statuses.get(realm_name)
        if status is None:
            self.update(f"[dim]Loading {realm_name}…[/]")
            return

        icon = REALM_ICONS.get(realm_name, "◆")
        description = REALMS.get(realm_name, "Unknown realm")

        lines: list[str] = [
            f"[bold] {icon}  {realm_name}[/]",
            f"[dim]    {description}[/]",
            "",
            f"  Health:  {_health_label(status.health)}",
            f"  Git:     {_git_label(status.git_status)}",
            f"  Tests:   {_test_label(status.test_status)}",
            f"  Path:    [dim]{status.path}[/]",
            f"  Last commit: [dim]{status.last_commit_date or 'N/A'}[/]",
            "",
            f"  [bold]Projects ({status.project_count})[/]",
        ]

        if status.projects:
            lines.append("")
            for proj in status.projects:
                branch_text = f"[dim]{proj.branch}[/]" if proj.branch else "[dim]no branch[/]"
                dirty = "[yellow]✗[/]" if proj.uncommitted_changes else "[green]✓[/]"
                lines.append(f"    {dirty} {proj.name}  {branch_text}")
        elif status.health == HealthStatus.DOWN:
            lines.append("    [dim]No projects found (realm directory missing)[/]")

        self.update("\n".join(lines))
