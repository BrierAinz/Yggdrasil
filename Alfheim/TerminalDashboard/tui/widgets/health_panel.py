"""System health panel widget for the Textual TUI dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static


if TYPE_CHECKING:
    from tui.health import SystemHealth


class SystemHealthPanel(Static):
    """A Textual widget that displays system health information.

    Shows CPU, RAM, swap, disk, GPU, and Python process information
    in a formatted panel with progress bars and tables.
    """

    def __init__(
        self,
        health: SystemHealth | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the health panel.

        Args:
            health: Initial SystemHealth data. If None, shows placeholder.
            name: Widget name (passed to Textual Widget).
            id: Widget ID (passed to Textual Widget).
            classes: Widget CSS classes (passed to Textual Widget).

        """
        super().__init__(name=name, id=id, classes=classes)
        self._health = health
        self._flash_fields: set[str] = set()

    def update_health(self, health: SystemHealth, flash_fields: set[str] | None = None) -> None:
        """Update the panel with new health data.

        Args:
            health: New SystemHealth snapshot.
            flash_fields: Set of field names that changed and should flash.

        """
        self._health = health
        self._flash_fields = flash_fields or set()
        self._render_and_update()

    def _render_and_update(self) -> None:
        """Render the health panel and update the widget."""
        if self._health is None:
            self.update(
                Panel(
                    "No health data available",
                    title="System Health",
                    border_style="dim",
                ),
            )
            return

        renderable = self._build_renderable(self._health)
        self.update(renderable)

    def _build_renderable(self, health: SystemHealth) -> Panel:
        """Build the Rich renderable for the health panel.

        Returns:
            Rich Panel containing formatted health information.

        """
        sections: list[Any] = []

        # -- CPU Section --
        cpu_text = Text()
        cpu_label = self._maybe_flash("cpu_pct", f"CPU  {health.cpu_pct:5.1f}%")
        cpu_text.append(cpu_label)
        if health.cpu_per_core:
            cores_str = " | ".join(f"{c:.0f}%" for c in health.cpu_per_core)
            cpu_text.append(f"\n  Cores: {cores_str}", style="dim")
        if health.cpu_freq_mhz:
            cpu_text.append(f"\n  Freq: {health.cpu_freq_mhz:.0f} MHz", style="dim")
        sections.append(cpu_text)

        # -- RAM Section --
        ram_text = Text()
        ram_label = self._maybe_flash("ram_pct", f"RAM  {health.ram_pct:5.1f}%")
        ram_text.append(ram_label)
        ram_text.append(
            f"\n  {health.ram_used_gb:.1f} / {health.ram_total_gb:.1f} GB  "
            f"(avail: {health.ram_available_gb:.1f} GB)",
            style="dim",
        )
        if health.swap_total_gb > 0:
            self._maybe_flash("swap_pct", f"Swap {health.swap_pct:5.1f}%")
            ram_text.append(f"\n  Swap: {health.swap_used_gb:.1f} / {health.swap_total_gb:.1f} GB")
        sections.append(ram_text)

        # -- Disk Section --
        disk_text = Text()
        disk_label = self._maybe_flash("disk_pct", f"Disk {health.disk_pct:5.1f}%")
        disk_text.append(disk_label)
        disk_text.append(
            f"\n  {health.disk_used_gb:.1f} / {health.disk_total_gb:.1f} GB  "
            f"(free: {health.disk_free_gb:.1f} GB) [{health.disk_path}]",
            style="dim",
        )
        sections.append(disk_text)

        # -- Load Average --
        load_text = Text()
        load_text.append(
            f"Load: {health.load_avg_1m:.2f} / "
            f"{health.load_avg_5m:.2f} / {health.load_avg_15m:.2f}",
            style="dim",
        )
        sections.append(load_text)

        # -- GPU Section --
        if health.gpus:
            for i, gpu in enumerate(health.gpus):
                gpu_text = Text()
                gpu_header = self._maybe_flash(f"gpu_{i}_util", f"GPU{i}: {gpu.name}")
                gpu_text.append(gpu_header)
                gpu_text.append(f"\n  Util: {gpu.utilization_pct:.0f}%", style="dim")
                gpu_text.append(
                    f"  Mem: {gpu.memory_used_mb:.0f}/{gpu.memory_total_mb:.0f} MB "
                    f"({gpu.memory_util_pct:.0f}%)",
                    style="dim",
                )
                if gpu.temperature_c > 0:
                    temp_style = "yellow" if gpu.temperature_c > 80 else "green"
                    gpu_text.append(f"  Temp: {gpu.temperature_c:.0f}°C", style=temp_style)
                if gpu.power_draw_w > 0:
                    gpu_text.append(
                        f"  Power: {gpu.power_draw_w:.0f}/{gpu.power_limit_w:.0f}W",
                        style="dim",
                    )
                sections.append(gpu_text)

        # -- Python Processes --
        if health.python_processes:
            proc_table = Table(
                title=f"Python Processes ({health.python_process_count})",
                show_header=True,
                header_style="bold",
                box=None,
                padding=(0, 1),
            )
            proc_table.add_column("PID", style="cyan", width=6)
            proc_table.add_column("CPU%", width=6)
            proc_table.add_column("MEM%", width=6)
            proc_table.add_column("Command", style="dim")

            for proc in health.python_processes[:8]:  # Show top 8
                proc_table.add_row(
                    str(proc.get("pid", "")),
                    f"{proc.get('cpu_pct', 0):.1f}",
                    f"{proc.get('mem_pct', 0):.1f}",
                    str(proc.get("command", ""))[:60],
                )

            sections.append(proc_table)

        # Combine all sections
        group = Group(*sections)
        return Panel(group, title="System Health", border_style="green")

    def _maybe_flash(self, field: str, text: str) -> Text:
        """Return Text, styled with flash if the field has changed.

        Returns:
            Rich Text object, optionally styled with flash effect.

        """
        rich_text = Text(text)
        if field in self._flash_fields:
            rich_text.stylize("bold reverse")
        else:
            rich_text.stylize("bold")
        return rich_text

    def on_mount(self) -> None:
        """Perform initial render on mount."""
        self._render_and_update()

    @staticmethod
    def format_uptime(seconds: float) -> str:
        r"""Format uptime in seconds to human-readable string.

        Returns:
            Formatted string like \"2d 3h 15m\".

        """
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
