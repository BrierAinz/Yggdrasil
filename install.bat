@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo    YGGDRASIL INSTALLER v2.1
echo ==========================================
echo.

set "YGGDRASIL_DIR=%~dp0"
cd /d "%YGGDRASIL_DIR%"

echo [1/5] Instalando paquetes Python...
pip install -e Asgard\lilith-core -e Asgard\lilith-tools -e Asgard\lilith-memory -e Asgard\lilith-orchestrator -e Asgard\lilith-api -e Asgard\lilith-cli -e Vanaheimanaheim-framework
if errorlevel 1 (
    echo [ERROR] Fallo instalacion de paquetes.
    pause
    exit /b 1
)

echo [2/5] Dependencias adicionales...
pip install httpx fastapi uvicorn python-dotenv beautifulsoup4 lxml

echo [3/5] Configurando pre-commit...
if exist .pre-commit-config.yaml (
    pre-commit install
    echo [OK] pre-commit activo
)

echo [4/5] Creando scripts globales...
set "SCRIPTS_DIR=%LOCALAPPDATA%\Yggdrasil\bin"
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"

echo @echo off > "%SCRIPTS_DIR%\lilith.bat"
echo python -m lilith_cli.main %%* >> "%SCRIPTS_DIR%\lilith.bat"

echo @echo off > "%SCRIPTS_DIR%\yggdrasil.bat"
echo python "%~dp0yggdrasil_cli.py" %%* >> "%SCRIPTS_DIR%\yggdrasil.bat"

echo [5/5] Actualizando PATH...
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v Path 2^>nul') do set "CURRENT_PATH=%%b"
if not defined CURRENT_PATH set "CURRENT_PATH=%PATH%"

echo !CURRENT_PATH! | find /i "%SCRIPTS_DIR%" >nul
if errorlevel 1 (
    setx Path "!CURRENT_PATH!;%SCRIPTS_DIR%"
    echo [OK] PATH actualizado. Reinicia CMD para usar comandos globales.
) else (
    echo [OK] Ya estaba en PATH.
)

echo.
echo ==========================================
echo    INSTALACION COMPLETA
echo ==========================================
echo Comandos disponibles tras reiniciar CMD:
echo   lilith              - CLI de Lilith
echo   yggdrasil status    - Health check
echo   yggdrasil test      - Tests
echo   yggdrasil api       - API server
echo.
pause
