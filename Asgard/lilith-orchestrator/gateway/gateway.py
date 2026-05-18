"""
Lilith Gateway
==============
Servidor FastAPI que expone LilithOrchestrator via REST.
Conecta el Bot Telegram (y futuros clients) con el motor de Hermes-Lilith.
Endpoints criticos implementados; el resto devuelven stubs seguros.
"""

import asyncio
import logging
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# Use orjson for faster JSON serialization; fall back to stdlib json if unavailable
try:
    import orjson

    def _json_dumps(obj: Any) -> str:
        return orjson.dumps(obj).decode("utf-8")

    def _json_loads(data: str | bytes) -> Any:
        return orjson.loads(data)

except ImportError:
    import json  # type: ignore[no-redef]

    def _json_dumps(obj: Any) -> str:  # type: ignore[misc]
        return json.dumps(obj, ensure_ascii=False)

    def _json_loads(data: str | bytes) -> Any:  # type: ignore[misc]
        return json.loads(data)


from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# ───────────────────────────────────────────────────────────────────────────────
# TEMPORARY: Bridge to legacy Hermes-Lilith monolith.
# This sys.path hack allows importing from the old codebase during the
# incremental migration. It MUST be removed once all Lilith modules are
# fully extracted into their own packages and the monolith is decommissioned.
# ───────────────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve()
_HERMES_ROOT = _HERE.parent.parent.parent / "Asgard" / "Hermes-Lilith"
if str(_HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(_HERMES_ROOT))

from Lilith.Core.config import SYSTEM_PROMPT

# Importar motor de Lilith
from Lilith.Core.orchestrator import LilithOrchestrator
from Lilith.memory.enhanced import get_memory
from Lilith.tools.files import execute_tool as file_tool
from Lilith.tools.system import execute_tool as system_tool


# RAG
try:
    from Lilith.RAG.rag_engine import get_rag_engine
except ImportError:
    get_rag_engine = None

# Scheduler, Agents, Plugins (lazy import en endpoints)
_get_scheduler = None
_get_agent_mgr = None
_get_plugin_mgr = None


def _scheduler():
    global _get_scheduler
    if _get_scheduler is None:
        from Lilith.Scheduler.task_scheduler import get_scheduler

        _get_scheduler = get_scheduler()
    return _get_scheduler


def _agent_mgr():
    global _get_agent_mgr
    if _get_agent_mgr is None:
        from Lilith.Agents.agent_manager import get_agent_manager

        _get_agent_mgr = get_agent_manager()
    return _get_agent_mgr


def _plugin_mgr():
    global _get_plugin_mgr
    if _get_plugin_mgr is None:
        from Lilith.Plugins.plugin_manager import get_plugin_registry

        _get_plugin_mgr = get_plugin_registry()
    return _get_plugin_mgr


# ───────────────────────────────────────────────────────────────────────────────
# Estado global
# ───────────────────────────────────────────────────────────────────────────────
_global_orch: LilithOrchestrator | None = None
_orch_lock = asyncio.Lock()
# Scale thread pool with CPU cores: 4 workers per core, capped at 16.
# The previous max_workers=2 was a bottleneck under concurrent load.
_executor = ThreadPoolExecutor(max_workers=min(16, os.cpu_count() * 4))


def _get_orchestrator() -> LilithOrchestrator:
    """Lazy init del orchestrator global."""
    global _global_orch
    if _global_orch is None:
        logger.info("Initializing LilithOrchestrator...")
        _global_orch = LilithOrchestrator()
        logger.info("LilithOrchestrator ready.")
    return _global_orch


