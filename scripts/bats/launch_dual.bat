@echo off
chcp 65001 >nul
echo ==========================================
echo   YGGDRASIL - Dual Mode
echo   Asgard (Lilith) + Vanaheim (Panteon)
echo ==========================================
echo.
echo Este script lanza ambos servicios:
echo - Vanaheim: Servicio de agentes (puerto 8001)
echo - Asgard:   Lilith principal (puerto 8000)
echo.

cd /d "%~dp0"

REM Verificar que existen las carpetas
if not exist "Vanaheim\Core\api\server.py" (
    echo ERROR: No se encuentra Vanaheim\Core\api\server.py
    pause
    exit /b 1
)

if not exist "Asgard\Lilith\LILITH.bat" (
    echo ERROR: No se encuentra Asgard\Lilith\LILITH.bat
    pause
    exit /b 1
)

echo [1/3] Iniciando Vanaheim (Panteon de Agentes)...
start "VANAHEIM - Panteon de Agentes" cmd /k "cd Vanaheim && launch_vanaheim.bat"

echo Esperando 5 segundos para que Vanaheim inicie...
timeout /t 5 /nobreak >nul

echo.
echo [2/3] Verificando Vanaheim...
curl -s http://localhost:8001/health >nul 2>&1
if %errorlevel% == 0 (
    echo OK: Vanaheim responde en puerto 8001
) else (
    echo ADVERTENCIA: Vanaheim no responde todavia. Continuando...
)

echo.
echo [3/3] Iniciando Asgard (Lilith)...
echo.

REM Lanzar Lilith (esto inicia API + Discord + Telegram segun su config)
cd Asgard\Lilith
call LILITH.bat
