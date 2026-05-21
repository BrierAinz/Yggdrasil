"""Test configuration for persona v2."""

import sys
from pathlib import Path


# Ensure persona package is importable
_pkg_dir = str(Path(__file__).resolve().parent.parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)
