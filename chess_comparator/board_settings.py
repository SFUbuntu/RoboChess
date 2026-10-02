"""Persistent local settings for the chessboard appearance."""
import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path.home() / 'NibblerDualAnalysis'
DATA_FILE = DATA_DIR / 'board_colors.json'
DEFAULTS = {'light': '#eeeed2', 'dark': '#769656'}


def _valid_color(value):
    return isinstance(value, str) and len(value) == 7 and value[0] == '#' and all(c in '0123456789abcdefABCDEF' for c in value[1:])


def load():
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        if isinstance(data, dict) and _valid_color(data.get('light')) and _valid_color(data.get('dark')):
            return {'light': data['light'], 'dark': data['dark']}
    except (OSError, ValueError, TypeError):
        pass
    return DEFAULTS.copy()


def save(light, dark):
    if not (_valid_color(light) and _valid_color(dark)):
        raise ValueError('Board colors must be six-digit hexadecimal values.')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix='board-colors-', suffix='.json', dir=DATA_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump({'light': light, 'dark': dark}, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(path, DATA_FILE)
    finally:
        if os.path.exists(path):
            os.unlink(path)
