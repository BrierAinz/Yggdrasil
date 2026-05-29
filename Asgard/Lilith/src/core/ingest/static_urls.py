"""
Fase 4.1 — Ingesta de URLs estáticas: monitoreo de cambios por hash del contenido principal.
Limpieza de HTML con BeautifulSoup (solo texto principal, sin boilerplate) para evitar
falsos positivos por widgets, fecha en footer o rotadores de anuncios.
Atom/RSS se tratan como una sola “página” (título + resumen de entradas) para el hash.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ingest.static_urls")

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

USER_AGENT = "LilithBot/1.0 (Auto-learn; static URL monitor)"


def _extract_main_text(html: str, url: str) -> str:
    """
    Extrae solo el contenido textual principal: main, article, [role=main] o body
    sin script, style, nav, header, footer para hashear solo lo relevante.
    """
    if not BeautifulSoup or not (html or "").strip():
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find("div", class_=lambda c: c and "content" in (c or "").lower())
        )
        if main:
            return main.get_text(separator="\n", strip=True)
        body = soup.find("body")
        if body:
            for skip in ("nav", "header", "footer", "aside", "form"):
                for tag in body.find_all(skip):
                    tag.decompose()
            return body.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.debug("static_urls extract_main_text %s: %s", url[:50], e)
        return ""


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


def _fetch_url(
    url: str, user_agent: Optional[str] = None, timeout: int = 15
) -> tuple[str, str]:
    """Devuelve (content_type, body)."""
    if not requests:
        return "", ""
    headers = {"User-Agent": (user_agent or "").strip() or USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return (r.headers.get("Content-Type") or "", r.text or "")
    except Exception as e:
        logger.warning("static_urls fetch %s: %s", url[:60], e)
        return "", ""


def fetch_new_static_items(
    urls: List[str],
    state: Dict[str, Any],
    user_agent: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Para cada URL en urls_static: descarga, extrae contenido principal (HTML limpio o
    resumen Atom/RSS), hashea y compara con state. Solo devuelve ítems cuyo hash cambió.
    No confía solo en ETag: el hash es del contenido limpio para evitar boilerplate.
    """
    from src.core.ingest.state import mark_url_seen, url_content_hash_seen

    if not urls:
        return []
    agent = (user_agent or "").strip() or USER_AGENT
    new_items: List[Dict[str, Any]] = []

    for url in urls:
        if not (url or isinstance(url, str)):
            continue
        url = url.strip()
        if not url:
            continue

        content_type, body = _fetch_url(url, user_agent=agent)
        if not body:
            continue

        # Atom/RSS: tratar como una sola “página” para el hash (título + primeras entradas)
        if (
            "atom" in (content_type or "").lower()
            or "rss" in (content_type or "").lower()
            or url.endswith(".atom")
            or ".rss" in url
        ):
            try:
                import feedparser

                parsed = feedparser.parse(body, agent=agent)
                feed = getattr(parsed, "feed", None) or parsed.get("feed") or {}
                title = (
                    getattr(feed, "title", None)
                    or (feed.get("title") if isinstance(feed, dict) else None)
                    or ""
                ).strip()
                entries = (
                    getattr(parsed, "entries", None) or parsed.get("entries") or []
                )
                parts = [title]
                for e in entries[:5]:
                    ent = e if isinstance(e, dict) else {}
                    parts.append(
                        (ent.get("title") or getattr(e, "title", "") or "").strip()
                    )
                    parts.append(
                        (ent.get("link") or getattr(e, "link", "") or "").strip()
                    )
                    parts.append(
                        (
                            ent.get("summary")
                            or ent.get("description")
                            or getattr(e, "summary", "")
                            or ""
                        )[:500]
                    )
                text_to_hash = "\n".join(p for p in parts if p)
                content_preview = text_to_hash[:5000]
            except Exception as e:
                logger.debug("static_urls atom/rss parse %s: %s", url[:50], e)
                text_to_hash = body[:50000]
                content_preview = body[:5000]
        else:
            text_to_hash = _extract_main_text(body, url)
            if not text_to_hash.strip():
                text_to_hash = body[:50000]
            content_preview = (text_to_hash or body)[:5000]

        content_hash = _content_hash(text_to_hash)
        if url_content_hash_seen(state, url, content_hash):
            continue

        now = datetime.now(timezone.utc).isoformat()
        new_items.append(
            {
                "source": "url",
                "feed_url": url,
                "item_key": url,
                "link": url,
                "title": f"Actualización: {url[:80]}",
                "published": now,
                "content": content_preview,
            }
        )
        mark_url_seen(state, url, content_hash)

    return new_items
