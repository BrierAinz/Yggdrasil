"""
Fase 4.1 — Ingesta RSS/Atom con feedparser.
Obtiene entradas de cada feed y filtra por estado (solo ítems nuevos).
User-Agent personalizado (LilithBot/1.0) para reducir 429 en Reddit y ser un buen ciudadano.
Ver DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md §6.2 y §6.4.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("ingest.rss")

# User-Agent identificable: reduce rate limits (Reddit) y evita bloqueos por cliente genérico
DEFAULT_USER_AGENT = "LilithBot/1.0 (Auto-learn; RSS/Atom ingest)"

try:
    import feedparser
except ImportError:
    feedparser = None  # type: ignore


def _normalize_entry(entry: Any, feed_url: str) -> Dict[str, Any] | None:
    """Convierte una entrada feedparser a dict con id estable, content, etc."""
    if not getattr(entry, "link", None):
        return None
    # Clave estable: guid si existe, si no link
    item_key = getattr(entry, "id", None) or getattr(entry, "guid", None) or entry.link
    if not item_key:
        return None
    # Fecha: published_parsed o updated_parsed o now
    published_iso = None
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        p = getattr(entry, attr, None)
        if p and hasattr(p, "tm_year"):
            try:
                dt = datetime(*p[:6], tzinfo=timezone.utc)
                published_iso = dt.isoformat()
                break
            except Exception:
                pass
    if not published_iso:
        published_iso = datetime.now(timezone.utc).isoformat()
    # Contenido: summary o description o content[0].value
    content = ""
    if getattr(entry, "summary", None):
        content = entry.summary
    elif getattr(entry, "description", None):
        content = entry.description
    elif getattr(entry, "content", None) and len(entry.content) > 0:
        content = getattr(entry.content[0], "value", "") or ""
    title = getattr(entry, "title", None) or ""
    return {
        "source": "rss",
        "feed_url": feed_url,
        "item_key": item_key,
        "link": entry.link,
        "title": (title or "").strip(),
        "published": published_iso,
        "content": (content or "").strip()[:50000],
    }


def fetch_new_rss_items(
    feed_urls: List[str],
    state: Dict[str, Any],
    max_per_feed: int = 50,
    user_agent: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Para cada URL en feed_urls, descarga el feed con feedparser (User-Agent personalizado),
    filtra por estado (solo ítems no vistos) y devuelve lista de dicts normalizados.
    user_agent: si no se pasa, se usa DEFAULT_USER_AGENT (evita 429 en Reddit).
    """
    if not feedparser:
        logger.warning("feedparser no instalado; pip install feedparser")
        return []
    from src.core.ingest.state import mark_rss_seen, rss_key_seen

    agent = (user_agent or "").strip() or DEFAULT_USER_AGENT
    new_items: List[Dict[str, Any]] = []
    for feed_url in feed_urls:
        if not (feed_url or isinstance(feed_url, str)):
            continue
        feed_url = feed_url.strip()
        if not feed_url:
            continue
        try:
            parsed = feedparser.parse(feed_url, agent=agent)
        except Exception as e:
            logger.warning("feedparser parse %s: %s", feed_url, e)
            continue
        entries = getattr(parsed, "entries", []) or []
        count = 0
        for entry in entries:
            if count >= max_per_feed:
                break
            item = _normalize_entry(entry, feed_url)
            if not item:
                continue
            key = item["item_key"]
            if rss_key_seen(state, feed_url, key):
                continue
            new_items.append(item)
            mark_rss_seen(state, feed_url, key, item["published"])
            count += 1
    return new_items
