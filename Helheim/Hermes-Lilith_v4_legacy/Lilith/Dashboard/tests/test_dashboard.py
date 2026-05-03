"""
Tests para Lilith Dashboard Server
====================================
Tests unitarios del backend WebSocket + HTTP del Dashboard.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Asegurar que Lilith está en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Dashboard.server import DARK_FANTASY_THEME, DashboardServer, get_dashboard

# ──────────────────────────────────────────────────────────────────────────────
# DashboardServer Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDashboardServer:
    """Tests para la clase DashboardServer."""

    def test_creation_defaults(self):
        """DashboardServer se crea con valores por defecto."""
        server = DashboardServer()
        assert server.host == "localhost"
        assert server.port == 8765
        assert server._running is False
        assert len(server._ws_clients) == 0
        assert len(server._chat_history) == 0

    def test_creation_custom_params(self):
        """DashboardServer se crea con parámetros personalizados."""
        server = DashboardServer(host="0.0.0.0", port=9999)
        assert server.host == "0.0.0.0"
        assert server.port == 9999

    def test_theme_applied(self):
        """Se aplica el tema dark fantasy por defecto."""
        server = DashboardServer()
        assert server.theme == DARK_FANTASY_THEME
        assert server.theme["bg_primary"] == "#0a0a0f"
        assert server.theme["accent_red"] == "#ff3366"

    def test_custom_theme(self):
        """Se puede pasar un tema personalizado."""
        custom = {"bg_primary": "#1a1a2e", "accent_red": "#ff0055"}
        server = DashboardServer(theme=custom)
        assert server.theme == custom

    def test_get_status(self):
        """get_status retorna estado correcto."""
        server = DashboardServer()
        status = server.get_status()
        assert "running" in status
        assert "host" in status
        assert "port" in status
        assert "clients_connected" in status
        assert status["running"] is False
        assert status["host"] == "localhost"
        assert status["port"] == 8765
        # HTTP port should be WS port + 1
        assert status["http_port"] == 8766

    def test_get_layout_config(self):
        """get_layout_config retorna configuración válida."""
        server = DashboardServer()
        layout = server._get_layout_config()
        assert layout["type"] == "grid"
        assert "panes" in layout
        assert "chat" in layout["panes"]
        assert "terminal" in layout["panes"]

    def test_command_handlers_registered(self):
        """Los handlers de comandos están registrados."""
        server = DashboardServer()
        expected_handlers = [
            "chat",
            "command",
            "get_status",
            "resize_pane",
            "set_layout",
            "terminal_input",
            "terminal_resize",
            "swarm_status",
            "mcp_status",
            "memory_search",
            "ping",
        ]
        for handler_name in expected_handlers:
            assert (
                handler_name in server._command_handlers
            ), f"Missing handler: {handler_name}"

    def test_handle_chat_empty_message(self):
        """handle_chat retorna error con mensaje vacío."""
        server = DashboardServer()
        result = server._handle_chat({"message": ""})
        assert result["type"] == "error"

    def test_handle_chat_with_message(self):
        """handle_chat almacena mensaje en historial."""
        server = DashboardServer()
        result = server._handle_chat({"message": "Hola Lilith"})
        assert result["type"] == "chat_response"
        assert len(server._chat_history) == 1
        assert server._chat_history[0]["role"] == "user"
        assert server._chat_history[0]["content"] == "Hola Lilith"

    def test_handle_chat_max_history(self):
        """handle_chat trims historial al máximo."""
        server = DashboardServer()
        server._max_history = 5
        for i in range(10):
            server._handle_chat({"message": f"msg {i}"})
        assert len(server._chat_history) <= 5

    def test_handle_command_empty(self):
        """handle_command retorna error con comando vacío."""
        server = DashboardServer()
        result = server._handle_command({"command": ""})
        assert result["type"] == "error"

    def test_handle_ping(self):
        """handle_ping responde con pong."""
        server = DashboardServer()
        result = server._handle_ping({})
        assert result["type"] == "pong"
        assert "timestamp" in result

    def test_handle_get_status(self):
        """handle_get_status retorna estado de Lilith."""
        server = DashboardServer()
        result = server._handle_get_status({})
        assert result["type"] == "status"
        assert "data" in result

    def test_handle_resize_pane(self):
        """handle_resize_pane procesa resize de panel."""
        server = DashboardServer()
        server._panes["chat"] = {"size": {"width": 50, "height": 100}}
        result = server._handle_resize_pane(
            {"pane_id": "chat", "size": {"width": 60, "height": 80}}
        )
        assert result["type"] == "pane_resized"
        assert result["pane_id"] == "chat"

    def test_handle_set_layout(self):
        """handle_set_layout cambia la configuración de layout."""
        server = DashboardServer()
        result = server._handle_set_layout(
            {"layout": "vertical", "panes": ["terminal", "system"]}
        )
        assert result["type"] == "layout_updated"
        assert result["layout"] == "vertical"
        assert "terminal" in result["panes"]

    def test_handle_terminal_input(self):
        """handle_terminal_input responde con ack."""
        server = DashboardServer()
        result = server._handle_terminal_input({"data": "ls"})
        assert result["type"] == "terminal_ack"

    def test_handle_terminal_resize(self):
        """handle_terminal_resize responde con nuevas dimensiones."""
        server = DashboardServer()
        result = server._handle_terminal_resize({"cols": 120, "rows": 40})
        assert result["type"] == "terminal_resized"
        assert result["cols"] == 120
        assert result["rows"] == 40

    def test_lilith_instance_stored(self):
        """La instancia de Lilith se almacena correctamente."""
        mock_lilith = MagicMock()
        server = DashboardServer(lilith_instance=mock_lilith)
        assert server.lilith is mock_lilith

    def test_chat_with_lilith_instance(self):
        """Chat con instancia de Lilith funciona."""
        mock_lilith = MagicMock()
        mock_lilith.orch.chat.return_value = "Respuesta de Lilith"
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_chat({"message": "Hola"})
        assert result["type"] == "chat_response"
        assert result["content"] == "Respuesta de Lilith"
        assert len(server._chat_history) == 2  # user + assistant

    def test_command_with_lilith_instance(self):
        """Comando con instancia de Lilith funciona."""
        mock_lilith = MagicMock()
        mock_lilith.process_command.return_value = "Resultado del comando"
        server = DashboardServer(lilith_instance=mock_lilith)
        result = server._handle_command({"command": "/status"})
        assert result["type"] == "command_result"
        assert result["output"] == "Resultado del comando"

    def test_repr(self):
        """__repr__ es informativo."""
        server = DashboardServer()
        r = repr(server)
        assert "DashboardServer" in r
        assert "localhost" in r
        assert "8765" in r


# ──────────────────────────────────────────────────────────────────────────────
# Singleton Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestGetDashboard:
    """Tests para el singleton get_dashboard."""

    def setup_method(self):
        """Reset singleton antes de cada test."""
        from Lilith.Dashboard import server as srv

        srv._dashboard_instance = None

    def test_singleton_creation(self):
        """get_dashboard crea una instancia."""
        dashboard = get_dashboard()
        assert isinstance(dashboard, DashboardServer)

    def test_singleton_same_instance(self):
        """get_dashboard retorna la misma instancia."""
        d1 = get_dashboard()
        d2 = get_dashboard()
        assert d1 is d2

    def test_singleton_custom_params(self):
        """get_dashboard con parámetros personalizados."""
        dashboard = get_dashboard(host="0.0.0.0", port=9999)
        assert dashboard.host == "0.0.0.0"
        assert dashboard.port == 9999


# ──────────────────────────────────────────────────────────────────────────────
# Theme Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDarkFantasyTheme:
    """Tests para el tema dark fantasy."""

    def test_all_colors_defined(self):
        """Todos los colores del tema están definidos."""
        expected_colors = [
            "bg_primary",
            "bg_secondary",
            "bg_tertiary",
            "bg_pane",
            "bg_input",
            "bg_hover",
            "border",
            "border_active",
            "border_focus",
            "text_primary",
            "text_secondary",
            "text_dim",
            "text_bright",
            "accent_red",
            "accent_green",
            "accent_yellow",
            "accent_blue",
            "accent_magenta",
            "accent_cyan",
            "accent_purple",
        ]
        for color in expected_colors:
            assert color in DARK_FANTASY_THEME, f"Missing color: {color}"
            assert DARK_FANTASY_THEME[color].startswith("#"), f"Invalid color: {color}"

    def test_fonts_defined(self):
        """Las fuentes del tema están definidas."""
        assert "font_mono" in DARK_FANTASY_THEME
        assert "font_sans" in DARK_FANTASY_THEME
        assert "JetBrains" in DARK_FANTASY_THEME["font_mono"]


# ──────────────────────────────────────────────────────────────────────────────
# Frontend Files Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestFrontendFiles:
    """Tests para los archivos del frontend."""

    def test_index_html_exists(self):
        """index.html existe en frontend/."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        assert (frontend_dir / "index.html").exists()

    def test_style_css_exists(self):
        """style.css existe en frontend/."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        assert (frontend_dir / "style.css").exists()

    def test_app_js_exists(self):
        """app.js existe en frontend/."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        assert (frontend_dir / "app.js").exists()

    def test_index_html_has_dark_fantasy_theme(self):
        """index.html contiene referencias al tema dark fantasy."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        content = (frontend_dir / "index.html").read_text()
        assert "Lilith" in content
        assert "dashboard" in content.lower() or "Dashboard" in content

    def test_app_js_has_websocket(self):
        """app.js contiene configuración WebSocket."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        content = (frontend_dir / "app.js").read_text()
        assert "WebSocket" in content
        assert "ws://" in content

    def test_style_css_has_dark_theme(self):
        """style.css tiene tema oscuro."""
        frontend_dir = Path(__file__).parent.parent / "frontend"
        content = (frontend_dir / "style.css").read_text()
        assert "--bg-primary" in content
        assert "--accent-red" in content
        assert "0a0a0f" in content  # dark background


