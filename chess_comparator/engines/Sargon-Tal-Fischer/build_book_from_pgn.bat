@echo off
setlocal
cd /d "%~dp0"
if not exist SargonBookBuilder.exe (
  echo Run build_sargon_tal_x64.bat first to build SargonBookBuilder.exe.
  exit /b 1
)
if not exist Sargon_Tal_Fischer.pgn (
  echo Sargon_Tal_Fischer.pgn was not found in this folder.
  exit /b 1
)
SargonBookBuilder.exe Sargon_Tal_Fischer.pgn Sargon-Tal-Fischer.bin 24
if errorlevel 1 exit /b 1
echo The opening book is ready. Keep the .bin beside the engine executable.
endlocal
