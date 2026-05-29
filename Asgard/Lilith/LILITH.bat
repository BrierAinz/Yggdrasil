@echo off
chcp 65001 >nul
title LILITH - Ecosistema Yggdrasil
cd /d "%~dp0"

:: ============================================
::  LILITH MASTER LAUNCHER v4.2.2
:: ============================================

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Instala Python 3.11+
    pause
    exit /b 1
)

:: Menu principal
:MENU
cls
echo.
echo ============================================
echo    LILITH - Ecosistema Yggdrasil v4.2.2
echo ============================================
echo.
echo  [1] INICIAR TODO - Backend + Discord + Telegram + Dashboard
echo.
echo  [2] Backend API + Dashboard
echo  [3] Solo Backend API
echo  [4] Solo Dashboard (requiere Backend externo)
echo  [5] Solo Discord Bot
echo  [6] Solo Telegram Bot
echo.
echo  [Q] Salir
echo.
echo ============================================
echo.
set /p "choice=Seleccion (1-6/Q): "

if "%choice%"=="1" goto :START_ALL
if "%choice%"=="2" goto :START_BACKEND_DASHBOARD
if "%choice%"=="3" goto :START_BACKEND_ONLY
if "%choice%"=="4" goto :START_DASHBOARD_ONLY
if "%choice%"=="5" goto :START_DISCORD
if "%choice%"=="6" goto :START_TELEGRAM
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="q" exit /b 0

echo Opcion invalida
timeout /t 1 >nul
goto :MENU

:: ============================================
:: START ALL SERVICES
:: ============================================
:START_ALL
echo.
echo [*] Iniciando Backend API...
start "LILITH-Backend" cmd /k "cd /d "%~dp0" ^&^& python -m Core.Backend.api.server"
timeout /t 3 /nobreak >nul
echo [OK] Backend iniciado en http://localhost:8000

echo.
echo [*] Iniciando Discord Bot...
if exist "Discord\bot.py" (
    start "LILITH-Discord" cmd /k "cd /d "%~dp0\Discord" ^&^& python bot.py"
    echo [OK] Discord iniciado
) else (
    echo [WARN] Discord bot no encontrado - ignorando
)

echo.
echo [*] Iniciando Telegram Bot...
if exist "Telegram\bot.py" (
    start "LILITH-Telegram" cmd /k "cd /d "%~dp0\Telegram" ^&^& python bot.py"
    echo [OK] Telegram iniciado
) else (
    echo [WARN] Telegram bot no encontrado - ignorando
)

goto :START_DASHBOARD

:: ============================================
:: START BACKEND + DASHBOARD
:: ============================================
:START_BACKEND_DASHBOARD
echo.
echo [*] Iniciando Backend API...
start "LILITH-Backend" cmd /k "cd /d "%~dp0" ^&^& python -m Core.Backend.api.server"
timeout /t 3 /nobreak >nul
echo [OK] Backend iniciado en http://localhost:8000

goto :START_DASHBOARD

:: ============================================
:: START BACKEND ONLY
:: ============================================
:START_BACKEND_ONLY
echo.
echo [*] Iniciando Backend API...
start "LILITH-Backend" cmd /k "cd /d "%~dp0" ^&^& python -m Core.Backend.api.server"
echo [OK] Backend iniciado en http://localhost:8000
echo.
echo Presiona una tecla para cerrar esta ventana...
pause >nul
exit /b 0

:: ============================================
:: START DASHBOARD
:: ============================================
:START_DASHBOARD
echo.
echo [*] Iniciando Dashboard Web...
if exist "..\Dashboards\start_dashboard.bat" (
    start "LILITH-Dashboard" cmd /k "cd /d "%~dp0\..\Dashboards" ^&^& call start_dashboard.bat"
    echo [OK] Dashboard iniciado en http://localhost:3000
) else (
    echo [WARN] Dashboard no encontrado
)

goto :SHOW_FINAL_MESSAGE

:: ============================================
:: START DASHBOARD ONLY
:: ============================================
:START_DASHBOARD_ONLY
echo.
echo [*] Iniciando Dashboard Web...
if exist "..\Dashboards\start_dashboard.bat" (
    cd /d "%~dp0\..\Dashboards"
    call start_dashboard.bat
) else (
    echo [ERROR] Dashboard no encontrado en ..\Dashboards
    pause
)
goto :MENU

:: ============================================
:: START DISCORD ONLY
:: ============================================
:START_DISCORD
echo.
echo [*] Iniciando Discord Bot...
if exist "Discord\bot.py" (
    cd /d "%~dp0\Discord"
    python bot.py
) else (
    echo [ERROR] Discord\bot.py no encontrado
    pause
)
goto :MENU

:: ============================================
:: START TELEGRAM ONLY
:: ============================================
:START_TELEGRAM
echo.
echo [*] Iniciando Telegram Bot...
if exist "Telegram\bot.py" (
    cd /d "%~dp0\Telegram"
    python bot.py
) else (
    echo [ERROR] Telegram\bot.py no encontrado
    pause
)
goto :MENU

:: ============================================
:: FINAL MESSAGE
:: ============================================
:SHOW_FINAL_MESSAGE
echo.
echo ============================================
echo    SERVICIOS INICIADOS
:: ============================================
echo.
echo URLs disponibles:
echo   - API Backend: http://localhost:8000
echo   - Dashboard:   http://localhost:3000
echo   - API Docs:    http://localhost:8000/docs
echo.
echo Comandos Discord/Telegram:
echo   /docs      - Consultar documentacion
echo   /automode  - Tareas autonomas
echo.
echo ============================================
echo.
echo Presiona una tecla para volver al menu...
pause >nul
goto :MENU
