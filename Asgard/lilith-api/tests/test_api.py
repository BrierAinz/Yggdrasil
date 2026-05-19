"""Tests for the Lilith API endpoints.

Covers health, status, chat, tools, and memory routes with
properly isolated dependency overrides.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from lilith_api.main import (
    _lock,
    _state,
    app,
    get_config,
    get_engine,
    get_memory,
    get_tools,
)


@pytest.fixture(autouse=True)
def _reset_lazy_state():
    """Reset lazy singletons between tests for isolation."""
    with _lock:
        _state.config = None
        _state.memory = None
        _state.engine = None
        _state.tools = None
    yield
    with _lock:
        _state.config = None
        _state.memory = None
        _state.engine = None
        _state.tools = None


@pytest.fixture
def client():
    """FastAPI test client with real dependency resolution."""
    return TestClient(app)


@pytest.fixture
def mock_memory():
    """Mock MemoryStore for isolated testing."""
    mem = MagicMock()
    mem.count_entries.return_value = 42
    mem.search.return_value = [
        {"content": "Hola mundo", "metadata": {"source": "test"}, "score": 0.95}
    ]
    mem.store.return_value = None
    return mem


@pytest.fixture
def mock_config():
    """Mock Config for isolated testing."""
    cfg = MagicMock()
    cfg.get.return_value = "auto"
    return cfg


@pytest.fixture
def mock_engine():
    """Mock LilithEngine for isolated testing."""
    eng = MagicMock()
    eng.process.return_value = {
        "response": "Respuesta de prueba",
        "context": [{"content": "ctx1"}],
        "tool_call": None,
    }
    eng.execute_tool.return_value = {"result": "ok"}
    return eng


@pytest.fixture
def isolated_client(mock_config, mock_memory, mock_engine):
    """Test client with all DI overrides for full isolation."""
    app.dependency_overrides[get_config] = lambda: mock_config
    app.dependency_overrides[get_memory] = lambda: mock_memory
    app.dependency_overrides[get_engine] = lambda: mock_engine
    app.dependency_overrides[get_tools] = lambda: MagicMock(
        list_tools=MagicMock(return_value={"system_info": "Sistema"})
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ── Health endpoint ──────────────────────────────────────────────────────


class TestHealth:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_has_version(self, client):
        """Health endpoint should include version field."""
        response = client.get("/health")
        assert "version" in response.json()

    def test_health_is_lightweight(self, isolated_client, mock_config):
        """Health endpoint should not trigger heavy initialization."""
        response = isolated_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model"] == "auto"


# ── Status endpoint ─────────────────────────────────────────────────────


class TestStatus:
    """Tests for GET /status."""

    def test_status_returns_details(self, isolated_client, mock_memory):
        """Status endpoint should return version, model, tools, and memory count."""
        response = isolated_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "model" in data
        assert "tools_available" in data
        assert "memory_entries" in data
        assert data["memory_entries"] == 42

    def test_status_includes_memory_count(self, isolated_client, mock_memory):
        """Status should reflect MemoryStore.count_entries()."""
        response = isolated_client.get("/status")
        assert response.json()["memory_entries"] == 42


# ── Chat endpoint ────────────────────────────────────────────────────────


class TestChat:
    """Tests for POST /chat."""

    def test_chat_basic(self, client):
        """Chat endpoint should accept a message and return a response."""
        response = client.post("/chat", json={"message": "Hola"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_with_model(self, client):
        """Chat endpoint should accept an optional model field."""
        response = client.post("/chat", json={"message": "Test", "model": "gpt-4"})
        assert response.status_code == 200

    def test_chat_returns_tool_call(self, isolated_client, mock_engine):
        """Chat response should include tool_call from engine."""
        mock_engine.process.return_value = {
            "response": "Detectado",
            "context": [{"content": "x"}],
            "tool_call": {"name": "system_info", "params": {}},
        }
        response = isolated_client.post("/chat", json={"message": "info del sistema"})
        assert response.status_code == 200
        data = response.json()
        assert data["tool_call"] is not None


# ── Tools endpoint ───────────────────────────────────────────────────────


class TestTools:
    """Tests for GET /tools and POST /tools/execute."""

    def test_list_tools(self, client):
        """GET /tools should return a dict of tool names and descriptions."""
        response = client.get("/tools")
        assert response.status_code == 200
        assert "system_info" in response.json()

    def test_execute_tool(self, isolated_client, mock_engine):
        """POST /tools/execute should delegate to engine.execute_tool."""
        response = isolated_client.post(
            "/tools/execute",
            json={"tool": "system_info", "params": {}},
        )
        assert response.status_code == 200
        mock_engine.execute_tool.assert_called_once_with("system_info", {})


# ── Memory endpoints ────────────────────────────────────────────────────


class TestMemoryRecall:
    """Tests for GET /memory."""

    def test_memory_recall_requires_query(self, isolated_client):
        """GET /memory should require query parameter."""
        response = isolated_client.get("/memory")
        assert response.status_code == 422  # Missing required param

    def test_memory_recall_with_query(self, isolated_client, mock_memory):
        """GET /memory?query=... should return search results."""
        response = isolated_client.get("/memory?query=test&k=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        mock_memory.search.assert_called_once_with("test", k=3)


class TestMemoryStore:
    """Tests for POST /memory."""

    def test_memory_store_basic(self, isolated_client, mock_memory):
        """POST /memory should store text and return confirmation."""
        response = isolated_client.post(
            "/memory",
            json={"text": "Recuerdo importante"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stored"
        assert "Recuerdo importante" in data["text"]

    def test_memory_store_with_metadata(self, isolated_client, mock_memory):
        """POST /memory should accept optional metadata."""
        response = isolated_client.post(
            "/memory",
            json={"text": "Nota", "metadata": {"source": "test", "priority": "high"}},
        )
        assert response.status_code == 200
        mock_memory.store.assert_called_once_with("Nota", {"source": "test", "priority": "high"})

    def test_memory_store_truncates_text(self, isolated_client, mock_memory):
        """POST /memory response should truncate text to 100 chars."""
        long_text = "x" * 200
        response = isolated_client.post(
            "/memory",
            json={"text": long_text},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["text"]) <= 100
