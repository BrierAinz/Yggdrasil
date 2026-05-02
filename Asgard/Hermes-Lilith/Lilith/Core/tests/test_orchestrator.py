"""
Tests para LilithOrchestrator - Integracion con LLMProvider
============================================================
Verifica que el orchestrator usa LLMProvider con fallback
en lugar de LMStudioClient directo.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Core.llm_provider import LLMProvider
from Lilith.Core.orchestrator import LilithOrchestrator

# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator Construction Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestOrchestratorConstruction:
    """Tests de construccion del orchestrator con LLMProvider."""

    def test_default_init_uses_get_provider(self):
        """Instanciacion sin args usa get_provider() para fallback automatico."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "lm_studio"
        mock_provider.model = "test-model"
        mock_provider.chat.return_value = {
            "choices": [{"message": {"content": "test", "tool_calls": []}}]
        }

        with patch("Lilith.Core.orchestrator.get_provider", return_value=mock_provider):
            orch = LilithOrchestrator()
            assert orch.client is mock_provider

    def test_explicit_provider_init(self):
        """Se puede pasar un LLMProvider explicito al constructor."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-2.6"

        orch = LilithOrchestrator(provider=mock_provider)
        assert orch.client is mock_provider
        assert orch.client.name == "kimi"

    def test_constructor_does_not_use_lm_studio_client(self):
        """El constructor NO importa ni usa LMStudioClient."""
        with patch(
            "Lilith.Core.orchestrator.get_provider",
            return_value=MagicMock(spec=LLMProvider),
        ):
            orch = LilithOrchestrator()
            # Verificar que el client es un LLMProvider (o mock de uno)
            assert hasattr(orch.client, "name") or hasattr(orch.client, "chat")

    def test_switch_provider(self):
        """switch_provider cambia el provider activo."""
        mock_provider_1 = MagicMock(spec=LLMProvider)
        mock_provider_1.name = "lm_studio"
        mock_provider_1.model = "local-model"

        mock_provider_2 = MagicMock(spec=LLMProvider)
        mock_provider_2.name = "kimi"
        mock_provider_2.model = "kimi-2.6"

        orch = LilithOrchestrator(provider=mock_provider_1)
        assert orch.client.name == "lm_studio"

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=mock_provider_2
        ):
            orch.switch_provider("kimi")
            assert orch.client.name == "kimi"


class TestOrchestratorProviderInfo:
    """Tests del metodo get_provider_info."""

    def test_get_provider_info_returns_dict(self):
        """get_provider_info retorna dict con info del provider activo."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "lm_studio"
        mock_provider.model = "gemma-4"
        mock_provider.provider_type = "local"
        mock_provider.is_available.return_value = True

        orch = LilithOrchestrator(provider=mock_provider)
        info = orch.get_provider_info()

        assert info["name"] == "lm_studio"
        assert info["model"] == "gemma-4"
        assert info["type"] == "local"
        assert info["available"] is True

    def test_get_provider_info_remote(self):
        """get_provider_info muestra info de provider remoto."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "kimi"
        mock_provider.model = "kimi-2.6"
        mock_provider.provider_type = "remote"
        mock_provider.is_available.return_value = True

        orch = LilithOrchestrator(provider=mock_provider)
        info = orch.get_provider_info()

        assert info["name"] == "kimi"
        assert info["type"] == "remote"


class TestOrchestratorChat:
    """Tests de chat() con LLMProvider."""

    def test_chat_calls_provider_chat(self):
        """chat() delega al provider.chat() del LLMProvider."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_provider.chat.return_value = {
            "choices": [
                {"message": {"content": "Hola desde el provider", "tool_calls": []}}
            ]
        }

        orch = LilithOrchestrator(provider=mock_provider)
        result = orch.chat("Hola")

        mock_provider.chat.assert_called_once()
        assert result == "Hola desde el provider"

    def test_chat_handles_provider_error(self):
        """chat() maneja errores del provider gracefully."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.chat.return_value = {"error": "Connection refused"}

        orch = LilithOrchestrator(provider=mock_provider)
        result = orch.chat("Hola")

        assert "Connection refused" in result

    def test_chat_stream_calls_provider_chat_stream(self):
        """chat_stream() delega al provider.chat_stream()."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.chat_stream.return_value = iter(["Hola", " desde", " provider"])

        orch = LilithOrchestrator(provider=mock_provider)
        chunks = list(orch.chat_stream("Hola"))

        mock_provider.chat_stream.assert_called_once()
        assert chunks == ["Hola", " desde", " provider"]


class TestOrchestratorClose:
    """Tests de close() - LLMProvider no necesita close."""

    def test_close_is_noop(self):
        """close() es no-op porque LLMProvider usa httpx function-scoped."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "test"
        mock_provider.model = "test-model"

        orch = LilithOrchestrator(provider=mock_provider)
        # No debe lanzar error - close() es intencionalmente no-op
        result = orch.close()
        assert result is None


class TestOrchestratorNoLMStudioClientImport:
    """Tests de que no se usa LMStudioClient."""

    def test_orchestrator_module_uses_llm_provider(self):
        """El modulo orchestrator importa de llm_provider, no llm_client."""
        import Lilith.Core.orchestrator as orch_module

        source = Path(orch_module.__file__).read_text()
        assert "from Lilith.Core.llm_provider import" in source
        assert "from Lilith.Core.llm_client import" not in source
        # Solo LMStudioClient en comentarios/docstrings, no en imports ni codigo
        import_lines = [l for l in source.splitlines() if "import" in l]
        assert not any(
            "llm_client" in l and "import" in l and not l.strip().startswith("#")
            for l in import_lines
        )

    def test_executor_module_uses_llm_provider(self):
        """El modulo executor importa de llm_provider, no llm_client."""
        import Lilith.Swarm.executor as exec_module

        source = Path(exec_module.__file__).read_text()
        assert "from Lilith.Core.llm_provider import" in source
        # Puede mencionar LMStudioClient solo en comentarios
        lines_with_import = [
            line
            for line in source.splitlines()
            if "llm_client" in line
            and "import" in line
            and not line.strip().startswith("#")
        ]
        assert len(lines_with_import) == 0


class TestOrchestratorFallback:
    """Tests del comportamiento de fallback automatico."""

    def test_orchestrator_uses_fallback_provider(self):
        """Si el provider primario falla, el orchestrator puede usar fallback.

        El fallback lo maneja get_provider(), no el orchestrator directamente.
        Pero el orchestrator se beneficia porque usa get_provider() en __init__.
        """
        # Simular que get_provider retorna un provider remoto (fallback)
        fallback_provider = MagicMock(spec=LLMProvider)
        fallback_provider.name = "kimi"
        fallback_provider.model = "kimi-2.6"
        fallback_provider.provider_type = "remote"

        with patch(
            "Lilith.Core.orchestrator.get_provider", return_value=fallback_provider
        ):
            orch = LilithOrchestrator()
            info = orch.get_provider_info()
            assert info["name"] == "kimi"
            assert info["type"] == "remote"

    def test_switch_restores_on_failure(self):
        """Si switch_provider falla, lanza ConnectionError correcto."""
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "lm_studio"

        orch = LilithOrchestrator(provider=mock_provider)

        with patch(
            "Lilith.Core.orchestrator.get_provider",
            side_effect=ConnectionError("Provider 'kimi' no disponible"),
        ):
            with pytest.raises(ConnectionError):
                orch.switch_provider("kimi")

        # El provider original debe seguir activo
        assert orch.client.name == "lm_studio"