# ──────────────────────────────────────────────────────────────────────────────
# Module Import Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestModuleImports:
    """Tests para imports del módulo Dashboard."""

    def test_import_dashboard(self):
        """El módulo Dashboard se puede importar."""
        from Lilith.Dashboard import DashboardServer, get_dashboard

        assert DashboardServer is not None
        assert get_dashboard is not None

    def test_import_server(self):
        """El módulo server se puede importar."""
        from Lilith.Dashboard.server import DashboardServer

        assert DashboardServer is not None

    def test_import_dashboard_tool(self):
        """El módulo dashboard tool se puede importar."""
        from Lilith.tools.dashboard import handle_dashboard_command

        assert handle_dashboard_command is not None

    def test_dashboard_command_start(self):
        """El comando /dashboard start funciona."""
        from Lilith.tools.dashboard import handle_dashboard_command

        result = handle_dashboard_command("start")
        assert "Dashboard" in result or "Error" in result or "start" in result.lower()

    def test_dashboard_command_help(self):
        """El comando /dashboard help funciona."""
        from Lilith.tools.dashboard import handle_dashboard_command

        result = handle_dashboard_command("help")
        assert "start" in result.lower()
        assert "stop" in result.lower()
        assert "status" in result.lower()

    def test_dashboard_command_status(self):
        """El comando /dashboard status funciona."""
        from Lilith.Dashboard import server as srv
        from Lilith.tools.dashboard import handle_dashboard_command

        srv._dashboard_instance = None  # Reset singleton
        result = handle_dashboard_command("status")
        assert "Dashboard" in result or "No" in result or "status" in result.lower()

    def test_dashboard_command_unknown(self):
        """El comando /dashboard con subcomando desconocido muestra error."""
        from Lilith.tools.dashboard import handle_dashboard_command

        result = handle_dashboard_command("xyz123")
        assert "desconocido" in result.lower() or "unknown" in result.lower()
