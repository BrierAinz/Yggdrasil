"""
Tests del LilithMCPServer
==========================
Tests unitarios para el servidor MCP que expone skills y tools de Lilith.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.MCP.protocol import JSONRPC_VERSION, MCP_PROTOCOL_VERSION
from Lilith.MCP.server import LilithMCPServer, get_mcp_server


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def server():
    """Crea un servidor MCP limpio para cada test."""
    s = LilithMCPServer(name="test_lilith", version="1.0.0")
    # Registrar tools de prueba
    s.register_tool(
        name="echo",
        description="Echo tool para pruebas",
        parameters=[
            {"name": "message", "type": "string", "description": "Message to echo", "required": True},
        ],
        executor=lambda args: f"Echo: {args.get('message', '')}",
    )
    s.register_tool(
        name="add",
        description="Suma dos números",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "integer", "description": "Primer número"},
                "b": {"type": "integer", "description": "Segundo número"},
            },
            "required": ["a", "b"],
        },
        executor=lambda args: args.get("a", 0) + args.get("b", 0),
    )
    return s


@pytest.fixture
def server_with_resources():
    """Servidor con recursos registrados."""
    s = LilithMCPServer(name="test_lilith", version="1.0.0")
    s.register_resource(
        uri="lilith://config/main",
        name="Main Config",
        description="Configuración principal de Lilith",
        mime_type="application/json",
        reader=lambda uri: '{"status": "ok"}',
    )
    s.register_resource(
        uri="lilith://memory/stats",
        name="Memory Stats",
        description="Estadísticas de memoria",
        mime_type="text/plain",
        reader=lambda uri: "Episodes: 42, Facts: 128",
    )
    return s


@pytest.fixture
def server_with_prompts():
    """Servidor con prompts registrados."""
    s = LilithMCPServer(name="test_lilith", version="1.0.0")
    s.register_prompt(
        name="summarize",
        description="Resume el contenido dado",
        arguments=[{"name": "content", "description": "Contenido a resumir", "required": True}],
        template="Resume el siguiente contenido: {content}",
    )
    s.register_prompt(
        name="translate",
        description="Traduce texto a otro idioma",
        arguments=[
            {"name": "text", "description": "Texto a traducir", "required": True},
            {"name": "language", "description": "Idioma destino", "required": True},
        ],
        template="Traduce el siguiente texto a {language}: {text}",
    )
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# Test initializing
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPServerInit:
    """Tests de inicialización del servidor MCP."""

    def test_server_creation(self):
        """Un servidor MCP se crea correctamente."""
        server = LilithMCPServer()
        assert server.name == "lilith"
        assert server.version == "3.0.0"
        assert server.protocol_version == MCP_PROTOCOL_VERSION
        assert server._running is False
        assert server._initialized is False

    def test_server_custom_name_version(self):
        """Se puede crear un servidor con nombre y versión custom."""
        server = LilithMCPServer(name="mi_server", version="2.0.0")
        assert server.name == "mi_server"
        assert server.version == "2.0.0"

    def test_server_registers_lilith_tools(self):
        """El servidor intenta registrar las tools nativas de Lilith."""
        server = LilithMCPServer()
        # Puede que haya tools registradas o no, dependiendo de si Lilith.tools existe
        assert isinstance(server._tools, dict)

    def test_get_status_initial(self):
        """El estado inicial del servidor es correcto."""
        server = LilithMCPServer(name="test")
        status = server.get_status()
        assert status["name"] == "test"
        assert status["initialized"] is False
        assert status["running"] is False
        assert "tools_count" in status
        assert "resources_count" in status
        assert "prompts_count" in status


# ═══════════════════════════════════════════════════════════════════════════════
# Test registro de tools
# ═══════════════════════════════════════════════════════════════════════════════


class TestToolRegistration:
    """Tests de registro de tools en el servidor MCP."""

    def test_register_tool_basic(self, server):
        """Una tool se registra correctamente."""
        server.register_tool(
            name="test_tool",
            description="Tool de prueba",
        )
        assert "test_tool" in server._tools
        assert server._tools["test_tool"]["description"] == "Tool de prueba"

    def test_register_tool_with_parameters(self, server):
        """Una tool con parámetros se registra correctamente."""
        server.register_tool(
            name="search",
            description="Buscar en la web",
            parameters=[
                {"name": "query", "type": "string", "description": "Búsqueda", "required": True},
                {"name": "limit", "type": "integer", "description": "Límite de resultados", "required": False},
            ],
        )
        tool = server._tools["search"]
        schema = tool["inputSchema"]
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "query" in schema["required"]
        assert "limit" not in schema.get("required", [])

    def test_register_tool_with_input_schema(self, server):
        """Una tool con input_schema se registra correctamente."""
        custom_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path"],
        }
        server.register_tool(
            name="custom_read",
            description="Lee un archivo",
            input_schema=custom_schema,
        )
        tool = server._tools["custom_read"]
        assert tool["inputSchema"] == custom_schema

    def test_register_tool_with_executor(self, server):
        """Una tool con executor se registra correctamente."""
        called_with = {}

        def my_executor(args):
            called_with.update(args)
            return "ok"

        server.register_tool(
            name="exec_tool",
            description="Tool con ejecutor",
            executor=my_executor,
        )
        assert "exec_tool" in server._tool_executors

    def test_register_tool_overwrite(self, server):
        """Registrar una tool con el mismo nombre la sobreescribe."""
        server.register_tool(name="dup", description="Primera")
        server.register_tool(name="dup", description="Segunda")
        assert server._tools["dup"]["description"] == "Segunda"

    def test_register_tool_empty_parameters(self, server):
        """Una tool sin parámetros tiene schema vacío."""
        server.register_tool(name="no_params", description="Sin params")
        tool = server._tools["no_params"]
        assert tool["inputSchema"] == {"type": "object", "properties": {}}


# ═══════════════════════════════════════════════════════════════════════════════
# Test registro de recursos
# ═══════════════════════════════════════════════════════════════════════════════


class TestResourceRegistration:
    """Tests de registro de recursos MCP."""

    def test_register_resource(self, server):
        """Un recurso se registra correctamente."""
        server.register_resource(
            uri="lilith://test",
            name="Test Resource",
            description="Recurso de test",
            mime_type="application/json",
            reader=lambda uri: '{"test": true}',
        )
        assert "lilith://test" in server._resources
        res = server._resources["lilith://test"]
        assert res.name == "Test Resource"
        assert res.uri == "lilith://test"

    def test_register_resource_default_mime(self, server):
        """Un recurso sin mime_type usa text/plain por defecto."""
        server.register_resource(
            uri="lilith://plain",
            name="Plain Resource",
        )
        assert server._resources["lilith://plain"].mime_type == "text/plain"

    def test_register_resource_without_reader(self, server):
        """Un recurso sin reader usa el URI como contenido."""
        server.register_resource(
            uri="lilith://no_reader",
            name="No Reader",
        )
        assert "lilith://no_reader" not in server._resource_readers


# ═══════════════════════════════════════════════════════════════════════════════
# Test registro de prompts
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptRegistration:
    """Tests de registro de prompts MCP."""

    def test_register_prompt(self, server):
        """Un prompt se registra correctamente."""
        server.register_prompt(
            name="test_prompt",
            description="Prompt de prueba",
            arguments=[{"name": "topic", "description": "Tema", "required": True}],
            template="Investiga sobre {topic}",
        )
        assert "test_prompt" in server._prompts
        p = server._prompts["test_prompt"]
        assert p["name"] == "test_prompt"
        assert p["template"] == "Investiga sobre {topic}"

    def test_register_prompt_empty_arguments(self, server):
        """Un prompt sin argumentos se registra correctamente."""
        server.register_prompt(name="simple", description="Simple prompt")
        p = server._prompts["simple"]
        assert p["arguments"] == []
        assert p["template"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Test JSON-RPC request handling
# ═══════════════════════════════════════════════════════════════════════════════


class TestRequestHandling:
    """Tests de manejo de requests JSON-RPC."""

    def test_handle_initialize(self, server):
        """El handler initialize responde con capabilities."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "clientInfo": {"name": "test_client", "version": "1.0"},
            },
        }
        response = server.handle_request(request)
        assert response["id"] == 1
        assert "result" in response
        result = response["result"]
        assert result["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]
        assert "prompts" in result["capabilities"]
        assert result["serverInfo"]["name"] == "test_lilith"

    def test_handle_initialize_sets_flag(self, server):
        """Initialize marca el servidor como inicializado."""
        assert server._initialized is False
        server.handle_request({
            "jsonrpc": JSONRPC_VERSION,
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert server._initialized is True

    def test_handle_ping(self, server):
        """El handler ping responde con status ok."""
        request = {"jsonrpc": JSONRPC_VERSION, "id": 2, "method": "ping"}
        response = server.handle_request(request)
        assert response["id"] == 2
        assert "result" in response
        assert response["result"]["status"] == "ok"

    def test_handle_tools_list(self, server):
        """El handler tools/list lista las tools registradas."""
        request = {"jsonrpc": JSONRPC_VERSION, "id": 3, "method": "tools/list"}
        response = server.handle_request(request)
        assert "result" in response
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_handle_tools_list_empty(self):
        """tools/list en un servidor sin tools retorna lista vacía."""
        server = LilithMCPServer(name="empty")
        server._tools = {}  # Forzar vacío
        request = {"jsonrpc": JSONRPC_VERSION, "id": 1, "method": "tools/list"}
        response = server.handle_request(request)
        assert response["result"]["tools"] == []

    def test_handle_tools_call(self, server):
        """El handler tools/call ejecuta una tool y retorna el resultado."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "hello"},
            },
        }
        response = server.handle_request(request)
        assert "result" in response
        assert "content" in response["result"]
        assert response["result"]["isError"] is False

    def test_handle_tools_call_add(self, server):
        """El handler tools/call ejecuta la tool add correctamente."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "add",
                "arguments": {"a": 3, "b": 5},
            },
        }
        response = server.handle_request(request)
        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["text"] == "8"

    def test_handle_tools_call_missing_name(self, server):
        """tools/call sin nombre de tool retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 6,
            "method": "tools/call",
            "params": {"arguments": {}},
        }
        response = server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32602

    def test_handle_tools_call_unknown_tool(self, server):
        """tools/call con tool desconocida retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "nonexistent",
                "arguments": {},
            },
        }
        response = server.handle_request(request)
        assert "error" in response
        assert "not found" in response["error"]["message"].lower() or response["error"]["code"] == -32602

    def test_handle_tools_call_executor_error(self, server):
        """tools/call con un executor que falla retorna isError=true."""
        server.register_tool(
            name="failing",
            description="Siempre falla",
            executor=lambda args: (_ for _ in ()).throw(ValueError("test error")),
        )
        # Usar un executor que realmente falle
        server._tool_executors["failing"] = lambda args: 1 / 0

        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "failing",
                "arguments": {},
            },
        }
        response = server.handle_request(request)
        assert "result" in response
        assert response["result"]["isError"] is True

    def test_handle_unknown_method(self, server):
        """Un método desconocido retorna error -32601."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 99,
            "method": "unknown/method",
        }
        response = server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601


# ═══════════════════════════════════════════════════════════════════════════════
# Test Resources
# ═══════════════════════════════════════════════════════════════════════════════


class TestResourceHandling:
    """Tests de manejo de recursos MCP."""

    def test_handle_resources_list(self, server_with_resources):
        """resources/list lista los recursos registrados."""
        request = {"jsonrpc": JSONRPC_VERSION, "id": 10, "method": "resources/list"}
        response = server_with_resources.handle_request(request)
        resources = response["result"]["resources"]
        assert len(resources) == 2
        uris = [r["uri"] for r in resources]
        assert "lilith://config/main" in uris
        assert "lilith://memory/stats" in uris

    def test_handle_resources_read(self, server_with_resources):
        """resources/read lee un recurso por su URI."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 11,
            "method": "resources/read",
            "params": {"uri": "lilith://config/main"},
        }
        response = server_with_resources.handle_request(request)
        contents = response["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "lilith://config/main"
        assert "ok" in contents[0]["text"]

    def test_handle_resources_read_missing_uri(self, server_with_resources):
        """resources/read sin URI retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 12,
            "method": "resources/read",
            "params": {},
        }
        response = server_with_resources.handle_request(request)
        assert "error" in response

    def test_handle_resources_read_unknown_uri(self, server_with_resources):
        """resources/read con URI desconocido retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 13,
            "method": "resources/read",
            "params": {"uri": "lilith://nonexistent"},
        }
        response = server_with_resources.handle_request(request)
        assert "error" in response


