import asyncio
import logging
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Add project root to sys.path to ensure imports work if run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ipc_messages import (
    BaseIPCMessage,
    CommandSendMessage,
    EventChatDelta,
    EventChatFinal,
    EventData,
    EventError,
    EventStatusUpdate,
    IPCMessageType,
    LLMProvider,
    QueryGetStatus,
)
from src.ipc_server import IPCServer
from src.utils.logger import get_logger, setup_logging

# Configurar logging global al cargar el módulo
setup_logging()
logger = get_logger("SebasCore")


# Alias para eventos genéricos — usa EventData que sí tiene action="data" y payload
def Event(payload=None):
    return EventData(payload=payload or {})


def _ping_pantheon_availability():
    """Ping each agent's API to determine real availability. Returns dict agent_key -> bool."""
    import requests

    result = {}
    # Eva: Grok API (xAI)
    try:
        r = requests.get("https://api.x.ai/v1/models", timeout=3)
        # Consideramos Eva "online" mientras la API responda (cualquier código < 500).
        # 4xx típicos (401/403) suelen indicar problema de key/permiso, pero la API está viva
        # y /eva puede seguir funcionando si la key de GROK_API_KEY es válida.
        result["eva"] = r.status_code < 500
    except Exception:
        result["eva"] = False
    # Adán: Ollama local
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        result["adan"] = r.status_code < 500
    except Exception:
        result["adan"] = False
    # Lucifer: Venice API (suele fallar si no hay key o red bloquea)
    try:
        r = requests.get("https://api.venice.ai/api/v1/models", timeout=3)
        result["lucifer"] = r.status_code < 500
    except Exception:
        result["lucifer"] = False
    # Lilith/Kimi: always online when Core is running
    result["kimi"] = True
    return result


from src.core.agent_router import AgentRouter
from src.core.config_manager import ConfigManager
from src.core.memory.manager import MemoryManager
from src.core.memory.memory_extractor import MemoryExtractor
from src.core.memory.procedural_memory import ProceduralMemory
from src.core.memory.semantic_memory import SemanticMemory
from src.core.memory.session_summarizer import SessionSummarizer
from src.core.pending_approvals import PendingApprovalsRegistry
from src.core.planning import PlanningEngine, PlanStepStatus, ThoughtStreamer
from src.core.stats_tracker import StatsTracker
from src.core.system_policy import SystemPolicy
from src.core.tool_registry import get_tool_registry
from src.ipc_messages import (
    CommandDecisionResult,
    CommandUpdateConfig,
    EventConfigData,
    EventDecisionRequest,
    EventStatsData,
    QueryGetConfig,
    QueryGetStats,
)
from src.llm.grok_client import GrokClient
from src.llm.kimi_client import KimiClient
from src.llm.ollama_client import OllamaClient
from src.llm.venice_client import VeniceClient

# === PANTEÓN: Comandos de fuerza de agente ===
# Después del cambio de roles: Lilith usa Kimi, Eva usa Grok
AGENT_COMMANDS = {
    "/eva": "eva",
    "/adán": "adan",
    "/adan": "adan",
    "/lucifer": "lucifer",
    "/lilith": "kimi",
    "/kimi": "kimi",
    "/grok": "grok",  # Comando legacy - redirige a Eva
}


def parse_agent_command(message: str) -> tuple:
    """
    Detecta si el mensaje empieza con un comando de agente.
    Retorna (agent_name, cleaned_message) o (None, message original)
    """
    message_lower = message.lower().strip()
    for cmd, agent in AGENT_COMMANDS.items():
        if message_lower.startswith(cmd + " "):
            cleaned = message[len(cmd) :].strip()
            return agent, cleaned
        elif message_lower == cmd:
            return agent, ""
    return None, message


from src.core.auto_workflow_generator import AutoWorkflowGenerator
from src.core.memory.session_manager import SessionManager

# Phase 4: Observability & Self-Improvement
from src.observability.session_logger import SessionLogger
from src.observability.telemetry import AgentTelemetry

# Global state
# approval_queues = {} # correlation_id -> queue.Queue # DEPRECATED by registry
_tool_registry = None
_memory_manager = None
_session_logger = None
_telemetry = None
_workflow_generator = None

# Session management globals
_global_session_manager = None
_session_summarizer = None
_procedural_memory = None
_memory_extractor = None
_current_session_id = None
_current_messages = []
_current_session_summary = (
    None  # title/summary for current session (for session_renamed)
)
_system_prompt = None
MAX_CONTEXT_TOKENS = 262_000  # Kimi-for-coding context window


def _generate_session_id():
    """Generate a unique session ID with timestamp."""
    import random

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = random.randint(1000, 9999)
    return f"session_{timestamp}_{random_suffix}"


def estimate_token_usage(messages, system_prompt=None):
    """Estimar uso de tokens (aproximado: 4 chars ≈ 1 token)"""
    total_chars = 0
    if system_prompt:
        total_chars += len(system_prompt)
    for msg in messages:
        total_chars += len(msg.get("content", ""))
    return total_chars // 4


def get_token_stats():
    """Obtener estadísticas de uso de tokens para la sesión actual"""
    global _current_messages, _system_prompt
    max_tokens = MAX_CONTEXT_TOKENS
    usage = estimate_token_usage(_current_messages, _system_prompt)
    percentage = (
        min(100.0, round((usage / max_tokens) * 100, 1)) if max_tokens > 0 else 0.0
    )
    logger.info(
        "[tokens] updated",
        extra={
            "session_id": _current_session_id,
            "agent": "lilith",
            "duration_ms": None,
        },
    )
    return {"used": usage, "max": max_tokens, "percentage": percentage}


def get_global_tool_registry():
    """Get or create global tool registry for this module"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = get_tool_registry()
        if not _tool_registry._initialized:
            _tool_registry.initialize()
    return _tool_registry


def get_global_memory_manager():
    """Get or create global memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(max_memory_messages=1000)
    return _memory_manager


# Planning engine instance
_planning_engine = None


def get_planning_engine(llm_client, system_prompt=None):
    """Singleton para PlanningEngine"""
    global _planning_engine
    if _planning_engine is None:
        _planning_engine = PlanningEngine(llm_client, system_prompt)
    return _planning_engine


