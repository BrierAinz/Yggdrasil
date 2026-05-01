"""
MCP CLI Tool — Comandos /mcp para Lilith
==========================================
Expone la gestion de servidores MCP desde la CLI.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List

from Lilith.MCP.manager import MCPManager, get_mcp_manager
from Lilith.MCP.protocol import MCPError


def get_tools():
    """Retorna las definiciones de tools MCP para el LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "mcp_list",
                "description": "Lista los servidores MCP conectados y sus tools",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detailed": {
                            "type": "boolean",
                            "description": "Si True, muestra informacion detallada de cada tool",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mcp_connect",
                "description": "Conecta a un servidor MCP nuevo o reconecta uno existente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre del servidor",
                        },
                        "command": {
                            "type": "string",
                            "description": "Comando para ejecutar (ej: npx, python3, uvx)",
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Argumentos del comando",
                        },
                        "env": {
                            "type": "object",
                            "description": 'Variables de entorno (ej: {"API_KEY": "${MY_KEY}"})',
                        },
                    },
                    "required": ["name", "command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mcp_disconnect",
                "description": "Desconecta y remueve un servidor MCP",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre del servidor a desconectar",
                        },
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mcp_call",
                "description": "Ejecuta una tool de un servidor MCP",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Nombre de la tool a ejecutar",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Argumentos para la tool",
                        },
                    },
                    "required": ["tool_name"],
                },
            },
        },
    ]


def execute_tool(name: str, args: Dict) -> Dict:
    """Ejecuta un comando MCP desde la CLI.

    Las operaciones que requieren async se ejecutan en un event loop.
    """
    if name == "mcp_list":
        return _mcp_list(args)
    elif name == "mcp_connect":
        return _mcp_connect(args)
    elif name == "mcp_disconnect":
        return _mcp_disconnect(args)
    elif name == "mcp_call":
        return _mcp_call(args)
    else:
        return {"error": f"Tool MCP desconocida: {name}"}


