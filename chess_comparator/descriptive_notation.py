"""Convert Spanish descriptive chess moves to legal SAN using a known position."""
from __future__ import annotations

import re

import chess

PIECE_TYPES = {
    'P': chess.PAWN,
    'C': chess.KNIGHT,
    'A': chess.BISHOP,
    'T': chess.ROOK,
    'D': chess.QUEEN,
    'R': chess.KING,
}

# Files named by their starting piece in Spanish descriptive notation.
# Single-letter names that occur twice (Torre, Caballo, Alfil) remain
# ambiguous until legal moves and the current position resolve them.
FILE_OPTIONS = {
    'TD': (0,), 'CD': (1,), 'AD': (2,), 'D': (3,), 'R': (4,),
    'AR': (5,), 'CR': (6,), 'TR': (7,),
    'T': (0, 7), 'C': (1, 6), 'A': (2, 5),
}

IGNORABLE = {
    'MATE', 'MAT', 'TABLAS', 'TABLAS.', 'GANAN', 'GANA', 'GANA.',
    '1-0', '0-1', '1/2-1/2', '*', 'EP', 'E.P.',
}


def tokenize(text: str) -> list[str]:
    """Split a pasted move line, removing move numbers and common comments."""
    text = re.sub(r'\{[^}]*\}|\([^)]*\)', ' ', str(text))
    text = text.replace('\u2026', ' ')
    text = re.sub(r'\b\d+\.(?:\.\.)?', ' ', text)
    text = re.sub(r'\b\d+\s*[-–]\s*\d+\b', ' ', text)
    text = re.sub(r'\s*([xX:])\s*', r'\1', text)
    # OCR often inserts a space between a piece letter and its destination.
    text = re.sub(r'\b([TCDRAP])\s+([1-8])', r'\1\2', text, flags=re.IGNORECASE)
    tokens = []
    for raw in re.split(r'[\s,;]+', text):
        token = raw.strip().strip('.,;')
        token = token.strip('!?')
        if not token or token.upper() in IGNORABLE:
            continue
        # Ignore isolated example numbering such as "2.0".
        if re.fullmatch(r'\d+(?:\.\d+)*\.?', token):
            continue
        tokens.append(token)
    return tokens


def _clean_descriptive_token(token: str) -> str:
    token = token.upper().replace('0-0', 'O-O')
    token = re.sub(r'[!?]+$', '', token)
    token = re.sub(r'[+#]+$', '', token)
    # Common ClearScan/OCR confusions in a rank digit.
    if len(token) > 1 and token[0] in PIECE_TYPES:
        rest = token[1:]
        rest = re.sub(r'^[IL|]', '1', rest)
        rest = re.sub(r'^S(?=[TCDRA])', '5', rest)
        token = token[0] + rest
    return token


def _descriptive_candidate(board: chess.Board, token: str, english: bool = False) -> chess.Move:
    def message(es, en):
        return en if english else es

    token = _clean_descriptive_token(token)
    castle = token.replace('0', 'O')
    if castle in ('O-O', 'O-O-O'):
        try:
            return board.parse_san(castle)
        except ValueError as exc:
            raise ValueError(message(f"enroque ilegal: {token}", f"illegal castling move: {token}")) from exc

    if not token or token[0] not in PIECE_TYPES:
        raise ValueError(message('no parece una jugada descriptiva española',
                                 'not a Spanish descriptive move'))
    moving_type = PIECE_TYPES[token[0]]
    rest = token[1:]
    capture = 'x' in rest.lower() or ':' in rest
    rest = re.sub(r'[xX:]', '', rest)

    target_piece_type = None
    target_rank = None
    target_files = None
    square_match = re.fullmatch(r'([1-8])([A-Z]{0,2})', rest)
    if square_match:
        target_rank = int(square_match.group(1))
        file_name = square_match.group(2)
        if file_name:
            target_files = FILE_OPTIONS.get(file_name)
            if target_files is None:
                raise ValueError(message(f"columna descriptiva no reconocida: {file_name}",
                                         f"unknown descriptive file: {file_name}"))
    elif rest in PIECE_TYPES and capture:
        target_piece_type = PIECE_TYPES[rest]
    elif rest:
        raise ValueError(message('formato descriptivo no reconocido',
                                 'unrecognized descriptive notation format'))

    target_rank_index = None
    if target_rank is not None:
        target_rank_index = target_rank - 1 if board.turn == chess.WHITE else 8 - target_rank

    matches = []
    for move in board.legal_moves:
        piece = board.piece_at(move.from_square)
        if not piece or piece.piece_type != moving_type:
            continue
        if target_rank_index is not None and chess.square_rank(move.to_square) != target_rank_index:
            continue
        if target_files is not None and chess.square_file(move.to_square) not in target_files:
            continue
        is_capture = board.is_capture(move)
        if capture and not is_capture:
            continue
        if target_piece_type is not None:
            captured = board.piece_at(move.to_square)
            captured_type = chess.PAWN if board.is_en_passant(move) else (captured.piece_type if captured else None)
            if captured_type != target_piece_type:
                continue
        # Descriptive pawn captures such as PxP identify the captured piece;
        # without a capture indicator, a pawn move still needs a destination.
        if not capture and target_rank_index is None:
            continue
        matches.append(move)

    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(message('no hay una jugada legal que coincida con la posición',
                                 'no legal move matches the current position'))
    squares = ', '.join(chess.square_name(move.to_square) for move in matches)
    raise ValueError(message(f"jugada ambigua; posibles destinos: {squares}",
                             f"ambiguous move; possible destinations: {squares}"))


def format_san(board: chess.Board, moves: list[chess.Move]) -> str:
    """Format a move sequence in standard algebraic notation from board."""
    working = board.copy(stack=True)
    tokens = []
    for move in moves:
        number = working.fullmove_number
        white_to_move = working.turn == chess.WHITE
        san = working.san(move)
        if white_to_move:
            tokens.append(f'{number}. {san}')
        elif tokens and not tokens[-1].endswith('...'):
            tokens[-1] += f' {san}'
        else:
            tokens.append(f'{number}... {san}')
        working.push(move)
    return ' '.join(tokens)


def parse_line(board: chess.Board, text: str, notation: str = 'Descriptive',
               language: str = 'Español') -> tuple[list[chess.Move], str]:
    """Parse an entire line atomically; return legal moves and SAN text.

    ``notation`` may be ``SAN`` or ``Descriptive``. Descriptive moves are
    resolved from the current board, so callers must first set up the diagram
    shown in the book when the line does not start from the normal initial
    position.
    """
    tokens = tokenize(text)
    english = language == 'English'
    if not tokens:
        raise ValueError('no moves were found' if english else 'no se encontraron jugadas')
    working = board.copy(stack=True)
    moves = []
    for index, token in enumerate(tokens, 1):
        try:
            if notation == 'SAN':
                move = working.parse_san(token)
            else:
                try:
                    move = working.parse_san(token)
                except ValueError:
                    move = _descriptive_candidate(working, token, english)
            san = working.san(move)
            moves.append(move)
            working.push(move)
        except (ValueError, AssertionError) as exc:
            prefix = f"move {index} ({token}): " if english else f"jugada {index} ({token}): "
            raise ValueError(prefix + str(exc)) from exc
    return moves, format_san(board, moves)
