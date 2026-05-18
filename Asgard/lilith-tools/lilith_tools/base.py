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
        pass

    def validate(self, params: dict[str, Any]) -> bool:
        if not self.parameters:
            return True
        for key, config in self.parameters.items():
            if config.get("required", False) and key not in params:
                return False
        return True
