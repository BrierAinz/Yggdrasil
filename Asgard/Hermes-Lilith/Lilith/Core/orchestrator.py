"""
Orchestrator
============
Orquestador principal de Lilith - maneja tools y conversacion.
Inyecta contexto de memoria relevante en cada interaccion.
Soporta modo streaming y tools dinamicas (nativas + MCP).
"""
import asyncio
import json
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.Core.config import (
    MAX_TOOL_CALLS,
    SKILLS_AUTO_TRIGGER,
    SKILLS_MAX_TRIGGERED,
    SYSTEM_PROMPT,
)
from Lilith.Core.dynamic_tools import DynamicToolRegistry, ToolSource
from Lilith.Core.llm_provider import LLMProvider, get_provider
from Lilith.Core.skill_registry import get_skill_registry
from Lilith.MCP.manager import MCPManager, get_mcp_manager
from Lilith.memory.background_consolidator import BackgroundConsolidator, get_consolidator
from Lilith.memory.enhanced import get_memory
from Lilith.memory.session_store import SessionStore, get_session_store
from Lilith.tools import ALL_TOOLS
from Lilith.tools.browser import execute_tool as execute_browser_tool
from Lilith.tools.coding import execute_tool as execute_coding_tool
from Lilith.tools.desktop import execute_tool as execute_desktop_tool
from Lilith.tools.files import execute_tool as execute_file_tool
from Lilith.tools.network import execute_tool as execute_network_tool
from Lilith.tools.system import execute_tool as execute_system_tool
from Lilith.tools.windows import execute_tool as execute_windows_tool

logger = logging.getLogger("Lilith.Orchestrator")

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


