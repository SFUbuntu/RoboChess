"""ECO opening lookup for RoboChess.

Data source: https://github.com/ornicar/eco (lichess.org opening names).
Each entry has an ECO code, a name, and the UCI moves that reach it.
"""
import json
import os

import chess


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'assets', 'eco.json')


class EcoBook:
    def __init__(self, path=DATA):
        self.entries = []
        self.by_moves = {}
        if not os.path.exists(path):
            return
        with open(path, encoding='utf-8') as source:
            self.entries = json.load(source)
        for entry in self.entries:
            moves = entry.get('m', '').split()
            if moves:
                self.by_moves[tuple(moves)] = entry

    def identify(self, board):
        """Return the deepest named opening reached by the current move stack."""
        moves = [move.uci() for move in board.move_stack]
        found = None
        for length in range(1, len(moves) + 1):
            entry = self.by_moves.get(tuple(moves[:length]))
            if entry:
                found = entry
        if found:
            return {'code': found['c'], 'name': found['n'], 'moves': found['m']}
        return None

    def search(self, text):
        query = text.strip().lower()
        if not query:
            return self.entries[:200]
        return [
            entry for entry in self.entries
            if query in entry['c'].lower() or query in entry['n'].lower()
        ][:300]

    def load_board(self, entry):
        board = chess.Board()
        for uci in entry.get('m', '').split():
            board.push_uci(uci)
        return board
