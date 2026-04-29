"""Lilith Tools - Sistema de herramientas."""
from . import filesystem, system
from .base import BaseTool, ToolResult
from .registry import ToolRegistry

__all__ = ["BaseTool", "ToolResult", "ToolRegistry"]

from lilith_tools.web_search import WebSearchTool
WebSearchTool()
from lilith_tools.browser import BrowserTool
BrowserTool()
from lilith_tools.coding import CodingTool
CodingTool()