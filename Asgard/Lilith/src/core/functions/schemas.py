"""
Schemas - Definiciones de datos para function calling

v5.0: Estructuras de datos para funciones, parámetros y respuestas.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Union


class ParameterType(str, Enum):
    """Tipos de parámetros soportados."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ParameterSchema:
    """Esquema de un parámetro de función."""

    name: str
    type: ParameterType
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    items: Optional[Dict[str, Any]] = None  # Para arrays
    properties: Optional[Dict[str, Any]] = None  # Para objects

    def to_json_schema(self) -> Dict[str, Any]:
        """Convierte a formato JSON Schema."""
        schema = {"type": self.type.value, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        if self.items:
            schema["items"] = self.items
        if self.properties:
            schema["properties"] = self.properties
        return schema


@dataclass
class FunctionSchema:
    """Esquema completo de una función registrada."""

    name: str
    description: str
    parameters: List[ParameterSchema]
    handler: Optional[Callable] = None
    return_type: str = "string"
    examples: List[Dict[str, Any]] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_message: str = ""
    category: str = "general"

    def to_openai_format(self) -> Dict[str, Any]:
        """Convierte al formato de OpenAI/Kimi function calling."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convierte al formato de Anthropic tool use."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


@dataclass
class ToolResponse:
    """Respuesta de ejecución de tool."""

    success: bool
    result: Any
    tool_name: str
    execution_time_ms: float
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "tool_name": self.tool_name,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "logs": self.logs,
            "metadata": self.metadata,
        }

    @classmethod
    def success_response(
        cls, result: Any, tool_name: str, execution_time_ms: float, **metadata
    ) -> "ToolResponse":
        """Crea una respuesta exitosa."""
        return cls(
            success=True,
            result=result,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            metadata=metadata,
        )

    @classmethod
    def error_response(
        cls, error: str, tool_name: str, execution_time_ms: float = 0.0
    ) -> "ToolResponse":
        """Crea una respuesta de error."""
        return cls(
            success=False,
            result=None,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            error=error,
        )
