@echo off
setlocal
cd /d "%~dp0"
where cl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: cl.exe was not found.
  echo Run this file from "x64 Native Tools Command Prompt for VS 2022".
  exit /b 1
)
if not exist src\MOVE_GEN.c if not exist src\move_gen.c (
  echo ERROR: the move generation source is missing from src.
  exit /b 1
)
cl.exe /nologo /O2 /MT /W3 /D_CRT_SECURE_NO_WARNINGS /DWIN32 /D_WINDOWS /Isrc ^
  src\exclude.c src\main.c src\move_cancel.c src\move_gen.c src\move_legal.c ^
  src\move_make.c src\move_near.c src\node_cut.c src\node_high.c src\node_pv.c ^
  src\node_superior.c src\node_total.c src\p_value.c src\position.c src\search.c ^
  src\search_fine.c src\search_fine_pv.c src\search_main.c src\see.c src\stack.c ^
  src\static.c src\time.c src\uci.c src\utils.c src\value.c src\values.c src\zobrist.c ^
  /link winmm.lib /OUT:RoboChess-x64.exe
if errorlevel 1 (
  echo.
  echo RoboChess did not compile. Review the compiler errors above.
  exit /b 1
)
echo.
echo Build succeeded: %CD%\RoboChess-x64.exe
endlocal
