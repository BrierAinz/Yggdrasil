@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo   ╔════════════════════════════════════════════════╗
echo   ║     ⚔  YGGDRASIL INSTALL  ⚔                   ║
echo   ║     Instalando el launcher en tu sistema      ║
echo   ╚════════════════════════════════════════════════╝
echo.
echo   Este instalador hara lo siguiente:
echo.
echo   1. Agregar la carpeta de Yggdrasil al PATH del usuario
echo   2. Crear el comando global "yggdrasil" en %LOCALAPPDATA%\Yggdrasil\bin
echo   3. Verificar que Python3 esta disponible (WSL o nativo)
echo   4. Instalar las dependencias Python (rich, cyclopts)
echo.
echo   Despues de instalar, abre un NUEVO CMD y escribe:
echo.
echo     yggdrasil          (menu interactivo)
echo     yggdrasil update    (actualizar)
echo     yggdrasil status    (ver estado)
echo.
pause
echo.

set "YGG_DIR=%~dp0"
set "YGG_DIR=%YGG_DIR:~0,-1%"

REM ── Step 1: Add Yggdrasil to PATH ───────────────────────────────
echo   [1/4] Agregando Yggdrasil al PATH del usuario...
echo         Carpeta: %YGG_DIR%

for /f "tokens=2* skip=2" %%a in ('reg query HKCU\Environment /v Path 2^>nul') do set "USER_PATH=%%b"

REM Remove trailing backslash if present
if "%USER_PATH:~-1%"=="\" set "USER_PATH=%USER_PATH:~0,-1%"

REM Check if already in PATH
echo !USER_PATH! | find /i "%YGG_DIR%" >nul
if errorlevel 1 (
    setx Path "!USER_PATH!;%YGG_DIR%" >nul 2>&1
    echo         [OK] PATH actualizado.
    echo         [!] CIERRA y REABRE CMD para que surta efecto.
) else (
    echo         [OK] Ya estaba en PATH.
)

REM ── Step 2: Create global yggdrasil command ─────────────────────
echo.
echo   [2/4] Creando comando global "yggdrasil"...

set "BIN_DIR=%LOCALAPPDATA%\Yggdrasil\bin"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

REM Create launcher script that delegates to WSL or native Python
(
echo @echo off
echo chcp 65001 ^>nul
echo REM Yggdrasil global launcher v3.0
echo REM Detects WSL and delegates accordingly
echo.
echo REM Try WSL first (preferred for full compatibility^)
echo wsl --list ^>nul 2^>^&1
echo if %%ERRORLEVEL%% EQU 0 (
echo     wsl -e python3 /mnt/d/Proyectos/Yggdrasil/yggdrasil_cli.py %%*
echo ^) else (
echo     python "D:\Proyectos\Yggdrasil\yggdrasil_cli.py" %%*
echo ^)
) > "%BIN_DIR%\yggdrasil.bat"

REM Also add bin dir to PATH if not there
echo !USER_PATH! | find /i "%BIN_DIR%" >nul
if errorlevel 1 (
    setx Path "!USER_PATH!;%YGG_DIR%;%BIN_DIR%" >nul 2>&1
)

echo         [OK] Comando creado en %BIN_DIR%\yggdrasil.bat

REM ── Step 3: Verify Python ──────────────────────────────────────
echo.
echo   [3/4] Verificando Python...

wsl --list >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo         [OK] WSL detectado.
    wsl -e python3 --version 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo         [X] Python3 no encontrado en WSL.
        echo         Instala con: sudo apt install python3 python3-pip
    ) else (
        echo         [OK] Python3 disponible en WSL.
    )
) else (
    python --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo         [X] Python no encontrado. Instala Python 3.10+
    ) else (
        python --version
        echo         [OK] Python disponible.
    )
)

REM ── Step 4: Install deps ───────────────────────────────────────
echo.
echo   [4/4] Instalando dependencias Python (rich, cyclopts)...

wsl --list >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    wsl -e pip3 install -q rich cyclopts
    echo         [OK] Dependencias instaladas en WSL.
) else (
    pip install -q rich cyclopts
    echo         [OK] Dependencias instaladas.
)

echo.
echo   ╔════════════════════════════════════════════════╗
echo   ║     ✓  INSTALACION COMPLETADA                  ║
echo   ╚════════════════════════════════════════════════╝
echo.
echo   IMPORTANTE: Cierra y reabre CMD para que el
echo   comando "yggdrasil" este disponible.
echo.
echo   Comandos disponibles:
echo.
echo     yggdrasil          ─  Menu interactivo (launcher)
echo     yggdrasil launch    ─  Menu interactivo
echo     yggdrasil update    ─  Actualizar (git pull + deps)
echo     yggdrasil status    ─  Estado de los reinos
echo     yggdrasil clean     ─  Limpiar basura
echo     yggdrasil tree      ─  Arbol de proyectos
echo     yggdrasil test       ─  Ejecutar tests
echo     yggdrasil health    ─  Health check
echo     yggdrasil backup    ─  Crear backup
echo     yggdrasil size      ─  Tamano por reino
echo     yggdrasil migrate   ─  Migrar proyecto entre reinos
echo.
pause
