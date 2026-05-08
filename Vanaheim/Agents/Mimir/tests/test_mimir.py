"""Tests for Mimir — The Well of Wisdom.

Verifies that Mimir draws from the depths of knowledge
and weaves findings into structured tapestries of insight.
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def agent_config():
    """Create a test AgentConfig for Mimir."""
    from Core.models.agent import AgentCapabilities, AgentConfig
    return AgentConfig(
        agent_id="mimir",
        name="Mimir",
        description="Deep Research Agent",
        model="grok-4-fast-reasoning",
        provider="grok",
        timeout=300,
        temperature=0.3,
        capabilities=AgentCapabilities(
            can_stream=True,
            supports_tools=True,
            max_context_tokens=128000,
            specialties=["research", "analysis", "synthesis", "arxiv", "web_search"],
            supported_tasks=["deep_research", "literature_review", "topic_analysis", "report_generation"],
        ),
    )


@pytest.fixture
def mimir(agent_config):
    """Create a MimirAgent instance for testing."""
    from Agents.Mimir.agent import MimirAgent
    return MimirAgent(agent_config)


# ── Test 1: Agent instantiation and properties ───────────────────────────────

class TestMimirAgentInstantiation:
    """The Well of Wisdom must be properly constructed."""

    def test_agent_id(self, mimir):
        """Mimir identifies itself."""
        assert mimir.agent_id == "mimir"

    def test_agent_state_idle(self, mimir):
        """Mimir starts idle, waiting for a task."""
        assert mimir.state.value == "idle"

    def test_capabilities(self, mimir):
        """Mimir declares its capabilities truthfully."""
        caps = mimir.capabilities
        assert caps.can_stream is True
        assert caps.supports_tools is True
        assert caps.max_context_tokens == 128000
        assert "research" in caps.specialties
        assert "deep_research" in caps.supported_tasks

    def test_config_preserved(self, mimir, agent_config):
        """Mimir carries its configuration."""
        assert mimir.config == agent_config
        assert mimir.config.model == "grok-4-fast-reasoning"
        assert mimir.config.temperature == 0.3

    def test_depth_configs_loaded(self, mimir):
        """Mimir knows the depths of research."""
        from Agents.Mimir.agent import DEPTH_CONFIGS
        assert "quick" in mimir._depth_configs
        assert "standard" in mimir._depth_configs
        assert "deep" in mimir._depth_configs

    def test_default_output_dir(self, mimir):
        """Mimir defaults to Svartalfheim/Knowledge/ for output."""
        assert str(mimir._output_dir) == "Svartalfheim/Knowledge"


# ── Test 2: Research phases execution ────────────────────────────────────────

class TestResearchPhases:
    """Mimir follows the four phases of wisdom."""

    @pytest.mark.asyncio
    async def test_research_quick_depth(self, mimir):
        """Quick depth research completes in minimal steps."""
        with patch.object(mimir._web_search, "search", new_callable=AsyncMock) as mock_web, \
             patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:

            mock_web.return_value = [
                {"title": "Test Source", "url": "https://example.com/1", "snippet": "Test snippet about AI", "source_type": "mock"}
            ]
            mock_arxiv.return_value = []

            result = await mimir.research("artificial intelligence", depth="quick")
            assert isinstance(result, Path)
            assert result.exists()
            mock_web.assert_called_once()
            mock_arxiv.assert_called_once()

            # Cleanup
            result.unlink()

    @pytest.mark.asyncio
    async def test_research_standard_depth(self, mimir):
        """Standard depth research orchestrates all four phases."""
        with patch.object(mimir._web_search, "search", new_callable=AsyncMock) as mock_web, \
             patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:

            mock_web.return_value = [
                {"title": f"Source {i}", "url": f"https://example.com/{i}", "snippet": f"Info about quantum computing {i}", "source_type": "mock"}
                for i in range(5)
            ]
            mock_arxiv.return_value = [
                {"title": "Quantum Paper", "authors": ["Dr. Smith"], "abstract": "Quantum computing research", "url": "https://arxiv.org/abs/1234", "published": "2025-01-15"}
            ]

            result = await mimir.research("quantum computing", depth="standard")
            assert isinstance(result, Path)
            assert result.name.startswith("mimir-")

            # Verify the file has content
            content = result.read_text(encoding="utf-8")
            assert "quantum computing" in content.lower()
            assert "## Summary" in content

            # Cleanup
            result.unlink()

    @pytest.mark.asyncio
    async def test_research_with_mock_fallback(self, mimir):
        """When SearXNG is unavailable, mock results are used."""
        with patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:
            # Let web_search use its mock fallback (no SearXNG running)
            mock_arxiv.return_value = []

            result = await mimir.research("test topic", depth="quick")
            assert isinstance(result, Path)
            assert result.exists()

            # Cleanup
            result.unlink()


# ── Test 3: Report generation format ────────────────────────────────────────

class TestReportGeneration:
    """The loom weaves a proper tapestry."""

    def test_report_has_required_sections(self, mimir):
        """Reports contain all required sections."""
        from Agents.Mimir.research_tools import ReportGenerator

        gen = ReportGenerator()
        sources = [
            {"title": "Test", "url": "https://example.com", "snippet": "A test snippet", "source_type": "web", "relevance_score": 0.8, "engine": "google"}
        ]
        papers = [
            {"title": "Test Paper", "authors": ["Author A"], "abstract": "Abstract text", "url": "https://arxiv.org/abs/1234", "published": "2025-01-01"}
        ]

        markdown, path = gen.generate(
            topic="test topic",
            sources=sources,
            arxiv_papers=papers,
            depth="standard",
        )

        assert "## Summary" in markdown
        assert "## Key Findings" in markdown
        assert "## Sources" in markdown
        assert "## Further Reading" in markdown
        assert "test topic" in markdown

    def test_report_includes_academic_papers(self):
        """Academic papers section appears when papers are provided."""
        from Agents.Mimir.research_tools import ReportGenerator

        gen = ReportGenerator()
        papers = [
            {"title": "Attention Is All You Need", "authors": ["Vaswani", "Shazeer"], "abstract": "We propose a new network architecture", "url": "https://arxiv.org/abs/1706.03762", "published": "2017-06-12"}
        ]

        markdown, _ = gen.generate("transformers", sources=[], arxiv_papers=papers, depth="standard")

        assert "## Academic Papers" in markdown
        assert "Attention Is All You Need" in markdown
        assert "Vaswani" in markdown

    def test_report_empty_sources_graceful(self):
        """Reports handle empty sources gracefully."""
        from Agents.Mimir.research_tools import ReportGenerator

        gen = ReportGenerator()
        markdown, _ = gen.generate("obscure topic", sources=[], arxiv_papers=[], depth="quick")

        assert "## Summary" in markdown
        assert "0 web sources" in markdown


# ── Test 4: Source ranking ──────────────────────────────────────────────────

class TestSourceRanking:
    """Mimir's sieve separates gold from sediment."""

    def test_rank_by_relevance(self):
        """More relevant sources score higher."""
        from Agents.Mimir.research_tools import SourceAnalyzer

        analyzer = SourceAnalyzer()
        sources = [
            {"title": "Quantum Computing Basics", "url": "https://example.com/quantum", "snippet": "Quantum computing uses quantum bits", "source_type": "web", "published": "2025-01-01"},
            {"title": "Cooking Recipes", "url": "https://example.com/cook", "snippet": "How to make pasta at home", "source_type": "web", "published": "2025-01-01"},
        ]

        ranked = analyzer.rank(sources, topic="quantum computing", top_k=2)

        assert len(ranked) <= 2
        # Quantum should rank higher than cooking for this topic
        assert ranked[0]["title"] == "Quantum Computing Basics"

    def test_rank_by_credibility(self):
        """ArXiv sources receive credibility bonus."""
        from Agents.Mimir.research_tools import SourceAnalyzer

        analyzer = SourceAnalyzer()
        sources = [
            {"title": "ML Research", "url": "https://arxiv.org/abs/1234", "snippet": "Research on machine learning", "source_type": "arxiv", "published": "2025-01-01"},
            {"title": "ML Blog", "url": "https://random-blog.com/ml", "snippet": "Research on machine learning", "source_type": "web", "published": "2025-01-01"},
        ]

        ranked = analyzer.rank(sources, topic="machine learning", top_k=2)

        assert ranked[0]["source_type"] == "arxiv"

    def test_rank_respects_top_k(self):
        """SourceAnalyzer returns at most top_k sources."""
        from Agents.Mimir.research_tools import SourceAnalyzer

        analyzer = SourceAnalyzer()
        sources = [
            {"title": f"Source {i}", "url": f"https://example.com/{i}", "snippet": f"About quantum {i}", "source_type": "web", "published": "2025-01-01"}
            for i in range(10)
        ]

        ranked = analyzer.rank(sources, topic="quantum", top_k=3)
        assert len(ranked) == 3


