"""Auto-refresh updater with asyncio, change detection, and flash animations."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from tui.health import HealthMonitor
from tui.scanner import RealmScanner


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


logger = logging.getLogger(__name__)

# Type alias for the data snapshot
Snapshot = dict[str, Any]


@dataclass
class ChangeRecord:
    """Record of a detected change between two snapshots."""

    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_significant(self) -> bool:
        """Whether the change is significant enough to warrant a flash."""
        if isinstance(self.old_value, int | float) and isinstance(self.new_value, int | float):
            # Numeric change > 5% is significant (or crossing zero)
            if self.old_value == 0 and self.new_value != 0:
                return True
            if self.old_value != 0:
                return abs(self.new_value - self.old_value) / max(abs(self.old_value), 1) > 0.05
            return abs(self.new_value) > 0.05
        # Non-numeric changes are always significant
        return self.old_value != self.new_value


@dataclass
class UpdateResult:
    """Result from an update cycle."""

    snapshot: Snapshot
    changes: list[ChangeRecord]
    has_changes: bool
    timestamp: datetime = field(default_factory=datetime.now)


class DashboardUpdater:
    """Manages periodic auto-refresh of dashboard data with change detection.

    Uses asyncio for non-blocking periodic data collection. Detects changes
    between snapshots and provides flash-style notification for significant
    changes.
    """

    def __init__(
        self,
        realm_scanner: RealmScanner | None = None,
        health_monitor: HealthMonitor | None = None,
        interval_seconds: float = 5.0,
    ) -> None:
        """Initialize the updater.

        Args:
            realm_scanner: Scanner for realm data. Created with defaults if None.
            health_monitor: Monitor for system health. Created with defaults if None.
            interval_seconds: Seconds between auto-refresh cycles.

        """
        self.realm_scanner = realm_scanner or RealmScanner()
        self.health_monitor = health_monitor or HealthMonitor()
        self.interval_seconds = interval_seconds

        self._previous_snapshot: Snapshot = {}
        self._current_snapshot: Snapshot = {}
        self._changes: list[ChangeRecord] = []
        self._flash_keys: set[str] = set()
        self._flash_timestamps: dict[str, datetime] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._on_change_callbacks: list[Callable[[UpdateResult], Coroutine]] = []
        self._last_update: datetime | None = None

    # -- Public API --------------------------------------------------------

    @property
    def current_snapshot(self) -> Snapshot:
        """Return the most recent data snapshot."""
        return self._current_snapshot

    @property
    def previous_snapshot(self) -> Snapshot:
        """Return the previous data snapshot."""
        return self._previous_snapshot

    @property
    def last_update_time(self) -> datetime | None:
        """Return the datetime of the last successful update."""
        return self._last_update

    @property
    def is_running(self) -> bool:
        """Whether the auto-refresh loop is active."""
        return self._running

    def on_change(self, callback: Callable[[UpdateResult], Coroutine]) -> None:
        """Register an async callback for when changes are detected."""
        self._on_change_callbacks.append(callback)

    def should_flash(self, key: str) -> bool:
        """Check whether a given key should show a flash animation.

                The flash lasts for 2 display cycles after a change is detected.

        Returns:
            True if the key should flash, False otherwise.

        """
        if key in self._flash_keys:
            return True
        flash_time = self._flash_timestamps.get(key)
        if flash_time is None:
            return False
        # Flash for up to 2 intervals after change
        elapsed = (datetime.now() - flash_time).total_seconds()
        return elapsed < self.interval_seconds * 2

    def clear_flash(self, key: str) -> None:
        """Clear the flash state for a given key."""
        self._flash_keys.discard(key)
        self._flash_timestamps.pop(key, None)

    def collect(self) -> Snapshot:
        """Collect a fresh data snapshot (realm scan + system health).

        Returns:
            Snapshot dictionary with realm and health data.

        """
        snapshot: Snapshot = {}

        try:
            realms = self.realm_scanner.scan_all()
            snapshot["realms"] = {name: status.to_dict() for name, status in realms.items()}
        except Exception as exc:
            logger.warning("Realm scan failed: %s", exc)
            snapshot["realms"] = self._current_snapshot.get("realms", {})

        try:
            health = self.health_monitor.get_health()
            snapshot["health"] = health.to_dict()
        except Exception as exc:
            logger.warning("Health check failed: %s", exc)
            snapshot["health"] = self._current_snapshot.get("health", {})

        snapshot["timestamp"] = datetime.now().isoformat()
        return snapshot

    def detect_changes(self, old: Snapshot, new: Snapshot, prefix: str = "") -> list[ChangeRecord]:
        """Detect changes between two snapshots.

                Recursively compares nested dicts. String-digit keys at the top level
                of 'realms' dict (realm names) are compared by their nested values.

        Returns:
            List of ChangeRecord for each detected difference.

        """
        changes: list[ChangeRecord] = []

        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val is None and new_val is not None:
                changes.append(ChangeRecord(key=full_key, old_value=None, new_value=new_val))
            elif old_val is not None and new_val is None:
                changes.append(ChangeRecord(key=full_key, old_value=old_val, new_value=None))
            elif isinstance(old_val, dict) and isinstance(new_val, dict):
                # Recurse into nested dicts
                changes.extend(self.detect_changes(old_val, new_val, prefix=full_key))
            elif old_val != new_val:
                changes.append(ChangeRecord(key=full_key, old_value=old_val, new_value=new_val))

        return changes

    def refresh(self) -> UpdateResult:
        """Perform one refresh cycle: collect, detect changes, update flash states.

        Returns:
            UpdateResult with the new snapshot and detected changes.

        """
        new_snapshot = self.collect()

        if self._current_snapshot:
            changes = self.detect_changes(self._current_snapshot, new_snapshot)
        else:
            # First run: everything is a "change"
            changes = []

        # Update flash states for significant changes
        for change in changes:
            if change.is_significant:
                self._flash_keys.add(change.key)
                self._flash_timestamps[change.key] = datetime.now()

        # Age out old flash keys (older than 2 * interval)
        cutoff = datetime.now()
        expired = [
            k
            for k, t in self._flash_timestamps.items()
            if (cutoff - t).total_seconds() >= self.interval_seconds * 2
        ]
        for k in expired:
            self._flash_keys.discard(k)
            del self._flash_timestamps[k]

        self._previous_snapshot = self._current_snapshot
        self._current_snapshot = new_snapshot
        self._changes = changes
        self._last_update = datetime.now()

        has_changes = len(changes) > 0
        return UpdateResult(
            snapshot=new_snapshot,
            changes=changes,
            has_changes=has_changes,
        )

    # -- Async lifecycle ---------------------------------------------------

    async def start(self) -> None:
        """Start the auto-refresh loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info("Dashboard updater started (interval=%.1fs)", self.interval_seconds)

    async def stop(self) -> None:
        """Stop the auto-refresh loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Dashboard updater stopped")

    async def _refresh_loop(self) -> None:
        """Run an internal async loop that refreshes data at the configured interval."""
        while self._running:
            try:
                result = self.refresh()
                if result.has_changes:
                    for callback in self._on_change_callbacks:
                        try:
                            await callback(result)
                        except Exception as exc:
                            logger.warning("Change callback error: %s", exc)
            except Exception as exc:
                logger.exception("Refresh loop error: %s", exc)

            await asyncio.sleep(self.interval_seconds)

    async def refresh_once(self) -> UpdateResult:
        """Perform a single async refresh (for manual triggers).

        Returns:
            UpdateResult with fresh snapshot and any detected changes.

        """
        return self.refresh()