def _run_async(coro):
    """Ejecuta una corrutina async desde contexto sincrono.

    Maneja el caso de ya estar en un event loop (ej: Jupyter, async frameworks)
    creando un nuevo thread con su propio loop si es necesario.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Ya hay un loop corriendo — ejecutar en un thread separado
        result = None
        exception = None

        def _run():
            nonlocal result, exception
            try:
                result = asyncio.run(coro)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=30)
        if exception:
            raise exception
        return result
    else:
        return asyncio.run(coro)


class LilithOrchestrator:
    """Orquestador principal de Lilith con memoria mejorada y tools dinamicas.

    Usa LLMProvider con fallback automatico.
    Si el provider primario (lm_studio) no esta disponible, intenta con
    los providers alternativos (kimi, etc.) automaticamente.

    Integracion con DynamicToolRegistry:
    - Las tools nativas (TOOL_EXECUTORS) se registran al crearse la instancia.
    - Las tools MCP se registran cuando los servidores MCP estan disponibles.
    - El LLM recibe la lista completa de tools (nativas + MCP) en cada llamada.
    - La ejecucion de tools nativa es sincrona; la de MCP es async con fallback.
    """

    def __init__(self, provider: LLMProvider = None):
        if provider is not None:
            self.client = provider
        else:
            self.client = get_provider()
        self.memory = get_memory()
        self.skill_registry = get_skill_registry()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_call_count = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # — Registro unificado de tools (nativas + MCP) —
        self._tool_registry = DynamicToolRegistry()
        self._mcp_manager: Optional[MCPManager] = None
        self._mcp_initialized = False
        self._registry_lock = threading.Lock()

        # — Session Store: persistencia de sesiones con contexto semántico —
        self.session_store: SessionStore = get_session_store()

        # — Background Consolidator: consolidación periódica de memoria —
        self._consolidator: Optional[BackgroundConsolidator] = None

        # Registrar tools nativas
        self._register_native_tools()

        # Intentar registrar tools MCP (lazy — no bloquea si no hay servidores)
        self._try_init_mcp()

    def _register_native_tools(self) -> None:
        """Registra las tools nativas de Lilith en el DynamicToolRegistry."""
        with self._registry_lock:
            count = self._tool_registry.register_native_tools(ALL_TOOLS, TOOL_EXECUTORS)
            logger.info(f"[Orchestrator] Registradas {count} tools nativas")

    def _try_init_mcp(self) -> None:
        """Intenta inicializar MCP y registrar sus tools.

        No lanza excepciones — si MCP no esta disponible, simplemente
        no se registran tools MCP y el comportamiento es identico
        al orchestrator original (solo tools nativas).
        """
        try:
            self._mcp_manager = get_mcp_manager()
            # MCPManager.start() es async — ejecutar en contexto sincrono
            _run_async(self._mcp_manager.start())
            self._mcp_initialized = True

            with self._registry_lock:
                mcp_count = self._tool_registry.register_mcp_tools(self._mcp_manager)
            logger.info(f"[Orchestrator] Registradas {mcp_count} tools MCP")
        except Exception as e:
            # MCP no disponible — comportamiento identico al original
            logger.debug(f"[Orchestrator] MCP no disponible: {e}")
            self._mcp_manager = None
            self._mcp_initialized = False

    def _get_tools_for_llm(self) -> List[Dict]:
        """Obtiene la lista de tools para enviar al LLM.

        Combina tools nativas y MCP en formato OpenAI function calling.
        Si el registry esta vacio (no deberia pasar), cae a ALL_TOOLS hardcoded.
        """
        with self._registry_lock:
            tools = self._tool_registry.get_openai_tools()
        if tools:
            return tools
        # Fallback de seguridad — nunca deberia llegarse aqui
        return ALL_TOOLS

    def _execute_tool(self, tool_name: str, tool_args: Dict) -> Dict:
        """Ejecuta una tool por nombre, buscando primero en executors nativos
        y luego en el registry para tools MCP.

        Args:
            tool_name: Nombre de la tool a ejecutar
            tool_args: Argumentos para la tool

        Returns:
            Resultado de la ejecucion (dict o str)
        """
        # 1. Intentar execution nativa (rapida, sincrona)
        executor = TOOL_EXECUTORS.get(tool_name)
        if executor:
            return executor(tool_name, tool_args)

        # 2. Buscar en el registry (podria ser tool MCP)
        with self._registry_lock:
            tool_info = self._tool_registry.get_tool(tool_name)

        if tool_info is None:
            return {"error": f"Tool no implementada: {tool_name}"}

        # 3. Si es tool MCP, ejecutar via el registry (async -> sync wrapper)
        if tool_info.source == ToolSource.MCP:
            try:
                result = _run_async(self._tool_registry.execute(tool_name, tool_args))
                return result if isinstance(result, dict) else {"result": result}
            except Exception as e:
                logger.error(
                    f"[Orchestrator] Error ejecutando tool MCP '{tool_name}': {e}"
                )
                return {"error": f"Error en tool MCP '{tool_name}': {e}"}

        # 4. Tool registrada pero sin executor
        if tool_info.executor:
            return tool_info.executor(tool_name, tool_args)

        return {"error": f"Tool sin executor: {tool_name}"}

    def refresh_mcp_tools(self) -> Dict[str, int]:
        """Reconecta servidores MCP y re-registra sus tools.

        Util para cuando se configuran nuevos servidores MCP en runtime.

        Returns:
            Dict con estadisticas: {'native': N, 'mcp': N}
        """
        logger.info("[Orchestrator] Refrescando tools MCP...")

        # Cerrar MCP anterior si existe
        if self._mcp_manager and self._mcp_initialized:
            try:
                _run_async(self._mcp_manager.stop())
            except Exception as e:
                logger.warning(f"[Orchestrator] Error cerrando MCP previo: {e}")

        # Limpiar tools MCP del registry
        with self._registry_lock:
            self._tool_registry.clear_mcp_tools()

        # Reiniciar MCP
        self._mcp_initialized = False
        self._try_init_mcp()

        with self._registry_lock:
            stats = self._tool_registry.get_stats()
        return {
            "native": stats["native_tools"],
            "mcp": stats["mcp_tools"],
        }

    def get_registry_stats(self) -> Dict:
        """Retorna estadisticas del registry de tools."""
        with self._registry_lock:
            return self._tool_registry.get_stats()

    def get_provider_info(self) -> dict:
        """Retorna informacion del provider activo."""
        info = {
            "name": self.client.name,
            "model": self.client.model,
            "type": self.client.provider_type,
            "available": self.client.is_available(),
        }
        with self._registry_lock:
            info["tools"] = self._tool_registry.get_stats()
        return info

    def switch_provider(self, name: str) -> None:
        """Cambia al proveedor LLM especificado por nombre.

        Util para forzar un provider remoto (ej. 'kimi') cuando el
        local no esta disponible, o viceversa.
        """
        self.client = get_provider(name)

    def reset(self):
        """Reinicia la conversacion, guardando la sesión actual primero."""
        # Guardar sesión actual antes de reiniciar
        self._save_current_session()

        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.tool_call_count = 0
        # Generar nuevo session_id para la nueva conversación
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _build_system_prompt(self, user_input: str) -> str:
        """Construye el system prompt con contexto de memoria, skills y sesiones pasadas."""
        base = SYSTEM_PROMPT

        # Inyectar contexto de memoria
        context = ""
        try:
            context = self.memory.get_relevant_context(user_input, max_tokens=1200)
            if context:
                base += f"\n\n=== CONTEXTO RELEVANTE DE MEMORIA ===\n{context}\n=== FIN CONTEXTO ==="
        except Exception:
            pass

        # Inyectar contexto de sesiones pasadas (SessionStore)
        session_context = self._inject_session_context(user_input)
        if session_context:
            base += f"\n\n{session_context}"

        # Inyectar skills activos
        if SKILLS_AUTO_TRIGGER:
            try:
                triggered = self.skill_registry.get_triggered_skills(
                    user_input, max_skills=SKILLS_MAX_TRIGGERED
                )
                if triggered:
                    base += "\n\n=== SKILLS ACTIVOS ===\n"
                    for skill in triggered:
                        # Renderizar template si existe, sino usar content
                        rendered = skill.render(
                            user_input=user_input,
                            context=context if context else "",
                            memory="",
                            skills=", ".join(s.name for s in triggered),
                        )
                        if rendered:
                            preview = rendered[:2000]
                            if len(rendered) > 2000:
                                preview += "\n... (truncado)"
                            base += f"\n[{skill.name}] {skill.description}\n{preview}\n"
                        else:
                            content_preview = skill.content[:2000]
                            if len(skill.content) > 2000:
                                content_preview += "\n... (truncado)"
                            base += f"\n[{skill.name}] {skill.description}\n{content_preview}\n"
                        # Registrar uso
                        self.skill_registry.record_trigger(skill.name)
                    base += "\n=== FIN SKILLS ==="
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
        """Procesa input del usuario y retorna respuesta completa.

        Usa DynamicToolRegistry para descubrir tools disponibles (nativas + MCP)
        y TOOL_EXECUTORS + registry para la ejecucion.
        """
        system_content = self._build_system_prompt(user_input)
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": system_content}

        self.messages.append({"role": "user", "content": user_input})
        tools_used = []

        # Obtener tools del registry (nativas + MCP)
        available_tools = self._get_tools_for_llm()

        while True:
            self.tool_call_count += 1
            if self.tool_call_count > MAX_TOOL_CALLS:
                return "Demasiadas llamadas a tools. Parece que hay un loop infinito."

            response = self.client.chat(self.messages, tools=available_tools)

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

                result = self._execute_tool(tool_name, tool_args)

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

    def start_consolidator(self, interval_seconds: int = 300):
        """Inicia el BackgroundConsolidator para consolidación periódica.

        El consolidador opera en segundo plano como un ente ancestral que
        teje los hilos de memoria en la penumbra eterna.
        """
        if self._consolidator is not None and self._consolidator.is_running:
            logger.info("[Orchestrator] BackgroundConsolidator ya está ejecutándose.")
            return
        self._consolidator = get_consolidator()
        self._consolidator.start()
        logger.info("[Orchestrator] BackgroundConsolidator iniciado (intervalo=%ds)", interval_seconds)

    def stop_consolidator(self):
        """Detiene el BackgroundConsolidator."""
        if self._consolidator is not None and self._consolidator.is_running:
            self._consolidator.stop()
            logger.info("[Orchestrator] BackgroundConsolidator detenido.")

    def get_consolidator_stats(self) -> Dict:
        """Retorna estadísticas del consolidador de fondo."""
        if self._consolidator is None:
            return {"running": False, "cycles_run": 0, "episodes_merged": 0, "facts_promoted": 0}
        return {
            "running": self._consolidator.is_running,
            "last_run": self._consolidator.last_run,
            **self._consolidator.stats,
        }

    def _save_current_session(self):
        """Guarda la sesión actual en el SessionStore.

        Las sombras de esta conversación se sellan en el archivo eterno
        para que los ecos persistan más allá de su conclusión.
        """
        try:
            episodes = self.memory.get_recent_episodes(count=200, session_id=self.session_id)
            summary = self.session_store.auto_summary(episodes)
            if not summary:
                summary = f"Sesión {self.session_id} — {len(self.messages)} mensajes"
            self.session_store.save_session(
                session_id=self.session_id,
                summary=summary,
                episode_count=len(episodes),
                metadata={"tool_calls": self.tool_call_count},
            )
            logger.info("[Orchestrator] Sesión %s guardada en SessionStore", self.session_id)
        except Exception as e:
            logger.warning("[Orchestrator] Error guardando sesión: %s", e)

    def _inject_session_context(self, user_input: str) -> str:
        """Inyecta contexto de sesiones pasadas relevantes al prompt.

        Los susurros de sesiones olvidadas se entretejen en el sistema
        para que la sabiduría ancestral ilumine las tinieblas.
        """
        try:
            context = self.session_store.get_relevant_context(
                query=user_input, max_sessions=3, max_tokens=800
            )
            if context:
                return context
        except Exception as e:
            logger.debug("[Orchestrator] Error inyectando contexto de sesión: %s", e)
        return ""

    def close(self):
        """Cierra recursos, incluyendo MCP y SessionStore."""
        # Guardar sesión antes de cerrar
        self._save_current_session()
        # Detener consolidador
        self.stop_consolidator()
        if self._mcp_manager and self._mcp_initialized:
            try:
                _run_async(self._mcp_manager.stop())
            except Exception as e:
                logger.warning(f"[Orchestrator] Error cerrando MCP: {e}")
