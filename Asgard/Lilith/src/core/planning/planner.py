"""
Lilith 3.0 — Planner (Fase 2 + 3 + 4).
Genera un plan de pasos (List[Step]).
Fase 3: consulta memoria semántica. Fase 4: prioriza planes aprendidos (LearningEngine).
Misión 3.4 E.3: auditoría de decisiones en decision_audit.jsonl.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger("Planner")

if TYPE_CHECKING:
    from .learning import LearningEngine, LocalIntentClassifier
    from .memory import MemoryManager

# v4.2: Decision Auditor v2 (adicional al auditor original)
from .auditor.decision_auditor_v2 import log_decision as log_decision_v2

# v5.0: Planner Auto-Batch para operaciones PC
from .planner_autobatch import try_auto_batch


@dataclass
class Step:
    """Un paso del plan: ejecutar una tool con unos params. 4.0 DAG: step_id y depends_on para oleadas paralelas."""

    tool_name: str
    params: Dict[str, Any]
    step_id: Optional[str] = None
    depends_on: Optional[List[str]] = None


@dataclass
class PlanResult:
    steps: List["Step"]
    confidence: float  # 0.0 – 1.0
    confidence_reason: str  # "intent_clear" | "fallback_used" | "dangerous_steps" | "low_match"


def _plan_to_result(steps: List["Step"], reason: str) -> PlanResult:
    """Calcula confidence a partir de cómo se generó el plan."""
    dangerous = {
        "edit_file",
        "system_execute",
        "exec",
        "self_improve",
        "browser_goto",
        "browser_click",
        "browser_fill",
        "browser_extract",
        "browser_scroll",
    }
    n_dangerous = sum(
        1 for s in (steps or []) if getattr(s, "tool_name", "") in dangerous
    )

    if reason == "learned":
        base = 0.9
    elif reason == "classifier":
        base = 0.85
    elif reason == "intent_pattern":
        base = 0.80
    elif reason == "matching_learning":
        base = 0.75
    elif reason == "fallback":
        base = 0.45
    else:
        base = 0.60

    confidence = max(0.1, base - (n_dangerous * 0.15))

    if confidence >= 0.75:
        label = "intent_clear"
    elif confidence >= 0.5:
        label = "low_match"
    else:
        label = "fallback_used" if "fallback" in (reason or "") else "dangerous_steps"

    return PlanResult(steps=steps or [], confidence=confidence, confidence_reason=label)


def _step_odin_conversacional(message: str) -> Step:
    """Paso único: delegar a Odín para respuesta conversacional (absorbió a Lucifer)."""
    return Step(
        tool_name="delegate_odin",
        params={
            "task": "Responde de forma conversacional y útil al siguiente mensaje.",
            "context": message or "",
        },
    )


def _step_lilith_conversacional(message: str) -> Step:
    """Paso único: Lilith responde directamente (fallback para conversación casual)."""
    return Step(
        tool_name="generate_reply",
        params={
            "user_message": message or "",
        },
    )


# Alias de retrocompatibilidad (ahora apunta a Lilith directa)
_step_lucifer_conversacional = _step_lilith_conversacional


def _inject_preemptive_context(
    steps: List["Step"], preemptive_ctx: str, attention_ctx: str = ""
) -> None:
    """
    D.10 — Inyecta el contexto preemptivo y attention stack en el param 'context' de Steps de agentes
    que lo tengan vacío. Solo afecta delegate_* y generate_reply.
    """
    if not steps:
        return

    # Combinar ambos contextos si existen
    combined_ctx = ""
    if attention_ctx:
        combined_ctx = attention_ctx
    if preemptive_ctx:
        if combined_ctx:
            combined_ctx = combined_ctx + "\n\n" + preemptive_ctx
        else:
            combined_ctx = preemptive_ctx

    if not combined_ctx:
        return

    _agent_tools = {
        "delegate_odin",
        "delegate_eva",
        "delegate_adan",
        "delegate_cursor",
        "delegate_kimi_cli",
        "delegate_shalltear",
        "delegate_odin_creative",
        "generate_reply",
    }
    for step in steps:
        tool = getattr(step, "tool_name", "") or ""
        if tool not in _agent_tools:
            continue
        params = getattr(step, "params", {}) or {}
        # Inyectar en 'context' si está vacío
        if "context" in params and not (params.get("context") or "").strip():
            params["context"] = combined_ctx
        # Para generate_reply, añadir como contexto adicional si hay user_message
        elif tool == "generate_reply" and "user_message" in params:
            params.setdefault("context", combined_ctx)


def _record_matching(planner: "Planner", message: str, steps: List[Step]) -> None:
    """Misión 4.0 Fase 0: registra mensaje → tool para matching learning."""
    if not steps:
        return
    try:
        from .matching_learner import is_enabled as matching_enabled
        from .matching_learner import record as matching_record

        base = (
            getattr(planner.memory_manager, "base_path", None)
            if planner.memory_manager
            else None
        )
        if base is None:
            base = Path(__file__).resolve().parent.parent.parent
        if matching_enabled(base):
            matching_record(base, message or "", steps[0].tool_name)
    except Exception:
        pass


def _extract_path(lower: str, text: str) -> Optional[str]:
    """Extrae una ruta de archivo o carpeta del mensaje."""
    # Rutas Windows (D:\Proyectos\Yggdrasil\Asgard\Lilith\Core\Docs)
    m = re.search(r"([a-z]:[\\/][\w\\/.-]+)", lower)
    if m:
        return text[m.start() : m.end()].strip().rstrip(".,;")
    m = re.search(
        r"(\b(?:backend|tests|core|api|memory)/[\w./\-]+\.[a-z0-9]+)", lower, re.I
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"([\w./\-]+\.(?:py|md|txt|json|yaml|yml))\b", lower, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\b(?:backend|tests|core|api|memory)(?:/[\w.-]+)*)\b", lower, re.I)
    if m:
        return m.group(1).strip()
    return None


def _after_keyword(text: str, lower: str, keyword: str) -> Optional[str]:
    """Devuelve el fragmento después del keyword (path o archivo)."""
    idx = lower.find(keyword)
    if idx == -1:
        return None
    start = idx + len(keyword)
    rest = text[start:].strip()
    rest = re.sub(r"^[:\s,]+", "", rest)
    m = re.match(r"([\w./\-]+(?:\.[a-z0-9]+)?)", rest, re.I)
    if m:
        return m.group(1).strip()
    if rest:
        parts = rest.split()
        return parts[0] if parts else None
    return None


# Patrón para extraer URLs del mensaje (expansión dinámica DAG, sección 5.3 / 6.1). Baja latencia, sin NLP.
_URL_PATTERN = re.compile(r"https?://[^\s\)\]\">\']+", re.IGNORECASE)


def _extract_urls_from_message(text: str, max_urls: int = 10) -> List[str]:
    """
    Extrae hasta max_urls URLs del mensaje con regex puro (sin NLP).
    Usado para expansión dinámica del DAG (N instancias del sub-grafo por URL).
    Devuelve lista ordenada por primera aparición, sin duplicados.
    """
    if not (text or text.strip()):
        return []
    seen: set = set()
    out: List[str] = []
    for m in _URL_PATTERN.finditer(text):
        url = m.group(0).rstrip(".,;:")
        if url not in seen and len(out) < max_urls:
            seen.add(url)
            out.append(url)
    return out


# Palabras que no son rutas: evita "Archivo no encontrado: tu/el/la/api" y "te" (de "mejorarte")
_INVALID_PATH_TOKENS = frozenset(
    {
        "tu",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "a",
        "mi",
        "su",
        "r",
        "y",
        "o",
        "de",
        "en",
        "api",
        "te",
    }
)


def _looks_like_meta_question(lower: str) -> bool:
    """True si el mensaje parece una pregunta de opinión/meta (no delegar a Eva ni improve_file)."""
    meta = (
        "qué te gustaría",
        "qué cambiarías",
        "desde tu perspectiva",
        "qué mejorarías en la experiencia",
        "lista 3-5 puntos",
        "lista 3-5 ideas",
        "mejorarte",
        "mejorarme",
        "ideas para mejorarte",
        "ideas para mejorarme",
        "dame ideas para mejorarte",
        "cómo mejorarte",
        "cómo mejorarme",
    )
    return any(m in lower for m in meta)


def _rest_after_keyword(
    text: str, lower: str, keyword: str, max_len: int = 200
) -> Optional[str]:
    """Devuelve todo el texto después del keyword (para nombres de proyecto con espacios)."""
    idx = lower.find(keyword)
    if idx == -1:
        return None
    rest = text[idx + len(keyword) :].strip()
    rest = re.sub(r"^[:\s,]+", "", rest)
    if not rest:
        return None
    return rest[:max_len].strip() or None


def _load_intent_patterns(base_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Carga Config/intent_patterns.json y devuelve intents ordenados por priority desc (Misión 3.3)."""
    from .json_safe import safe_load

    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent
    path = base_path / "Config" / "intent_patterns.json"
    data = safe_load(path, default={})
    intents = data.get("intents") if isinstance(data, dict) else []
    if not isinstance(intents, list):
        return []
    return sorted(intents, key=(lambda x: int(x.get("priority") or 0)), reverse=True)


