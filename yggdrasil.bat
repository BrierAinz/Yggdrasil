@echo off
chcp 65001 >nul
title Yggdrasil - The World Tree

REM ════════════════════════════════════════════════════════════════
REM  Yggdrasil Launcher - Windows CMD entry point
REM  Usage: yggdrasil [command]
REM  Commands: launch, status, clean, backup, purge, size, tree, test, health
REM ════════════════════════════════════════════════════════════════

set "YGG_DIR=%~dp0"

REM Check if running in WSL
wsl --list >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM WSL available — run the Python CLI via WSL for full compatibility
    wsl -e python3 /mnt/d/Proyectos/Yggdrasil/yggdrasil_cli.py %*
) else (
    REM No WSL — try native Python
    python "%YGG_DIR%yggdrasil_cli.py" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  [ERROR] Python no encontrado.
        echo  Instala Python 3.10+ y agregalo al PATH.
        echo.
        pause
        exit /b 1
    )
)
