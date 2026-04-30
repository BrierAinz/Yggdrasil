#!/usr/bin/env python3
"""
Lilith - Asistente Personal CLI
================================
CLI Dark Fantasy para Lilith (LM Studio + tools + streaming).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import Lilith.Core.llm_client as llm
import Lilith.Core.orchestrator as orch
import Lilith.tools as Lilith_tools
from Lilith.Agents.agent_manager import AgentCapability, AgentManager, get_agent_manager
from Lilith.auto_start import get_auto_start
from Lilith.memory.enhanced import EnhancedMemory, get_memory
from Lilith.notifications import get_notifications
from Lilith.Plugins.plugin_manager import get_plugin_registry
from Lilith.RAG.rag_engine import get_rag_engine
from Lilith.Scheduler.task_scheduler import TaskScheduler, TaskStatus, get_scheduler


# ═══════════════════════════════════════════════════════════════════════════════
# DARK FANTASY ANSI THEME
# ═══════════════════════════════════════════════════════════════════════════════
class C:
    """Dark Fantasy Color Palette."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    BG_BLACK = "\033[40m"
    BG_DARK = "\033[48;5;235m"

    CRIMSON = "\033[38;5;196m"
    BLOOD = "\033[38;5;88m"
    SHADOW = "\033[38;5;240m"

    GOLD = "\033[38;5;220m"
    ANCIENT_GOLD = "\033[38;5;178m"
    EMBER = "\033[38;5;214m"

    MYSTIC = "\033[38;5;81m"
    VOID = "\033[38;5;99m"
    ETHER = "\033[38;5;141m"

    BONE = "\033[38;5;252m"
    GHOST = "\033[38;5;250m"
    PARCHMENT = "\033[38;5;229m"

    RUNES = "\033[38;5;172m"
    CORRUPT = "\033[38;5;9m"
    HEAL = "\033[38;5;82m"
    FROST = "\033[38;5;75m"


class S:
    """Dark Fantasy Styles."""

    TITLE = f"{C.GOLD}{C.BOLD}"
    SUBTITLE = f"{C.EMBER}{C.BOLD}"
    PROMPT = f"{C.CRIMSON}{C.BOLD}"
    USER = f"{C.VOID}{C.BOLD}"
    ASSISTANT = f"{C.ETHER}{C.BOLD}"
    TOOL = f"{C.MYSTIC}{C.BOLD}"
    SUCCESS = f"{C.HEAL}{C.BOLD}"
    WARNING = f"{C.EMBER}"
    ERROR = f"{C.CORRUPT}{C.BOLD}"
    INFO = f"{C.FROST}{C.BOLD}"
    DIM = f"{C.SHADOW}"
    DIVIDER = f"{C.ANCIENT_GOLD}"
    BOX = f"{C.GOLD}"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


# ═══════════════════════════════════════════════════════════════════════════════
# LILITH CLI - DARK FANTASY EDITION
# ════════════════════════════════════════════════════════════════════════════════
class LilithCLI:
    """CLI Dark Fantasy para Lilith."""

    COMMANDS = {
        "exit": "Abandonar el realm",
        "quit": "Abandonar el realm",
        "q": "Abandonar el realm",
        "clear": "Limpiar visor",
        "cls": "Limpiar visor",
        "history": "Ver pergaminos del pasado",
        "sessions": "Ver sesiones guardadas",
        "reset": "Reiniciar conversacion",
        "tools": "Ver arsenal de herramientas",
        "status": "Estado completo del realm",
        "help": "Mostrar this grimoario",
        "h": "Mostrar this grimoario",
        "memory": "Ver memorias de Lilith",
        "recall": "Buscar en memorias",
        "agents": "Ver sub-agentes",
        "tasks": "Ver tareas programadas",
        "index": "Indexar archivos/carpeta",
        "search": "Buscar en documentos indexados",
        "plugins": "Ver plugins instalados",
        "autostart": "Configurar auto-arranque",
        "notify": "Enviar notificacion de prueba",
        "stream": "Toggle modo streaming",
        "compact": "Comprimir memorias antiguas",
    }

    def __init__(self):
        self.orch = orch.LilithOrchestrator()
        self.memory = get_memory()
        self.session_id = "default"
        self.msg_count = 0
        self.streaming_mode = False

    def p(self, msg, style=S.INFO):
        print(f"{style}{msg}{C.RESET}")

    def div(self, char="─"):
        self.p(f"{char * 70}", S.DIM)

    def print_banner(self, model_name: str = "Local Model"):
        tool_count = len(Lilith_tools.ALL_TOOLS)
        model_display = model_name[:22]
        line = f"{model_display} . Midgard . {tool_count} Tools"
        pad = max(0, (70 - len(line)) // 2)
        spad = " " * pad
        rpad = " " * (70 - pad - len(line))
        banner = (
            f"\n{C.GOLD}╔══════════════════════════════════════════════════════════╗{C.RESET}\n"
            f"{C.GOLD}║{C.RESET}                                                          {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}              ██╗   ██╗ ██████╗ ██╗   ██╗    ███████╗███████╗       {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}              ██║   ██║██╔═══██╗██║   ██║    ██╔════╝██╔════╝       {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}              ██║   ██║██║   ██║██║   ██║    ███████╗████╗        {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}              ╚██╗ ██╔╝██║   ██║██║   ██║    ╚════██║██╔╝        {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}               ╚████╔╝ ╚██████╔╝╚██████╔╝    ███████║███████╗       {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.GOLD}                ╚══╝   ╚═════╝  ╚═════╝     ╚══════╝╚══════╝       {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.RESET}                                                          {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.SHADOW}                     ~ Dark Fantasy Edition ~                       {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.SHADOW}{spad}{line}{rpad}{C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}║{C.RESET}                                                          {C.GOLD}║{C.RESET}\n"
            f"{C.GOLD}╚══════════════════════════════════════════════════════════╝{C.RESET}\n"
        )
        print(banner)

    def print_help(self):
        self.div()
        self.p(" GRIMORIO DE COMANDOS ", S.TITLE)
        self.div()
        for cmd, desc in self.COMMANDS.items():
            self.p(f"  {cmd:12} ◆ {desc}", S.DIM)
        self.div()
        self.p("  [mensaje]  ◆ Invocar a Lilith")
        self.p("")

    def print_tools(self):
        tools = Lilith_tools.ALL_TOOLS
        self.div()
        self.p(f" ARSENAL DE HERRAMIENTAS ({len(tools)}) ", S.TITLE)
        self.div()

        categories = {}
        for t in tools:
            name = t["function"]["name"]
            if name in ["screenshot", "get_cursor_position", "list_windows"]:
                cat = "DOMINIO"
            elif name in ["read_file", "write_file", "list_directory", "file_exists"]:
                cat = "ARCHIVOS"
            elif name in ["run_terminal", "open_vscode", "open_application"]:
                cat = "SISTEMA"
            elif name in [
                "ping",
                "check_port",
                "get_network_info",
                "download_file",
                "check_internet",
            ]:
                cat = "RED"
            elif name in [
                "run_git",
                "run_npm",
                "run_python_script",
                "search_in_files",
                "get_git_status",
                "list_git_branches",
            ]:
                cat = "CODING"
            elif name in [
                "list_processes",
                "kill_process",
                "get_system_info",
                "get_disk_space",
                "list_services",
                "start_service",
                "stop_service",
            ]:
                cat = "WINDOWS"
            elif name in [
                "open_url",
                "search_google",
                "clipboard_read",
                "clipboard_write",
                "type_text",
                "press_key",
                "copy_to_clipboard",
            ]:
                cat = "BROWSER"
            else:
                cat = "OTRO"
            categories.setdefault(cat, []).append(name)

        for cat, names in categories.items():
            self.p(f" [{cat}]", S.PROMPT)
            for n in names:
                self.p(f"   {n}", S.DIM)
        self.div()
        self.p("")

    def print_history(self):
        msgs = self.orch.get_history()
        self.div()
        self.p(f" PERGAMINOS ({len(msgs)} entradas) ", S.TITLE)
        self.div()
        for msg in msgs[-15:]:
            role = msg.get("role", "?")
            content = msg.get("content", "")[:70]
            style = S.USER if role == "user" else S.ASSISTANT
            self.p(f"  [{role:8}] {content}...", style)
        self.div()
        self.p("")

    def run(self):
        clear()

        self.p(" Conectando con el Ether...", S.DIM)
        if not llm.test_connection():
            self.print_banner("Sin conexion")
            self.p("", "")
            self.p(" ╔════════ ERROR ARCANO ════════╗", S.ERROR)
            self.p(" ║                                ║", S.ERROR)
            self.p(" ║  No puedo conectar con LM    ║", S.ERROR)
            self.p(" ║  Studio. Asegurate de:        ║", S.ERROR)
            self.p(" ║  1. Abrir LM Studio           ║", S.ERROR)
            self.p(" ║  2. Cargar un modelo          ║", S.ERROR)
            self.p(" ║  3. Activar Local Server     ║", S.ERROR)
            self.p(" ║                                ║", S.ERROR)
            self.p(" ╚═══════════════════════════════════╝", S.ERROR)
            self.p("")
            return

        client = llm.LMStudioClient()
        model_name = client.model
        client.close()
        self.print_banner(model_name)

        status_stream = "ON" if self.streaming_mode else "OFF"
        self.p(
            f" [OK] Conexion eterea establecida | Stream: {status_stream}", S.SUCCESS
        )
        self.p("")

        while True:
            try:
                ts = datetime.now().strftime("%H:%M")
                stream_indicator = "~" if self.streaming_mode else ">"
                user_input = input(
                    f"{C.VOID}{ts}{C.RESET} {S.PROMPT}LILITH{stream_indicator}{C.RESET} "
                ).strip()

                if not user_input:
                    continue

                cmd = user_input.lower()

                if cmd in ["exit", "quit", "q"]:
                    print()
                    self.p(" ╔══════════════════════════════╗", S.TITLE)
                    self.p(" ║                              ║", S.TITLE)
                    self.p(" ║   Viaje seguro, viajero.      ║", S.TITLE)
                    self.p(" ║   Hasta el proximo arcane.   ║", S.TITLE)
                    self.p(" ║                              ║", S.TITLE)
                    self.p(" ╚══════════════════════════════╝", S.TITLE)
                    print()
                    break

                elif cmd in ["clear", "cls"]:
                    clear()
                    self.print_banner(model_name)
                    continue

                elif cmd == "reset":
                    self.orch.reset()
                    self.msg_count = 0
                    self.p(" [OK] Conversacion reiniciada", S.SUCCESS)
                    continue

                elif cmd in ["help", "h"]:
                    self.print_help()
                    continue

                elif cmd == "history":
                    self.print_history()
                    continue

                elif cmd == "tools":
                    self.print_tools()
                    continue

                elif cmd == "sessions":
                    self.div()
                    self.p(" SESIONES EN MEMORIA ", S.TITLE)
                    self.div()
                    episodes = self.memory.get_recent_episodes(count=200)
                    sessions = {}
                    for ep in episodes:
                        sid = ep.get("session_id", "default")
                        sessions[sid] = sessions.get(sid, 0) + 1
                    for sid, count in sorted(
                        sessions.items(), key=lambda x: x[1], reverse=True
                    ):
                        self.p(f"  {sid}: {count} episodios")
                    self.div()
                    print()
                    continue

                elif cmd == "status":
                    self.div()
                    self.p(" ESTADO DEL REALM ", S.TITLE)
                    self.div()
                    self.p(f"  Mensajes: {self.msg_count}", S.INFO)
                    self.p(f"  Tools: {len(Lilith_tools.ALL_TOOLS)}", S.INFO)
                    stats = self.memory.get_stats()
                    self.p(f"  Episodios: {stats['episodes']}", S.INFO)
                    self.p(f"  Comprimidos: {stats['compressed_episodes']}", S.INFO)
                    self.p(f"  Resumenes: {stats['summaries']}", S.INFO)
                    self.p(f"  Entidades: {stats['entities']}", S.INFO)
                    self.p(f"  Hechos: {stats['facts']}", S.INFO)
                    self.p(f"  Errores: {stats['errors']}", S.INFO)
                    agent_mgr = get_agent_manager()
                    agents = agent_mgr.list_agents()
                    self.p(f"  Agentes: {len(agents)}", S.INFO)
                    scheduler = get_scheduler()
                    status = scheduler.get_status()
                    self.p(
                        f"  Tareas: {status['enabled_tasks']}/{status['total_tasks']}",
                        S.INFO,
                    )
                    self.div()
                    print()
                    continue

                elif cmd == "memory":
                    self.div()
                    self.p(" MEMORIAS DE LILITH ", S.TITLE)
                    self.div()
                    recent = self.memory.get_recent_episodes(count=5)
                    self.p(" [Episodios Recientes]", S.PROMPT)
                    for r in recent:
                        ts = r.get("timestamp", "??")[:19]
                        preview = r.get("user_input", "")[:50]
                        self.p(f"   {ts}: {preview}...", S.DIM)
                    entities = self.memory.get_entities(limit=10)
                    if entities:
                        self.p("\n [Entidades Conocidas]", S.PROMPT)
                        for e in entities:
                            self.p(
                                f"   - {e['name']} ({e['type']}): menciones={e['mentions']}",
                                S.DIM,
                            )
                    errors = self.memory.search_errors(query="error")[:3]
                    if errors:
                        self.p("\n [Errores Conocidos]", S.PROMPT)
                        for e in errors:
                            self.p(
                                f"   - {e.get('error_type', 'Unknown')}: {e.get('message', '')[:40]}...",
                                S.DIM,
                            )
                    self.div()
                    print()
                    continue

                elif cmd == "recall":
                    query = user_input[7:].strip()
                    if not query:
                        self.p(" Uso: recall <termino a buscar>", S.WARNING)
                        continue
                    self.div()
                    self.p(f" BUSCANDO: {query} ", S.TITLE)
                    self.div()
                    results = self.memory.search_episodes(query=query, limit=10)
                    for r in results:
                        item_type = "episode"
                        content = r.get("user_input", "")
                        score = 1.0
                        self.p(
                            f"   [{item_type}] score={score:.3f} {content[:60]}...",
                            S.DIM,
                        )
                    self.div()
                    print()
                    continue

                elif cmd == "agents":
                    self.div()
                    self.p(" SUB-AGENTES DE LILITH ", S.TITLE)
                    self.div()
                    agent_mgr = get_agent_manager()
                    agents_list = agent_mgr.list_agents()
                    for agent in agents_list:
                        status = (
                            f"[{C.HEAL}ON{C.RESET}]"
                            if agent.enabled
                            else f"[{C.CORRUPT}OFF{C.RESET}]"
                        )
                        self.p(f" {status} {agent.name}: {agent.description}", S.INFO)
                        caps = ", ".join([c.value for c in agent.capabilities])
                        self.p(f"     Capabilities: {caps}", S.DIM)
                        self.p(
                            f"     Tasks: {agent.stats['total_tasks']} | Success: {agent.success_rate:.1f}%",
                            S.DIM,
                        )
                    self.div()
                    print()
                    continue

                elif cmd == "tasks":
                    self.div()
                    self.p(" TAREAS PROGRAMADAS ", S.TITLE)
                    self.div()
                    scheduler = get_scheduler()
                    tasks = scheduler.list_tasks()
                    if not tasks:
                        self.p(" No hay tareas programadas.", S.DIM)
                    else:
                        for task in tasks[:10]:
                            status = (
                                f"[{C.HEAL}ON{C.RESET}]"
                                if task.enabled
                                else f"[{C.CORRUPT}OFF{C.RESET}]"
                            )
                            next_run = task.next_run[:19] if task.next_run else "N/A"
                            self.p(
                                f" {status} [{task.name}] - Next: {next_run}", S.INFO
                            )
                            self.p(f"     Schedule: {task.schedule}", S.DIM)
                    self.div()
                    self.p(" [Historial Reciente]", S.PROMPT)
                    history = scheduler.history.get_recent(5)
                    for h in history:
                        status_icon = (
                            f"{C.HEAL}OK"
                            if h["status"] == "completed"
                            else f"{C.CORRUPT}FAIL"
                        )
                        self.p(
                            f"   [{status_icon}{C.RESET}] {h['task_name']} - {h['started_at'][:19]}",
                            S.DIM,
                        )
                    self.div()
                    print()
                    continue

                elif cmd == "index":
                    path = user_input[6:].strip()
                    if not path:
                        self.p(" Uso: index <ruta archivo o carpeta>", S.WARNING)
                        self.p(" Ejemplo: index D:\\Proyectos\\Midgard", S.DIM)
                        continue
                    self.div()
                    self.p(f" INDEXANDO: {path} ", S.TITLE)
                    self.div()
                    rag = get_rag_engine()
                    rag_path = Path(path)
                    if rag_path.is_dir():
                        stats = rag.index_directory(path, recursive=True)
                        self.p(f" Documentos indexados: {stats['indexed']}", S.SUCCESS)
                        self.p(f" Omitidos: {stats['skipped']}", S.INFO)
                    else:
                        if rag.index_file(path):
                            self.p(" Archivo indexado exitosamente", S.SUCCESS)
                        else:
                            self.p(" Error al indexar o tipo no soportado", S.ERROR)
                    self.div()
                    print()
                    continue

                elif cmd == "search":
                    query = user_input[7:].strip()
                    if not query:
                        self.p(" Uso: search <consulta>", S.WARNING)
                        continue
                    self.div()
                    self.p(f" BUSQUEDA RAG: {query} ", S.TITLE)
                    self.div()
                    rag = get_rag_engine()
                    results = rag.search(query, limit=5)
                    if not results:
                        self.p(" No se encontraron resultados", S.DIM)
                    else:
                        for r in results:
                            self.p(
                                f"\n [{r['relevance'].upper()}] {r['title']}", S.PROMPT
                            )
                            self.p(f" {r['source']}", S.DIM)
                            self.p(f" {r['content'][:150]}...", S.INFO)
                    self.div()
                    print()
                    continue

                elif cmd == "plugins":
                    self.div()
                    self.p(" PLUGINS DE LILITH ", S.TITLE)
                    self.div()
                    registry = get_plugin_registry()
                    plugins = registry.list_plugins()
                    if not plugins:
                        self.p(" No hay plugins instalados", S.DIM)
                    else:
                        for plugin in plugins:
                            state_icon = (
                                f"{C.HEAL}ENABLED"
                                if plugin.state.value == "enabled"
                                else f"{C.SHADOW}{plugin.state.value.upper()}"
                            )
                            self.p(
                                f" [{state_icon}{C.RESET}] {plugin.name} v{plugin.version}",
                                S.INFO,
                            )
                            self.p(f"   {plugin.description}", S.DIM)
                            caps = ", ".join([c.value for c in plugin.capabilities])
                            self.p(f"   Capabilities: {caps}", S.DIM)
                    self.div()
                    print()
                    continue

                elif cmd == "autostart":
                    self.div()
                    self.p(" AUTO-ARRANQUE ", S.TITLE)
                    self.div()
                    auto_start = get_auto_start()
                    status = auto_start.get_status()
                    if status["platform"] != "win32":
                        self.p(" Auto-arranque solo disponible en Windows", S.WARNING)
                    else:
                        if status["enabled"]:
                            self.p(
                                f" [{C.HEAL}ON{C.RESET}] Auto-arranque habilitado",
                                S.SUCCESS,
                            )
                        else:
                            self.p(
                                f" [{C.SHADOW}OFF{C.RESET}] Auto-arranque deshabilitado",
                                S.DIM,
                            )
                        self.p(f" Script: {status['script_path']}", S.DIM)
                    self.div()
                    self.p(" Comandos: autostart enable | disable | status", S.INFO)
                    self.div()
                    print()
                    continue

                elif cmd == "notify":
                    self.div()
                    self.p(" NOTIFICACIONES DE PRUEBA ", S.TITLE)
                    self.div()
                    notify = get_notifications()
                    notify.info("Lilith", "Notificacion de prueba - Info")
                    notify.success("Lilith", "Notificacion de prueba - Exito")
                    notify.warning("Lilith", "Notificacion de prueba - Advertencia")
                    notify.error("Lilith", "Notificacion de prueba - Error")
                    self.p(" Notificaciones enviadas!", S.SUCCESS)
                    self.div()
                    print()
                    continue

                elif cmd == "stream":
                    self.streaming_mode = not self.streaming_mode
                    status = "ACTIVADO" if self.streaming_mode else "DESACTIVADO"
                    self.p(
                        f" Modo streaming {status}",
                        S.SUCCESS if self.streaming_mode else S.WARNING,
                    )
                    continue

                elif cmd == "compact":
                    self.div()
                    self.p(" COMPRIMIENDO MEMORIAS ", S.TITLE)
                    self.div()
                    try:
                        self.memory.compress_old_episodes(keep_recent=50)
                        stats = self.memory.get_stats()
                        self.p(
                            f" Completado. Episodios activos: {stats['episodes']}",
                            S.SUCCESS,
                        )
                        self.p(
                            f" Episodios comprimidos: {stats['compressed_episodes']}",
                            S.INFO,
                        )
                        self.p(f" Resumenes: {stats['summaries']}", S.INFO)
                    except Exception as e:
                        self.p(f" Error: {e}", S.ERROR)
                    self.div()
                    print()
                    continue

                # Chat
                self.div("─")
                if self.streaming_mode:
                    self.p(" Lilith canalizando...", S.DIM)
                    print(f"{S.ASSISTANT}", end="", flush=True)
                    full_response = []
                    try:
                        for chunk in self.orch.chat_stream(user_input):
                            print(chunk, end="", flush=True)
                            full_response.append(chunk)
                    except Exception as e:
                        self.p(f"\n[Error en streaming: {e}]", S.ERROR)
                    print(f"{C.RESET}")
                    response = "".join(full_response)
                else:
                    self.p(" Invocando a Lilith...", S.DIM)
                    response = self.orch.chat(user_input)
                    print()
                    self.div("─")
                    print(f"{S.ASSISTANT}{response}{C.RESET}")
                    self.div("─")

                # Guardar episodio en memoria (el orchestrator ya lo hace, pero por si acaso)
                self.msg_count += 1
                print()

            except KeyboardInterrupt:
                print()
                self.p(" Canalizacion interrumpida.", S.WARNING)
                continue
            except EOFError:
                print()
                self.p(" Viaje seguro, viajero.", S.TITLE)
                break
            except Exception as e:
                self.div("─")
                self.p(f" [ERROR] {e}", S.ERROR)
                self.div("─")


def main():
    cli = LilithCLI()
    cli.run()


if __name__ == "__main__":
    main()
