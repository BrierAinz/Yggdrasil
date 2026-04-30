# Lilith Tools Module
from .browser import get_tools as browser_tools
from .coding import get_tools as coding_tools
from .desktop import get_tools as desktop_tools
from .files import get_tools as file_tools
from .network import get_tools as network_tools
from .system import get_tools as system_tools
from .windows import get_tools as windows_tools

# Todas las tools combinadas
ALL_TOOLS = (
    desktop_tools()
    + file_tools()
    + system_tools()
    + network_tools()
    + coding_tools()
    + windows_tools()
    + browser_tools()
)

__all__ = [
    "ALL_TOOLS",
    "desktop_tools",
    "file_tools",
    "system_tools",
    "network_tools",
    "coding_tools",
    "windows_tools",
    "browser_tools",
]
