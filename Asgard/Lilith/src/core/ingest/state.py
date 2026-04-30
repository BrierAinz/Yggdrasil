"""
Fase 4.1 — Estado de ingesta (Data/ingest_state.json).
Carga/guardado y purga de entradas RSS por antigüedad (rss_retention_days).
Ver DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md §6.2 y §6.2.1.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("ingest.state")

DEFAULT_BASE_PATH: Path | None = None


def _base_path() -> Path:
    global DEFAULT_BASE_PATH
    if DEFAULT_BASE_PATH is None:
        # Backend/core/ingest/state.py -> Core
        DEFAULT_BASE_PATH = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE_PATH


def _state_path() -> Path:
    return _base_path() / "Data" / "ingest_state.json"


def load_state() -> Dict[str, Any]:
    """Carga ingest_state.json. Si no existe, devuelve estructura vacía."""
    from src.core.json_safe import safe_load

    path = _state_path()
    raw = safe_load(path, default={})
    if not isinstance(raw, dict):
        return {"rss": {}, "folders": {}, "urls": {}}
    return {
        "rss": raw.get("rss") if isinstance(raw.get("rss"), dict) else {},
        "folders": raw.get("folders") if isinstance(raw.get("folders"), dict) else {},
        "urls": raw.get("urls") if isinstance(raw.get("urls"), dict) else {},
    }


def save_state(state: Dict[str, Any]) -> None:
    """Guarda ingest_state.json. Crea Data/ si no existe."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("ingest state save failed: %s", e)


def rss_key_seen(state: Dict[str, Any], feed_url: str, item_key: str) -> bool:
    """True si (feed_url, item_key) ya está en el estado RSS."""
    feed_data = (state.get("rss") or {}).get(feed_url)
    if not feed_data or not isinstance(feed_data, dict):
        return False
    last_seen = feed_data.get("last_seen")
    if not isinstance(last_seen, dict):
        return False
    return item_key in last_seen


def mark_rss_seen(
    state: Dict[str, Any], feed_url: str, item_key: str, seen_at: str
) -> None:
    """Añade o actualiza last_seen para (feed_url, item_key). Modifica state in-place."""
    if "rss" not in state or not isinstance(state["rss"], dict):
        state["rss"] = {}
    if feed_url not in state["rss"] or not isinstance(state["rss"][feed_url], dict):
        state["rss"][feed_url] = {"last_seen": {}, "last_run": None}
    state["rss"][feed_url]["last_seen"][item_key] = seen_at
    state["rss"][feed_url]["last_run"] = datetime.now(timezone.utc).isoformat()


def purge_rss_older_than(state: Dict[str, Any], retention_days: int) -> int:
    """
    Elimina de last_seen las entradas cuya fecha sea anterior a (now - retention_days).
    Modifica state in-place. Devuelve número de claves eliminadas.
    """
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_str = cutoff.isoformat()
    removed = 0
    for feed_url, feed_data in list((state.get("rss") or {}).items()):
        if not isinstance(feed_data, dict):
            continue
        last_seen = feed_data.get("last_seen")
        if not isinstance(last_seen, dict):
            continue
        for key, date_str in list(last_seen.items()):
            if isinstance(date_str, str) and date_str < cutoff_str:
                del last_seen[key]
                removed += 1
    if removed:
        logger.debug(
            "ingest state: purged %d RSS entries older than %d days",
            removed,
            retention_days,
        )
    return removed


def url_content_hash_seen(state: Dict[str, Any], url: str, content_hash: str) -> bool:
    """True si la URL ya está en estado con el mismo content_hash (contenido no cambió)."""
    urls_data = state.get("urls") or {}
    if not isinstance(urls_data, dict):
        return False
    entry = urls_data.get(url)
    if not entry or not isinstance(entry, dict):
        return False
    return (entry.get("content_hash") or "") == content_hash


def mark_url_seen(state: Dict[str, Any], url: str, content_hash: str) -> None:
    """Registra la URL con content_hash y last_run. Modifica state in-place."""
    if "urls" not in state or not isinstance(state["urls"], dict):
        state["urls"] = {}
    from datetime import datetime, timezone

    state["urls"][url] = {
        "content_hash": content_hash,
        "last_run": datetime.now(timezone.utc).isoformat(),
    }
