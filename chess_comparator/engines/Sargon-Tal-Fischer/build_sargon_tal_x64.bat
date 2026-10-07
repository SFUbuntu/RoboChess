@echo off
setlocal
cd /d "%~dp0"
echo Compilando Sargon Tal-Fischer x64 con libro de aperturas...
echo Carpeta: %CD%
echo.
where cl.exe >nul 2>&1
if errorlevel 1 (
  echo cl.exe no esta en esta ventana. Buscando Visual Studio...
  set "VCVARS="
  for %%Y in (18 2022 2019) do for %%E in (Community Professional Enterprise BuildTools) do (
    if exist "C:\Program Files\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat"
  )
  if not defined VCVARS (
    echo No encontre las herramientas de C++. Abre x64 Native Tools Command Prompt for VS.
    pause
    exit /b 1
  )
  echo Usando %VCVARS%
  call "%VCVARS%"
)
where cl.exe >nul 2>&1
if errorlevel 1 (
  echo cl.exe sigue sin aparecer.
  pause
  exit /b 1
)
cl.exe /nologo /std:c++17 /O2 /EHsc /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /Isrc src\main.cpp src\thc.cpp /Fe:Sargon-Tal-Fischer-x64.exe
if errorlevel 1 (
  echo La compilacion del motor fallo.
  pause
  exit /b 1
)
cl.exe /nologo /std:c++17 /O2 /EHsc /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /Isrc src\book_builder.cpp src\thc.cpp /Fe:SargonBookBuilder.exe
if errorlevel 1 (
  echo La compilacion del constructor de libro fallo.
  pause
  exit /b 1
)
echo.
echo Listo:
echo %CD%\Sargon-Tal-Fischer-x64.exe
echo %CD%\SargonBookBuilder.exe
echo Deja Sargon-Tal-Fischer.bin en esta misma carpeta.
echo En RoboChess usa Cargar motor UCI y elige el exe.
pause
endlocal
