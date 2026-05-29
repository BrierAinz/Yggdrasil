@echo off
chcp 65001 >nul
title Lilith Gateway
cd /d "%~dp0"

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+
    pause
    exit /b 1
)

:: Verificar dependencias
python -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias...
    pip install fastapi uvicorn httpx
)

:: Iniciar gateway
echo [Lilith Gateway] Iniciando en http://localhost:8000
python gateway.py
pause
