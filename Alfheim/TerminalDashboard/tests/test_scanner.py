"""Tests for the realm status scanner."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from tui.scanner import (
    REALMS,
    GitStatus,
    HealthStatus,
    ProjectInfo,
    ProjTestStatus,
    RealmScanner,
    RealmStatus,
)


class TestRealmConstants:
    """Test realm constants and configuration."""

    def test_nine_realms_defined(self) -> None:
        assert len(REALMS) == 9

    def test_all_expected_realms_present(self) -> None:
        expected = {
            "Asgard",
            "Vanaheim",
            "Alfheim",
            "Svartalfheim",
            "Muspelheim",
            "Niflheim",
            "Helheim",
            "Jotunheim",
            "Midgard",
        }
        assert set(REALMS.keys()) == expected


class TestProjectInfo:
    """Test ProjectInfo dataclass."""

    def test_create_project_info(self) -> None:
        p = ProjectInfo(
            name="test-project",
            path=Path("/tmp/test"),
            branch="main",
            uncommitted_changes=False,
        )
        assert p.name == "test-project"
        assert p.branch == "main"

    def test_to_dict(self) -> None:
        p = ProjectInfo(name="proj", path=Path("/tmp/proj"))
        d = p.to_dict()
        assert d["name"] == "proj"
        assert d["path"] == "/tmp/proj"


class TestRealmStatus:
    """Test RealmStatus dataclass."""

    def test_create_realm_status(self) -> None:
        r = RealmStatus(
            name="Asgard",
            path=Path("/tmp/Asgard"),
            project_count=3,
            git_status=GitStatus.CLEAN,
            test_status=ProjTestStatus.UNKNOWN,
            health=HealthStatus.HEALTHY,
        )
        assert r.name == "Asgard"
        assert r.project_count == 3

    def test_description_known_realm(self) -> None:
        r = RealmStatus(name="Asgard", path=Path("/tmp/Asgard"))
        assert r.description == "Core tech (Lilith)"

    def test_description_unknown_realm(self) -> None:
        r = RealmStatus(name="UnknownRealm", path=Path("/tmp/X"))
        assert r.description == "Unknown realm"

    def test_to_dict(self) -> None:
        r = RealmStatus(
            name="Asgard",
            path=Path("/tmp/Asgard"),
            git_status=GitStatus.CLEAN,
        )
        d = r.to_dict()
        assert d["name"] == "Asgard"
        assert d["git_status"] == "clean"


class TestRealmScanner:
    """Test the RealmScanner class."""

    def test_scan_all_returns_all_realms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            results = scanner.scan_all()
            assert len(results) == 9
            for realm_name in REALMS:
                assert realm_name in results

    def test_scan_nonexistent_realm_returns_down(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = RealmScanner(base_path=tmpdir)
            status = scanner.scan_realm("Asgard")
            assert status.name == "Asgard"
            assert status.health == HealthStatus.DOWN
            assert status.project_count == 0

    def test_scan_empty_realm(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            realm_path = Path(tmpdir) / "Asgard"
            realm_path.mkdir()
            scanner = RealmScanner(base_path=tmpdir)
            status = scanner.scan_realm("Asgard")
            assert status.name == "Asgard"
            assert status.project_count == 0
            assert status.health == HealthStatus.DOWN

    def test_scan_realm_with_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            realm_path = Path(tmpdir) / "Asgard"
            realm_path.mkdir()
            (realm_path / "lilith-core").mkdir()
            (realm_path / "lilith-tools").mkdir()
            scanner = RealmScanner(base_path=tmpdir)
            status = scanner.scan_realm("Asgard")
            assert status.project_count == 2
            assert len(status.projects) == 2

    def test_scan_skips_hidden_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            realm_path = Path(tmpdir) / "Asgard"
            realm_path.mkdir()
            (realm_path / ".hidden").mkdir()
            (realm_path / "__pycache__").mkdir()
            (realm_path / "real-project").mkdir()
            scanner = RealmScanner(base_path=tmpdir)
            status = scanner.scan_realm("Asgard")
            assert status.project_count == 1
            assert status.projects[0].name == "real-project"

    def test_default_base_path(self) -> None:
        scanner = RealmScanner()
        # Default path should resolve to Yggdrasil root (auto-detected from file location)
        assert scanner.base_path.is_absolute()
        assert scanner.base_path.name == "Yggdrasil"

    def test_custom_base_path(self) -> None:
        scanner = RealmScanner(base_path="/custom/path")
        assert scanner.base_path == Path("/custom/path")


class TestGitStatus:
    """Test GitStatus enum."""

    def test_values(self) -> None:
        assert GitStatus.CLEAN.value == "clean"
        assert GitStatus.DIRTY.value == "dirty"
        assert GitStatus.NO_REPO.value == "no_repo"


class TestProjTestStatus:
    """Test ProjTestStatus enum."""

    def test_values(self) -> None:
        assert ProjTestStatus.PASS.value == "pass"
        assert ProjTestStatus.FAIL.value == "fail"
        assert ProjTestStatus.UNKNOWN.value == "unknown"


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_values(self) -> None:
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.DOWN.value == "down"
