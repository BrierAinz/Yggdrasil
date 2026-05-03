#!/usr/bin/env python3
"""
Lilith MCP Bridge
================
Expone las tools de Lilith como servidor MCP para Hermes Agent.

Uso:
    python mcp_bridge.py

Este script inicia un servidor MCP que Hermes Agent puede consumir.
"""
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Agregar Lilith al path (D:\Proyectos\Midgard)
LILITH_ROOT = Path(__file__).parent.parent.parent
if str(LILITH_ROOT) not in sys.path:
    sys.path.insert(0, str(LILITH_ROOT))

# Importar tools de Lilith
HAS_LILITH = False
try:
    import Lilith.tools.browser as browser
    import Lilith.tools.coding as coding
    import Lilith.tools.desktop as desktop
    import Lilith.tools.files as files
    import Lilith.tools.network as network
    import Lilith.tools.system as system
    import Lilith.tools.windows as windows

    HAS_LILITH = True
except ImportError as e:
    print(f"Warning: Lilith tools not available. Error: {e}", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Protocol Definitions
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MCPRequest:
    """Request del protocolo MCP."""

    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPResponse:
    """Response del protocolo MCP."""

    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPServer:
    """
    Servidor MCP (Model Context Protocol).

    Expone tools como endpoints que Hermes puede consumir.
    """

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._executors: Dict[str, callable] = {}

        if HAS_LILITH:
            self._register_lilith_tools()

    def _register_lilith_tools(self):
        """Registra todas las tools de Lilith."""

        # Map de ejecutores usando módulos importados
        executors = {
            "desktop": (desktop.get_tools(), desktop.execute_tool),
            "files": (files.get_tools(), files.execute_tool),
            "system": (system.get_tools(), system.execute_tool),
            "network": (network.get_tools(), network.execute_tool),
            "coding": (coding.get_tools(), coding.execute_tool),
            "windows": (windows.get_tools(), windows.execute_tool),
            "browser": (browser.get_tools(), browser.execute_tool),
        }

        for category, (tools, executor) in executors.items():
            for tool in tools:
                tool_name = tool["function"]["name"]
                self.tools[tool_name] = tool
                self._executors[tool_name] = executor

    def list_tools(self) -> List[Dict[str, Any]]:
        """Lista todas las tools disponibles."""
        return list(self.tools.values())

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta una tool."""
        if name not in self._executors:
            return {"error": f"Tool not found: {name}"}

        try:
            result = self._executors[name](name, arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}

    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Maneja un request MCP."""

        method = request.method

        try:
            if method == "tools/list":
                return MCPResponse(result={"tools": self.list_tools()}, id=request.id)

            elif method == "tools/execute":
                params = request.params or {}
                name = params.get("name")
                arguments = params.get("arguments", {})

                if not name:
                    return MCPResponse(
                        error={
                            "code": "INVALID_PARAMS",
                            "message": "Tool name required",
                        },
                        id=request.id,
                    )

                result = self.execute_tool(name, arguments)

                if "error" in result:
                    return MCPResponse(
                        error={"code": "EXECUTION_ERROR", "message": result["error"]},
                        id=request.id,
                    )

                return MCPResponse(result=result, id=request.id)

            elif method == "ping":
                return MCPResponse(
                    result={"status": "ok", "lilith_connected": HAS_LILITH}
                )

            else:
                return MCPResponse(
                    error={
                        "code": "METHOD_NOT_FOUND",
                        "message": f"Unknown method: {method}",
                    },
                    id=request.id,
                )

        except Exception as e:
            return MCPResponse(
                error={"code": "INTERNAL_ERROR", "message": str(e)}, id=request.id
            )


# ═══════════════════════════════════════════════════════════════════════════════
# JSON-RPC Server (StdIO)
# ═══════════════════════════════════════════════════════════════════════════════


class JSONRPCServer:
    """
    Servidor JSON-RPC sobre stdio.

    Este es el formato que usa MCP por stdio.
    """

    def __init__(self):
        self.mcp = MCPServer()

    def read_request(self) -> Optional[MCPRequest]:
        """Lee un request del stdin."""
        try:
            import sys

            line = sys.stdin.readline()
            if not line:
                return None

            data = json.loads(line.strip())
            return MCPRequest(
                method=data.get("method", ""),
                params=data.get("params"),
                id=data.get("id"),
            )
        except Exception:
            return None

    def write_response(self, response: MCPResponse):
        """Escribe response al stdout."""
        output = {"jsonrpc": "2.0"}

        if response.id is not None:
            output["id"] = response.id

        if response.error:
            output["error"] = response.error
        else:
            output["result"] = response.result

        print(json.dumps(output), flush=True)

    def run(self):
        """Loop principal del servidor."""
        print("Lilith MCP Bridge initialized", file=sys.stderr)
        print(f"Lilith tools available: {len(self.mcp.tools)}", file=sys.stderr)

        while True:
            request = self.read_request()
            if request is None:
                break

            response = self.mcp.handle_request(request)
            self.write_response(response)


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP Server (para testing)
# ═══════════════════════════════════════════════════════════════════════════════


async def http_server(host: str = "127.0.0.1", port: int = 8765):
    """Servidor HTTP simple para testing."""
    from aiohttp import web

    mcp = MCPServer()

    async def handle_list(request):
        return web.json_response({"tools": mcp.list_tools()})

    async def handle_execute(request):
        data = await request.json()
        name = data.get("name")
        arguments = data.get("arguments", {})

        result = mcp.execute_tool(name, arguments)
        return web.json_response(result)

    async def handle_ping(request):
        return web.json_response({"status": "ok", "lilith": HAS_LILITH})

    app = web.Application()
    app.router.add_get("/tools", handle_list)
    app.router.add_post("/execute", handle_execute)
    app.router.add_get("/ping", handle_ping)

    print(f"HTTP MCP Bridge running at http://{host}:{port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print("Lilith MCP Bridge HTTP server started", file=sys.stderr)
    print(f"Available tools: {len(mcp.tools)}", file=sys.stderr)

    # Keep running
    await asyncio.Event().wait()


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Lilith MCP Bridge")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Server mode (stdio for MCP, http for testing)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port")

    args = parser.parse_args()

    if args.mode == "http":
        asyncio.run(http_server(args.host, args.port))
    else:
        server = JSONRPCServer()
        server.run()


if __name__ == "__main__":
    main()
