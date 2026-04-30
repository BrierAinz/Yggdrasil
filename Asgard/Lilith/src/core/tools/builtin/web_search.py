import json
import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

from .base import ToolV3
from .protocol import ToolResult

logger = logging.getLogger("WebSearchTool")


_DEFAULT_BLACKLIST = (
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "instagram.com",
    "tiktok.com",
    "facebook.com",
    "x.com",
    "twitter.com",
)


def _domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc.split(":")[0]
    except Exception:
        return ""


def _is_blacklisted(url: str, blacklist: List[str]) -> bool:
    d = _domain(url)
    if not d:
        return True
    for b in blacklist:
        b = (b or "").strip().lower()
        if not b:
            continue
        if d == b or d.endswith("." + b):
            return True
    return False


class WebSearchTool(ToolV3):
    name = "web_search"
    description = "Busca en la web (DuckDuckGo) y devuelve 3-5 resultados con título, snippet y URL."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "query": "Texto a buscar (obligatorio).",
            "max_results": "Máximo de resultados (por defecto 5).",
            "blacklist": "Lista opcional de dominios a descartar.",
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        query = (params.get("query") or params.get("q") or "").strip()
        if not query:
            return {
                "response": json.dumps(
                    {"query": "", "results": [], "error": {"code": "missing_query"}},
                    ensure_ascii=False,
                )
            }

        try:
            max_results = int(params.get("max_results") or 5)
        except Exception:
            max_results = 5
        max_results = max(1, min(5, max_results))

        blacklist = params.get("blacklist")
        if isinstance(blacklist, list) and blacklist:
            bl = [str(x) for x in blacklist if x]
        else:
            bl = list(_DEFAULT_BLACKLIST)

        try:
            # duckduckgo_search es síncrono; encaja con tools en ThreadPool.
            try:
                # Nuevo nombre recomendado por el proyecto.
                from ddgs import DDGS  # type: ignore
            except Exception:
                from duckduckgo_search import DDGS  # type: ignore

            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results + 5):
                    url = (r.get("href") or r.get("url") or "").strip()
                    title = (r.get("title") or "").strip()
                    snippet = (r.get("body") or r.get("snippet") or "").strip()
                    if not url or not url.startswith("http"):
                        continue
                    if _is_blacklisted(url, bl):
                        continue
                    results.append({"title": title, "url": url, "snippet": snippet})
                    if len(results) >= max_results:
                        break

            payload: Dict[str, Any] = {"query": query, "results": results}
            return {"response": json.dumps(payload, ensure_ascii=False)}
        except Exception as e:
            msg = str(e)
            code = "search_failed"
            if "rate" in msg.lower() or "429" in msg:
                code = "rate_limited"
            payload = {
                "query": query,
                "results": [],
                "error": {
                    "code": code,
                    "hint": "Espera 30-60s o reformula la búsqueda.",
                    "detail": msg[:300],
                },
            }
            logger.warning("web_search failed: %s", msg)
            return {"response": json.dumps(payload, ensure_ascii=False)}
