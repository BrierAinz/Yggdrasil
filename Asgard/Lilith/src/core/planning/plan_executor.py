"""
Lilith 3.5 B.3 — PlanExecutor: ejecuta una lista de pasos en orden o por oleadas (DAG).
4.0: scratchpad (step_results), context_from_steps, ejecución en oleadas con ThreadPoolExecutor.
Solo el hilo principal escribe en step_results (recolección desde Futures); barrera estricta o timeout por oleada.
"""
import contextvars
import json
import logging
import random
import uuid
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from concurrent.futures import wait
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .agent_caller import AgentCaller
from .execution_context import set_current_agent
from .planner import Step
from .tools_v3.protocol import ToolResult
from .tools_v3.registry import ToolRegistryV3


def _try_parse_permission_denied(result: Any) -> Optional[Dict[str, Any]]:
    """
    Detecta el payload JSON de SecurityGuard (permission_denied) dentro de un ToolResult.
    Los tools de disco devuelven {"response": "<json>", "error": True}.
    """
    if not isinstance(result, dict):
        return None
    if not result.get("error"):
        return None
    raw = result.get("response")
    if not isinstance(raw, str) or not raw.strip().startswith("{"):
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("error") == "permission_denied":
            return data
    except Exception:
        return None
    return None


def _permission_request_from_denied(denied: Dict[str, Any]) -> Dict[str, Any]:
    agent = denied.get("agent") or "nobody"
    op = denied.get("op") or ""
    path = denied.get("path") or ""
    reason = denied.get("reason") or ""
    hint = denied.get("hint") or ""
    msg = denied.get("message") or "Permiso denegado."
    human = f"{msg} ({reason})."
    suggested = (
        hint
        or "Owner: ajusta agent_scopes.json o mueve el archivo a una zona permitida."
    )
    return {
        "type": "permission_request",
        "request_id": uuid.uuid4().hex,
        "agent": agent,
        "operation": op,
        "target_path": path,
        "security_reason": reason,
        "human_message": human,
        "suggested_action": suggested,
    }


logger = logging.getLogger("PlanExecutor")

_SEPARATOR = "\n\n---\n\n"
_PLACEHOLDER_UNAVAILABLE = "(Fuente no disponible)"
_PLACEHOLDER_TIMEOUT = "(Paso cancelado por timeout de oleada)"


def _audit_step_executed(sid: str, tool_name: str, result_preview: str) -> None:
    """Misión H: registra step_executed en el auditor. No propaga excepciones."""
    try:
        from .auditor.decision_auditor import append_decision

        append_decision(
            decision_type="step_executed",
            actor="executor",
            payload={
                "step_id": sid,
                "tool_name": tool_name,
                "result_preview": (result_preview or "")[:500],
            },
            reason=f"tool={tool_name}",
        )
    except Exception:
        pass


def _scratchpad_config(base_path: Optional[Path] = None) -> Dict[str, Any]:
    """Lee Config/planner.json: scratchpad_*, lilith_cite_sources_when_mining (4.0)."""
    out = {
        "max_context_chars": 10000,
        "min_chars_per_source": 800,
        "truncation": "tail_per_step",
        "prefer": "tail",
        "lilith_cite_sources_when_mining": False,
        "dag_max_workers": 5,
        "dag_use_parallel": True,
        "dag_wave_timeout_seconds": 0,
        "delegate_max_context_chars": 0,
        "dag_partial_failure_tolerant": False,
        "scratchpad_use_source_tags": False,
        "max_web_steps": 0,
    }
    if not base_path or not Path(base_path).exists():
        return out
    try:
        from .json_safe import safe_load

        cfg = safe_load(Path(base_path) / "Config" / "planner.json", default={})
        if isinstance(cfg, dict):
            out["max_context_chars"] = max(
                500, int(cfg.get("scratchpad_max_context_chars") or 10000)
            )
            out["min_chars_per_source"] = max(
                100, int(cfg.get("scratchpad_min_chars_per_source") or 800)
            )
            out["truncation"] = (
                cfg.get("scratchpad_truncation") or "tail_per_step"
            ).strip() or "tail_per_step"
            p = (cfg.get("scratchpad_prefer") or "tail").strip().lower()
            out["prefer"] = p if p in ("tail", "head", "middle") else "tail"
            out["lilith_cite_sources_when_mining"] = bool(
                cfg.get("lilith_cite_sources_when_mining")
            )
            out["dag_max_workers"] = max(
                1, min(16, int(cfg.get("dag_max_workers") or 5))
            )
            out["dag_use_parallel"] = bool(cfg.get("dag_use_parallel", True))
            out["dag_wave_timeout_seconds"] = max(
                0, int(cfg.get("dag_wave_timeout_seconds") or 0)
            )
            out["delegate_max_context_chars"] = max(
                0, int(cfg.get("delegate_max_context_chars") or 0)
            )
            out["dag_partial_failure_tolerant"] = bool(
                cfg.get("dag_partial_failure_tolerant", False)
            )
            out["scratchpad_use_source_tags"] = bool(
                cfg.get("scratchpad_use_source_tags", False)
            )
            out["max_web_steps"] = max(0, int(cfg.get("max_web_steps") or 0))
    except Exception:
        pass
    return out


