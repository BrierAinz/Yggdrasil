"""Hermes Agent client — HTTP client for communicating with Hermes.

Supports two modes:
1. **API Server mode**: Connects to Hermes' built-in API Server gateway
   (configured via `hermes gateway run` / API Server adapter).
2. **MCP mode**: Connects to Hermes running as an MCP server
   (configured via `hermes mcp serve`).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class HermesClient:
    """Async HTTP client for the Hermes Agent API.

    Connects to Hermes' API Server adapter, which exposes an
    OpenAI-compatible /v1/chat/completions endpoint plus
    tool execution and session management.

    Parameters
    ----------
    base_url:
        Base URL of the Hermes API Server (default: http://localhost:8080).
    api_key:
        Optional API key for authentication.
    timeout:
        Request timeout in seconds (default: 120 — Hermes can be slow).
    max_retries:
        Maximum number of retry attempts for transient failures.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        """Initialise the Hermes client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Clean up the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── Health ────────────────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Check if Hermes API is reachable."""
        client = await self._get_client()
        try:
            r = await client.get("/v1/models")
            r.raise_for_status()
            return {"connected": True, "models": r.json()}
        except Exception as exc:
            logger.warning("Hermes health check failed: %s", exc)
            return {"connected": False, "error": str(exc)}

    # ── Chat (OpenAI-compatible) ──────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Send a chat completion request to Hermes.

        Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint
        that Hermes' API Server exposes.

        Parameters
        ----------
        messages:
            OpenAI-format message list.
        model:
            Model to use (falls back to Hermes' default).
        tools:
            OpenAI-format tool definitions for function calling.
        temperature:
            Sampling temperature.
        max_tokens:
            Maximum tokens to generate.
        stream:
            If True, returns the raw response for SSE streaming.
        """
        client = await self._get_client()
        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if model:
            payload["model"] = model
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if stream:
            payload["stream"] = True

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if stream:
                    # For streaming, return the response object for SSE iteration.
                    r = await client.post("/v1/chat/completions", json=payload)
                    r.raise_for_status()
                    return {"stream": True, "response": r}

                r = await client.post("/v1/chat/completions", json=payload)
                r.raise_for_status()
                return r.json()

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code < 500:
                    raise  # Client errors don't benefit from retries.
                logger.warning(
                    "Hermes chat attempt %d/%d failed: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                last_exc = exc
                logger.warning(
                    "Hermes connection error attempt %d/%d: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )

            # Exponential backoff.
            import asyncio

            await asyncio.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"Hermes chat failed after {self.max_retries} retries: {last_exc}")

    async def chat_simple(
        self,
        message: str,
        *,
        context: str | None = None,
        model: str | None = None,
    ) -> str:
        """Send a simple message to Hermes and get a text response.

        Convenience wrapper that builds the messages list from a single
        user message, optionally with a context/system prefix.

        Parameters
        ----------
        message:
            The user message to send.
        context:
            Optional system context to prepend.
        model:
            Model to use.
        """
        messages: list[dict[str, Any]] = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": message})

        result = await self.chat(messages, model=model)
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    # ── Models ──────────────────────────────────────────────────────

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from Hermes."""
        client = await self._get_client()
        try:
            r = await client.get("/v1/models")
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception:
            return []

    # ── Tool execution ──────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool on the Hermes side via chat+function_calling.

        Hermes doesn't have a direct /tools/execute endpoint, but we can
        invoke tools by sending a chat message with the tool call embedded.

        This constructs an assistant message with a tool_call and sends
        it as a conversation to get Hermes to execute the tool.
        """
        # Build a prompt that requests the tool execution.
        messages = [
            {
                "role": "user",
                "content": (
                    f"Execute the tool '{tool_name}' with these parameters: {json.dumps(params)}"
                ),
            }
        ]

        result = await self.chat(messages)
        return result

    # ── Session management (for persistent conversations) ──────────

    async def create_session(self, session_id: str | None = None) -> str:
        """Create a new conversation session on Hermes.

        Returns the session ID for future messages.
        """
        # Hermes API Server manages sessions via headers.
        # For now, we use the chat endpoint with a unique identifier.
        import uuid

        return session_id or str(uuid.uuid4())


class HermesMCPClient:
    """Client for Hermes running in MCP (Model Context Protocol) mode.

    Hermes exposes tools and resources via the MCP protocol when started
    with ``hermes mcp serve``. This client connects via stdio/HTTP and
    provides access to Hermes' full tool suite.

    Parameters
    ----------
    server_url:
        URL of the Hermes MCP HTTP server (if using HTTP transport).
    server_command:
        Command to start the Hermes MCP stdio server.
        E.g. ``["hermes", "mcp", "serve"]``
    """

    def __init__(
        self,
        server_url: str | None = None,
        server_command: list[str] | None = None,
    ) -> None:
        """Initialise the MCP bridge with server connection details."""
        self.server_url = server_url
        self.server_command = server_command or ["hermes", "mcp", "serve"]
        self._available: bool = False
        self._tools_cache: list[dict[str, Any]] | None = None

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP connection and get server info."""
        # MCP initialization would go here.
        # For now, return a placeholder.
        return {"protocol": "mcp-1.0", "status": "placeholder"}

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the Hermes MCP server."""
        if self._tools_cache is not None:
            return self._tools_cache

        # In production, this would use the MCP protocol to discover tools.
        # Placeholder: return an empty list until MCP is configured.
        self._tools_cache = []
        return self._tools_cache

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the Hermes MCP server."""
        # MCP tool call would go here.
        raise NotImplementedError(
            "MCP tool calling requires an active Hermes MCP server. Start with: hermes mcp serve"
        )
