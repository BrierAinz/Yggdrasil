"""Mimir — The Well of Wisdom. Deep Research Agent for Vanaheim.

Mimir sees beneath the surface, drawing from the depths of knowledge
to synthesize insight. Where Odin sacrificed his eye for wisdom,
Mimir offers it freely — through methodical research and analysis.
"""

import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from Core.models.agent import AgentCapabilities, AgentConfig

from Agents.Base.vanir_agent import VanirAgent

from .research_tools import ArxivSearchTool, ReportGenerator, SourceAnalyzer, WebSearchTool


logger = logging.getLogger("yggdrasil.mimir")


# ── Depth configuration ──────────────────────────────────────────────────────

DEPTH_CONFIGS = {
    "quick": {
        "max_sources": 5,
        "max_arxiv_papers": 3,
        "deep_dive_top_k": 3,
        "timeout_seconds": 120,
    },
    "standard": {
        "max_sources": 10,
        "max_arxiv_papers": 5,
        "deep_dive_top_k": 5,
        "timeout_seconds": 600,
    },
    "deep": {
        "max_sources": 20,
        "max_arxiv_papers": 10,
        "deep_dive_top_k": 8,
        "timeout_seconds": 900,
    },
}


# ── MimirAgent ───────────────────────────────────────────────────────────────

