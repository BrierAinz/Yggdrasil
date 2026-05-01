"""
Dashboard Server — WebSocket + HTTP server para Lilith Dashboard
=================================================================
Backend que sirve el frontend HTML/JS y maneja comunicación
real-time via WebSocket con el core de Lilith.

Funcionalidades:
- Serves frontend HTML/JS/CSS (dark fantasy theme)
- WebSocket real-time bidirectional
- Comandos: /chat, /swarm status, /mcp list, /memory, /system
- Terminal PTY via WebSocket
- Multi-pane layout configurable
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("Lilith.Dashboard.Server")

# Intentar importar dependencias
try:
    import websockets
    from websockets.server import serve as ws_serve

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    logger.warning(
        "[Dashboard] websockets no instalado. Instalar con: pip install websockets"
    )

try:
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    HAS_HTTP = True
except ImportError:
    HAS_HTTP = False

# Directorio del frontend
FRONTEND_DIR = Path(__file__).parent / "frontend"

# Tema dark fantasy
DARK_FANTASY_THEME = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#12121e",
    "bg_tertiary": "#1a1a2e",
    "bg_pane": "#0d0d18",
    "bg_input": "#0f0f1a",
    "bg_hover": "#1e1e30",
    "border": "#2a2a3e",
    "border_active": "#ff3366",
    "border_focus": "#ff336688",
    "text_primary": "#e0e0e0",
    "text_secondary": "#8888aa",
    "text_dim": "#555577",
    "text_bright": "#ffffff",
    "accent_red": "#ff3366",
    "accent_green": "#00ff88",
    "accent_yellow": "#ffcc00",
    "accent_blue": "#3366ff",
    "accent_magenta": "#ff00ff",
    "accent_cyan": "#00ffff",
    "accent_purple": "#9966ff",
    "font_mono": "JetBrains Mono, Fira Code, monospace",
    "font_sans": "Inter, Segoe UI, sans-serif",
}


class DashboardServer:
    """Servidor HTTP + WebSocket para el Dashboard de Lilith.

    Proporciona:
    - HTTP: serves frontend HTML/JS/CSS
    - WebSocket: comunicación real-time bidirectional
    - Terminal PTY: conexión a terminal del sistema
    - API REST: endpoints para estado y configuración
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        lilith_instance=None,
        theme: Optional[Dict] = None,
    ):
        self.host = host
        self.port = port
        self.lilith = lilith_instance
        self.theme = theme or DARK_FANTASY_THEME

        # Estado del servidor
        self._running = False
        self._ws_clients: Set[Any] = set()
        self._http_server: Optional[HTTPServer] = None
        self._ws_server = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # Paneles configurados
        self._panes: Dict[str, Dict] = {}
        self._pane_order: List[str] = ["chat", "terminal", "memory", "system"]

        # Handlers de comandos
        self._command_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

        # Historial de chat
        self._chat_history: List[Dict] = []
        self._max_history = 1000

    # ═══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════════════

    def start(self):
        """Inicia el servidor en un thread separado."""
        if self._running:
            logger.warning("[Dashboard] Ya está ejecutándose")
            return

        if not HAS_WEBSOCKETS:
            logger.error(
                "[Dashboard] websockets no instalado. Ejecuta: pip install websockets"
            )
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        logger.info(f"[Dashboard] Servidor iniciando en http://{self.host}:{self.port}")

    def stop(self):
        """Detiene el servidor."""
        self._running = False
        if self._ws_server:
            asyncio.run_coroutine_threadsafe(
                self._ws_server.close(), self._loop
            ) if self._loop else None
        if self._http_server:
            self._http_server.shutdown()
        logger.info("[Dashboard] Servidor detenido")

    def _run_server(self):
        """Ejecuta el servidor (HTTP + WebSocket) en un event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            # Iniciar HTTP server en thread separado
            http_thread = threading.Thread(target=self._run_http_server, daemon=True)
            http_thread.start()

            # Iniciar WebSocket server en el event loop
            self._loop.run_until_complete(self._run_ws_server())
        except Exception as e:
            logger.error(f"[Dashboard] Error en servidor: {e}")
        finally:
            self._running = False

    def _run_http_server(self):
        """Ejecuta el HTTP server para servir el frontend."""
        handler = _make_http_handler(self)
        self._http_server = HTTPServer((self.host, self.port + 1), handler)
        self._http_server.timeout = 1
        self._http_server.serve_forever()

    async def _run_ws_server(self):
        """Ejecuta el WebSocket server."""

        async def handler(websocket):
            await self._handle_ws_connection(websocket)

        self._ws_server = await ws_serve(
            handler,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        )
        logger.info(f"[Dashboard] WebSocket escuchando en ws://{self.host}:{self.port}")

        # Mantener vivo hasta stop()
        while self._running:
            await asyncio.sleep(1)

    # ═══════════════════════════════════════════════════════════════════════
    # WebSocket Handler
    # ═══════════════════════════════════════════════════════════════════════

    async def _handle_ws_connection(self, websocket):
        """Maneja una nueva conexión WebSocket."""
        self._ws_clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"[Dashboard] Cliente conectado: {client_id}")

        # Enviar estado inicial
        await self._send_initial_state(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(
                        json.dumps({"type": "error", "message": "Invalid JSON"})
                    )
                except Exception as e:
                    logger.error(f"[Dashboard] Error procesando mensaje: {e}")
                    await websocket.send(
                        json.dumps({"type": "error", "message": str(e)})
                    )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._ws_clients.discard(websocket)
            logger.info(f"[Dashboard] Cliente desconectado: {client_id}")

    async def _send_initial_state(self, websocket):
        """Envía estado inicial al cliente."""
        state = {
            "type": "init",
            "theme": self.theme,
            "panes": self._pane_order,
            "layout": self._get_layout_config(),
        }

        # Agregar estado de Lilith si disponible
        if self.lilith:
            state["lilith_status"] = self._get_lilith_status()

        await websocket.send(json.dumps(state))

    async def _process_message(self, websocket, data: Dict):
        """Procesa un mensaje del cliente."""
        msg_type = data.get("type", "")

        handler = self._command_handlers.get(msg_type)
        if handler:
            response = (
                await handler(data)
                if asyncio.iscoroutinefunction(handler)
                else handler(data)
            )
            if isinstance(response, dict):
                await websocket.send(json.dumps(response))
            elif isinstance(response, list):
                for msg in response:
                    await websocket.send(json.dumps(msg))
        else:
            await websocket.send(
                json.dumps({"type": "error", "message": f"Unknown command: {msg_type}"})
            )

    # ═══════════════════════════════════════════════════════════════════════
    # Command Handlers
    # ═══════════════════════════════════════════════════════════════════════

    def _register_default_handlers(self):
        """Registra los handlers por defecto."""
        self._command_handlers = {
            "chat": self._handle_chat,
            "command": self._handle_command,
            "get_status": self._handle_get_status,
            "resize_pane": self._handle_resize_pane,
            "set_layout": self._handle_set_layout,
            "terminal_input": self._handle_terminal_input,
            "terminal_resize": self._handle_terminal_resize,
            "swarm_status": self._handle_swarm_status,
            "mcp_status": self._handle_mcp_status,
            "memory_search": self._handle_memory_search,
            "ping": self._handle_ping,
        }

    def _handle_chat(self, data: Dict) -> Dict:
        """Procesa un mensaje de chat del dashboard."""
        message = data.get("message", "")
        if not message:
            return {"type": "error", "message": "Empty message"}

        # Agregar al historial
        self._chat_history.append(
            {
                "role": "user",
                "content": message,
                "timestamp": time.time(),
            }
        )

        # Si tenemos instancia de Lilith, usar el orquestador
        if self.lilith and hasattr(self.lilith, "orch"):
            try:
                response = self.lilith.orch.chat(message)
                self._chat_history.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "timestamp": time.time(),
                    }
                )
                # Trim history
                if len(self._chat_history) > self._max_history:
                    self._chat_history = self._chat_history[-self._max_history :]
                return {"type": "chat_response", "content": response}
            except Exception as e:
                return {"type": "error", "message": str(e)}

        # Trim history (cuando no hay instancia de Lilith)
        if len(self._chat_history) > self._max_history:
            self._chat_history = self._chat_history[-self._max_history :]
        return {"type": "chat_response", "content": "Lilith no está disponible"}

    def _handle_command(self, data: Dict) -> Dict:
        """Ejecuta un comando slash del dashboard."""
        command = data.get("command", "")
        if not command:
            return {"type": "error", "message": "Empty command"}

        # Enrutar al handler apropiado de Lilith
        if self.lilith and hasattr(self.lilith, "process_command"):
            try:
                result = self.lilith.process_command(command)
                return {"type": "command_result", "output": result}
            except Exception as e:
                return {"type": "error", "message": str(e)}

        return {"type": "error", "message": "Command handler not available"}

    def _handle_get_status(self, data: Dict) -> Dict:
        """Retorna el estado completo de Lilith."""
        return {
            "type": "status",
            "data": self._get_lilith_status(),
        }

    def _handle_resize_pane(self, data: Dict) -> Dict:
        """Redimensiona un panel."""
        pane_id = data.get("pane_id", "")
        size = data.get("size", {})
        if pane_id in self._panes:
            self._panes[pane_id]["size"] = size
        return {"type": "pane_resized", "pane_id": pane_id}

    def _handle_set_layout(self, data: Dict) -> Dict:
        """Cambia la configuración de layout."""
        layout = data.get("layout", "grid")
        panes = data.get("panes", self._pane_order)
        self._pane_order = panes
        # Broadcast a todos los clientes
        return {"type": "layout_updated", "layout": layout, "panes": panes}

    def _handle_terminal_input(self, data: Dict) -> Dict:
        """Maneja input del terminal embebido."""
        # Por ahora, solo ACK
        return {"type": "terminal_ack"}

    def _handle_terminal_resize(self, data: Dict) -> Dict:
        """Maneja resize del terminal embebido."""
        cols = data.get("cols", 80)
        rows = data.get("rows", 24)
        return {"type": "terminal_resized", "cols": cols, "rows": rows}

    def _handle_swarm_status(self, data: Dict) -> Dict:
        """Retorna estado del swarm."""
        try:
            from Lilith.Swarm.manager import get_swarm_manager

            manager = get_swarm_manager()
            status = manager.get_status()
            return {"type": "swarm_status", "data": status}
        except Exception as e:
            return {"type": "error", "message": f"Swarm error: {e}"}

    def _handle_mcp_status(self, data: Dict) -> Dict:
        """Retorna estado de MCP."""
        try:
            from Lilith.MCP.manager import get_mcp_manager

            manager = get_mcp_manager()
            status = manager.get_status()
            return {"type": "mcp_status", "data": status}
        except Exception as e:
            return {"type": "error", "message": f"MCP error: {e}"}

    def _handle_memory_search(self, data: Dict) -> Dict:
        """Busca en la memoria de Lilith."""
        query = data.get("query", "")
        if not query:
            return {"type": "error", "message": "Empty query"}

        try:
            if self.lilith and hasattr(self.lilith, "memory"):
                results = self.lilith.memory.search(query)
                return {"type": "memory_results", "results": results}
        except Exception as e:
            return {"type": "error", "message": f"Memory error: {e}"}

        return {"type": "memory_results", "results": []}

    def _handle_ping(self, data: Dict) -> Dict:
        """Responde a ping."""
        return {"type": "pong", "timestamp": time.time()}

    # ═══════════════════════════════════════════════════════════════════════
    # Status & Config
    # ═══════════════════════════════════════════════════════════════════════

    def _get_lilith_status(self) -> Dict[str, Any]:
        """Retorna el estado completo de Lilith."""
        status = {
            "running": self.lilith is not None,
            "dashboard_running": self._running,
            "clients_connected": len(self._ws_clients),
            "chat_messages": len(self._chat_history),
        }

        if self.lilith:
            try:
                status["model"] = getattr(self.lilith, "current_model", "unknown")
            except Exception:
                status["model"] = "unknown"

        return status

    def _get_layout_config(self) -> Dict:
        """Retorna la configuración de layout actual."""
        default_sizes = {
            "chat": {"width": 50, "height": 100},
            "terminal": {"width": 50, "height": 50},
            "memory": {"width": 25, "height": 50},
            "system": {"width": 25, "height": 50},
        }
        return {
            "type": "grid",
            "panes": {
                name: {
                    "id": name,
                    "size": default_sizes.get(name, {"width": 50, "height": 50}),
                    "visible": True,
                }
                for name in self._pane_order
            },
        }

    # ═══════════════════════════════════════════════════════════════════════
    # Broadcasting
    # ═══════════════════════════════════════════════════════════════════════

    async def broadcast(self, message: Dict):
        """Envía un mensaje a todos los clientes conectados."""
        if not self._ws_clients:
            return
        data = json.dumps(message)
        disconnected = set()
        for client in self._ws_clients:
            try:
                await client.send(data)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception:
                disconnected.add(client)
        self._ws_clients -= disconnected

    def broadcast_sync(self, message: Dict):
        """Envía un mensaje a todos los clientes (sync wrapper)."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)

    # ═══════════════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retorna estado del dashboard."""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "http_port": self.port + 1,
            "clients_connected": len(self._ws_clients),
            "chat_messages": len(self._chat_history),
            "panes": list(self._pane_order),
        }

    def __repr__(self) -> str:
        return f"<DashboardServer {self.host}:{self.port} running={self._running}>"


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Handler — serves frontend files
# ═══════════════════════════════════════════════════════════════════════════════


