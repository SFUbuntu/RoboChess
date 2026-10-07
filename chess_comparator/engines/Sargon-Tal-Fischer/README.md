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
- Libro de aperturas binario de Sargon. El archivo incluido se genera desde las 3,258 partidas PGN de Tal y Fischer y cubre los primeros 24 plies. Sargon verifica que la jugada del libro sea legal y, si una posición no aparece, continúa su búsqueda normal.
- Evaluación base y reglas de ajedrez proceden de THC (`thc.h`/`thc.cpp`), una biblioteca publicada por Bill Forster bajo licencia MIT. Se corrigió una copia fuera de límites en la inicialización de su tabla de final. El texto de licencia está en `LICENSE-THC.txt`.

## Compilar en Windows x64

1. Instala Visual Studio con el componente **Desktop development with C++**.
2. Abre **x64 Native Tools Command Prompt for VS**.
3. Ejecuta `build_sargon_tal_x64.bat`.
4. Se crean `Sargon-Tal-Fischer-x64.exe` y `SargonBookBuilder.exe`.
5. Para reconstruir el libro a partir del PGN combinado, ejecuta `build_book_from_pgn.bat`.
6. Mantén `Sargon-Tal-Fischer.bin` junto al motor o indica su ruta en la configuración del motor.

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
- `OwnBook`: activa o desactiva el libro.
- `Book File`: ruta del libro binario de Sargon.
- `Book Depth`: profundidad máxima de uso del libro en plies; valor inicial 24.
- `Book Random`: elige entre jugadas del libro según su frecuencia.
- `Clear Hash`: vacía la tabla.

## Crear el libro desde PGN

El constructor admite una colección PGN como entrada:

```text
SargonBookBuilder.exe partidas.pgn Sargon-Tal-Fischer.bin 24
```

El número final es la profundidad máxima en plies. El formato binario `SARGONB1` pertenece a este prototipo y no es compatible directamente con los libros internos de Crafty ni con Polyglot.

## Aprendizaje

Esta versión usa el libro estático generado desde PGN. El aprendizaje persistente todavía no está activado. La siguiente etapa puede guardar en un archivo separado las novedades y resultados de las partidas para ajustar sus pesos y conservar intacto el libro base.

## Límites actuales

Es un prototipo de búsqueda y estilo, no una versión de fuerza medida ni una imitación literal de Tal o Fischer. El motor original del repositorio Retro Sargon ya tiene una interfaz UCI, pero depende de ensamblador de 32 bits; por eso este programa sustituye esa búsqueda por un motor C++ nativo de 64 bits. La fuerza debe medirse con partidas de prueba antes de asignarle un Elo o presentarlo como rival potente.