def main():
    global _global_memory_manager, _global_session_manager, _current_session_id, _current_messages, _system_prompt, _current_session_summary

    try:
        logger.info("SEBAS Core starting...")

        # Initialize Config
        config_manager = ConfigManager()
        config = config_manager.load()
        logger.info(f"Loaded config. Default provider: {config.llm.provider}")

        # Load System Prompt / Persona
        system_prompt = config.llm.system_prompt
        if not system_prompt:
            # Load from Phase 4 Workspace/Alma structure
            persona_path = os.path.join(project_root, "Workspace", "Alma", "persona.md")
            if os.path.exists(persona_path):
                logger.info(f"Loading persona from {persona_path}")
                try:
                    with open(persona_path, "r", encoding="utf-8") as f:
                        system_prompt = f.read()
                except Exception as e:
                    logger.error(f"Failed to load persona: {e}")
            else:
                logger.warning("No persona.md found and no system_prompt in config.")
        else:
            logger.info("Using system_prompt from config.")

        # v2.2 Fase A: inyectar contexto de memoria semántica (perfil Ainz, proyectos activos)
        try:
            semantic_memory = SemanticMemory(project_root)
            semantic_context = semantic_memory.get_context_for_prompt()
            system_prompt = (
                system_prompt.rstrip()
                + f"\n\n## Contexto sobre Ainz:\n{semantic_context}"
            )
            logger.info("Semantic context injected into system prompt.")
        except Exception as e:
            logger.warning("Semantic memory context not injected: %s", e)

        # Store in global for token calculation
        global _system_prompt
        _system_prompt = system_prompt

        # Load Secrets
        secrets_path = os.path.join(project_root, "Config", "secrets.env")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip()

        # Initialize LLM Clients
        ollama = OllamaClient()
        grok = GrokClient()
        venice = VeniceClient()
        kimi = KimiClient()  # Lilith ahora usa Kimi (contexto 262k)

        # Provider Map
        llm_providers = {
            "ollama": ollama,
            "grok": grok,
            "venice": venice,
            "kimi": kimi,  # Provider principal
        }

        # Initialize Tool Registry (includes GitTools, SystemExecutor, CodeAnalyzer)
        tool_registry = get_global_tool_registry()

        # Get tool instances from registry
        git_tool = tool_registry.get_tool("GitTools")
        sys_executor = tool_registry.get_tool("SystemExecutor")

        if not git_tool or not sys_executor:
            logger.error("Critical tools not available in registry")
            sys.exit(1)

        # Initialize Stats
        stats_tracker = StatsTracker()

        # Phase 4: Initialize Observability
        global _session_logger, _telemetry, _workflow_generator
        _session_logger = SessionLogger()
        _telemetry = AgentTelemetry()
        _workflow_generator = AutoWorkflowGenerator()
        session_id = _session_logger.start_session("Lilith Core interactive session")
        logger.info(f"Observability initialized. Session: {session_id}")

        # Initialize Safety & Policy
        approvals_registry = PendingApprovalsRegistry()
        system_policy = SystemPolicy()

        # Initialize Session Manager
        global _global_session_manager, _session_summarizer, _procedural_memory, _memory_extractor
        _global_session_manager = SessionManager()
        _session_summarizer = SessionSummarizer(project_root)
        _procedural_memory = ProceduralMemory(project_root)
        _memory_extractor = MemoryExtractor(project_root)
        logger.info(
            f"SessionManager initialized at {_global_session_manager.sessions_dir}"
        )

        msg_queue = queue.Queue()
        server = IPCServer(msg_queue)
        server.start()

        # v2.3 Fase B: notificaciones proactivas (monitores cada 60s)
        def _notification_loop(srv):
            from pathlib import Path

            from src.notifications.notification_engine import NotificationEngine

            engine = NotificationEngine(
                base_path=Path(project_root),
                get_token_stats=get_token_stats,
                send_event=lambda p: srv.send(Event(payload=p)),
            )
            time.sleep(10)  # Primera ejecución tras 10s para no saturar al arranque
            while True:
                try:
                    engine.run_once()
                except Exception as e:
                    logger.warning("NotificationEngine: %s", e)
                time.sleep(60)

        threading.Thread(target=_notification_loop, args=(server,), daemon=True).start()
        logger.info("NotificationEngine started (60s interval).")

        logger.info("Server started, entering main loop.")

        try:
            while True:
                # Check for expired approvals
                expired = approvals_registry.expire_due()
                for pa in expired:
                    server.send(
                        EventError(
                            payload={
                                "message": f"Command '{pa.request_payload.get('command')}' auto-denied due to timeout."
                            }
                        )
                    )

                try:
                    msg = msg_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                logger.info(f"Processing message: {msg.type} - {msg.action}")

                try:
                    if msg.action == "session_history":
                        # Listar historial de sesiones guardadas
                        try:
                            sessions = _global_session_manager.list_sessions()
                            server.send(
                                Event(
                                    payload={
                                        "type": "session_history",
                                        "sessions": sessions,
                                    }
                                )
                            )
                        except Exception as e:
                            server.send(
                                EventError(
                                    payload={
                                        "message": f"Error loading session history: {e}"
                                    }
                                )
                            )

                    elif msg.action == "load_session":
                        session_id = msg.payload.get("session_id")
                        try:
                            session_data = _global_session_manager.load_session(
                                session_id
                            )
                            if session_data:
                                _current_session_id = session_id
                                _current_messages = session_data.get("messages", [])
                                _current_session_summary = (
                                    session_data.get("summary") or None
                                )
                                logger.info(
                                    f"[load_session] Loaded {len(_current_messages)} messages from {session_id}"
                                )
                                # Enviar mensajes al frontend
                                server.send(
                                    Event(
                                        payload={
                                            "type": "session_loaded",
                                            "session_id": session_id,
                                            "messages": _current_messages,
                                        }
                                    )
                                )
                                logger.info(
                                    f"[load_session] Sent {len(_current_messages)} messages to frontend"
                                )
                                # Enviar estadísticas de tokens actualizadas
                                server.send(
                                    Event(
                                        payload={
                                            "type": "token_stats",
                                            **get_token_stats(),
                                        }
                                    )
                                )
                            else:
                                server.send(
                                    EventError(
                                        payload={
                                            "message": f"Session {session_id} not found"
                                        }
                                    )
                                )
                        except Exception as e:
                            server.send(
                                EventError(
                                    payload={"message": f"Error loading session: {e}"}
                                )
                            )

                    elif msg.action == "new_session":
                        # v2.2 Fase B: resumir sesión actual antes de limpiar
                        if (
                            _current_session_id
                            and _current_messages
                            and _session_summarizer
                        ):
                            try:
                                summary = asyncio.run(
                                    _session_summarizer.summarize(
                                        _current_messages, _current_session_id
                                    )
                                )
                                if summary:
                                    sem = SemanticMemory(project_root)
                                    sem.update_from_session(summary)
                            except Exception as e:
                                logger.warning(
                                    "Session summarizer on new_session: %s", e
                                )
                        # Crear nueva sesión
                        if _current_session_id and _current_messages:
                            # Guardar sesión actual primero (con summary si existe)
                            _global_session_manager.save_session(
                                _current_messages,
                                _current_session_id,
                                summary=_current_session_summary,
                            )
                        _current_session_id = _generate_session_id()
                        _current_messages = []
                        _current_session_summary = None
                        server.send(
                            Event(
                                payload={
                                    "type": "session_created",
                                    "session_id": _current_session_id,
                                }
                            )
                        )
                        server.send(
                            Event(payload={"type": "token_stats", **get_token_stats()})
                        )

                    elif msg.action == "get_token_stats":
                        server.send(
                            Event(payload={"type": "token_stats", **get_token_stats()})
                        )

                    elif msg.action == "send_message":
                        user_text = msg.payload.get("text", "").strip()

                        if user_text.startswith("@git"):
                            t = threading.Thread(
                                target=handle_git_command,
                                args=(user_text, git_tool, server, stats_tracker),
                            )
                            t.daemon = True
                            t.start()
                        elif user_text.startswith("@run"):
                            # The args must match the function signature
                            t = threading.Thread(
                                target=handle_run_command_threaded,
                                args=(
                                    user_text,
                                    sys_executor,
                                    server,
                                    stats_tracker,
                                    approvals_registry,
                                    system_policy,
                                    config,
                                ),
                            )
                            t.daemon = True
                            t.start()
                        elif user_text.startswith("@plan"):
                            # Nuevo: Manejo de planning requests
                            t = threading.Thread(
                                target=handle_planning_request,
                                args=(
                                    user_text,
                                    llm_providers,
                                    config,
                                    server,
                                    stats_tracker,
                                    system_prompt,
                                ),
                            )
                            t.daemon = True
                            t.start()
                        elif user_text.startswith("/auto "):
                            objetivo = user_text[6:].strip()
                            if not objetivo:
                                server.send(
                                    EventChatFinal(
                                        payload={
                                            "text": "Usa: /auto [objetivo]. Ejemplo: /auto Analiza main.py y dime los 3 problemas principales."
                                        }
                                    )
                                )
                            else:
                                t = threading.Thread(
                                    target=handle_auto_mode, args=(objetivo, server)
                                )
                                t.daemon = True
                                t.start()
                        else:
                            t = threading.Thread(
                                target=handle_chat_request,
                                args=(
                                    user_text,
                                    llm_providers,
                                    config,
                                    server,
                                    stats_tracker,
                                    system_prompt,
                                ),
                            )
                            t.daemon = True
                            t.start()

                    elif msg.action == "decision_result":
                        # Handle user approval/denial via registry
                        cid = msg.payload.get("correlation_id")
                        approved = msg.payload.get("approved", False)
                        logger.info(f"Received decision for {cid}: {approved}")

                        resolved = approvals_registry.resolve(cid, approved)
                        if not resolved:
                            logger.warning(
                                f"Received decision for unknown/ejected CID: {cid}"
                            )

                        # Check if this is a plan approval
                        if (
                            approved
                            and hasattr(server, "_active_plans")
                            and cid in server._active_plans
                        ):
                            plan = server._active_plans[cid]
                            logger.info(f"Executing approved plan: {plan.plan_id}")

                            # TODO: Implement plan execution engine
                            t = threading.Thread(
                                target=_execute_plan_threaded,
                                args=(plan, server, stats_tracker),
                            )
                            t.daemon = True
                            t.start()

                            # Clean up
                            del server._active_plans[cid]

                    elif msg.action == "auto_pause":
                        task_id = msg.payload.get("task_id")
                        if task_id:
                            from src.auto_mode.task_monitor import TaskMonitor

                            TaskMonitor(Path(project_root)).pause_task(task_id)
                    elif msg.action == "auto_resume":
                        task_id = msg.payload.get("task_id")
                        if task_id:
                            from src.auto_mode.task_monitor import TaskMonitor

                            TaskMonitor(Path(project_root)).resume_task(task_id)

                    elif msg.action == "get_status":
                        active_provider = config.llm.provider
                        client = llm_providers.get(active_provider, ollama)
                        is_healthy = client.check_health()
                        server.send(
                            EventStatusUpdate(
                                payload={
                                    "state": "idle",
                                    "provider": active_provider,
                                    "health": {
                                        active_provider: "ok" if is_healthy else "error"
                                    },
                                }
                            )
                        )

                    elif msg.action == "get_pantheon_status":
                        # Enviar estado del Panteón (pings reales a cada API)
                        router = AgentRouter()
                        info = router.get_agent_info()
                        availability = _ping_pantheon_availability()
                        status = {}
                        for key, agent in info.items():
                            status[key] = {
                                **agent,
                                "available": availability.get(
                                    key, agent.get("available", False)
                                ),
                            }
                        server.send(
                            Event(
                                payload={
                                    "type": "pantheon_status",
                                    "agents": status,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        )

                    elif msg.action == "get_config":
                        current_config = config_manager.get()
                        server.send(
                            EventConfigData(payload=current_config.model_dump())
                        )

                    elif msg.action == "update_config":
                        new_data = msg.payload
                        logger.info(f"Updating config with: {new_data}")
                        try:
                            # Update and save
                            config = config_manager.update(new_data)
                            # Notify success
                            server.send(
                                EventChatFinal(
                                    payload={
                                        "text": "[CONFIG] ConfiguraciÃ³n actualizada correctamente."
                                    }
                                )
                            )
                            # Broadcast new config back to UI to confirm sync
                            server.send(EventConfigData(payload=config.model_dump()))
                        except Exception as e:
                            logger.error(f"Failed to update config: {e}")
                            server.send(
                                EventChatFinal(
                                    payload={
                                        "text": f"[ERROR CONFIG] No se pudo guardar: {e}"
                                    }
                                )
                            )

                    elif msg.action == "get_stats":
                        stats_data = stats_tracker.get_all()
                        server.send(EventStatsData(payload=stats_data))

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    server.send(EventError(payload={"message": str(e)}))

        except KeyboardInterrupt:
            logger.info("Stopping SEBAS Core...")
            if _session_logger:
                _session_logger.end_session(status="shutdown")
            # v2.2 Fase B: resumir sesión actual y actualizar memoria semántica antes de guardar
            if _global_session_manager and _current_session_id and _current_messages:
                try:
                    if _session_summarizer:
                        try:
                            summary = asyncio.run(
                                _session_summarizer.summarize(
                                    _current_messages, _current_session_id
                                )
                            )
                            if summary:
                                sem = SemanticMemory(project_root)
                                sem.update_from_session(summary)
                        except Exception as e:
                            logger.warning("Session summarizer on shutdown: %s", e)
                    _global_session_manager.save_session(
                        _current_messages,
                        _current_session_id,
                        summary=_current_session_summary,
                    )
                    logger.info(f"Session {_current_session_id} saved before shutdown.")
                except Exception as e:
                    logger.error(f"Error saving session on shutdown: {e}")
            server.stop()
    except Exception as e:
        logger.critical("Fatal error in main loop: %s", e, exc_info=True)


def handle_auto_mode(objetivo, server):
    """v2.3 Fase C: Modo automático — planificar y ejecutar subtareas, emitir progreso por IPC."""
    global _current_messages, _current_session_id
    from src.auto_mode.task_executor import TaskExecutor
    from src.auto_mode.task_monitor import TaskMonitor
    from src.auto_mode.task_planner import TaskPlanner

    # Registrar mensaje del usuario en la sesión
    user_text = f"/auto {objetivo}"
    _current_messages.append({"role": "user", "content": user_text})
    if not _current_session_id:
        _current_session_id = _generate_session_id()

    monitor = TaskMonitor(Path(project_root))
    task_id = monitor.create_task(objetivo, _current_session_id)
    monitor.update_task(task_id, estado="planning")

    # Mensaje inicial en el chat
    server.send(
        EventChatFinal(
            payload={
                "text": f"⚡ **Modo automático** iniciado para: _{objetivo[:80]}_\n\nGenerando plan con Kimi…",
                "agent_display": "Lilith",
            }
        )
    )
    if _current_messages and _current_messages[-1].get("role") == "user":
        _current_messages.append(
            {
                "role": "assistant",
                "content": f"Modo automático iniciado: {objetivo[:80]}...",
                "agent_display": "Lilith",
            }
        )

    try:
        planner = TaskPlanner()
        plan = asyncio.run(planner.plan(objetivo))
        monitor.update_task(task_id, estado="running", plan=plan)
        server.send(
            Event(
                payload={
                    "type": "auto_plan_created",
                    "task_id": task_id,
                    "objetivo": plan.get("objetivo", objetivo),
                    "subtareas": plan.get("subtareas", []),
                    "estimacion": plan.get("estimacion", ""),
                }
            )
        )

        def on_progress(subtarea_id, total, estado, descripcion, resultado):
            server.send(
                Event(
                    payload={
                        "type": "auto_progress",
                        "task_id": task_id,
                        "subtarea": subtarea_id,
                        "total": total,
                        "estado": estado,
                        "descripcion": descripcion or "",
                        "resultado": (resultado[:500] + "…")
                        if isinstance(resultado, str) and len(resultado) > 500
                        else resultado,
                    }
                )
            )

        executor = TaskExecutor(task_monitor=monitor)
        res = asyncio.run(
            executor.execute(
                task_id,
                plan,
                file_context=plan.get("file_context"),
                on_progress=on_progress,
            )
        )
        monitor.update_task(
            task_id, estado="done", resultados=res.get("resultados", [])
        )

        resultados_list = res.get("resultados", [])
        resumen = (
            f"✅ **Modo automático completado** ({len(resultados_list)} subtareas)."
        )
        # Construir mensaje visible en el chat con el resumen completo de cada subtarea
        lineas = ["**Modo automático completado.**", ""]
        for r in resultados_list:
            sid = r.get("subtarea_id", "?")
            estado = r.get("estado", "")
            desc = (r.get("descripcion") or "")[:80]
            res_text = r.get("resultado")
            if isinstance(res_text, str) and len(res_text) > 600:
                res_text = res_text[:600].rstrip() + "\n…"
            lineas.append(f"**Subtarea {sid}** ({estado}): {desc}")
            if res_text:
                lineas.append(str(res_text))
            lineas.append("")
        content_chat = "\n".join(lineas).strip()
        server.send(
            Event(
                payload={
                    "type": "auto_complete",
                    "task_id": task_id,
                    "resumen": resumen,
                    "resultados": resultados_list,
                    "objetivo": res.get("objetivo", ""),
                }
            )
        )
        server.send(
            EventChatFinal(
                payload={
                    "text": content_chat,
                    "agent_display": "Lilith",
                }
            )
        )
        _current_messages.append(
            {
                "role": "assistant",
                "content": content_chat,
                "agent_display": "Lilith",
            }
        )
    except Exception as e:
        logger.exception("handle_auto_mode: %s", e)
        monitor.update_task(task_id, estado="failed")
        server.send(
            Event(
                payload={
                    "type": "auto_complete",
                    "task_id": task_id,
                    "resumen": str(e),
                    "resultados": [],
                    "error": True,
                }
            )
        )
        server.send(
            EventChatFinal(
                payload={
                    "text": f"❌ Modo automático falló: {e}",
                    "agent_display": "Lilith",
                }
            )
        )
    finally:
        server.send(EventStatusUpdate(payload={"state": "idle"}))


def handle_chat_request(text, providers, config, server, stats, system_prompt=None):
    global _current_messages, _current_session_summary, _current_session_id
    stats.record_message()
    start_time = time.perf_counter()
    server.send(EventStatusUpdate(payload={"state": "busy"}))

    # Auto-crear sesión si el frontend no envió new_session
    if not _current_session_id:
        _current_session_id = _generate_session_id()
        logger.info(f"[session] Auto-created session: {_current_session_id}")
    logger.debug("[auto-title] session_id=%s", _current_session_id)

    # Guardar mensaje del usuario en sesión actual
    _current_messages.append({"role": "user", "content": text})
    logger.info(
        f"[handle_chat_request] Added user message. Total: {len(_current_messages)} messages"
    )

    # Log user message to memory
    memory_manager = get_global_memory_manager()
    memory_manager.log_user_message(
        text=text, provider=config.llm.provider, model=config.llm.model
    )

    # Obtener contexto relevante de ChromaDB
    relevant_context = memory_manager.get_relevant_context(
        text, limit=5, time_filter_hours=48
    )
    context_str = (
        memory_manager.format_context_for_prompt(relevant_context)
        if relevant_context
        else ""
    )

    # === PANTEÓN: Routing de agentes ===
    # 1. Detectar comandos de fuerza (/eva, /adan, etc.)
    forced_agent, clean_text = parse_agent_command(text)
    if forced_agent:
        text = clean_text
        # Actualizar el mensaje del usuario en la sesión con el texto limpio
        _current_messages[-1]["content"] = text
        logger.info(f"[PANTEÓN] Comando forzado: {forced_agent}")

    # v2.2 Fase C: alerta de error recurrente (prepend contexto si ya ocurrió antes)
    message_for_llm = text
    if _procedural_memory:
        try:
            alert = asyncio.run(_procedural_memory.check_recurring_error(text))
            if alert:
                sol = (alert.get("soluciones") or [""])[0][:400]
                message_for_llm = f"[MEMORIA] Este error ocurrió antes el {alert.get('ultima_vez', '')}. Solución anterior: {sol}\n\n{text}"
                logger.info(
                    "[ProceduralMemory] Recurring error alert prepended to context"
                )
        except Exception as e:
            logger.warning("check_recurring_error: %s", e)

    router = AgentRouter()

    if forced_agent:
        agent_name = forced_agent
    else:
        agent_name = router.select_agent(
            message_for_llm, context_tokens=len(system_prompt) if system_prompt else 0
        )

    if agent_name != "grok":
        # Notificar al frontend que un agente del panteón está pensando
        agent_info = router.get_agent_info().get(agent_name, {})
        server.send(
            Event(
                payload={
                    "type": "agent_thinking",
                    "agent": agent_name,
                    "agent_display": agent_info.get("name", agent_name.capitalize()),
                }
            )
        )

        # Delegar al agente del panteón (usar message_for_llm por si hay alerta de error recurrente)
        import asyncio

        result = asyncio.run(
            router.execute(
                task=message_for_llm, agent_name=agent_name, context=context_str
            )
        )

        if result.get("delegated"):
            agent_response = result["result"]
            # Enviar respuesta al frontend indicando qué agente respondió
            server.send(EventChatDelta(payload={"delta": agent_response}))
            server.send(
                EventChatFinal(
                    payload={
                        "text": agent_response,
                        "agent": result["agent_display"],
                        "delegated": True,
                    }
                )
            )

            # Guardar en sesión actual incluyendo el agente
            _current_messages.append(
                {
                    "role": "assistant",
                    "content": agent_response,
                    "agent": agent_name,
                    "agent_display": result["agent_display"],
                }
            )
            logger.info(
                f"[handle_chat_request] Delegated to {result['agent_display']}. Total: {len(_current_messages)} messages"
            )

            # Log to memory
            memory_manager.log_assistant_message(
                text=agent_response, provider=result["agent"], model="pantheon"
            )

            server.send(EventStatusUpdate(payload={"state": "idle"}))

            # First response in new session: auto-title from first user message
            # Contar solo user+assistant (no system) para no fallar si hay system prompt
            if not _current_session_summary:
                _u = [m for m in _current_messages if m.get("role") == "user"]
                _a = [m for m in _current_messages if m.get("role") == "assistant"]
                if len(_u) == 1 and len(_a) == 1:
                    auto_title = (_u[0].get("content") or "").strip()[:40]
                    if auto_title:
                        _current_session_summary = auto_title
                        logger.info(
                            f"[auto-title] Session renamed: '{auto_title}' (id={_current_session_id})"
                        )
                        server.send(
                            Event(
                                payload={
                                    "type": "session_renamed",
                                    "session_id": _current_session_id,
                                    "name": auto_title,
                                }
                            )
                        )

            # Auto-save session (token_stats sent at end of handler via single place)
            if _global_session_manager and _current_session_id and _current_messages:
                try:
                    _global_session_manager.save_session(
                        _current_messages,
                        _current_session_id,
                        summary=_current_session_summary,
                    )
                    logger.info(
                        f"[auto-save] Session {_current_session_id} saved ({len(_current_messages)} messages)"
                    )
                except Exception as e:
                    logger.error(f"[auto-save] Error saving session: {e}")

            # Token stats after history is updated
            server.send(Event(payload={"type": "token_stats", **get_token_stats()}))
            # v2.2 Fase C + D: extraer y guardar; emitir memory_stored para badge en UI
            if _memory_extractor and agent_response:

                def _run_extract(u, a, srv):
                    try:

                        def on_stored(typ, summary):
                            srv.send(
                                Event(
                                    payload={
                                        "type": "memory_stored",
                                        "payload": {"type": typ, "summary": summary},
                                    }
                                )
                            )

                        asyncio.run(
                            _memory_extractor.extract_and_store(
                                u, a, on_stored=on_stored
                            )
                        )
                    except Exception as e:
                        logger.warning("MemoryExtractor (delegated): %s", e)

                threading.Thread(
                    target=_run_extract,
                    args=(text, agent_response, server),
                    daemon=True,
                ).start()
            duration = time.perf_counter() - start_time
            stats.add_llm_time(duration)
            return

    # Verificar uso de tokens para auto-compresión (token_stats se envía al final)
    token_stats = get_token_stats()
    if token_stats["percentage"] > 70:
        logger.info(
            f"Token usage at {token_stats['percentage']}%, compressing conversation..."
        )
        compressed = _global_session_manager.compress_conversation(
            _current_messages, token_stats["percentage"]
        )
        summary_msg = f"[Previous conversation summarized]: {compressed}"
        _current_messages = [
            {"role": "system", "content": summary_msg}
        ] + _current_messages[-10:]

    # Accumulate assistant response for logging
    assistant_response = []

    def on_chunk(chunk):
        server.send(EventChatDelta(payload={"delta": chunk}))
        assistant_response.append(chunk)  # Accumulate response

    logger.info("--> Iniciando handle_chat_request")
    model_name = config.llm.model
    provider_name = config.llm.provider

    logger.info(f"--> Buscando provider: {provider_name} con modelo: {model_name}")
    client = providers.get(provider_name)
    if not client:
        logger.error(
            f"--> Provider {provider_name} NO encontrado en diccionario providers: {list(providers.keys())}"
        )
        server.send(
            EventChatFinal(
                payload={
                    "text": f"âŒ Error: Provider '{provider_name}' no configurado o no encontrado."
                }
            )
        )
        server.send(EventStatusUpdate(payload={"state": "idle"}))
        return

    # Unified stream_chat interface (duck typing)
    # OllamaClient.stream_chat(model, prompt, callback, system) -> None (Push)
    # Grok/Venice/Kimi.stream_chat(messages, system, model) -> Generator (Pull)

    try:
        if provider_name == "ollama":
            logger.info("--> Invocando ollama.stream_chat")
            # Push style
            client.stream_chat(model_name, text, on_chunk, system=system_prompt)
        else:
            logger.info("--> Preparando modelo Pull (Grok/Venice/Kimi)")
            # Pull style (Grok/Venice/Kimi) — message_for_llm incluye alerta de error recurrente si aplica
            messages = [{"role": "user", "content": message_for_llm}]
            logger.info(f"--> Invocando stream_chat en {client.__class__.__name__}")
            generator = client.stream_chat(
                messages, system_prompt=system_prompt, model=model_name
            )
            logger.info("--> Comienza loop for chunk in generator")
            chunk_received = False
            for chunk in generator:
                chunk_received = True
                on_chunk(chunk)

            logger.info(
                f"--> Fin del loop chunk in generator. Â¿chunk_received?= {chunk_received}"
            )
            if not chunk_received:
                error_msg = f"âŒ Error: La API ({provider_name}) no devolviÃ³ ningÃºn texto. Verifica tu conexiÃ³n o revisa los logs."
                logger.error(error_msg)
                server.send(EventChatFinal(payload={"text": error_msg}))
                server.send(EventStatusUpdate(payload={"state": "error"}))
                return

    except Exception as e:
        logger.error(f"LLM Error (excepciÃ³n disparada): {e}", exc_info=True)
        server.send(EventChatFinal(payload={"text": f"âŒ Error del modelo: {e}"}))
        server.send(EventStatusUpdate(payload={"state": "idle"}))
        return

    logger.info("--> Guardando respuesta en memory manager")
    full_response = ""
    if assistant_response:
        full_response = "".join(assistant_response)
        # Guardar en sesión actual con agente Lilith
        _current_messages.append(
            {
                "role": "assistant",
                "content": full_response,
                "agent": "grok",
                "agent_display": "Lilith",
            }
        )
        logger.info(
            f"[handle_chat_request] Added assistant message. Total: {len(_current_messages)} messages"
        )
        memory_manager.log_assistant_message(
            text=full_response, provider=config.llm.provider, model=config.llm.model
        )
    else:
        logger.warning(
            f"La respuesta consolidada de {provider_name} quedÃ³ vacÃ­a tras el streaming."
        )

    # v2.2 Fase C + D: extraer y guardar; emitir memory_stored para badge en UI
    if _memory_extractor and full_response:

        def _run_extract_lilith(u, a, srv):
            try:

                def on_stored(typ, summary):
                    srv.send(
                        Event(
                            payload={
                                "type": "memory_stored",
                                "payload": {"type": typ, "summary": summary},
                            }
                        )
                    )

                asyncio.run(
                    _memory_extractor.extract_and_store(u, a, on_stored=on_stored)
                )
            except Exception as e:
                logger.warning("MemoryExtractor (Lilith): %s", e)

        threading.Thread(
            target=_run_extract_lilith, args=(text, full_response, server), daemon=True
        ).start()

    server.send(
        EventChatFinal(payload={"text": "", "agent": "Lilith"})
    )  # Empty text signals end of stream
    server.send(EventStatusUpdate(payload={"state": "idle"}))

    # First response in new session: auto-title from first user message
    # Contar solo user+assistant (no system) para no fallar si hay system prompt
    if not _current_session_summary:
        _u = [m for m in _current_messages if m.get("role") == "user"]
        _a = [m for m in _current_messages if m.get("role") == "assistant"]
        if len(_u) == 1 and len(_a) == 1:
            auto_title = (_u[0].get("content") or "").strip()[:40]
            if auto_title:
                _current_session_summary = auto_title
                logger.info(
                    f"[auto-title] Session renamed: '{auto_title}' (id={_current_session_id})"
                )
                server.send(
                    Event(
                        payload={
                            "type": "session_renamed",
                            "session_id": _current_session_id,
                            "name": auto_title,
                        }
                    )
                )

    # Auto-save session after each completed message (token_stats at end)
    if _global_session_manager and _current_session_id and _current_messages:
        try:
            _global_session_manager.save_session(
                _current_messages, _current_session_id, summary=_current_session_summary
            )
            logger.info(
                f"[auto-save] Session {_current_session_id} saved ({len(_current_messages)} messages)"
            )
        except Exception as e:
            logger.error(f"[auto-save] Error saving session: {e}")

    # Token stats after assistant message is in history
    server.send(Event(payload={"type": "token_stats", **get_token_stats()}))
    duration = time.perf_counter() - start_time
    stats.add_llm_time(duration)

    # Phase 4: Log to observability
    if _session_logger:
        _session_logger.log_tool_usage(
            tool_name="LLM", action="chat", duration_ms=duration * 1000, success=True
        )
    if _telemetry:
        _telemetry.log_tool_usage(
            tool_name="LLM", action="chat", duration_ms=duration * 1000, success=True
        )


def handle_git_command(text, git_tool, server, stats):
    stats.record_command("git")
    server.send(EventStatusUpdate(payload={"state": "busy"}))

    # Log to memory
    memory_manager = get_global_memory_manager()
    memory_manager.log_command(command=text, command_type="git")

    parts = text.split()
    if len(parts) < 2:
        response = "âŒ Uso: @git <comando>"
    else:
        cmd = parts[1:]
        response = git_tool.execute(cmd)

    server.send(EventChatFinal(payload={"text": f"[GIT]\n{response}"}))
    server.send(EventStatusUpdate(payload={"state": "idle"}))


def handle_run_command_threaded(
    text, sys_executor, server, stats_tracker, approvals_registry, system_policy, config
):
    stats_tracker.record_command("system")

    # Log to memory
    memory_manager = get_global_memory_manager()
    memory_manager.log_command(command=text, command_type="run")

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        server.send(EventChatFinal(payload={"text": "âŒ Uso: @run <comando>"}))
        return

    command = parts[1]

    # 1. Check Policy
    decision = system_policy.classify(command)
    risk = decision.risk.lower()

    requires_approval = decision.requires_approval

    # If config says block_on_pending_approval, we might check if there are ANY pending approvals first?
    # For V1 simplicity, we just check if THIS command needs approval.
    # Config override:
    if not config.safety.block_on_pending_approval:
        # If blocking is disabled, maybe we allow everything? Or just ignore pending queue?
        pass

    if requires_approval:
        import uuid

        cid = str(uuid.uuid4())

        # Create pending approval
        timeout = config.safety.approval_timeout_sec
        pa = approvals_registry.create(cid, timeout, {"command": command, "risk": risk})

        server.send(
            EventDecisionRequest(
                payload={
                    "command": command,
                    "risk_level": risk,
                    "reason": decision.reason,
                    "correlation_id": cid,
                }
            )
        )

        server.send(
            EventChatFinal(
                payload={
                    "text": f"â³ [{decision.risk}] Esperando aprobaciÃ³n para: `{command}`\nMotivo: {decision.reason}"
                }
            )
        )

        # Wait for decision
        pa.event.wait(timeout=timeout + 1)

        if pa.result is True:
            approved = True
        else:
            approved = False  # Denied or Expired or None (timeout)

        if not approved:
            reason = "Tiempo agotado" if pa.result is None else "Denegado por usuario"
            server.send(EventChatFinal(payload={"text": f"âŒ {reason}."}))
            return

    # Execution (Low risk or Approved)
    server.send(EventStatusUpdate(payload={"state": "busy"}))
    output = sys_executor.execute(command)
    server.send(EventChatFinal(payload={"text": f"[RUN]\n{output}"}))
    server.send(EventStatusUpdate(payload={"state": "idle"}))


def _execute_plan_threaded(plan, server, stats):
    """
    Ejecuta un plan aprobado con retries, timeouts y ejecuciÃ³n PARALELA

    Args:
        plan: ExecutionPlan a ejecutar
        server: IPCServer para enviar eventos
        stats: StatsTracker para mÃ©tricas
    """
    import queue
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from src.core.execution_engine import ExecutionEngine
    from src.core.tool_registry import get_tool_registry

    logger.info(f"Starting PARALLEL plan execution: {plan.plan_id}")

    server.send(EventStatusUpdate(payload={"state": "busy"}))
    server.send(
        EventChatDelta(
            payload={
                "delta": f"\nðŸš€ **Ejecutando plan** {plan.plan_id} (con paralelizaciÃ³n inteligente)\n\n",
                "type": "execution_start",
            }
        )
    )

    try:
        # Inicializar execution engine con retries
        execution_engine = ExecutionEngine(max_retries=2, default_timeout_seconds=30)

        # Obtener tool registry
        registry = get_tool_registry()
        if not registry._initialized:
            registry.initialize()

        # Thread-safe UI event queue
        ui_event_queue = queue.Queue()

        def send_ui_event(event_type, delta):
            """Thread-safe UI event sender"""
            ui_event_queue.put((event_type, delta))

        # UI event processor (runs in main thread)
        def process_ui_events():
            while True:
                try:
                    event_type, delta = ui_event_queue.get(timeout=0.1)
                    server.send(
                        EventChatDelta(payload={"delta": delta, "type": event_type})
                    )
                except queue.Empty:
                    break

        # EstadÃ­sticas de ejecuciÃ³n
        completed_steps = 0
        failed_steps = 0
        total_duration = 0.0
        step_results = {}

        # Lock para acceso thread-safe al plan
        plan_lock = threading.Lock()

        # FunciÃ³n para ejecutar un paso individual
        def execute_single_step(step, step_number, total_steps):
            """Ejecuta un paso con manejo de dependencias y retries"""

            # Verificar dependencias
            with plan_lock:
                deps_ready = all(
                    dep_step.status == PlanStepStatus.COMPLETED
                    for dep_step in plan.steps
                    if dep_step.step_id in step.dependencies
                )

                if not deps_ready:
                    send_ui_event(
                        "step_blocked",
                        f"â¸ï¸ **[{step_number}/{total_steps}] {step.title}** - Bloqueado (esperando {len(step.dependencies)} dependencias)\n",
                    )
                    step.status = PlanStepStatus.BLOCKED
                    return {"status": "blocked", "step_id": step.step_id}

            # Obtener herramienta
            tool_instance = None
            if step.tool:
                tool_instance = registry.get_tool(step.tool)

                if not tool_instance:
                    with plan_lock:
                        step.status = PlanStepStatus.FAILED
                        step.error = f"Tool {step.tool} not available"
                    send_ui_event(
                        "step_failed",
                        f"âŒ **[{step_number}/{total_steps}] {step.title}** - Tool no disponible\n",
                    )
                    return {
                        "status": "failed",
                        "step_id": step.step_id,
                        "error": step.error,
                    }

            # Marcar como en progreso
            with plan_lock:
                step.status = PlanStepStatus.IN_PROGRESS

            send_ui_event(
                "step_start",
                f"\nâ–¶ï¸ **[{step_number}/{total_steps}] {step.title}** - En progreso\n",
            )

            # Callback para progreso
            def progress_callback(msg):
                send_ui_event("step_progress", f"   â†³ {msg}\n")

            # Ejecutar con retries
            try:
                result = execution_engine.execute_step(
                    step, tool_instance, progress_callback
                )

                with plan_lock:
                    if result.success:
                        step.status = PlanStepStatus.COMPLETED
                        step.result = {"output": result.output}
                        retry_info = (
                            f" (attempt {result.attempts})"
                            if result.attempts > 1
                            else ""
                        )
                        send_ui_event(
                            "step_complete",
                            f"   âœ… **Completado**{retry_info} (took {result.duration_seconds:.1f}s)\n",
                        )
                        return {
                            "status": "completed",
                            "step_id": step.step_id,
                            "duration": result.duration_seconds,
                            "attempts": result.attempts,
                        }
                    else:
                        step.status = PlanStepStatus.FAILED
                        step.error = result.error
                        send_ui_event(
                            "step_failed",
                            f"   âŒ **Fallido** ({result.attempts} attempts): {result.error}\n",
                        )
                        return {
                            "status": "failed",
                            "step_id": step.step_id,
                            "error": result.error,
                        }

            except Exception as e:
                logger.error(
                    f"Unexpected error in step {step.step_id}: {e}", exc_info=True
                )
                with plan_lock:
                    step.status = PlanStepStatus.FAILED
                    step.error = f"Critical error: {str(e)}"
                send_ui_event("step_failed", f"   âŒ **Error crÃ­tico**: {str(e)}\n")
                return {
                    "status": "failed",
                    "step_id": step.step_id,
                    "error": step.error,
                }

        # EjecuciÃ³n paralela con thread pool
        max_workers = min(4, len(plan.steps))  # Limitar_workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit initial ready steps
            futures = {}
            active_steps = 0

            # Loop hasta completar todos los pasos
            while completed_steps + failed_steps < len(plan.steps):
                # Obtener pasos ready
                with plan_lock:
                    ready_steps = []
                    for idx, step in enumerate(plan.steps):
                        if step.status == PlanStepStatus.PENDING:
                            deps_ready = all(
                                plan.get_step(dep_id).status == PlanStepStatus.COMPLETED
                                for dep_id in step.dependencies
                            )
                            if deps_ready:
                                ready_steps.append((step, idx + 1))

                # Submit pasos ready al pool
                for step, step_num in ready_steps:
                    if len(futures) < max_workers:
                        future = executor.submit(
                            execute_single_step, step, step_num, len(plan.steps)
                        )
                        futures[future] = step.step_id
                        active_steps += 1
                        with plan_lock:
                            step.status = PlanStepStatus.IN_PROGRESS

                # Esperar a que al menos un paso complete
                if futures:
                    done, _ = as_completed(futures.keys(), timeout=1).__next__(), []

                    # Process completed futures
                    for future in list(futures.keys()):
                        if future.done():
                            try:
                                result = future.result()
                                step_results[result["step_id"]] = result

                                if result["status"] == "completed":
                                    completed_steps += 1
                                    total_duration += result.get("duration", 0)
                                elif result["status"] == "failed":
                                    failed_steps += 1

                            except Exception as e:
                                logger.error(f"Future error: {e}", exc_info=True)
                                failed_steps += 1

                            del futures[future]

                # Process UI events
                process_ui_events()

                # PequeÃ±a pausa para no saturar CPU
                time.sleep(0.1)

        # Procesar eventos UI finales
        process_ui_events()

        # Resumen final de ejecuciÃ³n
        execution_stats = execution_engine.get_progress()

        server.send(
            EventChatDelta(
                payload={
                    "delta": f"\nðŸ“Š **EjecuciÃ³n completada**\n",
                    "type": "execution_summary",
                }
            )
        )

        server.send(
            EventChatDelta(
                payload={
                    "delta": f"âœ… Completados: {completed_steps}/{len(plan.steps)} ({execution_stats['completion_rate']:.0%})\n",
                    "type": "summary_completed",
                }
            )
        )

        if failed_steps > 0:
            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"âŒ Fallidos: {failed_steps}\n",
                        "type": "summary_failed",
                    }
                )
            )

        if execution_stats["retry_count"] > 0:
            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"ðŸ”„ Retries automÃ¡ticos: {execution_stats['retry_count']}\n",
                        "type": "summary_retries",
                    }
                )
            )

        server.send(
            EventChatDelta(
                payload={
                    "delta": f"â±ï¸ **DuraciÃ³n total**: {execution_stats['total_duration_seconds']:.1f}s\n",
                    "type": "summary_duration",
                }
            )
        )

        server.send(
            EventChatFinal(
                payload={
                    "text": "",
                    "plan_id": plan.plan_id,
                    "execution_completed": True,
                    "stats": execution_stats,
                    "parallel_execution": True,
                }
            )
        )

    except Exception as e:
        logger.error(f"Critical plan execution error: {e}", exc_info=True)
        server.send(
            EventChatFinal(
                payload={
                    "text": f"âŒ Error crÃ­tico durante ejecuciÃ³n del plan: {str(e)}",
                    "error": str(e),
                }
            )
        )

    server.send(EventStatusUpdate(payload={"state": "idle"}))


