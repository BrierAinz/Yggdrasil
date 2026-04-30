@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================================
:: LILITH LAUNCHER - Sistema de Automatizacion Inteligente v5.0
:: DEBUG VERSION
:: ============================================================================

title Lilith Launcher v5.0

:: Configuracion de rutas base
set "BASE_DIR=D:\Proyectos\Yggdrasil\Asgard\Lilith"
set "CORE_DIR=%BASE_DIR%\Core\Backend"
set "API_DIR=%BASE_DIR%\Core\Backend\api"
set "DISCORD_DIR=%BASE_DIR%\Discord"
set "TELEGRAM_DIR=%BASE_DIR%\Telegram"
set "FRONTEND_DIR=%BASE_DIR%\Frontend\lilith-dashboard"

:: Archivos de log
set "LOGS_DIR=%BASE_DIR%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

:: ============================================================================
:: FUNCIONES DE UTILIDAD
:: ============================================================================

goto :main

:print_header
cls
echo.
echo    ================================================================
echo.
echo       LILITH SYSTEM LAUNCHER v5.0
echo.
echo       Sistema de Automatizacion Inteligente con IA
echo.
echo       Ubicacion: D:\Proyectos\Yggdrasil\Asgard\Lilith
echo.
echo    ================================================================
echo.
goto :eof

:check_python
    python --version >nul 2>&1
    if errorlevel 1 (
        python3 --version >nul 2>&1
        if errorlevel 1 (
            echo    [X] Python no encontrado
            exit /b 1
        ) else (
            set "PYTHON_CMD=python3"
        )
    ) else (
        set "PYTHON_CMD=python"
    )
    echo    [OK] Python detectado: %PYTHON_CMD%
    goto :eof

:check_node
    node --version >nul 2>&1
    if errorlevel 1 (
        echo    [X] Node.js no encontrado
        exit /b 1
    )
    for /f "tokens=*" %%a in ('node --version') do set "NODE_VERSION=%%a"
    echo    [OK] Node.js detectado: %NODE_VERSION%
    goto :eof

:check_service
    set "svc_name=%~1"
    set "svc_dir=%~2"
    set "svc_file=%~3"

    echo    DEBUG: Verificando %svc_name%
    echo    DEBUG:   Directorio: %svc_dir%
    echo    DEBUG:   Archivo: %svc_file%

    if not exist "%svc_dir%" (
        echo    [X] %svc_name%: DIRECTORIO NO EXISTE
        echo           %svc_dir%
        exit /b 1
    )

    if not exist "%svc_dir%\%svc_file%" (
        echo    [X] %svc_name%: ARCHIVO NO ENCONTRADO
        echo           %svc_dir%\%svc_file%
        exit /b 1
    )

    echo    [OK] %svc_name%: Listo
    goto :eof

:launch_in_window
    set "window_title=%~1"
    set "work_dir=%~2"
    set "command=%~3"

    start "%window_title%" cmd /c "cd /d "%work_dir%" && title %window_title% && echo Iniciando %window_title%... && %command% && echo. && echo Presiona cualquier tecla para cerrar... && pause >nul"
    goto :eof

:: ============================================================================
:: MENU PRINCIPAL
:: ============================================================================

:main
call :print_header

echo    Verificando dependencias...
echo.

call :check_python
if errorlevel 1 goto :error_exit

call :check_node
if errorlevel 1 goto :error_exit

echo.
echo    Verificando componentes...
echo.

call :check_service "Core Backend" "%CORE_DIR%" "main.py"
if errorlevel 1 goto :error_exit

echo.

call :check_service "API Server" "%API_DIR%" "server.py"
if errorlevel 1 goto :error_exit

echo.

call :check_service "Discord Bot" "%DISCORD_DIR%" "bot.py"
if errorlevel 1 goto :error_exit

echo.

call :check_service "Telegram Bot" "%TELEGRAM_DIR%" "bot.py"
if errorlevel 1 goto :error_exit

echo.

call :check_service "Frontend Dashboard" "%FRONTEND_DIR%" "package.json"
if errorlevel 1 goto :error_exit

echo.
echo    [OK] Todos los componentes verificados correctamente.
echo.
pause

:menu
call :print_header

