"""
Lilith MCP — Model Context Protocol Module
============================================
Expone skills y tools de Lilith via MCP, gestiona servidores MCP
externos, scheduling de tareas periódicas, y templates de agentes.

Componentes:
    - server     — LilithMCPServer (expone tools via JSON-RPC stdio)
    - client     — MCPClient (se conecta a servidores MCP externos)
    - manager    — MCPManager (gestiona múltiples servidores MCP)
    - protocol   — Tipos y helpers del protocolo MCP
    - cron       — CronScheduler (tareas periódicas)
    - templates  — Agent Templates (plantillas de agentes)
"""

from Lilith.MCP.cron import CronJob, CronScheduler, get_cron_scheduler
from Lilith.MCP.server import LilithMCPServer, get_mcp_server
from Lilith.MCP.templates import (
    AgentTemplate,
    TemplateLibrary,
    TemplateRenderer,
    get_template_library,
)

# Los imports de client, manager, protocol se mantienen para compatibilidad
from Lilith.MCP.protocol import (
    JSONRPC_VERSION,
    MCP_PROTOCOL_VERSION,
    MCPConnectionState,
    MCPError,
    MCPMethod,
    MCPResource,
    MCPServerInfo,
    MCPTool,
    MCPToolParameter,
    make_error,
    make_notification,
    make_request,
    make_response,
    parse_mcp_response,
)

__all__ = [
    # Server
    "LilithMCPServer",
    "get_mcp_server",
    # Client (importado de client.py)
    # Manager (importado de manager.py)
    # Protocol
    "MCPTool",
    "MCPToolParameter",
    "MCPServerInfo",
    "MCPConnectionState",
    "MCPResource",
    "MCPMethod",
    "MCPError",
    "JSONRPC_VERSION",
    "MCP_PROTOCOL_VERSION",
    "make_request",
    "make_response",
    "make_error",
    "make_notification",
    "parse_mcp_response",
    # Cron
    "CronJob",
    "CronScheduler",
    "get_cron_scheduler",
    # Templates
    "AgentTemplate",
    "TemplateLibrary",
    "TemplateRenderer",
    "get_template_library",
]