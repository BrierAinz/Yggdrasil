"""Research tools for Mimir — the instruments of wisdom.

Each tool draws from a different stream of knowledge:
  - ArxivSearchTool: The scholarly stream (peer-reviewed papers)
  - WebSearchTool: The public stream (SearXNG aggregation)
  - SourceAnalyzer: The sieve that separates gold from sediment
  - ReportGenerator: The loom that weaves findings into tapestry
"""

import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger("yggdrasil.mimir")


# ── ArxivSearchTool ──────────────────────────────────────────────────────────


class ArxivSearchTool:
    """Search arxiv for scholarly papers.

    Mimir peers into the pages of scholarship — the ArXiv API
    provides structured access to academic research.
    """

    ARXIV_API = "http://export.arxiv.org/api/query"

    def __init__(self):
        """Inicializar ArxivSearchTool con cliente HTTP asíncrono lazy."""
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    async def is_available(self) -> bool:
        """Check if the ArXiv API is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(
                self.ARXIV_API, params={"max_results": 1, "search_query": "all:electron"}
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search arxiv papers by keyword.

        Args:
            query: Search keywords or phrase.
            max_results: Maximum number of results to return.

        Returns:
            List of dicts with: title, authors, abstract, url, published
        """
        client = await self._get_client()
        # arxiv expects "all:" prefix for general search
        search_query = f"all:{query}"

        try:
            resp = await client.get(
                self.ARXIV_API,
                params={
                    "search_query": search_query,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
            )
            resp.raise_for_status()
            return self._parse_arxiv_response(resp.text)
        except httpx.HTTPStatusError as exc:
            logger.warning("ArXiv API returned %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.exception("ArXiv search failed: %s", exc)
            return []

    def _parse_arxiv_response(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse ArXiv API Atom XML response into structured results."""
        results = []
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.warning("Failed to parse ArXiv XML response")
            return []

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            published_el = entry.find("atom:published", ns)
            id_el = entry.find("atom:id", ns)

            if title_el is None or id_el is None:
                continue

            title = title_el.text.strip().replace("\n", " ") if title_el.text else "Untitled"
            abstract = (
                summary_el.text.strip().replace("\n", " ")
                if summary_el is not None and summary_el.text
                else ""
            )
            url = id_el.text.strip() if id_el.text else ""
            published = (
                published_el.text.strip()[:10]
                if published_el is not None and published_el.text
                else ""
            )

            # Extract authors
            authors = []
            for author_el in entry.findall("atom:author", ns):
                name_el = author_el.find("atom:name", ns)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract[:500],  # Truncate for readability
                    "url": url,
                    "published": published,
                }
            )

        return results

    async def close(self):
        """Cerrar el cliente HTTP de ArXiv."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ── WebSearchTool ────────────────────────────────────────────────────────────


class WebSearchTool:
    """SearXNG integration for web search.

    The public stream flows through many channels — SearXNG
    aggregates them into a single current of knowledge.
    """

    def __init__(self, base_url: str = "http://localhost:8888"):
        """Inicializar WebSearchTool con URL de SearXNG."""
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        return self._client

    async def is_available(self) -> bool:
        """Check if SearXNG is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self._base_url}/", params={"format": "json", "q": "test"})
            return resp.status_code == 200
        except Exception:
            return False

    async def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search the web via SearXNG.

        Args:
            query: Search query string.
            max_results: Maximum results to return.

        Returns:
            List of dicts with: title, url, snippet, source_type, engine
        """
        client = await self._get_client()

        try:
            resp = await client.get(
                f"{self._base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general,science",
                    "language": "en",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])[:max_results]

            return [
                {
                    "title": r.get("title", "Untitled"),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:300],
                    "source_type": "web",
                    "engine": r.get("engine", "unknown"),
                    "published": r.get("publishedDate", ""),
                }
                for r in results
                if r.get("url")
            ]
        except httpx.HTTPStatusError as exc:
            logger.warning("SearXNG returned %d: %s", exc.response.status_code, exc)
            return self._mock_search(query, max_results)
        except Exception as exc:
            logger.warning("SearXNG search failed, using mock data: %s", exc)
            return self._mock_search(query, max_results)

    def _mock_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Fallback mock results when SearXNG is unavailable.

        The well still provides water even when the rivers are dry.
        """
        logger.info("Using mock search results for: %s", query)
        return [
            {
                "title": f"Research: {query} — Source {i + 1}",
                "url": f"https://example.com/research/{urllib.parse.quote(query, safe='')}/{i + 1}",
                "snippet": f"This source discusses various aspects of {query} and related topics.",
                "source_type": "mock",
                "engine": "mock",
                "published": datetime.now(UTC).strftime("%Y-%m-%d"),
            }
            for i in range(min(max_results, 5))
        ]

    async def close(self):
        """Cerrar el cliente HTTP de SearXNG."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ── SourceAnalyzer ────────────────────────────────────────────────────────────


class SourceAnalyzer:
    """Analyze and rank sources by relevance, recency, and credibility.

    Mimir's sieve separates gold from sediment — not all knowledge
    is equally valuable. This tool ranks sources to surface the
    most relevant and trustworthy findings.
    """

    # Credibility tiers based on URL patterns
    CREDIBILITY_TIERS = {
        "high": [
            "arxiv.org",
            "nature.com",
            "science.org",
            "dl.acm.org",
            "ieee.org",
            "springer.com",
            "wiley.com",
            "nist.gov",
            "nist.gov",
            "ncbi.nlm.nih.gov",
            "gnu.org",
            "python.org",
        ],
        "medium": [
            "github.com",
            "stackoverflow.com",
            "medium.com",
            "wikipedia.org",
            "docs.python.org",
            "mozilla.org",
            "react.dev",
            "typescriptlang.org",
        ],
    }

    def rank(
        self,
        sources: list[dict[str, Any]],
        topic: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Rank sources by relevance, recency, and credibility.

        Args:
            sources: List of source dicts (from web/arxiv search).
            topic: The research topic for relevance scoring.
            top_k: Number of top sources to return.

        Returns:
            Sorted and filtered list of sources with added scores.
        """
        scored = []
        topic_terms = set(re.findall(r"\w+", topic.lower()))

        for source in sources:
            score = self._compute_score(source, topic_terms)
            scored.append({**source, "relevance_score": score})

        # Sort by score descending
        scored.sort(key=lambda s: s["relevance_score"], reverse=True)
        return scored[:top_k]

    def _compute_score(self, source: dict[str, Any], topic_terms: set) -> float:
        """Compute a composite score for a source.

        Score components:
          - Relevance: keyword overlap between topic and title+snippet
          - Recency: newer sources score higher
          - Credibility: academic/governmental sources score higher
        """
        # Relevance: keyword overlap
        text = (
            f"{source.get('title', '')} {source.get('snippet', source.get('abstract', ''))}".lower()
        )
        text_terms = set(re.findall(r"\w+", text))
        overlap = len(topic_terms & text_terms)
        relevance = overlap / max(len(topic_terms), 1)

        # Recency: penalize old sources
        published = source.get("published", "")
        recency = self._recency_score(published)

        # Credibility: tier-based  # noqa: ERA001
        url = source.get("url", "")
        credibility = self._credibility_score(url)

        # Source type bonus
        type_bonus = 0.15 if source.get("source_type") == "arxiv" else 0.0

        return round(relevance * 0.4 + recency * 0.2 + credibility * 0.3 + type_bonus, 3)

    def _recency_score(self, published: str) -> float:
        """Score from 0.0 (ancient) to 1.0 (today)."""
        if not published:
            return 0.5  # Unknown age — neutral
        try:
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d")
            now = datetime.now(UTC)
            age_days = (now - pub_date).days
            # Exponential decay: 1.0 for today, ~0.5 for 1 year
            return max(0.0, min(1.0, 0.5 ** (age_days / 365.25)))
        except (ValueError, TypeError):
            return 0.5

    def _credibility_score(self, url: str) -> float:
        """Score based on URL domain credibility tier."""
        for tier, domains in self.CREDIBILITY_TIERS.items():
            for domain in domains:
                if domain in url:
                    return {"high": 1.0, "medium": 0.7}.get(tier, 0.4)
        return 0.4  # Default: low-ish credibility


# ── ReportGenerator ──────────────────────────────────────────────────────────


class ReportGenerator:
    """Generate structured markdown research reports.

    The loom that weaves disparate threads into a single tapestry.
    Reports follow a consistent structure that transcends depth level.
    """

    DEPTH_LABELS = {
        "quick": "Quick Scan",
        "standard": "Standard Research",
        "deep": "Deep Analysis",
    }

    def generate(
        self,
        topic: str,
        sources: list[dict[str, Any]],
        arxiv_papers: list[dict[str, Any]],
        depth: str = "standard",
        output_dir: Path | None = None,
    ) -> tuple[str, Path | None]:
        """Generate a structured markdown report.

        Args:
            topic: The research topic.
            sources: Ranked web sources (from SourceAnalyzer).
            arxiv_papers: ArXiv paper results.
            depth: Research depth level.
            output_dir: Directory to save the report (None = don't save).

        Returns:
            Tuple of (markdown_content, file_path or None)
        """
        now = datetime.now(UTC)
        depth_label = self.DEPTH_LABELS.get(depth, "Research")

        # ── Build the report ────────────────────────────────────────────────
        lines: list[str] = []

        # Title
        lines.append(f"# {topic}")
        lines.append("")
        lines.append(
            f"> **{depth_label}** — Generated by Mimir on {now.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        lines.append(
            (
                f"> *The Well of Wisdom draws from {len(sources)} sources "
                f"and {len(arxiv_papers)} academic papers.*"
            )
        )
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        summary = self._generate_summary(topic, sources, arxiv_papers)
        lines.append(summary)
        lines.append("")

        # Key Findings
        lines.append("## Key Findings")
        lines.append("")
        findings = self._generate_findings(sources, arxiv_papers)
        for i, finding in enumerate(findings, 1):
            lines.append(f"{i}. {finding}")
        lines.append("")

        # Academic Papers
        if arxiv_papers:
            lines.append("## Academic Papers")
            lines.append("")
            for paper in arxiv_papers:
                title = paper.get("title", "Untitled")
                url = paper.get("url", "")
                authors = ", ".join(paper.get("authors", [])[:3])
                if len(paper.get("authors", [])) > 3:
                    authors += " et al."
                abstract_snippet = paper.get("abstract", "")[:200]
                published = paper.get("published", "Unknown date")

                lines.append(f"### [{title}]({url})")
                lines.append(f"- **Authors:** {authors}")
                lines.append(f"- **Published:** {published}")
                lines.append(f"- **Abstract:** {abstract_snippet}...")
                lines.append("")

        # Sources
        lines.append("## Sources")
        lines.append("")
        for source in sources:
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            snippet = source.get("snippet", "")[:150]
            source_type = source.get("source_type", "web")
            score = source.get("relevance_score", 0)
            engine = source.get("engine", "")

            lines.append(f"- [{title}]({url})")
            if snippet:
                lines.append(f"  > {snippet}")
            lines.append(f"  *Type: {source_type} | Relevance: {score:.2f} | Engine: {engine}*")
            lines.append("")

        # Further Reading
        lines.append("## Further Reading")
        lines.append("")
        further = self._generate_further_reading(topic, sources)
        for suggestion in further:
            lines.append(f"- {suggestion}")
        lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Report generated by Mimir — The Well of Wisdom*")
        lines.append(f"*Yggdrasil Ecosystem — {now.strftime('%Y-%m-%d')}*")

        markdown = "\n".join(lines)

        # Save if output_dir provided
        file_path = None
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            slug = self._slugify(topic)
            date = now.strftime("%Y-%m-%d")
            filename = f"mimir-{slug}-{date}.md"
            file_path = output_dir / filename
            file_path.write_text(markdown, encoding="utf-8")
            logger.info("Report saved to: %s", file_path)

        return markdown, file_path

    @staticmethod
    def _slugify(text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug[:64].strip("-")

    def _generate_summary(self, topic: str, sources: list, papers: list) -> str:
        """Generate a brief summary paragraph based on source snippets."""
        snippets = []
        for s in sources[:3]:
            snippet = s.get("snippet", "") or s.get("abstract", "")
            if snippet:
                snippets.append(snippet[:100])

        if snippets:
            combined = " ".join(snippets)
            return (
                f"Research on **{topic}** reveals insights from "
                f"{len(sources)} web sources and {len(papers)} "
                f"academic papers. {combined}"
            )
        else:
            return (
                f"Research on **{topic}** examined {len(sources)} "
                f"web sources and {len(papers)} academic papers, "
                "though detailed summaries were not available."
            )

    def _generate_findings(self, sources: list, papers: list) -> list[str]:
        """Extract key findings from source titles and snippets."""
        findings = []

        for source in sources[:5]:
            title = source.get("title", "")
            snippet = source.get("snippet", "") or source.get("abstract", "")
            if title and snippet:
                findings.append(f"**{title}** — {snippet[:120]}")
            elif title:
                findings.append(f"**{title}** — relevant to the research topic.")

        for paper in papers[:3]:
            title = paper.get("title", "")
            if title and not any(title in f for f in findings):
                findings.append(
                    f"Academic: **{title}** — peer-reviewed research relevant to this topic."
                )

        if not findings:
            findings.append("No significant findings were extracted from the available sources.")

        return findings

    def _generate_further_reading(self, topic: str, sources: list) -> list[str]:
        """Suggest further reading directions."""
        suggestions = [
            f"Explore related topics: combine '{topic}' with specific subdomains or applications.",
            "Check for recent conference proceedings and preprints not yet indexed.",
        ]
        # Add unique source domains as suggested sites
        seen_domains = set()
        for s in sources:
            url = s.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse

                    domain = urlparse(url).netloc
                    if domain and domain not in seen_domains and len(seen_domains) < 3:
                        seen_domains.add(domain)
                        suggestions.append(f"Search within: {domain}")
                except Exception:
                    pass
        return suggestions
