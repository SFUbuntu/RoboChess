ROBOCHESS — NOTAS DE MEJORAS
Actualizado: 9 de octubre de 2026

CAMBIOS RECIENTES

- Se corrigió un fallo al abrir Lichess Video Library. El error era:
  TypeError: LichessVideo.__init__() got an unexpected keyword argument 'close_callback'
  Ocurría cuando un app.py nuevo se usaba con un lichess_video.py antiguo. La aplicación enviaba close_callback, pero el módulo anterior no lo aceptaba. Los archivos de la aplicación y del módulo de video ya están sincronizados. Instala juntos los archivos de una misma actualización. No mezcles app.py y lichess_video.py de versiones distintas.

- Se añadió el botón Cerrar videos a Lichess Video Library. Detiene y cierra la vista temporal del video y regresa a la pantalla Estudio. Esa vista está limitada a la biblioteca de videos. Desde ella se bloquean el inicio de sesión y las páginas de partidas de Lichess. El tablero de análisis permanece disponible junto al video.

- Se añadió el reinicio automático del tablero DGT. Cuando todas las piezas vuelven a sus casillas iniciales, RoboChess reinicia la partida, detiene el motor y el reloj, y devuelve el turno a las blancas. Ignora las piezas levantadas de forma temporal y las colocaciones incompletas. El reinicio no está disponible en el editor, en los puzzles, en la revisión, en Engine Match ni en el torneo Quad.

- Se tradujo la ventana Partida > Personalidades al inglés y al español. Los controles, los títulos de campeón, los países y las descripciones de estilo están disponibles en ambos idiomas para los 18 grandes maestros. Los nombres, el Elo y las estadísticas de aperturas en notación algebraica no cambian.

FUNCIONES INCLUIDAS EN ESTA VERSIÓN

- Comparación del análisis de motores, con las líneas candidatas de Stockfish y la variante principal de Crafty, barra de evaluación y flechas en el tablero.
- Guardado del análisis en PGN o en texto para revisarlo en otros programas.
- Partidas contra motores configurados, relojes y controles de partida, además de perfiles locales de progreso y consejos del tutor.
- Conexión de un tablero DGT Smart Board por puerto serie para introducir las jugadas en el tablero físico.
- Recursos y ejercicios de ajedrez incluidos en el proyecto: libros de aperturas, estilos de piezas, tablas de finales y posiciones de entrenamiento.

NOTAS DE INSTALACIÓN

- Conserva la estructura de carpetas al extraer una actualización.
- Para corregir el error de Lichess, actualiza juntos los archivos app.py y lichess_video.py de la misma versión.
- El tablero DGT requiere un controlador que funcione y las dependencias opcionales indicadas en requirements-dgt.txt. La biblioteca de videos integrada puede requerir WebView2 Runtime en Windows.
- La fuerza y el análisis dependen del motor seleccionado, de su configuración y del tiempo de búsqueda disponible. Los ajustes de Elo son aproximados y no representan una clasificación oficial.
