"""Test configuration for lilith-api.

The API lazily imports lilith_orchestrator, lilith_tools, and lilith_memory
inside endpoint handlers.  We inject lightweight stubs so that import-time
side-effects succeed without the full Lilith codebase installed.

Also adds the package directory to sys.path so that
``from lilith_api.main import ...`` works without pip install.

IMPORTANT: Stubs are installed via an ``autouse`` fixture that saves and
restores ``sys.modules`` — this prevents the mocks from leaking into other
packages' test sessions (e.g. lilith-memory's real tests).
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


# ── Stub definitions (installed only during lilith-api tests) ──────────

# Create a mock engine that responds to .process()
_mock_engine = MagicMock()
_mock_engine.process = MagicMock(return_value={"response": "stub", "tool_call": {}, "context": []})

_LILITH_ORCHESTRATOR_STUBS = {
    "lilith_orchestrator": _make_stub(
        "lilith_orchestrator",
        engine=_make_stub(
            "lilith_orchestrator.engine",
            LilithEngine=MagicMock(return_value=_mock_engine),
        ),
    ),
    "lilith_orchestrator.engine": None,  # set after orchestrator above
}

# Stub lilith_memory.store.MemoryStore — required by _LazyState._ensure_memory()
_mock_memory = MagicMock()
_mock_memory.count_entries = MagicMock(return_value=0)
_mock_memory.search = MagicMock(return_value=[])
_mock_memory.store = MagicMock(return_value=None)

_LILITH_MEMORY_STUBS = {
    "lilith_memory": _make_stub(
        "lilith_memory",
        store=_make_stub("lilith_memory.store", MemoryStore=MagicMock(return_value=_mock_memory)),
        backends=_make_stub(
            "lilith_memory.backends",
            MemoryBackend=MagicMock(),
            SQLiteBackend=MagicMock(),
            Mem0Backend=MagicMock(),
        ),
    ),
    "lilith_memory.store": None,  # set after memory above
    "lilith_memory.backends": None,
    "lilith_memory.backends.base": None,
    "lilith_memory.backends.sqlite_backend": None,
    "lilith_memory.backends.mem0_backend": None,
}

# Fill in cross-references
_LILITH_ORCHESTRATOR_STUBS["lilith_orchestrator.engine"] = _LILITH_ORCHESTRATOR_STUBS[
    "lilith_orchestrator"
].engine
_LILITH_MEMORY_STUBS["lilith_memory.store"] = _LILITH_MEMORY_STUBS["lilith_memory"].store
_LILITH_MEMORY_STUBS["lilith_memory.backends"] = _LILITH_MEMORY_STUBS["lilith_memory"].backends
_LILITH_MEMORY_STUBS["lilith_memory.backends.base"] = _LILITH_MEMORY_STUBS["lilith_memory"].backends
_LILITH_MEMORY_STUBS["lilith_memory.backends.sqlite_backend"] = _LILITH_MEMORY_STUBS[
    "lilith_memory"
].backends
_LILITH_MEMORY_STUBS["lilith_memory.backends.mem0_backend"] = _LILITH_MEMORY_STUBS[
    "lilith_memory"
].backends

_ALL_STUBS = {**_LILITH_ORCHESTRATOR_STUBS, **_LILITH_MEMORY_STUBS}


@pytest.fixture(autouse=True)
def _isolate_lilith_stubs():
    """Install mock stubs for lilith-api's lazy imports, then remove them.

    Using ``sys.modules.setdefault`` at module level poisons other packages'
    test sessions (e.g. lilith-memory's real tests get MagicMock instead of
    the real SQLiteBackend).  An autouse fixture with save/restore ensures
    stubs only exist during lilith-api test collection/execution.
    """
    # Modules that already exist in sys.modules — we should not overwrite them
    saved = {}
    for key, stub in _ALL_STUBS.items():
        if key in sys.modules:
            saved[key] = sys.modules[key]
        else:
            # Mark that this key was not previously in sys.modules
            saved[key] = _NOT_IN_MODULES

        # Only install stub if the real module is NOT already loaded
        if key not in sys.modules:
            sys.modules[key] = stub

    yield

    # Restore: remove stubs that we added, put back originals
    for key, original in saved.items():
        if original is _NOT_IN_MODULES:
            # We added this — remove it unless a real module replaced it
            if key in sys.modules and sys.modules[key] is _ALL_STUBS.get(key):
                del sys.modules[key]
        else:
            # Restore original module
            sys.modules[key] = original


# Sentinel to track "was not in sys.modules before us"
_NOT_IN_MODULES = object()
