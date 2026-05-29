"""Shared pytest fixtures for TerminalDashboard tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from tui.scanner import REALMS, RealmScanner


if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# temp_yggdrasil – creates a temp directory tree of 9 realms with sample files
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_yggdrasil(tmp_path: Path) -> Path:
    """Create a temporary Yggdrasil directory tree with all 9 realms.

    Each realm gets a few sample project directories and files inside them,
    providing a realistic structure for scanner and integration tests.

    Returns the root path (the parent directory containing the 9 realm dirs).
    """
    root = tmp_path / "Yggdrasil"
    root.mkdir()

    # Per-realm project definitions: realm -> list of (project_name, [files])
    realm_projects: dict[str, list[tuple[str, list[str]]]] = {
        "Asgard": [
            ("Lilith-core", ["README.md", "pyproject.toml"]),
            ("provider-openai", ["README.md", "main.py"]),
        ],
        "Vanaheim": [
            ("agent-alpha", ["agent.py", "config.yaml"]),
            ("task-runner", ["runner.py"]),
        ],
        "Alfheim": [
            ("TerminalDashboard", ["pyproject.toml", "app.py"]),
            ("ui-prototype", ["prototype.html"]),
        ],
        "Svartalfheim": [
            ("wiki-engine", ["wiki.md", "index.py"]),
            ("knowledge-base", ["notes.md"]),
        ],
        "Muspelheim": [
            ("hotfix-urgent", ["fix.py"]),
            ("feature-x", ["feature.py", "test_feature.py"]),
        ],
        "Niflheim": [
            ("data-models", ["models.py"]),
            ("resource-assets", ["assets.csv"]),
        ],
        "Helheim": [
            ("legacy-app", ["old_code.py"]),
        ],
        "Jotunheim": [
            ("massive-project", ["big_main.py", "big_utils.py", "README.md"]),
            ("huge-repo", ["repo.py"]),
        ],
        "Midgard": [
            ("my-app", ["app.py", "requirements.txt"]),
            ("dashboard-home", ["dashboard.py"]),
        ],
    }

    # Validate that all 9 REALMS are represented
    for realm_name in REALMS:
        assert realm_name in realm_projects, f"Missing fixture data for realm: {realm_name}"

    for realm_name, projects in realm_projects.items():
        realm_dir = root / realm_name
        realm_dir.mkdir()
        for proj_name, files in projects:
            proj_dir = realm_dir / proj_name
            proj_dir.mkdir()
            for fname in files:
                (proj_dir / fname).write_text(f"# {proj_name} – {fname}\n", encoding="utf-8")

    return root


# ---------------------------------------------------------------------------
# mock_gpu – mocks nvidia-smi subprocess calls
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_gpu() -> MagicMock:
    """Mock nvidia-smi subprocess calls to return controlled GPU data.

    Returns the MagicMock object so tests can inspect/modify call args.
    The patch is applied to ``subprocess.run`` in ``tui.health`` so that
    ``HealthMonitor._get_gpu_info`` receives deterministic data.
    """
    nvidia_output = "NVIDIA GeForce RTX 3060, 45, 12288, 6144, 6144, 65, 40, 120.5, 170.0"
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = nvidia_output

    with patch("tui.health.subprocess.run", return_value=mock_result) as patched:
        yield patched


# ---------------------------------------------------------------------------
# scanner – returns a RealmScanner pointed at the temp_yggdrasil root
# ---------------------------------------------------------------------------


@pytest.fixture
def scanner(temp_yggdrasil: Path) -> RealmScanner:
    """Return a RealmScanner initialized with the temp Yggdrasil root."""
    return RealmScanner(base_path=temp_yggdrasil)
