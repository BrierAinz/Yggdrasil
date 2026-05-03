#!/usr/bin/env python3
"""Remove common Python artefacts from the Yggdrasil monorepo.

Cleans:  __pycache__ dirs, .pyc files, .pytest_cache dirs,
         .ruff_cache dirs, and *.egg-info dirs.
"""

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
]

FILE_PATTERNS = [
    "*.pyc",
    "*.egg-info",  # matches directories too
]


def clean() -> None:
    removed = 0

    # Directory patterns
    for pattern in PATTERNS:
        for p in ROOT.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
                removed += 1
                print(f"  removed {p}")

    # *.egg-info can be either dir or file glob
    for p in ROOT.rglob("*.egg-info"):
        if p.is_dir():
            shutil.rmtree(p)
            removed += 1
            print(f"  removed {p}")

    # File patterns
    for pattern in FILE_PATTERNS:
        if pattern == "*.egg-info":
            continue  # handled above
        for p in ROOT.rglob(pattern):
            if p.is_file():
                p.unlink()
                removed += 1
                print(f"  removed {p}")

    print(f"\nDone – removed {removed} items.")


if __name__ == "__main__":
    clean()
