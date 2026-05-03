"""
Tests del sistema de Graceful Shutdown & Crash Recovery
========================================================
Verifica que las Norns cierren los hilos del destino ordenadamente.
"""

import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from Lilith.Core.graceful_shutdown import (
    CRASH_MARKER,
    check_crash_recovery,
    clear_crash_marker,
    execute_shutdown,
    register_shutdown_hook,
    request_shutdown,
    save_crash_marker,
    setup_graceful_shutdown,
    _shutdown_hooks,
    _shutdown_requested,
    _shutdown_complete,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Limpia estado global entre tests."""
    _shutdown_hooks.clear()
    _shutdown_requested.clear()
    _shutdown_complete.clear()
    # Usar temp dir para crash marker
    original_marker = CRASH_MARKER
    yield
    # Cleanup
    _shutdown_hooks.clear()
    _shutdown_requested.clear()
    _shutdown_complete.clear()
    if original_marker.exists():
        try:
            original_marker.unlink()
        except Exception:
            pass


# ─── Crash Marker ────────────────────────────────────────────────────────

class TestCrashMarker:
    """Tests del marcador de crash para recuperación de sesiones."""

    def test_save_crash_marker_creates_file(self, tmp_path):
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", tmp_path / "test_crash"):
            save_crash_marker("session_abc123")
            assert (tmp_path / "test_crash").exists()
            assert (tmp_path / "test_crash").read_text() == "session_abc123"

    def test_check_crash_recovery_returns_session(self, tmp_path):
        marker = tmp_path / "test_crash"
        marker.write_text("session_xyz789")
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            result = check_crash_recovery()
            assert result == "session_xyz789"

    def test_check_crash_recovery_none_when_no_marker(self, tmp_path):
        marker = tmp_path / "nonexistent"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            result = check_crash_recovery()
            assert result is None

    def test_clear_crash_marker_removes_file(self, tmp_path):
        marker = tmp_path / "test_crash"
        marker.write_text("session_abc")
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            clear_crash_marker()
            assert not marker.exists()

    def test_clear_crash_marker_no_error_if_missing(self, tmp_path):
        marker = tmp_path / "nonexistent"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            clear_crash_marker()  # No debe lanzar excepción

    def test_full_crash_recovery_cycle(self, tmp_path):
        """Simula: inicio -> crash -> recovery -> cleanup."""
        marker = tmp_path / "test_crash"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            # 1. Inicio normal: guardar marker
            save_crash_marker("session_001")
            assert marker.exists()

            # 2. Simular crash (no se ejecuta clear_crash_marker)
            # 3. Próximo inicio: detectar crash
            recovered = check_crash_recovery()
            assert recovered == "session_001"

            # 4. Restaurar sesión y limpiar
            clear_crash_marker()
            assert not marker.exists()

            # 5. Siguiente inicio: no hay crash
            recovered = check_crash_recovery()
            assert recovered is None

    def test_save_crash_marker_overwrites(self, tmp_path):
        marker = tmp_path / "test_crash"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            save_crash_marker("session_old")
            save_crash_marker("session_new")
            assert marker.read_text() == "session_new"


# ─── Shutdown Hooks ──────────────────────────────────────────────────────

class TestShutdownHooks:
    """Tests del sistema de hooks de cierre ordenado."""

    def test_register_shutdown_hook(self):
        hook = MagicMock()
        register_shutdown_hook(hook)
        assert hook in _shutdown_hooks

    def test_execute_shutdown_runs_hooks(self):
        hook1 = MagicMock()
        hook2 = MagicMock()
        register_shutdown_hook(hook1)
        register_shutdown_hook(hook2)

        execute_shutdown()

        # LIFO order: hook2 primero, hook1 segundo
        hook2.assert_called_once()
        hook1.assert_called_once()

    def test_execute_shutdown_lifo_order(self):
        """Los hooks se ejecutan en orden LIFO (último registrado, primero ejecutado)."""
        call_order = []

        def hook_a():
            call_order.append("A")

        def hook_b():
            call_order.append("B")

        register_shutdown_hook(hook_a)
        register_shutdown_hook(hook_b)

        execute_shutdown()

        assert call_order == ["B", "A"]

    def test_execute_shutdown_handles_exception(self):
        """Si un hook falla, los demás se ejecutan igualmente."""
        call_order = []

        def hook_good():
            call_order.append("good")

        def hook_bad():
            raise RuntimeError("Oops")

        register_shutdown_hook(hook_good)
        register_shutdown_hook(hook_bad)

        execute_shutdown()

        # hook_bad se ejecuta y falla, hook_good se ejecuta igualmente
        assert "good" in call_order

    def test_execute_shutdown_idempotent(self):
        """execute_shutdown solo ejecuta hooks una vez."""
        hook = MagicMock()
        register_shutdown_hook(hook)

        execute_shutdown()
        execute_shutdown()  # Segunda llamada

        hook.assert_called_once()

    def test_request_shutdown_sets_event(self):
        request_shutdown()
        assert _shutdown_requested.is_set()

    def test_request_shutdown_idempotent(self):
        """Múltiples solicitudes no causan problemas."""
        hook = MagicMock()
        register_shutdown_hook(hook)

        # Ejecutar shutdown manualmente
        execute_shutdown()

        # Segunda ejecución no llama hooks de nuevo
        execute_shutdown()

        # hook se llamó exactamente una vez (orden LIFO)
        hook.assert_called_once()


# ─── Signal Handlers ─────────────────────────────────────────────────────

class TestSignalHandlers:
    """Tests de configuración de signal handlers."""

    def test_setup_graceful_shutdown_no_error(self):
        """setup_graceful_shutdown no lanza excepciones."""
        mock_hook = MagicMock()
        # No podemos realmente testear signals en tests,
        # pero verificamos que la configuración no crashea
        original_signal = __import__("signal")
        setup_graceful_shutdown(on_shutdown=mock_hook)

    def test_graceful_shutdown_registers_hook(self):
        hook = MagicMock()
        setup_graceful_shutdown(on_shutdown=hook)
        assert hook in _shutdown_hooks


# ─── Integration ─────────────────────────────────────────────────────────

class TestShutdownIntegration:
    """Tests de integración del sistema de cierre ordenado."""

    def test_shutdown_cycle(self, tmp_path):
        """Ciclo completo: guardar marker, ejecutar shutdown, limpiar."""
        marker = tmp_path / "test_crash"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            # 1. Inicio: guardar marker
            save_crash_marker("session_integration")

            # 2. Registrar hook de cleanup
            cleanup_called = []

            def cleanup():
                cleanup_called.append(True)
                clear_crash_marker()

            register_shutdown_hook(cleanup)

            # 3. Cerrar ordenadamente
            execute_shutdown()

            # 4. Verificar que cleanup se ejecutó
            assert len(cleanup_called) == 1

    def test_crash_then_recovery_then_shutdown(self, tmp_path):
        """Simula crash -> recovery -> shutdown limpio."""
        marker = tmp_path / "test_crash"
        with patch("Lilith.Core.graceful_shutdown.CRASH_MARKER", marker):
            # 1. Inicio: guardar marker
            save_crash_marker("session_abc")

            # 2. Simular crash (no se ejecutó shutdown)

            # 3. Próximo inicio: detectar crash
            assert check_crash_recovery() == "session_abc"

            # 4. Registrar shutdown hook que limpia marker
            def cleanup():
                clear_crash_marker()

            register_shutdown_hook(cleanup)
            execute_shutdown()

            # 5. Verificar que marker se limpió
            assert not marker.exists()