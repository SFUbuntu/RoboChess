"""English labels paired with the application's original Spanish interface labels."""
LABELS = {
 'Analyze':'Analyze','Stop':'Stop','Reset':'Reset','Undo':'Undo','Load PGN':'Load PGN',
 'Save analysis PGN':'Save analysis PGN','Save analysis TXT':'Save analysis TXT',
 'Seconds / engine:':'Seconds / engine:',
 'Girar tablero':'Flip board','Jugar contra:':'Play against:','Tu color:':'Your color:',
 'Nivel 1–3800:':'Level 1–3800:','s/jugada:':'s/move:',
 'Nueva partida':'New game','Terminar':'End game','Guardar PGN':'Save PGN',
 'Perfil / progreso':'Profile / progress','Set FEN':'Set FEN',
 'Flechas Stockfish (verde/azul)':'Stockfish arrows (green/blue)',
 'Flecha Crafty (naranja)':'Crafty arrow (orange)',
 'La barra favorece a blancas arriba del 50 %':'Above 50%, the bar favors White',
 'Análisis':'Analysis','Tutor y personajes':'Tutor and characters',
 'Tácticas / comparación':'Tactics / comparison',
 'Tutor de ajedrez\nPistas basadas en el motor':'Chess tutor\nEngine-based hints',
 'Tu rival':'Your opponent','Activar tutor automático':'Enable automatic tutor',
 'Pista':'Hint','Explicar':'Explain',
 'Retirar jugada':'Takeback','Ofrecer tablas':'Offer draw','Rendirse':'Resign',
 'Recursos y ejercicios':'Resources and exercises',
 'Piezas / Pieces':'Pieces','Vista 2D / 3D · Board view:':'Board view: 2D / 3D',
}
SPANISH = {'Analyze':'Analizar','Stop':'Detener','Reset':'Reiniciar','Undo':'Deshacer',
           'Load PGN':'Abrir PGN','Save analysis PGN':'Guardar análisis PGN',
           'Save analysis TXT':'Guardar análisis TXT','Seconds / engine:':'Segundos / motor:',
           'Set FEN':'Poner FEN'}

# Labels used by the compact toolbar and a few controls that were originally
# written in English. Most of the rest of the window uses paired labels.
PAIRED = {
 '⚙ Stockfish':('⚙ Stockfish','⚙ Stockfish'), '⚙ Crafty':('⚙ Crafty','⚙ Crafty'),
 '⚙ RoboChess':('⚙ RoboChess','⚙ RoboChess'), '▦ CPU / UCI':('▦ CPU / UCI','▦ CPU / UCI'),
 '✎ Edit':('✎ Editar','✎ Edit'), '↻ Flip':('↻ Girar','↻ Flip'),
 '▶ Analyze':('▶ Analizar','▶ Analyze'), '■ Stop':('■ Detener','■ Stop'),
 'Reset':('Reiniciar','Reset'), '↶ Undo':('↶ Deshacer','↶ Undo'),
 '📂 PGN':('📂 PGN','📂 PGN'), '💾 PGN analysis':('💾 Análisis PGN','💾 PGN analysis'),
 'Seconds / engine:':('Segundos / motor:','Seconds / engine:'),
 'FEN':('FEN','FEN'), 'Set FEN':('Fijar FEN','Set FEN'),
 'Play as White':('Jugar con blancas','Play as White'),
 'Play as Black':('Jugar con negras','Play as Black'), 'Cancel':('Cancelar','Cancel'),
 'Stockfish':('Stockfish','Stockfish'), 'Crafty':('Crafty','Crafty'),
 'RoboChess':('RoboChess','RoboChess'), 'English':('English','English'),
 'Español':('Español','Spanish'),
 'Tu rival':('Tu rival','Your opponent'),
 'Tutor y personajes':('Tutor y personajes','Tutor and characters'),
 'Recursos y ejercicios':('Recursos y ejercicios','Resources and exercises'),
 'Puzzles de Lichess / Lichess puzzles':('Puzzles de Lichess','Lichess puzzles'),
 'Sin base PGN cargada / No PGN database loaded':('Sin base PGN cargada','No PGN database loaded'),
 'No clock / Sin reloj (5 s/move)':('Sin reloj (5 s/jugada)','No clock (5 s/move)'),
 'Vista 2D / 3D · Board view:':('Vista del tablero: 2D / 3D','Board view: 2D / 3D'),
 'Tutor de ajedrez\nPistas basadas en el motor':('Tutor de ajedrez\nPistas basadas en el motor','Chess tutor\nEngine-based hints'),
}

_SPANISH_MARKERS = (
 'abrir','abrir','cargar','partida','partidas','blancas','negras','resultado','evento',
 'fecha','apertura','ritmo','jugada','frecuencia','porcentaje','usuario','público',
 'doble clic','elegir','descargar','siguiente','pista','explicar','puzzles de',
 'pieza','piezas','tablero','clara','oscura','libro','final','carpeta','colección',
 'ejercicio','mejor','encontrar','vaciar','limpiar','aplicar','cancelar','rendirse',
 'retirar','ofrecer','tablas','terminar','análisis','análisis','tutor','recursos',
 'selecciona','seleccionar','motor','colores','categoría','tema','porcentaje','sin reloj',
 'vista','posición','paleta','selecciona','puls',
)

def translate_label(original, language):
    """Translate fixed widget text without changing internal values/state."""
    if language == 'English':
        if original in LABELS:return LABELS[original]
        if original in PAIRED:return PAIRED[original][1]
    else:
        if original in SPANISH:return SPANISH[original]
        if original in PAIRED:return PAIRED[original][0]
    if ' / ' in original:
        left,right=original.split(' / ',1)
        # Paired UI labels are Spanish-first except for a handful such as
        # "No clock / Sin reloj". Detect those by common Spanish words.
        left_es=any(word in left.lower() for word in _SPANISH_MARKERS) or any(ch in left for ch in 'áéíóúñ¿¡')
        right_es=any(word in right.lower() for word in _SPANISH_MARKERS) or any(ch in right for ch in 'áéíóúñ¿¡')
        if left_es != right_es:
            return (right if right_es else left) if language == 'Español' else (left if right_es else right)
    if language == 'English':return LABELS.get(original,original)
    return SPANISH.get(original,original)

def choose(language, spanish, english):
    return english if language == 'English' else spanish