# ═══════════════════════════════════════════════════════════════════════════════
# Test Prompts
# ═══════════════════════════════════════════════════════════════════════════════


class TestPromptHandling:
    """Tests de manejo de prompts MCP."""

    def test_handle_prompts_list(self, server_with_prompts):
        """prompts/list lista los prompts registrados."""
        request = {"jsonrpc": JSONRPC_VERSION, "id": 20, "method": "prompts/list"}
        response = server_with_prompts.handle_request(request)
        prompts = response["result"]["prompts"]
        assert len(prompts) == 2
        names = [p["name"] for p in prompts]
        assert "summarize" in names
        assert "translate" in names

    def test_handle_prompts_get(self, server_with_prompts):
        """prompts/get renderiza un prompt con argumentos."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 21,
            "method": "prompts/get",
            "params": {
                "name": "translate",
                "arguments": {"text": "Hello world", "language": "es"},
            },
        }
        response = server_with_prompts.handle_request(request)
        result = response["result"]
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert "es" in result["messages"][0]["content"]["text"]
        assert "Hello world" in result["messages"][0]["content"]["text"]

    def test_handle_prompts_get_missing_name(self, server_with_prompts):
        """prompts/get sin nombre retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 22,
            "method": "prompts/get",
            "params": {},
        }
        response = server_with_prompts.handle_request(request)
        assert "error" in response

    def test_handle_prompts_get_unknown_name(self, server_with_prompts):
        """prompts/get con nombre desconocido retorna error."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 23,
            "method": "prompts/get",
            "params": {"name": "nonexistent"},
        }
        response = server_with_prompts.handle_request(request)
        assert "error" in response


# ═══════════════════════════════════════════════════════════════════════════════
# Test Singleton
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPServerSingleton:
    """Tests del singleton LilithMCPServer."""

    def test_get_mcp_server_returns_instance(self):
        """get_mcp_server retorna una instancia."""
        import Lilith.MCP.server as server_mod
        server_mod._server_instance = None  # Reset singleton
        server = get_mcp_server()
        assert isinstance(server, LilithMCPServer)

    def test_get_mcp_server_singleton(self):
        """get_mcp_server retorna la misma instancia."""
        import Lilith.MCP.server as server_mod
        server_mod._server_instance = None  # Reset
        s1 = get_mcp_server()
        s2 = get_mcp_server()
        assert s1 is s2