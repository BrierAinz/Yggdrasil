"""Tests for the Lilith Bridge package."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lilith_bridge.config import BridgeConfig
from lilith_bridge.models import (
    BridgeChatRequest,
    BridgeChatResponse,
    BridgeHealth,
    BridgeMemoryQuery,
    BridgeMemoryStore,
    BridgeSkillSearch,
    HermesChatRequest,
    HermesChatResponse,
    HermesToolExecute,
    HermesToolResult,
)


# ── Model tests ───────────────────────────────────────────────────────


class TestBridgeModels:
    """Test Pydantic models for the bridge API."""

    def test_bridge_chat_request_defaults(self):
        req = BridgeChatRequest(message="hello")
        assert req.message == "hello"
        assert req.session_id is None
        assert req.stream is False
        assert req.metadata == {}

    def test_bridge_chat_request_full(self):
        req = BridgeChatRequest(
            message="test",
            session_id="abc-123",
            stream=True,
            metadata={"key": "value"},
        )
        assert req.session_id == "abc-123"
        assert req.stream is True

    def test_bridge_chat_response(self):
        resp = BridgeChatResponse(
            response="hi",
            session_id="sess-1",
            latency_ms=42.5,
            tools_used=["search"],
            usage={"tokens": 100},
        )
        assert resp.response == "hi"
        assert resp.latency_ms == 42.5
        assert len(resp.tools_used) == 1

    def test_bridge_memory_query(self):
        q = BridgeMemoryQuery(query="lilith", k=10)
        assert q.k == 10

    def test_bridge_memory_store(self):
        s = BridgeMemoryStore(text="remember this", metadata={"tag": "test"})
        assert s.text == "remember this"
        assert s.metadata["tag"] == "test"

    def test_bridge_skill_search(self):
        s = BridgeSkillSearch(query="comfyui", category="mlops", limit=5)
        assert s.category == "mlops"
        assert s.limit == 5

    def test_hermes_chat_request(self):
        req = HermesChatRequest(
            message="solve this",
            context="You are an expert",
            toolsets=["terminal", "web"],
        )
        assert req.context == "You are an expert"
        assert req.toolsets == ["terminal", "web"]

    def test_hermes_tool_execute(self):
        req = HermesToolExecute(
            tool="web_search",
            params={"query": "test"},
        )
        assert req.tool == "web_search"
        assert req.params["query"] == "test"

    def test_hermes_tool_result_success(self):
        result = HermesToolResult(
            tool="web_search",
            success=True,
            result="found it",
        )
        assert result.success is True
        assert result.error is None

    def test_hermes_tool_result_failure(self):
        result = HermesToolResult(
            tool="web_search",
            success=False,
            error="timeout",
        )
        assert result.success is False
        assert result.result is None

    def test_bridge_health_defaults(self):
        h = BridgeHealth()
        assert h.status == "healthy"
        assert h.bridge_version == "1.0.0"
        assert h.lilith_engine is False
        assert h.hermes_connected is False
        assert h.skills_loaded == 0


# ── Config tests ──────────────────────────────────────────────────────


class TestBridgeConfig:
    """Test BridgeConfig model."""

    def test_defaults(self):
        config = BridgeConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 9001
        assert config.hermes_url == "http://localhost:8080"
        assert config.hermes_timeout == 120.0
        assert config.hermes_max_retries == 3
        assert config.enable_streaming is True

    def test_custom_config(self):
        config = BridgeConfig(
            host="127.0.0.1",
            port=8080,
            hermes_url="http://hermes.local:9000",
            auth_token="secret-token",
        )
        assert config.port == 8080
        assert config.auth_token == "secret-token"

    def test_resolve_skills_dir_explicit(self):
        config = BridgeConfig(lilith_skills_dir="/tmp/skills")
        result = config.resolve_skills_dir()
        assert str(result) == "/tmp/skills"

    def test_resolve_memory_db(self):
        config = BridgeConfig(lilith_memory_db="~/.yggdrasil/test.db")
        result = config.resolve_memory_db()
        # Should have expanded ~
        assert "~" not in str(result)

    def test_load_bridge_config_missing_file(self, tmp_path):
        from lilith_bridge.config import load_bridge_config

        config = load_bridge_config(str(tmp_path / "nonexistent.yaml"))
        # Should return defaults when file doesn't exist
        assert config.port == 9001


# ── Hermes client tests ───────────────────────────────────────────────


class TestHermesClient:
    """Test HermesClient HTTP communication."""

    def test_client_init(self):
        from lilith_bridge.hermes_client import HermesClient

        client = HermesClient(
            base_url="http://localhost:8080",
            api_key="test-key",
            timeout=30.0,
            max_retries=5,
        )
        assert client.base_url == "http://localhost:8080"
        assert client.api_key == "test-key"
        assert client.timeout == 30.0
        assert client.max_retries == 5

    def test_client_default_url(self):
        from lilith_bridge.hermes_client import HermesClient

        client = HermesClient()
        assert client.base_url == "http://localhost:8080"
        assert client.api_key is None

    @pytest.mark.asyncio
    async def test_client_close(self):
        from lilith_bridge.hermes_client import HermesClient

        client = HermesClient()
        # No client created yet, should be safe to close.
        await client.close()
        assert client._client is None


class TestHermesMCPClient:
    """Test HermesMCPClient placeholder."""

    def test_mcp_init(self):
        from lilith_bridge.hermes_client import HermesMCPClient

        client = HermesMCPClient(
            server_url="http://localhost:3000",
        )
        assert client.server_url == "http://localhost:3000"
        assert client.server_command == ["hermes", "mcp", "serve"]

    def test_mcp_custom_command(self):
        from lilith_bridge.hermes_client import HermesMCPClient

        client = HermesMCPClient(
            server_command=["python", "-m", "hermes_agent"],
        )
        assert client.server_command == ["python", "-m", "hermes_agent"]

    @pytest.mark.asyncio
    async def test_mcp_initialize_placeholder(self):
        from lilith_bridge.hermes_client import HermesMCPClient

        client = HermesMCPClient()
        result = await client.initialize()
        assert result["protocol"] == "mcp-1.0"
        assert result["status"] == "placeholder"

    @pytest.mark.asyncio
    async def test_mcp_call_tool_not_implemented(self):
        from lilith_bridge.hermes_client import HermesMCPClient

        client = HermesMCPClient()
        with pytest.raises(NotImplementedError, match="MCP tool calling"):
            await client.call_tool("test", {})


# ── FastAPI app tests ─────────────────────────────────────────────────


class TestBridgeApp:
    """Test the FastAPI application factory and endpoints."""

    @pytest.fixture
    def app_client(self):
        """Create a test client with no auth token."""
        from httpx import ASGITransport, AsyncClient

        from lilith_bridge.app import create_app

        config = BridgeConfig(auth_token=None)  # No auth for testing
        app = create_app(config)

        return app

    def test_create_app_no_auth(self):
        from lilith_bridge.app import create_app

        config = BridgeConfig(auth_token=None)
        app = create_app(config)
        assert app.title == "Hermes Bridge"

    def test_create_app_with_auth(self):
        from lilith_bridge.app import create_app

        config = BridgeConfig(auth_token="test-secret")
        app = create_app(config)
        assert app.title == "Hermes Bridge"

    def test_app_routes_registered(self):
        from lilith_bridge.app import create_app

        config = BridgeConfig(auth_token=None)
        app = create_app(config)

        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/bridge/health" in route_paths
        assert "/api/bridge/chat" in route_paths
        assert "/api/bridge/memory" in route_paths
        assert "/api/bridge/skills" in route_paths
        assert "/api/bridge/hermes/chat" in route_paths
        assert "/api/bridge/hermes/models" in route_paths
        assert "/api/bridge/hermes/execute" in route_paths
        assert "/api/bridge/hermes/health" in route_paths


# ── Bifrost integration tests ─────────────────────────────────────────


class TestBifrostIntegration:
    """Test the BifrostGateway integration router."""

    def test_create_bridge_router(self):
        from lilith_bridge.bifrost_integration import create_bridge_router

        config = BridgeConfig(auth_token=None)
        mock_engine = MagicMock()
        mock_memory = MagicMock()

        router = create_bridge_router(
            config=config,
            engine=mock_engine,
            memory=mock_memory,
        )

        # Verify all expected routes are registered (with prefix).
        route_paths = [r.path for r in router.routes]
        assert "/bridge/health" in route_paths
        assert "/bridge/chat" in route_paths
        assert "/bridge/memory" in route_paths
        assert "/bridge/skills" in route_paths
        assert "/bridge/skills/search" in route_paths
        assert "/bridge/hermes/chat" in route_paths
        assert "/bridge/hermes/models" in route_paths
        assert "/bridge/hermes/execute" in route_paths
        assert "/bridge/hermes/health" in route_paths

    def test_router_prefix(self):
        from lilith_bridge.bifrost_integration import create_bridge_router

        config = BridgeConfig(auth_token=None)
        router = create_bridge_router(config=config, engine=None, memory=None)
        assert router.prefix == "/bridge"


# ── Config loading tests ──────────────────────────────────────────────


class TestConfigLoading:
    """Test YAML config loading and env interpolation."""

    def test_load_from_yaml(self, tmp_path):
        from lilith_bridge.config import load_bridge_config

        yaml_content = """
bridge:
  host: "0.0.0.0"
  port: 9001
  hermes_url: "http://hermes.local:8080"
  auth_token: "my-secret"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        config = load_bridge_config(str(config_file))
        assert config.port == 9001
        assert config.hermes_url == "http://hermes.local:8080"
        assert config.auth_token == "my-secret"

    def test_load_missing_file_returns_defaults(self):
        from lilith_bridge.config import load_bridge_config

        config = load_bridge_config("/nonexistent/path/config.yaml")
        assert config.port == 9001  # Default

    def test_env_interpolation(self, tmp_path, monkeypatch):
        from lilith_bridge.config import load_bridge_config

        monkeypatch.setenv("HERMES_TEST_KEY", "sk-test-123")

        yaml_content = """
bridge:
  hermes_api_key: "${HERMES_TEST_KEY}"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        config = load_bridge_config(str(config_file))
        assert config.hermes_api_key == "sk-test-123"

    def test_cors_defaults(self):
        config = BridgeConfig()
        assert "http://localhost" in config.cors_origins
        assert len(config.cors_origins) == 5