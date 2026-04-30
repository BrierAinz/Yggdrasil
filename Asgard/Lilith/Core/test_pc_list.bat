@echo off
echo ============================================
echo TEST PC_LIST - Ejecutando prueba manual...
echo ============================================
cd /d "%~dp0"
python test_pc_list_manual.py
echo.
echo ============================================
echo Presiona cualquier tecla para salir...
pause > nul
