"""Tests for the DashboardUpdater – auto-refresh, change detection, flash."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from tui.health import HealthMonitor, SystemHealth
from tui.scanner import HealthStatus, RealmScanner, RealmStatus
from tui.updater import ChangeRecord, DashboardUpdater, UpdateResult


class TestChangeRecord:
    """Tests for the ChangeRecord dataclass."""

    def test_is_significant_string_change(self) -> None:
        cr = ChangeRecord(key="status", old_value="healthy", new_value="degraded")
        assert cr.is_significant is True

    def test_is_significant_string_same(self) -> None:
        cr = ChangeRecord(key="status", old_value="healthy", new_value="healthy")
        assert cr.is_significant is False

    def test_is_significant_numeric_large_change(self) -> None:
        cr = ChangeRecord(key="cpu_pct", old_value=10.0, new_value=60.0)
        assert cr.is_significant is True

    def test_is_significant_numeric_small_change(self) -> None:
        cr = ChangeRecord(key="cpu_pct", old_value=50.0, new_value=51.0)
        assert cr.is_significant is False  # < 5% change

    def test_is_significant_zero_to_nonzero(self) -> None:
        cr = ChangeRecord(key="val", old_value=0, new_value=0.5)
        assert cr.is_significant is True

    def test_is_significant_none_to_value(self) -> None:
        cr = ChangeRecord(key="val", old_value=None, new_value="hello")
        assert cr.is_significant is True

    def test_timestamp_auto_set(self) -> None:
        cr = ChangeRecord(key="x", old_value=0, new_value=1)
        assert isinstance(cr.timestamp, datetime)


class TestUpdateResult:
    """Tests for the UpdateResult dataclass."""

    def test_basic_construction(self) -> None:
        result = UpdateResult(
            snapshot={"a": 1},
            changes=[],
            has_changes=False,
        )
        assert result.snapshot == {"a": 1}
        assert result.has_changes is False
        assert isinstance(result.timestamp, datetime)


class TestDashboardUpdater:
    """Tests for the DashboardUpdater class."""

    def _make_updater(
        self,
        realms: dict | None = None,
        health: SystemHealth | None = None,
    ) -> DashboardUpdater:
        """Create an updater with mocked scanner and monitor."""
        scanner = MagicMock(spec=RealmScanner)
        if realms is not None:
            realm_objs = {}
            for name, data in realms.items():
                realm_objs[name] = RealmStatus(
                    name=name,
                    path="/tmp",
                    health=HealthStatus.HEALTHY,
                    **data,
                )
            scanner.scan_all.return_value = realm_objs
        else:
            scanner.scan_all.return_value = {}

        monitor = MagicMock(spec=HealthMonitor)
        if health is not None:
            monitor.get_health.return_value = health
        else:
            monitor.get_health.return_value = SystemHealth()

        return DashboardUpdater(
            realm_scanner=scanner,
            health_monitor=monitor,
            interval_seconds=1.0,
        )

    def test_initial_state(self) -> None:
        updater = self._make_updater()
        assert updater.current_snapshot == {}
        assert updater.previous_snapshot == {}
        assert updater.last_update_time is None
        assert not updater.is_running

    def test_collect_returns_snapshot(self) -> None:
        updater = self._make_updater(health=SystemHealth(cpu_pct=42.0))
        snapshot = updater.collect()
        assert "health" in snapshot
        assert "realms" in snapshot
        assert "timestamp" in snapshot

    def test_refresh_first_run_no_changes(self) -> None:
        updater = self._make_updater()
        result = updater.refresh()
        assert result.has_changes is False
        assert len(result.changes) == 0
        assert "timestamp" in result.snapshot

    def test_refresh_detects_changes(self) -> None:
        updater = self._make_updater(health=SystemHealth(cpu_pct=10.0))
        updater.refresh()  # First run

        # Change the health data
        updater.health_monitor.get_health.return_value = SystemHealth(cpu_pct=80.0)
        result = updater.refresh()
        assert result.has_changes is True
        assert len(result.changes) > 0

    def test_flash_detection(self) -> None:
        updater = self._make_updater(health=SystemHealth(cpu_pct=10.0))
        updater.refresh()

        # Big CPU change
        updater.health_monitor.get_health.return_value = SystemHealth(cpu_pct=80.0)
        updater.refresh()

        assert updater.should_flash("health.cpu_pct")

    def test_no_flash_for_unchanged(self) -> None:
        updater = self._make_updater(health=SystemHealth(cpu_pct=50.0))
        updater.refresh()

        assert not updater.should_flash("health.cpu_pct")

    def test_clear_flash(self) -> None:
        updater = self._make_updater(health=SystemHealth(cpu_pct=10.0))
        updater.refresh()

        updater.health_monitor.get_health.return_value = SystemHealth(cpu_pct=80.0)
        updater.refresh()
        updater.clear_flash("health.cpu_pct")
        assert not updater.should_flash("health.cpu_pct")

    def test_on_change_callback(self) -> None:
        callback = AsyncMock()
        updater = self._make_updater(health=SystemHealth(cpu_pct=10.0))
        updater.on_change(callback)
        updater.refresh()

        updater.health_monitor.get_health.return_value = SystemHealth(cpu_pct=80.0)
        updater.refresh()
        # Callback will be invoked by the async loop, not by sync refresh directly

    def test_detect_changes_nested(self) -> None:
        updater = self._make_updater()
        old = {"health": {"cpu_pct": 10.0, "ram_pct": 50.0}}
        new = {"health": {"cpu_pct": 80.0, "ram_pct": 50.0}}
        changes = updater.detect_changes(old, new)
        assert any(c.key == "health.cpu_pct" for c in changes)
        assert not any(c.key == "health.ram_pct" for c in changes)

    def test_detect_changes_new_key(self) -> None:
        updater = self._make_updater()
        old = {"health": {"cpu_pct": 10.0}}
        new = {"health": {"cpu_pct": 10.0, "ram_pct": 50.0}}
        changes = updater.detect_changes(old, new)
        assert any("ram_pct" in c.key for c in changes)

    def test_detect_changes_removed_key(self) -> None:
        updater = self._make_updater()
        old = {"health": {"cpu_pct": 10.0, "ram_pct": 50.0}}
        new = {"health": {"cpu_pct": 10.0}}
        changes = updater.detect_changes(old, new)
        assert any("ram_pct" in c.key for c in changes)


class TestDashboardUpdaterAsync:
    """Async tests for the DashboardUpdater lifecycle."""

    @pytest.mark.asyncio
    async def test_start_stop(self) -> None:
        scanner = MagicMock(spec=RealmScanner)
        scanner.scan_all.return_value = {}
        monitor = MagicMock(spec=HealthMonitor)
        monitor.get_health.return_value = SystemHealth()

        updater = DashboardUpdater(
            realm_scanner=scanner,
            health_monitor=monitor,
            interval_seconds=0.1,
        )
        await updater.start()
        assert updater.is_running

        await asyncio.sleep(0.3)  # Let it cycle a couple times

        await updater.stop()
        assert not updater.is_running

    @pytest.mark.asyncio
    async def test_refresh_once(self) -> None:
        scanner = MagicMock(spec=RealmScanner)
        scanner.scan_all.return_value = {}
        monitor = MagicMock(spec=HealthMonitor)
        monitor.get_health.return_value = SystemHealth(cpu_pct=55.0)

        updater = DashboardUpdater(
            realm_scanner=scanner,
            health_monitor=monitor,
            interval_seconds=1.0,
        )
        result = await updater.refresh_once()
        assert "health" in result.snapshot
        assert result.snapshot["health"]["cpu_pct"] == 55.0
