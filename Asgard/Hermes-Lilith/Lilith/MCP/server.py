"""
LilithMCPServer — Servidor MCP que expone skills y tools de Lilith
=====================================================================
Implementacion simplificada del Model Context Protocol (MCP) que permite
a clientes externos descubrir y ejecutar las tools de Lilith via stdio.

Transporte: stdin/stdout JSON-RPC 2.0
Config en TOML: [mcp] enabled=true, port=5700

Se integra con:
  - SkillRegistry para auto-discovery de skills como tools MCP
  - Orchestrator para ejecutar tools con el pipeline completo
"""

import json
import logging
import sys
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from Lilith.MCP.protocol import (
    JSONRPC_VERSION,
    MCP_PROTOCOL_VERSION,
    MCPMethod,
    MCPResource,
    MCPTool,
    MCPToolParameter,
    make_error,
    make_response,
)

logger = logging.getLogger("Lilith.MCP.Server")


# ═══════════════════════════════════════════════════════════════════════════════
# Tipos de datos del servidor
# ═══════════════════════════════════════════════════════════════════════════════


class LilithMCPServer:
    """Servidor MCP que expone skills y tools de Lilith.

    Implementa el protocolo MCP sobre stdio (stdin/stdout JSON-RPC 2.0),
    permitiendo a clientes externos como Claude Desktop, VS Code, o Hermes
    descubrir y ejecutar las tools de Lilith.

    Endpoints soportados:
        - initialize           — Handshake del protocolo
        - ping                 — Health check
        - tools/list           — Lista tools disponibles
        - tools/call           — Ejecuta una tool
        - resources/list       — Lista recursos
        - resources/read       — Lee un recurso
        - prompts/list         — Lista prompts (skills)
        - prompts/get          — Obtiene un prompt

    Uso:
        server = LilithMCPServer()
        server.register_tool("my_tool", schema, executor)
        server.start_stdio()  # loop de lectura de stdin
    """

    def __init__(self, name: str = "lilith", version: str = "3.0.0"):
        self.name = name
        self.version = version
        self.protocol_version = MCP_PROTOCOL_VERSION

        # Registro de tools, recursos y prompts
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_executors: Dict[str, Callable] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._resource_readers: Dict[str, Callable] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}

        # Estado del servidor
        self._running = False
        self._request_id = 0
        self._initialized = False

        # Auto-registrar tools de Lilith
        self._register_lilith_tools()

    # ═══════════════════════════════════════════════════════════════════════
    # Registro de tools, recursos y prompts
    # ═══════════════════════════════════════════════════════════════════════

    def register_tool(
        self,
        name: str,
        description: str = "",
        parameters: Optional[List[Dict[str, Any]]] = None,
        executor: Optional[Callable] = None,
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra una tool en el servidor MCP.

        Args:
            name: Nombre único de la tool.
            description: Descripción legible de la tool.
            parameters: Lista de parámetros (dict con name, type, description, required).
            executor: Función callable que ejecuta la tool. Recibe un dict con argumentos.
            input_schema: JSON Schema completo. Si se provee, se usa en vez de parameters.
        """
        tool_def: Dict[str, Any] = {
            "name": name,
            "description": description or f"Lilith tool: {name}",
        }

        if input_schema:
            tool_def["inputSchema"] = input_schema
        elif parameters:
            props = {}
            required = []
            for p in parameters:
                p_name = p["name"]
                prop: Dict[str, Any] = {"type": p.get("type", "string")}
                if p.get("description"):
                    prop["description"] = p["description"]
                if p.get("enum"):
                    prop["enum"] = p["enum"]
                props[p_name] = prop
                if p.get("required", False):
                    required.append(p_name)
            schema: Dict[str, Any] = {"type": "object", "properties": props}
            if required:
                schema["required"] = required
            tool_def["inputSchema"] = schema
        else:
            tool_def["inputSchema"] = {
                "type": "object",
                "properties": {},
            }

        self._tools[name] = tool_def
        if executor:
            self._tool_executors[name] = executor
        logger.debug("[MCPServer] Tool registrada: %s", name)

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "text/plain",
        reader: Optional[Callable] = None,
    ) -> None:
        """Registra un recurso en el servidor MCP.

        Args:
            uri: URI única del recurso (ej: "lilith://memory/stats").
            name: Nombre legible del recurso.
            description: Descripción del recurso.
            mime_type: Tipo MIME del contenido.
            reader: Función callable que retorna el contenido del recurso.
        """
        self._resources[uri] = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            server_name=self.name,
        )
        if reader:
            self._resource_readers[uri] = reader
        logger.debug("[MCPServer] Recurso registrado: %s", uri)

    def register_prompt(
        self,
        name: str,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None,
        template: str = "",
    ) -> None:
        """Registra un prompt template (skill) en el servidor MCP.

        Args:
            name: Nombre del prompt.
            description: Descripción del prompt.
            arguments: Lista de argumentos que acepta el prompt.
            template: Template del prompt con {variables}.
        """
        self._prompts[name] = {
            "name": name,
            "description": description,
            "arguments": arguments or [],
            "template": template,
        }
        logger.debug("[MCPServer] Prompt registrado: %s", name)

    def _register_lilith_tools(self) -> None:
        """Auto-registra las tools nativas de Lilith como tools MCP."""
        try:
            import Lilith.tools as LilithTools
            for tool_def in LilithTools.ALL_TOOLS:
                func = tool_def.get("function", {})
                name = func.get("name", "")
                desc = func.get("description", "")
                params = func.get("parameters", {})
                if name:
                    self.register_tool(
                        name=name,
                        description=desc,
                        input_schema=params,
                        executor=self._make_tool_executor(name),
                    )
        except ImportError:
            logger.warning("[MCPServer] No se pudieron importar las tools de Lilith")

    def _make_tool_executor(self, tool_name: str) -> Callable:
        """Crea un executor que delega al Orchestrator de Lilith."""
        def executor(arguments: Dict[str, Any]) -> Any:
            # Buscar en los ejecutores de tools del Orchestrator
            try:
                from Lilith.Core.orchestrator import LilithOrchestrator
                # Intentar usar el Orchestrator existente si está disponible
                orch = LilithOrchestrator()
                result = orch._execute_tool(tool_name, arguments)
                return result
            except Exception:
                # Fallback: ejecución directa por módulo
                return self._execute_tool_fallback(tool_name, arguments)
        return executor

    def _execute_tool_fallback(self, name: str, args: Dict[str, Any]) -> Any:
        """Ejecución directa de tools sin Orchestrator (fallback)."""
        import Lilith.tools.browser as browser
        import Lilith.tools.coding as coding
        import Lilith.tools.desktop as desktop
        import Lilith.tools.files as files
        import Lilith.tools.network as network
        import Lilith.tools.system as system
        import Lilith.tools.windows as windows

        module_map = {
            "browser": browser,
            "coding": coding,
            "desktop": desktop,
            "files": files,
            "network": network,
            "system": system,
            "windows": windows,
        }
        for mod in module_map.values():
            for tool in mod.get_tools():
                if tool["function"]["name"] == name:
                    return mod.execute_tool(name, args)
        raise ValueError(f"Tool no encontrada: {name}")

    # ═══════════════════════════════════════════════════════════════════════
    # Manejo de requests JSON-RPC
    # ═══════════════════════════════════════════════════════════════════════

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Maneja un request JSON-RPC y devuelve la respuesta.

        Este es el dispatcher central del servidor MCP.
        """
        method = request.get("method", "")
        req_id = request.get("id", 0)
        params = request.get("params", {})

        try:
            if method == "initialize":
                return self._handle_initialize(req_id, params)
            elif method == "ping":
                return self._handle_ping(req_id)
            elif method == MCPMethod.LIST_TOOLS.value:
                return self._handle_tools_list(req_id)
            elif method == MCPMethod.CALL_TOOL.value:
                return self._handle_tools_call(req_id, params)
            elif method == MCPMethod.LIST_RESOURCES.value:
                return self._handle_resources_list(req_id)
            elif method == MCPMethod.READ_RESOURCE.value:
                return self._handle_resources_read(req_id, params)
            elif method == MCPMethod.LIST_PROMPTS.value:
                return self._handle_prompts_list(req_id)
            elif method == MCPMethod.GET_PROMPT.value:
                return self._handle_prompts_get(req_id, params)
            else:
                return make_error(req_id, -32601, f"Method not found: {method}")
        except Exception as e:
            logger.error("[MCPServer] Error manejando request: %s", e)
            return make_error(req_id, -32603, f"Internal error: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    # Handlers de protocolo
    # ═══════════════════════════════════════════════════════════════════════

    def _handle_initialize(self, req_id: int, params: Dict) -> Dict[str, Any]:
        """Maneja el handshake initialize del protocolo MCP."""
        self._initialized = True
        result = {
            "protocolVersion": self.protocol_version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }
        return make_response(req_id, result)

    def _handle_ping(self, req_id: int) -> Dict[str, Any]:
        """Responde a un ping de health check."""
        return make_response(req_id, {"status": "ok", "timestamp": datetime.now().isoformat()})

    def _handle_tools_list(self, req_id: int) -> Dict[str, Any]:
        """Lista todas las tools disponibles."""
        tools = []
        for name, tool_def in self._tools.items():
            tools.append({
                "name": tool_def["name"],
                "description": tool_def["description"],
                "inputSchema": tool_def.get("inputSchema", {"type": "object", "properties": {}}),
            })
        return make_response(req_id, {"tools": tools})

    def _handle_tools_call(self, req_id: int, params: Dict) -> Dict[str, Any]:
        """Ejecuta una tool y devuelve el resultado."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if not tool_name:
            return make_error(req_id, -32602, "Missing required parameter: name")

        if tool_name not in self._tools:
            return make_error(req_id, -32602, f"Tool not found: {tool_name}")

        executor = self._tool_executors.get(tool_name)
        if not executor:
            return make_error(req_id, -32603, f"No executor for tool: {tool_name}")

        try:
            result = executor(arguments)
            # MCP spec: los resultados van en content
            content = []
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
            elif isinstance(result, str):
                content = [{"type": "text", "text": result}]
            else:
                content = [{"type": "text", "text": json.dumps(result, default=str, ensure_ascii=False)}]

            return make_response(req_id, {"content": content, "isError": False})
        except Exception as e:
            return make_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    def _handle_resources_list(self, req_id: int) -> Dict[str, Any]:
        """Lista todos los recursos disponibles."""
        resources = []
        for uri, res in self._resources.items():
            resources.append({
                "uri": res.uri,
                "name": res.name,
                "description": res.description,
                "mimeType": res.mime_type,
            })
        return make_response(req_id, {"resources": resources})

    def _handle_resources_read(self, req_id: int, params: Dict) -> Dict[str, Any]:
        """Lee el contenido de un recurso."""
        uri = params.get("uri", "")
        if not uri:
            return make_error(req_id, -32602, "Missing required parameter: uri")

        if uri not in self._resources:
            return make_error(req_id, -32602, f"Resource not found: {uri}")

        reader = self._resource_readers.get(uri)
        if reader:
            try:
                content = reader(uri)
            except Exception as e:
                return make_error(req_id, -32603, f"Error reading resource: {e}")
        else:
            content = f"Resource: {uri}"

        res = self._resources[uri]
        return make_response(req_id, {
            "contents": [{
                "uri": uri,
                "mimeType": res.mime_type,
                "text": str(content),
            }]
        })

    def _handle_prompts_list(self, req_id: int) -> Dict[str, Any]:
        """Lista todos los prompts (skills) disponibles."""
        prompts = []
        for name, pdef in self._prompts.items():
            prompts.append({
                "name": pdef["name"],
                "description": pdef["description"],
                "arguments": pdef.get("arguments", []),
            })
        return make_response(req_id, {"prompts": prompts})

    def _handle_prompts_get(self, req_id: int, params: Dict) -> Dict[str, Any]:
        """Obtiene un prompt renderizado con los argumentos dados."""
        name = params.get("name", "")
        args = params.get("arguments", {})

        if not name:
            return make_error(req_id, -32602, "Missing required parameter: name")

        if name not in self._prompts:
            return make_error(req_id, -32602, f"Prompt not found: {name}")

        pdef = self._prompts[name]
        template = pdef.get("template", "")

        # Renderizar template con los argumentos
        try:
            rendered = template.format(**args) if args else template
        except KeyError as e:
            return make_error(req_id, -32602, f"Missing argument: {e}")

        messages = [{"role": "user", "content": {"type": "text", "text": rendered}}]
        return make_response(req_id, {
            "description": pdef["description"],
            "messages": messages,
        })

    # ═══════════════════════════════════════════════════════════════════════
    # Registro automático de skills como prompts MCP
    # ═══════════════════════════════════════════════════════════════════════

    def register_skills_as_prompts(self) -> int:
        """Auto-descubre skills del SkillRegistry y los registra como prompts MCP.

        Returns:
            Número de skills registrados como prompts.
        """
        try:
            from Lilith.Core.skill_registry import get_skill_registry
            registry = get_skill_registry()
            skills = registry.list_skills()
            count = 0
            for skill in skills:
                args = []
                if hasattr(skill, "trigger") and skill.trigger:
                    args.append({
                        "name": "query",
                        "description": f"Query que activa el skill {skill.name}",
                        "required": False,
                    })

                self.register_prompt(
                    name=skill.name,
                    description=skill.description or f"Skill arcano: {skill.name}",
                    arguments=args,
                    template=skill.system_prompt if hasattr(skill, "system_prompt") and skill.system_prompt else f"Ejecuta el skill {skill.name}",
                )
                count += 1
            logger.info("[MCPServer] %d skills registrados como prompts", count)
            return count
        except ImportError:
            logger.warning("[MCPServer] SkillRegistry no disponible")
            return 0

    # ═══════════════════════════════════════════════════════════════════════
    # StdIO transport
    # ═══════════════════════════════════════════════════════════════════════

    def start_stdio(self) -> None:
        """Inicia el servidor MCP leyendo JSON-RPC desde stdin.

        Lee líneas de stdin, cada una es un request JSON-RPC.
        Escribe respuestas JSON-RPC a stdout.
        Errores y logs van a stderr.
        """
        self._running = True
        logger.info("[MCPServer] Servidor MCP iniciado (stdio) — %s v%s", self.name, self.version)

        # Enviar notificación de inicialización (para clientes que lo esperen)
        init_notification = {
            "jsonrpc": JSONRPC_VERSION,
            "method": "notifications/message",
            "params": {
                "level": "info",
                "data": f"Lilith MCP Server v{self.version} ready",
            },
        }
        sys.stdout.write(json.dumps(init_notification) + "\n")
        sys.stdout.flush()

        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    response = make_error(0, -32700, f"Parse error: {e}")
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    continue

                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("[MCPServer] Error en loop stdio: %s", e)
                error_resp = make_error(0, -32603, f"Internal error: {e}")
                sys.stdout.write(json.dumps(error_resp) + "\n")
                sys.stdout.flush()

        self._running = False
        logger.info("[MCPServer] Servidor MCP detenido")

    def stop(self) -> None:
        """Detiene el servidor MCP."""
        self._running = False

    # ═══════════════════════════════════════════════════════════════════════
    # Status y debug
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado del servidor MCP."""
        return {
            "name": self.name,
            "version": self.version,
            "protocol_version": self.protocol_version,
            "initialized": self._initialized,
            "running": self._running,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
            "tools": list(self._tools.keys()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton y CLI
# ═══════════════════════════════════════════════════════════════════════════════

_server_instance: Optional[LilithMCPServer] = None


def get_mcp_server() -> LilithMCPServer:
    """Obtiene la instancia singleton del servidor MCP."""
    global _server_instance
    if _server_instance is None:
        _server_instance = LilithMCPServer()
    return _server_instance


def main():
    """Punto de entrada para ejecutar el servidor MCP standalone."""
    import argparse

    parser = argparse.ArgumentParser(description="Lilith MCP Server")
    parser.add_argument("--name", default="lilith", help="Nombre del servidor")
    parser.add_argument("--version", default="3.0.0", help="Versión del servidor")
    args = parser.parse_args()

    server = LilithMCPServer(name=args.name, version=args.version)

    # Registrar skills como prompts MCP
    server.register_skills_as_prompts()

    # Iniciar loop stdio
    server.start_stdio()


if __name__ == "__main__":
    main()