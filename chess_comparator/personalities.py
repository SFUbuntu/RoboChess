"""Grandmaster personalities: portrait, Elo and Polyglot opening book."""
import os
import random
import chess
import chess.polyglot

ROOT = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(ROOT, 'personalities')

PLAYERS = [
    {'id': 'Steinitz', 'name': 'Wilhelm Steinitz', 'title': 'World champion 1886–1894', 'elo': 2600, 'country': 'Austria', 'flag': 'at', 'style': 'Positional and defensive. He accumulated small advantages.', 'white': 'e4 74%, d4 18%', 'black': 'e4: e5. d4: d5 87%'},
    {'id': 'Lasker', 'name': 'Emanuel Lasker', 'title': 'World champion 1894–1921', 'elo': 2650, 'country': 'Germany', 'flag': 'de', 'style': 'Practical fighter. He played the opponent, not only the position.', 'white': 'e4 79%, d4 18%', 'black': 'e4: e5 81%. d4: d5 82%'},
    {'id': 'Capablanca', 'name': 'José Raúl Capablanca', 'title': 'World champion 1921–1927', 'elo': 2720, 'country': 'Cuba', 'flag': 'cu', 'style': 'Simple, clear positions and precise endgames.', 'white': 'd4 54%, e4 33%', 'black': 'e4: e5 68%. d4: Nf6 66%'},
    {'id': 'Alekhine', 'name': 'Alexander Alekhine', 'title': 'World champion 1927–1935, 1937–1946', 'elo': 2690, 'country': 'Russia', 'flag': 'ru', 'style': 'Sharp attack and deep opening preparation.', 'white': 'd4 48%, e4 46%', 'black': 'e4: e5 63%. d4: Nf6 53%'},
    {'id': 'Euwe', 'name': 'Max Euwe', 'title': 'World champion 1935–1937', 'elo': 2650, 'country': 'Netherlands', 'flag': 'nl', 'style': 'Logical and methodical. He prepared openings carefully.', 'white': 'd4 63%, e4 24%', 'black': 'e4: e5 64%. d4: Nf6 54%'},
    {'id': 'Botvinnik', 'name': 'Mikhail Botvinnik', 'title': 'World champion 1948–1957, 1958–1960, 1961–1963', 'elo': 2720, 'country': 'Soviet Union', 'flag': 'su', 'style': 'Scientific preparation and long-term plans.', 'white': 'd4 45%, c4 33%', 'black': 'e4: e6 31%. d4: Nf6 58%'},
    {'id': 'Tal', 'name': 'Mikhail Tal', 'title': 'World champion 1960–1961', 'elo': 2700, 'country': 'Latvia', 'flag': 'su', 'style': 'Sacrifices, complications and initiative.', 'white': 'e4 61%, Nf3 14%', 'black': 'e4: c5 71%. d4: Nf6 75%'},
    {'id': 'Petrosian', 'name': 'Tigran Petrosian', 'title': 'World champion 1963–1969', 'elo': 2700, 'country': 'Armenia', 'flag': 'am', 'style': 'Prophylaxis and iron defense. He prevented counterplay.', 'white': 'd4 50%, c4 31%', 'black': 'e4: c5 33%, e6 31%. d4: Nf6 68%'},
    {'id': 'Spassky', 'name': 'Boris Spassky', 'title': 'World champion 1969–1972', 'elo': 2720, 'country': 'Soviet Union', 'flag': 'su', 'style': 'Universal. He could attack or play a quiet position.', 'white': 'e4 62%, d4 35%', 'black': 'e4: e5 61%. d4: Nf6 69%'},
    {'id': 'Fischer', 'name': 'Bobby Fischer', 'title': 'World champion 1972–1975', 'elo': 2780, 'country': 'United States', 'flag': 'us', 'style': 'Direct, concrete and relentless. 1.e4 and the Sicilian.', 'white': 'e4 91%', 'black': 'e4: c5 87%. d4: Nf6 93%'},
    {'id': 'Karpov', 'name': 'Anatoly Karpov', 'title': 'World champion 1975–1985', 'elo': 2780, 'country': 'Russia', 'flag': 'ru', 'style': 'Restriction. He squeezed small advantages without risk.', 'white': 'd4 58%, e4 24%', 'black': 'e4: e5 42%, c6 42%. d4: Nf6 92%'},
    {'id': 'Kasparov', 'name': 'Garry Kasparov', 'title': 'World champion 1985–2000', 'elo': 2850, 'country': 'Azerbaijan', 'flag': 'az', 'style': 'Dynamic preparation and pressure from the opening.', 'white': 'd4 44%, e4 39%', 'black': 'e4: c5 87%. d4: Nf6 78%'},
    {'id': 'Anand', 'name': 'Viswanathan Anand', 'title': 'World champion 2007–2013', 'elo': 2800, 'country': 'India', 'flag': 'in', 'style': 'Fast calculator. Solid openings and a sharp finish.', 'white': 'e4 84%, d4 11%', 'black': 'e4: e5 49%, c5 36%. d4: Nf6 66%'},
    {'id': 'Carlsen', 'name': 'Magnus Carlsen', 'title': 'World champion 2013–2023', 'elo': 2860, 'country': 'Norway', 'flag': 'no', 'style': 'Universal. He plays any opening and wins the endgame.', 'white': 'e4 44%, d4 30%, Nf3 9%', 'black': 'e4: c5 36%, e5 35%. d4: Nf6 59%'},
    {'id': 'Ding', 'name': 'Ding Liren', 'title': 'World champion 2023–2024', 'elo': 2790, 'country': 'China', 'flag': 'cn', 'style': 'Solid and precise, with sudden tactical bursts.', 'white': 'd4 57%, c4 19%', 'black': 'e4: e5 61%. d4: Nf6 89%'},
    {'id': 'Gukesh', 'name': 'Dommaraju Gukesh', 'title': 'World champion 2024–', 'elo': 2770, 'country': 'India', 'flag': 'in', 'style': 'Patient and resilient. He holds the position and counterattacks.', 'white': 'd4 42%, e4 28%', 'black': 'e4: c5 46%. d4: Nf6 64%'},
    {'id': 'Anderssen', 'name': 'Adolf Anderssen', 'title': 'Unofficial champion, 1850s–1860s', 'elo': 2550, 'country': 'Germany', 'flag': 'de', 'style': 'Romantic attack. Open games and sacrifices.', 'white': 'e4 96%', 'black': 'e4: e5 88%. d4: d5 or f5'},
    {'id': 'Marshall', 'name': 'Frank Marshall', 'title': 'US champion 1909–1936', 'elo': 2570, 'country': 'United States', 'flag': 'us', 'style': 'Swashbuckling attack and counterattack.', 'white': 'd4 80%, e4 19%', 'black': 'e4: e5 79%. d4: d5 70%'},
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


def flag_path(player):
    path = os.path.join(FOLDER, 'flags', player.get('flag', '') + '.png')
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
