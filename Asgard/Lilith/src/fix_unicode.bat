@echo off
cd /D "%~dp0.."

REM Remove emoji characters using PowerShell
echo Fixing Unicode characters...
if not exist "Backend\execute_pipeline_b_a_c.py" (
  echo [WARN] No se encontro "Backend\execute_pipeline_b_a_c.py". Nada que arreglar.
  echo        Si el pipeline cambio de nombre/ubicacion, actualiza este .bat.
  pause
  exit /b 0
)
powershell -Command "(Get-Content Backend\\execute_pipeline_b_a_c.py) -replace '✅', '[OK]' -replace '⚠️', '[WARN]' | Set-Content Backend\\execute_pipeline_b_a_c.py -Encoding ASCII"

echo Done! Re-running pipeline...
python Backend\execute_pipeline_b_a_c.py
pause
