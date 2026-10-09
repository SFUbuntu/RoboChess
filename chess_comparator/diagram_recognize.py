"""Recognize printed chess diagrams, including hatched book diagrams."""
from __future__ import annotations

import io

import chess


def recognize_diagram(png_data):
    try:
        from PIL import Image
    except ImportError:
        return None
    image = Image.open(io.BytesIO(png_data)).convert('L')
    side = min(image.width, image.height)
    if side < 70:
        return None
    image = image.crop((0, 0, side, side)).resize((256, 256))
    cell = 32
    board = chess.Board.empty()
    occupied = 0
    for rank in range(8):
        for file in range(8):
            crop = image.crop((file * cell + 3, rank * cell + 3, (file + 1) * cell - 3, (rank + 1) * cell - 3))
            kind = _square_kind(crop)
            if kind is None:
                continue
            color, piece = kind
            board.set_piece_at(chess.square(file, 7 - rank), chess.Piece(piece, color))
            occupied += 1
    if occupied < 1 or occupied > 32:
        return None
    return board.board_fen()


def _trim_board(image):
    pixels = image.load()
    width, height = image.size
    xs = [x for y in range(height) for x in range(width) if pixels[x, y] < 90]
    ys = [y for y in range(height) for x in range(width) if pixels[x, y] < 90]
    if len(xs) < 40:
        return None
    left, right = max(0, min(xs) - 2), min(width, max(xs) + 3)
    top, bottom = max(0, min(ys) - 2), min(height, max(ys) + 3)
    if right - left < 70 or bottom - top < 70:
        return None
    return image.crop((left, top, right, bottom))


def _square_kind(crop):
    data = list(crop.getdata())
    dark = [pixel < 105 for pixel in data]
    ratio = sum(dark) / len(data)
    if ratio < 0.12:
        return None
    width = crop.width
    center = [pixel for index, pixel in enumerate(data)
              if width * 0.22 < index % width < width * 0.78 and width * 0.18 < index // width < width * 0.84]
    center_ratio = sum(pixel < 105 for pixel in center) / max(1, len(center))
    periodic = _hatch_score(data, width)
    if center_ratio < 0.30 or periodic > 0.76:
        return None
    color = chess.BLACK if center_ratio > 0.36 else chess.WHITE
    return color, _piece_type(data, width)


def _hatch_score(data, width):
    hits = 0
    checks = 0
    for index, dark in enumerate(pixel < 105 for pixel in data):
        x, y = index % width, index // width
        if x + 3 >= width or y + 3 >= width:
            continue
        other = data[(y + 3) * width + (x + 3)] < 105
        checks += 1
        hits += dark == other
    return hits / checks if checks else 0


def _piece_type(data, width):
    ink = [index for index, pixel in enumerate(data) if pixel < 105 and width * 0.18 < index % width < width * 0.82]
    if len(ink) < 6:
        return chess.PAWN
    rows = {}
    cols = {}
    for index in ink:
        rows[index // width] = rows.get(index // width, 0) + 1
        cols[index % width] = cols.get(index % width, 0) + 1
    top = min(rows)
    height = max(rows) - top + 1
    top_mass = sum(count for row, count in rows.items() if row < top + height * 0.35)
    bottom_mass = sum(count for row, count in rows.items() if row > top + height * 0.65)
    used_width = len(cols)
    if used_width >= width * 0.45 and top_mass > bottom_mass:
        return chess.KING
    if used_width <= width * 0.34 and height > width * 0.45:
        return chess.ROOK
    if top_mass > bottom_mass * 1.3:
        return chess.BISHOP
    if used_width >= width * 0.4:
        return chess.KNIGHT
    return chess.PAWN
