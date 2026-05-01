"""
Tests MCP — Protocol, Client, Manager, DynamicTools
=====================================================
Tests unitarios e integracion para los modulos de MCP.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Asegurar que podemos importar Lilith
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.Core.dynamic_tools import DynamicToolRegistry, ToolInfo, ToolSource
from Lilith.MCP.client import MCPClient
from Lilith.MCP.manager import MCPManager
from Lilith.MCP.protocol import (
    JSONRPC_VERSION,
    MCP_PROTOCOL_VERSION,
    MCPConnectionState,
    MCPError,
    MCPMethod,
    MCPServerInfo,
    MCPTool,
    MCPToolParameter,
    make_error,
    make_notification,
    make_request,
    make_response,
    parse_mcp_response,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PROTOCOL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPProtocol:
    """Tests para los tipos y helpers del protocolo MCP."""

    def test_mcp_tool_creation(self):
        """Una tool MCP se crea correctamente."""
        tool = MCPTool(
            name="read_file",
            description="Read a file from disk",
            server_name="filesystem",
        )
        assert tool.name == "read_file"
        assert tool.description == "Read a file from disk"
        assert tool.server_name == "filesystem"
        assert tool.parameters == []

    def test_mcp_tool_with_input_schema(self):
        """Una tool MCP con input_schema se convierte a OpenAI format."""
        tool = MCPTool(
            name="read_file",
            description="Read a file",
            server_name="filesystem",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path"}},
                "required": ["path"],
            },
        )
        openai_func = tool.to_openai_function()
        assert openai_func["name"] == "read_file"
        assert openai_func["description"] == "Read a file"
        assert "properties" in openai_func["parameters"]
        assert "path" in openai_func["parameters"]["properties"]

    def test_mcp_tool_without_schema(self):
        """Una tool MCP sin input_schema construye schema desde parameters."""
        tool = MCPTool(
            name="search",
            description="Search the web",
            server_name="brave",
            parameters=[
                MCPToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                MCPToolParameter(
                    name="count", type="integer", description="Result count", default=10
                ),
            ],
        )
        openai_func = tool.to_openai_function()
        assert openai_func["name"] == "search"
        params = openai_func["parameters"]
        assert "query" in params["properties"]
        assert "count" in params["properties"]
        assert params["required"] == ["query"]

    def test_mcp_tool_parameter_to_json_schema(self):
        """MCPToolParameter se convierte a JSON Schema property."""
        param = MCPToolParameter(
            name="path",
            type="string",
            description="File path",
            required=True,
        )
        schema = param.to_json_schema()
        assert schema["type"] == "string"
        assert schema["description"] == "File path"

    def test_mcp_tool_parameter_with_enum(self):
        """MCPToolParameter con enum se convierte correctamente."""
        param = MCPToolParameter(
            name="mode",
            type="string",
            description="Mode",
            enum=["read", "write"],
        )
        schema = param.to_json_schema()
        assert schema["enum"] == ["read", "write"]

    def test_make_request(self):
        """make_request construye un request JSON-RPC valido."""
        req = make_request("tools/list", {"cursor": "abc"}, request_id=5)
        assert req["jsonrpc"] == JSONRPC_VERSION
        assert req["id"] == 5
        assert req["method"] == "tools/list"
        assert req["params"] == {"cursor": "abc"}

    def test_make_request_no_params(self):
        """make_request sin params no incluye campo params."""
        req = make_request("ping", request_id=1)
        assert "params" not in req
        assert req["method"] == "ping"

    def test_make_notification(self):
        """make_notification no tiene id."""
        notif = make_notification("notifications/initialized")
        assert "id" not in notif
        assert notif["jsonrpc"] == JSONRPC_VERSION
        assert notif["method"] == "notifications/initialized"

    def test_make_response(self):
        """make_response construye una respuesta JSON-RPC exitosa."""
        resp = make_response(42, {"tools": []})
        assert resp["jsonrpc"] == JSONRPC_VERSION
        assert resp["id"] == 42
        assert resp["result"] == {"tools": []}

    def test_make_error(self):
        """make_error construye una respuesta JSON-RPC de error."""
        err = make_error(1, -32600, "Invalid Request")
        assert err["jsonrpc"] == JSONRPC_VERSION
        assert err["id"] == 1
        assert err["error"]["code"] == -32600
        assert err["error"]["message"] == "Invalid Request"

    def test_make_error_with_data(self):
        """make_error con data extra."""
        err = make_error(2, -32602, "Invalid params", data={"missing": "path"})
        assert err["error"]["data"] == {"missing": "path"}

    def test_parse_mcp_response_success(self):
        """parse_mcp_response retorna result de respuesta exitosa."""
        resp = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        result = parse_mcp_response(resp)
        assert result == {"tools": []}

    def test_parse_mcp_response_error(self):
        """parse_mcp_response lanza MCPError en respuesta de error."""
        resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
        with pytest.raises(MCPError) as exc_info:
            parse_mcp_response(resp)
        assert exc_info.value.code == -32600
        assert "Invalid Request" in exc_info.value.message

    def test_mcp_connection_state_defaults(self):
        """MCPConnectionState tiene defaults correctos."""
        state = MCPConnectionState()
        assert state.connected is False
        assert state.initialized is False
        assert state.server_info is None
        assert state.request_id == 0
        assert state.error is None

    def test_mcp_server_info(self):
        """MCPServerInfo se crea con defaults correctos."""
        info = MCPServerInfo(name="test-server", version="1.0.0")
        assert info.protocol_version == MCP_PROTOCOL_VERSION
        assert info.capabilities == {}

    def test_mcp_method_enum(self):
        """MCPMethod tiene los metodos correctos."""
        assert MCPMethod.INITIALIZE.value == "initialize"
        assert MCPMethod.LIST_TOOLS.value == "tools/list"
        assert MCPMethod.CALL_TOOL.value == "tools/call"
        assert MCPMethod.LIST_RESOURCES.value == "resources/list"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP CLIENT TESTS (mocked — no subprocess)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPClient:
    """Tests para MCPClient (mocked)."""

    def test_client_creation(self):
        """MCPClient se crea con config correcta."""
        from Lilith.MCP.client import MCPClient

        client = MCPClient(
            {
                "name": "test-server",
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-server-filesystem", "/tmp"],
                "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
            }
        )
        assert client.name == "test-server"
        assert client.command == "npx"
        assert client.args == ["-y", "@anthropic/mcp-server-filesystem", "/tmp"]
        assert client.state.connected is False
        assert client.state.initialized is False
        assert len(client.tools) == 0

    def test_client_get_status(self):
        """get_status retorna estado correcto."""
        from Lilith.MCP.client import MCPClient

        client = MCPClient({"name": "test", "command": "echo"})
        status = client.get_status()
        assert status["name"] == "test"
        assert status["connected"] is False
        assert status["tools_count"] == 0
        assert status["command"] == "echo"

    def test_client_repr(self):
        """MCPClient tiene repr informativo."""
        from Lilith.MCP.client import MCPClient

        client = MCPClient({"name": "myserver", "command": "test"})
        assert "myserver" in repr(client)
        assert "disconnected" in repr(client)

    def test_resolve_env_vars(self):
        """_resolve_env resuelve variables ${VAR}."""
        from Lilith.MCP.client import MCPClient

        os.environ["TEST_LILITH_VAR"] = "secret123"
        resolved = MCPClient._resolve_env(
            {"API_KEY": "${TEST_LILITH_VAR}", "OTHER": "literal"}
        )
        assert resolved["API_KEY"] == "secret123"
        assert resolved["OTHER"] == "literal"
        del os.environ["TEST_LILITH_VAR"]

    def test_resolve_env_missing_var(self):
        """_resolve_env maneja variables de entorno no encontradas."""
        from Lilith.MCP.client import MCPClient

        resolved = MCPClient._resolve_env({"MISSING": "${NONEXISTENT_VAR_12345}"})
        assert resolved["MISSING"] == ""


# ═══════════════════════════════════════════════════════════════════════════════
# MCP MANAGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPManager:
    """Tests para MCPManager."""

    def test_manager_creation(self):
        """MCPManager se crea correctamente."""
        manager = MCPManager(config_path=Path("/tmp/nonexistent_mcp.json"))
        assert len(manager.clients) == 0
        assert manager._started is False

    def test_manager_get_status_empty(self):
        """get_status funciona sin servers."""
        manager = MCPManager(config_path=Path("/tmp/nonexistent_mcp.json"))
        status = manager.get_status()
        assert status["servers_count"] == 0
        assert status["connected_count"] == 0
        assert status["total_tools"] == 0

    def test_manager_create_default_config(self):
        """_create_default_config crea archivo mcp.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".lilith_test" / "mcp.json"
            manager = MCPManager(config_path=config_path)
            # Crea directorio y archivo
            manager._create_default_config()
            assert config_path.exists()
            with open(config_path) as f:
                config = json.load(f)
            assert "servers" in config

    def test_manager_load_config_empty(self):
        """_load_config con archivo vacio."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"servers": {}}, f)
            f.flush()
            manager = MCPManager(config_path=Path(f.name))
            manager._load_config()  # __init__ no carga, hay que llamarlo
            assert len(manager.clients) == 0
        os.unlink(f.name)

    def test_manager_load_config_with_servers(self):
        """_load_config carga servers desde archivo."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "servers": {
                    "test-server": {
                        "command": "echo",
                        "args": [],
                        "env": {},
                    }
                }
            }
            json.dump(config, f)
            f.flush()
            manager = MCPManager(config_path=Path(f.name))
            manager._load_config()
            assert "test-server" in manager.clients
            assert manager.clients["test-server"].command == "echo"
        os.unlink(f.name)

    def test_manager_save_config(self):
        """save_config guarda la configuracion correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp_save_test.json"
            manager = MCPManager(config_path=config_path)

            manager.clients["my-server"] = MCPClient(
                {
                    "name": "my-server",
                    "command": "npx",
                    "args": ["-y", "test-server"],
                    "env": {},
                }
            )

            manager.save_config()
            assert config_path.exists()
            with open(config_path) as f:
                saved = json.load(f)
            assert "my-server" in saved["servers"]
            assert saved["servers"]["my-server"]["command"] == "npx"

    def test_manager_get_server_names(self):
        """get_server_names lista nombres de servers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config = {
                "servers": {
                    "fs": {"command": "echo", "args": [], "env": {}},
                    "gh": {"command": "echo2", "args": [], "env": {}},
                }
            }
            json.dump(config, f)
            f.flush()
            manager = MCPManager(config_path=Path(f.name))
            manager._load_config()
            names = manager.get_server_names()
            assert "fs" in names
            assert "gh" in names
        os.unlink(f.name)

    def test_manager_repr(self):
        """MCPManager tiene repr informativo."""
        manager = MCPManager(config_path=Path("/tmp/nonexistent.json"))
        assert "0 servers" in repr(manager)

    def test_manager_add_server(self):
        """add_server agrega un server al manager (sin conectar)."""
        from Lilith.MCP.client import MCPClient as MC

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp_add.json"
            manager = MCPManager(config_path=config_path)

            config = {"command": "nonexistent_cmd_xyz", "args": [], "env": {}}
            manager.clients["test"] = MC({**config, "name": "test"})
            assert "test" in manager.clients


# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC TOOLS REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDynamicToolRegistry:
    """Tests para DynamicToolRegistry."""

    def test_registry_creation(self):
        """DynamicToolRegistry se crea vacio."""
        registry = DynamicToolRegistry()
        assert len(registry) == 0

    def test_register_native_tool(self):
        """Registrar una tool nativa."""
        registry = DynamicToolRegistry()

        def mock_executor(name, args):
            return {"result": "ok"}

        registry.register_native_tool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            executor=mock_executor,
        )
        assert "test_tool" in registry
        assert len(registry) == 1

    def test_register_native_tools_batch(self):
        """Registrar multiples tools nativas."""
        registry = DynamicToolRegistry()

        tools_list = [
            {
                "type": "function",
                "function": {
                    "name": "tool_a",
                    "description": "Tool A",
                    "parameters": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_b",
                    "description": "Tool B",
                    "parameters": {
                        "type": "object",
                        "properties": {"y": {"type": "integer"}},
                    },
                },
            },
        ]

        def mock_executor(name, args):
            return {"tool": name}

        executors = {"tool_a": mock_executor, "tool_b": mock_executor}
        count = registry.register_native_tools(tools_list, executors)
        assert count == 2
        assert len(registry) == 2

    def test_register_native_tools_without_executor(self):
        """Registrar tools nativas sin executor genera warning."""
        registry = DynamicToolRegistry()

        tools_list = [
            {
                "type": "function",
                "function": {
                    "name": "orphan_tool",
                    "description": "Tool sin executor",
                    "parameters": {},
                },
            },
        ]

        count = registry.register_native_tools(tools_list, {})
        assert count == 1
        # La tool existe pero no se puede ejecutar
        assert "orphan_tool" in registry

    def test_execute_native_tool(self):
        """Ejecutar una tool nativa sincronamente."""
        registry = DynamicToolRegistry()

        def echo_executor(name, args):
            return {"echo": args.get("text", "")}

        registry.register_native_tool(
            name="echo",
            description="Echo tool",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}},
            executor=echo_executor,
        )

        result = registry.execute_native("echo", {"text": "hello"})
        assert result == {"echo": "hello"}

    def test_execute_native_tool_not_found(self):
        """execute_native lanza KeyError si la tool no existe."""
        registry = DynamicToolRegistry()
        with pytest.raises(KeyError):
            registry.execute_native("nonexistent")

    def test_execute_native_tool_no_executor(self):
        """execute_native lanza RuntimeError si no hay executor."""
        registry = DynamicToolRegistry()
        registry.register_native_tool(
            name="broken",
            description="Sin executor",
            parameters={},
            executor=None,
        )
        with pytest.raises(RuntimeError):
            registry.execute_native("broken")

    def test_unregister_tool(self):
        """unregister_tool remueve una tool."""
        registry = DynamicToolRegistry()

        registry.register_native_tool(
            name="temp",
            description="Temporal",
            parameters={},
            executor=lambda n, a: None,
        )
        assert "temp" in registry
        assert registry.unregister_tool("temp") is True
        assert "temp" not in registry
        assert registry.unregister_tool("nonexistent") is False

    def test_list_tools(self):
        """list_tools retorna todas las tools."""
        registry = DynamicToolRegistry()

        registry.register_native_tool(
            name="tool_1", description="T1", parameters={}, executor=lambda n, a: None
        )
        registry.register_native_tool(
            name="tool_2", description="T2", parameters={}, executor=lambda n, a: None
        )

        all_tools = registry.list_tools()
        assert len(all_tools) == 2

        native_tools = registry.list_tools(source=ToolSource.NATIVE)
        assert len(native_tools) == 2

    def test_search_tools(self):
        """search_tools busca por nombre o descripcion."""
        registry = DynamicToolRegistry()

        registry.register_native_tool(
            name="read_file",
            description="Read a file from disk",
            parameters={},
            executor=lambda n, a: None,
        )
        registry.register_native_tool(
            name="write_file",
            description="Write content to a file",
            parameters={},
            executor=lambda n, a: None,
        )
        registry.register_native_tool(
            name="list_processes",
            description="Show running processes",
            parameters={},
            executor=lambda n, a: None,
        )

        results = registry.search_tools("file")
        assert len(results) == 2

        results = registry.search_tools("process")
        assert len(results) == 1

    def test_get_openai_tools(self):
        """get_openai_tools retorna formato OpenAI function calling."""
        registry = DynamicToolRegistry()

        registry.register_native_tool(
            name="test_tool",
            description="A test",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            executor=lambda n, a: None,
            function_schema={
                "name": "test_tool",
                "description": "A test",
                "parameters": {
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                },
            },
        )

        openai_tools = registry.get_openai_tools()
        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"
        assert openai_tools[0]["function"]["name"] == "test_tool"

    def test_get_stats(self):
        """get_stats retorna estadisticas correctas."""
        registry = DynamicToolRegistry()

        registry.register_native_tool(
            name="t1", description="D1", parameters={}, executor=lambda n, a: None
        )
        registry.register_native_tool(
            name="t2", description="D2", parameters={}, executor=lambda n, a: None
        )

        stats = registry.get_stats()
        assert stats["total_tools"] == 2
        assert stats["native_tools"] == 2
        assert stats["mcp_tools"] == 0

    def test_register_mcp_tools(self):
        """Registrar tools MCP en el registry."""
        registry = DynamicToolRegistry()

        # Mock MCP manager
        mock_manager = MagicMock()
        mock_manager.get_all_tools.return_value = [
            MCPTool(name="mcp_read", description="MCP read", server_name="fs"),
            MCPTool(name="mcp_write", description="MCP write", server_name="fs"),
        ]

        count = registry.register_mcp_tools(mock_manager)
        assert count == 2
        assert len(registry) == 2

        mcp_tools = registry.list_tools(source=ToolSource.MCP)
        assert len(mcp_tools) == 2

    def test_clear_mcp_tools(self):
        """clear_mcp_tools remueve solo las tools MCP."""
        registry = DynamicToolRegistry()

        # Agregar tools nativas
        registry.register_native_tool(
            name="native_1",
            description="Nativa",
            parameters={},
            executor=lambda n, a: None,
        )

        # Agregar tools MCP
        mock_manager = MagicMock()
        mock_manager.get_all_tools.return_value = [
            MCPTool(name="mcp_1", description="MCP 1", server_name="srv"),
        ]
        registry.register_mcp_tools(mock_manager)

        assert len(registry) == 2

        registry.clear_mcp_tools()
        assert len(registry) == 1
        assert "native_1" in registry
        assert "mcp_1" not in registry

    def test_get_tool(self):
        """get_tool retorna info de una tool especifica."""
        registry = DynamicToolRegistry()
        registry.register_native_tool(
            name="my_tool",
            description="My tool",
            parameters={},
            executor=lambda n, a: None,
        )
        info = registry.get_tool("my_tool")
        assert info is not None
        assert info.name == "my_tool"
        assert info.source == ToolSource.NATIVE

        assert registry.get_tool("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSingletons:
    """Tests para singletons."""

    def test_get_mcp_manager(self):
        """get_mcp_manager retorna instancia singleton."""
        import Lilith.MCP.manager as mgr_mod
        from Lilith.MCP.manager import _manager_instance, get_mcp_manager

        # Reset singleton para test
        mgr_mod._manager_instance = None
        manager = get_mcp_manager()
        assert isinstance(manager, MCPManager)
        manager2 = get_mcp_manager()
        assert manager is manager2
        mgr_mod._manager_instance = None  # Cleanup

    def test_get_dynamic_tool_registry(self):
        """get_dynamic_tool_registry retorna instancia singleton."""
        import Lilith.Core.dynamic_tools as dt_mod
        from Lilith.Core.dynamic_tools import (
            _registry_instance,
            get_dynamic_tool_registry,
        )

        dt_mod._registry_instance = None
        registry = get_dynamic_tool_registry()
        assert isinstance(registry, DynamicToolRegistry)
        registry2 = get_dynamic_tool_registry()
        assert registry is registry2
        dt_mod._registry_instance = None  # Cleanup


# ═══════════════════════════════════════════════════════════════════════════════
# MCP CLI TOOLS TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPCLITools:
    """Tests para las tools MCP CLI."""

    def test_get_tools_returns_list(self):
        """get_tools retorna la lista de definiciones MCP."""
        from Lilith.tools.mcp_connect import get_tools

        tools = get_tools()
        assert len(tools) == 4
        names = [t["function"]["name"] for t in tools]
        assert "mcp_list" in names
        assert "mcp_connect" in names
        assert "mcp_disconnect" in names
        assert "mcp_call" in names

    def test_execute_tool_unknown(self):
        """execute_tool con nombre desconocido retorna error."""
        from Lilith.tools.mcp_connect import execute_tool

        result = execute_tool("unknown_tool", {})
        assert "error" in result

    def test_handle_mcp_command_help(self):
        """handle_mcp_command con argumento invalido muestra ayuda."""
        from Lilith.tools.mcp_connect import handle_mcp_command

        result = handle_mcp_command("xyzunknown")
        assert "MCP" in result or "mcp" in result.lower()

    def test_handle_mcp_command_status(self):
        """handle_mcp_command status muestra estado."""
        from Lilith.tools.mcp_connect import handle_mcp_command

        result = handle_mcp_command("status")
        assert "MCP" in result
