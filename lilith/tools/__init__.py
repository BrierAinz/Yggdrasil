"""Lilith Agent — Tool definitions registry."""

# Tool definitions are imported from lilith_agent.py for now
# This module provides the registry pattern for future modularization

from collections.abc import Callable


class ToolRegistry:
    """Registry for agent tools."""

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        """Register a new tool."""
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self._handlers[name] = handler

    def get_schema(self) -> list[dict]:
        """Get all tool schemas for API calls."""
        return list(self._tools.values())

    def execute(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool by name."""
        if name not in self._handlers:
            return f"Unknown tool: {name}"
        try:
            return self._handlers[name](args, **kwargs)
        except Exception as e:
            return f"Error in {name}: {e}"

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
