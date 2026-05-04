"""Tool registry for discovering and managing available Lilith tools."""

from .base import BaseTool


class ToolRegistry:
    _tools: dict[str, type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: type[BaseTool]):
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> type[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> dict[str, str]:
        return {name: tool_class.description for name, tool_class in cls._tools.items()}

    @classmethod
    def clear(cls):
        cls._tools.clear()