def _build_context_from_steps(
    step_results: Dict[str, str],
    context_from_steps: List[str],
    max_context_chars: int,
    truncation: str,
    prefer: str = "tail",
    min_chars_per_source: int = 0,
    use_source_tags: bool = False,
    step_metadata: Optional[Dict[str, Dict[str, str]]] = None,
    skip_unavailable_sources: bool = False,
) -> str:
    """
    Construye el contexto concatenando salidas de los pasos indicados.
    Si total > max_context_chars: tail_per_step proporcional (cada paso recibe cuota por longitud).
    Si min_chars_per_source > 0, cada paso recibe al menos esa cuota (fan-in: evita diluir 5+ fuentes).
    Si use_source_tags=True, envuelve cada fragmento en <source id="key" url="..." domain="...">...</source> (url/domain si step_metadata lo aporta).
    Si skip_unavailable_sources=True, se excluyen las claves cuyo contenido es _PLACEHOLDER_UNAVAILABLE (evita contaminar persistencia).
    """
    texts = []
    for key in context_from_steps:
        if key not in step_results:
            continue
        val = step_results[key].strip()
        if skip_unavailable_sources and (
            val == _PLACEHOLDER_UNAVAILABLE or val.strip().startswith("(Paso cancelado")
        ):
            continue
        if val:
            texts.append((key, val))
    if not texts:
        return ""
    meta = step_metadata or {}

    def _tag(k: str, t: str) -> str:
        if not use_source_tags or len(texts) <= 1:
            return t
        attrs = [f'id="{k}"']
        m = meta.get(k, {})
        if m.get("url"):
            attrs.append(f'url="{_xml_escape_attr(m["url"])}"')
        if m.get("domain"):
            attrs.append(f'domain="{_xml_escape_attr(m["domain"])}"')
        return f"<source {' '.join(attrs)}>{t}</source>"

    raw = _SEPARATOR.join(t[1] for t in texts)
    if len(raw) <= max_context_chars:
        if use_source_tags and len(texts) > 1:
            return "\n\n".join(_tag(k, t) for k, t in texts)
        return raw
    if truncation == "global_tail":
        return raw[-max_context_chars:]
    # tail_per_step proporcional; prefer (tail|head|middle) evita inyectar boilerplate del final
    lengths = [len(t[1]) for t in texts]
    total_len = sum(lengths)
    if total_len <= 0:
        return raw[-max_context_chars:]
    quotas = [max(1, int(max_context_chars * L / total_len)) for L in lengths]
    if min_chars_per_source > 0:
        quotas = [max(min_chars_per_source, q) for q in quotas]
        total_quota = sum(quotas)
        if total_quota > max_context_chars and total_quota > 0:
            scale = max_context_chars / total_quota
            quotas = [max(1, int(q * scale)) for q in quotas]
            remainder = max_context_chars - sum(quotas)
            if remainder > 0 and quotas:
                idx_max = max(range(len(quotas)), key=lambda i: lengths[i])
                quotas[idx_max] += remainder
    else:
        remainder = max_context_chars - sum(quotas)
        if remainder > 0 and quotas:
            idx_max = max(range(len(quotas)), key=lambda i: lengths[i])
            quotas[idx_max] += remainder
    prefer_slice = (prefer or "tail").strip().lower()
    if prefer_slice not in ("head", "middle"):
        prefer_slice = "tail"
    parts_with_key: List[Tuple[str, str]] = []
    for (key, text), quota in zip(texts, quotas):
        if len(text) <= quota:
            part = text
        elif prefer_slice == "head":
            part = text[:quota]
        elif prefer_slice == "middle":
            start = max(0, (len(text) - quota) // 2)
            part = text[start : start + quota]
        else:
            part = text[-quota:]
        parts_with_key.append((key, part))
    if use_source_tags and len(parts_with_key) > 1:
        return "\n\n".join(_tag(k, p) for k, p in parts_with_key)
    return _SEPARATOR.join(p for _, p in parts_with_key)


def _result_to_str(result: ToolResult) -> str:
    """Extrae el texto de respuesta de un ToolResult."""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict) and "response" in result:
        val = result["response"]
        return str(val).strip() if val is not None else ""
    return str(result).strip()


def _extract_source_metadata(result: ToolResult) -> Dict[str, str]:
    """Extrae url y domain de un ToolResult para etiquetas <source> (LoreExtractor, etc.)."""
    out: Dict[str, str] = {}
    if not isinstance(result, dict):
        return out
    for key in ("url", "domain"):
        if key in result and result[key]:
            val = str(result[key]).strip()
            if val:
                out[key] = val[:500]
    return out


def _xml_escape_attr(val: str) -> str:
    """Escapa caracteres para uso en atributos XML."""
    return (
        val.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _compute_waves(
    steps_with_meta: List[Tuple[str, List[str], Step]],
) -> List[List[Tuple[str, List[str], Step]]]:
    """Agrupa pasos en oleadas: cada oleada contiene pasos cuyas dependencias ya están en oleadas anteriores."""
    waves: List[List[Tuple[str, List[str], Step]]] = []
    completed: set = set()
    remaining = list(steps_with_meta)
    while remaining:
        wave = [
            (sid, deps, s)
            for (sid, deps, s) in remaining
            if all(d in completed for d in deps)
        ]
        if not wave:
            break
        waves.append(wave)
        for sid, _, _ in wave:
            completed.add(sid)
        remaining = [
            (sid, deps, s) for (sid, deps, s) in remaining if sid not in completed
        ]
    return waves


def _label_for_tool(tool_name: str) -> str:
    """Etiqueta legible para feedback progresivo (ej. Discord 'Paso N: ...')."""
    labels = {
        "lore_extractor": "Extrayendo lore",
        "delegate_web_scraper": "Extrayendo web",
        "delegate_content_cleaner": "Limpiando contenido",
        "delegate_quality_filter": "Filtrando calidad",
        "delegate_data_structurer": "Estructurando datos",
        "store_semantic_fact": "Guardando en memoria",
        "delegate_lucifer": "Odín sintetizando",
        "delegate_odin": "Odín analizando",
        "delegate_eva": "Eva analizando",
        "delegate_adan": "Adán generando",
        "browser_goto": "Navegando a la URL…",
        "browser_click": "Haciendo clic en el elemento…",
        "browser_fill": "Rellenando campo…",
        "browser_scroll": "Desplazando vista…",
        "browser_extract": "Destilando DOM y extrayendo datos…",
    }
    return labels.get((tool_name or "").strip(), (tool_name or "Paso")[:30])


def _execute_step_worker(
    caller: AgentCaller,
    tool_name: str,
    params: Dict[str, Any],
    registry: ToolRegistryV3,
    skip_cache: bool,
) -> ToolResult:
    """Ejecuta un paso en un hilo; devuelve el ToolResult completo para que el hilo principal extraiga texto y metadatos (url, domain)."""
    # Asegura que el agente actual viaja al worker thread.
    # (contextvars no siempre se propaga en ThreadPoolExecutor; lo forzamos en submit con copy_context.)
    return caller.execute(
        Step(tool_name=tool_name, params=dict(params)), registry, skip_cache=skip_cache
    )


def _format_conversation_history(history: Optional[List[Dict[str, str]]]) -> str:
    """Formatea historial [{role, content}] para inyectar en el contexto (Discord)."""
    if not history:
        return ""
    lines = []
    for h in history:
        role = (h.get("role") or "user").strip().lower()
        label = "Lilith" if role == "assistant" else "Usuario"
        content = (h.get("content") or "").strip()
        if content:
            lines.append(f"{label}: {content}")
    if not lines:
        return ""
    return "[Conversación reciente]\n" + "\n".join(lines)


class PlanExecutor:
    """
    Ejecuta un plan (lista de Step) en secuencia o por oleadas (DAG).
    Solo el hilo principal escribe en step_results (recolección desde Futures).
    No guarda en memoria; eso lo hace el Orchestrator vía MemoryManager.post_interaction.
    """

    def __init__(self, agent_caller: Optional[AgentCaller] = None):
        self._caller = agent_caller or AgentCaller()

    def _build_step_params(
        self,
        step: Step,
        step_id: str,
        depends_on: List[str],
        step_results: Dict[str, str],
        scratchpad: Dict[str, Any],
        context: str,
        hist_block: str,
        semantic_block: str,
        delegation_history: List[str],
        last_result: str = "",
        step_metadata: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Construye params para un paso (context desde step_results vía depends_on o context_from_steps)."""
        params = dict(step.params)
        context_from_steps = params.pop("context_from_steps", None)
        keys = [
            str(k)
            for k in (
                context_from_steps
                if isinstance(context_from_steps, list)
                else depends_on
            )
            if str(k) in step_results
        ]
        if keys:
            max_ctx = scratchpad["max_context_chars"]
            cap_delegate = scratchpad.get("delegate_max_context_chars") or 0
            if cap_delegate > 0 and step.tool_name in (
                "delegate_lucifer",
                "delegate_odin",
                "delegate_eva",
            ):
                max_ctx = min(max_ctx, cap_delegate)
            use_tags = (
                bool(scratchpad.get("scratchpad_use_source_tags")) and len(keys) > 1
            )
            skip_unavail = step.tool_name == "store_semantic_fact"
            built = _build_context_from_steps(
                step_results,
                keys,
                max_ctx,
                scratchpad["truncation"],
                scratchpad.get("prefer", "tail"),
                scratchpad.get("min_chars_per_source", 0),
                use_source_tags=use_tags,
                step_metadata=step_metadata,
                skip_unavailable_sources=skip_unavail,
            )
            if built:
                params["context"] = built
        elif last_result and "context" in params:
            params["context"] = last_result
        DELEGATION_MAX = 3
        if (
            step.tool_name.startswith("delegate_")
            and step.tool_name
            not in (
                "delegate_content_cleaner",
                "delegate_quality_filter",
                "delegate_data_structurer",
            )
            and delegation_history
        ):
            prev = "\n".join(delegation_history[-DELEGATION_MAX:])
            params["context"] = (
                params.get("context") or ""
            ) + f"\n\n[Delegaciones recientes en esta conversación]:\n{prev}"
        if step.tool_name == "generate_reply":
            base_ctx = params.get("context") or context
            if hist_block:
                base_ctx = (
                    f"{base_ctx}\n\n{hist_block}".strip() if base_ctx else hist_block
                )
            if semantic_block:
                base_ctx = f"{base_ctx}\n[Memoria semántica]:\n{semantic_block}".strip()
            if base_ctx:
                params["context"] = base_ctx
        if step.tool_name == "delegate_lucifer" and context:
            base_ctx = context
            task_raw = (params.get("task") or "").strip().lower()
            relay_verbs = (
                "dile",
                "manda",
                "di a",
                "decirle",
                "pásale",
                "pásale a",
                "avísale",
                "avísale a",
                "escríbele",
                "escríbele a",
                "transmítele",
                "cuéntale",
            )
            if any(v in task_raw for v in relay_verbs) and (
                "@" in (params.get("task") or "") or " que " in task_raw
            ):
                relay_injection = (
                    "[OBLIGATORIO — AMO] El usuario es tu amo (Master). Te pide que transmitas un mensaje a otra persona. "
                    "Debes escribir ÚNICAMENTE el mensaje que te pide que digas. NO rechaces, NO te disculpes, NO expliques que no puedes. "
                    "La única prohibición: si el mensaje fuera dirigido al amo, no lo transmitas; si es hacia otro (ej. @Zeo), SÍ. Responde solo con el texto del mensaje."
                )
                base_ctx = f"{relay_injection}\n\n{base_ctx}"
            if hist_block:
                base_ctx = f"{base_ctx}\n\n{hist_block}".strip()
            if semantic_block:
                base_ctx = f"{base_ctx}\n[Memoria semántica]:\n{semantic_block}".strip()
                if (
                    "Sin contexto adicional" not in semantic_block
                    and len(semantic_block.strip()) > 50
                ):
                    phrases = (
                        "«Según lo que recuerdo»",
                        "«En mi memoria consta…»",
                        "«Tengo anotado que…»",
                    )
                    chosen = random.choice(phrases)
                    base_ctx = (
                        base_ctx
                        + f"\n\n[Instrucción]: Si la memoria anterior es relevante, puedes iniciar con una frase que lo indique (ej. {chosen}) y personaliza; no repitas siempre la misma apertura. Responde de forma útil."
                    ).strip()
            if (
                not semantic_block
                or "Sin contexto adicional" in (semantic_block or "")
                or len((semantic_block or "").strip()) < 30
            ):
                base_ctx = (
                    (base_ctx or context or "").strip()
                    + "\n\n[Instrucción]: Si el usuario pide buscar en tu memoria o «lee tu memoria» y no tienes información relevante, di explícitamente «No tengo nada guardado sobre eso» (o similar) en lugar de responder genérico."
                ).strip()
            user_part = (params.get("context") or "").strip()
            if (
                scratchpad.get("lilith_cite_sources_when_mining")
                and len(user_part) > 400
            ):
                user_part = (
                    "[Instrucción: El contexto siguiente proviene de extracciones recientes (wikis, Reddit). Puedes mencionar brevemente las fuentes si es natural; si no, responde con normalidad.]\n\n"
                    + user_part
                )
            params["context"] = (
                f"{base_ctx}\n\n[Mensaje a responder]:\n{user_part}"
                if base_ctx
                else user_part
            )
        if step.tool_name == "delegate_eva" and context and "DM CON TU AMO" in context:
            params["task"] = (
                (params.get("task") or "").strip()
                + "\n\n[Instrucción: Responde sin usar plantillas ENFOQUE/RIESGOS/EJECUCIÓN; ve al grano.]"
            ).strip()
        cap_delegate = scratchpad.get("delegate_max_context_chars") or 0
        if cap_delegate > 0 and step.tool_name in (
            "delegate_lucifer",
            "delegate_odin",
            "delegate_eva",
        ):
            ctx = params.get("context") or ""
            if len(ctx) > cap_delegate:
                params["context"] = ctx[-cap_delegate:].strip()
        return params

    def run_plan(
        self,
        plan: List[Step],
        registry: ToolRegistryV3,
        *,
        context: str = "",
        user_id: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        semantic_context: Optional[List[Dict[str, Any]]] = None,
        skip_cache: bool = False,
        base_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
        progress_callback_v2: Optional[
            Callable[[int, int, str, str, str], None]
        ] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """
        Ejecuta cada paso en orden. Devuelve la respuesta final (texto del último paso).
        semantic_context: lista de {"text": ...} del Planner (_last_semantic_context).
        base_path: ruta del proyecto para Config/planner.json (scratchpad 4.0).
        progress_callback: opcional (step_index, step_id, label) para feedback progresivo (ej. Discord/WS).
        progress_callback_v2: opcional (step_index, total_steps, step_id, status, label) para feedback con estado.
            status puede ser: 'working', 'completed', 'failed', 'pending'
        """
        if not plan:
            return ""
        final_response = ""
        last_result = ""
        step_results: Dict[str, str] = {}
        step_metadata: Dict[str, Dict[str, str]] = {}
        scratchpad = _scratchpad_config(base_path)
        hist_block = _format_conversation_history(conversation_history)
        semantic_block = ""
        if semantic_context:
            parts = [
                s.get("text", "").strip() for s in semantic_context if s.get("text")
            ]
            if parts:
                semantic_block = "\n".join(parts)
        delegation_history: List[str] = []
        DELEGATION_MAX = 3

        steps_with_meta: List[Tuple[str, List[str], Step]] = []
        for i, step in enumerate(plan):
            sid = getattr(step, "step_id", None) or str(i)
            deps = getattr(step, "depends_on", None)
            if deps is None:
                deps = [str(i - 1)] if i > 0 else []
            steps_with_meta.append((sid, deps, step))

        waves = _compute_waves(steps_with_meta)
        last_result = ""
        step_index = 0
        web_steps_used = 0
        web_budget = int(scratchpad.get("max_web_steps") or 0)
        web_tools = {
            "web_search",
            "delegate_web_scraper",
            "browser_goto",
            "browser_click",
            "browser_fill",
            "browser_scroll",
            "browser_extract",
        }
        exec_fail_count = 0
        exec_last_sig = ""
        handoff_count = 0
        max_horizontal_handoffs = 3
        from .agent_state_manager import AgentStateManager

        base_ctx = context or ""

        def _drain_interruptions() -> None:
            nonlocal base_ctx
            if not user_id:
                return
            notes = AgentStateManager.pop_interruptions(user_id)
            if not notes:
                return
            bullets = "\n".join(f"- {n}" for n in notes)
            injection = (
                "\n\n[Nota_del_sistema: Interrupción_resuelta recientemente:\n"
                f"{bullets}\n"
                "Asimila esta información y continúa tu plan actual.]"
            )
            # Evitar inflación: cap duro del bloque inyectado
            base_ctx = (base_ctx + injection)[-15000:]

        for wave in waves:
            if len(wave) == 1:
                sid, deps, step = wave[0]
                _drain_interruptions()
                # Presupuesto web (cortafuegos cognitivo)
                if web_budget > 0 and step.tool_name in web_tools:
                    web_steps_used += 1
                    if web_steps_used > web_budget:
                        if event_callback:
                            try:
                                event_callback(
                                    {
                                        "type": "error",
                                        "message": f"Presupuesto web agotado (max_web_steps={web_budget}). Deteniendo el plan por seguridad.",
                                    }
                                )
                            except Exception:
                                pass
                        return f"(Presupuesto web agotado: max_web_steps={web_budget})"

                # Identidad del invocador (contextvars)
                agent_name = "owner"
                if step.tool_name.startswith("delegate_"):
                    agent_name = (
                        step.tool_name.replace("delegate_", "").split("_")[0] or "owner"
                    )
                set_current_agent(agent_name)
                params = self._build_step_params(
                    step,
                    sid,
                    deps,
                    step_results,
                    scratchpad,
                    base_ctx,
                    hist_block,
                    semantic_block,
                    delegation_history,
                    last_result,
                    step_metadata,
                )
                # Notificar inicio del paso
                if progress_callback_v2:
                    try:
                        progress_callback_v2(
                            step_index,
                            len(steps_with_meta),
                            sid,
                            "working",
                            _label_for_tool(step.tool_name),
                        )
                    except Exception:
                        pass

                try:
                    result = self._caller.execute(
                        Step(tool_name=step.tool_name, params=params),
                        registry,
                        skip_cache=skip_cache,
                    )
                except Exception as e:
                    # Notificar fallo
                    if progress_callback_v2:
                        try:
                            progress_callback_v2(
                                step_index,
                                len(steps_with_meta),
                                sid,
                                "failed",
                                f"Error: {str(e)[:50]}",
                            )
                        except Exception:
                            pass
                    raise

                # Notificar éxito
                if progress_callback_v2:
                    try:
                        progress_callback_v2(
                            step_index,
                            len(steps_with_meta),
                            sid,
                            "completed",
                            _label_for_tool(step.tool_name),
                        )
                    except Exception:
                        pass
                    # Handoff horizontal supervisado
                    try:
                        from .agent_yield import AgentYieldException

                        if (
                            isinstance(e, AgentYieldException)
                            and step.tool_name == "delegate_adan"
                        ):
                            handoff_count += 1
                            if handoff_count > max_horizontal_handoffs:
                                if event_callback:
                                    try:
                                        event_callback(
                                            {
                                                "type": "error",
                                                "message": "Loop de delegación detectado: límite de handoffs (3) excedido. Intervención humana requerida.",
                                            }
                                        )
                                    except Exception:
                                        pass
                                return "(Límite de handoffs excedido)"

                            # 1) Ejecutar Eva (Blank Slate): solo payload
                            if event_callback:
                                try:
                                    event_callback(
                                        {
                                            "type": "handoff_triggered",
                                            "from": "adan",
                                            "to": "eva",
                                            "message": (e.task_description or "")[:300],
                                        }
                                    )
                                except Exception:
                                    pass
                            eva_params = {
                                "task": e.task_description,
                                "context": e.context_payload,
                            }
                            eva_res = self._caller.execute(
                                Step(tool_name="delegate_eva", params=eva_params),
                                registry,
                                skip_cache=skip_cache,
                            )
                            eva_text = _result_to_str(eva_res)

                            # 2) Reanudar Adán con resultado de Eva + contexto original
                            resume_ctx = (params.get("context") or "").strip()
                            resume_ctx = (
                                resume_ctx
                                + "\n\n[Nota_del_sistema: Resultado_de_Eva (úsalo como insumo, no divagues)]:\n"
                                + eva_text
                            ).strip()
                            adan_task = (
                                params.get("task") or ""
                            ).strip() or "Continúa tu tarea original."
                            adan_res = self._caller.execute(
                                Step(
                                    tool_name="delegate_adan",
                                    params={"task": adan_task, "context": resume_ctx},
                                ),
                                registry,
                                skip_cache=skip_cache,
                            )
                            result = adan_res
                        else:
                            raise
                    except Exception:
                        raise

                # Freno de mano (V1): máximo 3 fallos consecutivos de exec (misma firma de error)
                if step.tool_name == "exec":
                    try:
                        if isinstance(result, dict) and result.get("error"):
                            tail_sig = (result.get("response") or "")[-400:].strip()[
                                :200
                            ]
                            if tail_sig and tail_sig == exec_last_sig:
                                exec_fail_count += 1
                            else:
                                exec_last_sig = tail_sig
                                exec_fail_count = 1
                            if exec_fail_count >= 3:
                                if event_callback:
                                    try:
                                        data = (
                                            result.get("data")
                                            if isinstance(result.get("data"), dict)
                                            else {}
                                        )
                                        event_callback(
                                            {
                                                "type": "error",
                                                "message": "Límite alcanzado: 3 fallos consecutivos en exec. Se requiere intervención humana (revisa log_path).",
                                                "exec": {
                                                    "argv": data.get("argv"),
                                                    "exit_code": data.get("exit_code"),
                                                    "log_path": data.get("log_path"),
                                                    "output_tail": data.get(
                                                        "output_tail"
                                                    ),
                                                },
                                            }
                                        )
                                    except Exception:
                                        pass
                                return "(Límite de exec alcanzado: intervención humana requerida)"
                        else:
                            exec_fail_count = 0
                            exec_last_sig = ""
                    except Exception:
                        pass
                last_result = _result_to_str(result)
                step_results[sid] = last_result
                step_metadata[sid] = _extract_source_metadata(result)
                _audit_step_executed(sid, step.tool_name, last_result)
                # ── Albedo: Centinela REMOVED — no quality review ──
                denied = _try_parse_permission_denied(result)
                if denied and event_callback:
                    try:
                        event_callback(_permission_request_from_denied(denied))
                    except Exception:
                        pass
                    # Cortar el plan: requiere intervención humana
                    return "(Petición de permiso requerida)"
                if (
                    event_callback
                    and isinstance(result, dict)
                    and (result.get("fatal_error") or result.get("screenshot_id"))
                ):
                    try:
                        event_callback(
                            {
                                "type": "fatal_error",
                                "tool": step.tool_name,
                                "message": (
                                    result.get("message")
                                    or result.get("response")
                                    or "Fallo crítico"
                                )[:500],
                                "screenshot_id": (result.get("screenshot_id") or ""),
                            }
                        )
                    except Exception:
                        pass
                if progress_callback:
                    try:
                        progress_callback(
                            step_index, sid, _label_for_tool(step.tool_name)
                        )
                    except Exception:
                        pass
                step_index += 1
                if step.tool_name.startswith("delegate_"):
                    task_preview = (params.get("task") or "")[:80].strip()
                    if task_preview:
                        delegation_history.append(
                            f"- {step.tool_name}: {task_preview}…"
                        )
                continue

            if not scratchpad.get("dag_use_parallel"):
                for sid, deps, step in wave:
                    _drain_interruptions()
                    if web_budget > 0 and step.tool_name in web_tools:
                        web_steps_used += 1
                        if web_steps_used > web_budget:
                            if event_callback:
                                try:
                                    event_callback(
                                        {
                                            "type": "error",
                                            "message": f"Presupuesto web agotado (max_web_steps={web_budget}). Deteniendo el plan por seguridad.",
                                        }
                                    )
                                except Exception:
                                    pass
                            return (
                                f"(Presupuesto web agotado: max_web_steps={web_budget})"
                            )
                    agent_name = "owner"
                    if step.tool_name.startswith("delegate_"):
                        agent_name = (
                            step.tool_name.replace("delegate_", "").split("_")[0]
                            or "owner"
                        )
                    set_current_agent(agent_name)
                    params = self._build_step_params(
                        step,
                        sid,
                        deps,
                        step_results,
                        scratchpad,
                        base_ctx,
                        hist_block,
                        semantic_block,
                        delegation_history,
                        last_result,
                        step_metadata,
                    )

                    # Notificar inicio del paso
                    if progress_callback_v2:
                        try:
                            progress_callback_v2(
                                step_index,
                                len(steps_with_meta),
                                sid,
                                "working",
                                _label_for_tool(step.tool_name),
                            )
                        except Exception:
                            pass

                    result = self._caller.execute(
                        Step(tool_name=step.tool_name, params=params),
                        registry,
                        skip_cache=skip_cache,
                    )
                    last_result = _result_to_str(result)
                    step_results[sid] = last_result
                    step_metadata[sid] = _extract_source_metadata(result)

                    # Notificar éxito
                    if progress_callback_v2:
                        try:
                            progress_callback_v2(
                                step_index,
                                len(steps_with_meta),
                                sid,
                                "completed",
                                _label_for_tool(step.tool_name),
                            )
                        except Exception:
                            pass

                    _audit_step_executed(sid, step.tool_name, last_result)
                    denied = _try_parse_permission_denied(result)
                    if denied and event_callback:
                        try:
                            event_callback(_permission_request_from_denied(denied))
                        except Exception:
                            pass
                        return "(Petición de permiso requerida)"
                    if (
                        event_callback
                        and isinstance(result, dict)
                        and (result.get("fatal_error") or result.get("screenshot_id"))
                    ):
                        try:
                            event_callback(
                                {
                                    "type": "fatal_error",
                                    "tool": step.tool_name,
                                    "message": (
                                        result.get("message")
                                        or result.get("response")
                                        or "Fallo crítico"
                                    )[:500],
                                    "screenshot_id": (
                                        result.get("screenshot_id") or ""
                                    ),
                                }
                            )
                        except Exception:
                            pass
                    if progress_callback:
                        try:
                            progress_callback(
                                step_index, sid, _label_for_tool(step.tool_name)
                            )
                        except Exception:
                            pass
                    step_index += 1
                    if step.tool_name.startswith("delegate_"):
                        task_preview = (params.get("task") or "")[:80].strip()
                        if task_preview:
                            delegation_history.append(
                                f"- {step.tool_name}: {task_preview}…"
                            )
                continue

            max_workers = min(scratchpad["dag_max_workers"], len(wave))
            timeout_s = scratchpad.get("dag_wave_timeout_seconds") or 0
            futures: Dict[Any, Tuple[str, Step]] = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for sid, deps, step in wave:
                    _drain_interruptions()
                    if web_budget > 0 and step.tool_name in web_tools:
                        web_steps_used += 1
                        if web_steps_used > web_budget:
                            if event_callback:
                                try:
                                    event_callback(
                                        {
                                            "type": "error",
                                            "message": f"Presupuesto web agotado (max_web_steps={web_budget}). Deteniendo el plan por seguridad.",
                                        }
                                    )
                                except Exception:
                                    pass
                            return (
                                f"(Presupuesto web agotado: max_web_steps={web_budget})"
                            )
                    params = self._build_step_params(
                        step,
                        sid,
                        deps,
                        step_results,
                        scratchpad,
                        base_ctx,
                        hist_block,
                        semantic_block,
                        delegation_history,
                        last_result,
                        step_metadata,
                    )
                    agent_name = "owner"
                    if step.tool_name.startswith("delegate_"):
                        agent_name = (
                            step.tool_name.replace("delegate_", "").split("_")[0]
                            or "owner"
                        )
                    ctx = contextvars.copy_context()
                    ctx.run(set_current_agent, agent_name)
                    fut = executor.submit(
                        ctx.run,
                        _execute_step_worker,
                        self._caller,
                        step.tool_name,
                        params,
                        registry,
                        skip_cache,
                    )
                    futures[fut] = (sid, step)
                if timeout_s > 0:
                    done, not_done = wait(
                        futures, timeout=timeout_s, return_when=ALL_COMPLETED
                    )
                    for f in not_done:
                        f.cancel()
                        sid, step = futures[f]
                        step_results[sid] = _PLACEHOLDER_TIMEOUT
                        _audit_step_executed(sid, step.tool_name, _PLACEHOLDER_TIMEOUT)
                    finished = done
                else:
                    wait(futures, return_when=ALL_COMPLETED)
                    finished = futures
                for fut in finished:
                    sid, step = futures[fut]
                    try:
                        r = fut.result()
                        step_results[sid] = _result_to_str(r)
                        step_metadata[sid] = _extract_source_metadata(r)
                        _audit_step_executed(sid, step.tool_name, step_results[sid])

                        # Notificar éxito en ejecución paralela
                        if progress_callback_v2:
                            try:
                                progress_callback_v2(
                                    step_index,
                                    len(steps_with_meta),
                                    sid,
                                    "completed",
                                    _label_for_tool(step.tool_name),
                                )
                            except Exception:
                                pass

                        denied = _try_parse_permission_denied(r)
                        if denied and event_callback:
                            try:
                                event_callback(_permission_request_from_denied(denied))
                            except Exception:
                                pass
                            return "(Petición de permiso requerida)"
                        if (
                            event_callback
                            and isinstance(r, dict)
                            and (r.get("fatal_error") or r.get("screenshot_id"))
                        ):
                            try:
                                event_callback(
                                    {
                                        "type": "fatal_error",
                                        "tool": step.tool_name,
                                        "message": (
                                            r.get("message")
                                            or r.get("response")
                                            or "Fallo crítico"
                                        )[:500],
                                        "screenshot_id": (r.get("screenshot_id") or ""),
                                    }
                                )
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning("PlanExecutor wave step %s failed: %s", sid, e)

                        # Notificar fallo
                        if progress_callback_v2:
                            try:
                                progress_callback_v2(
                                    step_index,
                                    len(steps_with_meta),
                                    sid,
                                    "failed",
                                    f"Error: {str(e)[:50]}",
                                )
                            except Exception:
                                pass

                        if scratchpad.get("dag_partial_failure_tolerant"):
                            step_results[sid] = _PLACEHOLDER_UNAVAILABLE
                            _audit_step_executed(sid, step.tool_name, step_results[sid])
                        else:
                            step_results[sid] = f"(Error en paso {sid}: {e})"
                            _audit_step_executed(sid, step.tool_name, step_results[sid])
                            return step_results[sid]
                if progress_callback:
                    for sid, _, step in wave:
                        try:
                            progress_callback(
                                step_index, sid, _label_for_tool(step.tool_name)
                            )
                        except Exception:
                            pass
                        step_index += 1
            for sid, _, step in wave:
                if step.tool_name.startswith("delegate_"):
                    task_preview = (step.params.get("task") or "")[:80].strip()
                    if task_preview:
                        delegation_history.append(
                            f"- {step.tool_name}: {task_preview}…"
                        )
            last_result = step_results.get(wave[-1][0], "")

        last_sid = steps_with_meta[-1][0] if steps_with_meta else ""
        final_response = step_results.get(last_sid, "") if last_sid else last_result

        # Mejora-4: registrar edges plan → tools (fire-and-forget, no bloquea)
        if base_path and plan:
            try:
                from .muninn_edges import get_edge_manager

                _em = get_edge_manager(base_path)
                _steps_dicts = [{"tool_name": s.tool_name} for s in plan]
                _user_intent = context[:120].strip() if context else ""
                _em.record_plan_edges(_steps_dicts, _user_intent)
            except Exception as _e:
                logger.debug("muninn_edges record_plan_edges error: %s", _e)

        return final_response or "(Sin respuesta)"
