"""
Lilith Web API - FastAPI server with Core integration via IPC
"""
# Windows: Playwright usa subprocess; requiere Proactor (default en Windows).
# No forzar Selector, o asyncio.create_subprocess_exec fallará con NotImplementedError.
import sys
from pathlib import Path

# Cargar variables de entorno (.env) para que `LILITH_INTERNAL_TOKEN` coincida con el bot.
# El arranque actual (run_api_windows.py / server.py) no carga .env por defecto.
try:
    from dotenv import load_dotenv

    _root = Path(__file__).resolve().parents[3]  # D:\Proyectos\Yggdrasil\Asgard\Lilith
    # Cargar en orden de prioridad (primero el más específico, override=False = no sobreescribir)
    for _env_candidate in [
        _root / ".env",  # raíz del proyecto
        _root / "Discord" / ".env",  # bot Discord (legacy)
        _root / "Telegram" / ".env",  # bot Telegram
        _root / "Core" / "Config" / "secrets.env",  # secretos LLM
    ]:
        if _env_candidate.exists():
            load_dotenv(str(_env_candidate), override=False)
except Exception:
    # Nunca romper arranque por fallos de dotenv.
    pass

if sys.platform.startswith("win"):
    import asyncio as _asyncio_policy

    try:
        # Asegurar Proactor (subprocess disponible). En Windows, este es el default.
        _asyncio_policy.set_event_loop_policy(
            _asyncio_policy.WindowsProactorEventLoopPolicy()
        )
    except Exception:
        pass

import asyncio
import json
import logging
import queue
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# Add Core (parent of Backend) to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.middleware.input_validator import (
    InputValidationMiddleware,
    validate_ws_message,
)
from src.core.file_watcher import FileChange, get_watcher

# Context Integration
from src.core.git_context import get_git_context_manager
from src.core.pattern_learner import get_pattern_learner
from src.core.proactive_suggestions import (
    SuggestionPriority,
    SuggestionType,
    get_proactive_suggestions,
)
from src.core.project_context import get_project_manager
from src.core.session_manager import SessionMessage, get_session_manager
from src.core.tools.registry import ToolRegistryV3 as ToolRegistry
from src.core.trust_score_engine import get_trust_engine

# Initialize all v4.2 systems
from src.initialize_all_systems import initialize_all_systems

# IPC Integration
from src.ipc.client import IPCClient
from src.ipc.messages import (
    BaseIPCMessage,
    CommandDecisionResult,
    CommandSendMessage,
    EventChatDelta,
    EventChatFinal,
    EventData,
    EventDecisionRequest,
    EventError,
    EventStatusUpdate,
    IPCMessageType,
    QueryGetStatus,
)
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("LilithAPI")


# Models
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def _message_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El mensaje no puede estar vacío")
        if len(v) > 50_000:
            raise ValueError("Mensaje demasiado largo (max 50k chars)")
        return v

    @field_validator("session_id")
    @classmethod
    def _session_id_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        import re as _re

        if not _re.match(r"^[\w\-]{1,64}$", v):
            raise ValueError("session_id inválido")
        return v


class MessageResponse(BaseModel):
    success: bool
    response: str
    intent: Optional[str] = None
    tool_suggestions: List[str] = []
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict] = None


class ToolExecuteRequest(BaseModel):
    tool_name: str
    action: str
    parameters: Dict[str, Any]
    session_id: Optional[str] = "default"


class ConfirmationRequest(BaseModel):
    tool_name: str
    action: str
    parameters: Dict[str, Any]
    confirmed: bool
    session_id: Optional[str] = "default"


_auto_learn_task: Optional[asyncio.Task] = None
_task_scheduler: Optional["TaskScheduler"] = None


async def _auto_learn_loop() -> None:
    """Fase 4.3: cada N minutos ejecuta el job de auto-aprendizaje si está habilitado."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    interval_min = 60
    while True:
        try:
            from src.core.json_safe import safe_load

            cfg = safe_load(root / "Config" / "auto_learn.json", default={})
            if isinstance(cfg, dict):
                interval_min = max(5, int(cfg.get("interval_minutes") or 60))
                if cfg.get("auto_learn_enabled"):
                    from src.core.auto_learn import run_auto_learn_job

                    await asyncio.to_thread(run_auto_learn_job, root)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug("auto_learn_loop: %s", e)
        await asyncio.sleep(interval_min * 60.0)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup: init registry, IPC y motor de navegador. Reemplaza on_event('startup')."""
    from src.core.task_scheduler import TaskScheduler
    from src.core.tools.browser.browser_engine import BrowserEngine

    global main_loop, _auto_learn_task, _task_scheduler
    logger.info("Starting Lilith API server...")
    main_loop = asyncio.get_running_loop()

    await get_registry()
    get_ipc_client()

    # Motor de auto-aprendizaje
    _auto_learn_task = asyncio.create_task(_auto_learn_loop())

    # Scheduler de tareas programadas (APScheduler)
    try:
        root = Path(__file__).resolve().parent.parent.parent
        _task_scheduler = TaskScheduler(root)
        _task_scheduler.start()
    except Exception as e:
        logger.warning("TaskScheduler no pudo iniciar: %s", e)

    # MuninnDB: asegurar per-agent vaults al arranque
    try:
        root_path = Path(__file__).resolve().parent.parent.parent
        from src.core.memory.muninn_memory import MuninnMemory

        await MuninnMemory(root_path).ensure_vaults()
        logger.info("MuninnDB: per-agent vaults ensured.")
    except Exception as e:
        logger.debug("MuninnDB ensure_vaults skipped: %s", e)

    # Motor de navegador (Agencia Web V1)
    browser_engine = BrowserEngine()
    await browser_engine.start()

    # Recolector de basura (V1): limpiar screenshots huérfanos > 24h
    try:
        import os
        import time as _time

        screenshots_dir = (
            Path(__file__).resolve().parent.parent.parent / "Data" / "temp_screenshots"
        )
        if screenshots_dir.exists():
            cutoff = _time.time() - (24 * 60 * 60)
            for p in screenshots_dir.glob("*.png"):
                try:
                    if p.stat().st_mtime < cutoff:
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            screenshots_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Inicializar sistemas v4.2
    try:
        root_path = Path(__file__).resolve().parent.parent.parent
        modules = initialize_all_systems(root_path)
        logger.info(f"All v4.2 systems initialized: {list(modules.keys())}")
    except Exception as e:
        logger.error(f"Failed to initialize v4.2 systems: {e}")
        # No fatal - continuar con lo que se pueda

    # Inicializar WebhookManager (v4.2.8)
    try:
        root_path = Path(__file__).resolve().parent.parent.parent
        from src.core.webhooks import get_webhook_manager

        webhook_manager = get_webhook_manager(root_path)
        await webhook_manager.start()
        logger.info("WebhookManager: Iniciado")
    except Exception as e:
        logger.warning("WebhookManager no pudo iniciar: %s", e)

    # Inicializar WorkflowEngine (v4.2.8)
    try:
        root_path = Path(__file__).resolve().parent.parent.parent
        from src.core.workflows import get_workflow_engine

        workflow_engine = get_workflow_engine(root_path)
        logger.info(
            f"WorkflowEngine: {len(workflow_engine.list_workflows())} workflows cargados"
        )
    except Exception as e:
        logger.warning("WorkflowEngine no pudo iniciar: %s", e)

    # Inicializar DashboardWebSocketManager con realm providers (Ojo de Hrafnsmál)
    try:
        from src.core.agent_metrics import get_metrics
        from src.core.dashboard_websocket import (
            get_dashboard_manager,
            start_dashboard_websocket,
        )
        from src.core.traffic_tracker import get_traffic_tracker

        manager = get_dashboard_manager()

        async def _asgard_provider():
            from src.api.v1.asgard import get_ecosystem_status

            return {"asgard": await get_ecosystem_status()}

        def _vanaheim_provider():
            return {"vanaheim": get_metrics().get_stats_with_status()}

        def _traffic_provider():
            return {
                "traffic": get_traffic_tracker().get_sankey_data(window_seconds=300)
            }

        manager.register_realm_provider(_asgard_provider)
        manager.register_realm_provider(_vanaheim_provider)
        manager.register_realm_provider(_traffic_provider)
        await start_dashboard_websocket()
        logger.info("DashboardWebSocketManager: Iniciado con realm providers")
    except Exception as e:
        logger.warning("DashboardWebSocketManager no pudo iniciar: %s", e)

    try:
        yield
    finally:
        if _auto_learn_task and not _auto_learn_task.done():
            _auto_learn_task.cancel()
            try:
                await _auto_learn_task
            except asyncio.CancelledError:
                pass
        if _task_scheduler is not None:
            try:
                await _task_scheduler.shutdown()
            except Exception as e:
                logger.debug("Error al detener TaskScheduler: %s", e)
        # Detener WebhookManager
        try:
            from src.core.webhooks import get_webhook_manager

            await get_webhook_manager().stop()
            logger.info("WebhookManager: Detenido")
        except Exception as e:
            logger.debug("Error al detener WebhookManager: %s", e)
        # Detener Playwright
        await browser_engine.stop()
        # Detener DashboardWebSocketManager
        try:
            from src.core.dashboard_websocket import stop_dashboard_websocket

            await stop_dashboard_websocket()
            logger.info("DashboardWebSocketManager: Detenido")
        except Exception as e:
            logger.debug("Error al detener DashboardWebSocketManager: %s", e)


