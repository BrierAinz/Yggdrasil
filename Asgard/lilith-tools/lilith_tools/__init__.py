"""Lilith Tools — Sistema de herramientas del agente."""

from . import filesystem, system
from .base import BaseTool, ToolResult
from .browser import BrowserTool
from .coding import CodingTool
from .registry import ToolRegistry
from .web_search import WebSearchTool


# Auto-register tools that don't use @ToolRegistry.register decorator
WebSearchTool()
BrowserTool()
CodingTool()

__all__ = [
    "BaseTool",
    "BrowserTool",
    "CodingTool",
    "ToolRegistry",
    "ToolResult",
    "WebSearchTool",
    "filesystem",
    "system",
]
