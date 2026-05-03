@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title Lilith - Instalador Global

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║              LILITH - INSTALADOR GLOBAL                  ║
echo  ║                                                          ║
echo  ║           Dark Fantasy CLI Agent Setup                   ║
echo  ║                                                          ║
echo  ╚═══════════════════════════════════════════════════════════════════════════════╝
echo.

:: Detectar ruta del proyecto
set "LILITH_HOME=%~dp0"
set "LILITH_HOME=%LILITH_HOME:~0,-1%"
set "LILITH_HOME_PS=%LILITH_HOME:\=/%"

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no encontrado.
    echo  Instalar Python 3.10+ desde python.org y marcar "Add to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('python --version 2^>^&1') do echo  [OK] %%a

:: Directorio de instalacion global
set "TOOLS_DIR=%LOCALAPPDATA%\Lilith\bin"
set "LILITH_BAT=%TOOLS_DIR%\lilith.bat"
set "LILITH_PS1=%TOOLS_DIR%\lilith.ps1"

:: Detectar instalacion previa
if exist "%LILITH_BAT%" (
    echo.
    echo  [INFO] Lilith ya esta instalado.
    set /p REINSTALL="  Reinstalar/actualizar? (S/N): "
    if /I not "!REINSTALL!"=="S" (
        echo  Cancelado.
        pause
        exit /b 0
    )
    echo  [OK] Reinstalando...
)

:: Instalar dependencias
echo.
echo  [1/5] Instalando dependencias...
cd /d "%LILITH_HOME%"
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo  [WARN] Algunas dependencias opcionales fallaron (winrt)
    echo        Las notificaciones funcionaran en modo consola.
    pip install httpx --quiet
)
echo  [OK] Dependencias listas

:: Crear carpeta de binarios global
echo.
echo  [2/5] Creando comando global 'lilith'...
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

:: Wrapper lilith.bat (CMD)
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo set "LILITH_HOME=%LILITH_HOME%"
    echo cd /d "%%LILITH_HOME%%"
    echo python "Lilith\main.py" %%*
) > "%LILITH_BAT%"

:: Wrapper lilith.ps1 (PowerShell)
(
    echo #!/usr/bin/env pwsh
    echo $env:LILITH_HOME = '%LILITH_HOME%'
    echo Set-Location -Path $env:LILITH_HOME
    echo ^& python "Lilith\main.py" @args
) > "%LILITH_PS1%"

echo  [OK] Wrapper creado: %LILITH_BAT%
echo  [OK] Wrapper PS1 creado: %LILITH_PS1%

:: Agregar al PATH via PowerShell (evita truncamiento de setx)
echo.
echo  [3/5] Configurando PATH...

powershell -NoProfile -ExecutionPolicy Bypass -Command "
    $toolsDir = '%TOOLS_DIR%';
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User');
    if ($userPath -notlike "*$toolsDir*") {
        $newPath = $userPath + ';' + $toolsDir;
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User');
        Write-Host '  [OK] PATH actualizado.';
    } else {
        Write-Host '  [OK] PATH ya contiene el directorio.';
    }
"

:: Crear carpetas de datos necesarias
echo.
echo  [4/5] Creando carpetas de datos...
if not exist "%LILITH_HOME%\logs" mkdir "%LILITH_HOME%\logs"
if not exist "%LILITH_HOME%\screenshots" mkdir "%LILITH_HOME%\screenshots"
if not exist "%LILITH_HOME%\memory" mkdir "%LILITH_HOME%\memory"
if not exist "%LILITH_HOME%\Data\agents" mkdir "%LILITH_HOME%\Data\agents"
if not exist "%LILITH_HOME%\Data\notifications" mkdir "%LILITH_HOME%\Data\notifications"
echo  [OK] Carpetas listas

:: Guardar ruta en archivo de config
echo.
echo  [5/5] Guardando configuracion...
echo %LILITH_HOME% > "%TOOLS_DIR%\.lilith_home"
echo  [OK] Configuracion guardada

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════════════╗
echo  ║  INSTALACION COMPLETA                                   ║
echo  ║                                                          ║
echo  ║  Uso:                                                    ║
echo  ║    lilith              - Iniciar CLI interactivo         ║
echo  ║    lilith --help       - Mostrar ayuda                   ║
echo  ║    lilith --version    - Mostrar version                  ║
echo  ║    lilith --no-banner  - Sin banner de inicio            ║
echo  ║                                                          ║
echo  ║  Requisitos:                                             ║
echo  ║    1. Abrir LM Studio                                    ║
echo  ║    2. Cargar un modelo (ej: gemma-4-e4b)                 ║
echo  ║    3. Activar Local Server en puerto 1234                ║
echo  ║                                                          ║
echo  ║  NOTA: Reinicia la terminal CMD/PowerShell para que     ║
echo  ║        'lilith' funcione desde cualquier directorio.     ║
echo  ╚═══════════════════════════════════════════════════════════════════════════════╝
echo.
pause
