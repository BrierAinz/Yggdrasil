@echo off
echo [Yggdrasil] Setup iniciado...

pip install -e Asgard\lilith-core ^
    -e Asgard\lilith-tools ^
    -e Asgard\lilith-memory ^
    -e Asgard\lilith-orchestrator ^
    -e Asgard\lilith-api ^
    -e Asgard\lilith-cli ^
    -e Vanaheimanaheim-framework

if exist .pre-commit-config.yaml (
    pre-commit install
    echo [OK] pre-commit hooks instalados
)

echo [Yggdrasil] Corriendo tests...
pytest -q

echo [Yggdrasil] Setup completo.
pause