echo    MENU PRINCIPAL
echo.
echo    [1] Iniciar TODO (Core + API + Discord + Telegram + Frontend)
echo    [2] Iniciar solo Backend (Core + API)
echo    [3] Iniciar Bots (Discord + Telegram)
echo    [4] Iniciar solo Frontend Dashboard
echo    [5] Iniciar componentes individuales...
echo.
echo    [6] Ver estado de servicios
echo    [7] Abrir carpeta de logs
echo    [8] Limpiar logs antiguos
echo    [9] Diagnostico (ver errores)
echo.
echo    [0] Salir
echo.
echo    ---------------------------------------------------------------
echo.
set /p choice="    Tu seleccion: "

if "%choice%"=="1" goto :launch_all
if "%choice%"=="2" goto :launch_backend
if "%choice%"=="3" goto :launch_bots
if "%choice%"=="4" goto :launch_frontend
if "%choice%"=="5" goto :menu_individual
if "%choice%"=="6" goto :check_status
if "%choice%"=="7" goto :open_logs
if "%choice%"=="8" goto :clean_logs
if "%choice%"=="9" goto :diagnostic
if "%choice%"=="0" goto :exit

cls
echo    Opcion invalida. Intenta de nuevo.
timeout /t 2 /nobreak >nul
goto :menu

:: ============================================================================
:: OPCION 1: INICIAR TODO
:: ============================================================================

:launch_all
call :print_header

echo    Iniciando todos los servicios...
echo.

:: Iniciar Core Backend
echo    [>>] Iniciando Core Backend...
call :launch_in_window "Lilith - Core Backend" "%CORE_DIR%" "%PYTHON_CMD% main.py"
timeout /t 2 /nobreak >nul

:: Iniciar API Server
echo    [>>] Iniciando API Server...
call :launch_in_window "Lilith - API Server" "%API_DIR%" "%PYTHON_CMD% server.py"
timeout /t 2 /nobreak >nul

:: Iniciar Discord Bot
echo    [>>] Iniciando Discord Bot...
call :launch_in_window "Lilith - Discord Bot" "%DISCORD_DIR%" "%PYTHON_CMD% bot.py"
timeout /t 2 /nobreak >nul

:: Iniciar Telegram Bot
echo    [>>] Iniciando Telegram Bot...
call :launch_in_window "Lilith - Telegram Bot" "%TELEGRAM_DIR%" "%PYTHON_CMD% bot.py"
timeout /t 2 /nobreak >nul

:: Iniciar Frontend
echo    [>>] Iniciando Frontend Dashboard...
call :launch_in_window "Lilith - Frontend Dashboard" "%FRONTEND_DIR%" "npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo    ================================================================
echo      OK - Todos los servicios han sido iniciados
echo    ================================================================
echo.
echo    Accesos:
echo    * Dashboard: http://localhost:5173
echo    * API Docs:  http://localhost:8000/docs (si aplica)
echo.
echo    Los servicios se estan ejecutando en ventanas separadas.
echo    Presiona cualquier tecla para volver al menu.
echo.
pause >nul
goto :menu

:: ============================================================================
:: OPCION 2: INICIAR BACKEND
:: ============================================================================

:launch_backend
call :print_header

echo    Iniciando Backend...
echo.

echo    [>>] Iniciando Core Backend...
call :launch_in_window "Lilith - Core Backend" "%CORE_DIR%" "%PYTHON_CMD% main.py"
timeout /t 2 /nobreak >nul

echo    [>>] Iniciando API Server...
call :launch_in_window "Lilith - API Server" "%API_DIR%" "%PYTHON_CMD% server.py"
timeout /t 2 /nobreak >nul

echo.
echo    OK - Backend iniciado
echo.
pause
goto :menu

:: ============================================================================
:: OPCION 3: INICIAR BOTS
:: ============================================================================

:launch_bots
call :print_header

echo    Iniciando Bots...
echo.

echo    [>>] Iniciando Discord Bot...
call :launch_in_window "Lilith - Discord Bot" "%DISCORD_DIR%" "%PYTHON_CMD% bot.py"
timeout /t 2 /nobreak >nul

echo    [>>] Iniciando Telegram Bot...
call :launch_in_window "Lilith - Telegram Bot" "%TELEGRAM_DIR%" "%PYTHON_CMD% bot.py"
timeout /t 2 /nobreak >nul

