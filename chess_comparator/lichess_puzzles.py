"""Small, streaming reader for the public Lichess puzzle CSV export."""
import csv
import gzip
import random


# Display categories follow the organization used by Lichess Puzzle Themes.
PUZZLE_CATEGORIES = {
    'Recomendados / Recommended': [
        ('Mezcla saludable / Healthy mix', ''),
    ],
    'Fases / Phases': [
        ('Apertura / Opening', 'opening'), ('Medio juego / Middlegame', 'middlegame'),
        ('Final / Endgame', 'endgame'), ('Final de torres / Rook endgame', 'rookEndgame'),
        ('Final de alfiles / Bishop endgame', 'bishopEndgame'), ('Final de peones / Pawn endgame', 'pawnEndgame'),
        ('Final de caballos / Knight endgame', 'knightEndgame'), ('Final de damas / Queen endgame', 'queenEndgame'),
        ('Final de dama y torre / Queen and rook endgame', 'queenRookEndgame'),
    ],
    'Aperturas / Openings': [
        ('Defensa Siciliana / Sicilian Defense', 'Sicilian_Defense'),
        ('Defensa Francesa / French Defense', 'French_Defense'),
        ('Apertura Italiana / Italian Game', 'Italian_Game'),
        ('Defensa Caro-Kann / Caro-Kann Defense', 'Caro-Kann_Defense'),
        ('Defensa Escandinava / Scandinavian Defense', 'Scandinavian_Defense'),
        ('Apertura de peón de dama / Queen’s Pawn Game', 'Queens_Pawn_Game'),
        ('Gambito de Dama Rehusado / Queen’s Gambit Declined', 'Queens_Gambit_Declined'),
        ('Apertura Inglesa / English Opening', 'English_Opening'),
        ('Apertura Española / Ruy Lopez', 'Ruy_Lopez'),
        ('Apertura Escocesa / Scotch Game', 'Scotch_Game'),
        ('Defensa India / Indian Defense', 'Indian_Defense'), ('Defensa Philidor / Philidor Defense', 'Philidor_Defense'),
    ],
    'Motivos / Motifs': [
        ('Peón avanzado / Advanced pawn', 'advancedPawn'), ('Ataque a f2/f7 / Attack f2/f7', 'attackingF2F7'),
        ('Eliminar defensor / Capture the defender', 'capturingDefender'), ('Ataque descubierto / Discovered attack', 'discoveredAttack'),
        ('Jaque doble / Double check', 'doubleCheck'), ('Rey expuesto / Exposed king', 'exposedKing'),
        ('Clavada / Pin', 'pin'), ('Tenedor / Fork', 'fork'), ('Pieza colgada / Hanging piece', 'hangingPiece'),
        ('Ataque al rey / Kingside attack', 'kingsideAttack'), ('Ataque al flanco de dama / Queenside attack', 'queensideAttack'),
        ('Sacrificio / Sacrifice', 'sacrifice'), ('Enfilada / Skewer', 'skewer'), ('Pieza atrapada / Trapped piece', 'trappedPiece'),
    ],
    'Avanzados / Advanced': [
        ('Atracción / Attraction', 'attraction'), ('Despeje / Clearance', 'clearance'),
        ('Jaque descubierto / Discovered check', 'discoveredCheck'), ('Defensa precisa / Defensive move', 'defensiveMove'),
        ('Desviación / Deflection', 'deflection'), ('Interferencia / Interference', 'interference'),
        ('Intermedia / Zwischenzug', 'intermezzo'), ('Jugada tranquila / Quiet move', 'quietMove'),
        ('Ataque X-Ray / X-Ray attack', 'xRayAttack'), ('Zugzwang / Zugzwang', 'zugzwang'),
    ],
    'Mates / Mates': [
        ('Jaque mate / Checkmate', 'mate'), ('Mate en 1 / Mate in 1', 'mateIn1'),
        ('Mate en 2 / Mate in 2', 'mateIn2'), ('Mate en 3 / Mate in 3', 'mateIn3'),
        ('Mate en 4 / Mate in 4', 'mateIn4'), ('Mate en 5 o más / Mate in 5+', 'mateIn5'),
    ],
    'Patrones de mate / Mate themes': [
        ('Mate de Anastasia / Anastasia’s mate', 'anastasiaMate'), ('Mate árabe / Arabian mate', 'arabianMate'),
        ('Mate en la última fila / Back rank mate', 'backRankMate'), ('Mate de Boden / Boden’s mate', 'bodenMate'),
        ('Mate Balestra / Balestra mate', 'balestraMate'), ('Mate Blind Swine / Blind Swine mate', 'blindSwineMate'),
        ('Mate de esquina / Corner mate', 'cornerMate'), ('Mate de alfiles / Double bishop mate', 'doubleBishopMate'),
        ('Mate Dovetail / Dovetail mate', 'dovetailMate'), ('Mate Epaulette / Epaulette mate', 'epauletteMate'),
        ('Mate Hook / Hook mate', 'hookMate'), ('Mate Kill Box / Kill box mate', 'killBoxMate'),
        ('Mate de Morphy / Morphy’s mate', 'morphysMate'), ('Mate de Opera / Opera mate', 'operaMate'),
        ('Mate de Pillsbury / Pillsbury’s mate', 'pillsburysMate'), ('Mate Swallow’s tail', 'swallowsTailMate'),
        ('Mate triangular / Triangle mate', 'triangleMate'), ('Mate ahogado / Smothered mate', 'smotheredMate'),
        ('Mate Vuković / Vukovic mate', 'vukovicMate'),
    ],
    'Jugadas especiales / Special moves': [
        ('Enroque / Castling', 'castling'), ('Captura al paso / En passant', 'enPassant'),
        ('Promoción / Promotion', 'promotion'), ('Subpromoción / Underpromotion', 'underPromotion'),
    ],
    'Objetivos / Goals': [
        ('Igualar / Equality', 'equality'), ('Conseguir ventaja / Advantage', 'advantage'),
        ('Ventaja decisiva / Crushing', 'crushing'),
    ],
    'Longitud / Length': [
        ('Una jugada / One-move puzzle', 'oneMove'), ('Corto / Short', 'short'),
        ('Largo / Long', 'long'), ('Muy largo / Very long', 'veryLong'),
    ],
    'Origen / Origin': [
        ('Partidas de maestros / Master games', 'master'), ('Maestro contra maestro / Master vs Master', 'masterVsMaster'),
        ('Super GM', 'superGM'),
    ],
}


