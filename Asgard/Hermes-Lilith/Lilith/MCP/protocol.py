"""
MCP Protocol — Tipos y constantes del Model Context Protocol
==============================================================
Define los dataclasses y constantes para comunicacion JSON-RPC 2.0
con servidores MCP, siguiendo la especificacion 2024-11-05.

Refs: https://spec.modelcontextprotocol.io/specification/2024-11-05/
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# constantes
# ═══════════════════════════════════════════════════════════════════════════════

MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_CLIENT_NAME = "lilith"
MCP_CLIENT_VERSION = "3.0.0"
JSONRPC_VERSION = "2.0"


# Metodos del protocolo
class MCPMethod(str, Enum):
    """Metodos MCP definidos en la especificacion."""

    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    PING = "ping"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    SUBSCRIBE = "resources/subscribe"
    UNSUBSCRIBE = "resources/unsubscribe"
    COMPLETION = "completion/complete"
    LOGGING = "logging/setLevel"
    CANCEL = "notifications/cancelled"
    PROGRESS = "notifications/progress"


# ═══════════════════════════════════════════════════════════════════════════════
# tipos de datos del protocolo
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MCPToolParameter:
    """Parametro de una tool MCP."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convierte a JSON Schema property."""
        schema: Dict[str, Any] = {"type": self.type}
        if self.description:
            schema["description"] = self.description
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass
class MCPTool:
    """Tool expuesta por un server MCP."""

    name: str
    description: str = ""
    server_name: str = ""  # de que server viene
    parameters: List[MCPToolParameter] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None  # schema completo si viene del server

    def to_openai_function(self) -> Dict[str, Any]:
        """Convierte a formato OpenAI function calling.

        Esto permite inyectar tools MCP directamente en las llamadas al LLM
        como si fueran tools nativas de Lilith.
        """
        # Si el server ya dio un schema completo, usarlo
        if self.input_schema:
            parameters = self.input_schema
        else:
            # Construir schema desde parameters
            properties = {}
            required = []
            for p in self.parameters:
                properties[p.name] = p.to_json_schema()
                if p.required:
                    required.append(p.name)

            parameters = {
                "type": "object",
                "properties": properties,
            }
            if required:
                parameters["required"] = required

        return {
            "name": self.name,
            "description": self.description or f"MCP tool: {self.name}",
            "parameters": parameters,
        }


@dataclass
class MCPResource:
    """Recurso expuesto por un server MCP (archivos, datos, etc.)."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    server_name: str = ""


@dataclass
class MCPPrompt:
    """Prompt template expuesto por un server MCP."""

    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    server_name: str = ""


@dataclass
class MCPPromptArgument:
    """Argumento de un prompt template."""

    name: str
    description: str = ""
    required: bool = False


@dataclass
class MCPServerInfo:
    """Informacion del servidor MCP tras el handshake."""

    name: str = ""
    version: str = ""
    protocol_version: str = MCP_PROTOCOL_VERSION
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPConnectionState:
    """Estado de la conexion a un server MCP."""

    connected: bool = False
    initialized: bool = False
    server_info: Optional[MCPServerInfo] = None
    request_id: int = 0
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# helpers JSON-RPC
# ═══════════════════════════════════════════════════════════════════════════════


def make_request(
    method: str, params: Optional[Dict[str, Any]] = None, request_id: int = 1
) -> Dict[str, Any]:
    """Construye un mensaje JSON-RPC request."""
    msg: Dict[str, Any] = {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "method": method,
    }
    if params:
        msg["params"] = params
    return msg


def make_notification(
    method: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Construye un mensaje JSON-RPC notification (sin id, no espera respuesta)."""
    msg: Dict[str, Any] = {
        "jsonrpc": JSONRPC_VERSION,
        "method": method,
    }
    if params:
        msg["params"] = params
    return msg


def make_response(request_id: int, result: Any) -> Dict[str, Any]:
    """Construye un mensaje JSON-RPC response (exitoso)."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "result": result,
    }


def make_error(
    request_id: int, code: int, message: str, data: Any = None
) -> Dict[str, Any]:
    """Construye un mensaje JSON-RPC error response."""
    error: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": error,
    }


# Codigos de error JSON-RPC
class JSONRPCError(int, Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class MCPError(Exception):
    """Error especifico de MCP."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")


def parse_mcp_response(raw: Dict[str, Any]) -> Any:
    """Parsea una respuesta MCP y lanza excepcion si es error."""
    if "error" in raw:
        err = raw["error"]
        raise MCPError(
            code=err.get("code", -32603),
            message=err.get("message", "Unknown MCP error"),
            data=err.get("data"),
        )
    return raw.get("result")
