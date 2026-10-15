@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

echo ============================================
echo   RoboChess - modo depuracion
echo ============================================
echo Esta ventana se queda abierta para mostrar errores.
echo.
%PY% "%~dp0app.py"
echo.
echo Codigo de salida: %errorlevel%
pause