def _get_matched_intent_name(
    message: str, base_path: Optional[Path] = None
) -> Optional[str]:
    """Devuelve el nombre de la primera intención que coincide con el mensaje (C.3)."""
    if not (message or message.strip()):
        return None
    lower = message.strip().lower()
    for intent in _load_intent_patterns(base_path):
        triggers = intent.get("triggers") or []
        if isinstance(triggers, list) and any(
            (t or "").strip().lower() in lower for t in triggers
        ):
            name = (intent.get("name") or "").strip()
            if name:
                return name
    return None


def _load_plan_dag(
    base_path: Optional[Path], dag_name: str
) -> Optional[Dict[str, Any]]:
    """Carga Config/plan_dags.json y devuelve el DAG con ese nombre (nodos con depends_on)."""
    if not base_path or not Path(base_path).exists():
        return None
    try:
        from .json_safe import safe_load

        path = Path(base_path) / "Config" / "plan_dags.json"
        if not path.exists():
            return None
        data = safe_load(path, default={})
        if not isinstance(data, dict):
            return None
        return data.get(dag_name) if isinstance(data.get(dag_name), dict) else None
    except Exception:
        return None


class DAGCycleError(ValueError):
    """Excepción cuando plan_dags.json define dependencias circulares."""

    def __init__(self, dag_name: str, cycle_nodes: List[str]):
        self.dag_name = dag_name
        self.cycle_nodes = cycle_nodes
        super().__init__(
            f"DAG '{dag_name}' tiene ciclo o dependencias inválidas en nodos: {sorted(cycle_nodes)}"
        )


def _dag_to_steps(
    dag: Dict[str, Any], message_text: str, dag_name: str = ""
) -> List[Step]:
    """
    Convierte un DAG (nodos con tool_name, params, depends_on) en lista de Steps en orden topológico.
    Sustituye {{message}} en params por message_text.
    Lanza DAGCycleError si hay dependencias circulares (nodos que no se pueden ordenar).
    """
    nodes = dag.get("nodes")
    if not isinstance(nodes, dict):
        return []
    order: List[str] = []
    remaining = set(nodes.keys())
    while remaining:
        added = False
        for nid in list(remaining):
            node = nodes.get(nid)
            deps = (node.get("depends_on") or []) if isinstance(node, dict) else []
            if all(d in order for d in deps):
                order.append(nid)
                remaining.discard(nid)
                added = True
                break
        if not added:
            raise DAGCycleError(dag_name or "unknown", list(remaining))
    steps: List[Step] = []
    for nid in order:
        node = nodes.get(nid)
        if not isinstance(node, dict):
            continue
        tool_name = (node.get("tool_name") or "").strip()
        if not tool_name:
            continue
        params = dict(node.get("params") or {})
        for k, v in params.items():
            if isinstance(v, str) and "{{message}}" in v:
                params[k] = v.replace("{{message}}", message_text)
        deps = node.get("depends_on")
        if not isinstance(deps, list):
            deps = []
        steps.append(
            Step(tool_name=tool_name, params=params, step_id=nid, depends_on=deps)
        )
    return steps


