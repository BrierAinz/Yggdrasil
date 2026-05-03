#!/usr/bin/env python3
"""Launcher para Bifrost Gateway."""

import sys
from pathlib import Path


# Agregar directorio de Vanaheim al path ANTES de cualquier import
vanaheim_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(vanaheim_dir))

# Ahora importar y ejecutar
import uvicorn
from bifrost.gateway import app


if __name__ == "__main__":
    print(f"Path: {sys.path[:2]}")
    print(
        f"Agents available: {list(app.state.get('agents', {}).keys()) if hasattr(app.state, 'get') else 'N/A'}"
    )
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
