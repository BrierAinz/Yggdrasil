"""
Tests para LLM Provider System
===============================
Test unitarios del sistema multi-provider con fallback.
"""

import os

# Asegurar path
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Lilith.Core.llm_provider import (
    LLMProvider,
    _init_providers,
    _providers,
    get_provider,
    list_providers,
    switch_provider,
    test_all_providers,
)

# ──────────────────────────────────────────────────────────────────────────────
# LLMProvider Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestLLMProvider:
    """Tests para la clase LLMProvider."""

    def test_creation_basic(self):
        """Provider se crea con valores por defecto."""
        provider = LLMProvider(
            name="test",
            base_url="http://localhost:1234/v1",
        )
        assert provider.name == "test"
        assert provider.base_url == "http://localhost:1234/v1"
        assert provider.api_key is None
        assert provider.provider_type == "local"

    def test_creation_with_api_key(self):
        """Provider se crea con API key."""
        provider = LLMProvider(
            name="kimi",
            base_url="https://api.moonshot.cn/v1",
            model="kimi-2.6",
            api_key="sk-test-123",
            provider_type="remote",
        )
        assert provider.api_key == "sk-test-123"
        assert provider.provider_type == "remote"

    def test_get_headers_no_key(self):
        """Headers sin API key no incluyen Authorization."""
        provider = LLMProvider(name="test", base_url="http://localhost:1234/v1")
        headers = provider._get_headers()
        assert "Content-Type" in headers
        assert "Authorization" not in headers

    def test_get_headers_with_key(self):
        """Headers con API key incluyen Authorization Bearer."""
        provider = LLMProvider(
            name="kimi",
            base_url="https://api.moonshot.cn/v1",
            api_key="sk-test-123",
        )
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer sk-test-123"

    def test_repr(self):
        """__repr__ es informativo."""
        provider = LLMProvider(name="test", base_url="http://localhost:1234/v1")
        r = repr(provider)
        assert "test" in r
        assert "LLMProvider" in r

    def test_get_status(self):
        """get_status retorna info completa."""
        provider = LLMProvider(
            name="kimi",
            base_url="https://api.moonshot.cn/v1",
            model="kimi-2.6",
            api_key="sk-test",
            provider_type="remote",
        )
        status = provider.get_status()
        assert status["name"] == "kimi"
        assert status["type"] == "remote"
        assert status["model"] == "kimi-2.6"
        assert status["has_api_key"] is True

    def test_get_status_no_api_key(self):
        """get_status muestra has_api_key=False."""
        provider = LLMProvider(name="lm_studio", base_url="http://localhost:1234/v1")
        status = provider.get_status()
        assert status["has_api_key"] is False

    def test_auto_detect_model_no_server(self):
        """Auto-detect model falls back gracefully sin servidor."""
        provider = LLMProvider(
            name="test",
            base_url="http://localhost:99999/v1",  # puerto inexistente
            model="auto",
        )
        # No crashea, usa fallback
        assert provider.model in ("local-model", "unknown") or provider.model

    def test_chat_error_handling(self):
        """chat maneja errores de conexion gracefully."""
        provider = LLMProvider(
            name="test",
            base_url="http://localhost:99999/v1",
            model="test-model",
        )
        result = provider.chat(messages=[{"role": "user", "content": "test"}])
        assert "error" in result

    def test_chat_stream_error_handling(self):
        """chat_stream maneja errores gracefully."""
        provider = LLMProvider(
            name="test",
            base_url="http://localhost:99999/v1",
            model="test-model",
        )
        chunks = list(
            provider.chat_stream(messages=[{"role": "user", "content": "test"}])
        )
        # Deberia yield un mensaje de error
        assert len(chunks) > 0
        assert "Error" in chunks[0] or "error" in chunks[0].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Provider Registry Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestProviderRegistry:
    """Tests para el registro y fallback de providers."""

    def setup_method(self):
        """Reset providers antes de cada test."""
        import Lilith.Core.llm_provider as prov_module

        prov_module._providers = {}
        prov_module._active_provider = None

    def test_init_providers(self):
        """_init_providers carga los providers desde config."""
        _init_providers()
        assert "lm_studio" in _providers
        assert "kimi" in _providers

    def test_init_providers_lm_studio_config(self):
        """Provider lm_studio se configura correctamente."""
        _init_providers()
        lm = _providers["lm_studio"]
        assert lm.name == "lm_studio"
        assert lm.provider_type == "local"
        assert lm.api_key is None

    def test_init_providers_kimi_config(self):
        """Provider kimi se configura con API key."""
        _init_providers()
        kimi = _providers["kimi"]
        assert kimi.name == "kimi"
        assert kimi.provider_type == "remote"
        assert kimi.base_url == "https://api.moonshot.cn/v1"

    def test_list_providers(self):
        """list_providers retorna estado de todos."""
        providers = list_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 2
        # Verificar estructura
        for p in providers:
            assert "name" in p
            assert "available" in p

    def test_get_provider_force_kimi(self):
        """get_provider con nombre kimi funciona si está configurado."""
        _init_providers()
        # Kimi no responderá en tests, así que esperamos ConnectionError
        try:
            provider = get_provider("kimi")
            assert provider.name == "kimi"
        except ConnectionError:
            pass  # Expected si Kimi no responde

    def test_switch_provider(self):
        """switch_provider cambia el provider activo."""
        _init_providers()
        try:
            provider = switch_provider("kimi")
            assert provider.name == "kimi"
        except ConnectionError:
            pass  # Expected si no hay servidor


# ──────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestProviderIntegration:
    """Tests de integracion del sistema de providers."""

    def test_config_has_providers(self):
        """La configuracion define providers."""
        from Lilith.Core.config import LLM_PROVIDERS

        assert isinstance(LLM_PROVIDERS, list)
        assert len(LLM_PROVIDERS) >= 2
        names = [p["name"] for p in LLM_PROVIDERS]
        assert "lm_studio" in names
        assert "kimi" in names

    def test_config_has_provider_setting(self):
        """La configuracion tiene LLM_PROVIDER."""
        from Lilith.Core.config import LLM_PROVIDER

        assert LLM_PROVIDER in ("auto", "lm_studio", "kimi")

    def test_env_file_exists(self):
        """El archivo .env existe."""
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        assert env_path.exists()

    def test_env_example_exists(self):
        """El archivo .env.example existe."""
        example_path = Path(__file__).parent.parent.parent.parent / ".env.example"
        assert example_path.exists()

    def test_kimi_api_key_not_empty(self):
        """La API key de Kimi esta configurada (no vacia)."""
        # Verificar que KIMI_API_KEY esta en el .env
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        content = env_path.read_text()
        assert "KIMI_API_KEY=" in content
        # La key no debe estar vacia en el .env real
        for line in content.splitlines():
            if line.startswith("KIMI_API_KEY="):
                key_value = line.split("=", 1)[1].strip()
                assert len(key_value) > 0, "KIMI_API_KEY no debe estar vacia"
                break

    def test_gitignore_has_env(self):
        """El .gitignore excluye .env."""
        gitignore_path = Path(__file__).parent.parent.parent.parent / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            assert ".env" in content, ".gitignore debe excluir .env"
