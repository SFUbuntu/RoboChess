# Windows package validation

The Windows 1.0.0 package was built with Python 3.12 x64, PyInstaller 6.22.3,
MSVC, and Inno Setup 6.7.4.

Checks completed for the installer preparation:

- All 1,844 files in the original repository were accounted for. The four
  intentional native-source changes are described in `README-WINDOWS.md`.
- The packaged executable opened its window and displayed the chessboard and
  piece images.
- Crafty, RoboChess x64, and Sargon responded to their engine protocols and
  produced legal moves.
- RoboChess x64 produced three legal principal variations through MultiPV.
- Sargon's existing `tests/uci_smoke.py` passed: UCI handshake, Hash, depth
  limit, mate in one, tactical capture, and opening book.
- PDF, DGT, image, and Zstandard dependencies imported successfully in the
  build environment.
- A test installer using the same payload completed with exit code 0.
  All 2,950 installed payload files matched the packaged files byte for byte.
- The test uninstaller completed with exit code 0 and removed the application
  executable.
- The delivered source ZIP passed its archive integrity check.

## Scope and limitations

The isolated installation test disabled uninstall-registry registration.
The environment denied Start menu shortcut creation. Registry registration and
shortcuts were therefore not verified there. The distributed installer retains
the normal uninstall registration and shortcut entries. The user subsequently
confirmed that the delivered installer installed RoboChess as a Windows app.

No physical DGT board was tested. These checks do not cover every application
feature, all hardware configurations, or engine playing strength. The installer
has no digital signature. Stockfish is not bundled.
