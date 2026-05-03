"""
Dynamic Tool Registry — Registro de tools nativas + MCP
========================================================
Unifica las tools nativas de Lilith con las tools de los
servidores MCP en un solo registro. Permite al LLM invocar
cualquier tool (nativa o MCP) de forma transparente.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from Lilith.MCP.protocol import MCPTool

logger = logging.getLogger("Lilith.DynamicTools")


class ToolSource(str, Enum):
    """Origen de una tool."""

    NATIVE = "native"  # tools de Lilith (files, system, browser, etc.)
    MCP = "mcp"  # tools de servidores MCP externos


@dataclass
class ToolInfo:
    """Informacion completa sobre una tool registrada."""

    name: str
    description: str
    source: ToolSource
    parameters: Dict[str, Any] = field(default_factory=dict)  # JSON Schema
    server_name: str = ""  # solo para MCP tools
    executor: Optional[Callable] = None  # solo para tools nativas
    function_schema: Optional[Dict[str, Any]] = None  # schema OpenAI completo


class DynamicToolRegistry:
    """Registro unificado de tools nativas y MCP.

    Mantiene un diccionario de todas las tools disponibles (nativas y MCP)
    y permite ejecutarlas de forma transparente. Las tools nativas se ejecutan
    via sus executors directamente, las MCP via el MCPManager.

    Uso:
        registry = DynamicToolRegistry()

        # Registrar tools nativas de Lilith
        registry.register_native_tools(ALL_TOOLS, TOOL_EXECUTORS)

        # Registrar tools de MCP
        registry.register_mcp_tools(mcp_manager)

        # Listar todas las tools
        tools = registry.list_tools()

        # Ejecutar una tool (nativa o MCP)
        result = await registry.execute("read_file", {"path": "/tmp/test.txt"})
    """

    def __init__(self):
        self._tools: Dict[str, ToolInfo] = {}
        self._mcp_manager = None

    # ═══════════════════════════════════════════════════════════════════════
    # Registro de Tools
    # ═══════════════════════════════════════════════════════════════════════

    def register_native_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        executor: Callable,
        function_schema: Dict[str, Any] = None,
    ) -> None:
        """Registra una tool nativa.

        Args:
            name: Nombre de la tool (ej: 'read_file')
            description: Descripcion de la tool
            parameters: JSON Schema de parametros
            executor: Funcion que ejecuta la tool
            function_schema: Schema completo formato OpenAI (opcional)
        """
        self._tools[name] = ToolInfo(
            name=name,
            description=description,
            source=ToolSource.NATIVE,
            parameters=parameters,
            executor=executor,
            function_schema=function_schema,
        )
        logger.debug(f"[DynamicTools] Tool nativa registrada: {name}")

    def register_native_tools(
        self, tools_list: List[Dict], executors: Dict[str, Callable]
    ) -> int:
        """Registra multiples tools nativas desde la lista ALL_TOOLS.

        Args:
            tools_list: Lista de definiciones de tools (formato OpenAI)
            executors: Mapeo de nombre -> funcion ejecutora

        Returns:
            Numero de tools registradas
        """
        count = 0
        for tool_def in tools_list:
            func = tool_def.get("function", {})
            name = func.get("name", "")
            description = func.get("description", "")
            parameters = func.get("parameters", {})
            executor = executors.get(name)

            if name and executor:
                self.register_native_tool(
                    name=name,
                    description=description,
                    parameters=parameters,
                    executor=executor,
                    function_schema=func,
                )
                count += 1
            elif name:
                # Tool sin executor — registrar pero no se podra ejecutar
                self.register_native_tool(
                    name=name,
                    description=description,
                    parameters=parameters,
                    executor=None,
                    function_schema=func,
                )
                count += 1
                logger.warning(f"[DynamicTools] Tool nativa sin executor: {name}")

        logger.info(f"[DynamicTools] Registradas {count} tools nativas")
        return count

    def register_mcp_tools(self, mcp_manager) -> int:
        """Registra todas las tools de los servidores MCP.

        Args:
            mcp_manager: Instancia de MCPManager

        Returns:
            Numero de tools MCP registradas
        """
        self._mcp_manager = mcp_manager
        count = 0

        for tool in mcp_manager.get_all_tools():
            self._tools[tool.name] = ToolInfo(
                name=tool.name,
                description=tool.description,
                source=ToolSource.MCP,
                parameters=tool.input_schema or {},
                server_name=tool.server_name,
                function_schema=tool.to_openai_function(),
            )
            count += 1

        logger.info(f"[DynamicTools] Registradas {count} tools MCP")
        return count

    def unregister_tool(self, name: str) -> bool:
        """Remueve una tool del registro.

        Returns:
            True si la tool existia y fue removida
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def clear_mcp_tools(self):
        """Remueve todas las tools MCP del registro."""
        mcp_names = [
            name for name, info in self._tools.items() if info.source == ToolSource.MCP
        ]
        for name in mcp_names:
            del self._tools[name]
        logger.info(f"[DynamicTools] Removidas {len(mcp_names)} tools MCP")

    # ═══════════════════════════════════════════════════════════════════════
    # Ejecucion
    # ═══════════════════════════════════════════════════════════════════════

    async def execute(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Ejecuta una tool por nombre (nativa o MCP).

        Args:
            tool_name: Nombre de la tool
            arguments: Argumentos para la tool

        Returns:
            Resultado de la ejecucion

        Raises:
            KeyError: Si la tool no existe
            RuntimeError: Si no hay executor para una tool nativa
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise KeyError(f"Tool '{tool_name}' no encontrada en el registro")

        if tool.source == ToolSource.NATIVE:
            if tool.executor is None:
                raise RuntimeError(f"Tool nativa '{tool_name}' sin executor")
            return tool.executor(tool_name, arguments or {})

        elif tool.source == ToolSource.MCP:
            if self._mcp_manager is None:
                raise RuntimeError("MCPManager no configurado")
            return await self._mcp_manager.call_tool(tool_name, arguments or {})

    def execute_native(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Ejecuta una tool nativa de forma sincrona.

        Args:
            tool_name: Nombre de la tool
            arguments: Argumentos

        Returns:
            Resultado

        Raises:
            KeyError: Si la tool no existe o no es nativa
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise KeyError(f"Tool '{tool_name}' no encontrada")
        if tool.source != ToolSource.NATIVE:
            raise KeyError(
                f"Tool '{tool_name}' es MCP, usar execute() en vez de execute_native()"
            )
        if tool.executor is None:
            raise RuntimeError(f"Tool nativa '{tool_name}' sin executor")
        return tool.executor(tool_name, arguments or {})

    # ═══════════════════════════════════════════════════════════════════════
    # Consultas
    # ═══════════════════════════════════════════════════════════════════════

    def list_tools(self, source: ToolSource = None) -> List[ToolInfo]:
        """Lista todas las tools registradas.

        Args:
            source: Filtrar por origen (NATIVE o MCP). None = todas.

        Returns:
            Lista de ToolInfo
        """
        if source:
            return [t for t in self._tools.values() if t.source == source]
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Obtiene informacion de una tool especifica."""
        return self._tools.get(name)

    def get_openai_tools(self, source: ToolSource = None) -> List[Dict[str, Any]]:
        """Retorna todas las tools en formato OpenAI function calling.

        Esto se puede inyectar directamente en la llamada al LLM.

        Args:
            source: Filtrar por origen. None = todas.

        Returns:
            Lista de definiciones de tools en formato OpenAI
        """
        tools = []
        for info in self._tools.values():
            if source and info.source != source:
                continue

            if info.function_schema:
                # Schema completo disponible (viene de ALL_TOOLS o MCP)
                tools.append(
                    {
                        "type": "function",
                        "function": info.function_schema,
                    }
                )
            else:
                # Construir desde la info basica
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": info.name,
                            "description": info.description,
                            "parameters": info.parameters,
                        },
                    }
                )
        return tools

    def search_tools(self, query: str) -> List[ToolInfo]:
        """Busca tools por nombre o descripcion."""
        q = query.lower()
        return [
            t
            for t in self._tools.values()
            if q in t.name.lower() or q in t.description.lower()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadisticas del registro."""
        native = sum(1 for t in self._tools.values() if t.source == ToolSource.NATIVE)
        mcp = sum(1 for t in self._tools.values() if t.source == ToolSource.MCP)
        return {
            "total_tools": len(self._tools),
            "native_tools": native,
            "mcp_tools": mcp,
            "mcp_connected": self._mcp_manager is not None,
        }

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<DynamicToolRegistry {len(self._tools)} tools>"


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_registry_instance: Optional[DynamicToolRegistry] = None


def get_dynamic_tool_registry() -> DynamicToolRegistry:
    """Obtiene la instancia singleton del DynamicToolRegistry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DynamicToolRegistry()
    return _registry_instance
