@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title Lilith - Instalador

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║              LILITH - INSTALADOR GLOBAL                  ║
echo  ║                                                          ║
echo  ║           Dark Fantasy CLI Agent Setup                   ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Detectar ruta del proyecto
set "LILITH_HOME=%~dp0"
set "LILITH_HOME=%LILITH_HOME:~0,-1%"

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Instalar Python 3.11+ desde python.org y marcar "Add to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('python --version 2^>^&1') do echo  [OK] %%a

:: Instalar dependencias
echo.
echo  [1/4] Instalando dependencias...
cd /d "%LILITH_HOME%"
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo  [WARN] Algunas dependencias opcionales fallaron (winrt)
    echo        Las notificaciones funcionaran en modo consola.
    pip install httpx --quiet
)
echo  [OK] Dependencias listas

:: Crear carpeta de tools global
set "TOOLS_DIR=%LOCALAPPDATA%\Lilith\bin"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

:: Crear wrapper lilith.bat
echo.
echo  [2/4] Creando comando global 'lilith'...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo set "LILITH_HOME=%LILITH_HOME%"
    echo cd /d "%%LILITH_HOME%%"
    echo python "Lilith\main.py" %%*
) > "%TOOLS_DIR%\lilith.bat"

echo  [OK] Wrapper creado en: %TOOLS_DIR%\lilith.bat

:: Agregar al PATH si no está
echo.
echo  [3/4] Configurando PATH...

for /f "tokens=*" %%a in ('echo %PATH% ^| find /i "%TOOLS_DIR%"') do (
    set "PATH_HAS_IT=1"
)

if not defined PATH_HAS_IT (
    setx PATH "%PATH%;%TOOLS_DIR%" >nul 2>&1
    echo  [OK] PATH actualizado. Reinicia CMD para usar 'lilith'.
) else (
    echo  [OK] PATH ya contiene el directorio.
)

:: Crear carpetas de datos necesarias
echo.
echo  [4/4] Creando carpetas de datos...
if not exist "%LILITH_HOME%\logs" mkdir "%LILITH_HOME%\logs"
if not exist "%LILITH_HOME%\screenshots" mkdir "%LILITH_HOME%\screenshots"
if not exist "%LILITH_HOME%\memory" mkdir "%LILITH_HOME%\memory"
if not exist "%LILITH_HOME%\Data\agents" mkdir "%LILITH_HOME%\Data\agents"
if not exist "%LILITH_HOME%\Data\notifications" mkdir "%LILITH_HOME%\Data\notifications"
echo  [OK] Carpetas listas

:: Guardar ruta en archivo de config
echo %LILITH_HOME% > "%TOOLS_DIR%\.lilith_home"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  INSTALACION COMPLETA                                    ║
echo  ║                                                          ║
echo  ║  Uso:                                                    ║
echo  ║    lilith              - Iniciar CLI                     ║
echo  ║    lilith --help       - Mostrar ayuda                   ║
echo  ║                                                          ║
echo  ║  Requisitos:                                             ║
echo  ║    1. Abrir LM Studio                                    ║
echo  ║    2. Cargar un modelo (ej: gemma-4-e4b)                ║
echo  ║    3. Activar Local Server en puerto 1234               ║
echo  ║                                                          ║
echo  ║  NOTA: Reinicia la terminal CMD para que 'lilith'       ║
echo  ║        funcione desde cualquier directorio.              ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
