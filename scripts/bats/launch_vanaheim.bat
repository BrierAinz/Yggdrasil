@echo off
chcp 65001 >nul
echo ==========================================
echo   VANAHEIM - Panteon de Agentes
echo   El Exodo del Panteon v1.0
echo ==========================================
echo.

cd /d "%~dp0"

set PYTHONPATH=%~dp0
set VANAHEIM_PORT=8001
set VANAHEIM_HOST=0.0.0.0

echo Iniciando servidor Vanaheim en puerto %VANAHEIM_PORT%...
echo.

python -m Core.api.server

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo iniciar Vanaheim
    pause
    exit /b 1
)