def handle_planning_request(text, providers, config, server, stats, system_prompt=None):
    """
    Maneja solicitudes que requieren planificaciÃ³n multi-paso

    Args:
        text: Solicitud del usuario (puede empezar con @plan o ser detectada automÃ¡ticamente)
    """
    stats.record_message()
    start_time = time.perf_counter()
    server.send(EventStatusUpdate(payload={"state": "busy"}))

    # Extraer solicitud limpia (remover @plan si existe)
    user_intent = text
    if text.startswith("@plan"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            user_intent = parts[1]
        else:
            server.send(
                EventChatFinal(payload={"text": "âŒ Uso: @plan <tarea compleja>"})
            )
            server.send(EventStatusUpdate(payload={"state": "idle"}))
            return

    # Log to memory and get relevant context
    memory_manager = get_global_memory_manager()
    memory_manager.log_command(
        command=text,
        command_type="plan",
        provider=config.llm.provider,
        model=config.llm.model,
    )

    # Get relevant context from memory
    relevant_context = memory_manager.get_relevant_context(
        user_intent, limit=5, time_filter_hours=24
    )
    context_str = (
        memory_manager.format_context_for_prompt(relevant_context)
        if relevant_context
        else ""
    )

    # Determinar quÃ© LLM usar para planificaciÃ³n
    # Preferir Grok para planificaciÃ³n compleja, fallback a Ollama
    provider_name = config.llm.provider
    if provider_name == "ollama":
        # Para tareas complejas, usar Grok si estÃ¡ disponible
        if "grok" in providers:
            provider_name = "grok"

    client = providers.get(provider_name)
    if not client:
        server.send(
            EventChatFinal(
                payload={"text": f"âŒ Error: No LLM available for planning"}
            )
        )
        server.send(EventStatusUpdate(payload={"state": "idle"}))
        return

    # Crear thought streamer para UI
    thought_streamer = ThoughtStreamer(server.send)

    try:
        # Anunciar que estamos planificando
        server.send(
            EventChatDelta(
                payload={
                    "delta": "ðŸ¤– **Analizando solicitud y generando plan...**\n",
                    "type": "planning_start",
                }
            )
        )

        # Phase 4: Check auto-workflows BEFORE calling LLM
        if _workflow_generator:
            matching = _workflow_generator.find_matching_workflow(user_intent)
            if matching and matching.get("metadata", {}).get("confidence", 0) >= 0.7:
                match_score = matching["metadata"].get("match_score", 0)
                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"â™»ï¸ **Workflow cached encontrado** (score: {match_score:.0%})\n",
                            "type": "workflow_cache_hit",
                        }
                    )
                )
                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"ðŸ“‹ **{matching['name']}**: {matching['description']}\n",
                            "type": "workflow_details",
                        }
                    )
                )
                for step in matching.get("steps", []):
                    server.send(
                        EventChatDelta(
                            payload={
                                "delta": f"  â””â”€ {step.get('tool', '?')}.{step.get('action', '?')}\n",
                                "type": "workflow_step",
                            }
                        )
                    )
                server.send(
                    EventChatFinal(
                        payload={
                            "text": "",
                            "cached_workflow": matching["name"],
                            "match_score": match_score,
                        }
                    )
                )
                server.send(EventStatusUpdate(payload={"state": "idle"}))
                logger.info(
                    f"Auto-workflow cache hit: {matching['name']} (score={match_score})"
                )
                return

        # Obtener planning engine
        planning_engine = get_planning_engine(client, system_prompt)

        # Preparar contexto enriquecido con memoria histÃ³rica
        context = {
            "available_tools": ["SystemExecutor", "GitTools"],  # Por ahora bÃ¡sico
            "relevant_files": [],  # PodrÃ­a ser expandido con bÃºsqueda automÃ¡tica
            "memory_context": context_str,  # Context from previous conversations
        }

        # Generar plan
        plan = planning_engine.generate_plan(user_intent, context)

        # Stream plan details
        server.send(
            EventChatDelta(
                payload={
                    "delta": f"\n**AnÃ¡lisis:** {plan.analysis}\n\n",
                    "type": "analysis",
                }
            )
        )

        server.send(
            EventChatDelta(
                payload={
                    "delta": f"ðŸ“Š **Plan generado** ({len(plan.steps)} pasos, â±ï¸ {plan.estimated_total_duration}s, ðŸ’ª {plan.overall_confidence:.0%} confianza)\n\n",
                    "type": "plan_summary",
                }
            )
        )

        # Stream cada paso
        server.send(
            EventChatDelta(
                payload={"delta": "**Pasos de ejecuciÃ³n:**\n", "type": "steps_header"}
            )
        )

        for i, step in enumerate(plan.steps, 1):
            status_icon = "â³"
            tool_info = f" [{step.tool}]" if step.tool else ""

            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"{i}. {status_icon} **{step.title}**{tool_info}\n",
                        "type": "step_title",
                    }
                )
            )

            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"   â””â”€ {step.description}\n",
                        "type": "step_description",
                    }
                )
            )

            if step.dependencies:
                deps = ", ".join(step.dependencies)
                server.send(
                    EventChatDelta(
                        payload={
                            "delta": f"   â””â”€ Dependencias: {deps}\n",
                            "type": "step_deps",
                        }
                    )
                )

            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"   â””â”€ Estimado: {step.estimated_duration}s, Confianza: {step.confidence:.0%}\n\n",
                        "type": "step_metrics",
                    }
                )
            )

        # Resumen de riesgo y aprobaciÃ³n
        risk_emoji = {"low": "ðŸŸ¢", "medium": "ðŸŸ¡", "high": "ðŸ”´", "unknown": "âšª"}
        server.send(
            EventChatDelta(
                payload={
                    "delta": f"{risk_emoji.get(plan.risk_level, 'âšª')} **Nivel de riesgo:** {plan.risk_level}\n",
                    "type": "risk_assessment",
                }
            )
        )

        if plan.requires_approval:
            server.send(
                EventChatDelta(
                    payload={
                        "delta": f"âš ï¸ **Requiere aprobaciÃ³n manual**\n\n",
                        "type": "approval_required",
                    }
                )
            )

            # Crear solicitud de decisiÃ³n
            import uuid

            cid = str(uuid.uuid4())

            # Store plan in a registry for execution if approved
            # For now, we'll use a simple in-memory registry
            if not hasattr(server, "_active_plans"):
                server._active_plans = {}
            server._active_plans[cid] = plan

            server.send(
                EventDecisionRequest(
                    payload={
                        "command": f"Execute plan: {plan.plan_id}",
                        "risk_level": plan.risk_level,
                        "reason": f"Plan with {len(plan.steps)} steps and {plan.risk_level} risk",
                        "correlation_id": cid,
                        "plan_id": plan.plan_id,
                        "plan_summary": {
                            "steps_count": len(plan.steps),
                            "duration": plan.estimated_total_duration,
                            "confidence": plan.overall_confidence,
                        },
                    }
                )
            )

            # Wait for decision
            # This would need integration with approvals_registry
            # For now, we'll send a message indicating it's waiting
            server.send(
                EventChatFinal(
                    payload={
                        "text": f"â³ Esperando aprobaciÃ³n para ejecutar plan {plan.plan_id}...",
                        "plan_id": plan.plan_id,
                    }
                )
            )
        else:
            # Auto-execute low-risk plans
            server.send(
                EventChatDelta(
                    payload={
                        "delta": "âœ… **Ejecutando plan automÃ¡ticamente (bajo riesgo)...**\n",
                        "type": "auto_execute",
                    }
                )
            )

            # TODO: Implement plan execution engine
            server.send(
                EventChatFinal(
                    payload={
                        "text": f"ðŸš§ Auto-ejecuciÃ³n no implementada todavÃ­a. Plan {plan.plan_id} ready."
                    }
                )
            )

    except Exception as e:
        logger.error(f"Planning error: {e}", exc_info=True)
        server.send(
            EventChatFinal(payload={"text": f"âŒ Error en planificaciÃ³n: {str(e)}"})
        )

    server.send(EventStatusUpdate(payload={"state": "idle"}))

    duration = time.perf_counter() - start_time
    stats.add_llm_time(duration)


if __name__ == "__main__":
    main()
