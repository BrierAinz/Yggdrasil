@echo off
chcp 65001 >nul
title Yggdrasil - Update

echo.
echo   ╔════════════════════════════════════════════════╗
echo   ║     ⚔  YGGDRASIL UPDATE  ⚔                    ║
echo   ║     Actualizando el Arbol Sagrado              ║
echo   ╚════════════════════════════════════════════════╝
echo.

set "YGG_DIR=%~dp0"
set "YGG_DIR=%YGG_DIR:~0,-1%"

REM ── Step 1: Git stash (si hay cambios locales) ─────────────
echo   [1/5] Guardando cambios locales (git stash)...
cd /d "D:\Proyectos\Yggdrasil"
git stash
if %ERRORLEVEL% NEQ 0 (
    echo         [!] No hay cambios locales que guardar.
)

REM ── Step 2: Git pull ────────────────────────────────────────
echo.
echo   [2/5] Descargando ultimos cambios (git pull)...
git pull
if %ERRORLEVEL% NEQ 0 (
    echo         [X] Error al hacer git pull. Abortando.
    pause
    exit /b 1
)
echo         [OK] Cambios descargados.

REM ── Step 3: Git stash pop ──────────────────────────────────
echo.
echo   [3/5] Restaurando cambios locales (git stash pop)...
git stash pop
if %ERRORLEVEL% NEQ 0 (
    echo         [!] No havia stash que restaurar.
)

REM ── Step 4: Python deps ─────────────────────────────────────
echo.
echo   [4/5] Instalando dependencias Python...
pip install -q rich cyclopts

REM ── Step 5: uv sync (si uv esta disponible) ────────────────
echo.
echo   [5/5] Sincronizando paquetes (uv sync)...
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    uv sync --all-packages
    echo         [OK] Paquetes sincronizados.
) else (
    echo         [!] uv no encontrado. Saltando uv sync.
    echo         Instala uv: https://docs.astral.sh/uv/
)

echo.
echo   ╔════════════════════════════════════════════════╗
echo   ║     ✓  ACTUALIZACION COMPLETADA                ║
echo   ╚════════════════════════════════════════════════╝
echo.
echo   Ejecuta "yggdrasil" para abrir el launcher.
echo.
pause
