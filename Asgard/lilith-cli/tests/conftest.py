"""Test configuration for lilith-cli.

Adds the package directory to sys.path so that
`from lilith_cli.main import ...` works without pip install.
"""

import sys
from pathlib import Path


# Ensure lilith_cli is importable when running tests directly
_pkg_dir = str(Path(__file__).resolve().parent.parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
