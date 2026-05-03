"""Tool de busqueda web usando DuckDuckGo HTML (sin API key)."""

import re
import urllib.parse
import urllib.request
from typing import Any

from lilith_tools.base import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Busca en la web usando DuckDuckGo. Parametros: query (str), max_results (int, default 5)"
    )
    parameters = {
        "query": {"type": "string", "description": "Termino de busqueda"},
        "max_results": {
            "type": "integer",
            "description": "Maximo resultados",
            "default": 5,
        },
    }

    def execute(self, query: str = "", max_results: int = 5) -> dict[str, Any]:
        if not query:
            return {"error": "Query vacia"}
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            results = []
            for m in re.finditer(
                r'<a rel="nofollow" class="result__a" href="([^"]+)">([^<]+)</a>', html
            ):
                if len(results) >= max_results:
                    break
                href = m.group(1)
                title = re.sub(r"<[^>]+>", "", m.group(2))
                results.append({"title": title, "url": href})

            return {"query": query, "results": results, "count": len(results)}
        except Exception as e:
            return {"error": str(e), "query": query}
