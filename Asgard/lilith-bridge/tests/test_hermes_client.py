"""Tests for the HermesClient HTTP communication layer.

Covers: retry logic, chat_simple, health/health failure,
list_models fallback, execute_tool, session creation, and
MCP client placeholder behaviors.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from lilith_bridge.hermes_client import HermesClient, HermesMCPClient


# ── HermesClient init ──────────────────────────────────────────────────


class TestHermesClientInit:
    """Test HermesClient initialization."""

    def test_default_init(self):
        client = HermesClient()
        assert client.base_url == "http://localhost:8080"
        assert client.api_key is None
        assert client.timeout == 120.0
        assert client.max_retries == 3
        assert client._client is None

    def test_custom_init(self):
        client = HermesClient(
            base_url="http://hermes.local:9000",
            api_key="sk-test",
            timeout=30.0,
            max_retries=5,
        )
        assert client.base_url == "http://hermes.local:9000"
        assert client.api_key == "sk-test"
        assert client.timeout == 30.0
        assert client.max_retries == 5

    def test_base_url_trailing_slash_stripped(self):
        client = HermesClient(base_url="http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"


# ── HermesClient close ────────────────────────────────────────────────


class TestHermesClientClose:
    """Test HermesClient cleanup."""

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        client = HermesClient()
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_active_client(self):
        client = HermesClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Trigger client creation via health()
            await client.health()
            assert client._client is not None
            assert not client._client.is_closed

            # Now close it
            await client.close()
            assert client._client is None


# ── HermesClient _get_client ────────────────────────────────────────────


class TestHermesClientGetClient:
    """Test lazy HTTP client creation."""

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self):
        client = HermesClient()
        http_client = await client._get_client()
        assert isinstance(http_client, httpx.AsyncClient)
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        client = HermesClient()
        c1 = await client._get_client()
        c2 = await client._get_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_get_client_with_api_key(self):
        client = HermesClient(api_key="test-key")
        http_client = await client._get_client()
        assert "Authorization" in http_client.headers
        assert http_client.headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_get_client_no_api_key(self):
        client = HermesClient()
        http_client = await client._get_client()
        assert "Authorization" not in http_client.headers


# ── HermesClient health ────────────────────────────────────────────────


class TestHermesClientHealth:
    """Test HermesClient health check."""

    @pytest.mark.asyncio
    async def test_health_success(self):
        client = HermesClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "model-1"}]}
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.health()
            assert result["connected"] is True
            assert "models" in result

    @pytest.mark.asyncio
    async def test_health_failure(self):
        client = HermesClient()
        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await client.health()
            assert result["connected"] is False
            assert "error" in result


# ── HermesClient chat ──────────────────────────────────────────────────


class TestHermesClientChat:
    """Test HermesClient chat completion."""

    @pytest.mark.asyncio
    async def test_chat_basic(self):
        client = HermesClient()
        expected = {
            "choices": [{"message": {"content": "Hello!"}}],
            "model": "test-model",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat([{"role": "user", "content": "hi"}])
            assert result["choices"][0]["message"]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_chat_with_params(self):
        client = HermesClient()
        expected = {"choices": [{"message": {"content": "response"}}]}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat(
                [{"role": "user", "content": "test"}],
                model="gpt-4",
                temperature=0.5,
                max_tokens=100,
            )
            assert result["choices"][0]["message"]["content"] == "response"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        client = HermesClient()
        expected = {"choices": [{"message": {"content": "used tool"}}]}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        tools = [{"type": "function", "function": {"name": "search"}}]

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat(
                [{"role": "user", "content": "search"}],
                tools=tools,
            )
            assert result["choices"][0]["message"]["content"] == "used tool"

    @pytest.mark.asyncio
    async def test_chat_stream(self):
        client = HermesClient()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat(
                [{"role": "user", "content": "stream me"}],
                stream=True,
            )
            assert result["stream"] is True
            assert "response" in result

    @pytest.mark.asyncio
    async def test_chat_client_error_no_retry(self):
        """Client errors (4xx) should NOT be retried."""
        client = HermesClient(max_retries=3)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response,
        )

        with (
            patch.object(
                httpx.AsyncClient,
                "post",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await client.chat([{"role": "user", "content": "bad"}])


# ── HermesClient chat_simple ─────────────────────────────────────────────


class TestHermesClientChatSimple:
    """Test HermesClient chat_simple convenience wrapper."""

    @pytest.mark.asyncio
    async def test_chat_simple_with_context(self):
        client = HermesClient()
        expected = {
            "choices": [{"message": {"content": "Norse response"}}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat_simple(
                "Tell me about Yggdrasil",
                context="You are a Norse mythology expert",
            )
            assert result == "Norse response"

    @pytest.mark.asyncio
    async def test_chat_simple_no_context(self):
        client = HermesClient()
        expected = {
            "choices": [{"message": {"content": "Hello back"}}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat_simple("hi")
            assert result == "Hello back"

    @pytest.mark.asyncio
    async def test_chat_simple_empty_choices(self):
        client = HermesClient()
        expected = {"choices": []}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.chat_simple("hi")
            assert result == ""


# ── HermesClient list_models ─────────────────────────────────────────────


class TestHermesClientListModels:
    """Test HermesClient list_models."""

    @pytest.mark.asyncio
    async def test_list_models_success(self):
        client = HermesClient()
        models_data = [
            {"id": "gpt-4", "object": "model"},
            {"id": "llama3", "object": "model"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": models_data}
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.list_models()
            assert len(result) == 2
            assert result[0]["id"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_list_models_failure_returns_empty(self):
        client = HermesClient()
        with patch.object(
            httpx.AsyncClient,
            "get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Offline"),
        ):
            result = await client.list_models()
            assert result == []


# ── HermesClient execute_tool ────────────────────────────────────────────


class TestHermesClientExecuteTool:
    """Test HermesClient execute_tool."""

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        client = HermesClient()
        expected = {"choices": [{"message": {"content": "tool result"}}]}
        mock_response = MagicMock()
        mock_response.json.return_value = expected
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.execute_tool("web_search", {"query": "Yggdrasil"})
            assert result["choices"][0]["message"]["content"] == "tool result"


# ── HermesClient create_session ──────────────────────────────────────────


class TestHermesClientCreateSession:
    """Test HermesClient create_session."""

    @pytest.mark.asyncio
    async def test_create_session_with_id(self):
        client = HermesClient()
        session_id = await client.create_session("my-session-123")
        assert session_id == "my-session-123"

    @pytest.mark.asyncio
    async def test_create_session_auto_id(self):
        client = HermesClient()
        session_id = await client.create_session()
        assert session_id is not None
        assert len(session_id) > 0  # UUID format


# ── HermesMCPClient ────────────────────────────────────────────────────


class TestHermesMCPClientExtended:
    """Extended tests for HermesMCPClient."""

    def test_mcp_default_url(self):
        client = HermesMCPClient()
        assert client.server_url is None
        assert client.server_command == ["hermes", "mcp", "serve"]

    def test_mcp_custom_url(self):
        client = HermesMCPClient(server_url="http://localhost:3000")
        assert client.server_url == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_mcp_list_tools_cache(self):
        client = HermesMCPClient()
        # First call populates cache
        result1 = await client.list_tools()
        assert result1 == []

        # Second call returns cached value
        result2 = await client.list_tools()
        assert result2 is result1  # Same object (cached)
