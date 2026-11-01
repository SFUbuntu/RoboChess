# Changelog

## 1.0.0 — Windows installer

- Add a per-user Windows 10/11 x64 installer with Spanish and English setup,
  an uninstaller, a Start menu shortcut, and an optional desktop shortcut.
- Bundle Python, Tk, images, training resources, sounds, and the dependencies
  for PDF reading, DGT connectivity, and compressed Lichess puzzles.
- Include compiled RoboChess x64, Sargon Tal–Fischer x64, and SargonBookBuilder
  alongside the existing Crafty engine and original engine sources.
- Fix Sargon compilation and gambit-book board comparison.
- Fix RoboChess compilation and standard-input handling for modern MSVC/UCRT.
- Add pinned build requirements, Python/PowerShell packaging scripts, CMake
  support for RoboChess, and Windows build/validation documentation.
- Preserve existing profiles across uninstallation. Stockfish remains optional
  and is selected separately.
