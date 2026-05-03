@echo off
chcp 65001 >nul
title Lilith Ecosystem Launcher

set "BASE=D:\Proyectos\Yggdrasil"
set "GATEWAY=%BASE%\Asgard\lilith-orchestrator\gateway"
set "TELEGRAM=%BASE%\Vanaheim\Bots_Lilith_v5\telegram"

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  LILITH ECOSYSTEM LAUNCHER                                    ║
echo ║  Asgard Core + Vanaheim Telegram Bot                          ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Verificar .env existe
if not exist "%BASE%\Asgard\Hermes-Lilith\.env" (
    echo [ERROR] Falta .env — copia .env.example y configura
    pause
    exit /b 1
)

echo [1/3] Iniciando Gateway (FastAPI)...
start "Lilith Gateway" cmd /k "cd /d %GATEWAY% && python -m uvicorn gateway:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

echo [2/3] Iniciando Bot Telegram...
start "Lilith Telegram Bot" cmd /k "cd /d %TELEGRAM% && python bot.py"

echo [3/3] Listo. Ambos servicios corriendo.
echo.
echo   Gateway:  http://localhost:8000
echo   Health:   http://localhost:8000/api/health
echo.
pause
