"""Unified LLM provider wrapper for Yggdrasil CLI v6.0.

Uses httpx directly for OpenAI-compatible endpoints (fast, lightweight),
with optional litellm fallback for non-OpenAI providers (Anthropic, etc.).
Streaming, tool-calling, and exponential-backoff retry included.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import httpx


if TYPE_CHECKING:
    from .config import YggdrasilConfig


logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds
_REQUEST_TIMEOUT = 120.0  # seconds


# ── Provider factory ────────────────────────────────────────────────


def create_provider(config: YggdrasilConfig) -> LLMProviderWrapper:
    """Instantiate the appropriate :class:`LLMProviderWrapper`."""
    return LLMProviderWrapper(config)


# ── Tool-call dataclasses ───────────────────────────────────────────


class ToolCall:
    """Represents a single function-call returned by the LLM."""

    __slots__ = ("arguments", "id", "name")

    def __init__(self, id: str, name: str, arguments: dict[str, Any]) -> None:
        self.id = id
        self.name = name
        self.arguments = arguments

    def __repr__(self) -> str:
        return f"ToolCall(id={self.id!r}, name={self.name!r})"


class ToolResult:
    """Result from executing a tool call."""

    __slots__ = ("content", "name", "tool_call_id")

    def __init__(self, tool_call_id: str, name: str, content: str) -> None:
        self.tool_call_id = tool_call_id
        self.name = name
        self.content = content

    def to_openai_message(self) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": self.content,
        }


# ── Main wrapper ────────────────────────────────────────────────────


class LLMProviderWrapper:
    """High-level provider with streaming, tool-calling, and retry.

    Uses httpx directly for OpenAI-compatible endpoints (fast, no deps).
    Falls back to litellm for Anthropic/Ollama/etc. if available.
    """

    def __init__(self, config: YggdrasilConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    # ── HTTP client ─────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            api_key = self._resolve_api_key()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            self._client = httpx.AsyncClient(
                base_url=self._resolve_base_url() or "https://api.openai.com/v1",
                headers=headers,
                timeout=httpx.Timeout(_REQUEST_TIMEOUT),
            )
        return self._client

    # ── Public helpers ──────────────────────────────────────────────

    def _resolve_base_url(self) -> str | None:
        """Resolve base URL considering per-provider profile overrides."""
        profile = self.config.providers.get(self.config.provider.lower())
        if profile and profile.base_url:
            return profile.base_url
        return self.config.base_url

    def _resolve_api_key(self) -> str | None:
        """Resolve API key considering per-provider profile overrides."""
        profile = self.config.providers.get(self.config.provider.lower())
        if profile and profile.api_key:
            return profile.api_key
        return self.config.api_key

    def _resolve_model(self) -> str:
        """Return the model name considering per-provider profile overrides."""
        profile = self.config.providers.get(self.config.provider.lower())
        if profile and profile.model:
            return profile.model
        return self.config.model

    # ── Core interface: complete ─────────────────────────────────────

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send messages and return a standardised response dict.

        Retries up to 3 times with exponential back-off on transient errors.
        """
        model = model or self._resolve_model()
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await self._do_complete(model, messages, tools=tools, **kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning("Attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} retries: {last_exc}")

    # ── Core interface: stream ───────────────────────────────────────

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream text chunks from the LLM.

        Yields dicts with keys:
          content (str), finish_reason (str|None), tool_calls (list|None)
        """
        model = model or self._resolve_model()
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        if tools:
            payload["tools"] = tools

        # Accumulate tool calls across chunks.
        tc_accumulator: dict[int, dict[str, Any]] = {}

        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()

            async for raw_line in response.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    # Flush remaining tool calls.
                    if tc_accumulator:
                        tcs = list(tc_accumulator.values())
                        for tc in tcs:
                            if "arguments" in tc and isinstance(tc["arguments"], str):
                                try:
                                    tc["arguments"] = json.loads(tc["arguments"])
                                except json.JSONDecodeError:
                                    tc["arguments"] = {"raw": tc["arguments"]}
                        yield {
                            "content": "",
                            "finish_reason": "tool_calls",
                            "tool_calls": tcs,
                        }
                    return

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})

                # GLM-5.1 sends reasoning_content — yield it as a separate event
                # so the REPL can display thinking panels.
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    yield {
                        "type": "reasoning",
                        "content": reasoning,
                        "finish_reason": None,
                        "tool_calls": None,
                    }

                content = delta.get("content") or ""
                finish_reason = choice.get("finish_reason")

                # Tool calls in stream.
                delta_tcs = delta.get("tool_calls")
                if delta_tcs:
                    for tc_delta in delta_tcs:
                        idx = tc_delta.get("index", 0)
                        if idx not in tc_accumulator:
                            tc_accumulator[idx] = {
                                "id": tc_delta.get("id", ""),
                                "name": "",
                                "arguments": "",
                            }
                        if tc_delta.get("id"):
                            tc_accumulator[idx]["id"] = tc_delta["id"]
                        func = tc_delta.get("function", {})
                        if func.get("name"):
                            tc_accumulator[idx]["name"] = func["name"]
                        if func.get("arguments"):
                            tc_accumulator[idx]["arguments"] += func["arguments"]

                # When tool calls finish, flush them.
                if finish_reason == "tool_calls" or (finish_reason == "stop" and tc_accumulator):
                    tcs = list(tc_accumulator.values())
                    for tc in tcs:
                        if "arguments" in tc and isinstance(tc["arguments"], str):
                            try:
                                tc["arguments"] = json.loads(tc["arguments"])
                            except json.JSONDecodeError:
                                tc["arguments"] = {"raw": tc["arguments"]}
                    yield {
                        "content": content,
                        "finish_reason": finish_reason,
                        "tool_calls": tcs,
                    }
                    tc_accumulator.clear()
                    return

                yield {
                    "content": content,
                    "finish_reason": finish_reason,
                    "tool_calls": None,
                }

    # ── Internal: HTTP completion ────────────────────────────────────

    async def _do_complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Non-streaming completion via OpenAI-compatible API."""
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        if tools:
            payload["tools"] = tools

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        return self._normalise_response(data)

    @staticmethod
    def _normalise_response(data: dict[str, Any]) -> dict[str, Any]:
        """Normalise an OpenAI-format JSON response into our standard dict."""
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices in response: {data}")

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        # GLM-5.1: expose reasoning_content so callers can display it.
        reasoning_content = message.get("reasoning_content") or ""

        # Parse tool calls.
        tool_calls: list[ToolCall] = []
        for tc_raw in message.get("tool_calls", []):
            func = tc_raw.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}")) if func.get("arguments") else {}
            except json.JSONDecodeError:
                args = {"raw": func.get("arguments", "")}
            tool_calls.append(
                ToolCall(
                    id=tc_raw.get("id", ""),
                    name=func.get("name", ""),
                    arguments=args,
                ),
            )

        usage = data.get("usage", {})

        return {
            "content": content,
            "reasoning_content": reasoning_content,
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "finish_reason": choice.get("finish_reason", "stop"),
            "model": data.get("model", ""),
        }

    # ── Cleanup ─────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def reset_client(self) -> None:
        """Force recreation of the HTTP client on next request.
        Useful after changing provider/model at runtime.
        """
        if self._client and not self._client.is_closed:
            # Sync close is OK — httpx handles it.
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._client.aclose())  # noqa: RUF006
            except RuntimeError:
                pass
        self._client = None


# ── Tool schema conversion helpers ──────────────────────────────────


def lilith_tools_to_openai(
    tools_data: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Lilith tool descriptions to OpenAI function-calling format.

    Each *tools_data* item should have keys: ``name``, ``description``,
    ``parameters``.
    """
    openai_tools: list[dict[str, Any]] = []
    for tool in tools_data:
        params = tool.get("parameters") or {}
        properties: dict[str, Any] = {}
        required: list[str] = []

        for pname, pconfig in params.items():
            if isinstance(pconfig, dict) and pconfig.get("required"):
                required.append(pname)
            ptype = "string"
            if isinstance(pconfig, dict):
                ptype = pconfig.get("type", "string")
            properties[pname] = {
                "type": ptype,
                "description": pconfig.get("description", "") if isinstance(pconfig, dict) else "",
            }

        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            },
        )
    return openai_tools
