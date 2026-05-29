"""
Lilith — API de Telegram.
Canal principal de Ainz. Acceso completo: conversación, PC Agent, agentes, investigación.
Prioridad más alta sobre Discord DM y Discord público.
"""
import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel
from src.api.dependencies import get_orchestrator

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
logger = logging.getLogger("lilith.telegram_api")

# ─── Helpers básicos ──────────────────────────────────────────────────────────


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


async def _record_confirmation_to_muninn(
    action: str, plan_summary: str, original_message: str, transport: str
) -> None:
    """Escribe confirmación/denegación del owner como engrama en MuninnDB vault telegram."""
    try:
        from datetime import datetime

        from src.core.memory.muninn_memory import (
            MuninnMemory,
            _run_coro_fire_and_forget,
        )

        # F.16: Usar MuninnMemory con vault de telegram
        muninn = MuninnMemory(_project_root(), transport="telegram")
        if action == "authorize":
            concept = f"owner_approved:{plan_summary[:80]}"
            content = (
                f"El owner autorizó la acción: {plan_summary}. "
                f"Contexto: {original_message[:200]}. Transporte: {transport}."
            )
            tags = ["confirmation", "approved", transport]
        else:
            concept = f"owner_denied:{plan_summary[:80]}"
            content = (
                f"El owner RECHAZÓ la acción: {plan_summary}. "
                f"Contexto: {original_message[:200]}. Transporte: {transport}."
            )
            tags = ["confirmation", "denied", transport]
        _run_coro_fire_and_forget(
            muninn.write(
                vault="telegram",
                concept=concept,
                content=content,
                tags=tags,
                metadata={
                    "action": action,
                    "plan_summary": plan_summary[:200],
                    "timestamp": datetime.now().isoformat(),
                },
            )
        )
    except Exception:
        pass


def _internal_token() -> str:
    return (os.getenv("LILITH_INTERNAL_TOKEN", "") or "").strip()


def _owner_chat_id() -> str:
    return (os.getenv("TELEGRAM_OWNER_CHAT_ID", "") or "").strip()


def _json_response(data: dict, status_code: int = 200) -> Response:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        status_code=status_code,
        media_type="application/json; charset=utf-8",
    )


def _verify(request: Request) -> bool:
    token = _internal_token()
    if not token:
        return False
    got = (request.headers.get("X-Lilith-Token") or "").strip()
    return got == token


# ─── Orchestrator singleton ───────────────────────────────────────────────────

_tg_orchestrator = None


def get_orchestrator():
    global _tg_orchestrator
    if _tg_orchestrator is None:
        from src.core.learning import LearningEngine, LocalIntentClassifier
        from src.core.memory import MemoryManager
        from src.core.orchestrator import Orchestrator
        from src.core.planner import Planner
        from src.core.tools.registry import create_default_registry

        project_root = _project_root()
        registry = create_default_registry(project_root)
        memory_manager = MemoryManager(project_root)
        learning_engine = LearningEngine(memory_manager)
        local_classifier = LocalIntentClassifier(project_root)
        planner = Planner(
            memory_manager=memory_manager,
            learning_engine=learning_engine,
            local_intent_classifier=local_classifier,
        )
        _tg_orchestrator = Orchestrator(
            planner, registry, memory_manager=memory_manager
        )
        try:
            from src.core.feedback_store import set_base_path

            set_base_path(project_root)
        except Exception:
            pass
    return _tg_orchestrator


# ─── Sistema de prioridad de canales ─────────────────────────────────────────


def _touch_priority():
    try:
        from src.core.channel_priority import channel_priority

        channel_priority.touch("telegram")
    except Exception:
        pass


# ─── Construcción del system prompt ──────────────────────────────────────────

TELEGRAM_OWNER_INSTRUCTION = (
    "\n\n[Canal: Telegram — Bunker de mando de Ainz. Máxima prioridad. "
    "Acceso completo: PC Agent, todos los agentes, memoria total. "
    "Responde de forma directa y operativa. Puedes ejecutar operaciones de sistema cuando Ainz lo pida. "
    "Si la operación es peligrosa, siempre pide confirmación antes de ejecutar.]"
)

TELEGRAM_CAPABILITIES_BLOCK = """
[Capacidades disponibles — Telegram owner]
SISTEMA DE ARCHIVOS (PC Agent):
- pc_list: listar contenido de carpetas (sin confirmación)
- pc_mkdir: crear carpetas (requiere confirmación)
- pc_move: mover archivos/carpetas (requiere confirmación)
- pc_copy: copiar archivos/carpetas (requiere confirmación)
- pc_delete: eliminar archivos/carpetas (requiere confirmación)
- pc_write_file: crear/escribir archivos (requiere confirmación)
- pc_exec: ejecutar comandos del sistema (requiere confirmación)
- pc_batch: múltiples operaciones en lote (1 sola confirmación)

F.17 MACROS DE PC AGENT (1 confirmación para todo el batch):
- backup_proyecto: Respalda carpeta de proyecto
- compilar_y_test: npm run build + npm test
- setup_proyecto_python: venv + requirements.txt
- limpiar_temp: Limpia archivos temporales
- git_commit_push: git add + commit + push
- crear_estructura_web: Crea estructura base web

AGENTES: delegate_eva, delegate_odin, delegate_adan, generate_reply
MEMORIA: store_semantic_fact, search_semantic_memory
INVESTIGACIÓN: lore_extractor, web_search
PROYECTOS: project (create/list/status/advance)

RUTAS CORTAS: "proyectos"=D:\\Proyectos, "lilith"=D:\\Proyectos\\Lilith,
              "core"=.../Core, "backend"=.../Backend, "config"=.../Config,
              "desktop"=%USERPROFILE%\\Desktop, "downloads"=%USERPROFILE%\\Downloads
"""

# ─── Historial conversacional por chat_id ─────────────────────────────────────
# F.16: Reemplazado por TelegramSessionManager para sesiones persistentes

_telegram_history: Dict[str, List[Dict[str, str]]] = {}
_MAX_HISTORY = 20

# F.16: Session manager singleton
_tg_session_manager = None


def _get_session_manager():
    """Obtiene el TelegramSessionManager singleton."""
    global _tg_session_manager
    if _tg_session_manager is None:
        from src.core.telegram_session import get_session_manager

        _tg_session_manager = get_session_manager(_project_root())
    return _tg_session_manager


