"""
Swarm Executor - Ejecutor de tools para agentes swarm
=====================================================
Conecta SwarmAgent con el LLM y las tools reales del sistema.
Usa LLMProvider con fallback automatico en lugar de LMStudioClient directo.
"""
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.Core.config import MAX_TOOL_CALLS
from Lilith.Core.llm_provider import LLMProvider, get_provider
from Lilith.Swarm.prompts import build_agent_prompt
from Lilith.tools import ALL_TOOLS
from Lilith.tools.browser import execute_tool as execute_browser_tool
from Lilith.tools.coding import execute_tool as execute_coding_tool
from Lilith.tools.desktop import execute_tool as execute_desktop_tool
from Lilith.tools.files import execute_tool as execute_file_tool
from Lilith.tools.network import execute_tool as execute_network_tool
from Lilith.tools.system import execute_tool as execute_system_tool
from Lilith.tools.windows import execute_tool as execute_windows_tool

TOOL_EXECUTORS = {
    "screenshot": execute_desktop_tool,
    "get_cursor_position": execute_desktop_tool,
    "list_windows": execute_desktop_tool,
    "read_file": execute_file_tool,
    "write_file": execute_file_tool,
    "list_directory": execute_file_tool,
    "file_exists": execute_file_tool,
    "run_terminal": execute_system_tool,
    "open_vscode": execute_system_tool,
    "open_application": execute_system_tool,
    "ping": execute_network_tool,
    "check_port": execute_network_tool,
    "get_network_info": execute_network_tool,
    "download_file": execute_network_tool,
    "check_internet": execute_network_tool,
    "run_git": execute_coding_tool,
    "run_npm": execute_coding_tool,
    "run_python_script": execute_coding_tool,
    "search_in_files": execute_coding_tool,
    "get_git_status": execute_coding_tool,
    "list_git_branches": execute_coding_tool,
    "list_processes": execute_windows_tool,
    "kill_process": execute_windows_tool,
    "get_system_info": execute_windows_tool,
    "get_disk_space": execute_windows_tool,
    "list_services": execute_windows_tool,
    "start_service": execute_windows_tool,
    "stop_service": execute_windows_tool,
    "open_url": execute_browser_tool,
    "search_google": execute_browser_tool,
    "clipboard_read": execute_browser_tool,
    "clipboard_write": execute_browser_tool,
    "type_text": execute_browser_tool,
    "press_key": execute_browser_tool,
    "copy_to_clipboard": execute_browser_tool,
}


class SwarmExecutor:
    """Ejecutor de tareas para agentes swarm usando LLM con fallback.

    Acepta opcionalmente un LLMProvider para control expliito, o usa
    get_provider() para fallback automatico entre providers.
    """

    def __init__(self, llm_client: Optional[LLMProvider] = None):
        self.client = llm_client or get_provider()
        self.max_tool_calls = MAX_TOOL_CALLS

    def execute_task(
        self,
        task: str,
        context: Dict,
        capabilities: List[str],
        stop_event=None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea usando el LLM y tools reales.

        Args:
            task: Descripcion de la tarea
            context: Dict con files_to_read, notes, etc.
            capabilities: Lista de capabilities del agente
            stop_event: threading.Event para detencion
            progress_callback: funcion(msg) para reportar progreso

        Returns:
            Dict con success, output, error, files_modified
        """
        system_prompt = build_agent_prompt(task, context, capabilities)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Ejecuta esta tarea: {task}"},
        ]

        tools_used = []
        files_modified = []
        tool_call_count = 0

        try:
            while True:
                # Verificar stop
                if stop_event and stop_event.is_set():
                    return {
                        "success": False,
                        "output": "",
                        "error": "Agent stopped by user",
                        "files_modified": files_modified,
                    }

                tool_call_count += 1
                if tool_call_count > self.max_tool_calls:
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Max tool calls exceeded ({self.max_tool_calls})",
                        "files_modified": files_modified,
                    }

                # Llamar al LLM
                response = self.client.chat(messages, tools=ALL_TOOLS)

                if "error" in response:
                    return {
                        "success": False,
                        "output": "",
                        "error": f"LLM error: {response['error']}",
                        "files_modified": files_modified,
                    }

                choices = response.get("choices", [])
                if not choices:
                    return {
                        "success": False,
                        "output": "",
                        "error": "No response from LLM",
                        "files_modified": files_modified,
                    }

                choice = choices[0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                content = message.get("content", "")

                # Reportar progreso si hay contenido
                if content and progress_callback:
                    progress_callback({"type": "thinking", "content": content})

                # Si no hay tool calls, la tarea termino
                if not tool_calls:
                    messages.append({"role": "assistant", "content": content})
                    return {
                        "success": True,
                        "output": content,
                        "error": None,
                        "files_modified": files_modified,
                    }

                # Ejecutar tools
                for tool_call in tool_calls:
                    if stop_event and stop_event.is_set():
                        return {
                            "success": False,
                            "output": "",
                            "error": "Agent stopped by user",
                            "files_modified": files_modified,
                        }

                    function = tool_call.get("function", {})
                    tool_name = function.get("name", "")
                    tool_args = function.get("arguments", {})
                    if isinstance(tool_args, str):
                        try:
                            tool_args = json.loads(tool_args)
                        except Exception:
                            tool_args = {}

                    tools_used.append(tool_name)

                    # Reportar tool execution
                    if progress_callback:
                        progress_callback({"type": "tool", "name": tool_name})

                    # Ejecutar
                    executor = TOOL_EXECUTORS.get(tool_name)
                    if executor:
                        result = executor(tool_name, tool_args)
                    else:
                        result = {"error": f"Tool not implemented: {tool_name}"}

                    # Trackear archivos modificados
                    if tool_name in ("write_file",) and "path" in tool_args:
                        files_modified.append(tool_args["path"])

                    # Agregar resultado al contexto
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.get("id", ""),
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "files_modified": files_modified,
            }

    def close(self):
        """Cierra recursos. LLMProvider no necesita close (usa httpx function-scoped)."""
        pass