def _open_text(path):
    lower = str(path).lower()
    if lower.endswith('.zst'):
        try:
            import zstandard
        except ImportError as exc:
            raise RuntimeError('Para leer .zst instala zstandard: py -m pip install zstandard') from exc
        binary = open(path, 'rb')
        reader = zstandard.ZstdDecompressor().stream_reader(binary)
        import io
        return io.TextIOWrapper(reader, encoding='utf-8', errors='replace')
    if lower.endswith('.gz'):
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace', newline='')
    return open(path, 'r', encoding='utf-8-sig', errors='replace', newline='')


def pick_puzzle(path, theme_tag='', scan_rows=250_000, reservoir_size=800):
    """Reservoir-sample one matching row from a bounded prefix of a large CSV."""
    reservoir = []
    matching = 0
    with _open_text(path) as source:
        rows = csv.DictReader(source)
        for index, row in enumerate(rows):
            if index >= scan_rows:
                break
            themes = set((row.get('Themes') or '').split()) | set((row.get('OpeningTags') or '').split())
            if theme_tag and theme_tag not in themes:
                continue
            matching += 1
            if len(reservoir) < reservoir_size:
                reservoir.append(row)
            else:
                slot = random.randrange(matching)
                if slot < reservoir_size:
                    reservoir[slot] = row
    if not reservoir:
        raise LookupError('No matching puzzle found in the scanned rows. Try another theme or a larger CSV sample.')
    return random.choice(reservoir)
