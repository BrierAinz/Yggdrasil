import subprocess
import sys
from pathlib import Path

YGGDRASIL_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
CLI = YGGDRASIL_ROOT / "Asgard" / "lilith-cli" / "lilith_cli" / "main.py"


def test_cli_version():
    result = subprocess.run(
        [sys.executable, str(CLI), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "2.0.0" in result.stdout
