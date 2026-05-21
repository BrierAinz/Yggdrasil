"""SmartToolRouter — unified interface for semantic matching, chaining, recovery, and analytics."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lilith_tools.router.analytics import ToolAnalytics, ToolUsage
from lilith_tools.router.chainer import ChainExecutor, ChainResult, ToolChain
from lilith_tools.router.matcher import MatchResult, ToolMatcher
from lilith_tools.router.recovery import FallbackChain, RecoveryManager, RetryPolicy


if TYPE_CHECKING:
    from pathlib import Path

    from lilith_tools.base import ToolResult
    from lilith_tools.registry import ToolRegistry


class SmartToolRouter:
    """High-level router that combines semantic matching, chaining, recovery,
    and analytics into a single facade.

    Usage::

        router = SmartToolRouter(ToolRegistry)
        matches = router.find_tools("search the web")
        result  = router.execute_tool("web_search", {"query": "python"})
    """

    def __init__(
        self,
        registry: ToolRegistry,
        analytics_path: Path | None = None,
    ) -> None:
        self.registry = registry
        self.matcher = ToolMatcher()
        self.executor = ChainExecutor(registry)
        self.recovery = RecoveryManager(registry)
        self.analytics = ToolAnalytics(db_path=analytics_path)

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    def find_tools(self, query: str, top_k: int = 3) -> list[MatchResult]:
        """Find the most relevant tools for a natural-language *query*."""
        tools = self.registry._tools
        return self.matcher.match(query, tools, top_k=top_k)

    # ------------------------------------------------------------------
    # Execution with retry
    # ------------------------------------------------------------------

    def execute_tool(
        self,
        name: str,
        params: dict[str, Any],
        retry_policy: RetryPolicy | None = None,
    ) -> ToolResult:
        """Execute a tool by *name*, optionally retrying on failure."""
        start = time.time()
        result = self.recovery.execute_with_retry(name, params, policy=retry_policy)
        duration_ms = (time.time() - start) * 1000

        # Record analytics
        self.analytics.record(
            ToolUsage(
                tool_name=name,
                timestamp=time.time(),
                success=result.success,
                duration_ms=duration_ms,
                error=result.error,
            )
        )
        return result

    # ------------------------------------------------------------------
    # Fallback execution
    # ------------------------------------------------------------------

    def execute_with_fallback(
        self,
        chain: FallbackChain,
        params: dict[str, Any],
    ) -> ToolResult:
        """Execute a *FallbackChain*, trying each tool until one succeeds."""
        start = time.time()
        result = self.recovery.execute_with_fallback(chain, params)
        duration_ms = (time.time() - start) * 1000

        self.analytics.record(
            ToolUsage(
                tool_name=chain.primary,
                timestamp=time.time(),
                success=result.success,
                duration_ms=duration_ms,
                error=result.error,
            )
        )
        return result

    # ------------------------------------------------------------------
    # Chain execution
    # ------------------------------------------------------------------

    def execute_chain(
        self,
        chain: ToolChain,
        context: dict[str, Any] | None = None,
    ) -> ChainResult:
        """Execute a *ToolChain* and record analytics for each step."""
        start = time.time()
        result = self.executor.execute(chain, context=context)
        duration_ms = (time.time() - start) * 1000

        for step in chain.steps:
            self.analytics.record(
                ToolUsage(
                    tool_name=step.tool_name,
                    timestamp=time.time(),
                    success=result.success,
                    duration_ms=duration_ms / max(len(chain.steps), 1),
                    error="; ".join(result.errors) if result.errors else "",
                )
            )
        return result

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_recommendations(self) -> list[dict[str, Any]]:
        """Return analytics-based recommendations for tool optimisation."""
        return self.analytics.get_recommendations()