def _append_history(chat_id: str, role: str, content: str) -> None:
    """F.16: Añade mensaje al historial persistente."""
    # Usar session manager para persistencia
    try:
        sm = _get_session_manager()
        sm.add_message(chat_id, chat_id, role, content)
    except Exception:
        pass

    # Fallback a memoria
    if chat_id not in _telegram_history:
        _telegram_history[chat_id] = []
    _telegram_history[chat_id].append(
        {
            "role": role,
            "content": content[:2000],
        }
    )
    if len(_telegram_history[chat_id]) > _MAX_HISTORY:
        _telegram_history[chat_id] = _telegram_history[chat_id][-_MAX_HISTORY:]


def _format_history(chat_id: str, limit: int = 10) -> str:
    """F.16: Formatea historial desde sesión persistente."""
    # Intentar obtener desde session manager primero
    try:
        sm = _get_session_manager()
        return sm.format_history_for_prompt(chat_id, chat_id, limit)
    except Exception:
        pass

    # Fallback a memoria
    history = _telegram_history.get(chat_id, [])[-limit:]
    if not history:
        return ""
    lines = []
    for h in history:
        label = "Ainz" if h["role"] == "user" else "Lilith"
        lines.append(f"{label}: {h['content'][:300]}")
    return "\n".join(lines)


# ─── Plan preview para confirmación ───────────────────────────────────────────

_SAFE_TOOLS = {
    "pc_list",
    "generate_reply",
    "delegate_eva",
    "delegate_odin",
    "delegate_adan",
    "store_semantic_fact",
    "lore_extractor",
    "web_search",
    "search_semantic_memory",
    "delegate_lucifer",
}
_ALWAYS_CONFIRM = {"pc_delete", "pc_exec"}
_WRITE_TOOLS = {"pc_mkdir", "pc_move", "pc_copy", "pc_write_file", "pc_batch"}
_PC_TOOLS = _ALWAYS_CONFIRM | _WRITE_TOOLS | {"pc_list"}


def _plan_needs_confirmation(steps: list) -> bool:
    for s in steps:
        tool = getattr(s, "tool_name", "")
        if tool in _ALWAYS_CONFIRM:
            return True
        if tool in _WRITE_TOOLS:
            return True
    return False


def _generate_plan_preview(steps: list, message: str) -> str:
    lines = ["📋 **Plan de ejecución:**\n"]
    tool_emojis = {
        "pc_list": "📁",
        "pc_mkdir": "📂",
        "pc_move": "📦",
        "pc_copy": "📄",
        "pc_delete": "🗑️",
        "pc_write_file": "✏️",
        "pc_exec": "⚡",
        "pc_batch": "🔧",
        "delegate_eva": "🧠",
        "delegate_odin": "🔮",
        "delegate_adan": "💻",
    }
    for i, step in enumerate(steps[:5]):
        tool = getattr(step, "tool_name", "?")
        params = getattr(step, "params", {}) or {}
        emoji = tool_emojis.get(tool, "🔧")
        # Build detail string
        if "path" in params:
            detail = f"`{params['path']}`"
        elif "source" in params and "destination" in params:
            detail = f"`{params['source']}` → `{params['destination']}`"
        elif "command" in params:
            detail = f"`{params['command']}`"
        elif "task" in params:
            detail = str(params["task"])[:80]
        else:
            detail = tool
        lines.append(f"{i+1}. {emoji} **{tool}**: {detail}")
    has_dangerous = any(getattr(s, "tool_name", "") in _ALWAYS_CONFIRM for s in steps)
    has_write = any(getattr(s, "tool_name", "") in _WRITE_TOOLS for s in steps)
    if has_dangerous:
        lines.append(
            "\n⚠️ Esta operación modifica el sistema de archivos de forma irreversible."
        )
    elif has_write:
        lines.append("\n⚠️ Esta operación modificará el sistema de archivos.")
    lines.append("\n¿Autorizar? Responde con el token: `CONFIRM <token>`")
    return "\n".join(lines)


def _build_system_prompt(user_id: Optional[str] = None) -> str:
    project_root = _project_root()

    # Usar el nuevo persona_loader para obtener la identidad de Lilith
    try:
        from src.core.persona.loader import get_persona_loader

        loader = get_persona_loader(project_root)
        system_prompt = loader.get_system_prompt("lilith", include_common=True)
        owner_context = loader.get_owner_context()
        # Inyectar contexto del owner al inicio
        system_prompt = f"{owner_context}\n\n{system_prompt}"
    except Exception:
        system_prompt = "[LILITH — Orquestadora del Panteón]\nEres Lilith. Hablas con Ainz (Martin). Sé directa y útil."

    # Agregar contexto de memoria si existe
    try:
        from src.core.memory_store import MemoryStore

        store = MemoryStore(project_root)
        hits = store.search_active_memories("", k=3)
        memory_ctx = store.format_memories_block(hits)
        if memory_ctx:
            system_prompt += f"\n\n[MEMORIA ACTIVA]\n{memory_ctx}"
    except Exception:
        pass

    # Cargar perfil del usuario para personalizar respuestas (legacy fallback)
    try:
        from src.core.memory.semantic_memory import SemanticMemory

        sem = SemanticMemory(project_root)
        profile = sem.load_user_profile()
        if profile:
            nombre = profile.get("nombre", "Usuario")
            edad = profile.get("edad")
            preferencias = profile.get("preferencias", {})
            proyectos = profile.get("proyectos", {})

            profile_lines = [f"\n[Perfil del Usuario]"]
            profile_lines.append(f"Nombre: {nombre}")
            if edad:
                profile_lines.append(f"Edad: {edad}")
            if preferencias:
                prefs_str = ", ".join(f"{k}={v}" for k, v in preferencias.items())
                profile_lines.append(f"Preferencias: {prefs_str}")
            if proyectos:
                activos = [
                    k
                    for k, v in proyectos.items()
                    if isinstance(v, dict) and v.get("estado") == "activo"
                ]
                if activos:
                    profile_lines.append(f"Proyectos activos: {', '.join(activos)}")

            system_prompt += "\n" + "\n".join(profile_lines)
    except Exception:
        pass

    system_prompt += TELEGRAM_OWNER_INSTRUCTION
    system_prompt += TELEGRAM_CAPABILITIES_BLOCK
    return system_prompt


