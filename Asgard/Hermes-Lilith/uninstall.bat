@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title Lilith - Desinstalador

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║           LILITH - DESINSTALADOR                         ║
echo  ║                                                          ║
echo  ╚═══════════════════════════════════════════════════════════════════════════════╝
echo.

set "TOOLS_DIR=%LOCALAPPDATA%\Lilith\bin"
set "LILITH_HOME_FILE=%TOOLS_DIR%\.lilith_home"

:: Detectar si hay instalacion
if not exist "%TOOLS_DIR%\lilith.bat" (
    echo  [WARN] No se encontro instalacion de Lilith.
    echo  Buscando en PATH...
    
    for /f "tokens=*" %%a in ('where lilith.bat 2^>nul') do (
        set "FOUND=%%a"
    )
    
    if defined FOUND (
        echo  [OK] Encontrado: !FOUND!
        for /f "delims=" %%i in ("!FOUND!") do set "TOOLS_DIR=%%~dpi"
    ) else (
        echo  [ERROR] No se encontro lilith.bat en el sistema.
        pause
        exit /b 1
    )
)

:: Leer ruta original del proyecto si existe
set "LILITH_HOME="
if exist "%LILITH_HOME_FILE%" (
    set /p LILITH_HOME=<"%LILITH_HOME_FILE%"
    echo  [INFO] Proyecto detectado en: %LILITH_HOME%
)

echo.
set /p CONFIRM="  Eliminar comando 'lilith' del sistema? (S/N): "
if /I not "%CONFIRM%"=="S" (
    echo  Cancelado.
    pause
    exit /b 0
)

:: Eliminar del PATH via PowerShell
echo.
echo  [1/2] Eliminando del PATH...
powershell -NoProfile -ExecutionPolicy Bypass -Command "
    $toolsDir = '%TOOLS_DIR%';
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User');
    if ($userPath -like "*$toolsDir*") {
        $newPath = ($userPath -split ';' | Where-Object { $_ -ne $toolsDir }) -join ';';
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User');
        Write-Host '  [OK] Eliminado del PATH.';
    } else {
        Write-Host '  [OK] No estaba en PATH.';
    }
"

:: Eliminar wrappers
echo  [2/2] Eliminando archivos...
if exist "%TOOLS_DIR%\lilith.bat" del "%TOOLS_DIR%\lilith.bat"
if exist "%TOOLS_DIR%\lilith.ps1" del "%TOOLS_DIR%\lilith.ps1"
if exist "%TOOLS_DIR%\.lilith_home" del "%TOOLS_DIR%\.lilith_home"

:: Intentar eliminar directorio vacio
rmdir "%TOOLS_DIR%" 2>nul
rmdir "%LOCALAPPDATA%\Lilith" 2>nul

echo  [OK] Archivos eliminados.

:: Preguntar sobre datos del proyecto
if defined LILITH_HOME (
    echo.
    set /p DELDATA="  Eliminar datos del proyecto (logs, memory, screenshots)? (S/N): "
    if /I "!DELDATA!"=="S" (
        if exist "%LILITH_HOME%\logs" rmdir /S /Q "%LILITH_HOME%\logs" 2>nul
        if exist "%LILITH_HOME%\screenshots" rmdir /S /Q "%LILITH_HOME%\screenshots" 2>nul
        if exist "%LILITH_HOME%\memory" rmdir /S /Q "%LILITH_HOME%\memory" 2>nul
        if exist "%LILITH_HOME%\Data" rmdir /S /Q "%LILITH_HOME%\Data" 2>nul
        echo  [OK] Datos eliminados.
    )
)

echo.
echo  ╔═══════════════════════════════════════════════════════════════════════════════╗
echo  ║  DESINSTALACION COMPLETA                                ║
echo  ║                                                          ║
echo  ║  Reinicia la terminal para que los cambios surtan       ║
echo  ║  efecto.                                                 ║
echo  ╚═══════════════════════════════════════════════════════════════════════════════╝
echo.
pause
