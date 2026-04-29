#!/bin/bash
set -e

echo "[Yggdrasil] Setup iniciado..."

# Instalar paquetes Python
pip install -e Asgard/lilith-core     -e Asgard/lilith-tools     -e Asgard/lilith-memory     -e Asgard/lilith-orchestrator     -e Asgard/lilith-api     -e Asgard/lilith-cli     -e Vanaheim/vanaheim-framework

# Instalar pre-commit
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "[OK] pre-commit hooks instalados"
fi

# Verificar tests
echo "[Yggdrasil] Corriendo tests..."
pytest -q

echo "[Yggdrasil] Setup completo."
