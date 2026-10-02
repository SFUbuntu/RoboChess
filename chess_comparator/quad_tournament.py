"""Training tournament pairings, Elo performance and simple study notes."""
import math
import random

ROUND_ROBIN = (
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
)


def section_ratings(center, count=3, spread=100):
    """Return nearby virtual-player ratings around a section center."""
    center = int(center)
    start = center - spread * ((count - 1) / 2)
    ratings = []
    for i in range(count):
        ratings.append(int(max(800, min(2800, round(start + i * spread)))))
    if center not in ratings and ratings:
        ratings[count // 2] = center
    return tuple(ratings)


def award(players, white, black, result):
    if result == '1-0':
        players[white]['points'] += 1
    elif result == '0-1':
        players[black]['points'] += 1
    elif result == '1/2-1/2':
        players[white]['points'] += .5
        players[black]['points'] += .5


def standings(players, games=()):
    buchholz = [0.0] * len(players)
    for game in games:
        buchholz[game['white']] += players[game['black']]['points']
        buchholz[game['black']] += players[game['white']]['points']
    return sorted(
        enumerate(players),
        key=lambda item: (-item[1]['points'], -buchholz[item[0]], -item[1]['rating'], item[1]['name']),
    )


def elo_result(white_rating, black_rating):
    white_expectation = 1 / (1 + 10 ** ((black_rating - white_rating) / 400))
    outcome = random.random()
    if outcome < .24:
        return '1/2-1/2'
    return '1-0' if outcome < .24 + .76 * white_expectation else '0-1'


def expected_score(player_elo, opponent_ratings):
    return sum(1 / (1 + 10 ** ((opp - player_elo) / 400)) for opp in opponent_ratings)


def performance_rating(opponent_ratings, score_points):
    """Approximate Elo performance from score vs a list of opponents."""
    n = len(opponent_ratings)
    if n == 0:
        return None
    rc = sum(opponent_ratings) / n
    p = score_points / n
    if p <= 0:
        return int(round(rc - 800))
    if p >= 1:
        return int(round(rc + 800))
    return int(round(rc + 400 * math.log10(p / (1 - p))))


def result_points_for_human(result, human_white):
    if result == '1/2-1/2':
        return 0.5
    if result == '1-0':
        return 1.0 if human_white else 0.0
    if result == '0-1':
        return 0.0 if human_white else 1.0
    return 0.0


def training_notes(played, language='Español'):
    """Very small, practical study hints from the finished games."""
    es = language != 'English'
    if not played:
        return 'Aún no hay partidas del torneo.' if es else 'No tournament games yet.'
    wins = sum(1 for g in played if g.get('points', 0) == 1)
    draws = sum(1 for g in played if g.get('points', 0) == 0.5)
    losses = sum(1 for g in played if g.get('points', 0) == 0)
    white_losses = sum(1 for g in played if g.get('points', 0) == 0 and g.get('human_white'))
    black_losses = sum(1 for g in played if g.get('points', 0) == 0 and not g.get('human_white'))
    short_losses = sum(1 for g in played if g.get('points', 0) == 0 and g.get('plies', 99) < 30)
    notes = []
    if es:
        notes.append(f'Resultado: {wins} victorias, {draws} tablas, {losses} derrotas.')
        if white_losses >= 2:
            notes.append('Varias derrotas con blancas: revisa tus aperturas de blanco y el plan de las primeras 12 jugadas.')
        if black_losses >= 2:
            notes.append('Varias derrotas con negras: elige un repertorio sólido y evita improvisar en la apertura.')
        if short_losses:
            notes.append('Hay partidas cortas perdidas: entrena táctica (jaques, capturas, amenazas) antes de cada jugada.')
        if wins and not losses:
            notes.append('Torneo limpio. Sube 50–100 Elo el nivel de los rivales en el próximo entrenamiento.')
        elif losses and not wins:
            notes.append('Baja 100 Elo el nivel o aumenta el tiempo por jugada; primero consolida y luego sube la dificultad.')
        else:
            notes.append('Analiza cada derrota con el motor: busca la primera jugada donde cambió la evaluación.')
        notes.append('Carga cada partida del listado, pulsa Analizar y compara tu jugada con la primera línea del motor.')
    else:
        notes.append(f'Score: {wins} wins, {draws} draws, {losses} losses.')
        if white_losses >= 2:
            notes.append('Several losses as White: review your White openings and the first 12-move plan.')
        if black_losses >= 2:
            notes.append('Several losses as Black: pick a solid repertoire instead of improvising in the opening.')
        if short_losses:
            notes.append('Short losses: train tactics (checks, captures, threats) before every move.')
        if wins and not losses:
            notes.append('Clean event. Raise opponent Elo by 50–100 in the next training event.')
        elif losses and not wins:
            notes.append('Drop opponent Elo by about 100 or add thinking time, then raise the level again.')
        else:
            notes.append('Analyze each loss and find the first move where the evaluation swung.')
        notes.append('Open each game from the list, press Analyze, and compare your move with the engine line.')
    return '\n'.join(notes)
