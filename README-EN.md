# RoboChess / Nibbler

English instructions. Instrucciones en español: [README-ES.md](README-ES.md).

Windows chess study and training program. Board, UCI engines, opening book, puzzles, player profiles, a local tournament against the computer, and game sounds.

This repository is the full program: code, piece sets, Lucas Chess puzzles, the Polyglot book, Gaviota tablebases, and Crafty. The Windows installer bundles Python and the required libraries. Python is needed only when running or building from source. Stockfish is optional and downloaded separately.

## Install on Windows

Open [Releases](https://github.com/SFUbuntu/RoboChess/releases) and download `RoboChess-Instalador-Windows-x64.exe` when a Windows release is published. Run the installer on Windows 10 or 11 (64-bit). No separate Python installation is required. Installation is per user and includes an uninstaller, a Start menu shortcut, and an optional desktop shortcut.

The installer is unsigned. Player profiles remain in the user folder after uninstalling.

## Requirements for running from source

- Windows 10 or 11
- Python 3.10 or newer from [python.org](https://www.python.org/downloads/)
- In the installer, check **Add python.exe to PATH** and **tcl/tk and IDLE**
- Do not use the Microsoft Store Python. It often ships without tkinter, and the window will not open.

Optional, only for Lichess puzzles in `.csv.zst`:

```bat
py -3 -m pip install zstandard
```

## Run it

1. Open the `chess_comparator` folder.
2. Double-click `INICIAR.bat`.
3. If an engine is missing, the program reports it and leaves the window open.

The first time, pick each engine executable with the toolbar buttons (Stockfish, Crafty, RoboChess). Crafty is already included as `crafty.exe`. The application prefers the included `robbochess\RoboChess-x64.exe`; the original 32-bit engine remains available. The experimental Sargon engine is included as `engines\Sargon-Tal-Fischer\Sargon-Tal-Fischer-x64.exe` and can be selected with **Engines → Add UCI Engine**. Stockfish is not bundled: download it from [stockfishchess.org](https://stockfishchess.org/download/) and point the button at `stockfish.exe`.

## Build the executable and installer

From the repository root, with Python 3.12 x64 and Inno Setup installed:

```powershell
.\COMPILAR-INSTALADOR.ps1
```

This creates `dist\RoboChess\RoboChess.exe` and `outputs\RoboChess-Instalador-Windows-x64.exe`. Copy the **whole** `dist\RoboChess` folder for portable use; the application executable requires its `_internal` folder.

See [README-WINDOWS.md](README-WINDOWS.md) for dependencies, custom compiler paths, and rebuilding the native engines. [WINDOWS-VALIDATION.md](WINDOWS-VALIDATION.md) documents the checks and their limits.

## How to use it

- **Game**: choose engine, Elo level, color, and time control, then start a new game.
- When you promote a pawn, pick queen, rook, bishop, or knight. Cancel leaves the pawn on its square. The computer chooses its own promotion piece.
- **Tournament**: local quad against three opponents at a chosen Elo, with rounds, time control, performance rating, and game review.
- **Training**: puzzles and drills from `assets\lucas_resources`.
- **Profile**: create or delete a profile, avatar, Elo, and progress.
- **Settings**: piece style, board colors, and 2D/3D view.
- **File**: open a PGN, import a PGN database, and save the game.

Sounds, if the `sounds` folder is next to `app.py`:

| File | When |
| --- | --- |
| `newgame.wav` | New game |
| `move6.wav` | Normal move |
| `capture1.wav` | Capture |
| `castle.wav` | Castling |
| `illegal.wav` | Illegal move |

## Layout

```text
chess_comparator/
  app.py                 main window
  profile_store.py       profiles in JSON
  quad_tournament.py     local tournament and performance
  training_resources.py  pieces, books, and puzzles
  board_settings.py      colors and perspective
  locale_ui.py           interface text
  lichess_puzzles.py     Lichess puzzles
  crafty_uci.py          Crafty UCI bridge
  INICIAR.bat            start with Python
  COMPILAR-EXE.bat       build the .exe
  avatars/               profile avatars
  sounds/                game sound effects
  assets/                pieces, Lucas puzzles, book, Gaviota
  vendor/                bundled python-chess
  robbochess/            RoboChess engine
  crafty.exe             Crafty engine for Windows
```

Profiles are stored in the user folder, not in this repository.

## Engines and books

- Crafty, RoboChess x64, and the experimental Sargon Tal–Fischer engine are included.
- Stockfish is selected separately. The game Elo limit weakens the engine for that game. It does not edit Stockfish's own file.
- The opening book is Polyglot (`.bin`). A ChessBase book (`.ctg`) cannot be opened here. Convert it to `.bin` and choose it under Tutor / Resources.
- PGN databases: File → Import PGN database. A file of a few thousand games is fine. A database of millions can freeze the window because every game is loaded into memory.

## Licenses

This repository combines several projects. Each keeps its own license:

- `NIBBLER-LICENSE.txt` — Nibbler study interface
- `LUCAS-CHESS-LICENSE.txt` — Lucas Chess pieces, puzzles, and resources
- `PYTHON-CHESS-LICENSE.txt` — `vendor/chess` library
- `STOCKFISH-LICENSE.txt` — Stockfish notes (the binary is not included)
- Crafty and RoboChess / RobboLito: see `CRAFTY-README.txt` and `robbochess/`

Do not redistribute an engine under a license that does not allow it. Stockfish is GPLv3. If you bundle it inside the `.exe`, you must also publish the corresponding source.

## Common problems

- The console closes when you open `app.py`: use `INICIAR.bat`. Python must include tkinter.
- The board does not fit: maximize the window. The board resizes to the available space.
- No sound: the `sounds` folder must sit next to `app.py`.
- The clock appears twice: use the `app.py` from this repository. Only the clock on the top bar should be visible.
