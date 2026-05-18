"""Tool registry for discovering and managing available Lilith tools."""

from .base import BaseTool


class ToolRegistry:
    _tools: dict[str, type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: type[BaseTool]):
        """Registrar una clase de herramienta en el registry."""
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get(cls, name: str) -> type[BaseTool]:
        """Obtener una clase de herramienta por nombre."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> dict[str, str]:
        """Listar todas las herramientas registradas con su descripción."""
        return {name: tool_class.description for name, tool_class in cls._tools.items()}

    @classmethod
    def clear(cls):
        """Limpiar todas las herramientas registradas."""
        cls._tools.clear()
