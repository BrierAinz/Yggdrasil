"""
Lilith Dashboard CLI Tool — /dashboard command handler
=======================================================
Manja el comando /dashboard desde la CLI de Lilith.
Subcomandos: start, stop, status, open
"""

import logging
import webbrowser
from typing import Optional

from Lilith.Dashboard.server import DashboardServer, get_dashboard

logger = logging.getLogger("Lilith.tools.dashboard")


def handle_dashboard_command(args: str, lilith_instance=None) -> str:
    """Maneja el comando /dashboard con subcomandos.

    Uso:
        /dashboard start    — Inicia el dashboard
        /dashboard stop     — Detiene el dashboard
        /dashboard status   — Muestra estado del dashboard
        /dashboard open     — Abre el navegador
        /dashboard          — Alias de /dashboard start
    """
    parts = args.strip().split()
    subcommand = parts[0].lower() if parts else "start"
    sub_args = parts[1:] if len(parts) > 1 else []

    if subcommand in ("start", "run", "launch"):
        return _cmd_start(lilith_instance)
    elif subcommand in ("stop", "kill", "close"):
        return _cmd_stop()
    elif subcommand in ("status", "info", "state"):
        return _cmd_status()
    elif subcommand in ("open", "browser", "web"):
        return _cmd_open()
    elif subcommand in ("help", "?"):
        return _cmd_help()
    else:
        return f"[Dashboard] Subcomando desconocido: '{subcommand}'. Usa: start, stop, status, open"


def _cmd_start(lilith_instance=None) -> str:
    """Inicia el dashboard."""
    try:
        dashboard = get_dashboard(lilith_instance=lilith_instance)

        if dashboard._running:
            return (
                "[Dashboard] Ya está ejecutándose.\n"
                f"  HTTP: http://{dashboard.host}:{dashboard.port + 1}\n"
                f"  WS:   ws://{dashboard.host}:{dashboard.port}"
            )

        dashboard.start()

        return (
            "[Dashboard] Servidor iniciado.\n"
            f"  HTTP: http://{dashboard.host}:{dashboard.port + 1}\n"
            f"  WS:   ws://{dashboard.host}:{dashboard.port}\n"
            f"  Clientes conectados: {len(dashboard._ws_clients)}\n\n"
            "Abre en tu navegador: /dashboard open"
        )
    except Exception as e:
        logger.error(f"[Dashboard] Error al iniciar: {e}")
        return f"[Dashboard] Error al iniciar: {e}"


def _cmd_stop() -> str:
    """Detiene el dashboard."""
    try:
        dashboard = get_dashboard()

        if not dashboard._running:
            return "[Dashboard] No está ejecutándose."

        dashboard.stop()
        return "[Dashboard] Servidor detenido."
    except Exception as e:
        logger.error(f"[Dashboard] Error al detener: {e}")
        return f"[Dashboard] Error al detener: {e}"


def _cmd_status() -> str:
    """Muestra estado del dashboard."""
    try:
        dashboard = get_dashboard()
        status = dashboard.get_status()

        lines = [
            "[Dashboard] Estado:",
            f"  Ejecutándose:  {'Sí' if status['running'] else 'No'}",
            f"  Host:          {status['host']}",
            f"  Puerto WS:     {status['port']}",
            f"  Puerto HTTP:   {status['http_port']}",
            f"  Clientes:      {status['clients_connected']}",
            f"  Mensajes:      {status['chat_messages']}",
            f"  Paneles:       {', '.join(status['panes'])}",
        ]

        return "\n".join(lines)
    except Exception as e:
        return f"[Dashboard] Error obteniendo estado: {e}"


def _cmd_open() -> str:
    """Abre el dashboard en el navegador."""
    try:
        dashboard = get_dashboard()
        url = f"http://{dashboard.host}:{dashboard.port + 1}"

        if not dashboard._running:
            return (
                f"[Dashboard] No está ejecutándose.\n"
                f"Ejecuta /dashboard start primero."
            )

        webbrowser.open(url)
        return f"[Dashboard] Abriendo navegador: {url}"
    except Exception as e:
        return f"[Dashboard] Error abriendo navegador: {e}"


def _cmd_help() -> str:
    """Muestra ayuda del comando /dashboard."""
    return """[Dashboard] Comandos disponibles:
  /dashboard start   — Inicia el servidor dashboard
  /dashboard stop    — Detiene el servidor
  /dashboard status   — Muestra estado
  /dashboard open     — Abre en el navegador
  /dashboard help     — Esta ayuda

El dashboard ofrece:
  - Chat en tiempo real con Lilith
  - Terminal embebida
  - Panel de estado del sistema (Swarm, MCP, Model)
  - Búsqueda en memoria
  - Multi-pane layout configurable
  - Tema Dark Fantasy"""
