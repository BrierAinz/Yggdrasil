"""
Fase 4.3 — Clasificación en dos fases (§6.1): heurística primero, LLM opcional con tope.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("auto_learn.classifier")

DEFAULT_BASE_PATH: Path | None = None


def _base_path() -> Path:
    global DEFAULT_BASE_PATH
    if DEFAULT_BASE_PATH is None:
        DEFAULT_BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE_PATH


def _load_notebook_config(base_path: Path) -> Dict[str, Any]:
    from src.core.json_safe import safe_load

    p = base_path / "Config" / "notebook.json"
    raw = safe_load(p, default={})
    return raw if isinstance(raw, dict) else {}


def heuristic_important(content: str, tags: List[str], config: Dict[str, Any]) -> bool:
    """
    Criba local: True si el contenido/tags contienen suficientes keywords de importante.
    content: texto a clasificar; tags: etiquetas opcionales.
    """
    if not (content or "").strip():
        return False
    keywords = config.get("important_keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    text = (content or "").lower() + " " + " ".join((tags or [])).lower()
    hits = sum(1 for k in keywords if (k or "").lower() in text)
    # Umbral: al menos 1 keyword o longitud mínima con 2+ keywords
    min_keywords = 1
    return hits >= min_keywords


def classify_items(
    items: List[Dict[str, Any]],
    base_path: Path | None = None,
    mode: str = "heuristic_then_llm",
    max_llm: int = 10,
) -> List[Dict[str, Any]]:
    """
    Para cada ítem añade "important": bool.
    mode: heuristic_only | heuristic_then_llm | llm_only.
    max_llm: máximo de ítems a refinar con LLM cuando mode incluye llm.
    """
    base_path = base_path or _base_path()
    config = _load_notebook_config(base_path)
    mode = (config.get("classification_mode") or mode or "heuristic_then_llm").strip()
    max_llm = int(config.get("max_llm_classifications_per_run") or max_llm or 10)

    out = []
    for item in items:
        content = (item.get("content") or item.get("title") or "").strip()
        tags = item.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        important = heuristic_important(content, tags, config)
        out.append({**item, "important": important})

    if mode == "heuristic_only":
        return out

    # Refino con LLM solo para los que pasaron criba (o sample)
    to_refine = [x for x in out if x.get("important")][:max_llm]
    if not to_refine:
        return out

    try:
        # Parte 2: Shalltear reemplaza a Kimi/Odin para scoring de importancia
        from src.core.agents.panteon.shalltear import ShalltearAgent

        shalltear = ShalltearAgent()
        if not shalltear.is_available():
            logger.debug("Shalltear no disponible, usando heurístico solo")
            return out

        for x in to_refine:
            content = (x.get("content") or x.get("title") or "")[:1500]
            try:
                score = shalltear.score_importance(content)
                # Score 0-10: >= 7 es importante
                x["important"] = score >= 7
                logger.debug(
                    "Shalltear scored importance: %d -> %s", score, x["important"]
                )
            except Exception as e:
                logger.debug("Shalltear scoring skip: %s", e)
        try:
            from src.core.auditor.decision_auditor import append_decision

            append_decision(
                decision_type="classify_important",
                actor="classifier",
                payload={"items_refined": len(to_refine), "mode": mode},
                reason="heuristic_then_llm",
            )
        except Exception:
            pass
    except Exception as e:
        logger.debug("auto_learn classifier LLM phase: %s", e)

    return out
