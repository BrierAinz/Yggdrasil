@echo off
REM Si se ejecuta por doble click, reabrir en cmd persistente
if /i "%~1" neq "__persist" (
  start "Lilith DEV Launcher" cmd /k ""%~f0" __persist"
  exit /b 0
)

setlocal EnableExtensions EnableDelayedExpansion

REM Raíz del repo = carpeta donde está este .bat (portable, sin disco fijo)
set "LILITH_ROOT=%~dp0"
if "%LILITH_ROOT:~-1%"=="\" set "LILITH_ROOT=%LILITH_ROOT:~0,-1%"
cd /d "%LILITH_ROOT%"

echo.
echo === Lilith DEV ===
echo Raiz: %LILITH_ROOT%
echo.

REM ── Detectar Muninn FUERA de cualquier bloque (evita delayed-expansion bug) ──
set "HAVE_MUNINN="
if exist "%LILITH_ROOT%\Core\Tools\muninndb\muninn.exe" set "HAVE_MUNINN=1"

REM ── Elegir modo de arranque ────────────────────────────────────────────────
where wt >nul 2>nul
if %errorlevel%==0 goto :launch_wt
goto :launch_separate


REM ═══════════════════════════════════════════════════════════════════════════
:launch_wt
REM Windows Terminal: una ventana con pestanas separadas por servicio.
REM ═══════════════════════════════════════════════════════════════════════════
if "%HAVE_MUNINN%"=="" (
  echo Abriendo Windows Terminal sin MuninnDB ^(no encontrado^)...
  echo  - FastAPI / Discord Bot / Telegram Bot
  echo.
  REM Una sola linea: wt rompe el parsing con cmd /K "cd ... && ..." y comillas dobles.
  wt --title "Lilith DEV" new-tab --title "FastAPI" cmd /K call "%LILITH_ROOT%\_lilith_wt_api.bat" 0 ; new-tab --title "Discord" cmd /K call "%LILITH_ROOT%\_lilith_wt_discord.bat" ; new-tab --title "Telegram" cmd /K call "%LILITH_ROOT%\_lilith_wt_telegram.bat"
) else (
  echo Abriendo Windows Terminal con 4 pestanas...
  echo  - MuninnDB / FastAPI / Discord Bot / Telegram Bot
  echo.
  wt --title "Lilith DEV" new-tab --title "MuninnDB" cmd /K call "%LILITH_ROOT%\_lilith_wt_muninn.bat" ; new-tab --title "FastAPI" cmd /K call "%LILITH_ROOT%\_lilith_wt_api.bat" 3 ; new-tab --title "Discord" cmd /K call "%LILITH_ROOT%\_lilith_wt_discord.bat" ; new-tab --title "Telegram" cmd /K call "%LILITH_ROOT%\_lilith_wt_telegram.bat"
)
echo Lilith arrancando en Windows Terminal.
goto :done


REM ═══════════════════════════════════════════════════════════════════════════
:launch_separate
REM Fallback: una ventana cmd por servicio.
REM ═══════════════════════════════════════════════════════════════════════════
echo Windows Terminal no encontrado. Abriendo ventanas separadas...
echo.

if not "%HAVE_MUNINN%"=="" (
  REM Comprobar si Muninn ya responde; si no, arrancarlo
  call :wait_url "http://127.0.0.1:8475/" 2
  if errorlevel 1 start "MuninnDB" cmd /K call "%LILITH_ROOT%\_lilith_wt_muninn.bat"
  call :wait_url "http://127.0.0.1:8475/" 30
) else (
  echo [WARN] muninn.exe no encontrado en Core\Tools\muninndb\. Saltando.
)

start "Lilith FastAPI"    cmd /K call "%LILITH_ROOT%\_lilith_wt_api.bat" 0
call :wait_url "http://127.0.0.1:8000/" 30

start "Lilith Discord"    cmd /K call "%LILITH_ROOT%\_lilith_wt_discord.bat"
start "Lilith Telegram"   cmd /K call "%LILITH_ROOT%\_lilith_wt_telegram.bat"

echo.
echo Listo:
echo  - MuninnDB:  ventana "MuninnDB"       ^(REST :8475 / UI :8476^)
echo  - FastAPI:   ventana "Lilith FastAPI"  ^(http://127.0.0.1:8000^)
echo  - Discord:   ventana "Lilith Discord"
echo  - Telegram:  ventana "Lilith Telegram"

:done
echo.
pause
goto :eof


REM ═══════════════════════════════════════════════════════════════════════════
:wait_url
REM Espera hasta que una URL responda. Devuelve 0 si OK, 1 si timeout.
REM Uso: call :wait_url "http://..." intentos_max
REM ═══════════════════════════════════════════════════════════════════════════
set "URL=%~1"
set "MAX_TRIES=%~2"
if "%MAX_TRIES%"=="" set "MAX_TRIES=30"
set /a _i=0
:_wu_loop
timeout /t 1 /nobreak >nul
where curl >nul 2>nul
if %errorlevel%==0 (
  curl -s --max-time 1 "%URL%" >nul 2>nul
) else (
  powershell -NoProfile -Command "try{iwr -UseBasicParsing -TimeoutSec 1 '%URL%'|Out-Null;exit 0}catch{exit 1}" >nul 2>nul
)
if %errorlevel%==0 goto :_wu_ok
set /a _i+=1
if !_i! GEQ %MAX_TRIES% goto :_wu_timeout
goto :_wu_loop
:_wu_ok
exit /b 0
:_wu_timeout
exit /b 1
