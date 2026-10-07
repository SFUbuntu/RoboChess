@echo off
setlocal
cd /d "%~dp0"
echo Compilando Sargon Tal-Fischer x64...
echo Carpeta: %CD%
echo.

where cl.exe >nul 2>&1
if errorlevel 1 (
  echo cl.exe no esta en esta ventana. Buscando Visual Studio...
  set "VCVARS="
  for %%E in (Community Professional Enterprise BuildTools) do (
    if exist "C:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat"
    if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\%%E\VC\Auxiliary\Build\vcvars64.bat"
  )
  if not defined VCVARS (
    echo.
    echo No encontre Visual Studio con las herramientas de C++.
    echo Instala Visual Studio y marca Desktop development with C++.
    echo Luego abre x64 Native Tools Command Prompt for VS y ejecuta este archivo otra vez.
    echo.
    pause
    exit /b 1
  )
  echo Usando %VCVARS%
  call "%VCVARS%"
)

where cl.exe >nul 2>&1
if errorlevel 1 (
  echo cl.exe sigue sin aparecer. Abre x64 Native Tools Command Prompt for VS.
  pause
  exit /b 1
)

cl.exe /nologo /std:c++17 /O2 /EHsc /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /Isrc src\main.cpp src\thc.cpp /Fe:Sargon-Tal-Fischer-x64.exe
if errorlevel 1 (
  echo.
  echo La compilacion fallo. Copia el texto de arriba.
  pause
  exit /b 1
)

echo.
echo Listo: %CD%\Sargon-Tal-Fischer-x64.exe
echo En RoboChess usa Cargar motor UCI y elige ese archivo.
pause
endlocal
