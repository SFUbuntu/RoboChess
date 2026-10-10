"""Puzzle Rush helpers for installed Lucas Chess FNS collections."""
from pathlib import Path
import json
import random
import re

DATA_FILE = Path.home() / 'NibblerDualAnalysis' / 'puzzle_rush.json'

# Stable keys are stored in settings; labels follow the selected UI language.
CATEGORIES = {
    'all': ('Todos los puzzles instalados', 'All installed puzzles'),
    'mate1': ('Mate en 1', 'Mate in 1'),
    'mate2': ('Mate en 2', 'Mate in 2'),
    'mate3': ('Mate en 3', 'Mate in 3'),
    'mate4': ('Mate en 4', 'Mate in 4'),
    'mate5': ('Mate en 5', 'Mate in 5'),
    'mate6': ('Mate en 6', 'Mate in 6'),
    'mate7': ('Mate en 7', 'Mate in 7'),
    'mate8': ('Mate en 8', 'Mate in 8'),
    'mate9': ('Mate en 9 o más', 'Mate in 9 or more'),
    'mate_mixed': ('Mates de longitud variable', 'Mates of mixed lengths'),
    'tactics': ('Tácticas', 'Tactics'),
    'fork': ('Ataque doble / horquilla', 'Fork / double attack'),
    'pin': ('Clavada', 'Pin'),
    'discovered': ('Ataque descubierto', 'Discovered attack'),
    'deflection': ('Desviación', 'Deflection'),
    'decoy': ('Atracción / señuelo', 'Decoy'),
    'defense': ('Eliminación de la defensa', 'Removal of the defender'),
    'promotion': ('Promoción de peón', 'Pawn promotion'),
    'endgame': ('Finales', 'Endgames'),
    'middlegame': ('Medio juego', 'Middlegames'),
}

_KEYWORDS = {
    'fork': ('fork', 'double attack', 'double_attack', 'doble ataque', 'horquilla'),
    'pin': ('pin', 'clavada'),
    'discovered': ('discovered', 'x-ray', 'xray', 'rayos x', 'ataque descubierto'),
    'deflection': ('deflection', 'desviacion', 'desviación'),
    'decoy': ('decoy', 'attraction', 'atrap', 'señuelo'),
    'defense': ('removal of defence', 'removal of defense', 'annihilation of defense',
                'elimination of the defender', 'eliminacion de la defensa'),
    'promotion': ('promotion', 'promocion', 'promoción'),
}


def _text(path):
    return str(path).replace('\\', '/').lower()


def classify(path):
    text = _text(path)
    if re.search(r'\bm\s*\d+\s*[-–]\s*\d+\b', text):
        return 'mate_mixed'
    mate = re.search(r'mate\s*in\s*(one|two|three|[1-9]\d*)', text)
    if not mate:
        mate = re.search(r'\bm\s*([1-9]\d*)\b', text)
    if mate:
        raw = mate.group(1)
        number = {'one': 1, 'two': 2, 'three': 3}.get(raw, int(raw) if raw.isdigit() else 0)
        return f'mate{number}' if number <= 8 else 'mate9'
    for key, words in _KEYWORDS.items():
        if any(word in text for word in words):
            return key
    if 'tactics' in text or 'tactic' in text:
        return 'tactics'
    if 'ending' in text or 'endgame' in text or 'pawn endings' in text:
        return 'endgame'
    if 'middlegame' in text or 'middle game' in text or 'technique' in text:
        return 'middlegame'
    if 'checkmate' in text or 'checkmates' in text:
        return 'mate_mixed'
    return 'all'


def available_categories(training_sets):
    files = [p for name, paths in training_sets.items() if name != 'All Lucas Chess exercises' for p in paths]
    result = {'all': files}
    for path in files:
        key = classify(path)
        if key != 'all':
            result.setdefault(key, []).append(path)
    # Keep categories in the intended teaching order and omit empty choices.
    order = ('all', 'mate1', 'mate2', 'mate3', 'mate4', 'mate5', 'mate6', 'mate7', 'mate8', 'mate9', 'mate_mixed', 'tactics', 'fork', 'pin', 'discovered',
             'deflection', 'decoy', 'defense', 'promotion', 'endgame', 'middlegame')
    return {key: result[key] for key in order if result.get(key)}


def load_stats():
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return {'rating': max(100, int(data.get('rating', 1200))),
                    'best_score': max(0, int(data.get('best_score', 0))),
                    'runs': max(0, int(data.get('runs', 0)))}
    except (OSError, ValueError, TypeError):
        pass
    return {'rating': 1200, 'best_score': 0, 'runs': 0}


def save_stats(stats):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(DATA_FILE)


def rating_change(first_try, used_hint):
    """Small local Puzzle Rush rating changes; never an official chess rating."""
    if used_hint:
        return 0
    return 10 if first_try else 5