def _run_async(coro):
    """Ejecuta una corrutina async de forma segura."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Ya estamos en un event loop — crear tarea
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _mcp_list(args: Dict) -> Dict:
    """Lista servidores MCP conectados."""
    manager = get_mcp_manager()
    status = manager.get_status()
    detailed = args.get("detailed", False)

    result = {
        "servidores": len(status["servers"]),
        "conectados": status["connected_count"],
        "total_tools": status["total_tools"],
        "total_recursos": status["total_resources"],
    }

    if detailed:
        for name, info in status["servers"].items():
            result[name] = {
                "conectado": info["connected"],
                "servidor": info.get("server_name", "N/A"),
                "version": info.get("server_version", "N/A"),
                "tools": info["tools_count"],
                "comando": info.get("command", ""),
            }
    else:
        result["servers"] = list(status["servers"].keys())

    return result


def _mcp_connect(args: Dict) -> Dict:
    """Conecta a un servidor MCP."""
    name = args.get("name", "")
    command = args.get("command", "")
    cmd_args = args.get("args", [])
    env = args.get("env", {})

    if not name or not command:
        return {"error": "Se requieren 'name' y 'command'"}

    manager = get_mcp_manager()
    config = {
        "command": command,
        "args": cmd_args,
        "env": env,
    }

    connected = _run_async(manager.add_server(name, config, connect=True))

    if connected:
        return {
            "status": "conectado",
            "name": name,
            "tools": len(manager.clients[name].tools) if name in manager.clients else 0,
        }
    else:
        return {
            "status": "error",
            "name": name,
            "error": manager.clients.get(name, {}).state.error
            if name in manager.clients
            else "Unknown error",
        }


def _mcp_disconnect(args: Dict) -> Dict:
    """Desconecta un servidor MCP."""
    name = args.get("name", "")
    if not name:
        return {"error": "Se requiere 'name'"}

    manager = get_mcp_manager()
    removed = _run_async(manager.remove_server(name))

    if removed:
        return {"status": "desconectado", "name": name}
    else:
        return {"error": f"Servidor '{name}' no encontrado"}


def _mcp_call(args: Dict) -> Dict:
    """Ejecuta una tool MCP."""
    tool_name = args.get("tool_name", "")
    arguments = args.get("arguments", {})

    if not tool_name:
        return {"error": "Se requiere 'tool_name'"}

    manager = get_mcp_manager()

    try:
        result = _run_async(manager.call_tool(tool_name, arguments))
        return {"result": result}
    except KeyError as e:
        return {"error": str(e)}
    except MCPError as e:
        return {"error": f"MCP Error {e.code}: {e.message}"}
    except Exception as e:
        return {"error": f"Error ejecutando tool: {e}"}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Commands — /mcp subcomandos (usados desde main.py)
# ═══════════════════════════════════════════════════════════════════════════════


def handle_mcp_command(text: str) -> str:
    """Maneja el comando /mcp desde la CLI.

    Subcomandos:
        /mcp status           — Lista servers y su estado
        /mcp list             — Lista todas las tools MCP disponibles
        /mcp connect <name> <command> [args...] — Conecta un server
        /mcp disconnect <name> — Desconecta un server
        /mcp call <tool> [args] — Ejecuta una tool MCP
        /mcp start             — Inicia todos los servers configurados
        /mcp stop              — Detiene todos los servers
        /mcp reload            — Recarga configuracion y reconecta
    """
    parts = text.strip().split(maxsplit=1)
    subcmd = parts[0] if parts else "status"
    rest = parts[1] if len(parts) > 1 else ""

    if subcmd in ("status", ""):
        return _cli_status()
    elif subcmd == "list":
        return _cli_list(rest)
    elif subcmd == "connect":
        return _cli_connect(rest)
    elif subcmd == "disconnect":
        return _cli_disconnect(rest)
    elif subcmd == "call":
        return _cli_call(rest)
    elif subcmd == "start":
        return _cli_start()
    elif subcmd == "stop":
        return _cli_stop()
    elif subcmd == "reload":
        return _cli_reload()
    else:
        return _cli_help()


def _cli_status() -> str:
    """Muestra estado de los servers MCP."""
    manager = get_mcp_manager()
    status = manager.get_status()

    lines = [
        "╔══════════════════════════════════════════╗",
        "║          MCP SERVERS STATUS               ║",
        "╠══════════════════════════════════════════╣",
        f"║ Servers configurados: {status['servers_count']:<19} ║",
        f"║ Conectados:           {status['connected_count']:<19} ║",
        f"║ Total tools:          {status['total_tools']:<19} ║",
        f"║ Total recursos:       {status['total_resources']:<19} ║",
        "╚══════════════════════════════════════════╝",
    ]

    for name, info in status["servers"].items():
        state = "🟢" if info["connected"] else "🔴"
        lines.append(f"  {state} {name}")
        lines.append(f"     Command: {info.get('command', 'N/A')}")
        lines.append(f"     Tools: {info['tools_count']}")

    if not status["servers"]:
        lines.append("  (No hay servers configurados)")
        lines.append("  Usa /mcp connect <name> <command> para agregar")

    return "\n".join(lines)


def _cli_list(filter_text: str) -> str:
    """Lista las tools MCP disponibles."""
    manager = get_mcp_manager()
    tools = manager.get_all_tools()

    if filter_text:
        tools = [
            t
            for t in tools
            if filter_text.lower() in t.name.lower()
            or filter_text.lower() in t.description.lower()
        ]

    if not tools:
        return (
            "No hay tools MCP disponibles."
            if not filter_text
            else f"No hay tools que coincidan con '{filter_text}'"
        )

    lines = [f"MCP Tools ({len(tools)}):"]
    for tool in tools:
        src = f"[{tool.server_name}]" if tool.server_name else ""
        desc = (
            tool.description[:60] + "..."
            if len(tool.description) > 60
            else tool.description
        )
        lines.append(f"  • {tool.name} {src}")
        lines.append(f"    {desc}")

    return "\n".join(lines)


def _cli_connect(rest: str) -> str:
    """Conecta un servidor MCP: /mcp connect <name> <command> [args...]"""
    import shlex

    try:
        parts = shlex.split(rest)
    except ValueError:
        return "Error: Argumentos invalidos"

    if len(parts) < 2:
        return "Uso: /mcp connect <name> <command> [args...]\nEjemplo: /mcp connect filesystem npx -y @modelcontextprotocol/server-filesystem /tmp"

    name = parts[0]
    command = parts[1]
    cmd_args = parts[2:]

    manager = get_mcp_manager()
    config = {"command": command, "args": cmd_args, "env": {}}

    connected = _run_async(manager.add_server(name, config, connect=True))

    if connected:
        client = manager.clients.get(name)
        tools_count = len(client.tools) if client else 0
        return f"✅ Server '{name}' conectado ({tools_count} tools disponibles)"
    else:
        client = manager.clients.get(name)
        error = client.state.error if client else "Unknown error"
        return f"❌ Error conectando '{name}': {error}"


def _cli_disconnect(rest: str) -> str:
    """Desconecta un servidor: /mcp disconnect <name>"""
    name = rest.strip()
    if not name:
        return "Uso: /mcp disconnect <name>"

    manager = get_mcp_manager()
    removed = _run_async(manager.remove_server(name))
    return (
        f"✅ Server '{name}' desconectado"
        if removed
        else f"❌ Server '{name}' no encontrado"
    )


def _cli_call(rest: str) -> str:
    """Ejecuta una tool: /mcp call <tool_name> [json_args]"""
    parts = rest.strip().split(maxsplit=1)
    if not parts:
        return "Uso: /mcp call <tool_name> [json_args]"

    tool_name = parts[0]
    arguments = {}
    if len(parts) > 1:
        try:
            arguments = json.loads(parts[1])
        except json.JSONDecodeError:
            return "Error: Los argumentos deben ser JSON valido"

    manager = get_mcp_manager()
    try:
        result = _run_async(manager.call_tool(tool_name, arguments))
        return f"Resultado de {tool_name}:\n{json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else result}"
    except KeyError as e:
        return f"❌ {e}"
    except MCPError as e:
        return f"❌ MCP Error {e.code}: {e.message}"
    except Exception as e:
        return f"❌ Error: {e}"


def _cli_start() -> str:
    """Inicia todos los servers MCP configurados."""
    manager = get_mcp_manager()
    results = _run_async(manager.start())

    lines = ["Iniciando servers MCP..."]
    for name, connected in results.items():
        state = "✅" if connected else "❌"
        lines.append(f"  {state} {name}")

    return "\n".join(lines)


def _cli_stop() -> str:
    """Detiene todos los servers MCP."""
    manager = get_mcp_manager()
    _run_async(manager.stop())
    return "🛑 Todos los servers MCP desconectados"


def _cli_reload() -> str:
    """Recarga configuracion y reconecta."""
    manager = get_mcp_manager()
    _run_async(manager.stop())
    results = _run_async(manager.start())

    lines = ["Recargando servers MCP..."]
    for name, connected in results.items():
        state = "✅" if connected else "❌"
        lines.append(f"  {state} {name}")

    return "\n".join(lines)


def _cli_help() -> str:
    """Muestra ayuda del comando /mcp."""
    return """MCP — Model Context Protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Comandos:
  /mcp status              — Lista servers y su estado
  /mcp list [filtro]       — Lista tools MCP disponibles
  /mcp connect <name> <cmd> [args] — Conecta un server
  /mcp disconnect <name>   — Desconecta un server
  /mcp call <tool> [json]  — Ejecuta una tool MCP
  /mcp start               — Inicia todos los servers
  /mcp stop                — Detiene todos los servers
  /mcp reload              — Recarga config y reconecta

Ejemplos:
  /mcp connect filesystem npx -y @modelcontextprotocol/server-filesystem /tmp
  /mcp connect github npx -y @modelcontextprotocol/server-github
  /mcp call read_file {"path": "/tmp/test.txt"}
  /mcp list filesystem"""
