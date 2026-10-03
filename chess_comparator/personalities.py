"""Grandmaster personalities: portrait, Elo and Polyglot opening book."""
import os
import random
import chess
import chess.polyglot

ROOT = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(ROOT, 'personalities')

PLAYERS = [
    {'id': 'Steinitz', 'name': 'Wilhelm Steinitz', 'title': 'World champion 1886–1894', 'elo': 2600},
    {'id': 'Lasker', 'name': 'Emanuel Lasker', 'title': 'World champion 1894–1921', 'elo': 2650},
    {'id': 'Capablanca', 'name': 'José Raúl Capablanca', 'title': 'World champion 1921–1927', 'elo': 2720},
    {'id': 'Alekhine', 'name': 'Alexander Alekhine', 'title': 'World champion 1927–1935, 1937–1946', 'elo': 2690},
    {'id': 'Euwe', 'name': 'Max Euwe', 'title': 'World champion 1935–1937', 'elo': 2650},
    {'id': 'Botvinnik', 'name': 'Mikhail Botvinnik', 'title': 'World champion 1948–1957, 1958–1960, 1961–1963', 'elo': 2720},
    {'id': 'Tal', 'name': 'Mikhail Tal', 'title': 'World champion 1960–1961', 'elo': 2700},
    {'id': 'Petrosian', 'name': 'Tigran Petrosian', 'title': 'World champion 1963–1969', 'elo': 2700},
    {'id': 'Spassky', 'name': 'Boris Spassky', 'title': 'World champion 1969–1972', 'elo': 2720},
    {'id': 'Fischer', 'name': 'Bobby Fischer', 'title': 'World champion 1972–1975', 'elo': 2780},
    {'id': 'Karpov', 'name': 'Anatoly Karpov', 'title': 'World champion 1975–1985', 'elo': 2780},
    {'id': 'Kasparov', 'name': 'Garry Kasparov', 'title': 'World champion 1985–2000', 'elo': 2850},
    {'id': 'Anand', 'name': 'Viswanathan Anand', 'title': 'World champion 2007–2013', 'elo': 2800},
    {'id': 'Carlsen', 'name': 'Magnus Carlsen', 'title': 'World champion 2013–2023', 'elo': 2860},
    {'id': 'Ding', 'name': 'Ding Liren', 'title': 'World champion 2023–2024', 'elo': 2790},
    {'id': 'Gukesh', 'name': 'Dommaraju Gukesh', 'title': 'World champion 2024–', 'elo': 2770},
    {'id': 'Anderssen', 'name': 'Adolf Anderssen', 'title': 'Unofficial champion, 1850s–1860s', 'elo': 2550},
    {'id': 'Marshall', 'name': 'Frank Marshall', 'title': 'US champion 1909–1936', 'elo': 2570},
]


def book_path(player):
    path = os.path.join(FOLDER, player['id'] + '.bin')
    return path if os.path.isfile(path) else None


def thumb_path(player):
    path = os.path.join(FOLDER, 'thumbs', player['id'] + '.png')
    return path if os.path.isfile(path) else None


def portrait_path(player):
    path = os.path.join(FOLDER, 'portraits', player['id'] + '.png')
    return path if os.path.isfile(path) else None


def book_move(path, board):
    """Weighted move from this master's book, or None when the position is unknown."""
    if not path or not os.path.isfile(path) or board.ply() >= 24:
        return None
    try:
        with chess.polyglot.open_reader(path) as reader:
            entries = [entry for entry in reader.find_all(board) if entry.move in board.legal_moves and entry.weight > 0]
    except (OSError, ValueError, IndexError):
        return None
    if not entries:
        return None
    total = sum(entry.weight for entry in entries)
    pick = random.randrange(total)
    running = 0
    for entry in entries:
        running += entry.weight
        if pick < running:
            return entry.move
    return entries[-1].move
