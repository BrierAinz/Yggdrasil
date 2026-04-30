"""
Fase 4.1 — Orquestador de ingesta: config, estado, purga y RSS.
Devuelve solo ítems nuevos; opcionalmente se puede conectar después al cuaderno (4.2).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import rss as ingest_rss
from . import state as ingest_state
from . import static_urls as ingest_static

logger = logging.getLogger("ingest.runner")

DEFAULT_BASE_PATH: Path | None = None


def _base_path() -> Path:
    global DEFAULT_BASE_PATH
    if DEFAULT_BASE_PATH is None:
        DEFAULT_BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE_PATH


def _load_config(base_path: Path | None = None) -> Dict[str, Any]:
    from src.core.json_safe import safe_load

    base_path = base_path or _base_path()
    path = base_path / "Config" / "fuentes_constantes.json"
    raw = safe_load(path, default={})
    return raw if isinstance(raw, dict) else {}


def run_ingest(
    base_path: Path | None = None, store_to_notebook_override: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Ejecuta una pasada de ingesta:
    1. Carga Config/fuentes_constantes.json y Data/ingest_state.json.
    2. Purga entradas RSS más antiguas que rss_retention_days.
    3. Para cada feed en rss_feeds, obtiene ítems nuevos (no vistos en estado).
    4. Actualiza estado con los vistos y guarda ingest_state.json.
    5. Devuelve la lista de ítems nuevos (cada uno: source, feed_url, item_key, link, title, published, content).

    Carpetas y URLs estáticas (4.1) se pueden añadir después; por ahora solo RSS.
    """
    base_path = base_path or _base_path()
    config = _load_config(base_path)
    if not config.get("enabled", True):
        logger.debug("ingest disabled in config")
        return []

    state = ingest_state.load_state()
    retention_days = int(config.get("rss_retention_days") or 30)
    ingest_state.purge_rss_older_than(state, retention_days)

    feed_urls = config.get("rss_feeds") or []
    if not isinstance(feed_urls, list):
        feed_urls = [feed_urls] if feed_urls else []
    max_items_per_run = int(config.get("max_items_per_run") or 20)
    max_per_feed = (
        max(5, max_items_per_run // max(1, len(feed_urls))) if feed_urls else 50
    )

    user_agent = (config.get("rss_user_agent") or "").strip() or None
    new_items = ingest_rss.fetch_new_rss_items(
        feed_urls,
        state,
        max_per_feed=max_per_feed,
        user_agent=user_agent,
    )

    # URLs estáticas: hash del contenido principal (HTML limpio o Atom) para evitar boilerplate
    urls_static = config.get("urls_static") or []
    if isinstance(urls_static, list) and urls_static:
        try:
            static_items = ingest_static.fetch_new_static_items(
                [u for u in urls_static if isinstance(u, str) and (u or "").strip()],
                state,
                user_agent=user_agent,
            )
            new_items = new_items + static_items
        except Exception as e:
            logger.debug("ingest static_urls: %s", e)

    # Limitar al tope global por run
    new_items = new_items[:max_items_per_run]

    ingest_state.save_state(state)

    # Fase 4.2: opcionalmente guardar ítems nuevos en el cuaderno (important=False). Si store_to_notebook_override is False (ej. llamado desde auto_learn job), no guardar aquí (el job clasifica y añade).
    do_store = (
        store_to_notebook_override
        if store_to_notebook_override is not None
        else (
            config.get("on_new_content") == "classify_and_store"
            or config.get("store_to_notebook")
        )
    )
    if new_items and do_store:
        try:
            from src.core.notebook import notebook_add

            for item in new_items:
                content = (item.get("title") or "").strip()
                body = (item.get("content") or "").strip()
                if body:
                    content = f"{content}\n\n{body}" if content else body
                if content:
                    notebook_add(
                        content=content[:50000],
                        important=False,
                        source="rss",
                        source_detail=item.get("link") or item.get("feed_url") or "",
                        tags=[],
                        base_path=base_path,
                    )
        except Exception as e:
            logger.debug("ingest: notebook_add skip: %s", e)

    if new_items:
        logger.info("ingest: %d new item(s) from RSS", len(new_items))
    return new_items
