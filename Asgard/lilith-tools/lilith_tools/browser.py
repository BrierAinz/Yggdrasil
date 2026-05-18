"""Tool de navegacion web con Playwright (fallback a requests+regex)."""

import re
import urllib.request
from typing import Any

from lilith_tools.base import BaseTool


class BrowserTool(BaseTool):
    """Web browser tool using Playwright with automatic fallback to requests+regex.

    Fetches a URL, extracts visible text, and returns title + truncated
    content.  Prefers Playwright for JS-heavy pages; falls back to
    ``urllib.request`` scraping when Playwright is unavailable.
    """

    name = "browser"
    description = (
        "Navega a una URL y extrae texto legible. "
        "Parametros: url (str), max_chars (int, default 3000), "
        "use_playwright (bool, default True)"
    )
    parameters = {
        "url": {"type": "string", "description": "URL a visitar"},
        "max_chars": {
            "type": "integer",
            "description": "Maximo caracteres",
            "default": 3000,
        },
        "use_playwright": {
            "type": "boolean",
            "description": "Usar Playwright para renderizado JS",
            "default": True,
        },
    }

    def execute(
        self, url: str = "", max_chars: int = 3000, use_playwright: bool = True
    ) -> dict[str, Any]:
        """Navega a una URL y extrae texto legible."""
        if not url:
            return {"error": "URL vacia"}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if use_playwright:
            try:
                return self._playwright_fetch(url, max_chars)
            except Exception:
                # Fallback silencioso a requests
                pass
        return self._requests_fetch(url, max_chars)

    def _playwright_fetch(self, url: str, max_chars: int) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = page.title()
            text = page.inner_text("body")
            browser.close()
        text = re.sub(r"\s+", " ", text).strip()
        return {
            "url": url,
            "title": title or "Sin titulo",
            "text": text[:max_chars],
            "length": len(text),
            "engine": "playwright",
        }

    def _requests_fetch(self, url: str, max_chars: int) -> dict[str, Any]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            title = ""
            tm = re.search(r"<title>([^<]+)</title>", html, re.I)
            if tm:
                title = tm.group(1).strip()
            return {
                "url": url,
                "title": title or "Sin titulo",
                "text": text[:max_chars],
                "length": len(text),
                "engine": "requests",
            }
        except Exception as e:
            return {"error": str(e), "url": url}
