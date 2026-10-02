"""Lucas Chess R2 board art, Polyglot books, Gaviota and FNS training adapters."""
from pathlib import Path
import os
import sys
import random
import re
import chess
import chess.polyglot
import chess.gaviota

def _assets_dir():
    candidates=[]
    if getattr(sys, 'frozen', False):
        candidates.append(Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))/'assets')
        candidates.append(Path(sys.executable).resolve().parent/'assets')
    candidates.append(Path(__file__).resolve().parent/'assets')
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]

ASSETS=_assets_dir()
LUCAS=ASSETS/'lucas_resources'
BOOKS=LUCAS/'Openings'
GAVIOTA=LUCAS/'Gaviota'
TRAINING=LUCAS/'Trainings'
TACTICS=LUCAS/'Tactics'
MATES=TRAINING/'Checkmates by Eduardo Sadier'/'Mate in one (derived from mate in two).fns'
PIECES=LUCAS/'Pieces'
BOOK=BOOKS/'GMopenings.bin'


def piece_sets():
    needed={c+p+'.svg' for c in 'wb' for p in 'kqrbnp'}
    result=[]
    names=set()
    if PIECES.is_dir():
        for folder in PIECES.iterdir():
            if folder.is_dir() and needed.issubset({f.name for f in folder.iterdir()}):
                names.add(folder.name)
    styles=ASSETS/'lucas_styles'
    if styles.is_dir():
        for folder in styles.iterdir():
            if folder.is_dir() and (folder/'K.png').is_file():
                names.add(folder.name)
    return sorted(names)


def book_files():
    if not BOOKS.is_dir():
        return []
    return sorted((p for p in BOOKS.rglob('*.bin') if p.is_file()),key=lambda p:str(p).lower())


def book_moves(board,path):
    with chess.polyglot.open_reader(str(path)) as reader:
        entries=sorted((e for e in reader.find_all(board) if e.move in board.legal_moves),key=lambda e:e.weight,reverse=True)
    total=sum(e.weight for e in entries)
    return [(board.san(e.move),e.weight,round(100*e.weight/total,1)) for e in entries] if total else []


def ending(board,directory=GAVIOTA):
    if board.castling_rights or len(board.piece_map())>5:
        raise ValueError('Gaviota only covers positions of up to five pieces without castling rights.')
    with chess.gaviota.open_tablebase(str(directory)) as tb:return tb.probe_wdl(board),tb.probe_dtm(board)


def training_sets():
    files=[]
    if TRAINING.is_dir():
        files.extend(TRAINING.rglob('*.fns'))
    if TACTICS.is_dir():
        files.extend(TACTICS.rglob('*.fns'))
    files=sorted(files)
    return {'All Lucas Chess exercises':files,**{str(p.relative_to(LUCAS)): [p] for p in files}}


def random_exercise(files):
    """Sample a random line from a selected collection without loading it all."""
    candidates=list(files)
    random.shuffle(candidates)
    for path in candidates:
        try:
            size=path.stat().st_size
            with path.open('rb') as stream:
                offsets=[0]+[random.randrange(size) for _ in range(29)] if size else [0]
                for offset in offsets:
                    stream.seek(offset)
                    if stream.tell():stream.readline()
                    raw=stream.readline().decode('utf-8-sig','replace').rstrip('\r\n')
                    if not raw.strip():continue
                    fields=raw.split('|')
                    try:
                        board=chess.Board(fields[0].strip())
                        if board.is_valid():return board,fields[2].strip() if len(fields)>2 else '',fields[1].strip() if len(fields)>1 else '',path
                    except ValueError:continue
        except OSError:continue
    raise ValueError('No valid training positions were found.')


def solution_moves(board,solution):
    """Parse the main SAN line, ignoring move numbers and comments."""
    clean=re.sub(r'\{[^}]*\}|\([^)]*\)', ' ', solution)
    clean=re.sub(r'\$\d+', ' ', clean)
    moves=[];copy=board.copy()
    for raw in clean.split():
        token=re.sub(r'^\d+\.{1,3}', '', raw)
        token=token.strip(' ,;')
        token=token.rstrip('!?')
        if token.endswith('++'):token=token[:-2]+'+'
        if not token or token in ('1-0','0-1','1/2-1/2','*','e.p.'):continue
        try:move=copy.parse_san(token)
        except ValueError:break
        moves.append(move);copy.push(move)
    return moves
