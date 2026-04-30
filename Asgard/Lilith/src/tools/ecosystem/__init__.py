"""
Lilith Ecosystem Tools (Phase 3)
Optional tools that expand Lilith's capabilities
"""

# WebBrowser - Requires playwright (install: pip install playwright)
try:
    from .web_browser import WebBrowser
except ImportError:
    WebBrowser = None

# Research - Requires requests and beautifulsoup (already installed)
try:
    from .research import Research
except ImportError:
    Research = None

# ImageProcessor - Requires ComfyUI server running
try:
    from .image_processor import ImageProcessor
except ImportError:
    ImageProcessor = None

__all__ = ["WebBrowser", "Research", "ImageProcessor"]
