# Windows Crafty build supplied with this package

The bundled `crafty.exe` was built for personal use from your `Crafty-master.zip`, version 25.6. The original search code is unchanged. `CRAFTY-XBOARD-PATCH.diff` removes an early `feature done=1` line so that the XBoard GUI receives Crafty's `ping` and `setboard` features before initialization completes. The standard `protover 2` handler remains responsible for emitting `feature done=1`.

The build used MinGW-w64 x86-64 on Linux, in the `src` directory after applying the patch to `main.c`:

```
x86_64-w64-mingw32-gcc -O2 -D WINDOWS -DCPUS=1 -DNO_INTRIN -DELO -o crafty.exe crafty.c -lm -lws2_32
```

`-DNO_INTRIN` avoids newer CPU instructions. The program starts Crafty as `crafty.exe xboard` and uses its original XBoard protocol. Stockfish uses UCI. The Windows binary's format and imports were checked; the patched negotiation and search were exercised with a Linux build from the same patched source. Actual execution under Windows should be confirmed on your PC.

`-DELO` enables Crafty’s internal `elo` command (800–3599 approximate; 3600+ unrestricted).
