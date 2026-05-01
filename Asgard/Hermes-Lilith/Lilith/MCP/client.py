"""
MCP Client — Conexion a un servidor MCP individual
====================================================
Gestiona el ciclo de vida de la conexion a un server MCP via stdio
usando JSON-RPC 2.0 sobre stdin/stdout.

El servidor se ejecuta como subproceso y la comunicacion es por
lineas JSON (un objeto JSON por linea).
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from Lilith.MCP.protocol import (
    MCPConnectionState,
    MCPError,
    MCPServerInfo,
    MCPTool,
    make_notification,
    make_request,
    parse_mcp_response,
)

logger = logging.getLogger("Lilith.MCP.Client")


class MCPClient:
    """Cliente MCP para conectar con un servidor externo via stdio.

    Cada servidor MCP se ejecuta como subproceso. La comunicacion
    es JSON-RPC 2.0 sobre stdin/stdout del subproceso.

    Flujo:
        1. connect()       — inicia el subproceso y hace handshake
        2. discover()      — lista tools, resources, prompts
        3. call_tool()     — ejecuta una tool del servidor
        4. read_resource() — lee un recurso del servidor
        5. disconnect()    — cierra el subproceso

    Uso:
        client = MCPClient({
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-server-filesystem", "/tmp"],
        })
        await client.connect()
        tools = client.tools
        result = await client.call_tool("read_file", {"path": "/tmp/test.txt"})
        await client.disconnect()
    """

    def __init__(self, config: Dict[str, Any]):
        self.name: str = config.get("name", "unknown")
        self.command: str = config.get("command", "")
        self.args: List[str] = config.get("args", [])
        self.env: Dict[str, str] = config.get("env", {})
        self.server_url: Optional[str] = config.get("url")  # para HTTP/SSE transport

        # Estado
        self.state = MCPConnectionState()
        self.tools: List[MCPTool] = []
        self.resources: List[Dict[str, Any]] = []
        self.prompts: List[Dict[str, Any]] = []

        # Subproceso
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader_lock = asyncio.Lock()
        self._writer_lock = asyncio.Lock()
        self._request_id = 0
        self._response_futures: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._running = False

    # ═══════════════════════════════════════════════════════════════════════
    # Conexion / Desconexion
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self) -> bool:
        """Inicia el subproceso MCP y hace el handshake de inicializacion.

        Returns:
            True si la conexion fue exitosa, False si fallo.
        """
        if self.state.connected:
            logger.warning(f"[MCP:{self.name}] Ya conectado")
            return True

        try:
            # Verificar que el comando existe
            cmd_path = shutil.which(self.command)
            if not cmd_path and not Path(self.command).exists():
                logger.error(f"[MCP:{self.name}] Comando no encontrado: {self.command}")
                self.state.error = f"Command not found: {self.command}"
                return False

            # Construir entorno
            env = {**os.environ, **self._resolve_env(self.env)}

            # Iniciar subproceso
            full_args = [self.command] + self.args
            self._process = await asyncio.create_subprocess_exec(
                *full_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            self._running = True

            # Iniciar lector de respuestas en background
            self._reader_task = asyncio.create_task(self._read_loop())

            # Handshake: initialize
            init_result = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True},
                        "prompts": {"listChanged": True},
                    },
                    "clientInfo": {
                        "name": "lilith",
                        "version": "3.0.0",
                    },
                },
            )

            # Parsear info del servidor
            server_info = init_result.get("serverInfo", {})
            self.state.server_info = MCPServerInfo(
                name=server_info.get("name", self.name),
                version=server_info.get("version", "unknown"),
                protocol_version=init_result.get("protocolVersion", "2024-11-05"),
                capabilities=init_result.get("capabilities", {}),
            )

            # Enviar notificacion initialized
            await self._send_notification("notifications/initialized")

            self.state.initialized = True

            # Descubrir tools, resources, prompts
            await self.discover()

            self.state.connected = True
            logger.info(
                f"[MCP:{self.name}] Conectado a {self.state.server_info.name} "
                f"v{self.state.server_info.version} "
                f"({len(self.tools)} tools, {len(self.resources)} resources)"
            )
            return True

        except Exception as e:
            logger.error(f"[MCP:{self.name}] Error conectando: {e}")
            self.state.error = str(e)
            await self._cleanup()
            return False

    async def disconnect(self):
        """Cierra la conexion con el servidor MCP."""
        if not self._running:
            return
        self._running = False
        await self._cleanup()
        self.state.connected = False
        logger.info(f"[MCP:{self.name}] Desconectado")

    async def _cleanup(self):
        """Limpia recursos del subproceso."""
        self._reader_lock = asyncio.Lock()
        self._writer_lock = asyncio.Lock()

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._process and self._process.returncode is None:
            try:
                self._process.stdin.close()
                await self._process.wait()
            except Exception:
                pass

        self._response_futures.clear()

    # ═══════════════════════════════════════════════════════════════════════
    # Discovery
    # ═══════════════════════════════════════════════════════════════════════

    async def discover(self):
        """Descubre tools, resources y prompts del servidor."""
        await self._discover_tools()
        await self._discover_resources()
        await self._discover_prompts()

    async def _discover_tools(self):
        """Lista las tools disponibles en el servidor."""
        try:
            result = await self._send_request("tools/list", {})
            tools_list = result.get("tools", [])
            self.tools = []
            for t in tools_list:
                tool = MCPTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    server_name=self.name,
                    input_schema=t.get("inputSchema"),
                    parameters=[],  # Se construye desde inputSchema si es necesario
                )
                # Si no hay inputSchema, construir desde annotations
                if not tool.input_schema and "parameters" in t:
                    tool.input_schema = t["parameters"]
                self.tools.append(tool)
            logger.debug(f"[MCP:{self.name}] Descubiertas {len(self.tools)} tools")
        except MCPError as e:
            logger.warning(f"[MCP:{self.name}] Error listando tools: {e}")
        except Exception as e:
            logger.warning(f"[MCP:{self.name}] Error listando tools: {e}")

    async def _discover_resources(self):
        """Lista los resources disponibles en el servidor."""
        try:
            result = await self._send_request("resources/list", {})
            self.resources = result.get("resources", [])
            logger.debug(
                f"[MCP:{self.name}] Descubiertos {len(self.resources)} resources"
            )
        except Exception as e:
            logger.debug(f"[MCP:{self.name}] No resources: {e}")
            self.resources = []

    async def _discover_prompts(self):
        """Lista los prompts disponibles en el servidor."""
        try:
            result = await self._send_request("prompts/list", {})
            self.prompts = result.get("prompts", [])
            logger.debug(f"[MCP:{self.name}] Descubiertos {len(self.prompts)} prompts")
        except Exception as e:
            logger.debug(f"[MCP:{self.name}] No prompts: {e}")
            self.prompts = []

    # ═══════════════════════════════════════════════════════════════════════
    # Ejecucion de Tools
    # ═══════════════════════════════════════════════════════════════════════

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Llama a una tool del servidor MCP.

        Args:
            tool_name: Nombre de la tool a ejecutar
            arguments: Argumentos para la tool

        Returns:
            El resultado de la tool (contenido/texto)

        Raises:
            MCPError: Si el servidor responde con error
            RuntimeError: Si no estamos conectados
        """
        if not self.state.connected:
            raise RuntimeError(f"[MCP:{self.name}] No conectado")

        result = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments or {},
            },
        )

        # El resultado viene en formatos variados, normalizar
        if isinstance(result, dict):
            # Formato MCP: {"content": [{"type": "text", "text": "..."}]}
            content = result.get("content", [])
            if content and isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                if texts:
                    return "\n".join(texts) if len(texts) > 1 else texts[0]
            # Si viene isError, lanzar
            if result.get("isError"):
                error_text = str(content) if content else "Unknown MCP tool error"
                raise MCPError(-32000, f"Tool error: {error_text}")
            return result

        return result

    async def read_resource(self, uri: str) -> Any:
        """Lee un recurso del servidor MCP.

        Args:
            uri: URI del recurso a leer

        Returns:
            Contenido del recurso
        """
        if not self.state.connected:
            raise RuntimeError(f"[MCP:{self.name}] No conectado")

        result = await self._send_request("resources/read", {"uri": uri})
        return result

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Obtiene un prompt template del servidor MCP.

        Args:
            name: Nombre del prompt
            arguments: Argumentos para el prompt

        Returns:
            Contenido del prompt renderizado
        """
        if not self.state.connected:
            raise RuntimeError(f"[MCP:{self.name}] No conectado")

        result = await self._send_request(
            "prompts/get",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        return result

    async def ping(self) -> bool:
        """Envia un ping al servidor para verificar conectividad.

        Returns:
            True si el servidor responde, False si no.
        """
        try:
            await self._send_request("ping", {})
            return True
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # Comunicacion JSON-RPC de bajo nivel
    # ═══════════════════════════════════════════════════════════════════════

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Envia un request JSON-RPC y espera la respuesta.

        Returns:
            El campo 'result' de la respuesta, o lanza MCPError.
        """
        if not self._process or self._process.returncode is not None:
            raise RuntimeError(f"[MCP:{self.name}] Proceso no disponible")

        self._request_id += 1
        request_id = self._request_id
        message = make_request(method, params, request_id)

        # Crear future para esperar la respuesta
        future = asyncio.get_event_loop().create_future()
        self._response_futures[request_id] = future

        # Enviar mensaje
        line = json.dumps(message) + "\n"
        async with self._writer_lock:
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()

        # Esperar respuesta con timeout
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return parse_mcp_response(result)
        except asyncio.TimeoutError:
            self._response_futures.pop(request_id, None)
            raise MCPError(-32603, f"Timeout esperando respuesta para {method}")
        finally:
            self._response_futures.pop(request_id, None)

    async def _send_notification(self, method: str, params: Dict[str, Any] = None):
        """Envia una notificacion JSON-RPC (no espera respuesta)."""
        if not self._process or self._process.returncode is not None:
            return

        message = make_notification(method, params)
        line = json.dumps(message) + "\n"
        async with self._writer_lock:
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()

    async def _read_loop(self):
        """Loop que lee respuestas del stdout del subproceso."""
        try:
            while self._running and self._process:
                line = await self._process.stdout.readline()
                if not line:
                    # EOF — el proceso cerro
                    logger.warning(f"[MCP:{self.name}] Proceso cerro stdout")
                    break

                line = line.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(f"[MCP:{self.name}] Linea invalida: {line[:100]}")
                    continue

                # Es una respuesta a un request?
                msg_id = message.get("id")
                if msg_id and msg_id in self._response_futures:
                    future = self._response_futures[msg_id]
                    if not future.done():
                        future.set_result(message)
                    continue

                # Es una notificacion del servidor?
                method = message.get("method")
                if method:
                    await self._handle_notification(method, message.get("params", {}))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._running:
                logger.error(f"[MCP:{self.name}] Error en read_loop: {e}")

    async def _handle_notification(self, method: str, params: Dict[str, Any]):
        """Maneja notificaciones del servidor (tools list changed, etc.)."""
        if method == "notifications/tools/list_changed":
            logger.info(f"[MCP:{self.name}] Tools cambiaron, re-descubriendo...")
            await self._discover_tools()
        elif method == "notifications/resources/list_changed":
            logger.info(f"[MCP:{self.name}] Resources cambiaron, re-descubriendo...")
            await self._discover_resources()
        elif method == "notifications/prompts/list_changed":
            logger.info(f"[MCP:{self.name}] Prompts cambiaron, re-descubriendo...")
            await self._discover_prompts()
        else:
            logger.debug(f"[MCP:{self.name}] Notificacion no manejada: {method}")

    # ═══════════════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _resolve_env(env: Dict[str, str]) -> Dict[str, str]:
        """Resuelve variables de entorno tipo ${VAR} en los valores."""
        resolved = {}
        for key, value in env.items():
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                var_name = value[2:-1]
                actual = os.environ.get(var_name, "")
                if not actual:
                    logger.warning(
                        f"[MCP] Variable de entorno no encontrada: {var_name}"
                    )
                resolved[key] = actual
            else:
                resolved[key] = value
        return resolved

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado actual de la conexion."""
        return {
            "name": self.name,
            "connected": self.state.connected,
            "initialized": self.state.initialized,
            "server_name": self.state.server_info.name
            if self.state.server_info
            else None,
            "server_version": self.state.server_info.version
            if self.state.server_info
            else None,
            "tools_count": len(self.tools),
            "resources_count": len(self.resources),
            "prompts_count": len(self.prompts),
            "error": self.state.error,
            "command": self.command,
            "args": self.args,
        }

    def __repr__(self) -> str:
        status = "connected" if self.state.connected else "disconnected"
        return f"<MCPClient {self.name} [{status}]>"
