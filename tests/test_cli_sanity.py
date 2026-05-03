import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()
CLI = YGGDRASIL_ROOT / "yggdrasil_cli.py"

# The CLI depends on cyclopts + rich, which may not be installed in CI
pytestmark = pytest.mark.skipif(
    not importlib.util.find_spec("cyclopts"),
    reason="cyclopts not installed",
)


def test_cli_status_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "status"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "YGGDRASIL" in result.stdout or "Yggdrasil" in result.stdout


def test_cli_tree_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "tree"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "Asgard" in result.stdout
