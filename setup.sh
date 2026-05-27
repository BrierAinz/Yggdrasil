#!/bin/bash
set -e

echo "[Yggdrasil] Setup iniciado..."

# Instalar paquetes Python (Asgard)
pip install -e Asgard/lilith-core \
    -e Asgard/lilith-tools \
    -e Asgard/lilith-memory \
    -e Asgard/lilith-orchestrator \
    -e Asgard/lilith-api \
    -e Asgard/lilith-cli

# Instalar paquetes Python (Vanaheim)
pip install -e Vanaheim/vanaheim-framework

# Instalar pre-commit
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "[OK] pre-commit hooks instalados"
fi

# Verificar tests
echo "[Yggdrasil] Corriendo tests..."
pytest -q

echo "[Yggdrasil] Setup completo."
