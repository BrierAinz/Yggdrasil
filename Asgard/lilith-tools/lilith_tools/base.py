"""Base classes and data structures for the Lilith tool system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str = ""


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] | None = None

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Ejecutar la herramienta con los argumentos dados."""
        pass

    def validate(self, params: dict[str, Any]) -> bool:
        """Validar que los parámetros requeridos estén presentes."""
        if not self.parameters:
            return True
        for key, config in self.parameters.items():
            if config.get("required", False) and key not in params:
                return False
        return True
