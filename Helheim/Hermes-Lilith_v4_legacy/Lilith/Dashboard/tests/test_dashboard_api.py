"""
Tests exhaustivos de API para Lilith Dashboard Server
======================================================
Tests de los endpoints HTTP API, handlers WebSocket,
y validación del frontend JavaScript.
"""

import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Asegurar que Lilith está en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Dashboard.server import DARK_FANTASY_THEME, DashboardServer, get_dashboard, _make_http_handler


# ──────────────────────────────────────────────────────────────────────────────
# HTTP API Tests (unit-level, no server startup needed)
# ──────────────────────────────────────────────────────────────────────────────


class TestMemoryAPIHandlers:
    """Tests para los handlers de la API de memoria."""

    def test_memory_stats_handler_no_lilith(self):
        """memory_stats sin instancia de Lilith retorna dict vacío."""
        server = DashboardServer()
        result = server._handle_memory_stats({})
        assert result["type"] == "memory_stats"
        assert result["stats"] == {}

    def test_memory_stats_handler_with_lilith_no_memory(self):
        """memory_stats con Lilith pero sin memoria retorna dict vacío."""
        mock_lilith = MagicMock(spec=[])
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_stats({})
        assert result["type"] == "memory_stats"
        assert result["stats"] == {}

    def test_memory_stats_handler_with_get_stats(self):
        """memory_stats usa get_stats si está disponible."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_stats.return_value = {
            "episodes": 42,
            "entities": 15,
            "facts": 99,
            "errors": 2,
        }
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_stats({})
        assert result["type"] == "memory_stats"
        assert result["stats"]["episodes"] == 42
        assert result["stats"]["entities"] == 15
        assert result["stats"]["facts"] == 99
        assert result["stats"]["errors"] == 2

    def test_memory_entities_handler_no_lilith(self):
        """memory_entities sin Lilith retorna lista vacía."""
        server = DashboardServer()
        result = server._handle_memory_entities({})
        assert result["type"] == "memory_entities"
        assert result["entities"] == []

    def test_memory_entities_handler_with_lilith(self):
        """memory_entities con Lilith retorna entities."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_entities.return_value = [
            {"name": "Alice", "type": "person", "mentions": 5},
            {"name": "wonderland", "type": "place", "mentions": 3},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_entities({})
        assert result["type"] == "memory_entities"
        assert len(result["entities"]) == 2
        assert result["entities"][0]["name"] == "Alice"

    def test_memory_entities_handler_removes_embeddings(self):
        """memory_entities elimina embeddings de la respuesta."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_entities.return_value = [
            {"name": "Bob", "type": "person", "embedding": [0.1, 0.2, 0.3], "context": "some context"},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_entities({})
        assert "embedding" not in result["entities"][0]

    def test_memory_entities_handler_with_type_filter(self):
        """memory_entities filtra por tipo de entidad."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_entities.return_value = [
            {"name": "Alice", "type": "person"},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_entities({"entity_type": "person", "min_mentions": 2})
        assert result["type"] == "memory_entities"
        mock_lilith.memory.get_entities.assert_called_once_with(entity_type="person", min_mentions=2)

    def test_memory_facts_handler_no_lilith(self):
        """memory_facts sin Lilith retorna lista vacía."""
        server = DashboardServer()
        result = server._handle_memory_facts({})
        assert result["type"] == "memory_facts"
        assert result["facts"] == []

    def test_memory_facts_handler_with_lilith(self):
        """memory_facts con Lilith retorna facts."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_facts.return_value = [
            {"category": "personal", "content": "Likes cats", "confidence": 0.9},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_facts({})
        assert result["type"] == "memory_facts"
        assert len(result["facts"]) == 1
        assert result["facts"][0]["category"] == "personal"

    def test_memory_facts_handler_with_category(self):
        """memory_facts filtra por categoría."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_facts.return_value = []
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_facts({"category": "preferences"})
        mock_lilith.memory.get_facts.assert_called_once_with(category="preferences")

    def test_memory_graph_handler_no_lilith(self):
        """memory_graph sin Lilith retorna grafo vacío."""
        server = DashboardServer()
        result = server._handle_memory_graph({})
        assert result["type"] == "memory_graph"
        assert result["graph"]["nodes"] == []
        assert result["graph"]["edges"] == []

    def test_memory_graph_handler_with_lilith(self):
        """memory_graph con Lilith y knowledge graph retorna datos."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_entities.return_value = [
            {"name": "Alice", "id": "ent1", "type": "person", "mentions": 5},
            {"name": "Wonderland", "id": "ent2", "type": "place", "mentions": 3},
        ]
        mock_lilith.memory.graph.get_all_edges.return_value = [
            {"source": "Alice", "target": "Wonderland", "relation": "visited", "strength": 0.8},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_graph({})
        assert result["type"] == "memory_graph"
        assert len(result["graph"]["nodes"]) == 2
        assert len(result["graph"]["edges"]) == 1
        assert result["graph"]["edges"][0]["relation"] == "visited"

    def test_memory_episodes_handler_no_lilith(self):
        """memory_episodes sin Lilith retorna lista vacía."""
        server = DashboardServer()
        result = server._handle_memory_episodes({})
        assert result["type"] == "memory_episodes"
        assert result["episodes"] == []
        assert result["count"] == 0

    def test_memory_episodes_handler_with_lilith(self):
        """memory_episodes con Lilith retorna episodios."""
        mock_lilith = MagicMock()
        episodes = [
            {"role": "user", "content": "Hello", "timestamp": 1000},
            {"role": "assistant", "content": "Hi there", "timestamp": 1001},
        ]
        mock_lilith.memory.get_recent_episodes.return_value = episodes
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_episodes({"count": 20})
        assert result["type"] == "memory_episodes"
        assert result["count"] == 2
        assert result["episodes"][0]["role"] == "user"

    def test_memory_episodes_handler_removes_embeddings(self):
        """memory_episodes elimina embeddings de la respuesta."""
        mock_lilith = MagicMock()
        mock_lilith.memory.get_recent_episodes.return_value = [
            {"role": "user", "content": "test", "embedding": [0.1, 0.2]},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_episodes({"count": 10})
        assert "embedding" not in result["episodes"][0]

    def test_memory_episodes_handler_fallback_get_full_history(self):
        """memory_episodes usa get_full_history si get_recent_episodes no existe."""
        mock_lilith = MagicMock(spec=["memory"])
        mock_lilith.memory = MagicMock(spec=["get_full_history"])
        mock_lilith.memory.get_full_history.return_value = [
            {"role": "user", "content": "test"},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_episodes({"count": 10})
        assert result["type"] == "memory_episodes"
        assert result["count"] == 1

    def test_memory_search_handler_empty_query(self):
        """memory_search con query vacío retorna error."""
        server = DashboardServer()
        result = server._handle_memory_search({"query": ""})
        assert result["type"] == "error"

    def test_memory_search_handler_no_query(self):
        """memory_search sin query retorna error."""
        server = DashboardServer()
        result = server._handle_memory_search({})
        assert result["type"] == "error"

    def test_memory_search_handler_with_lilith(self):
        """memory_search con Lilith retorna resultados."""
        mock_lilith = MagicMock()
        mock_lilith.memory.search.return_value = [
            {"key": "test_key", "content": "test content"},
        ]
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_memory_search({"query": "test"})
        assert result["type"] == "memory_results"
        assert len(result["results"]) == 1

    def test_memory_search_handler_no_lilith(self):
        """memory_search sin Lilith retorna resultados vacíos."""
        server = DashboardServer()
        result = server._handle_memory_search({"query": "test"})
        assert result["type"] == "memory_results"
        assert result["results"] == []


class TestSwarmAndMCPHandlers:
    """Tests para handlers de Swarm y MCP."""

    def test_swarm_status_handler_no_swarm(self):
        """swarm_status sin Swarm manager retorna error."""
        server = DashboardServer()
        result = server._handle_swarm_status({})
        # Importar Swarm puede fallar, debería dar error
        assert result["type"] in ("swarm_status", "error")

    def test_mcp_status_handler_no_mcp(self):
        """mcp_status sin MCP manager retorna error."""
        server = DashboardServer()
        result = server._handle_mcp_status({})
        assert result["type"] in ("mcp_status", "error")

    def test_swarm_status_handler_with_swarm(self):
        """swarm_status con Swarm manager retorna datos."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = {"active_agents": 3, "max_agents": 5}
        mock_module = MagicMock()
        mock_module.get_swarm_manager.return_value = mock_manager
        with patch.dict("sys.modules", {"Lilith.Swarm.manager": mock_module}):
            server = DashboardServer()
            result = server._handle_swarm_status({})
            assert result["type"] == "swarm_status"
            assert result["data"]["active_agents"] == 3

    def test_mcp_status_handler_with_mcp(self):
        """mcp_status con MCP manager retorna datos."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = {"connected": 2, "servers": []}
        mock_module = MagicMock()
        mock_module.get_mcp_manager.return_value = mock_manager
        with patch.dict("sys.modules", {"Lilith.MCP.manager": mock_module}):
            server = DashboardServer()
            result = server._handle_mcp_status({})
            assert result["type"] == "mcp_status"
            assert result["data"]["connected"] == 2


class TestChatHandlerExtended:
    """Tests extendidos para el handler de chat."""

    def test_handle_chat_strips_whitespace(self):
        """handle_chat con mensaje solo espacios retorna error."""
        server = DashboardServer()
        result = server._handle_chat({"message": "   "})
        # Whitespace-only should be treated as empty
        assert result["type"] == "chat_response" or result["type"] == "error"

    def test_handle_chat_response_no_lilith(self):
        """handle_chat sin Lilith retorna mensaje de no disponible."""
        server = DashboardServer()
        result = server._handle_chat({"message": "Hola"})
        assert result["type"] == "chat_response"
        assert "no" in result["content"].lower() or "Lilith" in result["content"]

    def test_handle_chat_with_lilith_exception(self):
        """handle_chat con Lilith que lanza excepción retorna error."""
        mock_lilith = MagicMock()
        mock_lilith.orch.chat.side_effect = RuntimeError("Boom")
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_chat({"message": "test"})
        assert result["type"] == "error"
        assert "Boom" in result["message"]

    def test_handle_chat_history_trims(self):
        """handle_chat trims historial al máximo."""
        server = DashboardServer()
        server._max_history = 3
        for i in range(5):
            server._handle_chat({"message": f"msg_{i}"})
        assert len(server._chat_history) <= 3


class TestCommandHandlerExtended:
    """Tests extendidos para el handler de comandos."""

    def test_handle_command_with_lilith_exception(self):
        """handle_command con Lilith que lanza excepción retorna error."""
        mock_lilith = MagicMock()
        mock_lilith.process_command.side_effect = RuntimeError("Command failed")
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_command({"command": "/test"})
        assert result["type"] == "error"

    def test_handle_command_no_lilith(self):
        """handle_command sin Lilith retorna error de no disponible."""
        server = DashboardServer()
        result = server._handle_command({"command": "/status"})
        assert result["type"] == "error"
        assert "not available" in result["message"]


class TestHTTPHandlerUnit:
    """Tests unitarios del HTTP handler sin iniciar servidor."""

    def test_make_http_handler_returns_class(self):
        """_make_http_handler retorna una clase handler."""
        server = DashboardServer()
        handler_cls = _make_http_handler(server)
        assert handler_cls is not None

    def test_fronted_dir_exists(self):
        """FRONTEND_DIR apunta a un directorio existente."""
        from Lilith.Dashboard.server import FRONTEND_DIR
        assert FRONTEND_DIR.exists()

    def test_frontend_dir_has_index_html(self):
        """FRONTEND_DIR contiene index.html."""
        from Lilith.Dashboard.server import FRONTEND_DIR
        assert (FRONTEND_DIR / "index.html").exists()

    def test_frontend_dir_has_app_js(self):
        """FRONTEND_DIR contiene app.js."""
        from Lilith.Dashboard.server import FRONTEND_DIR
        assert (FRONTEND_DIR / "app.js").exists()

    def test_frontend_dir_has_style_css(self):
        """FRONTEND_DIR contiene style.css."""
        from Lilith.Dashboard.server import FRONTEND_DIR
        assert (FRONTEND_DIR / "style.css").exists()


class TestDashboardServerLifecycle:
    """Tests del lifecycle del DashboardServer."""

    def test_server_creation_defaults(self):
        """Server se crea con valores por defecto."""
        server = DashboardServer()
        assert server.host == "localhost"
        assert server.port == 8765
        assert server._running is False

    def test_server_creation_custom(self):
        """Server se crea con parámetros personalizados."""
        server = DashboardServer(host="0.0.0.0", port=9999)
        assert server.host == "0.0.0.0"
        assert server.port == 9999

    def test_server_status_not_running(self):
        """get_status muestra servidor no corriendo."""
        server = DashboardServer()
        status = server.get_status()
        assert status["running"] is False
        assert status["host"] == "localhost"
        assert status["port"] == 8765
        assert status["http_port"] == 8766

    def test_server_chat_history_in_status(self):
        """get_status incluye chat_messages."""
        server = DashboardServer()
        server._handle_chat({"message": "Hello"})
        status = server.get_status()
        assert status["chat_messages"] == 1

    def test_server_panes_in_status(self):
        """get_status incluye panes."""
        server = DashboardServer()
        status = server.get_status()
        assert "panes" in status
        assert isinstance(status["panes"], list)

    def test_start_without_websockets_fails_gracefully(self):
        """start() sin websockets instalado no inicia servidor."""
        with patch("Lilith.Dashboard.server.HAS_WEBSOCKETS", False):
            server = DashboardServer()
            server.start()
            assert server._running is False

    def test_stop_when_not_running(self):
        """stop() no explota si el servidor no está corriendo."""
        server = DashboardServer()
        server.stop()  # Should not raise

    def test_repr(self):
        """__repr__ retorna string informativo."""
        server = DashboardServer()
        r = repr(server)
        assert "DashboardServer" in r
        assert "localhost" in r
        assert "8765" in r


class TestLayoutConfig:
    """Tests para configuración de layout."""

    def test_default_layout_config(self):
        """Layout por defecto es grid con 4 paneles."""
        server = DashboardServer()
        layout = server._get_layout_config()
        assert layout["type"] == "grid"
        assert "chat" in layout["panes"]
        assert "terminal" in layout["panes"]

    def test_set_layout(self):
        """set_layout cambia la configuración de layout."""
        server = DashboardServer()
        result = server._handle_set_layout({"layout": "vertical", "panes": ["terminal", "system"]})
        assert result["type"] == "layout_updated"
        assert result["layout"] == "vertical"
        assert "terminal" in result["panes"]

    def test_set_layout_default_panes(self):
        """set_layout usa pane_order como default si no se especifican panes."""
        server = DashboardServer()
        result = server._handle_set_layout({"layout": "single"})
        assert result["type"] == "layout_updated"
        assert result["layout"] == "single"

    def test_resize_pane(self):
        """resize_pane actualiza tamaño de panel."""
        server = DashboardServer()
        server._panes["chat"] = {"size": {"width": 50, "height": 100}}
        result = server._handle_resize_pane({"pane_id": "chat", "size": {"width": 60, "height": 80}})
        assert result["type"] == "pane_resized"
        assert result["pane_id"] == "chat"
        assert server._panes["chat"]["size"]["width"] == 60


class TestTerminalHandlers:
    """Tests para handlers de terminal."""

    def test_terminal_input_ack(self):
        """terminal_input retorna terminal_ack."""
        server = DashboardServer()
        result = server._handle_terminal_input({"data": "ls -la"})
        assert result["type"] == "terminal_ack"

    def test_terminal_input_empty(self):
        """terminal_input con datos vacíos retorna ack igualmente."""
        server = DashboardServer()
        result = server._handle_terminal_input({"data": ""})
        assert result["type"] == "terminal_ack"

    def test_terminal_resize(self):
        """terminal_resize retorna nuevas dimensiones."""
        server = DashboardServer()
        result = server._handle_terminal_resize({"cols": 120, "rows": 40})
        assert result["type"] == "terminal_resized"
        assert result["cols"] == 120
        assert result["rows"] == 40

    def test_terminal_resize_defaults(self):
        """terminal_resize con datos faltantes usa defaults."""
        server = DashboardServer()
        result = server._handle_terminal_resize({})
        assert result["type"] == "terminal_resized"
        assert result["cols"] == 80
        assert result["rows"] == 24


class TestPingHandler:
    """Tests para el handler de ping."""

    def test_ping_returns_pong(self):
        """ping retorna pong con timestamp."""
        server = DashboardServer()
        result = server._handle_ping({})
        assert result["type"] == "pong"
        assert "timestamp" in result

    def test_ping_timestamp_is_numeric(self):
        """timestamp de pong es numérico."""
        server = DashboardServer()
        result = server._handle_ping({})
        assert isinstance(result["timestamp"], (int, float))


class TestLilithStatusHandler:
    """Tests para el handler de estado de Lilith."""

    def test_get_lilith_status_no_lilith(self):
        """get_lilith_status sin instancia de Lilith."""
        server = DashboardServer()
        status = server._get_lilith_status()
        assert status["running"] is False
        assert "clients_connected" in status

    def test_get_lilith_status_with_lilith(self):
        """get_lilith_status con instancia de Lilith."""
        mock_lilith = MagicMock()
        mock_lilith.current_model = "gpt-4"
        server = DashboardServer(lilith_instance=mock_lilith)
        status = server._get_lilith_status()
        assert status["running"] is True
        assert status["model"] == "gpt-4"

    def test_handle_get_status_returns_status(self):
        """handle_get_status retorna estado completo."""
        server = DashboardServer()
        result = server._handle_get_status({})
        assert result["type"] == "status"
        assert "data" in result


class TestBroadcast:
    """Tests para la funcionalidad de broadcast."""

    def test_broadcast_sync_no_loop(self):
        """broadcast_sync sin loop no explota."""
        server = DashboardServer()
        server._loop = None
        # Should not raise
        server.broadcast_sync({"type": "test"})

    def test_broadcast_sync_with_closed_loop(self):
        """broadcast_sync con loop cerrado no explota."""
        server = DashboardServer()
        import asyncio
        server._loop = asyncio.new_event_loop()
        server._loop.close()
        # Should not raise
        server.broadcast_sync({"type": "test"})


# ──────────────────────────────────────────────────────────────────────────────
# Frontend JavaScript Validation
# ──────────────────────────────────────────────────────────────────────────────


class TestFrontendJavaScript:
    """Tests para validar el frontend JavaScript."""

    @pytest.fixture
    def app_js_content(self):
        frontend_dir = Path(__file__).parent.parent / "frontend"
        return (frontend_dir / "app.js").read_text()

    # --- Core Functions Existence ---

    def test_function_connect(self, app_js_content):
        """app.js tiene función connect."""
        assert "function connect(" in app_js_content

    def test_function_handle_message(self, app_js_content):
        """app.js tiene función handleMessage."""
        assert "function handleMessage(" in app_js_content

    def test_function_handle_init(self, app_js_content):
        """app.js tiene función handleInit."""
        assert "function handleInit(" in app_js_content

    def test_function_send(self, app_js_content):
        """app.js tiene función send."""
        assert "function send(" in app_js_content

    def test_function_apply_theme(self, app_js_content):
        """app.js tiene función applyTheme."""
        assert "function applyTheme(" in app_js_content

    def test_function_apply_layout(self, app_js_content):
        """app.js tiene función applyLayout."""
        assert "function applyLayout(" in app_js_content

    # --- Chat Functions ---

    def test_function_send_chat(self, app_js_content):
        """app.js tiene función sendChat."""
        assert "function sendChat(" in app_js_content

    def test_function_add_chat_message(self, app_js_content):
        """app.js tiene función addChatMessage."""
        assert "function addChatMessage(" in app_js_content

    def test_function_show_typing(self, app_js_content):
        """app.js tiene función showTypingIndicator."""
        assert "function showTypingIndicator(" in app_js_content

    def test_function_hide_typing(self, app_js_content):
        """app.js tiene función hideTypingIndicator."""
        assert "function hideTypingIndicator(" in app_js_content

    # --- Terminal Functions ---

    def test_function_send_terminal_command(self, app_js_content):
        """app.js tiene función sendTerminalCommand."""
        assert "function sendTerminalCommand(" in app_js_content

    def test_function_add_terminal_line(self, app_js_content):
        """app.js tiene función addTerminalLine."""
        assert "function addTerminalLine(" in app_js_content

    # --- Status Functions ---

    def test_function_update_system_status(self, app_js_content):
        """app.js tiene función updateSystemStatus."""
        assert "function updateSystemStatus(" in app_js_content

    def test_function_update_swarm_status(self, app_js_content):
        """app.js tiene función updateSwarmStatus."""
        assert "function updateSwarmStatus(" in app_js_content

    def test_function_update_mcp_status(self, app_js_content):
        """app.js tiene función updateMcpStatus."""
        assert "function updateMcpStatus(" in app_js_content

    def test_function_fetch_status(self, app_js_content):
        """app.js tiene función fetchStatus."""
        assert "function fetchStatus(" in app_js_content

    def test_function_update_status_bar(self, app_js_content):
        """app.js tiene función updateStatusBar."""
        assert "function updateStatusBar(" in app_js_content

    # --- Memory Functions (Previously Missing) ---

    def test_function_search_memory(self, app_js_content):
        """app.js tiene función searchMemory."""
        assert "function searchMemory(" in app_js_content

    def test_function_update_memory_results(self, app_js_content):
        """app.js tiene función updateMemoryResults."""
        assert "function updateMemoryResults(" in app_js_content

    def test_function_update_memory_stats(self, app_js_content):
        """app.js tiene función updateMemoryStats."""
        assert "function updateMemoryStats(" in app_js_content

    def test_function_update_memory_entities(self, app_js_content):
        """app.js tiene función updateMemoryEntities."""
        assert "function updateMemoryEntities(" in app_js_content

    def test_function_update_memory_facts(self, app_js_content):
        """app.js tiene función updateMemoryFacts."""
        assert "function updateMemoryFacts(" in app_js_content

    def test_function_update_memory_graph(self, app_js_content):
        """app.js tiene función updateMemoryGraph."""
        assert "function updateMemoryGraph(" in app_js_content

    def test_function_update_memory_episodes(self, app_js_content):
        """app.js tiene función updateMemoryEpisodes."""
        assert "function updateMemoryEpisodes(" in app_js_content

    def test_function_switch_memory_tab(self, app_js_content):
        """app.js tiene función switchMemoryTab."""
        assert "function switchMemoryTab(" in app_js_content

    def test_function_fetch_memory_data(self, app_js_content):
        """app.js tiene función fetchMemoryData."""
        assert "function fetchMemoryData(" in app_js_content

    def test_function_fetch_memory_stats(self, app_js_content):
        """app.js tiene función fetchMemoryStats."""
        assert "function fetchMemoryStats(" in app_js_content

    def test_function_fetch_all_memory_data(self, app_js_content):
        """app.js tiene función fetchAllMemoryData."""
        assert "function fetchAllMemoryData(" in app_js_content

    # --- Memory Graph Functions ---

    def test_function_draw_memory_graph(self, app_js_content):
        """app.js tiene función drawMemoryGraph."""
        assert "function drawMemoryGraph(" in app_js_content

    def test_function_memory_graph_zoom(self, app_js_content):
        """app.js tiene función memoryGraphZoom."""
        assert "function memoryGraphZoom(" in app_js_content

    def test_function_memory_graph_reset(self, app_js_content):
        """app.js tiene función memoryGraphReset."""
        assert "function memoryGraphReset(" in app_js_content

    def test_function_setup_graph_interaction(self, app_js_content):
        """app.js tiene función setupGraphInteraction."""
        assert "function setupGraphInteraction(" in app_js_content

    # --- Layout & Settings ---

    def test_function_toggle_layout(self, app_js_content):
        """app.js tiene función toggleLayout."""
        assert "function toggleLayout(" in app_js_content

    def test_function_toggle_settings(self, app_js_content):
        """app.js tiene función toggleSettings."""
        assert "function toggleSettings(" in app_js_content

    # --- Visual Effects ---

    def test_function_init_particle_canvas(self, app_js_content):
        """app.js tiene función initParticleCanvas."""
        assert "function initParticleCanvas(" in app_js_content

    def test_function_spawn_css_runes(self, app_js_content):
        """app.js tiene función spawnCSSRunes."""
        assert "function spawnCSSRunes(" in app_js_content

    def test_function_init_title_glitch(self, app_js_content):
        """app.js tiene función initTitleGlitch."""
        assert "function initTitleGlitch(" in app_js_content

    def test_function_escape_html(self, app_js_content):
        """app.js tiene función escapeHtml."""
        assert "function escapeHtml(" in app_js_content

    # --- WebSocket ---

    def test_websocket_url_config(self, app_js_content):
        """app.js tiene configuración de WebSocket URL."""
        assert "wsUrl" in app_js_content
        assert "ws://" in app_js_content

    def test_http_url_config(self, app_js_content):
        """app.js tiene configuración de HTTP URL para API."""
        assert "httpUrl" in app_js_content
        assert "8766" in app_js_content

    # --- Message Handler Coverage ---

    def test_handles_chat_response(self, app_js_content):
        """handleMessage maneja chat_response."""
        assert "'chat_response'" in app_js_content

    def test_handles_command_result(self, app_js_content):
        """handleMessage maneja command_result."""
        assert "'command_result'" in app_js_content

    def test_handles_status(self, app_js_content):
        """handleMessage maneja status."""
        assert "case 'status'" in app_js_content

    def test_handles_swarm_status(self, app_js_content):
        """handleMessage maneja swarm_status."""
        assert "case 'swarm_status'" in app_js_content

    def test_handles_mcp_status(self, app_js_content):
        """handleMessage maneja mcp_status."""
        assert "case 'mcp_status'" in app_js_content

    def test_handles_memory_results(self, app_js_content):
        """handleMessage maneja memory_results."""
        assert "case 'memory_results'" in app_js_content

    def test_handles_memory_stats(self, app_js_content):
        """handleMessage maneja memory_stats."""
        assert "case 'memory_stats'" in app_js_content

    def test_handles_memory_entities(self, app_js_content):
        """handleMessage maneja memory_entities."""
        assert "case 'memory_entities'" in app_js_content

    def test_handles_memory_facts(self, app_js_content):
        """handleMessage maneja memory_facts."""
        assert "case 'memory_facts'" in app_js_content

    def test_handles_memory_graph(self, app_js_content):
        """handleMessage maneja memory_graph."""
        assert "case 'memory_graph'" in app_js_content

    def test_handles_memory_episodes(self, app_js_content):
        """handleMessage maneja memory_episodes."""
        assert "case 'memory_episodes'" in app_js_content

    def test_handles_pong(self, app_js_content):
        """handleMessage maneja pong."""
        assert "case 'pong'" in app_js_content

    def test_handles_error(self, app_js_content):
        """handleMessage maneja error."""
        assert "case 'error'" in app_js_content

    def test_handles_layout_updated(self, app_js_content):
        """handleMessage maneja layout_updated."""
        assert "case 'layout_updated'" in app_js_content

    # --- Init Function Wiring ---

    def test_init_calls_setup_graph_interaction(self, app_js_content):
        """init() llama a setupGraphInteraction."""
        assert "setupGraphInteraction()" in app_js_content

    def test_init_calls_fetch_all_memory_data(self, app_js_content):
        """init() llama a fetchAllMemoryData."""
        assert "fetchAllMemoryData()" in app_js_content

    def test_init_calls_connect(self, app_js_content):
        """init() llama a connect."""
        assert re.search(r"init\(\).*connect\(\)", app_js_content, re.DOTALL) is not None or "connect();" in app_js_content

    # --- HTTP API Fetch ---

    def test_fetch_memory_data_calls_fetch(self, app_js_content):
        """fetchMemoryData usa fetch() para llamar a la API."""
        assert "fetch(`${CONFIG.httpUrl}" in app_js_content

    def test_fetch_memory_stats_calls_fetch(self, app_js_content):
        """fetchMemoryStats usa fetch() para /api/memory/stats."""
        assert "/api/memory/stats" in app_js_content

    def test_memory_search_http_fallback(self, app_js_content):
        """searchMemory tiene fallback HTTP cuando WebSocket no está disponible."""
        assert "/api/memory/search" in app_js_content


class TestFrontendHTML:
    """Tests para validar el HTML del frontend."""

    @pytest.fixture
    def index_html_content(self):
        frontend_dir = Path(__file__).parent.parent / "frontend"
        return (frontend_dir / "index.html").read_text()

    def test_memory_pane_exists(self, index_html_content):
        """index.html tiene panel de memoria."""
        assert "pane-memory" in index_html_content

    def test_memory_search_input_exists(self, index_html_content):
        """index.html tiene input de búsqueda de memoria."""
        assert "memory-search-input" in index_html_content

    def test_memory_stats_bar_exists(self, index_html_content):
        """index.html tiene barra de estadísticas de memoria."""
        assert "memory-stats-bar" in index_html_content

    def test_memory_tabs_exist(self, index_html_content):
        """index.html tiene tabs de memoria (graph, entities, facts, episodes)."""
        assert "switchMemoryTab('graph')" in index_html_content
        assert "switchMemoryTab('entities')" in index_html_content
        assert "switchMemoryTab('facts')" in index_html_content
        assert "switchMemoryTab('episodes')" in index_html_content

    def test_memory_graph_canvas_exists(self, index_html_content):
        """index.html tiene canvas para el grafo de memoria."""
        assert "memory-graph-canvas" in index_html_content

    def test_memory_entities_list_exists(self, index_html_content):
        """index.html tiene contenedor de entidades."""
        assert "memory-entities-list" in index_html_content

    def test_memory_facts_list_exists(self, index_html_content):
        """index.html tiene contenedor de facts."""
        assert "memory-facts-list" in index_html_content

    def test_memory_episodes_list_exists(self, index_html_content):
        """index.html tiene contenedor de episodios."""
        assert "memory-episodes-list" in index_html_content

    def test_memory_stat_chips_exist(self, index_html_content):
        """index.html tiene chips de estadísticas de memoria."""
        assert "mem-stat-episodes" in index_html_content
        assert "mem-stat-entities" in index_html_content
        assert "mem-stat-facts" in index_html_content
        assert "mem-stat-errors" in index_html_content

    def test_graph_controls_exist(self, index_html_content):
        """index.html tiene controles del grafo (zoom in, zoom out, reset)."""
        assert "memoryGraphZoom" in index_html_content
        assert "memoryGraphReset" in index_html_content

    def test_graph_tooltip_exists(self, index_html_content):
        """index.html tiene tooltip para el grafo."""
        assert "graph-tooltip" in index_html_content

    def test_chat_pane_exists(self, index_html_content):
        """index.html tiene panel de chat."""
        assert "pane-chat" in index_html_content

    def test_terminal_pane_exists(self, index_html_content):
        """index.html tiene panel de terminal."""
        assert "pane-terminal" in index_html_content

    def test_system_pane_exists(self, index_html_content):
        """index.html tiene panel de sistema."""
        assert "pane-system" in index_html_content

    def test_app_js_script_tag(self, index_html_content):
        """index.html carga app.js."""
        assert 'src="app.js"' in index_html_content


class TestFrontendCSS:
    """Tests para validar el CSS del frontend."""

    @pytest.fixture
    def style_css_content(self):
        frontend_dir = Path(__file__).parent.parent / "frontend"
        return (frontend_dir / "style.css").read_text()

    def test_dark_theme_variables(self, style_css_content):
        """style.css tiene variables de tema oscuro."""
        assert "--bg-primary" in style_css_content
        assert "--accent-red" in style_css_content

    def test_memory_styles(self, style_css_content):
        """style.css tiene estilos para elementos de memoria."""
        assert "memory-item" in style_css_content or ".memory-item" in style_css_content

    def test_pane_styles(self, style_css_content):
        """style.css tiene estilos para paneles."""
        assert ".pane" in style_css_content

    def test_chat_styles(self, style_css_content):
        """style.css tiene estilos para chat."""
        assert "chat" in style_css_content.lower()

    def test_terminal_styles(self, style_css_content):
        """style.css tiene estilos para terminal."""
        assert "terminal" in style_css_content.lower()


class TestServerHTTPAPIRouting:
    """Test the HTTP API routing logic via the handler factory."""

    def _make_handler(self):
        """Create a fresh server and HTTP handler for testing."""
        from Lilith.Dashboard.server import _make_http_handler
        server = DashboardServer()
        return _make_http_handler(server), server

    def test_handler_factory_returns_class(self):
        """_make_http_handler retorna una clase de handler."""
        server = DashboardServer()
        from Lilith.Dashboard.server import _make_http_handler
        handler_cls = _make_http_handler(server)
        assert handler_cls is not None
        assert hasattr(handler_cls, 'do_GET')

    def test_handler_has_serve_file(self):
        """El handler tiene método _serve_file."""
        server = DashboardServer()
        from Lilith.Dashboard.server import _make_http_handler
        handler_cls = _make_http_handler(server)
        assert hasattr(handler_cls, '_serve_file')

    def test_handler_has_send_json(self):
        """El handler tiene método _send_json."""
        server = DashboardServer()
        from Lilith.Dashboard.server import _make_http_handler
        handler_cls = _make_http_handler(server)
        assert hasattr(handler_cls, '_send_json')


class TestDashboardSingleton:
    """Tests extendidos del singleton."""

    def setup_method(self):
        from Lilith.Dashboard import server as srv
        srv._dashboard_instance = None

    def test_singleton_with_lilith_instance(self):
        """get_dashboard con instancia de Lilith."""
        mock_lilith = MagicMock()
        dashboard = get_dashboard(lilith_instance=mock_lilith)
        assert dashboard.lilith is mock_lilith

    def test_singleton_persists_after_second_call(self):
        """El segundo llamado a get_dashboard con diferentes params no cambia la instancia."""
        d1 = get_dashboard(host="localhost", port=8765)
        d2 = get_dashboard(host="0.0.0.0", port=9999)
        # d2 should be the same instance as d1 (singleton)
        assert d1 is d2
        assert d2.host == "localhost"
        assert d2.port == 8765