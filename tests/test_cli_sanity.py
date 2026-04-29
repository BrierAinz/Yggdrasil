import subprocess
import sys
from pathlib import Path

YGGDRASIL_ROOT = Path(__file__).parent.parent.resolve()
CLI = YGGDRASIL_ROOT / "yggdrasil_cli.py"


def test_cli_status_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "status"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "Yggdrasil Health Check" in result.stdout


def test_cli_tree_runs():
    result = subprocess.run(
        [sys.executable, str(CLI), "tree"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=YGGDRASIL_ROOT,
    )
    assert result.returncode == 0
    assert "Asgard/" in result.stdout
