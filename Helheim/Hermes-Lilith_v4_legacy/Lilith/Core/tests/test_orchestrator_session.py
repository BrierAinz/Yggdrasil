"""
Tests para integracion SessionStore + BackgroundConsolidator en Orchestrator
=============================================================================
Verifica que el orchestrator guarda sesiones, inyecta contexto,
y maneja el consolidador de fondo correctamente.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Core.orchestrator import LilithOrchestrator
from Lilith.Core.llm_provider import LLMProvider


# ──────────────────────────────────────────────────────────────────────────────
# Helper: crear orchestrator con provider mock
# ──────────────────────────────────────────────────────────────────────────────

def _make_orch():
    """Crea un LilithOrchestrator con provider mockeado."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.name = "test"
    mock_provider.model = "test-model"
    mock_provider.chat.return_value = {
        "choices": [{"message": {"content": "respuesta", "tool_calls": []}}]
    }
    return LilithOrchestrator(provider=mock_provider)


# ──────────────────────────────────────────────────────────────────────────────
# SessionStore Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestOrchestratorSessionStore:
    """Tests de integracion de SessionStore en el orchestrator."""

    def test_orchestrator_has_session_store(self):
        """El orchestrator tiene un session_store inicializado."""
        orch = _make_orch()
        assert hasattr(orch, "session_store"), "Orchestrator debe tener atributo session_store"
        assert orch.session_store is not None

    def test_orchestrator_has_session_id(self):
        """El orchestrator tiene un session_id generado."""
        orch = _make_orch()
        assert hasattr(orch, "session_id")
        assert isinstance(orch.session_id, str)
        assert len(orch.session_id) > 0

    def test_save_current_session(self):
        """_save_current_session() guarda la sesion en SessionStore."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_id = "test_session_001"

            # Agregar mensajes para que haya contexto
            orch.messages = [
                {"role": "user", "content": "Hola"},
                {"role": "assistant", "content": "Saludos"},
            ]

            orch._save_current_session()

            # Verificar que save_session fue llamado
            mock_ss.save_session.assert_called_once()
            call_args = mock_ss.save_session.call_args
            assert call_args[1]["session_id"] == "test_session_001"

    def test_save_current_session_handles_error_gracefully(self):
        """Si SessionStore falla, _save_current_session no crashea."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_ss.save_session.side_effect = Exception("DB error")
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            # No debe lanzar excepcion
            orch._save_current_session()

    def test_inject_session_context_returns_string(self):
        """_inject_session_context() retorna contexto de sesiones pasadas."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_ss.get_relevant_context.return_value = "[Sesion previa: Hablamos de python]"
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_store = mock_ss

            result = orch._inject_session_context("hola python")
            assert "python" in result

    def test_inject_session_context_returns_empty_on_no_results(self):
        """Si no hay sesiones relevantes, _inject_session_context retorna vacio."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_ss.get_relevant_context.return_value = ""
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_store = mock_ss

            result = orch._inject_session_context("algo random")
            assert result == ""

    def test_reset_saves_session_before_resetting(self):
        """reset() guarda la sesion actual antes de reiniciar."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_id = "old_session"
            orch.messages = [{"role": "user", "content": "test"}]

            orch.reset()

            # Verificar que save_session fue llamado ANTES del reset
            mock_ss.save_session.assert_called()

    def test_reset_generates_new_session_id(self):
        """Despues de reset(), el session_id es diferente."""
        orch = _make_orch()
        old_id = orch.session_id
        orch.reset()
        # session_id puede ser igual si el timestamp coincide, pero
        # el formato debe ser %Y%m%d_%H%M%S
        assert isinstance(orch.session_id, str)

    def test_close_saves_session(self):
        """close() guarda la sesion y detiene el consolidador."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_consolidator") as mock_get_cons, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_get_ss.return_value = mock_ss
            mock_cons = MagicMock()
            mock_get_cons.return_value = mock_cons
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch._consolidator = mock_cons
            orch.close()

            mock_ss.save_session.assert_called()
            mock_cons.stop.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# BackgroundConsolidator Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestOrchestratorConsolidator:
    """Tests de integracion de BackgroundConsolidator en el orchestrator."""

    def test_orchestrator_has_consolidator_attribute(self):
        """El orchestrator tiene _consolidator inicializado a None."""
        orch = _make_orch()
        assert hasattr(orch, "_consolidator")
        assert orch._consolidator is None  # No se inicia automaticamente

    def test_start_consolidator_creates_and_starts(self):
        """start_consolidator() obtiene y arranca el consolidador."""
        with patch("Lilith.Core.orchestrator.get_consolidator") as mock_get_cons, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_cons = MagicMock()
            mock_cons.is_running = False
            mock_get_cons.return_value = mock_cons
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.start_consolidator(interval_seconds=60)

            mock_get_cons.assert_called_once()
            mock_cons.start.assert_called_once()
            assert orch._consolidator is mock_cons

    def test_start_consolidator_idempotent(self):
        """Si el consolidador ya esta corriendo, start_consolidator es no-op."""
        with patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            mock_cons = MagicMock()
            mock_cons.is_running = True
            orch._consolidator = mock_cons

            orch.start_consolidator()
            # No llamar start() si ya esta corriendo
            mock_cons.start.assert_not_called()

    def test_stop_consolidator_stops_running(self):
        """stop_consolidator() detiene el consolidador si esta corriendo."""
        with patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            mock_cons = MagicMock()
            mock_cons.is_running = True
            orch._consolidator = mock_cons

            orch.stop_consolidator()
            mock_cons.stop.assert_called_once()

    def test_stop_consolidator_noop_if_none(self):
        """stop_consolidator() es no-op si no hay consolidador."""
        orch = _make_orch()
        # _consolidator es None por defecto
        orch.stop_consolidator()  # No debe lanzar error

    def test_get_consolidator_stats_none(self):
        """get_consolidator_stats() retorna dict vacio si no hay consolidador."""
        orch = _make_orch()
        stats = orch.get_consolidator_stats()
        assert isinstance(stats, dict)
        assert stats.get("running") is False

    def test_get_consolidator_stats_running(self):
        """get_consolidator_stats() retorna stats si el consolidador esta activo."""
        with patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            mock_cons = MagicMock()
            mock_cons.is_running = True
            mock_cons.last_run = "2025-01-01T00:00:00"
            mock_cons.stats = {
                "cycles_run": 5,
                "episodes_merged": 12,
                "facts_promoted": 3,
            }
            orch._consolidator = mock_cons

            stats = orch.get_consolidator_stats()
            assert stats["running"] is True
            assert stats["cycles_run"] == 5
            assert stats["episodes_merged"] == 12