echo.
echo    OK - Bots iniciados
echo.
pause
goto :menu

:: ============================================================================
:: OPCION 4: INICIAR FRONTEND
:: ============================================================================

:launch_frontend
call :print_header

echo    Iniciando Frontend Dashboard...
echo.

call :launch_in_window "Lilith - Frontend Dashboard" "%FRONTEND_DIR%" "npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo    OK - Frontend iniciado
echo    Acceso: http://localhost:5173
echo.
pause
goto :menu

:: ============================================================================
:: OPCION 5: MENU INDIVIDUAL
:: ============================================================================

:menu_individual
call :print_header

echo    Iniciar componente individual:
echo.
echo    [1] Core Backend (main.py)
echo    [2] API Server (server.py)
echo    [3] Discord Bot
echo    [4] Telegram Bot
echo    [5] Frontend Dashboard
echo.
echo    [0] Volver al menu principal
echo.
echo    ---------------------------------------------------------------
echo.
set /p ind_choice="    Tu seleccion: "

if "%ind_choice%"=="1" (
    call :launch_in_window "Lilith - Core Backend" "%CORE_DIR%" "%PYTHON_CMD% main.py"
    echo OK - Core Backend iniciado
    timeout /t 2 /nobreak >nul
    goto :menu_individual
)
if "%ind_choice%"=="2" (
    call :launch_in_window "Lilith - API Server" "%API_DIR%" "%PYTHON_CMD% server.py"
    echo OK - API Server iniciado
    timeout /t 2 /nobreak >nul
    goto :menu_individual
)
if "%ind_choice%"=="3" (
    call :launch_in_window "Lilith - Discord Bot" "%DISCORD_DIR%" "%PYTHON_CMD% bot.py"
    echo OK - Discord Bot iniciado
    timeout /t 2 /nobreak >nul
    goto :menu_individual
)
if "%ind_choice%"=="4" (
    call :launch_in_window "Lilith - Telegram Bot" "%TELEGRAM_DIR%" "%PYTHON_CMD% bot.py"
    echo OK - Telegram Bot iniciado
    timeout /t 2 /nobreak >nul
    goto :menu_individual
)
if "%ind_choice%"=="5" (
    call :launch_in_window "Lilith - Frontend Dashboard" "%FRONTEND_DIR%" "npm run dev"
    echo OK - Frontend Dashboard iniciado
    timeout /t 2 /nobreak >nul
    goto :menu_individual
)
if "%ind_choice%"=="0" goto :menu

goto :menu_individual

:: ============================================================================
:: OPCION 6: VER ESTADO
:: ============================================================================

:check_status
call :print_header

echo    Estado de servicios (puertos en uso):
echo.
echo    Buscando procesos de Lilith...
echo.

echo    Procesos Python:
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *Lilith*" 2>nul | findstr /I "python" >nul
if errorlevel 1 (
    echo    [X] No hay procesos de Lilith ejecutandose
) else (
    tasklist /FI "IMAGENAME eq python.exe" /NH 2>nul | findstr /I "python"
)

echo.
echo    Puertos comunes:

:: Puerto 5173 (Vite/Frontend)
netstat -ano | findstr ":5173" >nul
if errorlevel 1 (
    echo    [X] Puerto 5173 (Frontend) - Cerrado
) else (
    echo    [OK] Puerto 5173 (Frontend) - ACTIVO
)

:: Puerto 8000 (FastAPI)
netstat -ano | findstr ":8000" >nul
if errorlevel 1 (
    echo    [X] Puerto 8000 (API) - Cerrado
) else (
    echo    [OK] Puerto 8000 (API) - ACTIVO
)

echo.
echo    Ventanas activas:
tasklist /FI "WINDOWTITLE eq *Lilith*" /NH 2>nul | findstr /I "cmd" >nul
if errorlevel 1 (
    echo    [X] No hay ventanas de Lilith activas
) else (
    tasklist /FI "WINDOWTITLE eq *Lilith*" /NH 2>nul | findstr /I "cmd"
)

echo.
pause
goto :menu

:: ============================================================================
:: OPCION 7: ABRIR LOGS
:: ============================================================================

:open_logs
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
start "" "%LOGS_DIR%"
goto :menu

