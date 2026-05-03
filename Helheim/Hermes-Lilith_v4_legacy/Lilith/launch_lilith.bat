@echo off
chcp 65001 >nul
title Lilith - Asistente Personal

echo.
echo  🧚 Iniciando Lilith...
echo.

cd /d "%~dp0"

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instalar Python 3.11+
    pause
    exit /b 1
)

REM Instalar dependencias si es necesario
pip show httpx >nul 2>&1
if errorlevel 1 (
    echo 📦 Instalando dependencias...
    pip install -r requirements.txt
)

REM Crear carpetas necesarias
if not exist "logs" mkdir "logs"
if not exist "screenshots" mkdir "screenshots"
if not exist "memory" mkdir "memory"

REM Ejecutar Lilith
python main.py

pause
