"""
MCP Manager — Gestiona multiples servidores MCP
==================================================
Carga la configuracion, conecta/desconecta servers, y_expone
todas las tools como un registro unificado.

Config file: ~/.lilith/mcp.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from Lilith.MCP.client import MCPClient
from Lilith.MCP.protocol import MCPError, MCPTool

logger = logging.getLogger("Lilith.MCP.Manager")

# Default config path
DEFAULT_CONFIG_PATH = Path.home() / ".lilith" / "mcp.json"


class MCPManager:
    """Gestiona multiples conexiones a servidores MCP.

    Carga la configuracion desde mcp.json, conecta a los servers
    al iniciar, y provee acceso unificado a todas las tools.

    Uso:
        mgr = MCPManager()
        await mgr.start()  # conecta todos los servers
        tools = mgr.get_all_tools()
        result = await mgr.call_tool("filesystem_read_file", {"path": "/tmp/test.txt"})
        await mgr.stop()
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.clients: Dict[str, MCPClient] = {}
        self._tool_to_server: Dict[str, str] = {}  # tool_name -> server_name
        self._started = False

    # ═══════════════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════════════

    async def start(self) -> Dict[str, bool]:
        """Carga la configuracion y conecta a todos los servers.

        Returns:
            Dict con nombre de server -> True/False si conecto
        """
        self._load_config()
        results = {}
        for name, client in self.clients.items():
            try:
                connected = await client.connect()
                results[name] = connected
                if connected:
                    # Registrar tools
                    for tool in client.tools:
                        self._tool_to_server[tool.name] = name
            except Exception as e:
                logger.error(f"[MCP] Error conectando {name}: {e}")
                results[name] = False
        self._started = True
        return results

    async def stop(self):
        """Desconecta todos los servers."""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"[MCP] Error desconectando {name}: {e}")
        self.clients.clear()
        self._tool_to_server.clear()
        self._started = False

    # ═══════════════════════════════════════════════════════════════════════
    # Config
    # ═══════════════════════════════════════════════════════════════════════

    def _load_config(self):
        """Carga la configuracion de servers MCP desde mcp.json."""
        if not self.config_path.exists():
            logger.info(f"[MCP] No existe config: {self.config_path}")
            # Crear config default
            self._create_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            servers = config.get("servers", {})
            for name, server_config in servers.items():
                client = MCPClient({**server_config, "name": name})
                self.clients[name] = client

            logger.info(
                f"[MCP] Cargados {len(self.clients)} servers desde {self.config_path}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"[MCP] Error parseando config: {e}")
        except Exception as e:
            logger.error(f"[MCP] Error cargando config: {e}")

    def _create_default_config(self):
        """Crea un archivo de configuracion default con ejemplos comentados."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "servers": {
                # Ejemplo de configuracion (descomentar cuando se instale el server)
                # "filesystem": {
                #     "command": "npx",
                #     "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                #     "env": {}
                # },
                # "github": {
                #     "command": "npx",
                #     "args": ["-y", "@modelcontextprotocol/server-github"],
                #     "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
                # },
            }
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info(f"[MCP] Creada configuracion default en {self.config_path}")
        except Exception as e:
            logger.warning(f"[MCP] No se pudo crear config default: {e}")

    def save_config(self):
        """Guarda la configuracion actual a mcp.json."""
        config = {"servers": {}}
        for name, client in self.clients.items():
            config["servers"][name] = {
                "command": client.command,
                "args": client.args,
                "env": client.env,
            }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"[MCP] Config guardada en {self.config_path}")

    # ═══════════════════════════════════════════════════════════════════════
    # Server Management
    # ═══════════════════════════════════════════════════════════════════════

    async def add_server(
        self, name: str, config: Dict[str, Any], connect: bool = True
    ) -> bool:
        """Agrega un nuevo servidor MCP dinamicamente.

        Args:
            name: Nombre del servidor
            config: Configuracion (command, args, env)
            connect: Si conectar inmediatamente

        Returns:
            True si se agrego (y conecto) exitosamente
        """
        if name in self.clients:
            logger.warning(f"[MCP] Server {name} ya existe, reemplazando...")
            await self.remove_server(name)

        client = MCPClient({**config, "name": name})
        self.clients[name] = client

        if connect:
            connected = await client.connect()
            if connected:
                for tool in client.tools:
                    self._tool_to_server[tool.name] = name
                self.save_config()
            return connected

        self.save_config()
        return True

    async def remove_server(self, name: str) -> bool:
        """Remueve un servidor MCP.

        Args:
            name: Nombre del servidor

        Returns:
            True si se removio exitosamente
        """
        if name not in self.clients:
            return False

        client = self.clients[name]
        await client.disconnect()

        # Remover mapeo de tools
        tools_to_remove = [t for t, s in self._tool_to_server.items() if s == name]
        for tool_name in tools_to_remove:
            del self._tool_to_server[tool_name]

        del self.clients[name]
        self.save_config()
        return True

    async def reconnect_server(self, name: str) -> bool:
        """Reconecta un servidor MCP.

        Args:
            name: Nombre del servidor

        Returns:
            True si se reconecto exitosamente
        """
        if name not in self.clients:
            return False

        client = self.clients[name]
        await client.disconnect()

        connected = await client.connect()
        if connected:
            # Actualizar mapeo de tools
            tools_to_remove = [t for t, s in self._tool_to_server.items() if s == name]
            for tool_name in tools_to_remove:
                del self._tool_to_server[tool_name]
            for tool in client.tools:
                self._tool_to_server[tool.name] = name

        return connected

    # ═══════════════════════════════════════════════════════════════════════
    # Tool Access
    # ═══════════════════════════════════════════════════════════════════════

    def get_all_tools(self) -> List[MCPTool]:
        """Devuelve todas las tools de todos los servers conectados."""
        tools = []
        for client in self.clients.values():
            tools.extend(client.tools)
        return tools

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Devuelve todas las tools en formato OpenAI function calling.

        Esto permite inyectar directamente en el LLM como tools disponibles.
        """
        return [tool.to_openai_function() for tool in self.get_all_tools()]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Llama a una tool por nombre, enrutando al servidor correcto.

        Args:
            tool_name: Nombre de la tool
            arguments: Argumentos para la tool

        Returns:
            Resultado de la tool

        Raises:
            KeyError: Si la tool no existe
            MCPError: Si el servidor responde con error
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name or server_name not in self.clients:
            raise KeyError(f"Tool '{tool_name}' no encontrada en ningun servidor MCP")

        client = self.clients[server_name]
        return await client.call_tool(tool_name, arguments)

    def find_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Busca una tool por nombre exacto."""
        for tool in self.get_all_tools():
            if tool.name == tool_name:
                return tool
        return None

    def search_tools(self, query: str) -> List[MCPTool]:
        """Busca tools que contengan el query en nombre o descripcion."""
        query_lower = query.lower()
        results = []
        for tool in self.get_all_tools():
            if (
                query_lower in tool.name.lower()
                or query_lower in tool.description.lower()
            ):
                results.append(tool)
        return results

    # ═══════════════════════════════════════════════════════════════════════
    # Resources y Prompts
    # ═══════════════════════════════════════════════════════════════════════

    def get_all_resources(self) -> List[Dict[str, Any]]:
        """Devuelve todos los resources de todos los servers."""
        resources = []
        for client in self.clients.values():
            resources.extend(client.resources)
        return resources

    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """Devuelve todos los prompts de todos los servers."""
        prompts = []
        for client in self.clients.values():
            prompts.extend(client.prompts)
        return prompts

    async def read_resource(self, uri: str) -> Any:
        """Lee un resource por URI, enrutando al servidor correcto."""
        for client in self.clients.values():
            if not client.state.connected:
                continue
            for res in client.resources:
                if res.get("uri") == uri:
                    return await client.read_resource(uri)
        raise KeyError(f"Resource '{uri}' no encontrado")

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Any:
        """Obtiene un prompt template por nombre."""
        for client in self.clients.values():
            if not client.state.connected:
                continue
            for prompt in client.prompts:
                if prompt.get("name") == name:
                    return await client.get_prompt(name, arguments)
        raise KeyError(f"Prompt '{name}' no encontrado")

    # ═══════════════════════════════════════════════════════════════════════
    # Status
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de todos los servers."""
        servers = {}
        for name, client in self.clients.items():
            servers[name] = client.get_status()

        return {
            "started": self._started,
            "servers_count": len(self.clients),
            "connected_count": sum(
                1 for c in self.clients.values() if c.state.connected
            ),
            "total_tools": len(self.get_all_tools()),
            "total_resources": len(self.get_all_resources()),
            "total_prompts": len(self.get_all_prompts()),
            "servers": servers,
        }

    def get_server_names(self) -> List[str]:
        """Lista los nombres de todos los servidores configurados."""
        return list(self.clients.keys())

    def get_connected_servers(self) -> List[str]:
        """Lista los nombres de los servidores conectados."""
        return [n for n, c in self.clients.items() if c.state.connected]

    def __repr__(self) -> str:
        connected = len(self.get_connected_servers())
        return f"<MCPManager {len(self.clients)} servers, {connected} connected>"


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_manager_instance: Optional[MCPManager] = None


def get_mcp_manager(config_path: Optional[Path] = None) -> MCPManager:
    """Obtiene la instancia singleton del MCPManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MCPManager(config_path)
    return _manager_instance
