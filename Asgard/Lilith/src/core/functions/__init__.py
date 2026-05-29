"""
Function Calling Nativo - Sistema de tool execution v2

v5.0: Tool registry v2 con ejecutor nativo de funciones.
Soporta parsing de tool_calls, validación de parámetros, y ejecución segura.
"""
from .executor import FunctionExecutor, get_executor
from .parser import ParsedToolCall, ToolCallParser
from .registry import FunctionRegistry, get_function_registry
from .schemas import FunctionSchema, ParameterSchema, ToolResponse

__all__ = [
    "FunctionRegistry",
    "get_function_registry",
    "FunctionExecutor",
    "get_executor",
    "ToolCallParser",
    "ParsedToolCall",
    "FunctionSchema",
    "ParameterSchema",
    "ToolResponse",
]
