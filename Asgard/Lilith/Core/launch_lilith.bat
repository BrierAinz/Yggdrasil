@echo off
chcp 65001 >nul
title Lilith v2.1 - Operator AI Server
color 0B

set "LILITH_HOME=%~dp0"
if "%LILITH_HOME:~-1%"=="\" set "LILITH_HOME=%LILITH_HOME:~0,-1%"
set "BACKEND_DIR=%LILITH_HOME%\Backend"
set "SPA_DIR=%LILITH_HOME%\Frontend\spa"

echo.
echo ============================================
echo    LILITH v2.1 - OPERATOR AI SERVER
echo ============================================
echo.

:: Verificar que existe el directorio
echo [1/4] Verificando instalacion...
if not exist "%LILITH_HOME%" (
    echo [ERROR] No se encontro Lilith en: %LILITH_HOME%
    pause
    exit /b 1
)
echo     OK Lilith encontrado
echo.

:: Detectar Python
echo [2/4] Buscando Python...
set "PYTHON_CMD="

:: Buscar en ubicaciones comunes
if exist "C:\Python312\python.exe" (
    set "PYTHON_CMD=C:\Python312\python.exe"
) else if exist "C:\Python311\python.exe" (
    set "PYTHON_CMD=C:\Python311\python.exe"
) else if exist "C:\Python310\python.exe" (
    set "PYTHON_CMD=C:\Python310\python.exe"
) else (
    :: Probar en PATH
    python --version >nul 2>&1
    if %errorlevel% == 0 (
        set "PYTHON_CMD=python"
    ) else (
        py --version >nul 2>&1
        if %errorlevel% == 0 (
            set "PYTHON_CMD=py"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python no encontrado. Por favor instala Python 3.10+
    pause
    exit /b 1
)

echo     OK Python encontrado: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: Verificar dependencias Python
echo [3/4] Verificando dependencias...
cd /d "%BACKEND_DIR%"

:: Verificar FastAPI
%PYTHON_CMD% -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo     WARNING FastAPI no instalado. Instalando dependencias...
    %PYTHON_CMD% -m pip install -r "%LILITH_HOME%\requirements.txt" --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
    echo     OK Dependencias instaladas
) else (
    echo     OK FastAPI OK
)

:: Verificar pywin32 (necesario para IPC)
%PYTHON_CMD% -c "import win32file" >nul 2>&1
if %errorlevel% neq 0 (
    echo     WARNING pywin32 no instalado. Instalando...
    %PYTHON_CMD% -m pip install pywin32 --quiet
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo instalar pywin32
        pause
        exit /b 1
    )
    echo     OK pywin32 instalado
) else (
    echo     OK pywin32 OK
)
echo.

:: Verificar SPA build
echo [4/4] Verificando SPA...
if exist "%SPA_DIR%\dist\index.html" (
    echo     OK SPA build encontrada
    set "SPA_STATUS=OK"
) else (
    echo     WARNING SPA no construida. Se usara version fallback.
    set "SPA_STATUS=MISSING"
)
echo.

:: Informacion de inicio
echo ============================================
echo    INICIANDO SERVIDOR
echo ============================================
echo.
echo API Backend:     http://localhost:8000
echo Documentacion:   http://localhost:8000/docs
echo Interfaz Web:    http://localhost:8000
echo Dashboard API:   http://localhost:8000/api/status
echo.
echo ============================================
echo.

:: Abrir navegador automaticamente (opcional)
set /p OPEN_BROWSER="Abrir navegador automaticamente? (S/N): "
if /i "%OPEN_BROWSER%"=="S" (
    timeout /t 3 /nobreak >nul
    start http://localhost:8000
    echo.
    echo Abriendo navegador...
)

echo.
echo [OK] Servidor iniciado. Presiona Ctrl+C para detener.
echo.

:: Iniciar servidor
cd /d "%BACKEND_DIR%"

echo.
echo [1/3] Limpiando procesos en el puerto 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    if not "%%a"=="0" (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo.
echo [2/3] Iniciando SEBAS Core Process...
start "Lilith - SEBAS Core Engine" %PYTHON_CMD% main.py

echo     Esperando inicializacion del Core (8 segundos)...
echo     (El Core carga 31 herramientas, esto toma tiempo...)
timeout /t 8 /nobreak >nul

echo.
echo [3/3] Iniciando API y WebSocket Server...
start "Lilith - API & WebSocket" %PYTHON_CMD% -m api.server

echo.
echo [OK] Core y API lanzados en ventanas separadas.
echo Cierra las ventanas del Core/API para detenerlos.
pause

:: Si el servidor se cierra
echo.
echo.
echo [STOP] Servidor detenido.
echo.
set /p RESTART="Reiniciar servidor? (S/N): "
if /i "%RESTART%"=="S" (
    goto :start
)

echo.
echo Hasta luego!
timeout /t 2 /nobreak >nul
exit /b 0
