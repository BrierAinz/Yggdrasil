"""
Lilith 4.0 — LoreExtractorTool (Lore-Seeker).
Extrae contenido de APIs de wikis (MediaWiki) y Reddit (.json), sin pasar por ContentCleaner.
Dos modos: mediawiki (mitología, worldbuilding) y reddit (diseño de juegos, experiencias).
"""
import hashlib
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional

from .protocol import LilithTool, ToolResult

logger = logging.getLogger("LoreExtractorTool")

_REDDIT_UA = "LilithLoreSeeker/1.0 (Lilith 4.0; lore extraction)"
_REDDIT_MIN_GAP = 2.0
_LAST_REDDIT_REQUEST: float = 0.0
_REDDIT_LOCK = threading.Lock()

# Fallback si no existe Config/topic_routes.json
_DEFAULT_TOPIC_ROUTES: Dict[str, Dict[str, str]] = {
    "subreddits": {
        "worldbuilding": "rol_lore",
        "gamedev": "gamedev",
        "gamedesign": "gamedev",
    },
    "hosts": {
        "godofwar.fandom.com": "mitologia",
        "elderscrolls.fandom.com": "rol_lore",
    },
}


def _load_topic_routes(base_path: Optional[Any]) -> Dict[str, Dict[str, str]]:
    """Carga Config/topic_routes.json; si no existe, devuelve _DEFAULT_TOPIC_ROUTES."""
    if not base_path:
        return _DEFAULT_TOPIC_ROUTES
    try:
        from pathlib import Path

        from ..json_safe import safe_load

        path = Path(base_path) / "Config" / "topic_routes.json"
        if not path.exists():
            return _DEFAULT_TOPIC_ROUTES
        data = safe_load(path, default={})
        if not isinstance(data, dict):
            return _DEFAULT_TOPIC_ROUTES
        sub = data.get("subreddits")
        hosts = data.get("hosts")
        return {
            "subreddits": sub
            if isinstance(sub, dict)
            else _DEFAULT_TOPIC_ROUTES["subreddits"],
            "hosts": hosts
            if isinstance(hosts, dict)
            else _DEFAULT_TOPIC_ROUTES["hosts"],
        }
    except Exception:
        return _DEFAULT_TOPIC_ROUTES


def _resolve_topic(
    mode: str,
    url: str = "",
    wiki_base: str = "",
    routes: Optional[Dict[str, Dict[str, str]]] = None,
) -> Optional[str]:
    """Resuelve topic desde URL/wiki_base usando topic_routes (subreddits o hosts)."""
    if not routes:
        routes = _DEFAULT_TOPIC_ROUTES
    if mode == "reddit" and url:
        m = re.search(r"reddit\.com/r/([a-zA-Z0-9_]+)", url, re.IGNORECASE)
        if m:
            sub = m.group(1).lower()
            topic = (routes.get("subreddits") or {}).get(sub)
            if topic:
                return topic
    if mode == "mediawiki" and wiki_base:
        from urllib.parse import urlparse

        parsed = urlparse(wiki_base)
        host = (parsed.netloc or "").strip().lower()
        if host:
            topic = (routes.get("hosts") or {}).get(host)
            if topic:
                return topic
    return None


def _strip_html(html: str) -> str:
    """
    Extrae texto plano del HTML de MediaWiki eliminando infoboxes, navboxes, TOC y tablas
    que colapsarían en ruido (ej. "Fuerza 18 Destreza 14..."). Preserva el cuerpo narrativo.
    """
    if not html or not html.strip():
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    soup = BeautifulSoup(html, "html.parser")
    # Eliminar bloques que contaminan la densidad semántica (clases típicas de MediaWiki/Fandom)
    for selector in (
        ".infobox",
        ".infoboxes",
        ".navbox",
        ".navbox-inner",
        ".toc",
        "#toc",
        ".wikitable",
        "table.ambox",
        ".reference",
        "ol.references",
        "sup.reference",
        ".citation",
        ".metadata",
        "table.metadata",
    ):
        for node in soup.select(selector):
            node.decompose()
    # Referencias [1], [2] en sup o span que suelen quedar como texto
    for tag in soup.find_all(["sup", "span"], class_=re.compile(r"reference", re.I)):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    return text.strip()