def _make_http_handler(dashboard: DashboardServer):
    """Crea un HTTP handler con referencia al dashboard."""

    class DashboardHTTPHandler(BaseHTTPRequestHandler):
        """Sirve archivos del frontend del dashboard."""

        def do_GET(self):
            """Maneja peticiones GET."""
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Rutas API
            if path == "/api/status":
                self._send_json(dashboard.get_status())
                return

            if path == "/api/theme":
                self._send_json(dashboard.theme)
                return

            if path == "/api/chat_history":
                self._send_json(dashboard._chat_history)
                return

            # Archivos estáticos
            if path == "/" or path == "/index.html":
                self._serve_file("index.html", "text/html")
            elif path.endswith(".css"):
                self._serve_file(path.lstrip("/"), "text/css")
            elif path.endswith(".js"):
                self._serve_file(path.lstrip("/"), "application/javascript")
            elif (
                path.endswith(".svg") or path.endswith(".png") or path.endswith(".ico")
            ):
                self._serve_file(path.lstrip("/"), "application/octet-stream")
            else:
                self._serve_file("index.html", "text/html")

        def _serve_file(self, filename: str, content_type: str):
            """Sirve un archivo del frontend."""
            filepath = FRONTEND_DIR / filename
            if not filepath.exists():
                self.send_error(404, f"File not found: {filename}")
                return

            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, str(e))

        def _send_json(self, data):
            """Envía una respuesta JSON."""
            content = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format, *args):
            """Suprime logs de HTTP por defecto."""
            logger.debug(f"[Dashboard HTTP] {format % args}")

    return DashboardHTTPHandler


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_dashboard_instance: Optional[DashboardServer] = None


def get_dashboard(
    host: str = "localhost", port: int = 8765, lilith_instance=None
) -> DashboardServer:
    """Obtiene la instancia singleton del DashboardServer."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = DashboardServer(
            host=host, port=port, lilith_instance=lilith_instance
        )
    return _dashboard_instance
