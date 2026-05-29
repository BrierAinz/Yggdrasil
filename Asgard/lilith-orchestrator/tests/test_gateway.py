"""Tests for gateway.gateway — FastAPI app creation, endpoints, JSON helpers,
CORS middleware.
"""

import sys
from unittest.mock import patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# test_app_creation
# ---------------------------------------------------------------------------


class TestAppCreation:
    """Verify the FastAPI application can be imported and instantiated."""

    def test_app_is_fastapi_instance(self):
        """The 'app' object should be a FastAPI instance."""
        from fastapi import FastAPI
        from gateway.gateway import app as gw_app

        assert isinstance(gw_app, FastAPI)

    def test_app_title_and_version(self):
        from gateway.gateway import app as gw_app

        assert gw_app.title == "Lilith Gateway"
        assert gw_app.version == "1.0.0"


# ---------------------------------------------------------------------------
# test_health_endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Verify /health returns the expected payload with 200."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_payload(self, client: TestClient):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["gateway"] == "lilith-v1"


# ---------------------------------------------------------------------------
# test_config_defaults
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    """Verify that gateway.run module-level defaults are correct."""

    def test_default_host(self):
        from gateway.run import HOST

        # Remove env var if set so we see the real default
        assert HOST == "0.0.0.0"

    def test_default_port(self):
        from gateway.run import PORT

        assert PORT == 8000

    def test_default_workers(self):
        from gateway.run import WORKERS

        assert WORKERS == 1

    def test_default_log_level(self):
        from gateway.run import LOG_LEVEL

        assert LOG_LEVEL == "info"

    def test_app_ref_string(self):
        from gateway.run import APP_REF

        assert APP_REF == "gateway.gateway:app"


# ---------------------------------------------------------------------------
# test_json_dumps_loads
# ---------------------------------------------------------------------------


class TestJsonDumpsLoads:
    """Verify _json_dumps / _json_loads work with both orjson and stdlib."""

    def test_dumps_and_loads_roundtrip(self):
        from gateway.gateway import _json_dumps, _json_loads

        payload = {"name": "Lilith", "value": 42, "nested": {"a": [1, 2, 3]}}
        encoded = _json_dumps(payload)
        assert isinstance(encoded, str)
        decoded = _json_loads(encoded)
        assert decoded == payload

    def test_loads_accepts_bytes(self):
        from gateway.gateway import _json_dumps, _json_loads

        payload = {"key": "value"}
        encoded = _json_dumps(payload)
        # _json_loads should also accept bytes (orjson supports this)
        decoded = _json_loads(encoded.encode("utf-8"))
        assert decoded == payload

    def test_fallback_to_stdlib_json(self):
        """When orjson is unavailable, _json_dumps/_json_loads use stdlib json."""
        # We reload the gateway module with orjson temporarily hidden.
        # Save original module state.
        original_orjson = sys.modules.get("orjson")

        # Remove orjson from importable modules
        if "orjson" in sys.modules:
            del sys.modules["orjson"]

        # Also remove gateway.gateway so it gets re-imported
        mods_to_clear = [k for k in list(sys.modules) if k.startswith("gateway.gateway")]
        for m in mods_to_clear:
            del sys.modules[m]

        # Block orjson from being imported
        import builtins

        real_import = builtins.__import__

        def no_orjson_import(name, *args, **kwargs):
            if name == "orjson":
                raise ImportError("orjson is not available for this test")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", no_orjson_import):
            # Force re-import
            if "gateway.gateway" in sys.modules:
                del sys.modules["gateway.gateway"]
            import gateway.gateway as gw_fallback

        # Verify fallback functions work
        dumps = gw_fallback._json_dumps
        loads = gw_fallback._json_loads
        payload = {"test": "fallback", "num": 123}
        assert loads(dumps(payload)) == payload

        # Restore orjson for other tests
        if original_orjson is not None:
            sys.modules["orjson"] = original_orjson

        # Clear the fallback module so subsequent tests get the real one
        if "gateway.gateway" in sys.modules:
            del sys.modules["gateway.gateway"]


# ---------------------------------------------------------------------------
# test_cors_middleware
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    """Verify CORS middleware is properly configured on the app."""

    def test_cors_middleware_present(self):
        from gateway.gateway import app as gw_app

        # FastAPI stores user-added middleware in app.user_middleware
        # CORSMiddleware is always first in the stack
        middleware_classes = [
            mw.cls.__name__ if hasattr(mw, "cls") else str(mw) for mw in gw_app.user_middleware
        ]
        assert "CORSMiddleware" in middleware_classes, (
            f"CORSMiddleware not found in user middleware: {middleware_classes}"
        )

    def test_cors_allows_expected_origins(self, client: TestClient):
        """OPTIONS preflight to /health from an allowed origin returns 200."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # 200 or 204 — FastAPI TestClient handles CORS preflight
        assert response.status_code in (200, 204)

    def test_cors_response_headers(self, client: TestClient):
        """Simple GET request includes CORS headers for allowed origin."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        # The CORSMiddleware should echo the allowed origin
        assert response.headers.get("access-control-allow-origin") in (
            "http://localhost:3000",
            "*",
        )

    def test_cors_allowed_methods_include_get(self, client: TestClient):
        """Preflight response advertises allowed methods."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Either 200 or 204
        assert response.status_code in (200, 204)
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods
