"""
Lilith 4.2 — WebScraperAgent: agente de dominio para extraer texto de URLs.

Extrae el contenido textual principal de una página web con múltiples estrategias:
- full_page: HTML completo
- article_only: Contenido principal (usando readability)
- structured_data: Datos estructurados (JSON-LD, microdata)

Config: dominios permitidos, timeout y rate limiting en Config/web_sources.json.
Salida: ScrapedContent listo para ContentCleanerAgent.
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from .agent_registry import Agent
from .tools_v3.protocol import ToolResult
from .web_mining_models import ScrapedContent, ScrapingStrategy, get_strategy_for_source

logger = logging.getLogger("WebScraperAgent")

# Regex para detectar URL en un mensaje
_URL_RE = re.compile(
    r"https?://[^\s<>\"']+",
    re.IGNORECASE,
)


def _load_config(base_path: Optional[Path]) -> Dict[str, Any]:
    """Carga Config/web_sources.json (allowed_domains, timeout_seconds, rate_limits)."""
    if not base_path or not base_path.exists():
        return {}
    try:
        from .json_safe import safe_load

        path = base_path / "Config" / "web_sources.json"
        if not path.exists():
            return {}
        data = safe_load(path, default={})
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_url_from_text(text: str) -> Optional[str]:
    """Devuelve la primera URL encontrada en el texto o None."""
    if not (text or "").strip():
        return None
    m = _URL_RE.search(text.strip())
    return m.group(0).strip() if m else None


def _domain_allowed(url: str, allowed_domains: Optional[List[str]]) -> bool:
    """True si allowed_domains es None/vacío (permitir todo) o el dominio está en la lista."""
    if not allowed_domains:
        return True
    try:
        netloc = urlparse(url).netloc.lower()
        if not netloc:
            return False
        # Sin puerto para comparar
        domain = netloc.split(":")[0]
        return any(
            d.strip().lower() in domain or domain.endswith("." + d.strip().lower())
            for d in allowed_domains
            if d
        )
    except Exception:
        return False


def _extract_structured_data(html: str) -> Dict[str, Any]:
    """Extrae datos estructurados JSON-LD y microdata del HTML."""
    structured = {}

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # JSON-LD
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        structured["jsonld"] = []
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string or "{}")
                structured["jsonld"].append(data)
            except Exception:
                pass

        # Meta tags Open Graph y Twitter
        structured["meta"] = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name")
            content = tag.get("content")
            if prop and content:
                structured["meta"][prop] = content

        # Título
        title_tag = soup.find("title")
        if title_tag:
            structured["title"] = title_tag.get_text(strip=True)

        # Autor (heurístico)
        for selector in ["[rel=author]", ".author", "[name=author]"]:
            author_elem = soup.select_one(selector)
            if author_elem:
                structured["author"] = author_elem.get_text(strip=True)
                break

        # Fecha de publicación (heurístico)
        for selector in [
            "[property=article:published_time]",
            "[name=publishedDate]",
            "time[datetime]",
            ".published",
            ".date",
        ]:
            date_elem = soup.select_one(selector)
            if date_elem:
                date = (
                    date_elem.get("content")
                    or date_elem.get("datetime")
                    or date_elem.get_text(strip=True)
                )
                if date:
                    structured["published_date"] = date
                    break

    except Exception as e:
        logger.debug("Error extracting structured data: %s", e)

    return structured


def _extract_article_content(html: str) -> str:
    """Extrae solo el contenido principal del artículo usando readability."""
    try:
        # Intentar usar readability-lxml si está disponible
        from readability import Document

        doc = Document(html)
        return doc.summary()
    except ImportError:
        logger.debug("readability-lxml not available, using fallback")
    except Exception as e:
        logger.debug("readability failed: %s", e)

    # Fallback: usar BeautifulSoup con heurísticos
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Remover elementos no deseados
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
                "advertisement",
                ".ad",
                ".ads",
                ".sidebar",
                ".comments",
                ".social",
            ]
        ):
            tag.decompose()

        # Buscar contenido principal por selectores comunes
        content_selectors = [
            "article",
            "[role=main]",
            "main",
            ".content",
            ".post-content",
            ".entry-content",
            ".article-body",
            "#content",
            ".main-content",
        ]

        for selector in content_selectors:
            main = soup.select_one(selector)
            if main:
                return str(main)

        # Fallback: usar body
        body = soup.find("body")
        if body:
            return str(body)

        return html
    except Exception as e:
        logger.debug("Fallback extraction failed: %s", e)
        return html


def _fetch_and_extract_text(
    url: str,
    timeout_seconds: int = 15,
    strategy: ScrapingStrategy = ScrapingStrategy.FULL_PAGE,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Descarga la URL y extrae el contenido según la estrategia.

    Returns:
        Dict con html, text, metadata
    """
    import requests
    from bs4 import BeautifulSoup

    default_headers = {
        "User-Agent": "Lilith-WebScraper/4.2 (bot; +https://github.com/lilith)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
    }
    if headers:
        default_headers.update(headers)

    resp = requests.get(url, timeout=timeout_seconds, headers=default_headers)
    resp.raise_for_status()

    raw_html = resp.text

    # Extraer datos estructurados siempre
    structured_data = _extract_structured_data(raw_html)

    # Aplicar estrategia
    if strategy == ScrapingStrategy.ARTICLE_ONLY:
        html_for_text = _extract_article_content(raw_html)
    elif strategy == ScrapingStrategy.STRUCTURED_DATA:
        # Para structured_data, mantener el HTML pero enfocarse en contenido principal
        html_for_text = _extract_article_content(raw_html)
    else:
        html_for_text = raw_html

    # Parsear con BeautifulSoup para extraer texto
    soup = BeautifulSoup(html_for_text, "html.parser")

    # Remover scripts y estilos
    for tag in soup(["script", "style"]):
        tag.decompose()

    body = soup.find("body") or soup
    text = body.get_text(separator="\n", strip=True)

    # Normalizar líneas en blanco
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    text = "\n\n".join(lines)

    return {
        "html": raw_html,
        "text": text,
        "metadata": structured_data,
    }