# ─── Confirmaciones pendientes ────────────────────────────────────────────────


@dataclass
class _TgPending:
    token: str
    message: str
    steps: List[Dict[str, Any]]
    system_prompt: str
    created_at: float = field(default_factory=time.time)


_tg_pending: Dict[str, _TgPending] = {}
_TG_PENDING_TTL = 300  # 5 minutos


def _cleanup_pending():
    now = time.time()
    expired = [
        t for t, p in _tg_pending.items() if now - p.created_at > _TG_PENDING_TTL
    ]
    for t in expired:
        del _tg_pending[t]


# ─── Modelos Pydantic ─────────────────────────────────────────────────────────


class TelegramChatRequest(BaseModel):
    text: str
    chat_id: str
    user_id: Optional[str] = None
    message_id: Optional[int] = None


class TelegramConfirmRequest(BaseModel):
    token: str
    approved: bool


# ─── Endpoint principal ───────────────────────────────────────────────────────


@router.post("/chat")
async def telegram_chat(request: Request) -> Response:
    if not _verify(request):
        return _json_response({"ok": False, "error": "Token inválido."}, 403)

    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    text = str(body.get("text") or "").strip()
    chat_id = str(body.get("chat_id") or "").strip()
    user_id = str(body.get("user_id") or "").strip() or chat_id

    if not text or not chat_id:
        return _json_response({"ok": False, "error": "Faltan text/chat_id."}, 400)

    # Guard: solo Ainz
    owner_id = _owner_chat_id()
    if owner_id and chat_id != owner_id:
        return _json_response({"ok": True, "reply": "", "ignore": True})

    # Registrar prioridad de canal
    _touch_priority()

    # Feedback implícito: analizar si este mensaje es corrección sobre el anterior
    try:
        from src.core.implicit_feedback import (
            analyze_followup_and_record as _analyze_followup,
        )

        _analyze_followup(_project_root(), user_id, text)
    except Exception:
        pass

    # Working memory: detectar "recuerda que X" y añadir al contexto activo
    try:
        from src.core.memory.working_memory import WorkingMemory, get_working_memory

        _wm = get_working_memory("telegram")
        _extracted = WorkingMemory.extract_from_message(text)
        if _extracted:
            import hashlib as _hs

            _wm.add(
                _hs.md5(_extracted.encode()).hexdigest()[:8], _extracted, importance=1.5
            )
    except Exception:
        pass

    # Session summarizer: registrar actividad + detectar consultas de resumen
    try:
        from src.core.session_summarizer import get_session_summarizer

        _ss = get_session_summarizer(_project_root())
        _ss.record_activity("telegram")
        _summary_answer = _ss.answer_summary_query(text)
        if _summary_answer is not None:
            return _json_response(
                {"ok": True, "reply": _summary_answer, "requires_confirmation": False}
            )
    except Exception:
        pass

    # Normalizar response
    def _normalize(text: str) -> str:
        try:
            from src.core.response_normalizer import normalize_response_for_discord

            return normalize_response_for_discord(text) or text
        except Exception:
            return text

    # Obtener orchestrator
    try:
        orchestrator = get_orchestrator()
    except Exception as e:
        return _json_response({"ok": False, "reply": f"Error interno: {e}"}, 500)

    # Construir system prompt (con perfil del usuario)
    try:
        system_prompt = _build_system_prompt(user_id)
    except Exception:
        system_prompt = TELEGRAM_OWNER_INSTRUCTION

    # Inyectar working memory en system prompt
    try:
        from src.core.memory.working_memory import get_working_memory

        _wm_block = get_working_memory("telegram").format_for_prompt()
        if _wm_block:
            system_prompt = system_prompt + "\n\n" + _wm_block
    except Exception:
        pass

    # Inyectar resúmenes de sesión relevantes en system prompt
    try:
        from src.core.session_summarizer import get_session_summarizer

        _ss_block = get_session_summarizer(_project_root()).format_for_context(
            get_session_summarizer(_project_root()).search_summaries(text, k=2)
        )
        if _ss_block:
            system_prompt = system_prompt + "\n\n" + _ss_block
    except Exception:
        pass

    # Inyectar historial conversacional reciente
    _hist_block = _format_history(chat_id, limit=10)
    if _hist_block:
        system_prompt = system_prompt + f"\n\n[Historial reciente]\n{_hist_block}"

    # Registrar mensaje del owner en historial
    _append_history(chat_id, "user", text)

    # Auto-delegación: detectar URLs y decidir si investigar automáticamente
    try:
        from src.core.auto_delegate import get_auto_delegate_detector

        _delegation = get_auto_delegate_detector(_project_root()).detect(
            text, role="owner"
        )
        if _delegation:
            if _delegation["action"] == "ask_user":
                _ask_reply = _delegation["message"]
                _append_history(chat_id, "assistant", _ask_reply)
                return _json_response(
                    {"ok": True, "reply": _ask_reply, "requires_confirmation": False}
                )
            elif _delegation["action"] == "auto_investigate":
                text = _delegation["investigation_message"]
    except Exception:
        pass

    # Planificar
    try:
        plan_result = orchestrator.planner.plan(text, role="owner")
        steps = getattr(plan_result, "steps", plan_result) or []
        logger.info(
            f"[DEBUG] Telegram chat: text='{text[:50]}...' steps={[s.tool_name for s in steps]}, is_pc={_is_pc_plan(steps)}"
        )
    except Exception as e:
        logger.exception("[DEBUG] Telegram chat: Error en planner: %s", e)
        steps = []

    # ═══ PC Agent Integration: Detectar operaciones PC ═══
    if steps and _is_pc_plan(steps):
        logger.info("PC Plan detectado para chat %s", chat_id)
        pc_result = await _handle_pc_batch(steps, text, chat_id, orchestrator)
        if pc_result.get("pc_batch"):
            # Respuesta con batch pendiente (preview + confirmación)
            _append_history(chat_id, "assistant", pc_result.get("reply", ""))
            return _json_response(pc_result)
        else:
            # Auto-ejecutado (pc_list solo) o error
            _append_history(chat_id, "assistant", pc_result.get("reply", ""))
            return _json_response(
                {
                    "ok": pc_result.get("ok", True),
                    "reply": pc_result.get("reply", ""),
                    "requires_confirmation": False,
                }
            )

    if steps:
        # Confirmar si: herramientas peligrosas de PC ó baja confianza con tools peligrosas
        _should_confirm = _plan_needs_confirmation(steps)
        if not _should_confirm:
            try:
                from src.core.json_safe import safe_load

                meta_cfg = safe_load(
                    _project_root() / "Config" / "metacognition.json", default={}
                )
                if bool(meta_cfg.get("enabled", True)):
                    dangerous_tools = set(meta_cfg.get("dangerous_tools", []))
                    meta_threshold = float(meta_cfg.get("confidence_threshold", 0.60))
                    confidence = float(getattr(plan_result, "confidence", 1.0))
                    has_dangerous = any(
                        getattr(s, "tool_name", "") in dangerous_tools for s in steps
                    )
                    if has_dangerous and confidence < meta_threshold:
                        _should_confirm = True
            except Exception:
                pass

        if _should_confirm:
            _cleanup_pending()
            token = uuid.uuid4().hex
            preview = _generate_plan_preview(steps, text)
            _tg_pending[token] = _TgPending(
                token=token,
                message=text,
                steps=[{"tool_name": s.tool_name, "params": s.params} for s in steps],
                system_prompt=system_prompt,
            )
            return _json_response(
                {
                    "ok": True,
                    "reply": f"{preview}\n\nToken: `{token[:16]}`",
                    "requires_confirmation": True,
                    "confirmation_token": token,
                }
            )

        # Ejecutar plan
        try:
            # Crear request_id para streaming de progreso (WebSocket /ws/progress)
            _request_id: str = ""
            _progress_cb = None
            _pm = None
            try:
                from src.core.progress_manager import (
                    ProgressEvent,
                    get_progress_manager,
                )

                _pm = get_progress_manager()
                _request_id = _pm.create_request()
                _total = len(steps)

                def _progress_cb(step_idx: int, sid: str, label: str) -> None:
                    pct = (step_idx + 1) / max(_total, 1)
                    _pm.publish(
                        ProgressEvent(
                            request_id=_request_id,
                            step=sid or label,
                            status="running",
                            message=label,
                            pct=min(pct, 0.95),
                        )
                    )

            except Exception:
                pass

            response_text = await asyncio.to_thread(
                orchestrator.execute_steps,
                steps,
                context=system_prompt,
                user_message=text,
                channel="telegram",
                progress_callback=_progress_cb,
            )

            # Señal de finalización para WS
            if _request_id:
                try:
                    _pm.publish(
                        ProgressEvent(
                            request_id=_request_id, step="done", status="done", pct=1.0
                        )
                    )
                except Exception:
                    pass
            response_text = _normalize(
                (response_text or "").strip() or "(Sin respuesta)"
            )
            # Post-hook: registrar interacción para feedback implícito
            try:
                from src.core.implicit_feedback import register_interaction as _reg_i

                _reg_i(
                    _project_root(),
                    user_id,
                    text,
                    getattr(orchestrator, "_last_executed_tool", None)
                    or "generate_reply",
                    response_text,
                    "telegram",
                )
            except Exception:
                pass
            _append_history(chat_id, "assistant", response_text)
            resp_payload = {
                "ok": True,
                "reply": response_text,
                "requires_confirmation": False,
            }
            if _request_id:
                resp_payload["request_id"] = _request_id
            return _json_response(resp_payload)
        except Exception as e:
            if _request_id and _pm:
                try:
                    from src.core.progress_manager import ProgressEvent

                    _pm.publish(
                        ProgressEvent(
                            request_id=_request_id,
                            step="error",
                            status="error",
                            pct=1.0,
                            message=str(e),
                        )
                    )
                except Exception:
                    pass
            return _json_response(
                {"ok": False, "reply": f"Error al ejecutar: {e}"}, 500
            )

    # Sin plan — generar respuesta directa
    try:
        response_text = await asyncio.to_thread(
            orchestrator.execute_plan,
            text,
            context=system_prompt,
            user_id=user_id,
            skip_cache=True,
            channel="telegram",
        )
        response_text = _normalize((response_text or "").strip() or "(Sin respuesta)")
        # Post-hook: registrar interacción para feedback implícito
        try:
            from src.core.implicit_feedback import register_interaction as _reg_i

            _reg_i(
                _project_root(),
                user_id,
                text,
                getattr(orchestrator, "_last_executed_tool", None) or "generate_reply",
                response_text,
                "telegram",
            )
        except Exception:
            pass
        try:
            from src.core.memory.working_memory import get_working_memory

            get_working_memory("telegram").tick()
        except Exception:
            pass
        _append_history(chat_id, "assistant", response_text)
        return _json_response(
            {"ok": True, "reply": response_text, "requires_confirmation": False}
        )
    except Exception as e:
        return _json_response({"ok": False, "reply": f"Error: {e}"}, 500)


