# Sargon Tal–Fischer 64-bit (UCI)

Motor experimental para RoboChess, creado como una reinterpretación moderna e independiente inspirada en Sargon y en el juego dinámico de Mikhail Tal y Bobby Fischer. El protocolo UCI permite cargarlo como motor externo.

## Funciones

- Motor nativo de 64 bits; no usa el ensamblador x86 de 1978.
- UCI: `uci`, `isready`, `position`, `go`, `stop`, `ucinewgame` y `quit`.
- Profundidad máxima configurable: 1–20 plies. El límite no significa que vaya a completar profundidad 20 en cada posición; el reloj o `stop` pueden terminar la búsqueda antes.
- Tabla de transposición configurable de 1 a 32 MB (predeterminado 16 MB).
- Búsqueda iterativa alpha-beta, quiescence para capturas y jaques, ordenamiento de jugadas, tabla hash, extensiones limitadas de jaque, killer/history y reducciones tardías.
- Opción `Aggression` (0–100): ajusta la valoración de presión al rey, cercanía de atacantes, líneas abiertas e iniciativa. El motor favorece desequilibrios y sacrificios cuando su cálculo encuentra compensación; no introduce sacrificios aleatorios.
- Perfil `Style`: `Tal-Fischer` (predeterminado), `Tal` o `Fischer`; la opción cambia cuánto pesa la iniciativa y la presión al rey, sin alterar las reglas ni descartar material al azar.
- Evaluación base y reglas de ajedrez proceden de THC (`thc.h`/`thc.cpp`), una biblioteca publicada por Bill Forster bajo licencia MIT. Se corrigió una copia fuera de límites en la inicialización de su tabla de final. El texto de licencia está en `LICENSE-THC.txt`.

## Compilar en Windows x64

1. Instala Visual Studio con el componente **Desktop development with C++**.
2. Abre **x64 Native Tools Command Prompt for VS**.
3. Ejecuta `build_sargon_tal_x64.bat`.
4. El ejecutable `Sargon-Tal-Fischer-x64.exe` queda en esta carpeta.

También puedes abrir una terminal x64 y compilar con CMake:

```text
cmake -S . -B build -A x64 -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

En Linux x64: `./build_linux_x64.sh`.

## Cargarlo en RoboChess

Compila el ejecutable y selecciónalo desde **Load UCI engine / Cargar motor UCI**. Si tu interfaz ofrece una lista de motores incorporados, agrega la ruta del ejecutable como motor UCI externo. La versión empaquetada aquí no reemplaza `app.py` ni Stockfish, Crafty o RoboChess.

## Ajustes UCI

- `Hash`: 1–32 MB; valor inicial 16.
- `Max Depth`: 1–20; valor inicial 20.
- `Style`: `Tal-Fischer`, `Tal` o `Fischer`.
- `Aggression`: 0–100; valor inicial 72.
- `Move Overhead`: 0–500 ms; valor inicial 40.
- `Clear Hash`: vacía la tabla.

## Límites actuales

Es un prototipo de búsqueda y estilo, no una versión de fuerza medida ni una imitación literal de Tal o Fischer. El motor original del repositorio Retro Sargon ya tiene una interfaz UCI, pero depende de ensamblador de 32 bits; por eso este programa sustituye esa búsqueda por un motor C++ nativo de 64 bits. La fuerza debe medirse con partidas de prueba antes de asignarle un Elo o presentarlo como rival potente.
