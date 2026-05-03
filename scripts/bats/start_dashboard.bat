@echo off
chcp 65001 >nul
title Asgard Command Center
echo.
echo ========================================
echo   🏛️ Asgard Command Center
echo   Dashboard de Yggdrasil
echo ========================================
echo.

:: Verificar Node.js
echo [1/3] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no encontrado. Por favor instala Node.js.
    pause
    exit /b 1
)
echo       Node.js encontrado ✓

:: Ir al directorio del dashboard
cd /d "%~dp0web"

:: Instalar dependencias si no existen
echo.
echo [2/3] Verificando dependencias...
if not exist "node_modules" (
    echo       Instalando dependencias...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Falló la instalación de dependencias
        pause
        exit /b 1
    )
) else (
    echo       Dependencias instaladas ✓
)

:: Iniciar dashboard
echo.
echo [3/3] Iniciando dashboard...
echo       URL: http://localhost:3000
echo.
echo ========================================
echo   Presiona Ctrl+C para detener
echo ========================================
echo.

:: Abrir navegador después de 3 segundos
timeout /t 3 /nobreak >nul
start http://localhost:3000

:: Iniciar servidor
npm run dev

:: Si llega aquí, el servidor se detuvo
echo.
echo Dashboard detenido.
pause
