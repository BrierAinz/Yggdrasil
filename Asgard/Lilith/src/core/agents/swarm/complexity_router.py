"""
ComplexityRouter — Enruta tareas de código según complejidad.
Adán (Qwen 7B local) es óptimo para tareas simples/medianas.
Tareas complejas se redirigen a Eva o Odín (modelos más capaces).
"""
import logging
import re
from typing import Literal

logger = logging.getLogger("lilith.complexity_router")

# ─── Señales de alta complejidad ──────────────────────────────────────────────

# Tokens que sugieren trabajo complejo (arquitectura, refactor amplio, multi-archivo)
_COMPLEX_KEYWORDS = [
    r"\brefactor\b.*\btodo\b",  # "refactoriza todo el módulo"
    r"\barquitectura\b",
    r"\bmigra(?:r|ción)\b",
    r"\bdiseña?\b.*\bsistema\b",
    r"\boptimiza?\b.*\bbase\s+de\s+datos\b",
    r"\bmulti.?file\b",
    r"\bfull.?stack\b",
    r"\btest\s+suite\b",  # suite completa de tests
    r"\bpipeline\s+completo\b",
    r"\bendpoint.*autenticaci[oó]n\b",
    r"\bseguridad\b.*\bimplementa\b",
]

# Tokens que sugieren tarea simple (función puntual, snippet, fix pequeño)
_SIMPLE_KEYWORDS = [
    r"\bfunci[oó]n\b",
    r"\bsnippet\b",
    r"\bjson\b",
    r"\bconvierte?\b",
    r"\bcalcula?\b",
    r"\bformatea?\b",
    r"\borden[a]?\b",
    r"\bfilt(?:ra|er)\b",
    r"\bpars(?:ea|e)\b",
    r"\bfix\b",
    r"\btypo\b",
    r"\bun\s+test\b",
]

_COMPLEX_RE = [re.compile(p, re.IGNORECASE) for p in _COMPLEX_KEYWORDS]
_SIMPLE_RE = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_KEYWORDS]

# Umbral de tokens donde siempre consideramos la tarea larga (como señal heurística)
_LONG_TASK_TOKENS = 300


def classify_complexity(
    task: str, context: str = ""
) -> Literal["simple", "medium", "complex"]:
    """
    Clasifica la complejidad de una tarea de código.
    Retorna: 'simple', 'medium', 'complex'
    """
    combined = (task + " " + context).strip()
    token_count = len(combined.split())

    # Señales explícitas de complejidad alta
    complex_hits = sum(1 for r in _COMPLEX_RE if r.search(combined))
    simple_hits = sum(1 for r in _SIMPLE_RE if r.search(combined))

    if complex_hits >= 2 or token_count > _LONG_TASK_TOKENS * 2:
        return "complex"
    if complex_hits >= 1 and simple_hits == 0:
        return "complex"
    if simple_hits >= 1 and complex_hits == 0:
        return "simple"
    if token_count > _LONG_TASK_TOKENS:
        return "medium"
    return "medium"


def route_code_task(task: str, context: str = "") -> str:
    """
    Retorna el tool_name a usar según la complejidad de la tarea.
    - simple/medium → 'delegate_adan' (Qwen local, rápido)
    - complex       → 'delegate_eva' (Grok, mayor capacidad)
    """
    complexity = classify_complexity(task, context)
    logger.debug("complexity_router: '%s…' → %s", task[:60], complexity)
    if complexity == "complex":
        logger.info(
            "complexity_router: tarea compleja → delegate_eva (en lugar de delegate_adan)"
        )
        return "delegate_eva"
    return "delegate_adan"
