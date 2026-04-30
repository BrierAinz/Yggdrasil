"""
Base para tools con name/description como atributos de clase (ej. browser_tool).
Compatible con LilithTool para ToolRegistryV3.
"""
from typing import Any, Dict

from .protocol import LilithTool, ToolResult


class ToolV3(LilithTool):
    """
    Base que implementa LilithTool usando atributos de clase name y description.
    Las subclases definen: name, description y execute(params).
    """

    name: str = ""
    description: str = ""

    @property
    def name(self) -> str:
        return getattr(type(self), "name", "") or ""

    def get_description(self) -> str:
        return self.description or ""

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        raise NotImplementedError("Subclase debe implementar execute")
