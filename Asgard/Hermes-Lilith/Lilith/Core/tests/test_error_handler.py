"""
Tests del sistema de Error Handler
====================================
Verifica la jerarquía de errores y sanitización del Yggdrasil.
"""

import pytest

from Lilith.Core.error_handler import (
    ConfigError,
    LilithError,
    MemoryError,
    ProviderError,
    ToolError,
    format_error,
    sanitize_output,
)


class TestLilithError:
    """Tests de la jerarquía base de errores."""

    def test_lilith_error_is_exception(self):
        assert issubclass(LilithError, Exception)

    def test_lilith_error_message(self):
        err = LilithError("test error message")
        assert str(err) == "test error message"

    def test_lilith_error_can_be_raised(self):
        with pytest.raises(LilithError):
            raise LilithError("test")


class TestProviderError:
    """Tests de errores de LLM provider."""

    def test_provider_error_is_lilith_error(self):
        assert issubclass(ProviderError, LilithError)

    def test_provider_error_with_status_code(self):
        err = ProviderError("lm_studio", "Connection refused", status_code=503)
        assert "[lm_studio]" in str(err)
        assert "503" in str(err)
        assert err.provider == "lm_studio"
        assert err.status_code == 503

    def test_provider_error_without_status_code(self):
        err = ProviderError("kimi", "Timeout")
        assert "[kimi]" in str(err)
        assert "Timeout" in str(err)
        assert err.status_code is None

    def test_provider_error_caught_as_lilith_error(self):
        with pytest.raises(LilithError):
            raise ProviderError("test", "error")


class TestToolError:
    """Tests de errores de tools."""

    def test_tool_error_is_lilith_error(self):
        assert issubclass(ToolError, LilithError)

    def test_tool_error_with_original(self):
        original = ValueError("bad args")
        err = ToolError("screenshot", "Failed to capture", original_error=original)
        assert err.tool_name == "screenshot"
        assert err.original_error is original

    def test_tool_error_message(self):
        err = ToolError("network", "Connection timeout")
        assert "network" in str(err)

    def test_tool_error_without_original(self):
        err = ToolError("system", "Command failed")
        assert err.original_error is None


class TestMemoryError:
    """Tests de errores de memoria."""

    def test_memory_error_is_lilith_error(self):
        assert issubclass(MemoryError, LilithError)

    def test_memory_error_message(self):
        err = MemoryError("Failed to index episode")
        assert "Failed to index episode" in str(err)


class TestConfigError:
    """Tests de errores de configuración."""

    def test_config_error_is_lilith_error(self):
        assert issubclass(ConfigError, LilithError)

    def test_config_error_message(self):
        err = ConfigError("Invalid TOML syntax")
        assert "Invalid TOML syntax" in str(err)


class TestSanitizeOutput:
    """Tests de sanitización de outputs sensibles."""

    def test_removes_bearer_token(self):
        output = "Response: Bearer sk-abc123def456ghi789"
        sanitized = sanitize_output(output)
        assert "sk-abc123" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_removes_api_key_assignment(self):
        output = "Config: api_key=sk-abc123def"
        sanitized = sanitize_output(output)
        assert "sk-abc123" not in sanitized

    def test_removes_ghp_token(self):
        output = "Token: ghp_ABCDEFGHIJKLMNOP"
        sanitized = sanitize_output(output)
        assert "ghp_ABCDE" not in sanitized

    def test_removes_sk_token(self):
        output = "Key: sk-proj-1234567890abcdefghij"
        sanitized = sanitize_output(output)
        assert "sk-proj-" not in sanitized

    def test_preserves_normal_text(self):
        output = "Hello, this is a normal response from Lilith."
        sanitized = sanitize_output(output)
        assert sanitized == output

    def test_empty_string(self):
        assert sanitize_output("") == ""

    def test_none_returns_none(self):
        result = sanitize_output(None)
        assert result == ""

    def test_removes_email(self):
        output = "Contact: user@example.com for details"
        sanitized = sanitize_output(output)
        assert "user@example.com" not in sanitized

    def test_removes_url_with_credentials(self):
        output = "DB: postgresql://admin:password123@db.host:5432/mydb"
        sanitized = sanitize_output(output)
        assert "password123" not in sanitized

    def test_multiple_secrets_in_output(self):
        output = "Bearer sk-abcdefghij1234567890 and api_key=sk-xyz123456789012345 and ghp_TOKENABCDEFGH1234567890"
        sanitized = sanitize_output(output)
        assert "sk-abc" not in sanitized
        assert "sk-xyz" not in sanitized
        assert "ghp_TOKEN" not in sanitized


class TestFormatError:
    """Tests de formateo de errores para display."""

    def test_format_lilith_error(self):
        err = ProviderError("lm_studio", "Connection refused")
        formatted = format_error(err)
        assert "lm_studio" in formatted
        assert "Connection refused" in formatted

    def test_format_generic_error(self):
        err = ValueError("Bad value")
        formatted = format_error(err)
        assert "Bad value" in formatted

    def test_format_error_with_context(self):
        err = RuntimeError("Timeout")
        formatted = format_error(err, context="LLM call")
        assert "LLM call" in formatted or "Timeout" in formatted

    def test_format_nested_error(self):
        original = ConnectionError("Network unreachable")
        err = ToolError("network", "Failed", original_error=original)
        formatted = format_error(err)
        assert "network" in formatted