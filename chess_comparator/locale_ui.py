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
 'Piezas / Pieces':'Pieces','Vista 2D / 3D · Board view:':'Board view:',
}
SPANISH = {'Analyze':'Analizar','Stop':'Detener','Reset':'Reiniciar','Undo':'Deshacer',
           'Load PGN':'Abrir PGN','Save analysis PGN':'Guardar análisis PGN',
           'Save analysis TXT':'Guardar análisis TXT','Seconds / engine:':'Segundos / motor:',
           'Set FEN':'Poner FEN'}

def choose(language, spanish, english):
    return english if language == 'English' else spanish