# Create FastAPI app
app = FastAPI(
    title="Lilith API",
    description="Operator-class AI Assistant API with Core Integration",
    version="2.1.0",
    lifespan=_lifespan,
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validación básica de inputs (tamaño de body, JSON malformado, etc.)
app.add_middleware(InputValidationMiddleware)

# Setup SPA static mounts (js, css, fonts) BEFORE API routes
from src.api.spa_serve import setup_spa_catch_all, setup_spa_mounts

setup_spa_mounts(app)

# IDE Integration API
from src.api.ide_api import router as ide_router

app.include_router(ide_router, prefix="/api/ide")
from src.api.v1.memory import router as memory_router

app.include_router(memory_router)
from src.api.v1.dashboard.router_v1 import router as dashboard_router

app.include_router(dashboard_router)

from fastapi.responses import RedirectResponse as _RedirectResponse


@app.get("/dashboard", include_in_schema=False)
async def _dashboard_redirect():
    return _RedirectResponse(url="/api/dashboard/")


from src.api.notifications_api import router as notifications_router

app.include_router(notifications_router)
from src.api.v1.bots.discord import router as discord_router

app.include_router(discord_router)
from src.api.security_api import router as security_router

app.include_router(security_router)
from src.api.vscode_api import router as vscode_router

app.include_router(vscode_router)
from src.api.v1.webhook import router as webhook_router

app.include_router(webhook_router)
from src.api.scheduler_api import router as scheduler_router

app.include_router(scheduler_router)
from src.api.proactive_api import router as proactive_router

app.include_router(proactive_router)
from src.api.v1.pc_agent import router as pc_router

app.include_router(pc_router)

from src.api.v1.bots.telegram import router as telegram_router

app.include_router(telegram_router)

from src.api.v1.muninn_trigger import router as muninn_trigger_router

app.include_router(muninn_trigger_router)

from src.api.cache_api import router as cache_router

app.include_router(cache_router)

from src.api.v1.webhooks import router as webhooks_router

app.include_router(webhooks_router)

from src.api.auth_api import router as auth_router

app.include_router(auth_router)

# v4.2.8: Workflows API
from src.api.v1.workflows import router as workflows_router

app.include_router(workflows_router)

# v4.2.8: Audit API
from src.api.audit_api import router as audit_router

app.include_router(audit_router)

from src.api.v1.agents import router as agents_api_router

app.include_router(agents_api_router)

from src.api.progress_ws import router as progress_ws_router

app.include_router(progress_ws_router)

from src.api.plugins_api import router as plugins_router

app.include_router(plugins_router)

from src.api.v1.health import router as health_router

app.include_router(health_router)

from src.api.metrics_api import router as metrics_router

app.include_router(metrics_router)

from src.api.backups_api import router as backups_router

app.include_router(backups_router)

# 4.2: DAG Execution Engine API
from src.api.dag_api import router as dag_router

app.include_router(dag_router)

# Misión 2: Council deliberativo
from src.api.v1.council import router as council_router

app.include_router(council_router)

# Misión 4: Asgard Command Center - Dashboard de telemetría
from src.api.v1.asgard import router as asgard_router

app.include_router(asgard_router)

# Ojo de Hrafnsmál - Realms API
from src.api.v1.realms import router as realms_router

app.include_router(realms_router)

# Documentation / Archivero API
from src.api.docs_api import router as docs_router

app.include_router(docs_router)

# Health Check Extendido - APIs externas
from src.api.v1.health_extended import router as health_extended_router

app.include_router(health_extended_router)

# Macro Learning API
from src.api.macro_api import router as macro_router

app.include_router(macro_router)

# Global registry
registry: Optional[ToolRegistry] = None

# Global IPC Client
ipc_client: Optional[IPCClient] = None
ipc_connected = False


async def get_registry() -> ToolRegistry:
    """Get or initialize tool registry"""
    global registry
    if registry is None:
        registry = ToolRegistry()
        await asyncio.to_thread(registry.initialize)
    return registry


main_loop: Optional[asyncio.AbstractEventLoop] = None


def get_ipc_client() -> Optional[IPCClient]:
    """Get IPC client instance, reconnecting if Core became available after startup."""
    global ipc_client, ipc_connected, main_loop

    def on_ipc_message(msg: BaseIPCMessage):
        if main_loop and not main_loop.is_closed():
            asyncio.run_coroutine_threadsafe(route_ipc_to_websocket(msg), main_loop)
        else:
            logger.error("No main event loop to route message")

    if ipc_client is None:
        ipc_client = IPCClient(on_message_callback=on_ipc_message)

    if not ipc_client.connected:
        if ipc_client.connect():
            ipc_connected = True
            logger.info("IPC Client connected to Core")
        else:
            ipc_connected = False

    return ipc_client


async def route_ipc_to_websocket(msg: BaseIPCMessage):
    """Route IPC messages from Core to active WebSocket connections"""
    if manager.active_connections:
        try:
            # Convert IPC message to WebSocket format
            ws_msg = {"type": msg.action, "timestamp": msg.ts}

            if isinstance(msg, EventChatDelta):
                ws_msg["content"] = msg.payload.get("delta", "")
                ws_msg["message_type"] = "streaming"
            elif isinstance(msg, EventChatFinal):
                content = msg.payload.get("text", "")
                ws_msg["content"] = content
                ws_msg["message_type"] = "final"
                ws_msg["completed"] = True
                ws_msg["agent"] = msg.payload.get("agent")
                ws_msg["agent_display"] = msg.payload.get(
                    "agent_display"
                ) or msg.payload.get("agent")
                ws_msg["delegated"] = msg.payload.get("delegated", False)

                # El Core ya persiste los mensajes en Memory/sessions — no duplicar aquí

            elif isinstance(msg, EventStatusUpdate):
                ws_msg["state"] = msg.payload.get("state", "unknown")
                ws_msg["provider"] = msg.payload.get("provider")
                ws_msg["health"] = msg.payload.get("health")
            elif isinstance(msg, EventError):
                ws_msg["content"] = msg.payload.get("message", "Error")
                ws_msg["message_type"] = "error"
            elif isinstance(msg, EventDecisionRequest):
                ws_msg["message_type"] = "approval_request"
                ws_msg["command"] = msg.payload.get("command")
                ws_msg["risk_level"] = msg.payload.get("risk_level")
                ws_msg["reason"] = msg.payload.get("reason")
                ws_msg["correlation_id"] = msg.payload.get("correlation_id")
            elif isinstance(msg, EventData):
                # token_stats, session_history, session_loaded, pantheon_status, etc.
                event_type = msg.payload.get("type", "unknown")
                logger.info(
                    f"[ws-bridge] Broadcasting EventData: {event_type} → {len(manager.active_connections)} clients"
                )
                await manager.broadcast_json(msg.payload)
                return

            logger.info(
                f"[ws-bridge] Broadcasting: {ws_msg.get('type')} → {len(manager.active_connections)} clients"
            )
            await manager.broadcast_json(ws_msg)
        except Exception as e:
            logger.error(f"Error routing IPC to WebSocket: {e}")


# API Routes
@app.get("/api/status")
async def get_status():
    """Get system status including Core connection (E.2: versionado unificado)."""
    try:
        from src.core.version import LILITH_VERSION

        version = LILITH_VERSION
    except Exception:
        version = "3.4"
    reg = await get_registry()
    global ipc_connected
    if ipc_client:
        ipc_connected = ipc_client.connected
    return {
        "status": "online",
        "version": version,
        "tools_registered": len(reg.list_tools()),
        "core_connected": ipc_connected,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/version")
async def get_version():
    """Versión y fase de Lilith (E.2)."""
    try:
        from src.core.version import (
            COMPATIBILITY,
            LILITH_VERSION,
            MEMORY_VERSION,
            PHASE,
        )

        return {
            "version": LILITH_VERSION,
            "phase": PHASE,
            "memory_version": MEMORY_VERSION,
            "compatibility": COMPATIBILITY,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return {
            "version": "3.4",
            "phase": "3.4",
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/meta-report")
async def get_meta_report(write_file: bool = False):
    """D.2: Meta-informe de uso (decision_source %, config, sugerencias). Opcional: escribir Data/meta_report.json."""
    try:
        from pathlib import Path

        from src.core.meta_report import build_meta_report, write_meta_report

        root = Path(__file__).resolve().parent.parent.parent
        if write_file:
            write_meta_report(root)
        return build_meta_report(root)
    except Exception as e:
        return {"error": str(e), "sources": {}, "config": {}, "suggestions": []}


@app.get("/api/audit/summary")
async def get_audit_summary(limit: int = 100):
    """D.3: Resumen del audit de decisiones (por fuente, últimas N)."""
    try:
        from pathlib import Path

        from src.core.json_safe import safe_load_lines

        root = Path(__file__).resolve().parent.parent.parent
        path = root / "Data" / "decision_audit.jsonl"
        if not path.exists():
            return {"sources": {}, "recent": [], "total": 0}
        lines = safe_load_lines(path, default=[])
        valid = [e for e in lines if isinstance(e, dict)]
        recent = valid[-limit:]
        sources = {}
        for e in valid:
            src = (e.get("decision_source") or "unknown").strip()
            sources[src] = sources.get(src, 0) + 1
        return {
            "sources": sources,
            "total": len(valid),
            "recent": [
                {
                    "ts": e.get("timestamp"),
                    "source": e.get("decision_source"),
                    "message": (e.get("message") or "")[:100],
                }
                for e in recent[-20:]
            ],
        }
    except Exception as e:
        return {"error": str(e), "sources": {}, "recent": [], "total": 0}


@app.get("/api/tools")
async def get_tools():
    """Get all available tools (B.2: lazy tools are instantiated on first list)."""
    reg = await get_registry()
    tools = []
    for name in reg.list_tools():
        tool_obj = reg.get(name)
        if not tool_obj:
            continue
        tools.append(
            {
                "name": name,
                "category": getattr(tool_obj, "category", "general"),
                "description": getattr(
                    tool_obj,
                    "description",
                    getattr(tool_obj, "get_description", lambda: "")()
                    or "No description available",
                ),
                "risk_level": getattr(tool_obj, "risk_level", "MEDIUM"),
                "capabilities": getattr(tool_obj, "capabilities", []),
            }
        )
    return {"tools": tools, "count": len(tools)}


@app.get("/api/tools/{tool_name}")
async def get_tool_detail(tool_name: str):
    """Get detailed info about a tool (B.2: lazy-loads on first access)."""
    reg = await get_registry()
    tool_obj = reg.get(tool_name)
    if not tool_obj:
        raise HTTPException(status_code=404, detail="Tool not found")

    return {
        "name": tool_name,
        "description": getattr(tool_obj, "description", "No description available"),
        "long_description": getattr(
            tool_obj, "long_description", getattr(tool_obj, "description", "")
        ),
        "category": getattr(tool_obj, "category", "general"),
        "risk_level": getattr(tool_obj, "risk_level", "MEDIUM"),
        "parameters": getattr(tool_obj, "parameters", {}),
        "capabilities": getattr(tool_obj, "capabilities", []),
        "example_usage": getattr(tool_obj, "example_usage", None),
    }


@app.post("/api/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Process chat message via HTTP (fallback when WebSocket unavailable)"""
    global ipc_connected

    # Try to use Core via IPC first
    if ipc_client and ipc_client.connected:
        try:
            # Send message to Core
            msg = CommandSendMessage(payload={"text": request.message})
            ipc_client.send(msg)

            # Wait for response (simplified - in production use a response queue)
            return MessageResponse(
                success=True,
                response="Mensaje enviado al Core. Usa WebSocket para respuestas en streaming.",
                intent="forwarded_to_core",
            )
        except Exception as e:
            logger.error(f"IPC send failed: {e}")

    # Fallback to local intent detection
    try:
        from src.core.conversational_intent_detector import ConversationalIntentDetector
        from src.core.response_generator import ResponseGenerator

        detector = ConversationalIntentDetector()
        generator = ResponseGenerator()

        intent_result = detector.detect_intent(request.message)
        natural_response = generator.generate_conversational_response(
            intent_type=intent_result.intent_type,
            user_message=request.message,
            tool_suggestions=intent_result.tool_suggestions,
        )

        return MessageResponse(
            success=True,
            response=natural_response,
            intent=intent_result.intent_type,
            tool_suggestions=intent_result.tool_suggestions,
            requires_confirmation=False,
        )
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        return MessageResponse(
            success=False, response=f"Error procesando mensaje: {str(e)}"
        )


@app.post("/api/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool with trust evaluation"""
    reg = await get_registry()
    trust_engine = get_trust_engine(request.session_id)

    trust_result = trust_engine.evaluate_operation(
        tool_name=request.tool_name,
        action=request.action,
        parameters=request.parameters,
    )

    if trust_result.execution_mode.value != "auto":
        return {
            "success": None,
            "requires_confirmation": True,
            "trust_score": trust_result.score,
            "execution_mode": trust_result.execution_mode.value,
            "preview": trust_result.preview,
            "reasons": trust_result.reasons,
            "alternatives": trust_result.alternatives,
        }

    try:
        tool = reg.get_tool(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        result = await tool.execute(request.action, **request.parameters)

        trust_engine.record_operation(
            tool_name=request.tool_name,
            action=request.action,
            success=result.get("success", False),
            execution_mode=trust_result.execution_mode,
            user_confirmed=None,
        )

        return {"success": True, "result": result, "trust_score": trust_result.score}
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"success": False, "error": str(e), "trust_score": trust_result.score}


@app.post("/api/confirm")
async def confirm_execution(request: ConfirmationRequest):
    """Confirm and execute pending operation"""
    if not request.confirmed:
        return {"success": False, "cancelled": True}

    reg = await get_registry()
    trust_engine = get_trust_engine(request.session_id)

    try:
        tool = reg.get_tool(request.tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")

        result = await tool.execute(request.action, **request.parameters)

        from src.core.trust_score_engine import ExecutionMode

        trust_engine.record_operation(
            tool_name=request.tool_name,
            action=request.action,
            success=result.get("success", False),
            execution_mode=ExecutionMode.CONFIRM,
            user_confirmed=True,
        )

        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Confirmed execution error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/history")
async def get_history(session_id: str = "default", limit: int = 50):
    """Get operation history"""
    trust_engine = get_trust_engine(session_id)
    history = trust_engine.operation_history[-limit:]

    return {
        "history": [
            {
                "tool_name": op.tool_name,
                "action": op.action,
                "success": op.success,
                "timestamp": op.timestamp,
                "execution_mode": op.execution_mode,
            }
            for op in reversed(history)
        ]
    }


@app.get("/api/stats")
async def get_stats(session_id: str = "default"):
    """Get trust statistics"""
    trust_engine = get_trust_engine(session_id)
    return trust_engine.get_statistics()


@app.get("/api/suggestions/presets")
async def get_suggestion_presets(context: Optional[str] = None):
    """Get static/preset suggestions for the UI"""
    suggestions = [
        {"text": "Analiza este proyecto", "icon": "search", "intent": "project_scan"},
        {"text": "Genera el README", "icon": "file-alt", "intent": "generate_readme"},
        {"text": "Estado del repo", "icon": "code-branch", "intent": "git_status"},
        {"text": "Ejecuta los tests", "icon": "vial", "intent": "run_tests"},
        {"text": "Ver cobertura", "icon": "chart-pie", "intent": "analyze_coverage"},
        {
            "text": "Busca dependencias sin usar",
            "icon": "search",
            "intent": "find_unused_deps",
        },
    ]
    return {"suggestions": suggestions}


# Git Context Routes
@app.get("/api/git/status")
async def get_git_status():
    """Get git repository status"""
    try:
        git_manager = get_git_context_manager()
        status = git_manager.get_quick_status()
        return status
    except Exception as e:
        logger.error(f"Error getting git status: {e}")
        return {"is_git_repo": False, "error": str(e)}


@app.get("/api/git/context")
async def get_git_context():
    """Get full git context"""
    try:
        git_manager = get_git_context_manager()
        context = git_manager.get_context()
        return context.to_dict()
    except Exception as e:
        logger.error(f"Error getting git context: {e}")
        return {"is_git_repo": False, "error": str(e)}


@app.get("/api/git/suggestions")
async def get_git_suggestions():
    """Get suggested git actions based on current state"""
    try:
        git_manager = get_git_context_manager()
        suggestions = git_manager.suggest_actions()
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        logger.error(f"Error getting git suggestions: {e}")
        return {"suggestions": [], "error": str(e)}


# Project Context Routes
@app.get("/api/project/context")
async def get_project_context():
    """Get project context for current directory"""
    try:
        import os

        current_dir = os.getcwd()

        project_manager = get_project_manager()
        context = project_manager.get_context(current_dir)

        return context.to_dict()
    except Exception as e:
        logger.error(f"Error getting project context: {e}")
        return {"is_project": False, "error": str(e)}


@app.get("/api/project/recent")
async def get_recent_projects(limit: int = 10):
    """Get list of recent projects"""
    try:
        project_manager = get_project_manager()
        projects = project_manager.get_recent_projects(limit)
        return {"projects": projects, "count": len(projects)}
    except Exception as e:
        logger.error(f"Error getting recent projects: {e}")
        return {"projects": [], "error": str(e)}


# Session Management Routes
@app.post("/api/sessions")
async def create_session(request: Dict[str, Any] = {}):
    """Create a new session"""
    try:
        session_manager = get_session_manager()
        name = request.get("name", "default")
        workspace_path = request.get("workspace_path")

        session = session_manager.create_session(name, workspace_path)

        return {"success": True, "session": session.to_dict()}
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/sessions")
async def list_sessions(limit: int = 20):
    """List available sessions"""
    try:
        session_manager = get_session_manager()
        sessions = session_manager.list_sessions(limit)
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return {"sessions": [], "error": str(e)}


@app.get("/api/sessions/current")
async def get_current_session():
    """Get current session info"""
    try:
        session_manager = get_session_manager()
        info = session_manager.get_current_session_info()
        return {"has_session": info is not None, "session": info}
    except Exception as e:
        logger.error(f"Error getting current session: {e}")
        return {"has_session": False, "error": str(e)}


@app.post("/api/sessions/{session_id}/load")
async def load_session(session_id: str):
    """Load a session"""
    try:
        session_manager = get_session_manager()
        session = session_manager.load_session(session_id)

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"success": True, "session": session.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading session: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/sessions/{session_id}/save")
async def save_session(session_id: str):
    """Save current session"""
    try:
        session_manager = get_session_manager()
        success = session_manager.save_current_session(force=True)

        return {"success": success}
    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        session_manager = get_session_manager()
        success = session_manager.delete_session(session_id)

        return {"success": success}
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, request: Dict[str, Any] = {}):
    """Rename a session"""
    try:
        session_manager = get_session_manager()
        new_name = request.get("name")

        if not new_name:
            raise HTTPException(status_code=400, detail="Name is required")

        success = session_manager.rename_session(session_id, new_name)

        return {"success": success}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming session: {e}")
        return {"success": False, "error": str(e)}


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._ws_to_session: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, session_id: str = "default"):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._ws_to_session[websocket] = session_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self._ws_to_session:
            del self._ws_to_session[websocket]

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

    async def broadcast_json(self, message: Dict):
        """Broadcast JSON message to all connections"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket: {e}")

    async def send_to_session(self, session_id: str, message: Dict):
        """Send message to specific session"""
        for ws, sid in self._ws_to_session.items():
            if sid == session_id:
                try:
                    await ws.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@app.post("/api/notifications/test")
async def trigger_test_notification():
    """Crea una notificación de prueba y la envía por WebSocket para ver el toast."""
    from src.notifications.notification_store import NotificationStore

    root = Path(__file__).resolve().parent.parent.parent
    store = NotificationStore(root)
    item = store.add(
        "info", "🔔 Notificación de prueba desde Lilith.", ref_id="test_demo"
    )
    payload = {
        "type": "notification_new",
        "id": item["id"],
        "tipo": item["tipo"],
        "mensaje": item["mensaje"],
    }
    if manager.active_connections:
        await manager.broadcast_json(payload)
    return {"success": True, "notification": item}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates (legacy)"""
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "unknown")

            if msg_type == "chat":
                response = await process_chat_message(message)
                await websocket.send_json(response)
            elif msg_type == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )
            elif msg_type == "subscribe":
                await websocket.send_json(
                    {"type": "subscribed", "channel": message.get("channel")}
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/conversational")
async def websocket_conversational_endpoint(websocket: WebSocket):
    """WebSocket endpoint for conversational interface with Core integration"""
    session_id = f"session_{datetime.now().timestamp()}"
    await manager.connect(websocket, session_id)

    # Send session created message
    await websocket.send_json(
        {
            "type": "session_created",
            "session_id": session_id,
            "core_connected": ipc_client.connected if ipc_client else False,
            "message": "Conectado a Lilith. Â¿En quÃ© puedo ayudarte?",
        }
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            ok, error_msg = validate_ws_message(message)
            if not ok:
                logger.warning("Mensaje WebSocket inválido: %s", error_msg)
                await websocket.send_json(
                    {
                        "type": "error",
                        "message_type": "validation_error",
                        "detail": error_msg,
                    }
                )
                continue
            await process_conversational_message(websocket, message, session_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def process_conversational_message(
    websocket: WebSocket, message: Dict, session_id: str
):
    """Process conversational WebSocket message with Core integration"""
    msg_type = message.get("type", "unknown")

    # Get session manager for persistence
    session_manager = get_session_manager()

    if msg_type == "message":
        user_text = message.get("text", "")

        # Try to send to Core via IPC first (reconnects automatically if Core is now available)
        # El Core es la fuente de verdad para mensajes — no duplicar add_message aquí
        get_ipc_client()
        if ipc_client and ipc_client.connected:
            try:
                # Send message to Core
                ipc_msg = CommandSendMessage(payload={"text": user_text})
                ipc_client.send(ipc_msg)

                # The response will come asynchronously via route_ipc_to_websocket
                # Send acknowledgment to user
                await websocket.send_json(
                    {
                        "type": "message_received",
                        "message_id": message.get("id"),
                        "status": "processing",
                    }
                )
                return
            except Exception as e:
                logger.error(f"Failed to send to Core: {e}")
                await websocket.send_json(
                    {"type": "error", "content": f"Error conectando con Core: {str(e)}"}
                )

        # Fallback: Local intent detection
        try:
            from src.core.conversational_intent_detector import (
                ConversationalIntentDetector,
            )

            detector = ConversationalIntentDetector()
            intent_result = detector.detect_intent(user_text)

            response_text = f"Core no disponible. IntenciÃ³n detectada localmente: {intent_result.intent_type}"

            # Save assistant response to session
            session_manager.add_message(
                role="assistant",
                content=response_text,
                metadata={"intent": intent_result.intent_type, "fallback": True},
            )

            await websocket.send_json(
                {
                    "type": "response",
                    "content": response_text,
                    "response_type": "agent",
                    "requires_approval": False,
                    "fallback": True,
                }
            )
        except Exception as e:
            await websocket.send_json({"type": "error", "content": f"Error: {str(e)}"})

    elif msg_type == "ping":
        await websocket.send_json(
            {
                "type": "pong",
                "core_connected": ipc_client.connected if ipc_client else False,
            }
        )

    elif msg_type == "approval":
        # Handle approval response from user
        if ipc_client and ipc_client.connected:
            try:
                approval_msg = CommandDecisionResult(
                    payload={
                        "correlation_id": message.get("correlation_id"),
                        "approved": message.get("approved", False),
                    }
                )
                ipc_client.send(approval_msg)

                await websocket.send_json(
                    {
                        "type": "approval_response",
                        "status": "sent_to_core",
                        "approved": message.get("approved", False),
                    }
                )
            except Exception as e:
                await websocket.send_json(
                    {
                        "type": "error",
                        "content": f"Error enviando aprobaciÃ³n: {str(e)}",
                    }
                )
        else:
            await websocket.send_json(
                {"type": "approval_response", "status": "core_not_connected"}
            )

    elif msg_type == "get_status":
        # Request status from Core
        if ipc_client and ipc_client.connected:
            try:
                status_msg = QueryGetStatus()
                ipc_client.send(status_msg)
            except Exception as e:
                logger.error(f"Failed to request status: {e}")

        await websocket.send_json(
            {
                "type": "status_response",
                "core_connected": ipc_client.connected if ipc_client else False,
                "timestamp": datetime.now().isoformat(),
            }
        )

    elif msg_type == "COMMAND":
        # Handle command messages (session_history, load_session, feedback, etc.)
        # Try to reconnect IPC in case Core started after API
        get_ipc_client()
        payload = message.get("payload") or {}
        action = message.get("action") or payload.get("action", "")

        if action == "session_history":
            # Get session list from session manager
            try:
                logger.info(
                    f"Getting session history from: {session_manager.storage_path}"
                )
                sessions = session_manager.list_sessions()
                logger.info(f"Found {len(sessions)} sessions")
                await websocket.send_json(
                    {"type": "session_history", "sessions": sessions}
                )
            except Exception as e:
                logger.error(f"Failed to get session history: {e}")
                await websocket.send_json({"type": "session_history", "sessions": []})

        elif action == "load_session":
            # Forward to Core via IPC
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_msg = CommandGeneric(
                        action="load_session", payload=message.get("payload", {})
                    )
                    ipc_client.send(ipc_msg)
                except Exception as e:
                    logger.error(f"Failed to send load_session to Core: {e}")
                    await websocket.send_json(
                        {"type": "error", "content": f"Error cargando sesión: {str(e)}"}
                    )
            else:
                await websocket.send_json(
                    {"type": "error", "content": "Core no disponible"}
                )

        elif action == "new_session":
            # Forward to Core via IPC — el Core crea la sesión y responde con session_created
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_msg = CommandGeneric(action="new_session", payload={})
                    ipc_client.send(ipc_msg)
                    # El Core responderá con EventData session_created que llegará al frontend
                except Exception as e:
                    logger.error(f"Failed to create new session: {e}")
            else:
                # Sin Core: respuesta local mínima para que el frontend no quede colgado
                import random

                fallback_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}"
                await websocket.send_json(
                    {"type": "session_created", "session_id": fallback_id}
                )

        elif action == "get_token_stats":
            # Forward to Core via IPC
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_msg = CommandGeneric(action="get_token_stats", payload={})
                    ipc_client.send(ipc_msg)
                except Exception as e:
                    logger.error(f"Failed to get token stats: {e}")

        elif action == "get_pantheon_status":
            # Forward to Core via IPC; Core responds with EventData pantheon_status
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_msg = CommandGeneric(
                        action="get_pantheon_status", payload=message.get("payload", {})
                    )
                    ipc_client.send(ipc_msg)
                except Exception as e:
                    logger.error(f"Failed to send get_pantheon_status to Core: {e}")

        elif action == "auto_pause":
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_client.send(
                        CommandGeneric(
                            action="auto_pause", payload=message.get("payload", {})
                        )
                    )
                except Exception as e:
                    logger.error("Failed to send auto_pause: %s", e)
        elif action == "auto_resume":
            if ipc_client and ipc_client.connected:
                try:
                    from src.ipc.messages import CommandGeneric

                    ipc_client.send(
                        CommandGeneric(
                            action="auto_resume", payload=message.get("payload", {})
                        )
                    )
                except Exception as e:
                    logger.error("Failed to send auto_resume: %s", e)

        elif action == "feedback":
            msg_content = payload.get("content") or ""
            feedback_type = payload.get("type") or ""
            message_id = payload.get("message_id")

            logger.info(
                "[feedback] Recibido: type=%s, content_len=%d",
                feedback_type,
                len(msg_content),
            )

            if not msg_content:
                await websocket.send_json(
                    {
                        "type": "feedback_ack",
                        "status": "ignored",
                        "reason": "empty_content",
                        "message_id": message_id,
                    }
                )
                return

            try:
                if feedback_type == "positive":
                    # Eva analiza qué hizo bien y se guarda patrón en code_style.respuestas_preferidas
                    from src.core.agents.panteon.eva import EvaAgent
                    from src.core.memory.memory_extractor import MemoryExtractor
                    from src.core.memory.semantic_memory import SemanticMemory

                    patron = ""
                    desc = ""

                    eva = EvaAgent()
                    if eva.is_available():
                        prompt = f"""Analiza esta respuesta del asistente que el usuario marcó como positiva
y devuelve SOLO un JSON con el patrón de estilo que deberíamos repetir:

Respuesta:
{msg_content[:800]}

{{
  "patron": "frase corta que describa el estilo o enfoque",
  "descripcion": "explicación breve de por qué esta respuesta es buena"
}}"""
                        loop = asyncio.get_event_loop()
                        raw = await loop.run_in_executor(
                            None,
                            lambda: eva.execute(
                                task="Clasifica el estilo de la respuesta preferida.",
                                context=prompt,
                            ),
                        )
                        pattern_data = MemoryExtractor._parse_json_from_response(
                            raw or ""
                        )
                        if isinstance(pattern_data, dict):
                            patron = str(pattern_data.get("patron") or "").strip()
                            desc = str(pattern_data.get("descripcion") or "").strip()

                        sem = SemanticMemory(
                            Path(__file__).resolve().parent.parent.parent
                        )
                        code_style = sem.load_code_style()
                        prefs = code_style.get("respuestas_preferidas") or []
                        if not isinstance(prefs, list):
                            prefs = []
                        from datetime import datetime as _dt

                        prefs.append(
                            {
                                "patron": patron or "respuesta_preferida",
                                "descripcion": desc,
                                "contenido": msg_content[:2000],
                                "recorded_at": _dt.utcnow().isoformat() + "Z",
                            }
                        )
                        code_style["respuestas_preferidas"] = prefs[-50:]
                        sem.save_code_style(code_style)

                elif feedback_type == "negative":
                    # Guardar en error_history.json como respuesta a evitar
                    from datetime import datetime as _dt

                    from src.core.memory.procedural_memory import ProceduralMemory

                    proc = ProceduralMemory(
                        Path(__file__).resolve().parent.parent.parent
                    )
                    history = proc.load_error_history()
                    today = _dt.utcnow().strftime("%Y-%m-%d")
                    history.append(
                        {
                            "tipo": "respuesta_evitar",
                            "contenido": msg_content[:2000],
                            "fecha": today,
                            "recurrencias": 1,
                        }
                    )
                    proc.save_error_history(history)

                await websocket.send_json(
                    {
                        "type": "feedback_ack",
                        "status": "stored",
                        "feedback_type": feedback_type,
                        "message_id": message_id,
                    }
                )
            except Exception as e:
                logger.warning("Error procesando feedback: %s", e)
                await websocket.send_json(
                    {
                        "type": "feedback_ack",
                        "status": "error",
                        "message_id": message_id,
                    }
                )


async def process_chat_message(message: Dict) -> Dict:
    """Process chat message via WebSocket (legacy)"""
    try:
        from src.core.conversational_intent_detector import ConversationalIntentDetector

        detector = ConversationalIntentDetector()
        text = message.get("text", "")
        intent_result = detector.detect_intent(text)

        return {
            "type": "chat_response",
            "intent": intent_result.intent_type,
            "tool_suggestions": intent_result.tool_suggestions,
            "confidence": intent_result.confidence,
            "message": f"DetectÃ©: {intent_result.intent_type}",
        }
    except Exception as e:
        return {"type": "error", "error": str(e)}


# Pattern Learning Routes
@app.post("/api/patterns/record")
async def record_action(request: Dict[str, Any] = {}):
    """Record a user action for pattern learning"""
    try:
        learner = get_pattern_learner()

        action_type = request.get("action_type", "unknown")
        details = request.get("details", "")
        context = request.get("context", {})

        success = learner.record_action(action_type, details, context)

        return {"success": success}
    except Exception as e:
        logger.error(f"Error recording action: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/patterns/predict")
async def predict_next_action(
    last_type: Optional[str] = None, last_details: Optional[str] = None
):
    """Predict next actions based on patterns"""
    try:
        learner = get_pattern_learner()

        # Get current context
        context = {}
        try:
            import os

            from src.core.project_context import get_project_manager

            project_manager = get_project_manager()
            project_ctx = project_manager.get_context(os.getcwd())
            if project_ctx.config:
                context["project_type"] = project_ctx.config.project_type
        except:
            pass

        predictions = learner.predict_next_action(last_type, last_details, context)

        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Error predicting actions: {e}")
        return {"predictions": [], "error": str(e)}


@app.get("/api/patterns")
async def get_patterns(pattern_type: Optional[str] = None, min_confidence: float = 0.0):
    """Get detected patterns"""
    try:
        learner = get_pattern_learner()
        patterns = learner.get_patterns(pattern_type, min_confidence)

        return {"patterns": patterns, "count": len(patterns)}
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        return {"patterns": [], "error": str(e)}


@app.get("/api/patterns/stats")
async def get_pattern_stats():
    """Get pattern learning statistics"""
    try:
        learner = get_pattern_learner()
        stats = learner.get_stats()

        return stats
    except Exception as e:
        logger.error(f"Error getting pattern stats: {e}")
        return {"error": str(e)}


# Proactive Suggestions Routes
@app.get("/api/suggestions")
async def get_suggestions(include_shown: bool = False):
    """Get pending proactive suggestions"""
    try:
        suggestions = get_proactive_suggestions()
        pending = suggestions.get_pending_suggestions(include_shown)

        return {"suggestions": [s.to_dict() for s in pending], "count": len(pending)}
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return {"suggestions": [], "error": str(e)}


@app.get("/api/suggestions/next")
async def get_next_suggestion():
    """Get next suggestion to show (rate limited)"""
    try:
        suggestions = get_proactive_suggestions()
        suggestion = suggestions.get_next_suggestion()

        if suggestion is None:
            return {
                "has_suggestion": False,
                "message": "No suggestions available or rate limited",
            }

        return {"has_suggestion": True, "suggestion": suggestion.to_dict()}
    except Exception as e:
        logger.error(f"Error getting next suggestion: {e}")
        return {"has_suggestion": False, "error": str(e)}


@app.post("/api/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(suggestion_id: str, request: Dict[str, Any] = {}):
    """Dismiss a suggestion"""
    try:
        suggestions = get_proactive_suggestions()
        feedback = request.get("feedback")
        success = suggestions.dismiss_suggestion(suggestion_id, feedback)

        return {"success": success}
    except Exception as e:
        logger.error(f"Error dismissing suggestion: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/suggestions/{suggestion_id}/action")
async def take_suggestion_action(suggestion_id: str):
    """Mark that action was taken for a suggestion"""
    try:
        suggestions = get_proactive_suggestions()
        success = suggestions.mark_action_taken(suggestion_id)

        return {"success": success}
    except Exception as e:
        logger.error(f"Error marking action taken: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/suggestions/stats")
async def get_suggestions_stats():
    """Get suggestions statistics"""
    try:
        suggestions = get_proactive_suggestions()
        stats = suggestions.get_stats()

        return stats
    except Exception as e:
        logger.error(f"Error getting suggestions stats: {e}")
        return {"error": str(e)}


# File Watcher Routes
@app.post("/api/watcher/start")
async def start_file_watcher(request: Dict[str, Any] = {}):
    """Start watching a directory for changes"""
    try:
        import os

        path = request.get("path", os.getcwd())
        recursive = request.get("recursive", True)

        watcher = get_watcher()
        success = watcher.start_watching(path, recursive)

        return {"success": success, "path": path, "recursive": recursive}
    except Exception as e:
        logger.error(f"Error starting file watcher: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/watcher/stop")
async def stop_file_watcher():
    """Stop file watcher"""
    try:
        watcher = get_watcher()
        watcher.stop_watching()

        return {"success": True}
    except Exception as e:
        logger.error(f"Error stopping file watcher: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/watcher/changes")
async def get_recent_changes(seconds: int = 60):
    """Get recent file changes"""
    try:
        watcher = get_watcher()
        changes = watcher.get_recent_changes(seconds)

        return {"changes": [c.to_dict() for c in changes], "count": len(changes)}
    except Exception as e:
        logger.error(f"Error getting changes: {e}")
        return {"changes": [], "error": str(e)}


@app.get("/api/watcher/stats")
async def get_watcher_stats():
    """Get file watcher statistics"""
    try:
        watcher = get_watcher()
        stats = watcher.get_file_stats()

        return stats
    except Exception as e:
        logger.error(f"Error getting watcher stats: {e}")
        return {"error": str(e)}


# ===== FASES A-E API ENDPOINTS =====


@app.get("/api/fases/status")
async def get_fases_status():
    """Get status of Fases A-E tools"""
    try:
        from src.tools.fases_integration import (
            AutoDocumenterTool,
            CodeReviewTool,
            ConversationTool,
            MLAnalyzerTool,
            SecurityScannerTool,
            SmartCommitTool,
            TestGeneratorTool,
        )

        tools_status = {
            "SecurityScanner": SecurityScannerTool().check_dependencies(),
            "CodeReviewAI": CodeReviewTool().check_dependencies(),
            "TestGenerator": TestGeneratorTool().check_dependencies(),
            "AutoDocumenter": AutoDocumenterTool().check_dependencies(),
            "SmartCommit": SmartCommitTool().check_dependencies(),
            "MLCodeAnalyzer": MLAnalyzerTool().check_dependencies(),
            "ConversationEngine": ConversationTool().check_dependencies(),
        }

        return {
            "available": True,
            "tools": tools_status,
            "total_available": sum(1 for v in tools_status.values() if v),
        }
    except Exception as e:
        logger.error(f"Error getting Fases status: {e}")
        return {"available": False, "error": str(e)}


@app.post("/api/fases/security/scan")
async def fases_security_scan(
    include_dependencies: bool = True, file_path: Optional[str] = None
):
    """Run security scanner (FASE C)"""
    try:
        from src.tools.fases_integration import SecurityScannerTool

        scanner = SecurityScannerTool()
        if file_path:
            result = scanner.execute("scan_file", file_path=file_path)
        else:
            result = scanner.execute(
                "scan_project", include_dependencies=include_dependencies
            )

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Security scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fases/code-review")
async def fases_code_review(file_path: Optional[str] = None):
    """Run code review (FASE C)"""
    try:
        from src.tools.fases_integration import CodeReviewTool

        reviewer = CodeReviewTool()
        if file_path:
            result = reviewer.execute("review_file", file_path=file_path)
        else:
            result = reviewer.execute("review_project")

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Code review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fases/generate-tests")
async def fases_generate_tests(file_path: str):
    """Generate tests for file (FASE C)"""
    try:
        from src.tools.fases_integration import TestGeneratorTool

        generator = TestGeneratorTool()
        result = generator.execute("generate_tests", file_path=file_path)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Test generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fases/docstrings/scan")
async def fases_scan_docstrings(file_path: Optional[str] = None):
    """Scan for missing docstrings (FASE B)"""
    try:
        from src.tools.fases_integration import AutoDocumenterTool

        documenter = AutoDocumenterTool()
        result = documenter.execute("scan_missing", file_path=file_path)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Docstring scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fases/commit/suggestions")
async def fases_commit_suggestions(count: int = 3):
    """Get smart commit suggestions (FASE B)"""
    try:
        from src.tools.fases_integration import SmartCommitTool

        commit_tool = SmartCommitTool()
        result = commit_tool.execute("get_suggestions", count=count)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Commit suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fases/ml/analyze")
async def fases_ml_analyze():
    """Run ML code analysis (FASE E)"""
    try:
        from src.tools.fases_integration import MLAnalyzerTool

        analyzer = MLAnalyzerTool()
        result = analyzer.execute("analyze_project")

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"ML analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fases/ml/duplicates")
async def fases_ml_duplicates(similarity: float = 0.85):
    """Find code duplicates (FASE E)"""
    try:
        from src.tools.fases_integration import MLAnalyzerTool

        analyzer = MLAnalyzerTool()
        result = analyzer.execute("find_duplicates", similarity=similarity)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Duplicates search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== PAIR PROGRAMMING (FASE E) =====


@app.get("/api/pair/status")
async def get_pair_status():
    """Get pair programming status"""
    try:
        from src.tools.fases_integration import PairProgrammingTool

        tool = PairProgrammingTool()
        result = tool.execute("get_status")

        return {
            "success": result.success,
            "available": tool.check_dependencies(),
            "message": result.message,
        }
    except Exception as e:
        logger.error(f"Error getting pair status: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/pair/start")
async def pair_start_session(file_path: str):
    """Start pair programming session for a file"""
    try:
        from src.tools.fases_integration import PairProgrammingTool

        tool = PairProgrammingTool()
        result = tool.execute("start_session", file_path=file_path)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error starting pair session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pair/suggestions")
async def pair_get_suggestions(file_path: str):
    """Get live suggestions for a file"""
    try:
        from src.tools.fases_integration import PairProgrammingTool

        tool = PairProgrammingTool()
        result = tool.execute("get_suggestions", file_path=file_path)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pair/autocomplete")
async def pair_autocomplete(file_path: str, prefix: str = ""):
    """Get autocomplete suggestions"""
    try:
        from src.tools.fases_integration import PairProgrammingTool

        tool = PairProgrammingTool()
        result = tool.execute("autocomplete", file_path=file_path, prefix=prefix)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error getting autocomplete: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== METRICS DASHBOARD (FASE E) =====


@app.get("/api/metrics/dashboard")
async def get_metrics_dashboard():
    """Get complete metrics dashboard"""
    try:
        from src.tools.fases_integration import MetricsDashboardTool

        tool = MetricsDashboardTool()
        result = tool.execute("get_dashboard")

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/trends")
async def get_metrics_trends(days: int = 14):
    """Get trends analysis"""
    try:
        from src.tools.fases_integration import MetricsDashboardTool

        tool = MetricsDashboardTool()
        result = tool.execute("get_trends", days=days)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/snapshot")
async def save_metrics_snapshot():
    """Save current metrics snapshot"""
    try:
        from src.tools.fases_integration import MetricsDashboardTool

        tool = MetricsDashboardTool()
        result = tool.execute("save_snapshot")

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
        }
    except Exception as e:
        logger.error(f"Error saving snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== END FASES A-E =====


def start_server(host: str = "0.0.0.0", port: Optional[int] = None):
    """Start the API server. Port: LILITH_API_PORT o PORT en .env, por defecto 8000."""
    if port is None:
        import os

        port = int(
            os.environ.get("LILITH_API_PORT") or os.environ.get("PORT") or "8000"
        )
    uvicorn.run(app, host=host, port=port)


# ===== FILE SYSTEM ENDPOINTS FOR SPA =====


class FileContentRequest(BaseModel):
    path: str
    content: str


@app.get("/api/files/tree")
async def get_file_tree(path: str = "."):
    """Get project file tree"""
    try:
        import os
        from pathlib import Path as FilePath

        root = FilePath(path).resolve()
        if not root.exists():
            return {"success": False, "error": "Path not found"}

        def build_tree(p: FilePath, depth=0):
            if depth > 5:  # Limit depth
                return None

            result = {
                "id": str(p),
                "name": p.name or str(p),
                "path": str(p),
                "type": "directory" if p.is_dir() else "file",
            }

            if p.is_dir():
                children = []
                try:
                    for child in sorted(p.iterdir()):
                        if child.name.startswith(".") or child.name in [
                            "node_modules",
                            "__pycache__",
                            ".git",
                            "dist",
                            "build",
                        ]:
                            continue
                        child_tree = build_tree(child, depth + 1)
                        if child_tree:
                            children.append(child_tree)
                except PermissionError:
                    pass
                result["children"] = children
            else:
                # Detect language
                ext = p.suffix.lower()
                lang_map = {
                    ".py": "python",
                    ".js": "javascript",
                    ".jsx": "javascript",
                    ".ts": "typescript",
                    ".tsx": "typescript",
                    ".json": "json",
                    ".md": "markdown",
                    ".html": "html",
                    ".css": "css",
                    ".scss": "css",
                }
                result["language"] = lang_map.get(ext, "plaintext")

            return result

        tree = build_tree(root)
        return {"success": True, "data": tree}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/files/content")
async def get_file_content(path: str):
    """Get file content"""
    try:
        from pathlib import Path as FilePath

        file_path = FilePath(path).resolve()

        # Security check
        if not str(file_path).startswith(str(FilePath.cwd())):
            return {"success": False, "error": "Access denied"}

        if not file_path.exists():
            return {"success": False, "error": "File not found"}

        if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
            return {"success": False, "error": "File too large"}

        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/files/save")
async def save_file(request: FileContentRequest):
    """Save file content"""
    try:
        from pathlib import Path as FilePath

        file_path = FilePath(request.path).resolve()

        # Security check
        if not str(file_path).startswith(str(FilePath.cwd())):
            return {"success": False, "error": "Access denied"}

        file_path.write_text(request.content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===== SPA CATCH-ALL (MUST BE LAST) =====
# This catches all non-API routes for React Router
# It must be defined AFTER all API routes
setup_spa_catch_all(app)

# ===== MAIN =====

if __name__ == "__main__":
    import os

    port = int(os.environ.get("LILITH_API_PORT") or os.environ.get("PORT") or "8000")
    logger.info(
        "Lilith API listening on port %s (LILITH_API_PORT/PORT to override)", port
    )
    start_server(port=port)