class RateLimiter:
    """Rate limiter simple para requests HTTP."""

    def __init__(
        self,
        default_delay: float = 2.0,
        per_domain_limits: Optional[Dict[str, float]] = None,
    ):
        self.default_delay = default_delay
        self.per_domain_limits = per_domain_limits or {}
        self._last_request: Dict[str, float] = {}
        self._lock: Optional[asyncio.Lock] = None

    async def acquire(self, url: str):
        """Espera si es necesario antes de hacer un request."""
        # Inicializar lock si es necesario
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            domain = urlparse(url).netloc
            delay = self.per_domain_limits.get(domain, self.default_delay)

            now = time.time()
            last = self._last_request.get(domain, 0)
            wait_time = max(0, delay - (now - last))

            if wait_time > 0:
                logger.debug(
                    "[WebScraper] Rate limiting: waiting %.2fs for %s",
                    wait_time,
                    domain,
                )
                await asyncio.sleep(wait_time)

            self._last_request[domain] = time.time()


class WebScraperAgent(Agent):
    """
    Agente que extrae texto crudo de una URL.
    Respeta Config/web_sources.json: allowed_domains, timeout_seconds, rate_limits.
    Soporta múltiples estrategias de scraping.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = Path(base_path) if base_path else None
        self._config = _load_config(self._base_path)
        self._rate_limiter = RateLimiter(
            default_delay=self._config.get("rate_limits", {}).get(
                "default_delay_seconds", 2.0
            ),
            per_domain_limits=self._config.get("rate_limits", {}).get("per_domain", {}),
        )

    @property
    def agent_id(self) -> str:
        return "web_scraper"

    @property
    def tool_name(self) -> str:
        return "delegate_web_scraper"

    @property
    def description(self) -> str:
        return "Extrae el contenido textual principal de una URL (minería web)."

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """Ejecución síncrona (compatibilidad con AgentRegistry)."""
        try:
            result = self.scrape_sync(params)
            return result
        except Exception as e:
            logger.warning("WebScraperAgent: %s", e)
            return {
                "response": f"No pude extraer el contenido de la URL: {e}",
                "error": True,
            }

    def scrape_sync(self, params: Dict[str, Any]) -> ToolResult:
        """Scrape síncrono - wrapper sobre el async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop corriendo, usar run_coroutine_threadsafe
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.scrape(params))
                    return future.result()
            else:
                return loop.run_until_complete(self.scrape(params))
        except RuntimeError:
            # No hay loop, crear uno nuevo
            return asyncio.run(self.scrape(params))

    async def scrape(self, params: Dict[str, Any]) -> ToolResult:
        """
        Scrapea una URL y retorna el contenido estructurado.

        Args:
            params: Dict con url, task (opcional), strategy (opcional)

        Returns:
            ToolResult con response, structured_data, etc.
        """
        url = (params.get("url") or "").strip()
        task = (params.get("task") or "").strip()
        strategy_str = (params.get("strategy") or "").strip()

        if not url:
            url = _extract_url_from_text(task or "")

        if not url:
            # Permitir encadenamiento: si el paso previo fue web_search
            ctx = (params.get("context") or "").strip()
            if ctx:
                try:
                    data = json.loads(ctx)
                    if isinstance(data, dict):
                        results = data.get("results")
                        if isinstance(results, list) and results:
                            first = results[0] if isinstance(results[0], dict) else None
                            candidate = (
                                (first.get("url") or "").strip() if first else ""
                            )
                            if candidate.startswith("http"):
                                url = candidate
                except Exception:
                    pass

        if not url:
            return {
                "response": "Indica la URL a extraer (ej. «extrae contenido de https://...» o pasa el parámetro url).",
                "error": True,
            }

        # Verificar dominio permitido
        allowed = self._config.get("allowed_domains")
        if isinstance(allowed, list) and allowed and not _domain_allowed(url, allowed):
            logger.warning("[WebScraper] Domain not allowed: %s", url)
            return {
                "response": f"El dominio de la URL no está en la lista de permitidos (Config/web_sources.json).",
                "error": True,
            }

        # Determinar estrategia
        if strategy_str:
            try:
                strategy = ScrapingStrategy(strategy_str)
            except ValueError:
                strategy = get_strategy_for_source(url)
        else:
            # Usar configuración por fuente
            source_quality = self._config.get("strategies", {}).get(
                "high_quality_sources", "article_only"
            )
            general_strategy = self._config.get("strategies", {}).get(
                "general", "full_page"
            )

            from .web_mining_models import classify_source_quality

            quality = classify_source_quality(url)

            if quality == "high":
                strategy = ScrapingStrategy(source_quality)
            else:
                strategy = ScrapingStrategy(general_strategy)

        # Rate limiting
        await self._rate_limiter.acquire(url)

        timeout = max(10, int(self._config.get("timeout_seconds", 15)))

        try:
            logger.info("[WebScraper] Scraping: %s (strategy: %s)", url, strategy.value)

            content = _fetch_and_extract_text(
                url, timeout_seconds=timeout, strategy=strategy
            )

            text = content["text"]

            if not text or len(text.strip()) < 10:
                logger.warning("[WebScraper] Empty or minimal content: %s", url)
                return {
                    "response": f"La página no devolvió texto utilizable o está casi vacía: {url}",
                    "error": False,
                }

            # Limitar tamaño para no saturar contexto
            max_chars = int(self._config.get("max_chars", 0)) or 80_000
            if len(text) > max_chars:
                text = text[:max_chars].rstrip() + "\n\n… (truncado)"

            # Crear objeto ScrapedContent
            scraped = ScrapedContent(
                url=url,
                raw_html=content["html"][:100_000],  # Limitar HTML raw
                text=text,
                metadata=content["metadata"],
                strategy=strategy,
            )

            logger.info(
                "[WebScraper] Successfully scraped: %s (%d chars)", url, len(text)
            )

            return {
                "response": f"[Contenido extraído de {url}]\n\n{text}",
                "url": url,
                "scraped_content": scraped,
                "structured_data": content["metadata"],
                "error": False,
            }

        except requests.exceptions.Timeout as e:
            logger.error("[WebScraper] Timeout: %s - %s", url, e)
            return {
                "response": f"Timeout al extraer {url}: el servidor no respondió a tiempo.",
                "error": True,
                "error_type": "timeout",
            }
        except requests.exceptions.HTTPError as e:
            logger.error("[WebScraper] HTTP error: %s - %s", url, e)
            return {
                "response": f"Error HTTP al extraer {url}: {e}",
                "error": True,
                "error_type": "http_error",
            }
        except Exception as e:
            logger.exception("[WebScraper] Failed to scrape: %s - %s", url, e)
            return {
                "response": f"No pude extraer el contenido de {url}: {e}",
                "error": True,
                "error_type": "unknown",
            }

    async def scrape_batch(
        self,
        urls: List[str],
        strategy: Optional[ScrapingStrategy] = None,
        progress_callback: Optional[Any] = None,
    ) -> List[ToolResult]:
        """
        Scrapea múltiples URLs en paralelo con rate limiting.

        Args:
            urls: Lista de URLs a scrapear
            strategy: Estrategia opcional (si no, se autodetecta por URL)
            progress_callback: Callback opcional (url, index, total)

        Returns:
            Lista de resultados
        """
        results = []

        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(url, i, len(urls))

                params = {"url": url}
                if strategy:
                    params["strategy"] = strategy.value

                result = await self.scrape(params)
                results.append(result)

            except Exception as e:
                logger.error("[WebScraper] Batch error for %s: %s", url, e)
                results.append(
                    {
                        "response": f"Error: {e}",
                        "url": url,
                        "error": True,
                    }
                )

        return results