# ── Test 5: Depth level configuration ───────────────────────────────────────

class TestDepthConfiguration:
    """The depths of the well are measured precisely."""

    def test_quick_depth_settings(self):
        """Quick depth uses minimal resources."""
        from Agents.Mimir.agent import DEPTH_CONFIGS
        quick = DEPTH_CONFIGS["quick"]
        assert quick["max_sources"] == 5
        assert quick["max_arxiv_papers"] == 3
        assert quick["timeout_seconds"] == 120

    def test_standard_depth_settings(self):
        """Standard depth balances breadth and depth."""
        from Agents.Mimir.agent import DEPTH_CONFIGS
        standard = DEPTH_CONFIGS["standard"]
        assert standard["max_sources"] == 10
        assert standard["max_arxiv_papers"] == 5
        assert standard["timeout_seconds"] == 600

    def test_deep_depth_settings(self):
        """Deep depth uses maximum resources."""
        from Agents.Mimir.agent import DEPTH_CONFIGS
        deep = DEPTH_CONFIGS["deep"]
        assert deep["max_sources"] == 20
        assert deep["max_arxiv_papers"] == 10
        assert deep["timeout_seconds"] == 900


# ── Test 6: is_available check ───────────────────────────────────────────────

class TestAvailability:
    """The Well of Wisdom never truly dries."""

    @pytest.mark.asyncio
    async def test_mimir_always_available(self, mimir):
        """Mimir is always available — mock fallback ensures this."""
        result = await mimir.is_available()
        assert result is True