def _resolve_intent_from_config(
    message: str,
    lower: str,
    text: str,
    base_path: Optional[Path] = None,
) -> Optional[List[Step]]:
    """
    Resuelve la intención desde Config/intent_patterns.json (Misión 3.3).
    Devuelve lista de Steps si hay match, None si no.
    """
    intents = _load_intent_patterns(base_path)
    path = _extract_path(lower, text)

    for intent in intents:
        triggers = intent.get("triggers") or []
        if not isinstance(triggers, list):
            continue
        if not any((t or "").strip().lower() in lower for t in triggers):
            continue
        name = (intent.get("name") or "").strip()
        logger.debug("Planner: intent matched %s", name)

        if intent.get("action") == "store_fact":
            return [_step_lucifer_conversacional(message)]

        agent = (intent.get("agent") or "").strip().lower()
        if agent == "eva":
            if _looks_like_meta_question(lower):
                continue
            return [
                Step(tool_name="delegate_eva", params={"task": text, "context": ""})
            ]
        if agent == "lilith":
            return [Step(tool_name="generate_reply", params={"user_message": text})]
        if agent == "shalltear":
            return [
                Step(
                    tool_name="delegate_shalltear",
                    params={"task": "quick_answer", "user_message": text},
                )
            ]
        if agent == "pc_operation":
            # PC Agent batch operation - será manejado por telegram_api con confirmación
            return [Step(tool_name="pc_operation_batch", params={"user_message": text})]
        if agent == "odin":
            if intent.get("requires_gather_directory"):
                if not path:
                    m = re.search(r"\b(backend|core|api|tests)(?:/[\w.-]+)*\b", lower)
                    path = m.group(0) if m else "Backend"
                path = path or "Backend"
                if path and not path.endswith("/"):
                    path = path.rstrip("/")
                task_odin = (
                    "Analiza de forma exhaustiva el contenido proporcionado. "
                    "Busca patrones, problemas, arquitectura y oportunidades de mejora. Sé detallado y completo."
                )
                return [
                    Step(
                        tool_name="gather_directory",
                        params={
                            "path": path or "Backend",
                            "max_chars": 80000,
                            "max_files": 80,
                        },
                    ),
                    Step(
                        tool_name="delegate_odin",
                        params={"task": task_odin, "context": ""},
                    ),
                ]
            return [
                Step(tool_name="delegate_odin", params={"task": text, "context": ""})
            ]
        if agent == "cursor":
            return [
                Step(tool_name="delegate_cursor", params={"task": text, "context": ""})
            ]
        if agent == "adan":
            return [
                Step(tool_name="delegate_adan", params={"task": text, "context": ""})
            ]
        if agent in ("lucifer", "odin_creative"):
            # Lucifer absorbido por Odín con intent creativo
            if intent.get("requires_gather_directory") and path:
                path = path.rstrip("/\\").rstrip(".,;")
                if (
                    path
                    and path.strip().lower() not in _INVALID_PATH_TOKENS
                    and len(path.strip()) > 2
                ):
                    task_lucifer = (
                        "Con el contenido del directorio/carpeta proporcionado a continuación, responde en prosa natural. "
                        "No uses plantillas ENFOQUE/RIESGOS; resume con tus palabras qué hay, qué está implementado o qué preguntan. "
                        "No repitas literalmente etiquetas tipo Tópico:, Resumen: ni IDs de chunks."
                    )
                    return [
                        Step(
                            tool_name="gather_directory",
                            params={
                                "path": path.strip(),
                                "max_chars": 60000,
                                "max_files": 60,
                            },
                        ),
                        Step(
                            tool_name="delegate_odin",
                            params={
                                "task": task_lucifer
                                + "\n\nPregunta del usuario: "
                                + text,
                                "context": "",
                            },
                        ),
                    ]
            return [
                Step(tool_name="delegate_odin", params={"task": text, "context": ""})
            ]
        if agent == "local_irreverent_model":
            return [
                Step(
                    tool_name="delegate_local_irreverent",
                    params={"task": text, "context": ""},
                )
            ]
        if agent == "web_scraper":
            # Si el usuario dispara investigate_web pero no incluye URL, primero buscamos URLs
            # y dejamos que WebScraperAgent tome la primera desde context (ver web_scraper_agent.py).
            if not _extract_urls_from_message(text, max_urls=1):
                return [
                    Step(
                        tool_name="web_search", params={"query": text, "max_results": 5}
                    ),
                    Step(
                        tool_name="delegate_web_scraper",
                        params={"task": text, "context": ""},
                    ),
                    Step(
                        tool_name="delegate_content_cleaner",
                        params={"task": "Limpia el contenido extraído.", "context": ""},
                    ),
                    Step(
                        tool_name="delegate_quality_filter",
                        params={
                            "task": "Evalúa la calidad del contenido.",
                            "context": "",
                        },
                    ),
                    Step(
                        tool_name="delegate_data_structurer",
                        params={
                            "task": "Estructura el contenido validado.",
                            "context": "",
                        },
                    ),
                    Step(tool_name="store_semantic_fact", params={"context": ""}),
                ]
            dag = _load_plan_dag(base_path, "investigate_web")
            if dag and dag.get("nodes"):
                try:
                    steps_from_dag = _dag_to_steps(
                        dag, text, dag_name="investigate_web"
                    )
                    if steps_from_dag:
                        return steps_from_dag
                except DAGCycleError as e:
                    logger.warning("Planner: %s; usando plan plano.", e)
            # Fallback: lista plana (mismo orden que el DAG)
            return [
                Step(
                    tool_name="delegate_web_scraper",
                    params={"task": text, "context": ""},
                ),
                Step(
                    tool_name="delegate_content_cleaner",
                    params={"task": "Limpia el contenido extraído.", "context": ""},
                ),
                Step(
                    tool_name="delegate_quality_filter",
                    params={"task": "Evalúa la calidad del contenido.", "context": ""},
                ),
                Step(
                    tool_name="delegate_data_structurer",
                    params={"task": "Estructura el contenido validado.", "context": ""},
                ),
                Step(tool_name="store_semantic_fact", params={"context": ""}),
            ]

        tool = (intent.get("tool") or "").strip()
        if tool == "read_file":
            p = (
                path
                or _after_keyword(text, lower, "lee")
                or _after_keyword(text, lower, "leer")
                or _after_keyword(text, lower, "abre")
            )
            if p and (
                p.strip().lower() not in _INVALID_PATH_TOKENS and len(p.strip()) > 2
            ):
                return [Step(tool_name="read_file", params={"path": p})]
            continue
        if tool == "list_directory":
            # No interpretar "Lista 3-5 puntos/ideas/sugerencias" como listar directorio
            if re.search(
                r"lista\s+\d+\s*-\s*\d+\s*(puntos|ideas|sugerencias|concretos)", lower
            ) or re.search(r"listar\s+\d+\s*(puntos|ideas|sugerencias)", lower):
                continue
            p = path or "."
            if p.strip().lower() in _INVALID_PATH_TOKENS:
                p = "."
            return [Step(tool_name="list_directory", params={"path": p})]
        if tool == "edit_file":
            if path:
                return [
                    Step(
                        tool_name="edit_file",
                        params={"path": path, "action": "edit", "instruction": text},
                    )
                ]
            continue
        if tool == "project":
            proj_action = (intent.get("project_action") or "list").strip().lower()
            proj_name = (
                _rest_after_keyword(text, lower, "al proyecto")
                or _rest_after_keyword(text, lower, "proyecto")
                or _rest_after_keyword(text, lower, "proyectos")
            )
            params: Dict[str, Any] = {"action": proj_action}
            if proj_name:
                params["name"] = proj_name
            if proj_action == "create":
                params["description"] = text
            if proj_action == "add_task":
                task_title = (
                    _rest_after_keyword(text, lower, "tarea")
                    or _rest_after_keyword(text, lower, "añade")
                    or _rest_after_keyword(text, lower, "añadir")
                )
                if task_title and " al proyecto " in lower:
                    task_title = task_title.split(" al proyecto ")[0].strip()
                if task_title:
                    params["task_title"] = task_title
            steps = [Step(tool_name="project", params=params)]
            if proj_action == "advance" and proj_name:
                steps.append(
                    Step(
                        tool_name="delegate_odin",
                        params={
                            "task": "Desarrolla o desglosa la siguiente tarea del proyecto que te indico en el contexto. Responde en un tono útil y conciso.",
                            "context": "",
                        },
                    )
                )
            return steps
        if tool == "owner_system_action":
            sys_action = (intent.get("system_action") or "").strip().lower()
            if sys_action:
                return [
                    Step(
                        tool_name="owner_system_action",
                        params={"action": sys_action, "delay_seconds": 60},
                    )
                ]
            continue
        if tool == "delegate_kimi_cli":
            return [
                Step(
                    tool_name="delegate_kimi_cli", params={"task": text, "context": ""}
                )
            ]
        if tool == "lore_extractor":
            urls = _extract_urls_from_message(text)
            max_urls = 5
            if base_path:
                try:
                    from .json_safe import safe_load

                    cfg = safe_load(
                        Path(base_path) / "Config" / "planner.json", default={}
                    )
                    if isinstance(cfg, dict) and "max_urls_per_plan" in cfg:
                        max_urls = max(
                            0, min(10, int(cfg.get("max_urls_per_plan") or 5))
                        )
                except Exception:
                    pass
            if max_urls > 0 and len(urls) >= 2:
                capped = urls[:max_urls]
                steps = [
                    Step(
                        tool_name="lore_extractor",
                        params={"message": u, "store": True},
                        step_id=str(i),
                        depends_on=[],
                    )
                    for i, u in enumerate(capped)
                ]
                step_ids = [str(i) for i in range(len(capped))]
                steps.append(
                    Step(
                        tool_name="delegate_odin",
                        params={
                            "task": "Resume y sintetiza el contenido extraído de las fuentes indicadas. Si alguna fuente no está disponible, menciónalo brevemente.",
                            "context_from_steps": step_ids,
                        },
                        step_id="aggregator",
                        depends_on=step_ids,
                    )
                )
                return steps
            return [
                Step(
                    tool_name="lore_extractor", params={"message": text, "store": True}
                )
            ]

        chain = intent.get("chain")
        if isinstance(chain, list) and "read_file" in chain and "delegate_eva" in chain:
            if _looks_like_meta_question(lower) or (
                "experiencia" in lower and "discord" in lower
            ):
                continue
            # No interpretar "mejorarte" / "ideas para mejorarte" como archivo a mejorar
            if (
                "mejorarte" in lower
                or "mejorarme" in lower
                or ("ideas" in lower and "mejorar" in lower)
            ):
                continue
            p = (
                path
                or _after_keyword(text, lower, "mejora")
                or _after_keyword(text, lower, "mejorar")
            )
            if p and (
                p.strip().lower() not in _INVALID_PATH_TOKENS and len(p.strip()) > 2
            ):
                return [
                    Step(tool_name="read_file", params={"path": p}),
                    Step(
                        tool_name="delegate_eva",
                        params={
                            "task": "Explica este código y sugiere una mejora clara y concisa.",
                            "context": "El contenido del archivo se proporcionará a continuación.",
                        },
                    ),
                ]
            continue

    return None


