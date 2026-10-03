# RoboChess / Nibbler

Instrucciones en español. English: [README.md](README.md).

Programa de estudio y entrenamiento de ajedrez para Windows. Tablero, motores UCI, libro de aperturas, puzzles, perfiles, torneo local contra la computadora y sonidos de partida.

Esta carpeta es el programa completo: código, piezas, puzzles de Lucas Chess, libro Polyglot, tablas Gaviota y el motor Crafty. No hace falta bajar otra cosa para abrirlo, salvo Python y, si quieres el motor fuerte, Stockfish.

## Qué necesitas

- Windows 10 o 11
- Python 3.10 o más nuevo, desde [python.org](https://www.python.org/downloads/)
- En el instalador marca **Add python.exe to PATH** y **tcl/tk and IDLE**
- No uses el Python de la Microsoft Store: a menudo no trae tkinter y la ventana no abre

Opcional, solo para puzzles Lichess en `.csv.zst`:

```bat
py -3 -m pip install zstandard
```

## Cómo ejecutarlo

1. Entra en la carpeta `chess_comparator`.
2. Doble clic en `INICIAR.bat`.
3. Si falta un motor, el programa avisa y deja la ventana abierta.

La primera vez elige el ejecutable de cada motor con los botones de la barra (Stockfish, Crafty, RoboChess). Crafty ya viene como `crafty.exe`. RoboChess de 32 bits viene en `robbochess\RoboChess.exe`. Stockfish no se incluye: bájalo de [stockfishchess.org](https://stockfishchess.org/download/) y señala `stockfish.exe`.

## Cómo crear el ejecutable

Dentro de `chess_comparator`, doble clic en `COMPILAR-EXE.bat`.

Genera `dist\RoboChess\RoboChess.exe`. Copia **toda** la carpeta `dist\RoboChess` a otro PC. El `.exe` solo no arranca: necesita los assets y los motores que van a su lado.

## Cómo se juega

- **Partida / Game**: motor, nivel Elo, color y ritmo. Luego **Nueva partida**.
- Al coronar un peón tuyo sales a elegir dama, torre, alfil o caballo. Cancelar deja el peón donde estaba. La máquina elige su propia pieza.
- **Torneo / Tournament**: cuad local contra tres rivales de Elo configurable, rondas, ritmo, performance y análisis de las partidas.
- **Entrenamiento / Training**: puzzles y entrenamientos de `assets\lucas_resources`.
- **Perfil / Profile**: crear, borrar, avatar, Elo y progreso.
- **Configuración / Settings**: estilo de piezas, colores del tablero y vista 2D/3D.
- **Archivo / File**: abrir PGN, base PGN y guardar la partida.

Sonidos, si la carpeta `sounds` está junto a `app.py`:

| Archivo | Cuándo |
| --- | --- |
| `newgame.wav` | Nueva partida |
| `move6.wav` | Jugada normal |
| `capture1.wav` | Captura |
| `castle.wav` | Enroque |
| `illegal.wav` | Jugada ilegal |

## Estructura

```text
chess_comparator/
  app.py                 ventana principal
  profile_store.py       perfiles en JSON
  quad_tournament.py     torneo local y performance
  training_resources.py  piezas, libros y puzzles
  board_settings.py      colores y perspectiva
  locale_ui.py           textos
  lichess_puzzles.py     puzzles Lichess
  crafty_uci.py          puente UCI de Crafty
  INICIAR.bat            arrancar con Python
  COMPILAR-EXE.bat       generar el .exe
  avatars/               avatares de perfil
  sounds/                efectos de partida
  assets/                piezas, puzzles Lucas, libro, Gaviota
  vendor/                python-chess incluido
  robbochess/            motor RoboChess
  crafty.exe             motor Crafty para Windows
```

Los perfiles se guardan en la carpeta del usuario, no dentro del repositorio.

## Motores y libros

- Crafty y RoboChess vienen con el proyecto.
- Stockfish se elige aparte. El nivel Elo de la partida limita la fuerza del motor; no cambia el Elo de Stockfish en su archivo.
- El libro de aperturas es Polyglot (`.bin`). Un libro ChessBase (`.ctg`) no se abre aquí. Hay que convertirlo a `.bin` y elegirlo en Tutor / Resources.
- Bases PGN: Archivo → Importar base PGN. Un archivo de miles de partidas va bien. Una base de millones puede congelar la ventana porque se carga entera en memoria.

## Licencias

Este repositorio junta varios proyectos. Cada uno conserva su licencia:

- `NIBBLER-LICENSE.txt` — interfaz de estudio Nibbler
- `LUCAS-CHESS-LICENSE.txt` — piezas, puzzles y recursos Lucas Chess
- `PYTHON-CHESS-LICENSE.txt` — biblioteca `vendor/chess`
- `STOCKFISH-LICENSE.txt` — notas de Stockfish (el binario no va incluido)
- Crafty y RoboChess / RobboLito: ver `CRAFTY-README.txt` y `robbochess/`

No redistribuyas un motor con una licencia que no lo permita. Stockfish GPLv3, si lo compilas dentro del `.exe`, obliga a publicar también el código correspondiente.

## Problemas frecuentes

- La consola se cierra al abrir `app.py`: usa `INICIAR.bat`. Python tiene que incluir tkinter.
- El tablero no cabe: maximiza la ventana. El tablero se ajusta al espacio.
- No hay sonido: la carpeta `sounds` tiene que estar junto a `app.py`.
- El reloj sale duplicado: usa el `app.py` de este repositorio. Solo debe verse el reloj de la barra superior.