:: ============================================================================
:: OPCION 8: LIMPIAR LOGS
:: ============================================================================

:clean_logs
call :print_header

echo    Limpiando logs antiguos...
echo.

if exist "%LOGS_DIR%" (
    forfiles /P "%LOGS_DIR%" /S /M "*.log" /D -7 /C "cmd /c del @path" 2>nul
    echo    [OK] Logs antiguos (mayor a 7 dias) eliminados
) else (
    echo    [!] No hay carpeta de logs
)

echo.
pause
goto :menu

:: ============================================================================
:: OPCION 9: DIAGNOSTICO
:: ============================================================================

:diagnostic
call :print_header

echo    DIAGNOSTICO DE COMPONENTES
echo.
echo    Esta opcion te permite ver los errores exactos.
echo.
echo    [1] Probar Core Backend (con logs de error)
echo    [2] Probar API Server (con logs de error)
echo    [3] Verificar archivos existen
necho    [0] Volver al menu
echo.
echo    ---------------------------------------------------------------
echo.
set /p diag_choice="    Tu seleccion: "

if "%diag_choice%"=="1" (
    cls
    echo ============================================
    echo    DIAGNOSTICO: Core Backend
    echo ============================================
    echo.
    echo    Directorio: %CORE_DIR%
    echo    Comando: %PYTHON_CMD% main.py
    echo.
    cd /d "%CORE_DIR%"
    %PYTHON_CMD% main.py
    echo.
    echo ============================================
    echo    El comando termino con codigo: %errorlevel%
    echo ============================================
    pause
    goto :diagnostic
)

if "%diag_choice%"=="2" (
    cls
    echo ============================================
    echo    DIAGNOSTICO: API Server
    echo ============================================
    echo.
    echo    Directorio: %API_DIR%
    echo    Comando: %PYTHON_CMD% server.py
    echo.
    cd /d "%API_DIR%"
    %PYTHON_CMD% server.py
    echo.
    echo ============================================
    echo    El comando termino con codigo: %errorlevel%
    echo ============================================
    pause
    goto :diagnostic
)

if "%diag_choice%"=="3" (
    cls
    echo ============================================
    echo    VERIFICACION DE ARCHIVOS
    echo ============================================
    echo.
    echo    CORE_DIR: %CORE_DIR%
    if exist "%CORE_DIR%\main.py" (
        echo    [OK] main.py existe
    ) else (
        echo    [X] main.py NO existe
        dir "%CORE_DIR%\*.py" 2>nul
    )
    echo.
    echo    API_DIR: %API_DIR%
    if exist "%API_DIR%\server.py" (
        echo    [OK] server.py existe
    ) else (
        echo    [X] server.py NO existe
        dir "%API_DIR%\*.py" 2>nul
    )
    echo.
    echo    DISCORD_DIR: %DISCORD_DIR%
    if exist "%DISCORD_DIR%\bot.py" (
        echo    [OK] bot.py existe
    ) else (
        echo    [X] bot.py NO existe
    )
    echo.
    echo    TELEGRAM_DIR: %TELEGRAM_DIR%
    if exist "%TELEGRAM_DIR%\bot.py" (
        echo    [OK] bot.py existe
    ) else (
        echo    [X] bot.py NO existe
    )
    echo.
    echo ============================================
    pause
    goto :diagnostic
)

if "%diag_choice%"=="0" goto :menu
goto :diagnostic

:: ============================================================================
:: ERROR Y SALIDA
:: ============================================================================

:error_exit
echo.
echo    ================================================================
echo      X Error al verificar dependencias o archivos
echo    ================================================================
echo.
echo    Verifica que:
echo    - Python esta instalado y en el PATH
echo    - Node.js esta instalado y en el PATH
echo    - Los archivos del proyecto existen en las rutas configuradas
echo.
echo    Rutas esperadas:
echo    - Core:    %CORE_DIR%\main.py
echo    - API:     %API_DIR%\server.py
echo    - Discord: %DISCORD_DIR%\bot.py
echo    - Telegram: %TELEGRAM_DIR%\bot.py
echo    - Frontend: %FRONTEND_DIR%\package.json
echo.
pause
exit /b 1

:exit
call :print_header
echo    Gracias por usar Lilith Launcher v5.0
echo.
timeout /t 2 /nobreak >nul
exit /b 0
