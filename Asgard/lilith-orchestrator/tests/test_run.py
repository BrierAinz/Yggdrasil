"""
Tests for gateway.run — Configuration defaults and main() existence.
"""

import importlib
import os
from unittest.mock import patch


class TestMainFunction:
    """Verify the main() entry point exists and is callable."""

    def test_main_function_exists(self):
        from gateway.run import main

        assert callable(main)

    def test_main_calls_uvicorn_run(self):
        """main() should invoke uvicorn.run with the configured parameters."""
        from gateway import run as run_module

        with (
            patch.object(run_module, "uvicorn") as mock_uvicorn,
            patch.object(run_module, "HOST", "127.0.0.1"),
            patch.object(run_module, "PORT", 9999),
            patch.object(run_module, "WORKERS", 2),
            patch.object(run_module, "LOG_LEVEL", "debug"),
        ):
            run_module.main()

            mock_uvicorn.run.assert_called_once()
            call_kwargs = mock_uvicorn.run.call_args
            # uvicorn.run(APP_REF, host=, port=, workers=, log_level=, ...)
            assert call_kwargs[0][0] == "gateway.gateway:app"
            assert call_kwargs[1]["host"] == "127.0.0.1"
            assert call_kwargs[1]["port"] == 9999
            assert call_kwargs[1]["workers"] == 2
            assert call_kwargs[1]["log_level"] == "debug"


class TestConfigDefaults:
    """Verify environment-driven configuration defaults when no env vars are set."""

    def test_default_host(self):
        from gateway.run import HOST

        # If LILITH_HOST is not set, default should be 0.0.0.0
        assert os.environ.get("LILITH_HOST", "0.0.0.0") == HOST

    def test_default_port(self):
        from gateway.run import PORT

        assert int(os.environ.get("LILITH_PORT", "8000")) == PORT

    def test_default_workers(self):
        from gateway.run import WORKERS

        assert int(os.environ.get("LILITH_WORKERS", "1")) == WORKERS

    def test_default_log_level(self):
        from gateway.run import LOG_LEVEL

        # LOG_LEVEL is lowercased
        assert os.environ.get("LILITH_LOG_LEVEL", "info").lower() == LOG_LEVEL

    def test_env_override_host(self):
        """Setting LILITH_HOST env var should override the default."""
        from gateway import run as run_mod

        with patch.dict(os.environ, {"LILITH_HOST": "192.168.1.1"}, clear=False):
            importlib.reload(run_mod)
            assert run_mod.HOST == "192.168.1.1"
            importlib.reload(run_mod)

    def test_env_override_port(self):
        """Setting LILITH_PORT env var should override the default."""
        from gateway import run as run_mod

        with patch.dict(os.environ, {"LILITH_PORT": "9000"}, clear=False):
            importlib.reload(run_mod)
            assert run_mod.PORT == 9000
            importlib.reload(run_mod)

    def test_app_ref_value(self):
        from gateway.run import APP_REF

        assert APP_REF == "gateway.gateway:app"

    def test_log_level_is_lowercased(self):
        """LOG_LEVEL should always be lowercase even if env var has upper case."""
        from gateway import run as run_mod

        with patch.dict(os.environ, {"LILITH_LOG_LEVEL": "WARNING"}, clear=False):
            importlib.reload(run_mod)
            assert run_mod.LOG_LEVEL == "warning"
            importlib.reload(run_mod)
