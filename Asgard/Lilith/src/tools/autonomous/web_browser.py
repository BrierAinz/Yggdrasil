"""
WebBrowser - Web navigation and content extraction for Lilith
Handles: URL visits, content extraction, link following, basic searches
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urljoin, urlparse

logger = logging.getLogger(__name__)


class WebBrowser:
    """
    Autonomous tool for web browsing operations.

    Capabilities:
    - visit: Navigate to a URL and extract content
    - search: Perform web searches
    - extract_links: Extract all links from a page
    - extract_text: Extract clean text content from a page
    - find_element: Find specific elements by CSS selector
    - screenshot: Save page screenshot (if browser automation available)
    """

    def __init__(self):
        self.session = None
        self.current_url = None
        self.last_content = None
        self.max_content_length = 100000  # Max chars to extract
        self.allowed_schemes = ["http", "https"]
        self.blocked_domains = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "10.",
            "192.168.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
        ]
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _get_session(self):
        """Lazy initialization of requests session"""
        if self.session is None:
            try:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                self.session = requests.Session()
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self.session.mount("http://", adapter)
                self.session.mount("https://", adapter)
                self.session.headers.update({"User-Agent": self.user_agent})
            except ImportError:
                return None
        return self.session

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute web browsing operation

        Args:
            action: The browsing operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Dict with operation results
        """
        try:
            if action == "visit":
                return await self._visit_url(
                    kwargs.get("url"),
                    kwargs.get("extract_text", True),
                    kwargs.get("extract_links", True),
                )
            elif action == "search":
                return await self._web_search(
                    kwargs.get("query"), kwargs.get("num_results", 5)
                )
            elif action == "extract_links":
                return await self._extract_links(kwargs.get("url") or self.current_url)
            elif action == "extract_text":
                return await self._extract_text(
                    kwargs.get("url") or self.current_url, kwargs.get("selector", None)
                )
            elif action == "find_element":
                return await self._find_element(
                    kwargs.get("selector"), kwargs.get("url") or self.current_url
                )
            elif action == "get_title":
                return await self._get_page_title(kwargs.get("url") or self.current_url)
            else:
                return {
                    "success": False,
                    "error": f"Unknown web action: {action}",
                    "action": action,
                }
        except Exception as e:
            logger.error(f"Web operation failed: {e}")
            return {"success": False, "error": str(e), "action": action}

    def _validate_url(self, url: str) -> tuple[bool, str]:
        """
        Validate URL for safety

        Returns:
            (is_valid, error_message)
        """
        if not url:
            return False, "URL is required"

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in self.allowed_schemes:
            return False, f"Invalid URL scheme: {parsed.scheme}"

        # Check for blocked domains/IPs
        domain = parsed.hostname or ""
        for blocked in self.blocked_domains:
            if domain.startswith(blocked) or blocked in domain:
                return False, f"Access to this domain is blocked: {domain}"

        # Lista blanca: si Config/security.json tiene allowed_domains no vacío, solo esos dominios
        try:
            from src.core.input_sanitizer import validate_http_url

            base_path = Path(__file__).resolve().parent.parent.parent.parent
            ok, err = validate_http_url(url, base_path)
            if not ok:
                return False, err
        except Exception:
            pass

        return True, url

    def _fetch_url(self, url: str, timeout: int = 30) -> tuple[bool, Any]:
        """Fetch URL content"""
        session = self._get_session()
        if not session:
            return False, "requests library not available"

        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return True, response
        except Exception as e:
            return False, str(e)

    async def _visit_url(
        self, url: str, extract_text: bool = True, extract_links: bool = True
    ) -> Dict[str, Any]:
        """Visit a URL and extract information"""
        # Validate URL
        is_valid, result = self._validate_url(url)
        if not is_valid:
            return {"success": False, "error": result}

        url = result

        # Fetch content
        success, response = self._fetch_url(url)
        if not success:
            return {"success": False, "error": response, "url": url}

        # Update state
        self.current_url = response.url
        self.last_content = response.text

        result = {
            "success": True,
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", "unknown"),
        }

        # Extract text if HTML
        if extract_text and "text/html" in response.headers.get("Content-Type", ""):
            text_result = self._parse_html_content(response.text)
            result["title"] = text_result.get("title", "")
            result["text"] = text_result.get("text", "")[: self.max_content_length]
            result["text_truncated"] = (
                len(text_result.get("text", "")) > self.max_content_length
            )

        # Extract links
        if extract_links and "text/html" in response.headers.get("Content-Type", ""):
            links = self._parse_links(response.text, response.url)
            result["links"] = links[:50]  # Limit links
            result["link_count"] = len(links)

        return result

    def _parse_html_content(self, html: str) -> Dict[str, str]:
        """Parse HTML to extract title and clean text"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Get main content
            text = ""

            # Try to find main content areas
            main = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_=re.compile("content|main"))
            )
            if main:
                text = main.get_text(separator="\n", strip=True)
            else:
                # Fallback to body
                body = soup.find("body")
                if body:
                    text = body.get_text(separator="\n", strip=True)

            # Clean up text
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

            return {"title": title, "text": text}

        except ImportError:
            # Fallback to regex if BeautifulSoup not available
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_match.group(1) if title_match else ""

            # Strip tags
            text = re.sub(
                r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(
                r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            return {"title": title, "text": text}

    def _parse_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract links from HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            links = []

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(base_url, href)

                # Only include HTTP/HTTPS links
                if full_url.startswith(("http://", "https://")):
                    links.append(
                        {
                            "url": full_url,
                            "text": a_tag.get_text(strip=True)[:100],
                            "title": a_tag.get("title", ""),
                        }
                    )

            return links

        except ImportError:
            # Fallback to regex
            links = []
            pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
            for match in re.finditer(pattern, html, re.IGNORECASE):
                href = match.group(1)
                text = match.group(2)
                full_url = urljoin(base_url, href)

                if full_url.startswith(("http://", "https://")):
                    links.append({"url": full_url, "text": text[:100], "title": ""})

            return links

    async def _web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search
        Uses DuckDuckGo HTML version (no API key required)
        """
        if not query:
            return {"success": False, "error": "Search query is required"}

        session = self._get_session()
        if not session:
            return {"success": False, "error": "requests library not available"}

        try:
            # DuckDuckGo HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

            response = session.get(search_url, timeout=30)
            response.raise_for_status()

            # Parse results
            results = self._parse_duckduckgo_results(response.text, num_results)

            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "query": query}

    def _parse_duckduckgo_results(
        self, html: str, max_results: int
    ) -> List[Dict[str, str]]:
        """Parse DuckDuckGo search results"""
        results = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Find result containers
            for result in soup.find_all("div", class_="result")[:max_results]:
                # Extract title and URL
                link_elem = result.find("a", class_="result__a")
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    url = link_elem.get("href", "")

                    # Extract snippet
                    snippet_elem = result.find("a", class_="result__snippet")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append({"title": title, "url": url, "snippet": snippet})

        except ImportError:
            # Fallback to regex
            pattern = r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)

            for url, title in matches[:max_results]:
                results.append({"title": title.strip(), "url": url, "snippet": ""})

        return results

    async def _extract_links(self, url: Optional[str]) -> Dict[str, Any]:
        """Extract all links from a page"""
        if not url and not self.current_url:
            return {"success": False, "error": "No URL provided and no current page"}

        target_url = url or self.current_url

        # Validate
        is_valid, result = self._validate_url(target_url)
        if not is_valid:
            return {"success": False, "error": result}

        # Fetch
        success, response = self._fetch_url(result)
        if not success:
            return {"success": False, "error": response, "url": result}

        # Parse links
        links = self._parse_links(response.text, response.url)

        # Categorize
        internal = []
        external = []
        domain = urlparse(response.url).netloc

        for link in links:
            link_domain = urlparse(link["url"]).netloc
            if link_domain == domain or link_domain.endswith("." + domain):
                internal.append(link)
            else:
                external.append(link)

        return {
            "success": True,
            "url": response.url,
            "total_links": len(links),
            "internal_links": internal[:30],
            "external_links": external[:20],
            "internal_count": len(internal),
            "external_count": len(external),
        }

    async def _extract_text(
        self, url: Optional[str], selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract clean text from a page"""
        if not url and not self.current_url:
            return {"success": False, "error": "No URL provided and no current page"}

        target_url = url or self.current_url

        # Validate
        is_valid, result = self._validate_url(target_url)
        if not is_valid:
            return {"success": False, "error": result}

        # Fetch
        success, response = self._fetch_url(result)
        if not success:
            return {"success": False, "error": response, "url": result}

        # Parse
        parsed = self._parse_html_content(response.text)
        text = parsed.get("text", "")

        # Apply selector if provided
        if selector:
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "html.parser")
                elements = soup.select(selector)
                if elements:
                    text = "\n\n".join([el.get_text(strip=True) for el in elements])
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Selector error: {e}",
                    "url": response.url,
                }

        # Truncate if needed
        truncated = len(text) > self.max_content_length
        text = text[: self.max_content_length]

        return {
            "success": True,
            "url": response.url,
            "title": parsed.get("title", ""),
            "text": text,
            "truncated": truncated,
            "char_count": len(text),
        }

    async def _find_element(self, selector: str, url: Optional[str]) -> Dict[str, Any]:
        """Find elements by CSS selector"""
        if not selector:
            return {"success": False, "error": "CSS selector is required"}

        if not url and not self.current_url:
            return {"success": False, "error": "No URL provided and no current page"}

        target_url = url or self.current_url

        # Validate
        is_valid, result = self._validate_url(target_url)
        if not is_valid:
            return {"success": False, "error": result}

        # Fetch
        success, response = self._fetch_url(result)
        if not success:
            return {"success": False, "error": response, "url": result}

        # Parse with selector
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            elements = soup.select(selector)

            results = []
            for el in elements[:20]:  # Limit results
                results.append(
                    {
                        "tag": el.name,
                        "text": el.get_text(strip=True)[:200],
                        "attributes": {
                            k: v
                            for k, v in el.attrs.items()
                            if k in ["id", "class", "href", "src"]
                        },
                    }
                )

            return {
                "success": True,
                "url": response.url,
                "selector": selector,
                "found": len(results),
                "elements": results,
            }

        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available for selector parsing",
                "url": response.url,
            }

    async def _get_page_title(self, url: Optional[str]) -> Dict[str, Any]:
        """Get page title"""
        if not url and not self.current_url:
            return {"success": False, "error": "No URL provided and no current page"}

        target_url = url or self.current_url

        # Validate
        is_valid, result = self._validate_url(target_url)
        if not is_valid:
            return {"success": False, "error": result}

        # Fetch
        success, response = self._fetch_url(result)
        if not success:
            return {"success": False, "error": response, "url": result}

        # Parse title
        parsed = self._parse_html_content(response.text)

        return {
            "success": True,
            "url": response.url,
            "title": parsed.get("title", ""),
            "status_code": response.status_code,
        }