# ── Test 7: Markdown output formatting ───────────────────────────────────────

class TestMarkdownFormatting:
    """The tapestry must be woven with proper formatting."""

    def test_slugify(self):
        """Topics are properly slugified for filenames."""
        from Agents.Mimir.agent import MimirAgent

        assert MimirAgent._slugify("Quantum Computing 101") == "quantum-computing-101"
        assert MimirAgent._slugify("AI/ML & Deep Learning!") == "aiml-deep-learning"
        assert MimirAgent._slugify("  spaces  and___underscores  ") == "spaces-and-underscores"

    def test_report_markdown_structure(self):
        """Reports follow proper markdown structure."""
        from Agents.Mimir.research_tools import ReportGenerator

        gen = ReportGenerator()
        sources = [
            {"title": "Test Source", "url": "https://example.com", "snippet": "Test", "source_type": "web", "relevance_score": 0.5, "engine": "test"}
        ]

        markdown, _ = gen.generate("neural networks", sources=sources, arxiv_papers=[], depth="standard")

        # Must start with H1 title
        assert markdown.startswith("# ")
        # Must contain blockquote metadata
        assert ">" in markdown
        # Must contain all sections
        assert "## Summary" in markdown
        assert "## Key Findings" in markdown
        assert "## Sources" in markdown
        assert "## Further Reading" in markdown
        # Must have footer
        assert "Mimir" in markdown


# ── Test 8: File saving to Knowledge directory ───────────────────────────────

class TestFileSaving:
    """Wisdom preserved in the archives of Svartalfheim."""

    @pytest.mark.asyncio
    async def test_save_report_creates_file(self, mimir, tmp_path):
        """Reports are saved to the specified output directory."""
        mimir._output_dir = tmp_path / "Knowledge"

        with patch.object(mimir._web_search, "search", new_callable=AsyncMock) as mock_web, \
             patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:

            mock_web.return_value = [
                {"title": "Test", "url": "https://example.com", "snippet": "Test data", "source_type": "mock", "engine": "test", "published": "2025-01-01"}
            ]
            mock_arxiv.return_value = []

            result = await mimir.research("test file saving", depth="quick")

            assert result.exists()
            assert result.name.startswith("mimir-")
            assert result.name.endswith(".md")
            assert "test-file-saving" in result.name

            content = result.read_text(encoding="utf-8")
            assert "test file saving" in content.lower()

            # Cleanup
            result.unlink()

    @pytest.mark.asyncio
    async def test_save_report_creates_directory(self, mimir, tmp_path):
        """Output directories are created if they don't exist."""
        deep_dir = tmp_path / "nested" / "deep" / "dir"
        mimir._output_dir = deep_dir

        with patch.object(mimir._web_search, "search", new_callable=AsyncMock) as mock_web, \
             patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:

            mock_web.return_value = []
            mock_arxiv.return_value = []

            result = await mimir.research("directory creation", depth="quick")

            assert deep_dir.exists()
            assert result.exists()

            # Cleanup
            result.unlink()

    @pytest.mark.asyncio
    async def test_execute_returns_path(self, mimir, tmp_path):
        """execute() returns the report file path."""
        mimir._output_dir = tmp_path / "Knowledge"

        with patch.object(mimir._web_search, "search", new_callable=AsyncMock) as mock_web, \
             patch.object(mimir._arxiv_search, "search", new_callable=AsyncMock) as mock_arxiv:

            mock_web.return_value = []
            mock_arxiv.return_value = []

            result = await mimir.execute("test execute", context={"depth": "quick"})

            path = Path(result)
            assert path.exists()
            assert path.name.endswith(".md")

            # Cleanup
            path.unlink()