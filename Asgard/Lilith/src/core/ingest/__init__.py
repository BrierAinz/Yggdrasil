"""
Fase 4.1 — Ingesta de fuente constante (RSS, carpetas, URLs).
Estado en Data/ingest_state.json; purga por rss_retention_days.
Ver Core/Docs/DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md.
"""
from .rss import fetch_new_rss_items
from .runner import _load_config as load_fuentes_config
from .runner import run_ingest
from .state import (
    load_state,
    mark_rss_seen,
    mark_url_seen,
    purge_rss_older_than,
    rss_key_seen,
    save_state,
    url_content_hash_seen,
)
from .static_urls import fetch_new_static_items

__all__ = [
    "load_state",
    "save_state",
    "purge_rss_older_than",
    "rss_key_seen",
    "mark_rss_seen",
    "url_content_hash_seen",
    "mark_url_seen",
    "fetch_new_rss_items",
    "fetch_new_static_items",
    "run_ingest",
    "load_fuentes_config",
]
