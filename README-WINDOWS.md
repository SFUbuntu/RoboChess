# Building RoboChess for Windows

The Windows package includes the Python runtime, Tk, application resources,
Crafty, RoboChess x64, and the experimental Sargon Tal–Fischer engine. Stockfish
is selected separately. Player profiles remain in the user's
`NibblerDualAnalysis` folder when the application is uninstalled.

The repository root contains the build scripts. They work directly with
`chess_comparator/`; no extra `RoboChess-main` directory is needed.

## Requirements

- Windows 10 or 11, 64-bit.
- Python 3.12 x64 with Tcl/Tk.
- Inno Setup 6.7.4 or later, with its Spanish language file installed.
- Internet access for the initial Python dependency installation.
- To rebuild native engines: CMake and Visual Studio with Desktop development
  with C++ and a Windows SDK. The included executables can be used without C++.

## Build the executable and installer

In PowerShell, from the repository root:

```powershell
.\COMPILAR-INSTALADOR.ps1
```

For an Inno Setup compiler installed in another location:

```powershell
.\COMPILAR-INSTALADOR.ps1 -ISCC 'C:\Tools\Inno Setup 6\ISCC.exe'
```

To rebuild both native engines before packaging:

```powershell
.\COMPILAR-INSTALADOR.ps1 -RebuildEngines
```

The script creates `.build-venv`, installs the pinned dependencies from
`requirements-build.txt`, runs PyInstaller, and invokes Inno Setup.

Output:

- `dist\RoboChess\RoboChess.exe`: application executable. For portable use,
  copy **all** of `dist\RoboChess`, including `_internal`.
- `outputs\RoboChess-Instalador-Windows-x64.exe`: complete installer.

The installer installs for the current user, creates a Start menu shortcut,
offers an optional desktop shortcut, and includes an uninstaller. It supports
Spanish and English. It is not digitally signed.

Build folders and generated installers are ignored by Git. Attach the installer
to a GitHub Release; do not commit the large installer to the source tree.

## Build individual components

After installing `requirements-build.txt` into a Python environment:

```powershell
python build_windows.py
python build_windows.py --rebuild-engines
```

`--rebuild-engines` builds Sargon and its book builder using its original CMake
project, and RoboChess using `cmake/robbochess/CMakeLists.txt`. Both use the static
MSVC runtime. Sargon can then be loaded with **Engines → Add UCI Engine** by
selecting `chess_comparator\engines\Sargon-Tal-Fischer\Sargon-Tal-Fischer-x64.exe`.

## Native source changes

- Sargon: call `PlayMove` separately because it returns `void`, and compare board
  contents instead of array addresses when matching gambit-book positions.
- RoboChess: guard the repeated `type_next` typedef; replace the obsolete
  `stdin->_cnt` access with unbuffered standard input and the existing Windows
  pipe query, so commands remain visible to the engine under modern UCRT.

The main application `app.py` is unchanged. Original engine sources, licenses,
and attribution files are retained. Components keep their individual licenses,
including PyMuPDF's AGPL/commercial licensing.

See [WINDOWS-VALIDATION.md](WINDOWS-VALIDATION.md) for verification and limits.
