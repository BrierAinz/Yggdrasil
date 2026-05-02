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

import argparse
from typing import Optional

import Lilith.Core.llm_provider as llm_provider
import Lilith.Core.orchestrator as orch
import Lilith.tools as Lilith_tools
from Lilith.Agents.agent_manager import AgentCapability, AgentManager, get_agent_manager
from Lilith.auto_start import get_auto_start
from Lilith.MCP.manager import get_mcp_manager
from Lilith.memory.background_consolidator import BackgroundConsolidator, get_consolidator
from Lilith.memory.enhanced import EnhancedMemory, get_memory
from Lilith.memory.session_store import SessionStore, get_session_store
from Lilith.notifications import get_notifications
from Lilith.Plugins.plugin_manager import get_plugin_registry
from Lilith.RAG.rag_engine import get_rag_engine
from Lilith.Scheduler.task_scheduler import TaskScheduler, TaskStatus, get_scheduler
from Lilith.Swarm.manager import get_swarm_manager
from Lilith.tools.dashboard import handle_dashboard_command
from Lilith.tools.mcp_connect import handle_mcp_command
from Lilith.Core.graceful_shutdown import (
    check_crash_recovery, clear_crash_marker, register_shutdown_hook,
    save_crash_marker, setup_graceful_shutdown,
)
from Lilith.Core.skill_registry import get_skill_registry


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
        "session": "Gestionar sesiones (list, load, search, delete)",
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
        "consolidate": "Ejecutar ciclo de consolidacion",
        "swarm": "Gestionar swarm de agentes",
        "mcp": "Gestionar servidores MCP",
        "dashboard": "Abrir dashboard web",
        "skills": "Gestionar skills arcanos",
    }

    def __init__(self, no_banner=False, streaming_mode=None):
        self.orch = orch.LilithOrchestrator()
        self.memory = get_memory()
        self.session_store: SessionStore = get_session_store()
        self.session_id = "default"
        self.msg_count = 0
        self.streaming_mode = streaming_mode if streaming_mode is not None else False
        self.no_banner = no_banner
        self._copy_builtin_skills()
        self.skill_registry = get_skill_registry()
        # Iniciar BackgroundConsolidator en segundo plano
        self._consolidator: Optional[BackgroundConsolidator] = None

        # ── Graceful Shutdown & Crash Recovery ──
        def _on_shutdown():
            """Salva sesión y detiene consolidador al cerrar."""
            try:
                self.orch.close()
            except Exception:
                pass
            try:
                self.memory.save()
            except Exception:
                pass
            clear_crash_marker()

        register_shutdown_hook(_on_shutdown)
        setup_graceful_shutdown()
        save_crash_marker(self.session_id)

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

    def _handle_swarm_command(self, args: str):
        """Handler para comandos /swarm."""
        parts = args.split()
        subcmd = parts[0] if parts else "status"
        mgr = get_swarm_manager()

        if subcmd == "spawn":
            task = " ".join(parts[1:]) if len(parts) > 1 else "Tarea generica"
            num = 2
            use_llm = False
            # Parsear flags
            for i, p in enumerate(parts):
                if p == "--agents" and i + 1 < len(parts):
                    try:
                        num = int(parts[i + 1])
                    except ValueError:
                        pass
                elif p == "--llm":
                    use_llm = True
            self.div()
            self.p(f" INVOCANDO SWARM ", S.TITLE)
            self.div()
            self.p(f" Tarea: {task}", S.INFO)
            self.p(f" Agentes: {num}", S.INFO)
            self.p(f" LLM: {'ON' if use_llm else 'OFF (simulado)'}", S.INFO)
            try:
                # Si se pide LLM, inicializar executor
                if use_llm and not mgr._executor:
                    from Lilith.Core.llm_provider import get_provider
                    from Lilith.Swarm.executor import SwarmExecutor

                    provider = get_provider()
                    executor = SwarmExecutor(provider)
                    mgr._executor = executor
                    mgr._use_llm = True
                agent_ids = mgr.spawn_swarm(task=task, num_agents=num)
                self.p(f" [OK] Swarm spawnado: {', '.join(agent_ids)}", S.SUCCESS)
                # Activar persistencia
                mgr.enable_persistence()
                sid = mgr.save_session(task=task)
                self.p(f" [OK] Sesion guardada: {sid}", S.SUCCESS)
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        elif subcmd == "status":
            self.div()
            self.p(" ESTADO DEL SWARM ", S.TITLE)
            self.div()
            try:
                report = mgr.get_status_report()
                self.p(
                    f" Agentes: {report['total_agents']} (activos: {report['active']}, completados: {report['complete']})",
                    S.INFO,
                )
                self.p(f" Errores: {report['errors']}", S.INFO)
                self.p(f" Locks: {len(report['file_locks'])}", S.INFO)
                self.p(f" Mensajes pendientes: {report['pending_messages']}", S.INFO)
                if mgr._session_id:
                    self.p(f" Sesion: {mgr._session_id}", S.DIM)
                if report["agents"]:
                    self.p("\n [Agentes]", S.PROMPT)
                    for a in report["agents"]:
                        status_color = (
                            S.HEAL
                            if a["status"] == "complete"
                            else (S.WARNING if a["status"] == "working" else S.DIM)
                        )
                        self.p(
                            f"   {a['id']}: {a['status']} | {a['task'][:40]}...",
                            status_color,
                        )
                if report["conflicts"]:
                    self.p("\n [Conflictos]", S.WARNING)
                    for c in report["conflicts"]:
                        self.p(f"   {c['file']}: {', '.join(c['agents'])}", S.WARNING)
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        elif subcmd == "kill":
            if len(parts) < 2:
                self.p(" Uso: swarm kill <agent_id>", S.WARNING)
                return
            agent_id = parts[1]
            result = mgr.kill_agent(agent_id)
            self.p(
                f" {'[OK] Agente eliminado' if result else '[ERROR] No encontrado'}: {agent_id}",
                S.SUCCESS if result else S.ERROR,
            )

        elif subcmd == "killall":
            mgr.kill_all()
            self.p(" [OK] Todos los agentes eliminados", S.SUCCESS)

        elif subcmd == "result":
            if len(parts) < 2:
                self.p(" Uso: swarm result <agent_id>", S.WARNING)
                return
            agent_id = parts[1]
            result = mgr.get_agent_results(agent_id)
            self.div()
            self.p(f" RESULTADO: {agent_id} ", S.TITLE)
            self.div()
            if result:
                self.p(f" Status: {result['status']}", S.INFO)
                self.p(f" Duracion: {result['duration']:.1f}s", S.INFO)
                if result["result"]:
                    self.p(f" Output: {str(result['result'])[:200]}", S.DIM)
            else:
                self.p(" Agente no encontrado", S.ERROR)
            self.div()
            print()

        elif subcmd == "save":
            self.div()
            self.p(" GUARDANDO SWARM ", S.TITLE)
            self.div()
            try:
                mgr.enable_persistence()
                sid = mgr.save_session()
                self.p(f" [OK] Sesion guardada: {sid}", S.SUCCESS)
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        elif subcmd == "load":
            if len(parts) < 2:
                self.p(" Uso: swarm load <session_id>", S.WARNING)
                return
            sid = parts[1]
            self.div()
            self.p(f" CARGANDO SESION ", S.TITLE)
            self.div()
            try:
                ok = mgr.load_session(sid)
                if ok:
                    history = mgr.get_session_history(sid)
                    self.p(f" [OK] Sesion cargada: {sid}", S.SUCCESS)
                    self.p(f" Agentes: {len(history['agents'])}", S.INFO)
                    self.p(f" Mensajes: {len(history['messages'])}", S.INFO)
                    self.p(f" Conflictos: {len(history['conflicts'])}", S.INFO)
                else:
                    self.p(f" [ERROR] Sesion no encontrada: {sid}", S.ERROR)
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        elif subcmd == "history":
            self.div()
            self.p(" HISTORIAL DE SWARMS ", S.TITLE)
            self.div()
            try:
                mgr.enable_persistence()
                sessions = mgr.list_saved_sessions(limit=20)
                if not sessions:
                    self.p(" No hay sesiones guardadas", S.DIM)
                for s in sessions:
                    status_icon = "✓" if s.get("status") == "complete" else "○"
                    ts = s.get("created_at", 0)
                    ts_str = (
                        datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                        if ts
                        else "?"
                    )
                    self.p(
                        f" {status_icon} [{s['id'][:20]}...] {s.get('task', 'N/A')[:40]} | {ts_str}",
                        S.DIM,
                    )
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        else:
            self.p(" Comandos swarm:", S.INFO)
            self.p("   swarm spawn <tarea> [--agents N] [--llm]  - Crear swarm")
            self.p("   swarm status                               - Ver estado")
            self.p("   swarm kill <id>                            - Matar agente")
            self.p("   swarm killall                              - Matar todos")
            self.p("   swarm result <id>                          - Ver resultado")
            self.p("   swarm save                                 - Guardar sesion")
            self.p("   swarm load <session_id>                    - Cargar sesion")
            self.p("   swarm history                              - Ver historial")

    def _copy_builtin_skills(self):
        """Copia skills built-in desde Lilith/skills/ a ~/.lilith/skills/ si no existen."""
        import shutil
        builtin_dir = Path(__file__).parent / "skills"
        target_dir = Path.home() / ".lilith" / "skills"

        if not builtin_dir.exists():
            return

        target_dir.mkdir(parents=True, exist_ok=True)

        for skill_file in builtin_dir.glob("*.md"):
            target_file = target_dir / skill_file.name
            if not target_file.exists():
                shutil.copy2(skill_file, target_file)

    def _handle_skills_command(self, args: str):
        """Handler para comandos /skills."""
        parts = args.split()
        subcmd = parts[0] if parts else "list"
        subcmd_lower = subcmd.lower()

        if subcmd_lower in ("list", ""):
            self.div()
            self.p(" SKILLS ARCANOS ", S.TITLE)
            self.div()
            skills = self.skill_registry.list_skills()
            if not skills:
                self.p(" No hay skills cargados", S.DIM)
            else:
                for skill in skills:
                    status = f"{C.HEAL}ON{C.RESET}" if skill.enabled else f"{C.CORRUPT}OFF{C.RESET}"
                    triggers = len(skill.trigger)
                    self.p(
                        f" [{status}] {skill.name} (priority={skill.priority}, triggers={triggers})",
                        S.INFO,
                    )
                    self.p(f"     {skill.description}", S.DIM)
            stats = self.skill_registry.get_stats()
            self.p(f"\n Total: {stats['total_skills']} | Enabled: {stats['enabled_skills']} | Disabled: {stats['disabled_skills']}", S.DIM)
            self.div()
            print()

        elif subcmd_lower == "reload":
            self.div()
            self.p(" RECARGANDO SKILLS ", S.TITLE)
            self.div()
            loaded = self.skill_registry.reload()
            self.p(f" [OK] {len(loaded)} skills recargados: {', '.join(loaded) if loaded else 'ninguno'}", S.SUCCESS)
            self.div()
            print()

        elif subcmd_lower == "enable":
            if len(parts) < 2:
                self.p(" Uso: skills enable <nombre>", S.WARNING)
                return
            name = parts[1]
            if self.skill_registry.enable_skill(name):
                self.p(f" [OK] Skill '{name}' habilitado", S.SUCCESS)
            else:
                self.p(f" [ERROR] Skill '{name}' no encontrado", S.ERROR)

        elif subcmd_lower == "disable":
            if len(parts) < 2:
                self.p(" Uso: skills disable <nombre>", S.WARNING)
                return
            name = parts[1]
            if self.skill_registry.disable_skill(name):
                self.p(f" [OK] Skill '{name}' deshabilitado", S.WARNING)
            else:
                self.p(f" [ERROR] Skill '{name}' no encontrado", S.ERROR)

        elif subcmd_lower == "stats":
            self.div()
            self.p(" ESTADISTICAS DE SKILLS ", S.TITLE)
            self.div()
            usage = self.skill_registry.get_usage_stats()
            if not usage:
                self.p(" No hay estadisticas de uso", S.DIM)
            else:
                for name, stat in usage.items():
                    times = stat["times_triggered"]
                    last = stat["last_triggered"]
                    last_str = ""
                    if last:
                        from datetime import datetime as _dt
                        last_str = _dt.fromtimestamp(last).strftime("%Y-%m-%d %H:%M")
                    self.p(
                        f"  {name}: triggered {times}x | last: {last_str or 'never'}",
                        S.INFO,
                    )
            self.div()
            print()

        elif subcmd_lower == "info":
            if len(parts) < 2:
                self.p(" Uso: skills info <nombre>", S.WARNING)
                return
            name = " ".join(parts[1:])
            skill = self.skill_registry.get(name)
            if not skill:
                self.p(f" [ERROR] Skill '{name}' no encontrado", S.ERROR)
                return
            self.div()
            self.p(f" SKILL: {skill.name} ", S.TITLE)
            self.div()
            self.p(f"  Descripcion: {skill.description}", S.INFO)
            self.p(f"  Prioridad: {skill.priority}", S.INFO)
            self.p(f"  Habilitado: {'Si' if skill.enabled else 'No'}", S.INFO)
            self.p(f"  Version: {skill.version}", S.INFO)
            if skill.trigger:
                self.p(f"  Triggers (keywords): {', '.join(skill.trigger)}", S.PROMPT)
            if skill.trigger_regex:
                self.p(f"  Triggers (regex): {', '.join(skill.trigger_regex)}", S.PROMPT)
            if skill.trigger_intent:
                self.p(f"  Triggers (intent): {', '.join(skill.trigger_intent)}", S.PROMPT)
            if skill.tools_required:
                self.p(f"  Tools requeridos: {', '.join(skill.tools_required)}", S.PROMPT)
            usage = self.skill_registry.get_usage_stats().get(name, {})
            times = usage.get("times_triggered", 0)
            last = usage.get("last_triggered")
            last_str = ""
            if last:
                from datetime import datetime as _dt
                last_str = _dt.fromtimestamp(last).strftime("%Y-%m-%d %H:%M")
            self.p(f"  Veces activado: {times}", S.DIM)
            self.p(f"  Ultima activacion: {last_str or 'nunca'}", S.DIM)
            if skill.source_file:
                self.p(f"  Archivo: {skill.source_file}", S.DIM)
            self.div()
            print()

        else:
            self.p(" Comandos skills:", S.INFO)
            self.p("   skills list           - Listar skills", S.DIM)
            self.p("   skills reload         - Recargar skills", S.DIM)
            self.p("   skills enable <name>  - Habilitar skill", S.DIM)
            self.p("   skills disable <name> - Deshabilitar skill", S.DIM)
            self.p("   skills stats          - Estadisticas de uso", S.DIM)
            self.p("   skills info <name>    - Info detallada", S.DIM)

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

    def _handle_session_command(self, args: str):
        """Handler para comandos /session y /sessions."""
        parts = args.split()
        subcmd = parts[0] if parts else "list"
        subcmd_lower = subcmd.lower()

        if subcmd_lower in ("list", ""):
            self.div()
            self.p(" ARCHIVO DE SESIONES ", S.TITLE)
            self.div()
            sessions = self.session_store.list_sessions(limit=20)
            if not sessions:
                self.p(" No hay sesiones guardadas en el archivo", S.DIM)
            else:
                for s in sessions:
                    active_marker = ""
                    if s["id"] == self.orch.session_id:
                        active_marker = f" {C.HEAL}(actual){C.RESET}"
                    ts = s.get("last_active", "")[:16]
                    ep_count = s.get("episode_count", 0)
                    summary = s.get("summary", "(sin resumen)")[:60]
                    self.p(
                        f"  {C.VOID}{s['id']}{C.RESET}{active_marker}",
                        S.INFO,
                    )
                    self.p(f"    Ultima actividad: {ts} | Episodios: {ep_count}", S.DIM)
                    self.p(f"    {summary}", S.DIM)
            self.div()
            print()

        elif subcmd_lower == "search":
            query = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not query:
                self.p(" Uso: session search <consulta>", S.WARNING)
                return
            self.div()
            self.p(f" BUSQUEDA DE SESIONES: {query} ", S.TITLE)
            self.div()
            results = self.session_store.search_sessions(query, limit=5)
            if not results:
                self.p(" No se encontraron sesiones relevantes", S.DIM)
            else:
                for s in results:
                    score = s.get("search_score", 0)
                    ts = s.get("last_active", "")[:16]
                    summary = s.get("summary", "(sin resumen)")[:60]
                    self.p(
                        f"  {s['id']} (score={score:.3f})",
                        S.INFO,
                    )
                    self.p(f"    {ts} | {summary}", S.DIM)
            self.div()
            print()

        elif subcmd_lower == "load":
            if len(parts) < 2:
                self.p(" Uso: session load <session_id>", S.WARNING)
                return
            sid = parts[1]
            session_data = self.session_store.load_session(sid)
            if not session_data:
                self.p(f" [ERROR] Sesion no encontrada: {sid}", S.ERROR)
                return
            self.div()
            self.p(f" CARGANDO SESION: {sid} ", S.TITLE)
            self.div()
            ts = session_data.get("last_active", "")[:16]
            ep_count = session_data.get("episode_count", 0)
            summary = session_data.get("summary", "(sin resumen)")
            self.p(f"  Ultima actividad: {ts}", S.INFO)
            self.p(f"  Episodios: {ep_count}", S.INFO)
            self.p(f"  Resumen: {summary}", S.DIM)
            # Cargar episodios de la sesión en memoria
            episodes = self.memory.get_recent_episodes(count=50, session_id=sid)
            if episodes:
                self.p(f"\n  Restaurando {len(episodes)} episodios...", S.INFO)
                # Reiniciar conversación con contexto de la sesión cargada
                self.orch.reset()
                self.orch.session_id = sid
                for ep in reversed(episodes):
                    if ep.get("user_input"):
                        self.orch.messages.append({"role": "user", "content": ep["user_input"]})
                    if ep.get("response"):
                        self.orch.messages.append({"role": "assistant", "content": ep["response"]})
                self.p(f" [OK] Sesion {sid} restaurada con {len(episodes)} episodios", S.SUCCESS)
            else:
                self.p(" No se encontraron episodios para esta sesion", S.WARNING)
            self.div()
            print()

        elif subcmd_lower == "delete":
            if len(parts) < 2:
                self.p(" Uso: session delete <session_id>", S.WARNING)
                return
            sid = parts[1]
            if sid == self.orch.session_id:
                self.p(" No puedes eliminar la sesion activa", S.ERROR)
                return
            self.session_store.delete_session(sid)
            self.p(f" [OK] Sesion {sid} eliminada del archivo", S.SUCCESS)

        elif subcmd_lower == "save":
            self.div()
            self.p(" GUARDANDO SESION ACTUAL ", S.TITLE)
            self.div()
            try:
                self.orch._save_current_session()
                self.p(f" [OK] Sesion {self.orch.session_id} guardada", S.SUCCESS)
            except Exception as e:
                self.p(f" [ERROR] {e}", S.ERROR)
            self.div()
            print()

        else:
            self.p(" Comandos session:", S.INFO)
            self.p("   session list            - Listar sesiones", S.DIM)
            self.p("   session search <query>  - Buscar sesiones", S.DIM)
            self.p("   session load <id>       - Cargar sesion", S.DIM)
            self.p("   session delete <id>     - Eliminar sesion", S.DIM)
            self.p("   session save            - Guardar sesion actual", S.DIM)

    def _handle_consolidate_command(self):
        """Handler para el comando /consolidate."""
        self.div()
        self.p(" CONSOLIDACION DE MEMORIA ", S.TITLE)
        self.div()

        # Ejecutar un ciclo manual de consolidación
        try:
            consolidator = get_consolidator()
            self.p(" Ejecutando ciclo de consolidacion...", S.INFO)
            result = consolidator.run_cycle()

            self.p(f" Episodios fusionados: {result.get('merged', 0)}", S.INFO)
            self.p(f" Hechos promovidos: {result.get('facts_promoted', 0)}", S.INFO)
            self.p(f" Relaciones decaidas: {result.get('relations_decayed', 0)}", S.INFO)

            stats = self.orch.get_consolidator_stats()
            self.p(f"\n Estadisticas acumuladas:", S.PROMPT)
            self.p(f"  Ciclos: {stats.get('cycles_run', 0)}", S.DIM)
            self.p(f"  Total fusionados: {stats.get('episodes_merged', 0)}", S.DIM)
            self.p(f"  Total hechos promovidos: {stats.get('facts_promoted', 0)}", S.DIM)
            if stats.get('last_run'):
                self.p(f"  Ultimo ciclo: {stats['last_run'][:19]}", S.DIM)

            running = "ACTIVO" if stats.get('running') else "DETENIDO"
            self.p(f"  Consolidador: {running}", S.INFO)
        except Exception as e:
            self.p(f" [ERROR] {e}", S.ERROR)

        self.div()
        self.p(" Comandos: consolidate (manual) | El consolidador se puede iniciar con: orchestrator.start_consolidator()", S.DIM)
        print()

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

        # ── Crash Recovery ──────────────────────────────────────────
        # Si Lilith cerró inesperadamente, ofrecemos restaurar la sesión
        recovered = check_crash_recovery()
        if recovered:
            self.p(f" ⚠ Sesion previa detectada ({recovered})", S.WARNING)
            self.p(" Usar /session load <id> para restaurar", S.DIM)
        # ─────────────────────────────────────────────────────────────

        self.p(" Conectando con el Ether...", S.DIM)
        try:
            provider = llm_provider.get_provider()
        except ConnectionError as e:
            if not self.no_banner:
                self.print_banner("Sin conexion")
            else:
                self.p(" [ERROR] No hay conexion con ningun provider LLM.", S.ERROR)
            self.p("", "")
            self.p(" ╔════════ ERROR ARCANO ════════╗", S.ERROR)
            self.p(" ║                                ║", S.ERROR)
            self.p(" ║  No puedo conectar con ningun  ║", S.ERROR)
            self.p(" ║  provider LLM. Asegurate de:   ║", S.ERROR)
            self.p(" ║  1. Abrir LM Studio           ║", S.ERROR)
            self.p(" ║     o configurar API remota   ║", S.ERROR)
            self.p(" ║  2. Cargar un modelo          ║", S.ERROR)
            self.p(" ║  3. Activar Local Server     ║", S.ERROR)
            self.p(" ║                                ║", S.ERROR)
            self.p(f" ║  Detalle: {str(e)[:30]:<28} ║", S.ERROR)
            self.p(" ╚═══════════════════════════════════╝", S.ERROR)
            self.p("")
            return

        model_name = f"{provider.name}/{provider.model}"
        if not self.no_banner:
            self.print_banner(model_name)
        else:
            self.p(
                f" Lilith v3.0 | {model_name} | {len(Lilith_tools.ALL_TOOLS)} tools",
                S.TITLE,
            )
            self.div()

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
                    # Guardar sesión antes de salir
                    try:
                        self.orch._save_current_session()
                    except Exception:
                        pass
                    # Detener consolidador si está activo
                    try:
                        self.orch.stop_consolidator()
                    except Exception:
                        pass
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
                    if not self.no_banner:
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
                    self._handle_session_command("list")
                    continue

                elif cmd.startswith("session"):
                    self._handle_session_command(user_input[8:].strip())
                    continue

                elif cmd == "status":
                    self.div()
                    self.p(" ESTADO DEL REALM ", S.TITLE)
                    self.div()
                    self.p(f"  Mensajes: {self.msg_count}", S.INFO)
                    self.p(f"  Tools: {len(Lilith_tools.ALL_TOOLS)}", S.INFO)
                    # Mostrar info del provider LLM activo
                    try:
                        prov_info = self.orch.get_provider_info()
                        self.p(
                            f"  LLM: {prov_info['name']}/{prov_info['model']} ({prov_info['type']})",
                            S.INFO,
                        )
                    except Exception:
                        self.p("  LLM: (sin info)", S.WARNING)
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
                    self.p(" MEMORIAS DE LILITH v3.0 ", S.TITLE)
                    self.div()

                    # Stats generales
                    stats = self.memory.get_stats()
                    self.p(
                        f" [Estadisticas] Episodios: {stats.get('episodes',0)} | Entidades: {stats.get('entities',0)} | Facts: {stats.get('facts',0)} | Errores: {stats.get('errors',0)}",
                        S.PROMPT,
                    )

                    # Grafo
                    graph_stats = self.memory.graph.get_graph_stats()
                    if graph_stats.get("relations", 0) > 0:
                        self.p(
                            f" [Grafo] Relaciones: {graph_stats['relations']} | Entidades conectadas: {graph_stats['connected_entities']} | Fuerza promedio: {graph_stats['avg_strength']}",
                            S.PROMPT,
                        )

                    # Consolidacion
                    cons_stats = self.memory.consolidation.get_stats()
                    if cons_stats.get("consolidated_episodes", 0) > 0:
                        self.p(
                            f" [Consolidacion] Cola: {cons_stats['queue_size']} | Consolidados: {cons_stats['consolidated_episodes']}",
                            S.PROMPT,
                        )

                    recent = self.memory.get_recent_episodes(count=5)
                    self.p("\n [Episodios Recientes]", S.PROMPT)
                    for r in recent:
                        ts = r.get("timestamp", "??")[:19]
                        preview = r.get("user_input", "")[:50]
                        self.p(f"   {ts}: {preview}...", S.DIM)

                    entities = self.memory.get_entities(limit=10)
                    if entities:
                        self.p("\n [Entidades Conocidas]", S.PROMPT)
                        for e in entities:
                            # Mostrar vecinos del grafo
                            neighbors = self.memory.graph.get_neighbors(
                                e["name"], min_strength=0.5
                            )
                            neighbor_str = ""
                            if neighbors:
                                n_names = [n[0] for n in neighbors[:2]]
                                neighbor_str = f" -> {', '.join(n_names)}"
                            self.p(
                                f"   - {e['name']} ({e['type']}): {e['mentions']}x{neighbor_str}",
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
                    self.p(f" BUSQUEDA HIBRIDA: {query} ", S.TITLE)
                    self.div()

                    # Usar retrieval hibrido
                    results = self.memory.retriever.retrieve(
                        query=query, limit=10, include_sources=True
                    )
                    for r in results:
                        sources = r.get("retrieval_sources", {})
                        source_str = ",".join(
                            [f"{k}={v:.2f}" for k, v in sources.items()]
                        )
                        ts = r.get("timestamp", "??")[:10]
                        content = r.get("user_input", "")
                        score = r.get("retrieval_score", 0)
                        self.p(
                            f"   [{ts}] score={score:.3f} [{source_str}] {content[:60]}...",
                            S.DIM,
                        )
                        if r.get("response"):
                            self.p(f"      -> {r['response'][:60]}...", S.DIM)

                    # Mostrar entidades relacionadas del grafo
                    related = set()
                    for word in query.lower().split():
                        if len(word) > 3:
                            neighbors = self.memory.graph.get_neighbors(
                                word, min_strength=0.3
                            )
                            for n, rel_type, strength in neighbors[:3]:
                                related.add((n, rel_type, strength))
                    if related:
                        self.p("\n [Entidades Relacionadas en Grafo]", S.PROMPT)
                        for ent, rel_type, strength in sorted(
                            related, key=lambda x: x[2], reverse=True
                        )[:5]:
                            self.p(
                                f"   - {ent} ({rel_type}, strength={strength:.2f})",
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

                elif cmd == "consolidate":
                    self._handle_consolidate_command()
                    continue

                elif cmd.startswith("swarm"):
                    self._handle_swarm_command(user_input[5:].strip())
                    continue
                elif cmd.startswith("mcp"):
                    result = handle_mcp_command(user_input[3:].strip())
                    self.p(result)
                    continue
                elif cmd.startswith("dashboard"):
                    result = handle_dashboard_command(
                        user_input[10:].strip(), lilith_instance=self
                    )
                    self.p(result)
                    continue
                elif cmd.startswith("skills"):
                    self._handle_skills_command(user_input[6:].strip())
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
    parser = argparse.ArgumentParser(
        prog="lilith",
        description="Lilith - Dark Fantasy CLI Agent for LM Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Commands:
  exit, quit, q     Leave the realm
  clear, cls        Clean the viewport
  help, h           Show grimoire
  history           View past scrolls
  tools             View tool arsenal
  status            Full realm status
  memory            View Lilith's memories
  recall <query>    Search memories
  agents            View sub-agents
  tasks             View scheduled tasks
  swarm <cmd>       Manage agent swarm (spawn, status, kill, save, load, history)
  skills <cmd>     Manage arcane skills (list, enable, disable, reload, stats, info)
  index <path>      Index files/folder
  search <query>    Search indexed documents
  plugins           View installed plugins
  stream            Toggle streaming mode
  compact           Compress old memories

Example:
  lilith                    Start interactive session
  lilith --no-banner        Start without the intro banner
  lilith --streaming        Start with streaming enabled
        """.strip(),
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "--no-banner", action="store_true", help="Skip the intro banner"
    )
    parser.add_argument(
        "--streaming", action="store_true", help="Enable streaming mode"
    )
    parser.add_argument(
        "--no-streaming", action="store_true", help="Disable streaming mode"
    )
    parser.add_argument("--model", help="Override model name")
    parser.add_argument(
        "--cwd", type=Path, help="Change working directory before starting"
    )

    args = parser.parse_args()

    if args.version:
        print("Lilith v3.0.0 - Dark Fantasy Edition")
        sys.exit(0)

    if args.cwd:
        os.chdir(args.cwd)

    streaming = None
    if args.streaming and args.no_streaming:
        parser.error("Cannot use --streaming and --no-streaming together")
    if args.streaming:
        streaming = True
    elif args.no_streaming:
        streaming = False

    cli = LilithCLI(no_banner=args.no_banner, streaming_mode=streaming)
    cli.run()


if __name__ == "__main__":
    main()
