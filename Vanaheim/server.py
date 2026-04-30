#!/usr/bin/env python3
"""
Bifrost Server - Entry point para Vanaheim Gateway.

Arranca el servidor FastAPI que expone los agentes del Panteón
para ser llamados desde Asgard (Lilith).

Uso:
    python server.py
    python server.py --port 9000
    python server.py --host 0.0.0.0 --port 9000
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Añadir directorio actual al path para imports
_current_dir = Path(__file__).parent.resolve()
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# Setup logging antes de importar FastAPI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("bifrost.server")


def load_config():
    """Carga configuración desde config/bifrost.json."""
    config_path = Path(__file__).parent / "config" / "bifrost.json"
    default_config = {
        "server": {"host": "0.0.0.0", "port": 9000},
        "logging": {"level": "INFO"},
    }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"[Bifrost] Loaded config from {config_path}")
        return config
    except FileNotFoundError:
        logger.warning(f"[Bifrost] Config not found at {config_path}, using defaults")
        return default_config
    except json.JSONDecodeError as e:
        logger.error(f"[Bifrost] Invalid JSON in config: {e}")
        return default_config


def main():
    parser = argparse.ArgumentParser(description="Bifrost Gateway Server")
    parser.add_argument("--host", help="Host to bind (default: from config)")
    parser.add_argument("--port", type=int, help="Port to bind (default: from config)")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload (dev)"
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config()

    host = args.host or config["server"].get("host", "0.0.0.0")
    port = args.port or config["server"].get("port", 9000)

    # Validate auth tokens exist
    auth_config = config.get("auth", {})
    tokens = auth_config.get("tokens", [])
    if not tokens:
        logger.warning(
            "[Bifrost] No auth tokens configured! Requests will be rejected."
        )
        logger.warning("[Bifrost] Add tokens to config/bifrost.json: auth.tokens")

    try:
        import uvicorn
        from bifrost.gateway import app

        logger.info(f"╔════════════════════════════════════════════════╗")
        logger.info(f"║       BIFROST GATEWAY - VANAHEIM               ║")
        logger.info(f"║                                                ║")
        logger.info(f"║   http://{host}:{port:<15}                  ║")
        logger.info(f"║                                                ║")
        logger.info(f"║   Endpoints:                                   ║")
        logger.info(f"║   - GET  /api/bifrost/health                   ║")
        logger.info(f"║   - GET  /api/bifrost/agents                   ║")
        logger.info(f"║   - POST /api/bifrost/execute                  ║")
        logger.info(f"╚════════════════════════════════════════════════╝")

        uvicorn.run(
            "bifrost.gateway:app",
            host=host,
            port=port,
            reload=args.reload,
            log_level=config.get("logging", {}).get("level", "info").lower(),
        )

    except ImportError as e:
        logger.error(f"[Bifrost] Missing dependency: {e}")
        logger.error(
            "[Bifrost] Install with: pip install fastapi uvicorn pydantic httpx"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"[Bifrost] Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