def _mediawiki_extract(
    base_url: str, title: str, timeout: int = 25, full_page: bool = True
) -> tuple[str, str, str]:
    """
    Extrae texto plano de una página MediaWiki.
    full_page=True: usa action=parse&prop=text para artículo completo (sin truncamiento de extracts).
    full_page=False: usa prop=extracts&explaintext=1 (puede truncar artículos largos).
    Devuelve (texto_plano, source_id, title_used).
    """
    import urllib.parse

    try:
        import requests
    except ImportError:
        return "", "", title

    api = base_url.rstrip("/") + "/api.php"
    headers = {"User-Agent": _REDDIT_UA}

    if full_page:
        # Parse API: contenido completo en HTML; luego strip para texto plano (evita límite de extracts)
        params = {"action": "parse", "page": title, "prop": "text", "format": "json"}
        qs = urllib.parse.urlencode(params)
        url = f"{api}?{qs}"
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("LoreExtractor MediaWiki parse failed: %s", e)
            full_page = False
        if full_page:
            parse = data.get("parse") or {}
            raw_html = (parse.get("text") or {}).get("*") or ""
            if raw_html:
                text = _strip_html(raw_html)
                if text:
                    sid = hashlib.sha256(
                        f"{base_url}:{title}".encode("utf-8")
                    ).hexdigest()[:16]
                    title_used = parse.get("title") or title
                    return text, sid, title_used

    # Fallback: prop=extracts (puede truncar; iterar continue si hay múltiples páginas)
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "exintro": 0,
        "titles": title,
        "format": "json",
    }
    all_extracts: List[str] = []
    while True:
        qs = urllib.parse.urlencode(params)
        url = f"{api}?{qs}"
        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.warning("LoreExtractor MediaWiki query failed: %s", e)
            break
        query = data.get("query") or {}
        pages = query.get("pages") or {}
        for _pid, page in pages.items():
            ext = (page.get("extract") or "").strip()
            if ext:
                all_extracts.append(ext)
        cont = data.get("continue")
        if not cont or not isinstance(cont, dict):
            break
        params = dict(params)
        params.update(cont)
    if all_extracts:
        text = "\n\n".join(all_extracts)
        sid = hashlib.sha256(f"{base_url}:{title}".encode("utf-8")).hexdigest()[:16]
        title_used = next((p.get("title") or title for _, p in pages.items()), title)
        return text, sid, title_used
    return "", "", title


