"""Test configuration for lilith-api.

The API lazily imports lilith_orchestrator, lilith_tools, and lilith_memory
inside endpoint handlers.  We inject lightweight stubs so that import-time
side-effects succeed without the full Lilith codebase installed.

Also adds the package directory to sys.path so that
`from lilith_api.main import ...` works without pip install.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Ensure lilith_api is importable when running tests directly
_pkg_dir = str(Path(__file__).resolve().parent.parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)


def _make_stub(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# Create a mock engine that responds to .process()
_mock_engine = MagicMock()
_mock_engine.process = MagicMock(return_value={"response": "stub", "tool_call": {}, "context": []})

# Install stubs once at module load time so that lazy imports succeed.
_lilith_orchestrator = _make_stub(
    "lilith_orchestrator",
    engine=_make_stub(
        "lilith_orchestrator.engine", LilithEngine=MagicMock(return_value=_mock_engine)
    ),
)
sys.modules.setdefault("lilith_orchestrator", _lilith_orchestrator)
sys.modules.setdefault("lilith_orchestrator.engine", _lilith_orchestrator.engine)

# Stub lilith_memory.store.MemoryStore — required by _LazyState._ensure_memory()
_mock_memory = MagicMock()
_mock_memory.count_entries = MagicMock(return_value=0)
_mock_memory.search = MagicMock(return_value=[])
_mock_memory.store = MagicMock(return_value=None)

_lilith_memory = _make_stub(
    "lilith_memory",
    store=_make_stub("lilith_memory.store", MemoryStore=MagicMock(return_value=_mock_memory)),
)
sys.modules.setdefault("lilith_memory", _lilith_memory)
sys.modules.setdefault("lilith_memory.store", _lilith_memory.store)
