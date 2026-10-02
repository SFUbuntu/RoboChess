"""Generate simple circular cartoon avatars used by player profiles."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / 'avatars'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 160


def circle_base(bg):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, SIZE - 3, SIZE - 3), fill=bg)
    return img, d


def face(d, skin, cx=80, cy=78, r=38):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=skin)
    d.ellipse((cx - 14, cy - 8, cx - 6, cy + 2), fill='#2b2b2b')
    d.ellipse((cx + 6, cy - 8, cx + 14, cy + 2), fill='#2b2b2b')
    d.arc((cx - 14, cy + 4, cx + 14, cy + 22), 10, 170, fill='#c45b6a', width=3)


def hair(d, color, style):
    if style == 'short':
        d.pieslice((34, 28, 126, 90), 200, 340, fill=color)
    elif style == 'bob':
        d.ellipse((28, 30, 132, 110), fill=color)
    elif style == 'pigtails':
        d.ellipse((18, 70, 42, 104), fill=color)
        d.ellipse((118, 70, 142, 104), fill=color)
        d.ellipse((32, 28, 128, 88), fill=color)
    elif style == 'curly':
        for x, y in ((40, 42), (58, 28), (80, 24), (102, 28), (120, 42)):
            d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=color)
    elif style == 'blond':
        d.ellipse((30, 26, 130, 92), fill=color)
        d.polygon([(40, 70), (28, 118), (52, 90)], fill=color)
        d.polygon([(120, 70), (132, 118), (108, 90)], fill=color)


SPECS = {
    'hombre': dict(bg='#5da9e9', skin='#f0c39a', hair='#3b2a1a', hair_style='short'),
    'mujer': dict(bg='#f28ab2', skin='#f0c39a', hair='#4a2c14', hair_style='blond'),
    'nino': dict(bg='#7dcfb6', skin='#f6d3a8', hair='#6b3a18', hair_style='short'),
    'nina': dict(bg='#ffd166', skin='#f6d3a8', hair='#8b3a1a', hair_style='pigtails'),
    'astronauta': dict(bg='#3d5a80', skin='#f0c39a', hair=None, extra='astro'),
    'robot': dict(bg='#90a4ae', skin='#cfd8dc', hair=None, extra='robot'),
    'duende': dict(bg='#80b918', skin='#c8e07a', hair='#2d6a4f', hair_style='short', extra='elf'),
    'unicornio': dict(bg='#c77dff', skin='#ffe5ec', hair='#ffafcc', hair_style='curly', extra='uni'),
    'abuelo': dict(bg='#adb5bd', skin='#efd3b8', hair='#ececec', hair_style='short'),
    'abuela': dict(bg='#ffcfd2', skin='#efd3b8', hair='#f8f7f4', hair_style='bob'),
}


def extras(d, kind):
    if kind == 'astro':
        d.ellipse((36, 36, 124, 124), outline='#eef2f5', width=10)
        d.arc((48, 48, 100, 88), 200, 20, fill='#8ecae6', width=6)
    elif kind == 'robot':
        d.rectangle((48, 48, 112, 112), fill='#b0bec5', outline='#37474f', width=3)
        d.rectangle((60, 68, 74, 82), fill='#4fc3f7')
        d.rectangle((86, 68, 100, 82), fill='#4fc3f7')
        d.rectangle((68, 92, 92, 100), fill='#37474f')
        d.rectangle((72, 28, 88, 48), fill='#78909c')
    elif kind == 'elf':
        d.polygon([(80, 8), (64, 48), (96, 48)], fill='#2d6a4f')
        d.polygon([(28, 78), (8, 96), (36, 92)], fill='#c8e07a')
        d.polygon([(132, 78), (152, 96), (124, 92)], fill='#c8e07a')
    elif kind == 'uni':
        d.polygon([(80, 6), (72, 48), (88, 48)], fill='#bde0fe')
        d.ellipse((108, 36, 132, 60), fill='#ffafcc')


def build(name, spec):
    img, d = circle_base(spec['bg'])
    if spec.get('hair') and spec.get('hair_style') in ('bob', 'curly', 'blond', 'pigtails'):
        hair(d, spec['hair'], spec['hair_style'])
    if spec.get('extra') != 'robot':
        face(d, spec['skin'])
    if spec.get('hair') and spec.get('hair_style') == 'short':
        hair(d, spec['hair'], 'short')
    extras(d, spec.get('extra'))
    path = OUT / f'{name}.png'
    img.save(path)
    print(path)


if __name__ == '__main__':
    for name, spec in SPECS.items():
        build(name, spec)
