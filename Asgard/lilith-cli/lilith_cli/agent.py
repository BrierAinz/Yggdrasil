"""Core agent orchestrator for Yggdrasil CLI v6.0.

The ``AgentSession`` holds all runtime state (config, provider, tools,
memory, history) and implements the main message-processing loop with
tool-call resolution.
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .config import YggdrasilConfig, load_config
from .providers import (
    LLMProviderWrapper,
    ToolCall,
    ToolResult,
    create_provider,
    lilith_tools_to_openai,
)


logger = logging.getLogger(__name__)

# ── Conversation history message ─────────────────────────────────────


class Message(dict):
    """A single conversation message, stored as an OpenAI-compatible dict."""

    @staticmethod
    def user(text: str) -> dict[str, Any]:
        return {"role": "user", "content": text}

    @staticmethod
    def assistant(text: str, tool_calls: list[ToolCall] | None = None) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": "assistant", "content": text}
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments)
                        if isinstance(tc.arguments, dict)
                        else tc.arguments,
                    },
                }
                for tc in tool_calls
            ]
        return msg

    @staticmethod
    def tool_result(tc: ToolResult) -> dict[str, Any]:
        return tc.to_openai_message()

    @staticmethod
    def system(text: str) -> dict[str, Any]:
        return {"role": "system", "content": text}


# ── AgentSession ────────────────────────────────────────────────────


class AgentSession:
    """Holds all runtime state and drives the conversation loop.

    Parameters
    ----------
    config:
        The loaded :class:`YggdrasilConfig`.
    provider:
        The LLM provider wrapper.  If ``None`` one is created from *config*.
    """

    def __init__(
        self,
        config: YggdrasilConfig,
        provider: LLMProviderWrapper | None = None,
    ):
        self.config = config
        self.provider = provider or create_provider(config)
        self.history: list[dict[str, Any]] = []
        self.system_prompt = config.system_prompt
        self._tools_enabled = True
        self._total_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        self._last_user_message: str = ""  # For /redo support.

        # Memory store (lazy-init).
        self._memory: Any = None
        if config.memory.enabled:
            self._init_memory()

        # Tool registry (lazy-init).
        self._tool_registry: Any = None
        self._tools_cache: list[dict[str, Any]] | None = None

    # ── Memory ──────────────────────────────────────────────────────

    def _init_memory(self) -> None:
        """Initialise the memory store if *lilith_memory* is available."""
        try:
            from pathlib import Path

            from lilith_memory.store import MemoryStore

            db_path = Path(self.config.memory.db_path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._memory = MemoryStore(db_path)
            logger.info("Memoria inicializada: %s", db_path)
        except ImportError:
            logger.warning("lilith_memory no disponible — memoria deshabilitada")
            self._memory = None

    @property
    def memory(self) -> Any:
        return self._memory

    # ── Tools ───────────────────────────────────────────────────────

    def _init_tools(self) -> None:
        """Load tools from *lilith_tools* based on config flags."""
        try:
            # Force registration of all tool classes.
            from lilith_tools import ToolRegistry, filesystem, system  # noqa: F401

            with contextlib.suppress(ImportError):
                from lilith_tools import browser, coding, web_search  # noqa: F401

            self._tool_registry = ToolRegistry
        except ImportError:
            logger.warning("lilith_tools no disponible — herramientas deshabilitadas")
            self._tool_registry = None

    def get_tool_descriptions(self) -> list[dict[str, Any]]:
        """Return a list of tool description dicts (name, description,
        parameters) for currently enabled tools.
        """
        if self._tools_cache is not None:
            return self._tools_cache

        self._init_tools()
        if self._tool_registry is None:
            self._tools_cache = []
            return self._tools_cache

        tools: list[dict[str, Any]] = []
        all_tools = self._tool_registry.list_tools()

        # Map tool categories to their tool names.
        category_map: dict[str, list[str]] = {
            "filesystem": ["file_read", "directory_list"],
            "coding": ["coding"],
            "web_search": ["web_search"],
            "browser": ["browser"],
            "system": ["system"],
        }

        for name, description in all_tools.items():
            # Check if this tool's category is enabled.
            enabled = True
            for category, names in category_map.items():
                if name in names:
                    enabled = getattr(self.config.tools, category, True)
                    break

            if not enabled:
                continue

            tool_cls = self._tool_registry.get(name)
            params = tool_cls.parameters if tool_cls else {}
            tools.append(
                {
                    "name": name,
                    "description": description,
                    "parameters": params,
                }
            )

        self._tools_cache = tools
        return self._tools_cache

    def get_openai_tools(self) -> list[dict[str, Any]]:
        """Return tools in OpenAI function-calling format."""
        return lilith_tools_to_openai(self.get_tool_descriptions())

    def _repair_tool_name(self, concatenated_name: str) -> list[str]:
        """Try to split a concatenated tool name into valid tool names.

        Some models (e.g. GLM-5.1) concatenate multiple tool names into one,
        e.g. ``system_infodirectory_list`` → [``system_info``, ``directory_list``].
        This method tries all possible splits and returns the one where every
        segment matches a known tool name.
        """
        known = set(self._tool_registry.list_tools().keys()) if self._tool_registry else set()
        if not known:
            return [concatenated_name]

        # Try every possible left-prefix that is a valid tool name,
        # then recursively split the remainder.
        def _split(name: str) -> list[list[str]]:
            results: list[list[str]] = []
            for tool in known:
                if name.startswith(tool):
                    remainder = name[len(tool) :]
                    if not remainder:
                        results.append([tool])
                    else:
                        for sub in _split(remainder):
                            results.append([tool, *sub])
            return results

        splits = _split(concatenated_name)
        if splits:
            # Prefer the split with the fewest segments (most specific match).
            splits.sort(key=len)
            return splits[0]
        return [concatenated_name]

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call and return the result."""
        self._init_tools()

        tool_name = tool_call.name
        tool_args = tool_call.arguments

        if self._tool_registry is None:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                content="Error: herramientas no disponibles (lilith_tools no instalado)",
            )

        tool_cls = self._tool_registry.get(tool_name)

        # If tool name not found, try to repair concatenated names.
        if tool_cls is None:
            repaired = self._repair_tool_name(tool_name)
            if len(repaired) > 1 and all(self._tool_registry.get(n) for n in repaired):
                logger.info(
                    "Repaired concatenated tool name: %s → %s",
                    tool_name,
                    repaired,
                )
                # Return a hint so the caller can re-dispatch.
                return ToolResult(
                    tool_call_id=tool_call.id,
                    name=tool_name,
                    content=(
                        f"Error: tool '{tool_name}' was a concatenation of "
                        f"{repaired}. Please call each tool separately: " + ", ".join(repaired)
                    ),
                )

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                content=f"Error: herramienta desconocida '{tool_name}'",
            )

        try:
            tool_instance = tool_cls()
            result = tool_instance.execute(**tool_args)
            if result.success:
                content = (
                    json.dumps(result.data, ensure_ascii=False, default=str)
                    if not isinstance(result.data, str)
                    else result.data
                )
            else:
                content = f"Error: {result.error}"
        except Exception as exc:
            content = f"Error ejecutando {tool_name}: {exc}"
            logger.exception("Tool execution error: %s", tool_name)

        return ToolResult(tool_call_id=tool_call.id, name=tool_name, content=content)

    # ── History management ──────────────────────────────────────────

    def clear_history(self) -> None:
        """Reset conversation history (excluding system prompt)."""
        self.history.clear()
        self._total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def compact_history(self, summary: str, keep_recent: int = 2) -> None:
        """Replace conversation history with a summary + recent messages.

        This is called by /compact to reduce token usage while preserving
        context. The summary replaces older messages, and the last
        ``keep_recent`` exchanges (user+assistant pairs) are kept verbatim.

        Parameters
        ----------
        summary:
            A compressed summary of the conversation so far.
        keep_recent:
            Number of recent user+assistant *pairs* to keep (default 2).
        """
        # Calculate how many messages to keep from the end.
        # Each "pair" is typically 2 messages (user + assistant),
        # but tool calls can add tool_result messages, so we scan
        # backwards counting user messages.
        keep_count = 0
        pairs_found = 0
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].get("role") == "user":
                pairs_found += 1
                if pairs_found > keep_recent:
                    break
            keep_count += 1

        recent_messages = self.history[-keep_count:] if keep_count > 0 else []

        # Build the compacted history: assistant summary as context + recent messages.
        self.history = [
            {"role": "assistant", "content": f"[Resumen de la conversación anterior]\n{summary}"},
            *recent_messages,
        ]

        logger.info(
            "Historial compactado: %d mensajes → %d (1 resumen + %d recientes)",
            len(self.history) + keep_count,
            len(self.history),
            len(recent_messages),
        )

    async def generate_compact_summary(self) -> str:
        """Ask the LLM to summarize the current conversation history.

        Returns a concise summary suitable for replacing older messages
        in the history, freeing up context tokens.
        """
        if not self.history:
            return ""

        # Build a text representation of the conversation.
        lines = []
        for msg in self.history:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if role == "system":
                continue  # Skip system prompts — they're in every request anyway.
            # Truncate very long messages to keep the summary request manageable.
            if len(content) > 500:
                content = content[:500] + "…[truncado]"
            lines.append(f"{role.upper()}: {content}")

        conversation_text = "\n".join(lines)

        summary_prompt = (
            "Resume la siguiente conversación de forma concisa y completa. "
            "Incluye: decisiones tomadas, archivos modificados, comandos ejecutados, "
            "resultados clave, y cualquier contexto importante que pueda necesitarse "
            "para continuar la conversación. Sé específico con nombres de archivos, "
            "rutas, y valores. No incluyas saludos ni detalles irrelevantes. "
            "Responde en español.\n\n"
            f"CONVERSACIÓN:\n{conversation_text}\n\n"
            "RESUMEN:"
        )

        # Use a temporary session — don't add to history.
        temp_messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente que resume conversaciones de forma concisa y precisa."
                ),
            },
            {"role": "user", "content": summary_prompt},
        ]

        response = await self.provider.complete(temp_messages, tools=None)
        return response.get("content", "").strip()

    def _build_messages(self) -> list[dict[str, Any]]:
        """Build the full message list to send to the LLM."""
        messages: list[dict[str, Any]] = [Message.system(self.system_prompt)]

        # Add tool descriptions into the system prompt.
        tools_desc = self.get_tool_descriptions()
        if tools_desc and self._tools_enabled:
            tool_lines = "\n".join(f"- {t['name']}: {t['description']}" for t in tools_desc)
            messages[0]["content"] += (
                f"\n\nYou have access to the following tools:\n{tool_lines}\n\n"
                "IMPORTANT: Call each tool by its EXACT name shown above. "
                "Do NOT combine or concatenate multiple tool names into one call. "
                "If you need multiple tools, call them one at a time — "
                "wait for each result before calling the next. "
                "When you have enough information to answer directly, do so."
            )

        # Trim history to max_turns.
        max_turns = self.config.history.max_turns
        history = self.history[-max_turns * 2 :]  # user+assistant = 2 messages per turn

        messages.extend(history)
        return messages

    # ── Main processing loop ────────────────────────────────────────

    async def process_message(self, text: str) -> str:
        """Process a user message through the full loop:

        1. Add user message to history
        2. Send to LLM
        3. If LLM returns tool_calls, execute them and loop
        4. Return final assistant text

        Returns the final text response from the assistant.
        """
        self.history.append(Message.user(text))
        self._last_user_message = text

        messages = self._build_messages()
        tools = (
            self.get_openai_tools()
            if self._tools_enabled and self.get_tool_descriptions()
            else None
        )

        # Tool-calling loop.
        max_iterations = 10  # safety limit
        for _ in range(max_iterations):
            response = await self.provider.complete(messages, tools=tools)

            # Track usage.
            usage = response.get("usage", {})
            self._total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            self._total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            self._total_usage["total_tokens"] += usage.get("total_tokens", 0)

            content = response.get("content", "")
            tool_calls: list[ToolCall] = response.get("tool_calls", [])

            if not tool_calls:
                # No more tool calls — we're done.
                self.history.append(Message.assistant(content))
                return content

            # Auto-repair concatenated tool names (some models merge names).
            self._init_tools()
            repaired_tool_calls: list[ToolCall] = []
            for tc in tool_calls:
                if self._tool_registry and self._tool_registry.get(tc.name) is None:
                    repaired = self._repair_tool_name(tc.name)
                    if len(repaired) > 1 and all(self._tool_registry.get(n) for n in repaired):
                        logger.info(
                            "Non-stream: repaired concatenated tool name: %s → %s",
                            tc.name,
                            repaired,
                        )
                        for i, name in enumerate(repaired):
                            call_args = tc.arguments if i == 0 else {}
                            repaired_tool_calls.append(
                                ToolCall(
                                    id=f"{tc.id}_{i}" if tc.id else f"repair_{i}",
                                    name=name,
                                    arguments=call_args,
                                )
                            )
                        continue
                repaired_tool_calls.append(tc)
            tool_calls = repaired_tool_calls

            # There are tool calls — execute each one.
            # First, add the assistant message (with tool_calls) to history.
            self.history.append(Message.assistant(content, tool_calls=tool_calls))

            # Execute tools.
            for tc in tool_calls:
                result = await self.execute_tool(tc)

                # Notify frontend via a callback (set by REPL).
                if self._on_tool_call is not None:
                    self._on_tool_call(tc.name, tc.arguments, result.content)

                # Add tool result to history.
                self.history.append(result.to_openai_message())

            # Rebuild messages for the next iteration.
            messages = self._build_messages()

        return content  # fallback

    async def process_message_stream(self, text: str) -> AsyncIterator[dict[str, Any]]:
        """Stream a response from the LLM, yielding chunks.

        Each yielded dict has:
          - "type": "text" | "tool_call" | "tool_result" | "done"
          - additional keys depending on type.
        """
        self.history.append(Message.user(text))
        self._last_user_message = text
        messages = self._build_messages()
        tools = (
            self.get_openai_tools()
            if self._tools_enabled and self.get_tool_descriptions()
            else None
        )

        max_iterations = 10
        for _ in range(max_iterations):
            accumulated_text = ""
            accumulated_tool_calls: dict[int, dict[str, Any]] = {}

            async for chunk in self.provider.stream(messages, tools=tools):
                content = chunk.get("content", "")
                finish_reason = chunk.get("finish_reason")
                tc_deltas = chunk.get("tool_calls")

                if content:
                    accumulated_text += content
                    yield {"type": "text", "content": content}

                # Accumulate tool call deltas.
                if tc_deltas:
                    for tc_delta in tc_deltas:
                        idx = tc_delta.get("index", 0)
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc_delta.get("id"):
                            accumulated_tool_calls[idx]["id"] = tc_delta["id"]
                        if tc_delta.get("name"):
                            accumulated_tool_calls[idx]["name"] += tc_delta["name"]
                        if tc_delta.get("arguments"):
                            arg_delta = tc_delta["arguments"]
                            # Some providers (e.g. opencode/glm) return arguments
                            # as a parsed dict instead of a JSON string.
                            if isinstance(arg_delta, dict):
                                arg_delta = json.dumps(arg_delta, ensure_ascii=False)
                            accumulated_tool_calls[idx]["arguments"] += arg_delta

                if finish_reason == "stop":
                    break

            # No tool calls — we're done.
            if not accumulated_tool_calls:
                self.history.append(Message.assistant(accumulated_text))
                yield {"type": "done", "content": accumulated_text, "usage": self._total_usage}
                return

            # Resolve tool calls — with auto-repair for concatenated names.
            resolved_tool_calls: list[ToolCall] = []
            for idx in sorted(accumulated_tool_calls):
                tc_data = accumulated_tool_calls[idx]
                try:
                    args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    args = {"raw": tc_data["arguments"]}

                tc_name = tc_data["name"]
                tc_id = tc_data["id"]

                # Auto-repair: some models (e.g. GLM-5.1) concatenate
                # multiple tool names into one call.  Split them up.
                self._init_tools()
                if self._tool_registry and self._tool_registry.get(tc_name) is None:
                    repaired = self._repair_tool_name(tc_name)
                    if len(repaired) > 1 and all(self._tool_registry.get(n) for n in repaired):
                        logger.info(
                            "Stream: repaired concatenated tool name: %s → %s",
                            tc_name,
                            repaired,
                        )
                        # Create a separate ToolCall for each split name.
                        # Arguments go to the first tool; the rest get {}.
                        for i, name in enumerate(repaired):
                            call_args = args if i == 0 else {}
                            resolved_tool_calls.append(
                                ToolCall(
                                    id=f"{tc_id}_{i}" if tc_id else f"repair_{i}",
                                    name=name,
                                    arguments=call_args,
                                )
                            )
                        continue

                tc = ToolCall(id=tc_id, name=tc_name, arguments=args)
                resolved_tool_calls.append(tc)

            self.history.append(Message.assistant(accumulated_text, tool_calls=resolved_tool_calls))

            # Execute and yield tool results.
            for tc in resolved_tool_calls:
                yield {"type": "tool_call", "name": tc.name, "arguments": tc.arguments}

                result = await self.execute_tool(tc)
                yield {"type": "tool_result", "name": tc.name, "content": result.content}

                self.history.append(result.to_openai_message())

            # Rebuild messages for next iteration.
            messages = self._build_messages()

        yield {"type": "done", "content": accumulated_text, "usage": self._total_usage}

    # ── Callback hook for REPL ──────────────────────────────────────

    _on_tool_call_callbacks: list = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @property
    def _on_tool_call(self):
        """Callback for tool call notifications (set by REPL)."""
        return getattr(self, "__on_tool_call", None)

    @_on_tool_call.setter
    def _on_tool_call(self, fn):
        self.__on_tool_call = fn

    # ── Convenience ──────────────────────────────────────────────────

    @property
    def total_usage(self) -> dict[str, int]:
        return dict(self._total_usage)

    @property
    def last_user_message(self) -> str:
        """Return the last user message text (for /redo support)."""
        return self._last_user_message

    @classmethod
    def from_config_path(cls, config_path: str | None = None) -> AgentSession:
        """Create an :class:`AgentSession` from a config file path."""
        config = load_config(config_path)
        return cls(config)