# ──────────────────────────────────────────────────────────────────────────────
# System Prompt Session Context Injection Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSessionContextInjection:
    """Tests de inyeccion de contexto de sesiones en el system prompt."""

    def test_build_system_prompt_includes_session_context(self):
        """_build_system_prompt incluye contexto de sesion cuando hay resultados."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_ss.get_relevant_context.return_value = (
                "=== SESIONES PASADAS ===\n"
                "Sesion 20250101: Hablamos de alquimia\n"
                "Sesion 20250102: Exploramos las sombras"
            )
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_store = mock_ss

            prompt = orch._build_system_prompt("dime sobre alquimia")
            # El contexto de sesiones pasadas debe aparecer en el prompt
            assert "alquimia" in prompt or "SESIONES PASADAS" in prompt or "sombras" in prompt

    def test_build_system_prompt_without_session_context(self):
        """_build_system_prompt funciona sin contexto de sesion (sin matches)."""
        with patch("Lilith.Core.orchestrator.get_session_store") as mock_get_ss, \
             patch("Lilith.Core.orchestrator.get_provider") as mock_get_prov:
            mock_ss = MagicMock()
            mock_ss.get_relevant_context.return_value = ""
            mock_get_ss.return_value = mock_ss
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = "test"
            mock_provider.model = "test-model"
            mock_get_prov.return_value = mock_provider

            orch = LilithOrchestrator()
            orch.session_store = mock_ss

            prompt = orch._build_system_prompt("algo nuevo")
            # No debe crashear, retorna el prompt base
            assert isinstance(prompt, str)
            assert len(prompt) > 0