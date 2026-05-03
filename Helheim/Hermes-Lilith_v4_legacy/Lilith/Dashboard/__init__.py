"""
Lilith Dashboard v3.0 — Web UI multi-pane con tema dark fantasy
================================================================
Backend WebSocket que sirve el frontend y maneja comunicación
real-time con el core de Lilith.
"""

from .server import DashboardServer, get_dashboard

__all__ = ["DashboardServer", "get_dashboard"]
