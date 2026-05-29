#!/usr/bin/env python3
"""
Lilith Web Server Launcher
Inicia el servidor API con el frontend
"""
import argparse
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.server import start_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lilith Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument(
        "--dev", action="store_true", help="Development mode with auto-reload"
    )

    args = parser.parse_args()

    print(
        f"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                                                          â•‘
â•‘   ðŸ¤– Lilith v2.1 - Operator-class AI Assistant         â•‘
â•‘                                                          â•‘
â•‘   Web Interface: http://{args.host}:{args.port:<5}                 â•‘
â•‘                                                          â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

Presiona Ctrl+C para detener el servidor
    """
    )

    if args.dev:
        import uvicorn
        from src.api.server import app

        uvicorn.run(
            "Backend.api.server:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[str(Path(__file__).parent / "Backend")],
        )
    else:
        start_server(host=args.host, port=args.port)