class Planner:
    """
    Genera un plan de ejecución (lista de Steps) a partir del mensaje del usuario.
    Fase 3: consulta memoria semántica. Fase 4: si hay LearningEngine, prioriza planes aprendidos.
    """

    def __init__(
        self,
        memory_manager: Optional["MemoryManager"] = None,
        learning_engine: Optional["LearningEngine"] = None,
        local_intent_classifier: Optional["LocalIntentClassifier"] = None,
    ):
        self.memory_manager = memory_manager
        self.learning_engine = learning_engine
        self.local_intent_classifier = local_intent_classifier
        self._last_semantic_context: List[Dict[str, Any]] = []
        self._last_used_pattern_id: Optional[
            str
        ] = None  # Misión 3.2 (C.1): refuerzo procedimental
        self._last_plan_result: Optional[PlanResult] = None

    def _steps_from_category(
        self, category: str, text: str, lower: str
    ) -> Optional[List[Step]]:
        """
        Parte 4: Mapea categoría de Shalltear a lista de Steps.
        Retorna None si no hay match o si debe escalar a Kimi.
        """
        if category in ("conversacion_casual", "pregunta_sobre_lilith"):
            return [Step(tool_name="generate_reply", params={"user_message": text})]

        if category == "pc_operation":
            # Delegar a Shalltear para parsear NL a operaciones PC
            try:
                from src.core.agents.panteon.shalltear import ShalltearAgent

                _shalltear = ShalltearAgent()
                result = _shalltear.parse_nl_to_params(
                    text, operation="filesystem_batch"
                )
                if result and "operations" in result and result["operations"]:
                    steps = []
                    for op in result["operations"]:
                        intent = op.get("intent")
                        params = op.get("params", {})
                        if intent:
                            steps.append(Step(tool_name=intent, params=params))
                    if steps:
                        return steps
            except Exception:
                pass

            # Fix 2: Fallback inteligente para listado de directorios
            # Si parece un listado pero Shalltear no lo parseó, detectamos manualmente
            list_keywords = [
                "qué hay",
                "que hay",
                "lista",
                "archivos",
                "contenido",
                "qué tengo",
                "que tengo",
                "dime que",
                "dime qué",
            ]
            if any(kw in lower for kw in list_keywords):
                path = self._extract_path_for_listing(text, lower)
                if path:
                    return [Step(tool_name="pc_list", params={"path": path})]

            # Fallback: intentar heurístico simple
            return self._plan_pc_operation(text, "pc_generic")

        if category == "investigacion_web":
            return [
                Step(tool_name="delegate_odin", params={"task": text, "context": ""})
            ]

        if category == "codigo":
            return [
                Step(tool_name="delegate_adan", params={"task": text, "context": ""})
            ]

        if category == "analisis_documento":
            return [
                Step(tool_name="delegate_eva", params={"task": text, "context": ""})
            ]

        if category == "pregunta_sobre_memoria":
            return [Step(tool_name="search_semantic_memory", params={"query": text})]

        # "desconocido" o cualquier otro → escalar a Kimi/intent_patterns
        return None

    def _extract_path_for_listing(self, text: str, lower: str) -> Optional[str]:
        """Extrae ruta de carpeta específica para comandos de listado."""
        # Mapeo de aliases comunes a rutas reales
        path_aliases = {
            "descargas": r"C:\Users\Game_\Downloads",
            "downloads": r"C:\Users\Game_\Downloads",
            "escritorio": r"C:\Users\Game_\Desktop",
            "desktop": r"C:\Users\Game_\Desktop",
            "documentos": r"C:\Users\Game_\Documents",
            "documents": r"C:\Users\Game_\Documents",
            "proyectos": r"D:\Proyectos",
            "projects": r"D:\Proyectos",
            "lilith": r"D:\Proyectos\Yggdrasil\Asgard\Lilith",
        }

        # Buscar alias específicos en el texto
        for alias, real_path in path_aliases.items():
            if alias in lower:
                return real_path

        # Buscar "en X" o "de X" o "carpeta X"
        patterns = [
            r'(?:en|de|la|el|carpeta|directorio)\s+["\']?([^"\'\s]+)',
            r"(?:descargas|downloads|escritorio|desktop|documentos|documents)",
        ]

        for pattern in patterns:
            m = re.search(pattern, lower)
            if m:
                matched = m.group(1) if m.groups() else m.group(0)
                if matched in path_aliases:
                    return path_aliases[matched]
                # Si parece una ruta absoluta o relativa
                if matched and len(matched) > 1:
                    return matched

        # Default: descargas si se menciona "descargas" o "downloads"
        if "descargas" in lower or "downloads" in lower:
            return r"C:\Users\Game_\Downloads"
        if "escritorio" in lower or "desktop" in lower:
            return r"C:\Users\Game_\Desktop"
        if "documentos" in lower or "documents" in lower:
            return r"C:\Users\Game_\Documents"

        return None

    def _plan_pc_operation(self, text: str, intent: str) -> List[Step]:
        """Plan para operaciones PC (usado por Shalltear pre-filtro)."""
        # Por ahora, simplificación: si parece mover/copiar
        lower = text.lower()
        if any(v in lower for v in ("mueve", "mover", "move", "traslada")):
            return [Step(tool_name="pc_move", params={"source": "", "destination": ""})]
        if any(v in lower for v in ("copia", "copiar", "copy", "duplica")):
            return [Step(tool_name="pc_copy", params={"source": "", "destination": ""})]
        if any(v in lower for v in ("elimina", "borra", "delete", "remove")):
            return [Step(tool_name="pc_delete", params={"path": ""})]
        if any(v in lower for v in ("crea carpeta", "mkdir", "nueva carpeta")):
            return [Step(tool_name="pc_mkdir", params={"path": ""})]
        if any(v in lower for v in ("lista", "qué hay", "que hay", "ls ", "archivos")):
            # Extraer path si es posible
            path = self._extract_path_for_listing(text, lower)
            return [Step(tool_name="pc_list", params={"path": path or ""})]
        # Default: generar respuesta con info de cómo usar PC
        return [
            Step(
                tool_name="generate_reply",
                params={
                    "user_message": f"Para operaciones de archivos, usa: pc_list, pc_move, pc_copy, pc_delete, pc_mkdir. Tu mensaje: {text}"
                },
            )
        ]

    def _memory_config(self) -> Dict[str, Any]:
        """Carga Config/memory.json (E.1). Misión 3.8: prioriza Config/planner.json para use_learned_plan, use_classifier y prioridades."""
        from .json_safe import safe_load

        base = Path(__file__).resolve().parent.parent.parent
        memory_path = base / "Config" / "memory.json"
        planner_path = base / "Config" / "planner.json"
        out = safe_load(memory_path, default={})
        if not isinstance(out, dict):
            out = {}
        if planner_path.exists():
            planner = safe_load(planner_path, default={})
            if isinstance(planner, dict):
                for key in (
                    "use_learned_plan",
                    "use_classifier",
                    "plan_learned_priority",
                    "classifier_priority",
                    "rules_priority",
                ):
                    if key in planner:
                        out[key] = planner[key]
        return out

    def _fetch_preemptive_context(self, message: str) -> str:
        """
        D.10 — Preemptive retrieval: consulta MuninnDB ANTES de planear e inyecta facts/episodios
        relevantes como bloque <relevant_context>. Fallback a semántica si Muninn no disponible.
        Siempre sincrónico (usa asyncio.run si no hay loop activo); silencioso ante errores.
        """
        from pathlib import Path as _Path

        from .json_safe import safe_load

        _bp = _Path(__file__).resolve().parent.parent.parent
        cfg_planner = safe_load(_bp / "Config" / "planner.json", default={})
        pr_cfg = (cfg_planner or {}).get("preemptive_retrieval", {})
        if not pr_cfg.get("enabled", True):
            return ""
        muninn_top_k = int(pr_cfg.get("muninn_top_k", 5))
        semantic_top_k = int(pr_cfg.get("semantic_top_k", 3))
        template = pr_cfg.get(
            "context_template",
            "<relevant_context>\nRelevant facts from memory:\n{facts}\n</relevant_context>",
        )

        facts_lines: list = []

        # 1) Intentar Muninn
        try:
            import asyncio as _aio

            from .muninn_memory import MuninnMemory

            _muninn = MuninnMemory(_bp)
            if _muninn.enabled:
                try:
                    _loop = _aio.get_running_loop()
                    # Ya hay loop: no podemos blocking-run; skip Muninn (no bloqueamos)
                except RuntimeError:
                    acts = _aio.run(
                        _muninn.activate(
                            [message], vault="facts", max_results=muninn_top_k
                        )
                    )
                    for a in acts or []:
                        concept = (a.get("concept") or "").strip()[:120]
                        content = (a.get("content") or "").strip()[:200]
                        if concept or content:
                            facts_lines.append(
                                f"- {concept}: {content}" if concept else f"- {content}"
                            )
                    if facts_lines:
                        logger.info(
                            "[Planner] Preemptive retrieval: %d facts inyectados desde Muninn",
                            len(facts_lines),
                        )
        except Exception as _e:
            logger.debug("[Planner] Preemptive retrieval Muninn error: %s", _e)

        # 2) Fallback: memoria semántica local
        if not facts_lines and self.memory_manager and semantic_top_k > 0:
            try:
                sem_results = self.memory_manager.search_context(
                    message, limit=semantic_top_k
                )
                for r in sem_results or []:
                    content = (r.get("content") or r.get("text") or "").strip()[:200]
                    topic = (r.get("topic") or r.get("concept") or "").strip()[:80]
                    if content:
                        facts_lines.append(
                            f"- {topic}: {content}" if topic else f"- {content}"
                        )
                if facts_lines:
                    logger.info(
                        "[Planner] Preemptive retrieval: %d facts desde semántica (fallback)",
                        len(facts_lines),
                    )
            except Exception as _e:
                logger.debug("[Planner] Preemptive retrieval semántica error: %s", _e)

        if not facts_lines:
            return ""
        return template.format(facts="\n".join(facts_lines))

    def _fetch_attention_stack_context(self, session_id: str) -> str:
        """
        Carga tareas pendientes del attention stack para incluir en el contexto de planificación.

        Args:
            session_id: ID de la sesión (channel_id, chat_id, etc.)

        Returns:
            String formateado con las tareas pendientes, o vacío si no hay.
        """
        from pathlib import Path as _Path

        from .attention_stack import get_attention_stack, set_db_path

        _bp = _Path(__file__).resolve().parent.parent.parent
        db_path = _bp / "Data" / "attention_stack.db"

        if not db_path.exists():
            return ""

        try:
            set_db_path(db_path)
            stack = get_attention_stack(session_id)
            active_items = stack.get_active()

            if not active_items:
                return ""

            lines = ["📋 TAREAS PENDIENTES DE ESTA SESIÓN:", ""]

            priority_emoji = {
                5: "🔴",  # HIGHEST
                4: "🟠",  # HIGH
                3: "🟡",  # MEDIUM
                2: "🔵",  # LOW
                1: "⚪",  # LOWEST
            }

            status_emoji = {"pending": "⏳", "in_progress": "🔨", "blocked": "🚫"}

            for idx, item in enumerate(active_items, 1):
                prio_emoji = priority_emoji.get(item.priority, "🟡")
                status_icon = status_emoji.get(item.status, "❓")
                lines.append(f"{idx}. {status_icon} {prio_emoji} {item.description}")

            lines.append("")
            lines.append(
                "Considera completar estas tareas si el mensaje del usuario está relacionado con ellas."
            )

            return "\n".join(lines)

        except Exception as e:
            logger.debug("[Planner] Error fetching attention stack: %s", e)
            return ""

    def _maybe_batch_pc_ops(self, steps: List["Step"], text: str) -> List["Step"]:
        """
        v5.0 Auto-Batch: Intenta agrupar múltiples operaciones PC en un solo batch.
        Llama a planner_autobatch.try_auto_batch si hay 2+ operaciones PC.
        """
        if not steps or len(steps) < 2:
            return steps
        # Solo aplicar si hay operaciones PC
        pc_ops = [s for s in steps if getattr(s, "tool_name", "").startswith("pc_")]
        if len(pc_ops) < 2:
            return steps
        try:
            batched = try_auto_batch(text, steps)
            if batched and len(batched) < len(steps):
                logger.info(
                    "[Planner] Auto-Batch: %d steps → %d steps (batch)",
                    len(steps),
                    len(batched),
                )
                return batched
        except Exception as e:
            logger.debug("[Planner] Auto-Batch error (ignorando): %s", e)
        return steps

    def plan(
        self, message: str, role: str = "user", session_id: Optional[str] = None
    ) -> PlanResult:
        """
        Analiza el mensaje y devuelve una lista de pasos a ejecutar en orden.
        Si hay LearningEngine y devuelve un plan aprendido, se usa; si no, reglas por defecto.
        E.1: use_learned_plan y use_classifier desde Config/memory.json.
        D.10: preemptive retrieval de Muninn/semántica antes de planear.

        Args:
            message: Mensaje del usuario
            role: Rol del usuario (owner, trusted, public)
            session_id: ID de sesión opcional para cargar attention stack
        """
        text = (message or "").strip()
        lower = text.lower()
        logger.info(f"[DEBUG] Planner.plan START: text='{text[:80]}', role={role}")

        self._last_semantic_context = []
        self._last_plan_result = None
        self._muninn_memory_quality: float = (
            0.5  # Mejora-2: calidad de memoria para calibración
        )

        # ═══ D.10 PREEMPTIVE RETRIEVAL ═══
        # Consultar Muninn/semántica ANTES de planear para enriquecer el contexto
        self._preemptive_context: str = ""
        try:
            self._preemptive_context = self._fetch_preemptive_context(text)
        except Exception as _pe:
            logger.debug("[Planner] Preemptive retrieval fallo general: %s", _pe)

        # ═══ ATTENTION STACK CONTEXT ═══
        # Cargar tareas pendientes del attention stack si hay session_id
        self._attention_context: str = ""
        if session_id:
            try:
                self._attention_context = self._fetch_attention_stack_context(
                    session_id
                )
                if self._attention_context:
                    logger.debug(
                        "[Planner] Attention stack context cargado para sesión %s",
                        session_id,
                    )
            except Exception as _ae:
                logger.debug("[Planner] Attention stack fetch error: %s", _ae)

        # ═══ MACRO DETECTION (antes de Shalltear/intent_patterns) ═══
        # Los macros tienen prioridad para operaciones PC comunes
        if message and isinstance(message, str):
            try:
                from .pc_macros import match_macro

                macro_steps = match_macro(message)
                if macro_steps:
                    logger.info(
                        "Planner: Macro match detectado: %s",
                        [s.tool_name for s in macro_steps],
                    )
                    try:
                        from .auditor.decision_auditor import log_plan_decision

                        log_plan_decision(
                            message,
                            "pc_macro",
                            plan_generated=[s.tool_name for s in macro_steps],
                            reason="pc_macro_match",
                        )
                    except Exception:
                        pass
                    _record_matching(self, message, macro_steps)
                    # v5.0: Intentar auto-batch para operaciones PC
                    macro_steps = self._maybe_batch_pc_ops(macro_steps, message)
                    pr = _plan_to_result(macro_steps, reason="pc_macro")
                    self._last_plan_result = pr
                    return pr
            except Exception as e:
                logger.debug("Planner macro detection error: %s", e)
        if self.memory_manager:
            try:
                # H.1+H.2: búsqueda unificada (perfil + hechos + resúmenes) con pesos desde memory.json
                self._last_semantic_context = self.memory_manager.search_context(
                    message if message else "", limit=10
                )
            except Exception:
                pass
        # Mejora-2: calidad de memoria Muninn para calibrar confianza
        try:
            from pathlib import Path as _Path

            from .muninn_memory import MuninnMemory

            _bp = _Path(__file__).resolve().parent.parent.parent
            import asyncio as _aio

            try:
                _loop = _aio.get_running_loop()
                # En event loop: obtener activaciones de forma fire-and-forget (no bloqueamos plan)
                # La calidad se actualiza asíncronamente; si falla, usamos default 0.5
            except RuntimeError:
                _acts = _aio.run(
                    MuninnMemory(_bp).activate([message], vault="lilith", max_results=3)
                )
                self._muninn_memory_quality = MuninnMemory.assess_memory_quality(_acts)
        except Exception:
            pass

        if not message or not isinstance(message, str):
            logger.info(f"[DEBUG] Planner.plan: mensaje vacío o no string")
            pr = _plan_to_result(
                [_step_lucifer_conversacional(message or "")], reason="fallback"
            )
            self._last_plan_result = pr
            return pr
        cfg = self._memory_config()
        use_learned = cfg.get("use_learned_plan", True)
        use_classifier = cfg.get("use_classifier", True)

        # Fase 4: plan aprendido desde memoria procedimental (prioridad). C.3: filtro por intención.
        self._last_used_pattern_id = None
        intent_hint = _get_matched_intent_name(text)
        if use_learned and self.learning_engine:
            try:
                result = self.learning_engine.get_plan_for_message(
                    text, intent_hint=intent_hint
                )
                if result:
                    learned_plan, pattern_id = result
                    self._last_used_pattern_id = pattern_id or None
                    steps = [
                        Step(
                            tool_name=x.get("tool_name", ""),
                            params=x.get("params") or {},
                        )
                        for x in learned_plan
                    ]
                    try:
                        from .auditor.decision_auditor import log_plan_decision

                        log_plan_decision(
                            text,
                            "learned_plan",
                            plan_generated=[s.tool_name for s in steps],
                            reason="learned_plan",
                        )
                    except Exception:
                        pass
                    _record_matching(self, text, steps)
                    # v5.0: Intentar auto-batch para operaciones PC
                    steps = self._maybe_batch_pc_ops(steps, text)
                    pr = _plan_to_result(steps, reason="learned")
                    self._last_plan_result = pr
                    return pr
            except Exception:
                pass

        # Fase 4: clasificador local (solo read_file, list_directory, delegate_eva, delegate_odin; Adán no se sugiere automáticamente)
        if (
            use_classifier
            and self.local_intent_classifier
            and self.local_intent_classifier.is_available()
        ):
            try:
                tool = self.local_intent_classifier.predict(text)
                logger.info(f"[DEBUG] Planner: LocalIntentClassifier → '{tool}'")
                if tool and tool not in ("generate_reply", "delegate_adan"):
                    path = _extract_path(lower, text) or "."
                    steps = None
                    if tool == "read_file" and path and path != ".":
                        steps = [Step(tool_name="read_file", params={"path": path})]
                    elif tool == "list_directory":
                        steps = [
                            Step(tool_name="list_directory", params={"path": path})
                        ]
                    elif tool == "delegate_eva":
                        steps = [
                            Step(
                                tool_name="delegate_eva",
                                params={"task": text, "context": ""},
                            )
                        ]
                    elif tool == "delegate_odin":
                        steps = [
                            Step(
                                tool_name="delegate_odin",
                                params={"task": text, "context": ""},
                            )
                        ]
                    if steps is not None:
                        try:
                            from .auditor.decision_auditor import log_plan_decision

                            log_plan_decision(
                                text,
                                "classifier",
                                plan_generated=[s.tool_name for s in steps],
                                reason=f"classifier → {steps[0].tool_name}",
                            )
                        except Exception:
                            pass
                        _record_matching(self, text, steps)
                        pr = _plan_to_result(steps, reason="classifier")
                        self._last_plan_result = pr
                        return pr
            except Exception:
                pass

        # ═══ PRE-CHECK: Detectar operaciones PC de listado ANTES de Shalltear ═══
        # Esto evita que Shalltear clasifique erróneamente como "conversacion_casual"
        pc_list_keywords = [
            "qué hay en",
            "que hay en",
            "qué archivos",
            "que archivos",
            "archivos en",
            "lista de archivos",
            "listar archivos",
            "dime que hay",
            "dime qué hay",
            "dime los archivos",
            "muéstrame que hay",
            "muestrame que hay",
            "muéstrame los archivos",
            "muestrame los archivos",
            "contenido de",
            "qué tiene",
            "que tiene",
        ]
        pc_path_keywords = [
            "descargas",
            "downloads",
            "escritorio",
            "desktop",
            "documentos",
            "documents",
        ]

        is_pc_list_query = any(kw in lower for kw in pc_list_keywords)
        mentions_pc_path = any(kw in lower for kw in pc_path_keywords)

        if is_pc_list_query or (
            mentions_pc_path
            and ("archivos" in lower or "carpeta" in lower or "directorio" in lower)
        ):
            logger.info(f"[DEBUG] Planner: PRE-CHECK detectó consulta de listado PC")
            path = self._extract_path_for_listing(text, lower)
            if path:
                logger.info(f"[DEBUG] Planner: PRE-CHECK path resuelto='{path}'")
                steps = [Step(tool_name="pc_list", params={"path": path})]
                try:
                    from .auditor.decision_auditor import log_plan_decision

                    log_plan_decision(
                        text,
                        "pc_list_precheck",
                        plan_generated=["pc_list"],
                        reason=f"path:{path}",
                    )
                except Exception:
                    pass
                _record_matching(self, text, steps)
                # v5.0: Intentar auto-batch para operaciones PC
                steps = self._maybe_batch_pc_ops(steps, text)
                pr = _plan_to_result(steps, reason="intent_pattern")
                self._last_plan_result = pr
                return pr

        # ─── Parte 4: Pre-filtro con Shalltear (antes de intent_patterns) ──────
        try:
            from src.core.agents.panteon.shalltear import ShalltearAgent

            _shalltear = ShalltearAgent()
            if _shalltear.is_available():
                categories = [
                    "conversacion_casual",  # → generate_reply
                    "pc_operation",  # → _plan_pc_operation
                    "investigacion_web",  # → delegate_odin + web_search
                    "codigo",  # → delegate_adan
                    "analisis_documento",  # → delegate_eva
                    "pregunta_sobre_lilith",  # → generate_reply
                    "pregunta_sobre_memoria",  # → search_semantic_memory
                    "desconocido",  # → escalar a Kimi/intent_patterns
                ]
                shalltear_result = _shalltear.classify_intent(text, categories)
                logger.info(
                    f"[DEBUG] Planner: Shalltear clasificó='{shalltear_result}'"
                )
                if shalltear_result and shalltear_result != "desconocido":
                    steps = self._steps_from_category(shalltear_result, text, lower)
                    if steps:
                        logger.info(
                            f"[DEBUG] Planner: Shalltear steps generados={[s.tool_name for s in steps]}"
                        )
                        try:
                            from .auditor.decision_auditor import log_plan_decision

                            log_plan_decision(
                                text,
                                "shalltear_prefilter",
                                plan_generated=[s.tool_name for s in steps],
                                reason=f"shalltear:{shalltear_result}",
                            )
                        except Exception:
                            pass
                        _inject_preemptive_context(
                            steps,
                            getattr(self, "_preemptive_context", ""),
                            getattr(self, "_attention_context", ""),
                        )
                        _record_matching(self, text, steps)
                        # v5.0: Intentar auto-batch para operaciones PC
                        steps = self._maybe_batch_pc_ops(steps, text)
                        pr = _plan_to_result(steps, reason="shalltear")
                        self._last_plan_result = pr
                        return pr
        except Exception as e:
            logger.warning(
                f"Planner: Shalltear pre-filtro fallo ({e}), continuando con intent_patterns"
            )

        # ─── Misión 3.3: intenciones desde Config/intent_patterns.json ───────
        base_path = (
            getattr(self.memory_manager, "base_path", None)
            if self.memory_manager
            else None
        )
        if base_path is None:
            base_path = Path(__file__).resolve().parent.parent.parent
        steps = _resolve_intent_from_config(message, lower, text, base_path)
        logger.info(
            f"[DEBUG] Planner: intent_patterns → steps={[s.tool_name for s in steps] if steps else None}"
        )
        if steps is not None:
            try:
                from .auditor.decision_auditor import log_plan_decision

                matched = _get_matched_intent_name(text)
                log_plan_decision(
                    text,
                    "intent_patterns",
                    matched_intent=matched,
                    plan_generated=[s.tool_name for s in steps],
                    reason=f"intent:{matched}" if matched else "intent_patterns",
                )
            except Exception:
                pass
            _inject_preemptive_context(
                steps,
                getattr(self, "_preemptive_context", ""),
                getattr(self, "_attention_context", ""),
            )
            _record_matching(self, text, steps)
            # v5.0: Intentar auto-batch para operaciones PC
            steps = self._maybe_batch_pc_ops(steps, text)
            pr = _plan_to_result(steps, reason="intent_pattern")
            self._last_plan_result = pr
            return pr

        # ─── Misión 4.0 Fase 0: Matching Learning — sugerencia antes de fallback ───
        try:
            from .matching_learner import is_enabled as matching_enabled
            from .matching_learner import suggest as matching_suggest

            base = (
                getattr(self.memory_manager, "base_path", None)
                if self.memory_manager
                else None
            )
            if base is None:
                base = Path(__file__).resolve().parent.parent.parent
            if matching_enabled(base):
                suggestion = matching_suggest(base, text)
                if suggestion:
                    tool_name, confidence = suggestion
                    if tool_name in ("delegate_eva", "delegate_odin", "delegate_adan"):
                        # Metacognición: rechazar si hay señales negativas recientes para este tool
                        _meta_skip = False
                        try:
                            from .implicit_feedback import (
                                has_recent_negatives_for_tool as _has_neg,
                            )

                            if _has_neg(base, text, tool_name):
                                _meta_skip = True
                                try:
                                    from .auditor.decision_auditor import (
                                        log_plan_decision,
                                    )

                                    log_plan_decision(
                                        text,
                                        "matching_rejected",
                                        plan_generated=[tool_name],
                                        reason="metacognition:negative_signals",
                                    )
                                except Exception:
                                    pass
                                logger.debug(
                                    "[Planner] Plan aprendido rechazado (metacognición): %s",
                                    tool_name,
                                )
                        except Exception:
                            pass
                        if not _meta_skip:
                            step = Step(
                                tool_name=tool_name,
                                params={"task": text, "context": ""},
                            )
                            try:
                                from .auditor.decision_auditor import log_plan_decision

                                log_plan_decision(
                                    text,
                                    "matching_learning",
                                    plan_generated=[tool_name],
                                    reason=f"confidence={confidence}",
                                )
                            except Exception:
                                pass
                            _inject_preemptive_context(
                                [step],
                                getattr(self, "_preemptive_context", ""),
                                getattr(self, "_attention_context", ""),
                            )
                            _record_matching(self, text, [step])
                            pr = _plan_to_result([step], reason="matching_learning")
                            self._last_plan_result = pr
                            return pr
        except Exception as e:
            logger.debug("Planner matching_learning: %s", e)

        # ─── Fallback: Lilith directa como motor de lenguaje por defecto ───
        logger.info(
            f"[DEBUG] Planner: FALLBACK → generate_reply (no match en ninguna fase)"
        )
        try:
            from .auditor.decision_auditor import log_plan_decision

            log_plan_decision(
                text,
                "fallback_lilith",
                reason="no_intent_or_learned_plan_matched",
                plan_generated=["generate_reply"],
            )
        except Exception:
            pass
        fallback_steps = [_step_lilith_conversacional(text)]
        _inject_preemptive_context(
            fallback_steps,
            getattr(self, "_preemptive_context", ""),
            getattr(self, "_attention_context", ""),
        )
        _record_matching(self, text, fallback_steps)
        pr = _plan_to_result(fallback_steps, reason="fallback")
        self._last_plan_result = pr
        return pr
