@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Compilar RoboChess.exe con PyInstaller
echo ============================================
echo.
echo Ejecuta este archivo DENTRO de la carpeta chess_comparator
echo en el mismo PC Windows donde quieres el .exe.
echo.

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
  echo ERROR: falta tkinter. Reinstala Python desde python.org con tcl/tk.
  pause
  exit /b 1
)

echo Instalando PyInstaller...
%PY% -m pip install --upgrade pip pyinstaller
if %errorlevel% neq 0 (
  echo No se pudo instalar PyInstaller.
  pause
  exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

set "DATA=--add-data assets;assets --add-data vendor;vendor"
if exist crafty.exe set "DATA=%DATA% --add-data crafty.exe;."
if exist crafty-linux set "DATA=%DATA% --add-data crafty-linux;."
if exist robbochess set "DATA=%DATA% --add-data robbochess;robbochess"
if exist Crafty-UCI.bat set "DATA=%DATA% --add-data Crafty-UCI.bat;."
if exist avatars set "DATA=%DATA% --add-data avatars;avatars"
if exist sounds set "DATA=%DATA% --add-data sounds;sounds"
if exist personalities set "DATA=%DATA% --add-data personalities;personalities"

echo.
echo Empaquetando (modo carpeta, mas estable con motores y assets)...
echo Esto tarda varios minutos.
echo.

%PY% -m PyInstaller --noconfirm --clean --windowed --onedir --name RoboChess ^
  --paths vendor --hidden-import chess --hidden-import chess.engine --hidden-import chess.pgn ^
  --hidden-import chess.polyglot --hidden-import chess.gaviota --hidden-import chess.svg ^
  --hidden-import profile_store --hidden-import board_settings --hidden-import training_resources ^
  --hidden-import quad_tournament --hidden-import lichess_puzzles --hidden-import locale_ui ^
  --hidden-import personalities --hidden-import crafty_uci --collect-all tkinter %DATA% app.py

if %errorlevel% neq 0 (
  echo.
  echo Fallo PyInstaller.
  pause
  exit /b 1
)

echo.
echo Listo.
echo Carpeta generada:
echo   %cd%\dist\RoboChess\
echo Ejecutable:
echo   %cd%\dist\RoboChess\RoboChess.exe
echo.
echo Copia TODA la carpeta dist\RoboChess a otro PC. No copies solo el .exe.
echo Stockfish no va incluido: en el programa pulsa "Stockfish" y elige stockfish.exe.
echo.
pause
