"""Persistent interface appearance preferences for RoboChess."""
import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path.home() / 'NibblerDualAnalysis'
DATA_FILE = DATA_DIR / 'ui_preferences.json'
THEMES = {'light', 'dark'}
LANGUAGES = {'English', 'Español'}


def load_theme():
    try:
        value = json.loads(DATA_FILE.read_text(encoding='utf-8')).get('theme')
        if value in THEMES:
            return value
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return 'light'


def load_language():
    try:
        value = json.loads(DATA_FILE.read_text(encoding='utf-8')).get('language')
        if value in LANGUAGES:
            return value
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return 'English'


def _save_setting(name, value):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        settings = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError, TypeError):
        settings = {}
    settings[name] = value
    fd, temporary = tempfile.mkstemp(prefix='ui-preferences-', suffix='.json', dir=DATA_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(settings, output, indent=2, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, DATA_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_theme(theme):
    if theme not in THEMES:
        raise ValueError('Theme must be light or dark.')
    _save_setting('theme', theme)


def save_language(language):
    if language not in LANGUAGES:
        raise ValueError('Language must be English or Español.')
    _save_setting('language', language)
