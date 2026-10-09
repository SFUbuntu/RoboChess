"""Best-effort recognition of a printed chess diagram crop."""
from __future__ import annotations

import io

import chess


def recognize_diagram(png_data):
    """Return a FEN board placement, or None if the crop is not a board.

    Piece types are estimated from the ink shape. The caller should let the
    user confirm the side to move before analysis.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    image = Image.open(io.BytesIO(png_data)).convert('RGB')
    if image.width < 80 or image.height < 80:
        return None
    side = min(image.width, image.height)
    image = image.crop((0, 0, side, side)).resize((256, 256))
    cell = 32
    squares = []
    for rank in range(8):
        for file in range(8):
            crop = image.crop((file * cell + 4, rank * cell + 4, (file + 1) * cell - 4, (rank + 1) * cell - 4))
            pixels = list(crop.getdata())
            mean = tuple(sum(channel) / len(pixels) for channel in zip(*pixels))
            variance = sum(sum((pixel[i] - mean[i]) ** 2 for i in range(3)) for pixel in pixels) / len(pixels)
            squares.append((mean, variance, pixels))
    empty_light = _background([squares[i] for i in range(64) if (i // 8 + i % 8) % 2 == 0])
    empty_dark = _background([squares[i] for i in range(64) if (i // 8 + i % 8) % 2 == 1])
    board = chess.Board.empty()
    occupied = 0
    for index, (mean, variance, pixels) in enumerate(squares):
        dark = (index // 8 + index % 8) % 2 == 1
        background = empty_dark if dark else empty_light
        distance = sum(abs(mean[i] - background[i]) for i in range(3))
        if variance < 180 and distance < 28:
            continue
        occupied += 1
        color = chess.BLACK if sum(mean) < sum(background) - 18 else chess.WHITE
        piece = _piece_type(pixels, background)
        board.set_piece_at(chess.square(index % 8, 7 - index // 8), chess.Piece(piece, color))
    if occupied < 2 or occupied > 32:
        return None
    return board.board_fen()


def _background(samples):
    quiet = sorted(samples, key=lambda item: item[1])[:6]
    return tuple(sum(item[0][channel] for item in quiet) / len(quiet) for channel in range(3))


def _piece_type(pixels, background):
    ink = [pixel for pixel in pixels if sum(abs(pixel[i] - background[i]) for i in range(3)) > 45]
    if len(ink) < 8:
        return chess.PAWN
    width = 24
    rows = [0] * width
    cols = [0] * width
    for offset, pixel in enumerate(pixels):
        if sum(abs(pixel[i] - background[i]) for i in range(3)) <= 45:
            continue
        rows[offset // width] += 1
        cols[offset % width] += 1
    top = sum(rows[:8])
    bottom = sum(rows[-8:])
    height = sum(1 for count in rows if count)
    width_used = sum(1 for count in cols if count)
    if height >= 16 and width_used >= 12 and top > bottom:
        return chess.QUEEN if top > bottom * 1.4 else chess.KING
    if height >= 14 and width_used <= 8:
        return chess.ROOK
    if top > bottom * 1.6 and height < 15:
        return chess.BISHOP
    if width_used >= 12 and height < 15:
        return chess.KNIGHT
    return chess.PAWN
