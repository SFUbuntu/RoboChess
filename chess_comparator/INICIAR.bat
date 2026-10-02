@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   RoboChess / Nibbler  -  lanzador Windows
echo ============================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo ERROR: No se encontro Python 3.
    echo Instala Python desde https://www.python.org/downloads/
    echo En el instalador marca:
    echo   - "Add python.exe to PATH"
    echo   - "tcl/tk and IDLE"
    echo.
    pause
    exit /b 1
  )
)

%PY% -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
  echo ERROR: Tu Python no incluye tkinter ^(Tcl/Tk^).
  echo Reinstala Python desde python.org y marca "tcl/tk and IDLE".
  echo El Python de la Microsoft Store a veces no trae tkinter.
  echo.
  pause
  exit /b 1
)

echo Iniciando app.py ...
echo Si aparece un error, esta ventana no se cerrara.
echo.
%PY% "%~dp0app.py"
set "RC=%errorlevel%"
echo.
if not "%RC%"=="0" (
  echo El programa termino con codigo %RC%.
  pause
)
exit /b %RC%
