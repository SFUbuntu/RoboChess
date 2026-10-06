@echo off
setlocal
cd /d "%~dp0"
if not defined VSCMD_ARG_TGT_ARCH (
  echo Open the x64 Native Tools Command Prompt for Visual Studio, then run this file.
  exit /b 1
)
if /I not "%VSCMD_ARG_TGT_ARCH%"=="x64" (
  echo The active Visual Studio prompt is not targeting x64. Open x64 Native Tools Command Prompt.
  exit /b 1
)
where cl.exe >nul 2>&1
if errorlevel 1 (
  echo cl.exe was not found. Install the Visual Studio C++ Desktop workload.
  exit /b 1
)
cl.exe /nologo /std:c++17 /O2 /EHsc /DNDEBUG /D_CRT_SECURE_NO_WARNINGS /Isrc src\main.cpp src\thc.cpp /Fe:Sargon-Tal-Fischer-x64.exe
if errorlevel 1 exit /b 1
echo Built Sargon-Tal-Fischer-x64.exe
endlocal
