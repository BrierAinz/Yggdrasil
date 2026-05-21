"""Lilith Tools — Sistema de herramientas del agente."""

__version__ = "2.0.0"

from . import filesystem, system
from .base import BaseTool, ToolResult
from .browser import BrowserTool
from .coding import CodingTool
from .filesystem import DirectoryListTool, FileReadTool
from .registry import ToolRegistry
from .system import SystemInfoTool, SystemTimeTool
from .web_search import WebSearchTool


__all__ = [
    "BaseTool",
    "BrowserTool",
    "CodingTool",
    "DirectoryListTool",
    "FileReadTool",
    "SystemInfoTool",
    "SystemTimeTool",
    "ToolRegistry",
    "ToolResult",
    "WebSearchTool",
    "filesystem",
    "system",
]

# Optional router subpackage — only available when extra deps are installed
try:
    from .router import (  # noqa: F401
        ChainExecutor,
        ChainResult,
        ChainStep,
        FallbackChain,
        MatchResult,
        RecoveryManager,
        RetryPolicy,
        SmartToolRouter,
        ToolAnalytics,
        ToolChain,
        ToolMatcher,
        ToolStats,
        ToolUsage,
    )

    __all__.extend(
        [
            "ChainExecutor",
            "ChainResult",
            "ChainStep",
            "FallbackChain",
            "MatchResult",
            "RecoveryManager",
            "RetryPolicy",
            "SmartToolRouter",
            "ToolAnalytics",
            "ToolChain",
            "ToolMatcher",
            "ToolStats",
            "ToolUsage",
        ]
    )
except ImportError:
    pass
