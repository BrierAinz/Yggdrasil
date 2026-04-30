"""
Orchestrator
============
Orquestador principal de Lilith - maneja tools y conversacion.
Inyecta contexto de memoria relevante en cada interaccion.
Soporta modo streaming.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.Core.config import MAX_TOOL_CALLS, SYSTEM_PROMPT
from Lilith.Core.llm_client import LMStudioClient
from Lilith.memory.enhanced import get_memory
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


class LilithOrchestrator:
    """Orquestador principal de Lilith con memoria mejorada."""

    def __init__(self):
        self.client = LMStudioClient()
        self.memory = get_memory()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_call_count = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def reset(self):
        """Reinicia la conversacion."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_call_count = 0

    def _build_system_prompt(self, user_input: str) -> str:
        """Construye el system prompt con contexto de memoria."""
        base = SYSTEM_PROMPT
        try:
            context = self.memory.get_relevant_context(user_input, max_tokens=1200)
            if context:
                base += f"\n\n=== CONTEXTO RELEVANTE DE MEMORIA ===\n{context}\n=== FIN CONTEXTO ==="
        except Exception:
            pass
        return base

    def _should_use_rag(self, text: str) -> bool:
        t = text.lower()
        factual_keywords = [
            "que",
            "cual",
            "cuales",
            "como",
            "donde",
            "cuando",
            "quien",
            "quienes",
            "explica",
            "busca",
            "encuentra",
            "muestra",
            "dime",
            "cuentame",
            "codigo",
            "archivo",
            "documento",
            "proyecto",
            "yggdrasil",
            "lilith",
            "configuracion",
            "implementa",
            "funcion",
            "clase",
            "metodo",
            "what",
            "how",
            "where",
            "when",
            "who",
            "explain",
            "find",
            "search",
            "show",
            "code",
            "file",
            "document",
            "project",
            "config",
            "implement",
        ]
        return any(kw in t for kw in factual_keywords)

    def chat(self, user_input: str) -> str:
        """Procesa input del usuario y retorna respuesta completa."""
        system_content = self._build_system_prompt(user_input)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": system_content}

        self.messages.append({"role": "user", "content": user_input})
        tools_used = []

        while True:
            self.tool_call_count += 1
            if self.tool_call_count > MAX_TOOL_CALLS:
                return "Demasiadas llamadas a tools. Parece que hay un loop infinito."

            response = self.client.chat(self.messages, tools=ALL_TOOLS)

            if "error" in response:
                return f"Error: {response['error']}"

            choices = response.get("choices", [])
            if not choices:
                return "No hay respuesta del modelo"

            choice = choices[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                response_content = message.get("content", "")
                self.messages.append({"role": "assistant", "content": response_content})
                try:
                    self.memory.add_episode(
                        user_input=user_input,
                        response=response_content,
                        tools_used=tools_used,
                        session_id=self.session_id,
                    )
                except Exception:
                    pass
                return response_content

            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                tool_name = function.get("name")
                tool_args = function.get("arguments", {})
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}

                tools_used.append(tool_name)
                print(f"  [TOOL] Ejecutando: {tool_name}")

                executor = TOOL_EXECUTORS.get(tool_name)
                if executor:
                    result = executor(tool_name, tool_args)
                else:
                    result = {"error": f"Tool no implementada: {tool_name}"}

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

    def chat_stream(self, user_input: str) -> Iterator[str]:
        """Procesa input y retorna chunks de texto en tiempo real.

        NOTA: El modo streaming NO soporta tool-calling interactivo
        porque requeriria parsear function_call en medio del stream.
        Para tareas con tools, usar chat() normal.
        """
        system_content = self._build_system_prompt(user_input)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": system_content}

        self.messages.append({"role": "user", "content": user_input})

        full_response = []
        for chunk in self.client.chat_stream(self.messages, tools=None):
            full_response.append(chunk)
            yield chunk

        response_text = "".join(full_response)
        self.messages.append({"role": "assistant", "content": response_text})
        try:
            self.memory.add_episode(
                user_input=user_input,
                response=response_text,
                tools_used=[],
                session_id=self.session_id,
            )
        except Exception:
            pass

    def get_history(self) -> List[Dict]:
        """Retorna historial de mensajes (sin system)."""
        return self.messages[1:]

    def close(self):
        """Cierra recursos."""
        self.client.close()
