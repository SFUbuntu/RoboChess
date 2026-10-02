"""Local chess training profiles. No network services or account required."""
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path.home() / 'NibblerDualAnalysis'
DATA_FILE = DATA_DIR / 'profiles.json'
PHASES = ('apertura', 'medio juego', 'final')
GENDERS = ('masculino', 'femenino', 'nino', 'nina', 'otro')
AVATARS = (
    'hombre', 'mujer', 'nino', 'nina', 'astronauta',
    'robot', 'duende', 'unicornio', 'abuelo', 'abuela',
)


def load():
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('profiles'), list):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {'version': 1, 'active': None, 'profiles': []}


def save(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix='profiles-', suffix='.json', dir=DATA_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(path, DATA_FILE)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def new_profile(data, name, knows_chess, elo, gender='otro', avatar='robot', photo=''):
    profile = {
        'id': str(uuid.uuid4()), 'name': name.strip(), 'knows_chess': bool(knows_chess),
        'reported_elo': elo, 'gender': gender or 'otro', 'avatar': avatar or 'robot',
        'photo': photo or '', 'created': datetime.now(timezone.utc).isoformat(),
        'moves': 0, 'hints': 0, 'evaluated': 0, 'mates_solved': 0, 'best_moves_solved': 0,
        'tactics_solved': 0, 'puzzles_by_theme': {},
        'quality': {'buena': 0, 'imprecision': 0, 'error': 0, 'grave': 0},
        'phases': {phase: {'evaluated': 0, 'mistakes': 0} for phase in PHASES}, 'recent': [],
    }
    data['profiles'].append(profile)
    data['active'] = profile['id']
    save(data)
    return profile


def update_profile(data, profile, **fields):
    for key, value in fields.items():
        if value is not None:
            profile[key] = value
    save(data)
    return profile


def delete_profile(data, profile_id):
    data['profiles'] = [p for p in data['profiles'] if p.get('id') != profile_id]
    if data.get('active') == profile_id:
        data['active'] = data['profiles'][0]['id'] if data['profiles'] else None
    save(data)
    return data.get('active')


def activate(data, profile_id):
    data['active'] = profile_id
    save(data)


def find(data, profile_id):
    return next((p for p in data.get('profiles', []) if p.get('id') == profile_id), None)


def record_move(data, profile, phase):
    profile['moves'] += 1
    save(data)


def record_exercise(data, profile, kind):
    key = 'best_moves_solved' if kind == 'best' else 'tactics_solved'
    profile[key] = profile.get(key, 0) + 1
    save(data)


def record_lichess_puzzle(data, profile, theme):
    profile['tactics_solved'] = profile.get('tactics_solved', 0) + 1
    progress = profile.setdefault('puzzles_by_theme', {})
    key = theme or 'mixed'
    progress[key] = progress.get(key, 0) + 1
    save(data)


def record_feedback(data, profile, phase, quality, played):
    if phase not in PHASES:
        phase = 'medio juego'
    profile['evaluated'] += 1
    profile['quality'][quality] += 1
    bucket = profile['phases'][phase]
    bucket['evaluated'] += 1
    if quality in ('error', 'grave'):
        bucket['mistakes'] += 1
    profile['recent'] = (profile['recent'] + [{'date': datetime.now(timezone.utc).isoformat(),
                         'move': played, 'phase': phase, 'quality': quality}])[-100:]
    save(data)


def plan(profile):
    n = profile.get('evaluated', 0)
    if n < 5:
        return 'Plan inicial: juega al menos cinco jugadas con un motor configurado. Antes de mover, busca jaques, capturas y amenazas. Después, estudia la alternativa del tutor.'
    phases = profile['phases']
    candidates = [(v['mistakes'] / v['evaluated'], v['mistakes'], phase)
                  for phase, v in phases.items() if v['evaluated'] >= 3]
    focus = max(candidates)[2] if candidates and max(candidates)[1] else None
    if focus == 'apertura':
        return 'Prioridad: apertura. En tus próximas tres partidas, desarrolla piezas, disputa el centro y enrócate. Revisa la primera jugada donde cambió la evaluación.'
    if focus == 'medio juego':
        return 'Prioridad: medio juego. Antes de cada jugada, comprueba jaques, capturas, amenazas y piezas indefensas. Repite las posiciones donde cometiste errores.'
    if focus == 'final':
        return 'Prioridad: finales. Practica actividad del rey, peones pasados y cálculo de carreras de peones. Vuelve a jugar los finales donde perdiste evaluación.'
    tactics = profile.get('tactics_solved', 0)
    if tactics < 10:
        return 'Prioridad: táctica. Abre Entrenamiento y resuelve puzzles de Lucas Chess por categorías (mates, desviación, atracción).'
    return 'Continúa con tres partidas a tu nivel y revisa cada variante del tutor. Aún no hay suficientes errores concentrados en una fase para elegir una prioridad.'
