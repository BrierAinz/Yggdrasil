"""Test configuration for lilith-orchestrator.

The gateway module has heavy dependencies on the Lilith monolith
(Lilith.Core, Lilith.memory, etc.) that are not available in a
standalone test environment. We inject lightweight stub modules into
sys.modules *before* the gateway package is imported, so that
import-time side-effects succeed without the real codebase.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Build a tree of stub modules so that `from Lilith.Core.config import ...`
# and similar deep imports resolve without error.
# ---------------------------------------------------------------------------


def _make_stub(name: str, **attrs) -> types.ModuleType:
    """Create a stub module with given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _install_lilith_stubs() -> None:
    """Populate sys.modules with lightweight Lilith stubs."""
    # Root package
    sys.modules.setdefault("Lilith", _make_stub("Lilith"))
    sys.modules.setdefault("Lilith.Core", _make_stub("Lilith.Core"))
    sys.modules.setdefault("Lilith.memory", _make_stub("Lilith.memory"))
    sys.modules.setdefault("Lilith.tools", _make_stub("Lilith.tools"))
    sys.modules.setdefault("Lilith.RAG", _make_stub("Lilith.RAG"))
    sys.modules.setdefault("Lilith.Scheduler", _make_stub("Lilith.Scheduler"))
    sys.modules.setdefault("Lilith.Agents", _make_stub("Lilith.Agents"))
    sys.modules.setdefault("Lilith.Plugins", _make_stub("Lilith.Plugins"))

    # Lilith.Core.config
    sys.modules.setdefault(
        "Lilith.Core.config",
        _make_stub("Lilith.Core.config", SYSTEM_PROMPT="You are Lilith."),
    )

    # Lilith.Core.orchestrator
    sys.modules.setdefault(
        "Lilith.Core.orchestrator",
        _make_stub("Lilith.Core.orchestrator", LilithOrchestrator=MagicMock),
    )

    # Lilith.memory.enhanced
    sys.modules.setdefault(
        "Lilith.memory.enhanced",
        _make_stub("Lilith.memory.enhanced", get_memory=MagicMock()),
    )

    # Lilith.tools.files
    sys.modules.setdefault(
        "Lilith.tools.files",
        _make_stub("Lilith.tools.files", execute_tool=MagicMock(return_value={})),
    )

    # Lilith.tools.system
    sys.modules.setdefault(
        "Lilith.tools.system",
        _make_stub("Lilith.tools.system", execute_tool=MagicMock(return_value={})),
    )

    # Lilith.RAG.rag_engine (optional import — can be None)
    sys.modules.setdefault(
        "Lilith.RAG.rag_engine",
        _make_stub("Lilith.RAG.rag_engine", get_rag_engine=MagicMock()),
    )

    # Lazy imports used inside endpoints
    sys.modules.setdefault(
        "Lilith.Scheduler.task_scheduler",
        _make_stub("Lilith.Scheduler.task_scheduler", get_scheduler=MagicMock()),
    )
    sys.modules.setdefault(
        "Lilith.Agents.agent_manager",
        _make_stub("Lilith.Agents.agent_manager", get_agent_manager=MagicMock()),
    )
    sys.modules.setdefault(
        "Lilith.Plugins.plugin_manager",
        _make_stub("Lilith.Plugins.plugin_manager", get_plugin_registry=MagicMock()),
    )

    # Lilith.Core.llm_client (used inside _pregunta_rapida_sync)
    sys.modules.setdefault(
        "Lilith.Core.llm_client",
        _make_stub("Lilith.Core.llm_client", LMStudioClient=MagicMock),
    )


# Install stubs once at module load so that `import gateway.gateway` succeeds.
_install_lilith_stubs()

# Now we can safely import the gateway module.
from gateway.gateway import app


@pytest.fixture
def client() -> TestClient:
    """Return a Fresh FastAPI TestClient for the Lilith gateway."""
    return TestClient(app)