def _reddit_get(
    json_url: str, timeout: int = 20, max_retries: int = 3
) -> Optional[Any]:
    """
    GET con respeto a rate limit: gap mínimo entre peticiones y reintentos con backoff en 429.
    _REDDIT_LOCK evita condiciones de carrera si el PlanExecutor ejecuta pasos en paralelo (DAG).
    """
    global _LAST_REDDIT_REQUEST
    try:
        import requests
    except ImportError:
        return None
    headers = {"User-Agent": _REDDIT_UA}
    for attempt in range(max_retries):
        with _REDDIT_LOCK:
            gap = _REDDIT_MIN_GAP - (time.time() - _LAST_REDDIT_REQUEST)
            if gap > 0:
                time.sleep(gap)
            _LAST_REDDIT_REQUEST = time.time()
        try:
            r = requests.get(json_url, timeout=timeout, headers=headers)
            if r.status_code == 429:
                wait = (2**attempt) + 1
                logger.warning(
                    "LoreExtractor Reddit 429, retry in %ss (attempt %d)",
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("LoreExtractor Reddit request failed: %s", e)
            if attempt + 1 < max_retries:
                time.sleep(2**attempt)
            return None
    return None


def _reddit_extract(
    url: str, max_top_comments: int = 15, timeout: int = 20
) -> tuple[str, str, Dict[str, Any]]:
    """
    GET Reddit URL + .json, extrae post y comentarios de nivel superior.
    Usa _reddit_get para rate limit y backoff en 429.
    """
    json_url = url if url.strip().endswith(".json") else url.rstrip("/") + ".json"
    listing = _reddit_get(json_url, timeout=timeout)
    if listing is None:
        return "", "", {}

    if not isinstance(listing, list) or len(listing) < 1:
        return "", "", {}

    # [0] = post, [1] = comments
    post_data = listing[0].get("data", {}).get("children", [])
    if not post_data:
        return "", "", {}
    post = post_data[0].get("data", {})
    title = post.get("title") or ""
    selftext = (post.get("selftext") or "").strip()
    post_id = post.get("id") or ""
    source_id = (
        f"reddit_{post_id}"
        if post_id
        else hashlib.sha256(json_url.encode()).hexdigest()[:16]
    )
    metadata = {
        "post_score": post.get("score"),
        "post_author": post.get("author"),
        "subreddit": post.get("subreddit"),
    }

    parts = [f"# {title}", ""]
    if selftext:
        parts.append(selftext)
        parts.append("")

    # Top-level comments from second element of listing
    if len(listing) > 1:
        comment_children = listing[1].get("data", {}).get("children", [])
        count = 0
        for child in comment_children:
            if count >= max_top_comments:
                break
            data = child.get("data", {})
            if data.get("kind") == "more":
                continue
            body = (data.get("body") or "").strip()
            if not body or data.get("depth", 0) > 1:
                continue
            # Solo texto puro en el cuerpo guardado; score queda en metadata para posible ranking futuro
            parts.append(body)
            parts.append("")
            count += 1

    text = "\n".join(parts).strip()
    return text, source_id, metadata


class LoreExtractorTool(LilithTool):
    """
    Extrae lore y discusiones de MediaWiki (Fandom) y Reddit vía API/JSON.
    No usa ContentCleaner; los datos ya vienen limpios.
    Por defecto guarda en memoria semántica con source_id; opción store=False devuelve solo el texto.
    """

    def __init__(self, base_path: Optional[Any] = None):
        self._base_path = base_path

    @property
    def name(self) -> str:
        return "lore_extractor"

    def get_description(self) -> str:
        return (
            "Extrae contenido de wikis (MediaWiki/Fandom) o de hilos de Reddit usando APIs/JSON. "
            "Modos: mediawiki (mitología, worldbuilding) o reddit (diseño de juegos, experiencias). "
            "Guarda el texto en memoria semántica con source_id; no pasa por ContentCleaner."
        )

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "description": "mediawiki | reddit"},
                "url": {
                    "type": "string",
                    "description": "URL del hilo (Reddit) o no usado si mode=mediawiki.",
                },
                "wiki_base": {
                    "type": "string",
                    "description": "Base URL del wiki (ej. https://godofwar.fandom.com) para mode=mediawiki.",
                },
                "title": {
                    "type": "string",
                    "description": "Título de la página wiki (mediawiki) o ignorado (reddit).",
                },
                "store": {
                    "type": "boolean",
                    "description": "Si true (default), guarda en memoria semántica; si false, solo devuelve el texto.",
                },
                "max_reddit_comments": {
                    "type": "integer",
                    "description": "Máximo de comentarios de nivel superior a incluir (default 15).",
                },
                "topic": {
                    "type": "string",
                    "description": "Taxonomía opcional; si no se pasa, se infiere de URL/subreddit/host vía Config/topic_routes.json.",
                },
                "structurer_before_store": {
                    "type": "boolean",
                    "description": "Si true, se ejecuta DataStructurerAgent sobre el texto y se guarda bloque de metadatos (tópico, resumen, conceptos) + '---' + texto original intacto.",
                },
            },
            "required": ["mode"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        mode = (params.get("mode") or "").strip().lower()
        store = params.get("store", True)
        message = (
            params.get("message") or params.get("context") or params.get("task") or ""
        ).strip()

        # Heurística: si no hay mode/url/wiki_base, intentar extraer del mensaje
        if not mode and message:
            url_match = re.search(r"https?://[^\s\)\]\"]+", message)
            if url_match:
                url = url_match.group(0).rstrip(".,;:")
                if "reddit.com" in url:
                    mode = "reddit"
                    params = dict(params)
                    params["url"] = url
                elif "fandom.com" in url or "wiki" in url.lower():
                    mode = "mediawiki"
                    params = dict(params)
                    from urllib.parse import urlparse

                    parsed = urlparse(url)
                    params["wiki_base"] = f"{parsed.scheme}://{parsed.netloc}"
                    path = (parsed.path or "").strip("/")
                    params["title"] = (
                        path.replace("/wiki/", "").replace("wiki/", "").split("/")[-1]
                        or "Main_Page"
                    )

        if mode not in ("mediawiki", "reddit"):
            return {
                "response": "Indica mode: 'mediawiki' o 'reddit', o escribe una URL de Reddit o Fandom para detectarla.",
                "error": True,
            }

        text = ""
        source_id = ""
        title_used = ""
        metadata: Dict[str, Any] = {}

        if mode == "mediawiki":
            wiki_base = (params.get("wiki_base") or "").strip()
            title = (params.get("title") or "").strip()
            if not wiki_base or not title:
                return {
                    "response": "Para mode=mediawiki indica wiki_base y title (o una URL de Fandom en el mensaje).",
                    "error": True,
                }
            text, source_id, title_used = _mediawiki_extract(wiki_base, title)
            if not text:
                return {
                    "response": f"No se pudo extraer contenido de la wiki para '{title}'.",
                    "error": False,
                }
        else:
            url = (params.get("url") or "").strip()
            if not url:
                return {
                    "response": "Para mode=reddit indica url del hilo (o una URL de Reddit en el mensaje).",
                    "error": True,
                }
            max_comments = max(0, min(50, int(params.get("max_reddit_comments") or 15)))
            text, source_id, metadata = _reddit_extract(
                url, max_top_comments=max_comments
            )
            if not text:
                return {
                    "response": "No se pudo extraer contenido del hilo de Reddit.",
                    "error": False,
                }

        topic = (params.get("topic") or "").strip() or None
        if not topic:
            routes = _load_topic_routes(self._base_path)
            topic = _resolve_topic(
                mode,
                url=(params.get("url") or "").strip(),
                wiki_base=(params.get("wiki_base") or "").strip(),
                routes=routes,
            )
        text_to_store = text
        if params.get("structurer_before_store") and text and self._base_path:
            try:
                from pathlib import Path

                from ..data_structurer_agent import DataStructurerAgent

                root = Path(self._base_path)
                if root.exists():
                    structurer = DataStructurerAgent(root)
                    out = structurer.execute({"context": text})
                    if not out.get("error") and out.get("response"):
                        text_to_store = out["response"].strip() + "\n\n---\n\n" + text
            except Exception as e:
                logger.warning("LoreExtractor structurer step failed: %s", e)
        if store and text_to_store and self._base_path:
            from pathlib import Path

            from ..memory import MemoryManager

            root = Path(self._base_path)
            if root.exists():
                try:
                    manager = MemoryManager(root)
                    manager.add_fact(
                        text_to_store, source_id=source_id or None, topic=topic
                    )
                except Exception as e:
                    logger.warning("LoreExtractor store failed: %s", e)

        preview = text[:600] + "…" if len(text) > 600 else text
        mode_label = "MediaWiki" if mode == "mediawiki" else "Reddit"
        msg = f"[Lore-Seeker] Extraído ({mode_label}, source_id={source_id or 'n/a'})."
        if metadata:
            msg += f" Metadatos: {metadata}"
        msg += f"\n\nVista previa:\n{preview}"
        out = {
            "response": msg,
            "source_id": source_id,
            "title": title_used or None,
            "metadata": metadata,
        }
        try:
            from urllib.parse import urlparse

            if mode == "reddit":
                url_used = (params.get("url") or "").strip()
                if url_used:
                    out["url"] = url_used
                    out["domain"] = urlparse(url_used).netloc or "reddit.com"
            else:
                wiki_base = (params.get("wiki_base") or "").strip()
                if wiki_base and title_used:
                    base = wiki_base.rstrip("/")
                    out["url"] = (
                        f"{base}/wiki/{title_used}"
                        if "/wiki/" not in base
                        else f"{base}/{title_used}"
                    )
                    out["domain"] = urlparse(wiki_base).netloc or ""
        except Exception:
            pass
        return out
