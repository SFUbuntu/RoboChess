RoboChess para Nibbler Dual Analysis
====================================

Esta versión incluye el ejecutable x86 (32 bits) del RAR proporcionado como
RoboChess.exe, con sus dos cadenas fijas de identificación cambiadas para que
el banner y UCI digan "RoboChess 0.085g3 w32". El ejecutable original sin
modificar se conserva en upstream. El binario activo es PE32 para Intel 80386 y
usa las DLL habituales de Windows KERNEL32 y WINMM. La comprobación fue estática;
no se pudo ejecutar aquí en Windows.

USO
Abre Nibbler con py app.py. En la carpeta incluida, la app busca primero
RoboChess-x64.exe (si se construyó) y después RoboChess.exe. También puedes
elegir el motor con el botón RoboChess… El ejecutable x86 del RAR anuncia su
nombre antiguo; la interfaz lo presenta como RoboChess. Tanto el ejecutable incluido como el x64 compilado anuncian RoboChess en la
consola inicial y mediante UCI.

COMPILAR UNA VERSIÓN x64 OPCIONAL
1. Instala Visual Studio 2022 con la carga de trabajo "Desarrollo para el
   escritorio con C++".
2. Abre "x64 Native Tools Command Prompt for VS 2022".
3. Cambia a la carpeta robbochess y ejecuta:
      build_robbochess_x64.bat
4. Si termina correctamente, se genera RoboChess-x64.exe. Nibbler lo preferirá
   automáticamente al ejecutable x86 incluido.

El fuente recibido en el ZIP fue adaptado para compilar como x64 con MSVC y para
anunciar el nombre RoboChess. Se conserva la corrección de 64 bits en zobrist.c
que aparece en ese fuente. Se añadió el encabezado search.h que faltaba en el
archivo recibido y MultiPV real de hasta cinco variantes: el motor ejecuta una
búsqueda por alternativa, excluye las primeras jugadas ya elegidas y divide el
tiempo disponible entre las líneas. Nibbler pide tres. Este entorno no dispone de MSVC; no se afirma que la versión x64 haya sido
compilada ni probada.

FUERZA Y OPCIONES
El motor histórico de 2009 ofrece Hash, Ponder y búsquedas UCI por profundidad.
La compilación desde esta fuente implementa MultiPV (1–5); el ejecutable x86
original incluido en el RAR solo ofrece una variante. Ninguna versión implementa
UCI_Elo. El selector 1–3800 de la interfaz se convierte en un límite aproximado
de profundidad 5–32; no representa un Elo medido. Las ideas de tutor inspiradas
en Capablanca, Fischer, Karpov y Kasparov son consejos de entrenamiento: no
cambian la evaluación interna del motor.

ORIGEN Y LICENCIA
El código fuente procede de los archivos proporcionados: RobboLito 0.085g3 y el
RAR de Windows w32. Se conserva la licencia GPL-3.0, los avisos y el historial
de la versión original. La imagen del robot fue proporcionada por el usuario.