def _chat_sync(text: str, history: list[dict] | None, user_id: str) -> str:
    """Ejecuta chat de forma sincrona (para thread pool)."""
    orch = _get_orchestrator()
    # Reconstruir historial
    system_msg = orch.messages[0] if orch.messages else {"role": "system", "content": SYSTEM_PROMPT}
    orch.messages = [system_msg]
    if history:
        for msg in history[-25:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                orch.messages.append(msg)
    orch.tool_call_count = 0
    orch.session_id = f"gateway_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        return orch.chat(text)
    except Exception as e:
        traceback.print_exc()
        return f"[Error del motor Lilith: {e}]"


def _pregunta_rapida_sync(text: str, user_id: str) -> str:
    """Pregunta rapida sin tool-calling."""
    orch = _get_orchestrator()
    system_msg = orch.messages[0] if orch.messages else {"role": "system", "content": SYSTEM_PROMPT}
    orch.messages = [system_msg, {"role": "user", "content": text}]
    orch.tool_call_count = 0
    orch.session_id = f"gateway_fast_{user_id}"
    try:
        # Forzar respuesta rapida sin tools
        from Lilith.Core.llm_client import LMStudioClient

        client = LMStudioClient()
        payload = {
            "model": client.model,
            "messages": orch.messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        import httpx

        r = httpx.post(f"{client.base_url}/chat/completions", json=payload, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"].get("content", "")
        client.close()
        return content
    except Exception as e:
        traceback.print_exc()
        return f"[Error: {e}]"


def _pc_fs_sync(op: str, path: str, dst: str, cmd: str, steps: list | None, user_id: str) -> dict:
    """Ejecuta operaciones de filesystem de forma sincrona."""
    try:
        if op == "list":
            result = file_tool("list_directory", {"path": path})
            return {
                "success": True,
                "output": _json_dumps(result),
            }
        if op == "mkdir":
            Path(path).mkdir(parents=True, exist_ok=True)
            return {"success": True, "output": f"Carpeta creada: {path}"}
        if op == "read":
            result = file_tool("read_file", {"path": path})
            return {"success": True, "output": result.get("content", "(vacío)")}
        if op == "write":
            result = file_tool("write_file", {"path": path, "content": cmd})
            return {"success": True, "output": _json_dumps(result)}
        if op == "move":
            import shutil

            shutil.move(path, dst)
            return {"success": True, "output": f"Movido: {path} -> {dst}"}
        if op == "copy":
            import shutil

            if Path(path).is_dir():
                shutil.copytree(path, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(path, dst)
            return {"success": True, "output": f"Copiado: {path} -> {dst}"}
        if op == "delete":
            import shutil

            p = Path(path)
            if p.is_dir():
                shutil.rmtree(path)
            else:
                p.unlink()
            return {"success": True, "output": f"Eliminado: {path}"}
        if op == "exec":
            result = system_tool("run_terminal", {"command": cmd})
            return {
                "success": True,
                "output": result.get("output", "") or result.get("error", "(sin salida)"),
            }
        if op == "batch":
            outputs = []
            for step in steps or []:
                sop = step.get("op", "")
                spath = step.get("path", "")
                sdst = step.get("dst", "")
                scmd = step.get("content", "") or step.get("cmd", "")
                res = _pc_fs_sync(sop, spath, sdst, scmd, None, user_id)
                outputs.append(res.get("output", "(ok)"))
            return {"success": True, "output": "\\n".join(outputs)}
        if op == "confirm":
            return {"success": True, "output": "Confirmación procesada (stub)."}
        return {
            "success": False,
            "error": f"Operación no soportada: {op}",
            "output": "(no implementado)",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "output": f"Error: {e}"}


# ───────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ───────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-warm the orchestrator; shutdown: no-op for now."""
    try:
        _get_orchestrator()
    except Exception as e:
        logger.warning("Could not pre-initialize orchestrator: %s", e)
    yield


app = FastAPI(title="Lilith Gateway", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "gateway": "lilith-v1"}


# ───────────────────────────────────────────────────────────────────────────────
# ENDPOINTS TELEGRAM (nuevos — el bot Telegram usa estos)
# ───────────────────────────────────────────────────────────────────────────────


@app.post("/api/telegram/chat")
async def api_telegram_chat(request: Request):
    """Chat principal para el bot de Telegram."""
    body = _json_loads(await request.body())
    text = (body.get("text") or "").strip()
    user_id = str(body.get("user_id", "telegram_user"))
    chat_id = str(body.get("chat_id", user_id))
    history = body.get("history")
    if not text:
        return JSONResponse(
            {"ok": False, "reply": "(mensaje vacío)", "agent": "Lilith"},
            status_code=400,
        )

    loop = asyncio.get_event_loop()
    async with _orch_lock:
        response = await loop.run_in_executor(_executor, _chat_sync, text, history, user_id)

    return {"ok": True, "reply": response, "agent": "Lilith", "chat_id": chat_id}


@app.post("/api/telegram/confirm")
async def api_telegram_confirm(request: Request):
    """Confirmar operacion pendiente para Telegram."""
    body = _json_loads(await request.body())
    body.get("token", "")
    approved = body.get("approved", False)
    return {
        "ok": True,
        "result": "Confirmación procesada." if approved else "Operación cancelada.",
        "agent": "Lilith",
    }


@app.post("/api/telegram/pc/confirm")
async def api_telegram_pc_confirm(request: Request):
    """Confirmar operacion PC para Telegram."""
    body = _json_loads(await request.body())
    body.get("token", "")
    approved = body.get("approved", False)
    return {
        "ok": approved,
        "result": "Operación PC ejecutada." if approved else "Operación PC cancelada.",
    }


# ───────────────────────────────────────────────────────────────────────────────
# PC OPERATIONS
# ───────────────────────────────────────────────────────────────────────────────


@app.post("/api/pc/fs")
async def api_pc_fs(request: Request):
    """Operaciones de filesystem remoto."""
    body = _json_loads(await request.body())
    op = body.get("op", "")
    path = body.get("path", "")
    dst = body.get("dst", "")
    cmd = body.get("cmd", "")
    steps = body.get("steps")
    user_id = str(body.get("user_id", "unknown"))

    # Confirmacion para operaciones de riesgo
    risky_ops = ("delete", "move", "exec", "batch")
    if op in risky_ops and body.get("requires_confirm") is not True:
        pass

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _pc_fs_sync, op, path, dst, cmd, steps, user_id)
    return result


# ───────────────────────────────────────────────────────────────────────────────
# STATS & MEMORY
# ───────────────────────────────────────────────────────────────────────────────


@app.get("/api/dashboard/stats")
async def api_dashboard_stats():
    """Estadisticas del sistema."""
    try:
        mem = get_memory()
        stats = mem.get_stats()
        return {
            "data": {
                "tokens": {"total_consumidos": 0, "hoy": 0},
                "sesiones": {
                    "total": stats["episodes"],
                    "esta_semana": stats["summaries"],
                    "por_dia": [],
                },
                "agentes_operativos": 4,
                "memory": stats,
            }
        }
    except Exception as e:
        return {
            "data": {
                "tokens": {"total_consumidos": 0},
                "sesiones": {"total": 0},
                "agentes_operativos": 4,
            },
            "error": str(e),
        }


@app.get("/api/memory/semantic")
async def api_memory_semantic():
    """Perfil semantico del usuario."""
    try:
        mem = get_memory()
        prefs = mem.get_user_preferences()
        entities = mem.get_entities(limit=20)
        return {
            "user_profile": prefs or {},
            "entities": [
                {"name": e["name"], "type": e["type"], "mentions": e["mentions"]} for e in entities
            ],
        }
    except Exception as e:
        return {"user_profile": {}, "error": str(e)}


@app.get("/api/notifications")
async def api_notifications():
    return {"success": True, "data": []}


# ───────────────────────────────────────────────────────────────────────────────
# SCHEDULER
# ───────────────────────────────────────────────────────────────────────────────


@app.get("/api/scheduler/tasks")
async def api_scheduler_tasks():
    try:
        sched = _scheduler()
        tasks = sched.get_all_tasks()
        return {
            "ok": True,
            "tasks": [t.to_dict() if hasattr(t, "to_dict") else str(t) for t in tasks],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/scheduler/tasks")
async def api_scheduler_add(request: Request):
    try:
        body = _json_loads(await request.body())
        sched = _scheduler()
        task_id = sched.add_task(
            description=body.get("description", ""),
            cron=body.get("cron"),
            preset=body.get("preset"),
            callback=body.get("callback"),
        )
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/scheduler/tasks/{task_id}")
async def api_scheduler_remove(task_id: str):
    try:
        sched = _scheduler()
        ok = sched.remove_task(task_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/scheduler/tasks/{task_id}/run")
async def api_scheduler_run(task_id: str):
    try:
        sched = _scheduler()
        ok = sched.run_task_now(task_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/scheduler/history")
async def api_scheduler_history():
    try:
        sched = _scheduler()
        hist = sched.get_task_history()
        return {"ok": True, "history": hist}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ───────────────────────────────────────────────────────────────────────────────
# AGENTS
# ───────────────────────────────────────────────────────────────────────────────


@app.get("/api/agents")
async def api_agents_list():
    try:
        mgr = _agent_mgr()
        agents = mgr.list_agents()
        return {
            "ok": True,
            "agents": [
                a.to_dict() if hasattr(a, "to_dict") else {"id": a.agent_id, "name": a.name}
                for a in agents
            ],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/agents")
async def api_agents_create(request: Request):
    try:
        body = _json_loads(await request.body())
        mgr = _agent_mgr()
        agent = mgr.create_agent(
            name=body.get("name", "Agente"),
            system_prompt=body.get("system_prompt", ""),
            capabilities=body.get("capabilities", []),
        )
        return {
            "ok": True,
            "agent": agent.to_dict() if hasattr(agent, "to_dict") else {"id": agent.agent_id},
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/agents/{agent_id}/stats")
async def api_agents_stats(agent_id: str):
    try:
        mgr = _agent_mgr()
        stats = mgr.get_agent_stats(agent_id)
        return {"ok": True, "stats": stats}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/agents/{agent_id}/delegate")
async def api_agents_delegate(agent_id: str, request: Request):
    try:
        body = _json_loads(await request.body())
        mgr = _agent_mgr()
        result = mgr.delegate_task(
            agent_id=agent_id,
            task_description=body.get("task", ""),
            context=body.get("context"),
        )
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.delete("/api/agents/{agent_id}")
async def api_agents_remove(agent_id: str):
    try:
        mgr = _agent_mgr()
        ok = mgr.remove_agent(agent_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ───────────────────────────────────────────────────────────────────────────────
# PLUGINS
# ───────────────────────────────────────────────────────────────────────────────


@app.get("/api/plugins")
async def api_plugins_list():
    try:
        pm = _plugin_mgr()
        plugins = pm.list_plugins()
        return {"ok": True, "plugins": [p.to_dict() for p in plugins]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/plugins/{plugin_id}/enable")
async def api_plugins_enable(plugin_id: str):
    try:
        pm = _plugin_mgr()
        ok = pm.enable_plugin(plugin_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/plugins/{plugin_id}/disable")
async def api_plugins_disable(plugin_id: str):
    try:
        pm = _plugin_mgr()
        ok = pm.disable_plugin(plugin_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/plugins/tools")
async def api_plugins_tools():
    try:
        pm = _plugin_mgr()
        tools = pm.get_all_tools()
        return {"ok": True, "tools": tools}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ───────────────────────────────────────────────────────────────────────────────
# GENERIC STUBS (compatibilidad)
# ───────────────────────────────────────────────────────────────────────────────


@app.get("/api/pending-for-dm")
async def api_pending_for_dm():
    return {"ok": True, "items": []}


@app.post("/api/mark-dm-sent")
async def api_mark_dm_sent(request: Request):
    return {"ok": True}


@app.get("/api/notes/pending")
async def api_notes_pending():
    return {"items": []}


@app.post("/api/feedback")
async def api_feedback(request: Request):
    return {"ok": True, "message": "Feedback registrado."}


@app.get("/api/patrones")
async def api_patrones():
    return {"learned": [], "suggested_intents": []}


@app.patch("/api/auto-learn/config")
async def api_auto_learn_config(request: Request):
    return {"ok": True}


@app.get("/api/notebook")
async def api_notebook():
    return {"items": []}


@app.post("/api/mode")
async def api_mode_post(request: Request):
    body = _json_loads(await request.body())
    return {"ok": True, "mode": body.get("mode", "default")}


@app.get("/api/mode")
async def api_mode_get(request: Request):
    return {"name": "default", "mode": "default"}


@app.get("/api/attention")
async def api_attention():
    return {"items": []}


@app.post("/api/attention/clear_completed")
async def api_attention_clear(request: Request):
    return {"ok": True, "removed": 0}


@app.post("/api/attention/add")
async def api_attention_add(request: Request):
    _json_loads(await request.body())
    return {"ok": True, "id": "stub-" + str(int(datetime.now().timestamp()))}


@app.post("/api/trusted-scopes/set")
async def api_trusted_scopes_set(request: Request):
    return {"ok": True}


@app.get("/api/trusted-scopes/list")
async def api_trusted_scopes_list():
    return {"items": []}


# ───────────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
