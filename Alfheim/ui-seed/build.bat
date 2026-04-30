@echo off
REM Build script para Lilith Dashboard Electron (Windows)
cd /d "%~dp0"
echo [Lilith] Instalando dependencias...
call npm install
echo [Lilith] Compilando Electron...
call npm run build
echo [Lilith] Build completado. Revisa la carpeta dist/
pause
