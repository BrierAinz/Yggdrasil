"""
Lilith MCP — Model Context Protocol
=====================================
Cliente MCP para conectar con servidores externos y registrar
sus tools dinámicamente en el ecosistema de Lilith.

Modulos:
    protocol  — Tipos y constantes del protocolo MCP (JSON-RPC)
    client    — Conexion a un server MCP individual
    manager   — Gestiona multiples servers MCP
"""

from Lilith.MCP.client import MCPClient
from Lilith.MCP.manager import MCPManager
from Lilith.MCP.protocol import MCPPrompt, MCPResource, MCPTool

__all__ = ["MCPClient", "MCPManager", "MCPTool", "MCPResource", "MCPPrompt"]
