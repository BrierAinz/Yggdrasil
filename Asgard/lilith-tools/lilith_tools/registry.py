from typing import Dict, Type

from .base import BaseTool


class ToolRegistry:
    _tools: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> Type[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        return {name: tool_class.description for name, tool_class in cls._tools.items()}

    @classmethod
    def clear(cls):
        cls._tools.clear()
