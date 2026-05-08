"""Test configuration for lilith-api.

The API lazily imports lilith_orchestrator, lilith_tools, and lilith_memory
inside endpoint handlers.  We inject lightweight stubs so that import-time
side-effects succeed without the full Lilith codebase installed.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


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
