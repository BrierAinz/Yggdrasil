"""
Fase 4.3 — Job de auto-aprendizaje: ingesta + clasificación + cuaderno; acciones peligrosas → confirmación.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("auto_learn.job")

DEFAULT_BASE_PATH: Path | None = None


def _base_path() -> Path:
    global DEFAULT_BASE_PATH
    if DEFAULT_BASE_PATH is None:
        DEFAULT_BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE_PATH


def _load_auto_learn_config(base_path: Path) -> Dict[str, Any]:
    from src.core.json_safe import safe_load

    p = base_path / "Config" / "auto_learn.json"
    raw = safe_load(p, default={})
    return raw if isinstance(raw, dict) else {}


def run_auto_learn_job(base_path: Path | None = None) -> Dict[str, Any]:
    """
    Ejecuta una pasada del modo auto-aprendizaje:
    1. Lee auto_learn.json; si auto_learn_enabled no es true, retorna sin hacer nada.
    2. Ejecuta ingesta (run_ingest) para obtener ítems nuevos.
    3. Clasifica cada ítem (importante / no) con clasificador en dos fases.
    4. Guarda en cuaderno (notebook_add) con el flag important.
    5. Opcionalmente para ítems importantes: add_fact en memoria semántica (acción segura).
    6. Si en el futuro se genera un plan con pasos peligrosos, se crea confirmación y se notifica al owner por DM (bot polling).

    Retorna un dict con: ran: bool, new_items: int, notebook_added: int, errors: list.
    """
    base_path = base_path or _base_path()
    config = _load_auto_learn_config(base_path)
    if not config.get("auto_learn_enabled"):
        return {
            "ran": False,
            "reason": "disabled",
            "new_items": 0,
            "notebook_added": 0,
            "errors": [],
        }

    from src.core.auto_learn.classifier import classify_items
    from src.core.ingest import run_ingest
    from src.core.notebook import notebook_add

    result = {"ran": True, "new_items": 0, "notebook_added": 0, "errors": []}

    try:
        new_items = run_ingest(base_path, store_to_notebook_override=False)
    except Exception as e:
        logger.warning("auto_learn ingest failed: %s", e)
        result["errors"].append(f"ingest: {e}")
        return result

    result["new_items"] = len(new_items)
    if not new_items:
        return result

    # Normalizar a formato con content/title para el clasificador
    for it in new_items:
        if "content" not in it and "title" in it:
            it["content"] = (it.get("title") or "") + "\n\n" + (it.get("content") or "")
        it.setdefault("tags", [])

    try:
        classified = classify_items(new_items, base_path=base_path)
    except Exception as e:
        logger.warning("auto_learn classify failed: %s", e)
        result["errors"].append(f"classify: {e}")
        classified = new_items
        for x in classified:
            x.setdefault("important", False)

    for item in classified:
        try:
            content = (item.get("content") or item.get("title") or "").strip()
            if not content:
                continue
            source = item.get("source") or "rss"
            source_detail = (
                item.get("link")
                or item.get("feed_url")
                or item.get("source_detail")
                or ""
            ).strip()
            important = bool(item.get("important"))
            notebook_add(
                content=content[:50000],
                important=important,
                source=source,
                source_detail=source_detail,
                tags=item.get("tags") or [],
                base_path=base_path,
            )
            result["notebook_added"] += 1
            if important:
                try:
                    from src.core.memory import MemoryManager

                    mm = MemoryManager(base_path)
                    mm.add_fact(content[:2000], topic="auto_learn")
                except Exception:
                    pass
        except Exception as e:
            result["errors"].append(str(e)[:200])

    return result