# ─── Endpoint de confirmación ─────────────────────────────────────────────────


@router.post("/confirm")
async def telegram_confirm(request: Request) -> Response:
    if not _verify(request):
        return _json_response({"ok": False, "error": "Token inválido."}, 403)

    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    token = str(body.get("token") or "").strip()
    approved = bool(body.get("approved", False))

    if not token:
        return _json_response({"ok": False, "error": "Falta token."}, 400)

    pending = _tg_pending.get(token)
    if not pending:
        return _json_response(
            {"ok": False, "error": "Token no encontrado o expirado."}, 404
        )

    del _tg_pending[token]

    if not approved:
        # Señal de feedback: denegación
        try:
            from src.core.implicit_feedback import (
                record_confirmation_signal as _rec_conf,
            )

            primary_tool = (
                pending.steps[0].get("tool_name", "unknown")
                if pending.steps
                else "unknown"
            )
            _rec_conf(
                _project_root(),
                pending.message,
                str(primary_tool),
                approved=False,
                transport="telegram",
            )
        except Exception:
            pass
        plan_summary = (
            " → ".join(s.get("tool_name", "?") for s in pending.steps)
            if pending.steps
            else pending.message[:80]
        )
        await _record_confirmation_to_muninn(
            "deny", plan_summary, pending.message, "telegram"
        )
        try:
            from src.core.muninn_edges import get_edge_manager

            _tool_names = (
                [s.get("tool_name", "") for s in pending.steps] if pending.steps else []
            )
            get_edge_manager(_project_root()).record_confirmation_edge(
                "deny", plan_summary, _tool_names
            )
        except Exception:
            pass
        return _json_response({"ok": True, "result": "❌ Operación cancelada."})

    # Reconstruir steps y ejecutar
    try:
        from src.core.planner import Step

        steps = [
            Step(tool_name=s["tool_name"], params=s.get("params", {}))
            for s in pending.steps
        ]
        orchestrator = get_orchestrator()
        result = await asyncio.to_thread(
            orchestrator.execute_steps,
            steps,
            context=pending.system_prompt,
            user_message=pending.message,
            channel="telegram",
        )

        def _normalize(t: str) -> str:
            try:
                from src.core.response_normalizer import normalize_response_for_discord

                return normalize_response_for_discord(t) or t
            except Exception:
                return t

        result = _normalize((result or "").strip() or "(Sin respuesta)")
        # Señal de feedback: aprobación exitosa
        try:
            from src.core.implicit_feedback import (
                record_confirmation_signal as _rec_conf,
            )

            primary_tool = (
                pending.steps[0].get("tool_name", "unknown")
                if pending.steps
                else "unknown"
            )
            _rec_conf(
                _project_root(),
                pending.message,
                str(primary_tool),
                approved=True,
                transport="telegram",
            )
        except Exception:
            pass
        plan_summary = (
            " → ".join(s.get("tool_name", "?") for s in pending.steps)
            if pending.steps
            else pending.message[:80]
        )
        await _record_confirmation_to_muninn(
            "authorize", plan_summary, pending.message, "telegram"
        )
        try:
            from src.core.muninn_edges import get_edge_manager

            _tool_names = (
                [s.get("tool_name", "") for s in pending.steps] if pending.steps else []
            )
            get_edge_manager(_project_root()).record_confirmation_edge(
                "authorize", plan_summary, _tool_names
            )
        except Exception:
            pass
        return _json_response({"ok": True, "result": result})
    except Exception as e:
        return _json_response({"ok": False, "result": f"Error al ejecutar: {e}"}, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# PC Agent Integration — Parte de Misión PC Agent end-to-end
# ═══════════════════════════════════════════════════════════════════════════════

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lilith.telegram.pc")


@dataclass
class _PCPendingBatch:
    """Batch de operaciones PC pendiente de confirmación."""

    token: str
    steps: List[Dict[str, Any]]
    chat_id: str
    preview: str
    risk: str
    created_at: float = field(default_factory=time.time)


# Almacenamiento de batches pendientes
_pc_pending_batches: Dict[str, _PCPendingBatch] = {}
_PC_BATCH_TTL = 120  # 2 minutos para confirmar

# Rate limiting para operaciones PC (30 por hora)
_PC_RATE_LIMIT = 30  # ops/hora
_PC_RATE_WINDOW = 3600  # 1 hora en segundos
_pc_op_log: List[float] = []  # timestamps de operaciones ejecutadas


def _check_pc_rate_limit() -> tuple[bool, int]:
    """
    Verifica si se puede ejecutar una operación PC.
    Retorna: (allowed: bool, remaining: int)
    """
    global _pc_op_log
    now = time.time()
    # Limpiar entradas antiguas (> 1 hora)
    _pc_op_log = [ts for ts in _pc_op_log if now - ts < _PC_RATE_WINDOW]

    if len(_pc_op_log) >= _PC_RATE_LIMIT:
        return False, 0
    return True, _PC_RATE_LIMIT - len(_pc_op_log)


def _record_pc_operation():
    """Registra una operación PC ejecutada."""
    _pc_op_log.append(time.time())


def _is_pc_plan(steps: List[Any]) -> bool:
    """Detecta si un plan contiene operaciones PC."""
    if not steps:
        return False
    for step in steps:
        tool = getattr(step, "tool_name", "")
        if tool and (tool.startswith("pc_") or tool == "pc_operation_batch"):
            return True
    return False


def _cleanup_pc_batches():
    """Limpia batches expirados."""
    now = time.time()
    expired = [
        token
        for token, batch in _pc_pending_batches.items()
        if now - batch.created_at > _PC_BATCH_TTL
    ]
    for token in expired:
        del _pc_pending_batches[token]
        logger.debug("PC Batch %s expirado y eliminado", token)


def _sanitize_pc_response(tool: str, response: str) -> str:
    """Convierte output markdown de pc_list/etc a texto limpio para Telegram."""
    if not response:
        return "(vacío)"

    # Quitar bold markers de Discord (**texto**)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", response)

    if tool == "pc_list" or tool.replace("pc_", "") == "list":
        lines = text.strip().splitlines()
        if not lines:
            return "(vacío)"

        header = lines[0].strip()  # la ruta
        items = lines[1:]  # archivos/carpetas

        # Filtrar líneas vacías y limpiar
        items = [line.strip() for line in items if line.strip()]

        # Truncar si hay muchos ítems (Telegram: 4096 chars por mensaje)
        MAX_ITEMS = 30
        truncated = len(items) > MAX_ITEMS
        shown = items[:MAX_ITEMS]

        body = "\n".join(f"  {item}" for item in shown)
        suffix = f"\n  …y {len(items) - MAX_ITEMS} más" if truncated else ""

        return f"`{header}`\n{body}{suffix}"

    # Para otras tools (mkdir, move, etc.) solo limpiar bold
    return text.strip()


def _format_pc_results(results: List[Dict[str, Any]]) -> str:
    """Formatea resultados de operaciones PC para Telegram."""
    if not results:
        return "⚠️ No hay resultados para mostrar."

    total = len(results)
    success = sum(1 for r in results if r.get("success"))

    if success == total:
        header = f"✅ Completado ({success}/{total}):"
    elif success == 0:
        header = f"❌ Falló todo ({total} operaciones):"
    else:
        header = f"⚠️ Parcial ({success}/{total} exitosas):"

    lines = [header, ""]

    for r in results:
        emoji = "✅" if r.get("success") else "❌"
        tool = r.get("tool", "unknown")
        tool_clean = tool.replace("pc_", "")

        if r.get("success"):
            output = str(r.get("output", ""))
            clean = _sanitize_pc_response(tool, output)
            lines.append(f"{emoji} `{tool_clean}`\n{clean}")
        else:
            error = str(r.get("error", "Error desconocido"))
            # Limpiar bold markers del error también
            error_clean = re.sub(r"\*\*(.+?)\*\*", r"\1", error)
            lines.append(f"{emoji} `{tool_clean}`\n  ❌ {error_clean[:200]}")

    return "\n\n".join(lines)


async def _handle_pc_batch(
    steps: List[Any], text: str, chat_id: str, orchestrator: Any
) -> Dict[str, Any]:
    """
    Maneja un batch de operaciones PC.
    F.17: Integración con sistema de macros.
    - Detecta macros desde lenguaje natural
    - 1 confirmación para todo el batch
    - Si es solo pc_list: ejecuta directo
    - Si no: genera preview y pide confirmación
    """
    logger.info(
        f"[DEBUG] _handle_pc_batch START: text='{text[:50]}' steps={[getattr(s, 'tool_name', str(s)) for s in steps]}"
    )
    from src.core.pc_batch_builder import get_batch_builder
    from src.core.pc_macro_engine import get_macro_engine

    builder = get_batch_builder()

    # Limpiar batches expirados
    _cleanup_pc_batches()

    # Convertir steps a formato interno si vienen del planner
    processed_steps = []
    for step in steps:
        if hasattr(step, "tool_name"):
            processed_steps.append(
                {"tool": step.tool_name, "params": getattr(step, "params", {})}
            )
        else:
            processed_steps.append(step)

    # F.17: Intentar detectar macro desde lenguaje natural
    macro_engine = get_macro_engine(_project_root())
    macro_detection = macro_engine.detect_macro(text)

    if macro_detection:
        macro_name, confidence = macro_detection
        logger.info(
            "[F.17] Macro detectada: %s (confianza: %.2f) para chat %s",
            macro_name,
            confidence,
            chat_id,
        )

        if confidence >= 0.5:  # Umbral de confianza
            macro = macro_engine.get_macro(macro_name)
            if macro:
                # Extraer parámetros del texto
                params = macro_engine.extract_params(text, macro_name)

                # Validar parámetros
                is_valid, error_msg = macro_engine.validate_params(macro_name, params)
                if is_valid:
                    # Construir steps de la macro
                    macro_steps = macro_engine.build_batch_steps(macro_name, params)
                    if macro_steps:
                        processed_steps = [
                            {
                                "tool": s["op"],
                                "params": {k: v for k, v in s.items() if k != "op"},
                            }
                            for s in macro_steps
                        ]
                        logger.info(
                            "[F.17] Macro '%s' aplicada con %d steps",
                            macro_name,
                            len(processed_steps),
                        )

                        # Guardar estado de macro en sesión
                        try:
                            sm = _get_session_manager()
                            sm.set_macro_state(
                                chat_id,
                                chat_id,
                                macro_name,
                                {"params": params, "steps_count": len(processed_steps)},
                            )
                        except Exception:
                            pass
                else:
                    logger.warning(
                        "[F.17] Macro '%s' params inválidos: %s", macro_name, error_msg
                    )

    # Si es solo lectura (pc_list), ejecutar directo (con rate limiting)
    if all(s.get("tool") == "pc_list" for s in processed_steps):
        logger.info(
            "[DEBUG] PC Auto-ejecutando pc_list para chat %s (processed_steps=%s)",
            chat_id,
            processed_steps,
        )

        # Verificar rate limit (pc_list cuenta como operación PC)
        allowed, remaining = _check_pc_rate_limit()
        if not allowed:
            return {
                "ok": False,
                "reply": f"⏳ Rate limit alcanzado. Máximo {_PC_RATE_LIMIT} operaciones/hora. Espera un poco.",
                "requires_confirmation": False,
            }

        results = await _execute_pc_steps(processed_steps, orchestrator)
        _record_pc_operation()
        return {
            "ok": True,
            "reply": _format_pc_results(results)
            + f"\n\n⏱ `{remaining - 1}/h restantes`",
            "requires_confirmation": False,
        }

    # Generar preview y token
    from src.core.planner import Step

    step_objects = [
        Step(tool_name=s["tool"], params=s["params"]) for s in processed_steps
    ]
    preview = builder.build_preview(step_objects)
    risk = builder.compute_risk(step_objects)
    token = builder.generate_batch_token(step_objects, chat_id)

    # Guardar batch pendiente
    _pc_pending_batches[token] = _PCPendingBatch(
        token=token, steps=processed_steps, chat_id=chat_id, preview=preview, risk=risk
    )

    logger.info(
        "PC Batch %s creado para chat %s (%d steps, risk=%s)",
        token,
        chat_id,
        len(processed_steps),
        risk,
    )

    # Construir respuesta con botones inline (el bot de Telegram maneja los botones)
    warning = ""
    if risk == "high":
        warning = "\n\n⚠️ **Esta operación incluye acciones destructivas.**"
    elif risk == "medium":
        warning = "\n\n⚡ Esta operación modificará archivos."

    return {
        "ok": True,
        "reply": preview + warning + f"\n\nToken: `{token[:8]}...`",
        "requires_confirmation": True,
        "confirmation_token": token,
        "confirmation_type": "pc",  # Tipo especial para PC operations
        "risk_level": risk,
        "pc_batch": True,
        "inline_keyboard": [
            [{"text": "✅ Ejecutar", "callback_data": f"pc_confirm:{token}"}],
            [{"text": "❌ Cancelar", "callback_data": f"pc_cancel:{token}"}],
        ],
    }


async def _execute_pc_steps(
    steps: List[Dict[str, Any]], orchestrator: Any
) -> List[Dict[str, Any]]:
    """Ejecuta una lista de steps PC."""
    logger.info(f"[DEBUG] _execute_pc_steps START: steps={steps}")
    results = []

    for i, step in enumerate(steps):
        tool_name = step.get("tool")
        params = step.get("params", {})

        try:
            # Obtener tool del registry (método correcto es get(), no get_tool())
            tool = orchestrator.registry.get(tool_name)
            if not tool:
                logger.error(f"[DEBUG] Tool {tool_name} no encontrado en registry")
                results.append(
                    {
                        "step": i + 1,
                        "tool": tool_name,
                        "success": False,
                        "output": None,
                        "error": f"Tool {tool_name} no encontrado",
                    }
                )
                continue

            # Ejecutar
            import asyncio

            logger.info(
                f"[DEBUG] Ejecutando tool.execute: {tool_name} con params={params}"
            )
            result = await asyncio.to_thread(tool.execute, params)
            logger.info(
                f"[DEBUG] Tool {tool_name} result: type={type(result)}, value={str(result)[:200]}"
            )

            # Manejar diferentes formatos de resultado
            if isinstance(result, dict):
                # ToolResult como dict
                success = not result.get("error", False)
                output = result.get("response", "")
                error = result.get("response", "") if not success else None
            elif hasattr(result, "success"):
                # Objeto con atributos success/output/error
                success = result.success
                output = result.output if hasattr(result, "output") else str(result)
                error = result.error if hasattr(result, "error") else None
            else:
                # String u otro tipo
                success = True
                output = str(result)
                error = None

            results.append(
                {
                    "step": i + 1,
                    "tool": tool_name,
                    "success": success,
                    "output": output,
                    "error": error,
                }
            )

            # Si falla un step crítico, abortar
            if not results[-1]["success"] and tool_name in ("pc_delete", "pc_move"):
                # Completar el resto como abortado
                for j in range(i + 1, len(steps)):
                    results.append(
                        {
                            "step": j + 1,
                            "tool": steps[j].get("tool", "unknown"),
                            "success": False,
                            "output": None,
                            "error": "Abortado: paso anterior falló",
                        }
                    )
                break

        except Exception as e:
            logger.exception("Error ejecutando %s", tool_name)
            results.append(
                {
                    "step": i + 1,
                    "tool": tool_name,
                    "success": False,
                    "output": None,
                    "error": str(e),
                }
            )

    return results


# ─── Endpoints para confirmar/cancelar PC batches ─────────────────────────────


class PCConfirmRequest(BaseModel):
    token: str


class PCCancelRequest(BaseModel):
    token: str


@router.post("/pc/confirm")
async def telegram_pc_confirm(request: Request) -> Response:
    """Confirma y ejecuta un batch de operaciones PC pendiente."""
    if not _verify(request):
        return _json_response({"ok": False, "error": "Token inválido."}, 403)

    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    token = str(body.get("token") or "").strip()
    if not token:
        return _json_response({"ok": False, "error": "Falta token."}, 400)

    # Buscar batch
    batch = _pc_pending_batches.get(token)
    if not batch:
        return _json_response({"ok": False, "error": "Token inválido o expirado."}, 404)

    # Verificar TTL
    if time.time() - batch.created_at > _PC_BATCH_TTL:
        del _pc_pending_batches[token]
        return _json_response(
            {"ok": False, "error": "Confirmación expirada (>2 min)."}, 410
        )

    # Rate limiting: máximo 30 ops/hora
    allowed, remaining = _check_pc_rate_limit()
    if not allowed:
        return _json_response(
            {
                "ok": False,
                "error": f"⏳ Rate limit alcanzado. Máximo {_PC_RATE_LIMIT} operaciones/hora. Espera un poco.",
            },
            429,
        )

    # Ejecutar
    try:
        orchestrator = get_orchestrator()
        results = await _execute_pc_steps(batch.steps, orchestrator)

        # Marcar como ejecutado
        del _pc_pending_batches[token]

        # Registrar operación para rate limiting
        _record_pc_operation()

        # Registrar en MuninnDB
        plan_summary = " → ".join(s.get("tool", "?") for s in batch.steps)
        await _record_confirmation_to_muninn(
            "authorize", plan_summary, f"PC Batch: {plan_summary}", "telegram"
        )

        # Calcular remaining después de esta operación
        _, remaining = _check_pc_rate_limit()

        return _json_response(
            {
                "ok": True,
                "result": _format_pc_results(results)
                + f"\n\n⏱ `{remaining}/h restantes`",
                "success": all(r.get("success") for r in results),
            }
        )

    except Exception as e:
        logger.exception("Error ejecutando PC batch %s", token)
        return _json_response({"ok": False, "error": f"Error al ejecutar: {e}"}, 500)


@router.post("/pc/cancel")
async def telegram_pc_cancel(request: Request) -> Response:
    """Cancela un batch de operaciones PC pendiente."""
    if not _verify(request):
        return _json_response({"ok": False, "error": "Token inválido."}, 403)

    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    token = str(body.get("token") or "").strip()
    if not token:
        return _json_response({"ok": False, "error": "Falta token."}, 400)

    batch = _pc_pending_batches.pop(token, None)
    if not batch:
        return _json_response(
            {"ok": False, "error": "Token inválido o ya procesado."}, 404
        )

    # Registrar cancelación
    plan_summary = " → ".join(s.get("tool", "?") for s in batch.steps)
    await _record_confirmation_to_muninn(
        "deny", plan_summary, f"PC Batch cancelado: {plan_summary}", "telegram"
    )

    logger.info("PC Batch %s cancelado por usuario", token)

    return _json_response(
        {"ok": True, "result": "❌ Operación cancelada.", "cancelled": True}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Progress Streaming v5.1 — Ejecución PC con feedback visual en tiempo real
# ═══════════════════════════════════════════════════════════════════════════════


class ExecuteWithProgressRequest(BaseModel):
    """Request para ejecutar operaciones PC con progress streaming."""

    steps: List[Dict[str, Any]]
    chat_id: str
    message_id: Optional[int] = None  # Si se proporciona, edita este mensaje
    user_id: Optional[str] = None


async def _execute_pc_steps_with_progress(
    steps: List[Dict[str, Any]],
    orchestrator: Any,
    streamer: Any,  # TelegramProgressStreamer
) -> List[Dict[str, Any]]:
    """
    Ejecuta steps PC con progress streaming.
    Envía actualizaciones en tiempo real al streamer.
    """
    import asyncio

    results = []
    total_steps = len(steps)

    for i, step in enumerate(steps):
        tool_name = step.get("tool")
        params = step.get("params", {})
        step_id = f"step_{i+1}"

        # Notificar inicio del paso
        step_id = f"step_{i+1}"
        await streamer.update_progress(
            step_index=i + 1,
            total_steps=total_steps,
            step_id=step_id,
            status="working",
            message=f"Ejecutando {tool_name}...",
        )

        try:
            # Obtener tool del registry
            tool = orchestrator.registry.get(tool_name)
            if not tool:
                logger.error(f"[Progress] Tool {tool_name} no encontrado")
                results.append(
                    {
                        "step": i + 1,
                        "tool": tool_name,
                        "success": False,
                        "output": None,
                        "error": f"Tool {tool_name} no encontrado",
                    }
                )
                await streamer.update_progress(
                    step_index=i + 1,
                    total_steps=total_steps,
                    step_id=step_id,
                    status="failed",
                    message=f"Tool no encontrado",
                )
                continue

            # Ejecutar
            result = await asyncio.to_thread(tool.execute, params)

            # Manejar diferentes formatos de resultado
            if isinstance(result, dict):
                success = not result.get("error", False)
                output = result.get("response", "")
                error = result.get("response", "") if not success else None
            elif hasattr(result, "success"):
                success = result.success
                output = result.output if hasattr(result, "output") else str(result)
                error = result.error if hasattr(result, "error") else None
            else:
                success = True
                output = str(result)
                error = None

            results.append(
                {
                    "step": i + 1,
                    "tool": tool_name,
                    "success": success,
                    "output": output,
                    "error": error,
                }
            )

            # Notificar éxito o fallo
            status = "completed" if success else "failed"
            message = (
                f"{tool_name} completado"
                if success
                else f"{tool_name} falló: {str(error)[:50]}"
            )
            await streamer.update_progress(
                step_index=i + 1,
                total_steps=total_steps,
                step_id=step_id,
                status=status,
                message=message,
            )

            # Si falla un step crítico, abortar resto
            if not success and tool_name in ("pc_delete", "pc_move"):
                for j in range(i + 1, len(steps)):
                    results.append(
                        {
                            "step": j + 1,
                            "tool": steps[j].get("tool", "unknown"),
                            "success": False,
                            "output": None,
                            "error": "Abortado: paso anterior falló",
                        }
                    )
                    await streamer.update_progress(
                        step_index=j + 1,
                        total_steps=total_steps,
                        step_id=f"step_{j+1}",
                        status="failed",
                        message="Abortado",
                    )
                break

        except Exception as e:
            logger.exception("Error ejecutando %s", tool_name)
            results.append(
                {
                    "step": i + 1,
                    "tool": tool_name,
                    "success": False,
                    "output": None,
                    "error": str(e),
                }
            )
            await streamer.update_progress(
                step_index=i + 1,
                total_steps=total_steps,
                step_id=step_id,
                status="failed",
                message=f"Error: {str(e)[:50]}",
            )

    return results


@router.post("/execute_with_progress")
async def telegram_execute_with_progress(request: Request) -> Response:
    """
    Ejecuta operaciones PC con progress streaming visual en Telegram.
    v5.1: Feedback en tiempo real con progress bars y emoji status.
    """
    if not _verify(request):
        return _json_response({"ok": False, "error": "Token inválido."}, 403)

    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass

    # Parsear request
    try:
        req = ExecuteWithProgressRequest(**body)
    except Exception as e:
        return _json_response({"ok": False, "error": f"Request inválido: {e}"}, 400)

    if not req.steps:
        return _json_response(
            {"ok": False, "error": "No hay steps para ejecutar."}, 400
        )

    chat_id = req.chat_id
    user_id = req.user_id or chat_id

    # Guard: solo Ainz
    owner_id = _owner_chat_id()
    if owner_id and chat_id != owner_id:
        return _json_response({"ok": True, "result": "", "ignore": True})

    # Verificar rate limit
    allowed, remaining = _check_pc_rate_limit()
    if not allowed:
        return _json_response(
            {
                "ok": False,
                "error": f"⏳ Rate limit alcanzado. Máximo {_PC_RATE_LIMIT} operaciones/hora.",
            },
            429,
        )

    # Obtener token del bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        return _json_response(
            {"ok": False, "error": "TELEGRAM_BOT_TOKEN no configurado."}, 500
        )

    # Obtener o crear message_id
    message_id = req.message_id
    if not message_id:
        # Enviar mensaje inicial
        try:
            import httpx

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": "⏳ Iniciando operaciones PC...",
                        "parse_mode": "Markdown",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        message_id = data["result"]["message_id"]
        except Exception as e:
            logger.warning("[Progress] Error enviando mensaje inicial: %s", e)
            return _json_response(
                {"ok": False, "error": f"Error enviando mensaje inicial: {e}"}, 500
            )

    if not message_id:
        return _json_response(
            {"ok": False, "error": "No se pudo obtener message_id"}, 500
        )

    # Crear progress streamer
    try:
        from src.core.telegram_progress_streamer import (
            ProgressConfig,
            TelegramProgressStreamer,
        )

        config = ProgressConfig(
            rate_limit_seconds=1.0,
            enable_progress_bar=True,
            enable_time_estimate=True,
            emoji_set="default",
        )

        streamer = TelegramProgressStreamer(
            bot_token=bot_token,
            chat_id=int(chat_id),
            message_id=message_id,
            config=config,
        )
    except Exception as e:
        logger.exception("[Progress] Error creando streamer")
        return _json_response(
            {"ok": False, "error": f"Error creando streamer: {e}"}, 500
        )

    # Obtener orchestrator
    try:
        orchestrator = get_orchestrator()
    except Exception as e:
        return _json_response({"ok": False, "error": f"Error interno: {e}"}, 500)

    # Ejecutar con progress streaming
    try:
        results = await _execute_pc_steps_with_progress(
            steps=req.steps,
            orchestrator=orchestrator,
            streamer=streamer,
        )

        # Finalizar streamer
        all_success = all(r.get("success") for r in results)
        await streamer.finalize(
            success=all_success,
            final_message=None,  # Deja que el streamer genere el mensaje final
        )

        # Registrar operación
        _record_pc_operation()

        # Devolver resultados
        return _json_response(
            {
                "ok": True,
                "result": _format_pc_results(results),
                "success": all_success,
                "message_id": message_id,
                "stats": streamer.get_stats(),
            }
        )

    except Exception as e:
        logger.exception("[Progress] Error ejecutando con streaming")
        await streamer.send_error(str(e))
        return _json_response(
            {"ok": False, "error": f"Error durante ejecución: {str(e)}"}, 500
        )
