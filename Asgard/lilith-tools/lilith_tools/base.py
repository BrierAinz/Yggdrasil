from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str = ""


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = None

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass

    def validate(self, params: Dict[str, Any]) -> bool:
        if not self.parameters:
            return True
        for key, config in self.parameters.items():
            if config.get("required", False) and key not in params:
                return False
        return True