class MimirAgent(VanirAgent):
    """Deep Research Agent — The Well of Wisdom.

    Mimir orchestrates multi-step research across web search and arxiv,
    synthesizing findings into structured markdown reports saved to
    Svartalfheim/Knowledge/.

    The well is deep; Mimir draws from many streams.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._searxng_url: str = "http://localhost:8888"
        self._output_dir: Path = Path("Svartalfheim/Knowledge")

        # Load depth configs from the config json if available
        self._depth_configs = DEPTH_CONFIGS.copy()
        # Merge any depth_configs from the AgentConfig capabilities
        if hasattr(config, "depth_configs") and config.depth_configs:
            self._depth_configs.update(config.depth_configs)

        # Initialize research tools — each draws from its own stream
        self._web_search = WebSearchTool(base_url=self._searxng_url)
        self._arxiv_search = ArxivSearchTool()
        self._source_analyzer = SourceAnalyzer()
        self._report_generator = ReportGenerator()

    # ── VanirAgent abstract properties ─────────────────────────────────────

    @property
    def agent_id(self) -> str:
        return "mimir"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            can_stream=True,
            supports_tools=True,
            max_context_tokens=128000,
            specialties=["research", "analysis", "synthesis", "arxiv", "web_search"],
            supported_tasks=[
                "deep_research",
                "literature_review",
                "topic_analysis",
                "report_generation",
            ],
        )

    # ── Availability check ─────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Check if Mimir can operate. The well never truly dries —
        we can always produce research with mock data."""
        # Mimir works standalone — always available
        return True

    # ── Execute: synchronous research ──────────────────────────────────────

    async def execute(self, task: str, context: dict[str, Any]) -> str:
        """Execute a research task and return the report path.

        The roots of Yggdrasil reach deep — Mimir gathers knowledge
        from every branch before distilling it.

        Args:
            task: A research topic or question.
            context: Optional context dict with keys:
                - depth: "quick" | "standard" | "deep" (default: "standard")
                - searxng_url: Override SearXNG URL
                - output_dir: Override output directory

        Returns:
            The absolute path to the generated report markdown file.
        """
        depth = context.get("depth", "standard") if context else "standard"
        if depth not in DEPTH_CONFIGS:
            logger.warning("Unknown depth '%s', falling back to 'standard'", depth)
            depth = "standard"

        # Apply context overrides
        if context:
            if "searxng_url" in context:
                self._web_search = WebSearchTool(base_url=context["searxng_url"])
            if "output_dir" in context:
                self._output_dir = Path(context["output_dir"])

        self._set_busy(task)
        try:
            report_path = await self.research(topic=task, depth=depth)
            return str(report_path)
        except Exception as exc:
            self._set_error(str(exc))
            logger.error("Mimir research failed: %s", exc, exc_info=True)
            raise
        finally:
            self._set_idle()

    # ── Stream: yield research updates ──────────────────────────────────────

    async def stream(self, task: str, context: dict[str, Any]) -> AsyncGenerator[str, None]:
        """Stream research progress as JSON-LD events.

        Yields events like:
            {"phase": "search", "status": "running", "sources_found": 5}
            {"phase": "arxiv", "status": "running", "papers_found": 3}
            {"phase": "synthesis", "status": "running", "report_length": 2048}
            {"phase": "complete", "report_path": "/path/to/report.md"}
        """
        depth = context.get("depth", "standard") if context else "standard"
        if depth not in DEPTH_CONFIGS:
            depth = "standard"

        if context:
            if "searxng_url" in context:
                self._web_search = WebSearchTool(base_url=context["searxng_url"])
            if "output_dir" in context:
                self._output_dir = Path(context["output_dir"])

        self._set_busy(task)
        try:
            # Phase 1: Broad web search
            yield json.dumps({"phase": "search", "status": "running", "topic": task})
            web_results = await self._web_search.search(task, max_results=DEPTH_CONFIGS[depth]["max_sources"])
            yield json.dumps({"phase": "search", "status": "complete", "sources_found": len(web_results)})

            # Phase 2: Arxiv paper search
            yield json.dumps({"phase": "arxiv", "status": "running"})
            arxiv_results = await self._arxiv_search.search(task, max_results=DEPTH_CONFIGS[depth]["max_arxiv_papers"])
            yield json.dumps({"phase": "arxiv", "status": "complete", "papers_found": len(arxiv_results)})

            # Phase 3: Deep dive into top sources
            yield json.dumps({"phase": "deep_dive", "status": "running", "top_k": DEPTH_CONFIGS[depth]["deep_dive_top_k"]})
            all_sources = web_results + [
                {"title": p["title"], "url": p["url"], "snippet": p["abstract"], "source_type": "arxiv", "published": p.get("published", "")}
                for p in arxiv_results
            ]
            ranked = self._source_analyzer.rank(all_sources, topic=task, top_k=DEPTH_CONFIGS[depth]["deep_dive_top_k"])
            yield json.dumps({"phase": "deep_dive", "status": "complete", "ranked_sources": len(ranked)})

            # Phase 4: Synthesis
            yield json.dumps({"phase": "synthesis", "status": "running"})
            report_markdown, _report_path = self._report_generator.generate(
                topic=task,
                sources=ranked,
                arxiv_papers=arxiv_results,
                depth=depth,
                output_dir=self._output_dir,
            )
            yield json.dumps({"phase": "synthesis", "status": "complete", "report_length": len(report_markdown)})

            # Save the report
            saved_path = self._save_report(task, report_markdown)
            yield json.dumps({"phase": "complete", "report_path": str(saved_path), "depth": depth})

        except Exception as exc:
            self._set_error(str(exc))
            yield json.dumps({"phase": "error", "error": str(exc)})
        finally:
            self._set_idle()

    # ── Main research method ───────────────────────────────────────────────

    async def research(self, topic: str, depth: str = "standard") -> Path:
        """Orchestrate multi-step research on a topic.

        The four phases of Mimir's wisdom:
          1. Broad Search — cast wide nets across the web
          2. Deep Dive — scrutinize the most promising sources
          3. Arxiv Analysis — peer into the pages of scholarship
          4. Synthesis — weave findings into a single tapestry

        Args:
            topic: The research topic or question.
            depth: "quick", "standard", or "deep".

        Returns:
            Path to the saved report file.
        """
        config = DEPTH_CONFIGS.get(depth, DEPTH_CONFIGS["standard"])
        logger.info("Mimir begins %s-depth research on: %s", depth, topic)

        # ── Phase 1: Broad web search ──────────────────────────────────────
        logger.info("Phase 1: Casting the wide net — web search for '%s'", topic)
        web_results = await self._web_search.search(
            topic, max_results=config["max_sources"]
        )
        logger.info("Phase 1 complete: %d sources found", len(web_results))

        # ── Phase 2: Arxiv paper search ─────────────────────────────────────
        logger.info("Phase 2: Peering into scholarship — arxiv search for '%s'", topic)
        arxiv_results = await self._arxiv_search.search(
            topic, max_results=config["max_arxiv_papers"]
        )
        logger.info("Phase 2 complete: %d papers found", len(arxiv_results))

        # ── Phase 3: Rank and deep-dive ────────────────────────────────────
        all_sources = web_results + [
            {
                "title": p["title"],
                "url": p["url"],
                "snippet": p["abstract"],
                "source_type": "arxiv",
                "published": p.get("published", ""),
            }
            for p in arxiv_results
        ]
        ranked = self._source_analyzer.rank(
            all_sources, topic=topic, top_k=config["deep_dive_top_k"]
        )
        logger.info("Phase 3 complete: %d sources ranked and selected", len(ranked))

        # ── Phase 4: Synthesis ──────────────────────────────────────────────
        logger.info("Phase 4: Weaving the tapestry — synthesizing report")
        report_markdown, _ = self._report_generator.generate(
            topic=topic,
            sources=ranked,
            arxiv_papers=arxiv_results,
            depth=depth,
            output_dir=self._output_dir,
        )

        saved_path = self._save_report(topic, report_markdown)
        logger.info("Research complete. Report saved to: %s", saved_path)
        return saved_path

    # ── Report saving ──────────────────────────────────────────────────────

    def _save_report(self, topic: str, content: str) -> Path:
        """Save the research report to Svartalfheim/Knowledge/.

        The Well preserves its wisdom in the archives.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(topic)
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"mimir-{slug}-{date}.md"
        path = self._output_dir / filename

        path.write_text(content, encoding="utf-8")
        logger.info("Report saved: %s", path)
        return path

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert a topic string to a URL-safe slug."""
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug[:64].strip("-")

    # ── Health check override ──────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        """Mimir's health — the depth of the well and clarity of the water."""
        base = await super().health()
        web_available = await self._web_search.is_available()
        arxiv_available = await self._arxiv_search.is_available()
        base.update({
            "searxng_available": web_available,
            "arxiv_available": arxiv_available,
            "output_dir": str(self._output_dir),
        })
        return base
