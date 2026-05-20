"""Lilith Tools — Sistema de herramientas del agente."""

__version__ = "2.0.0"

from . import filesystem, system
from .base import BaseTool, ToolResult
from .browser import BrowserTool
from .coding import CodingTool
from .registry import ToolRegistry
from .web_search import WebSearchTool


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
