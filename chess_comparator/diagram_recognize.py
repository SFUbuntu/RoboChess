"""Read a printed chess diagram and return its piece placement as FEN.

The reader first finds the checkerboard inside the marked area, then compares
each square with the empty squares of the same color. That keeps the diagonal
hatching of book diagrams from being mistaken for pieces.
"""
from __future__ import annotations

import io

import chess


def recognize_diagram(png_data):
    try:
        from PIL import Image
    except ImportError:
        return None
    image = Image.open(io.BytesIO(png_data)).convert('L')
    board_image = _find_board(image)
    if board_image is None:
        return None
    cells = [_cell(board_image, file, rank) for rank in range(8) for file in range(8)]
    pieces = _pieces(cells)
    if not pieces:
        return None
    board = chess.Board.empty()
    for file, rank, cell in pieces:
        color = chess.BLACK if cell['fill'] > 0.5 else chess.WHITE
        board.set_piece_at(chess.square(file, 7 - rank), chess.Piece(_kind(cell), color))
    return board.board_fen()


def _find_board(image):
    """Return a 256px board crop, or None if no checkerboard is visible."""
    width, height = image.size
    if min(width, height) < 70:
        return None
    best = None
    # Coarse search: the marked area should already be close to the diagram.
    for scale in (1.0, 0.92, 0.84, 0.76):
        side = int(min(width, height) * scale)
        if side < 64:
            continue
        for top in range(0, height - side + 1, max(4, side // 16)):
            for left in range(0, width - side + 1, max(4, side // 16)):
                score = _checker_score(image, left, top, side)
                if best is None or score > best[0]:
                    best = (score, left, top, side)
    if best is None or best[0] < 0.12:
        return None
    _, left, top, side = best
    return image.crop((left, top, left + side, top + side)).resize((256, 256))


def _checker_score(image, left, top, side):
    """High when the 8x8 cells alternate between plain and hatched squares."""
    cell = side / 8
    values = []
    for rank in range(8):
        for file in range(8):
            x = int(left + (file + 0.5) * cell)
            y = int(top + (rank + 0.5) * cell)
            values.append(_sample(image, x, y))
    if not values:
        return 0
    light = [values[i] for i in range(64) if (i // 8 + i % 8) % 2 == 0]
    dark = [values[i] for i in range(64) if (i // 8 + i % 8) % 2 == 1]
    # Either parity may be the hatched color. A real board has one bright set.
    gap = abs(sum(light) / len(light) - sum(dark) / len(dark))
    return gap / 255


def _sample(image, x, y):
    pixels = image.load()
    total = 0
    count = 0
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            xx, yy = x + dx, y + dy
            if 0 <= xx < image.width and 0 <= yy < image.height:
                total += pixels[xx, yy]
                count += 1
    return total / max(1, count)


def _cell(image, file, rank):
    cell = 32
    crop = image.crop((file * cell + 3, rank * cell + 3, (file + 1) * cell - 3, (rank + 1) * cell - 3))
    data = list(crop.getdata())
    width = crop.width
    ink = [pixel < 115 for pixel in data]
    center = [
        dark for index, dark in enumerate(ink)
        if width * 0.24 < index % width < width * 0.76 and width * 0.18 < index // width < width * 0.84
    ]
    rows = [0] * width
    cols = [0] * width
    for index, dark in enumerate(ink):
        if dark:
            rows[index // width] += 1
            cols[index % width] += 1
    return {
        'file': file,
        'rank': rank,
        'dark': (file + rank) % 2 == 1,
        'center': sum(center) / max(1, len(center)),
        'fill': sum(ink) / len(ink),
        'rows': rows,
        'cols': cols,
        'width': width,
    }


def _pieces(cells):
    found = []
    for dark in (False, True):
        group = [cell for cell in cells if cell['dark'] == dark]
        background = sorted(cell['center'] for cell in group)[len(group) // 2]
        for cell in group:
            if cell['center'] >= max(0.24, background + 0.16):
                found.append((cell['file'], cell['rank'], cell))
    return found


def _kind(cell):
    rows = cell['rows']
    width = cell['width']
    used = [index for index, count in enumerate(rows) if count]
    if len(used) < 3:
        return chess.PAWN
    height = used[-1] - used[0] + 1
    top_mass = sum(rows[used[0]:used[0] + max(1, height // 3)])
    bottom_mass = sum(rows[used[-1] - max(1, height // 3):used[-1] + 1])
    used_width = sum(1 for count in cell['cols'] if count)
    if used_width >= width * 0.4 and top_mass >= bottom_mass:
        return chess.KING
    if used_width <= width * 0.38 and height >= width * 0.42:
        return chess.ROOK
    if top_mass > bottom_mass * 1.2:
        return chess.BISHOP
    if used_width >= width * 0.4:
        return chess.KNIGHT
    return chess.PAWN
