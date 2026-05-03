"""
Graceful Shutdown & Crash Recovery
===================================
Sistema de cierre ordenado y recuperación de sesiones para Lilith v3.

Cuando las Norns deciden cortar un hilo del destino, este módulo
asegura que los ecos de la conversación se preserven en las raíces
del Yggdrasil antes de que el silencio eterno se apodere del realm.

Funcionalidades:
- Signal handler para SIGINT (Ctrl+C) y SIGTERM
- Guardado automático de sesión al cerrar
- Recuperación de sesión tras crash
- Cleanup ordenado de recursos (consolidator, MCP, etc.)
"""

import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Callable, List, Optional

from .lilith_logger import get_logger

logger = get_logger("lilith.shutdown")

# ─── Signal Handler ──────────────────────────────────────────────────────────

_shutdown_hooks: List[Callable] = []
_shutdown_requested = threading.Event()
_shutdown_complete = threading.Event()


def register_shutdown_hook(hook: Callable):
    """Registra una función para ejecutar al cerrar.

    Los ganchos se ejecutan en orden inverso de registro (LIFO).
    Cada hook debe ser seguro de llamar desde un signal handler,
    idealmente rápido y sin I/O bloqueante.

    Args:
        hook: Función sin argumentos a ejecutar al cerrar.
    """
    _shutdown_hooks.append(hook)
    logger.debug("Shutdown hook registrado: %s", hook.__name__ if hasattr(hook, '__name__') else str(hook))


def request_shutdown():
    """Solicita un cierre ordenado del sistema.

    Se puede llamar desde cualquier thread. El cierre real
    se ejecuta en el thread principal.
    """
    if _shutdown_requested.is_set():
        logger.warning("Shutdown ya solicitado — ignorando solicitud duplicada")
        return
    _shutdown_requested.set()
    logger.info("Shutdown solicitado — ejecutando hooks de cierre...")


def execute_shutdown():
    """Ejecuta los hooks de cierre en orden LIFO.

    Las raíces del Yggdrasil absorben los últimos susurros
    antes de que el silencio eterno se apodere del realm.
    """
    if _shutdown_complete.is_set():
        return

    logger.info("Ejecutando %d shutdown hooks...", len(_shutdown_hooks))

    for hook in reversed(_shutdown_hooks):
        try:
            hook()
            logger.debug("Hook completado: %s", hook.__name__ if hasattr(hook, '__name__') else str(hook))
        except Exception as e:
            logger.error("Error en shutdown hook: %s", e)

    _shutdown_complete.set()
    logger.info("Shutdown completo — el realm descansa en paz.")


# ─── Crash Recovery ─────────────────────────────────────────────────────────

CRASH_MARKER = Path.home() / ".lilith" / ".crash_recovery"


def save_crash_marker(session_id: str):
    """Guarda un marcador de sesión activa para recuperación tras crash.

    Si Lilith se cierra inesperadamente, este marcador permite
    restaurar la última sesión en el próximo inicio.

    Args:
        session_id: ID de la sesión actual.
    """
    try:
        CRASH_MARKER.parent.mkdir(parents=True, exist_ok=True)
        CRASH_MARKER.write_text(session_id)
        logger.debug("Crash marker guardado: sesión %s", session_id)
    except Exception as e:
        logger.warning("Error guardando crash marker: %s", e)


def check_crash_recovery() -> Optional[str]:
    """Verifica si hay una sesión recuperable tras crash.

    Si el marcador existe, significa que Lilith se cerró sin
    completar el shutdown ordenado (crash, kill -9, power outage).

    Returns:
        ID de la sesión recuperable, o None si no hay crash previo.
    """
    try:
        if CRASH_MARKER.exists():
            session_id = CRASH_MARKER.read_text().strip()
            logger.info("Crash recovery detectado: sesión %s", session_id)
            return session_id if session_id else None
    except Exception as e:
        logger.warning("Error leyendo crash marker: %s", e)
    return None


def clear_crash_marker():
    """Limpia el marcador de crash tras un cierre exitoso.

    Las Norns confirman que el hilo del destino se cerró
    ordenadamente — el marcador ya no es necesario.
    """
    try:
        if CRASH_MARKER.exists():
            CRASH_MARKER.unlink()
            logger.debug("Crash marker limpiado — cierre exitoso")
    except Exception as e:
        logger.warning("Error limpiando crash marker: %s", e)


# ─── Signal Setup ────────────────────────────────────────────────────────────

_original_sigint = None
_original_sigterm = None


def _handle_signal(signum, frame):
    """Signal handler para cierre ordenado.

    Primer Ctrl+C: solicita shutdown ordenado.
    Segundo Ctrl+C: fuerza salida inmediata.
    """
    if _shutdown_requested.is_set():
        # Segunda señal — salida forzada
        logger.warning("Segunda señal recibida — forzando salida")
        sys.exit(1)

    logger.info("Señal %s recibida — iniciando cierre ordenado", signal.Signals(signum).name)

    # Solicitar cierre ordenado
    request_shutdown()

    # Ejecutar hooks en este thread (el principal)
    execute_shutdown()
    clear_crash_marker()


def setup_signal_handlers():
    """Instala signal handlers para SIGINT y SIGTERM.

    Los Norns vigilan las señales del Yggdrasil — cuando un
    viajero desea partir, se ejecuta un cierre ordenado que
    preserva la memoria de la sesión.
    """
    global _original_sigint, _original_sigterm

    _original_sigint = signal.getsignal(signal.SIGINT)
    _original_sigterm = signal.getsignal(signal.SIGTERM)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.debug("Signal handlers instalados (SIGINT, SIGTERM)")


def restore_signal_handlers():
    """Restaura los signal handlers originales."""
    global _original_sigint, _original_sigterm

    if _original_sigint is not None:
        signal.signal(signal.SIGINT, _original_sigint)
    if _original_sigterm is not None:
        signal.signal(signal.SIGTERM, _original_sigterm)

    logger.debug("Signal handlers restaurados")


# ─── Atexit ─────────────────────────────────────────────────────────────────

def _atexit_handler():
    """Handler de atexit para cleanup de emergencia.

    Se ejecuta cuando el proceso termina normalmente (no por signal).
    """
    if not _shutdown_complete.is_set():
        logger.debug("atexit — ejecutando cleanup de emergencia")
        execute_shutdown()
    clear_crash_marker()


def setup_atexit():
    """Registra el handler de atexit para cleanup de emergencia.

    Las Norns del destino aseguran que incluso en un cierre
    inesperado, los ecos de la sesión se preserven.
    """
    import atexit
    atexit.register(_atexit_handler)
    logger.debug("atexit handler registrado")


# ─── Full Setup ──────────────────────────────────────────────────────────────

def setup_graceful_shutdown(on_shutdown: Optional[Callable] = None):
    """Configura el sistema completo de cierre ordenado.

    Instala signal handlers, atexit y registra hooks de cleanup.

    Args:
        on_shutdown: Función opcional a ejecutar como primer hook
                     (typically save session + stop consolidator).
    """
    # Registrar hook personalizado primero (se ejecuta último en LIFO)
    if on_shutdown:
        register_shutdown_hook(on_shutdown)

    setup_signal_handlers()
    setup_atexit()

    logger.info("Graceful shutdown configurado — las Norns vigilan el Yggdrasil")