# Draws the 24x24 pixel characters the AI can pick from.
# Letters: . empty  K outline  M main color  D main (shade)  A accent
#          W white  E eye (blinks)
from PIL import Image, ImageDraw
import math, sys, os, json

N = 24

class Grid:
    def __init__(s):
        s.g = [['.'] * N for _ in range(N)]
    def mask(s, fn, ch):
        im = Image.new('L', (N, N), 0)
        fn(ImageDraw.Draw(im))
        for y in range(N):
            for x in range(N):
                if im.getpixel((x, y)) > 127: s.g[y][x] = ch
    def ell(s, cx, cy, rx, ry, ch='M'):
        s.mask(lambda d: d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255), ch)
    def poly(s, pts, ch='M'):
        s.mask(lambda d: d.polygon(pts, fill=255), ch)
    def rect(s, x0, y0, x1, y1, ch='M'):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                s.set(x, y, ch)
    def set(s, x, y, ch):
        if 0 <= x < N and 0 <= y < N: s.g[y][x] = ch
    def pts(s, lst, ch):
        for x, y in lst: s.set(x, y, ch)
    def get(s, x, y):
        return s.g[y][x] if 0 <= x < N and 0 <= y < N else '.'
    def finish(s, shade=True):
        # shade: main pixels touching the bottom/right edge get darker
        if shade:
            out = [r[:] for r in s.g]
            for y in range(N):
                for x in range(N):
                    if s.g[y][x] == 'M':
                        if s.get(x + 1, y) == '.' or s.get(x, y + 1) == '.' or s.get(x + 1, y + 1) == '.':
                            out[y][x] = 'D'
            s.g = out
        # outline around everything
        out = [r[:] for r in s.g]
        for y in range(N):
            for x in range(N):
                if s.g[y][x] == '.':
                    if any(s.get(x + dx, y + dy) not in '.' for dx, dy in ((1,0),(-1,0),(0,1),(0,-1))):
                        out[y][x] = 'K'
        s.g = out
        return [''.join(r) for r in s.g]

def face(g, cx, cy, gap=3, blush=True, mouth=True):
    # two 2x2 eyes with a white shine, small w/smile mouth, blush
    for ex in (cx - gap - 1, cx + gap):
        g.pts([(ex, cy), (ex + 1, cy), (ex, cy + 1), (ex + 1, cy + 1)], 'E')
        g.set(ex, cy, 'W')
    if mouth:
        g.pts([(cx - 1, cy + 2), (cx, cy + 3), (cx + 1, cy + 2)], 'K') if gap >= 2 else None
    if blush:
        g.pts([(cx - gap - 3, cy + 2), (cx - gap - 2, cy + 2)], 'A')
        g.pts([(cx + gap + 2, cy + 2), (cx + gap + 3, cy + 2)], 'A')

def bunny():
    g = Grid()
    g.ell(8, 6, 2.6, 5.5); g.ell(15, 6, 2.6, 5.5)
    g.ell(8, 6, 1.0, 3.8, 'A'); g.ell(15, 6, 1.0, 3.8, 'A')
    g.ell(11.5, 15, 8.5, 6.8)
    face(g, 11, 14, 3)
    g.set(11, 15, 'A'); g.set(12, 15, 'A')
    g.pts([(10, 17), (11, 18), (12, 17), (13, 18), (14, 17)], 'K')
    g.pts([(11, 16), (12, 16)], 'M')
    # fix mouth override from face
    g.set(11, 16, 'M'); g.set(12, 16, 'M')
    return g.finish()

def cat():
    g = Grid()
    g.poly([(3, 2), (10, 8), (3, 12)]); g.poly([(20, 2), (13, 8), (20, 12)])
    g.poly([(4, 5), (7, 8), (4, 9)], 'A'); g.poly([(19, 5), (16, 8), (19, 9)], 'A')
    g.ell(11.5, 14, 9, 7)
    face(g, 11, 13, 3, mouth=False)
    g.set(11, 15, 'A'); g.set(12, 15, 'A')
    g.pts([(10, 16), (11, 17), (12, 17), (13, 16)], 'K')
    for y in (14, 16):   # whiskers
        g.set(1, y, 'K'); g.set(22, y, 'K')
    return g.finish()

def bear():
    g = Grid()
    g.ell(5, 6, 3.4, 3.4); g.ell(18, 6, 3.4, 3.4)
    g.ell(5, 6, 1.5, 1.5, 'A'); g.ell(18, 6, 1.5, 1.5, 'A')
    g.ell(11.5, 13, 9, 8)
    face(g, 11, 11, 3, mouth=False)
    g.ell(11.5, 16, 3.5, 2.4, 'W')
    g.pts([(11, 15), (12, 15)], 'K')
    g.pts([(10, 17), (11, 18), (12, 18), (13, 17)], 'K')
    return g.finish()

def frog():
    g = Grid()
    g.ell(6, 7, 3.8, 3.8); g.ell(17, 7, 3.8, 3.8)
    g.ell(11.5, 15, 10, 6.5)
    for ex in (6, 17):
        g.ell(ex, 7, 2.2, 2.2, 'W')
        g.pts([(ex - 1, 7), (ex, 7), (ex - 1, 8), (ex, 8)], 'E')
    g.pts([(4, 15), (5, 15), (18, 15), (19, 15)], 'A')
    g.pts([(7, 16)] + [(x, 17) for x in range(8, 16)] + [(16, 16)], 'K')
    return g.finish()

def ghost():
    g = Grid()
    g.ell(11.5, 10, 8.5, 8.5)
    g.rect(3, 10, 20, 18)
    for i, x in enumerate(range(3, 21, 3)):
        g.ell(x + 1, 19, 1.5, 1.8)
    g.pts([(5, 6), (6, 5), (5, 7)], 'W')
    face(g, 11, 10, 3)
    return g.finish(shade=True)

def alien():
    g = Grid()
    g.pts([(7, 1), (8, 2), (8, 3), (9, 4), (16, 1), (15, 2), (15, 3), (14, 4)], 'M')
    g.ell(7, 1, 1, 1, 'A'); g.ell(16, 1, 1, 1, 'A')
    g.ell(11.5, 12, 10, 7.5)
    g.poly([(5, 15), (18, 15), (11.5, 22)])
    for ex in (6, 14):
        g.poly([(ex - 1, 10), (ex + 3, 9), (ex + 4, 12), (ex, 13)], 'E')
        g.set(ex + 1, 10, 'W')
    g.pts([(10, 17), (11, 18), (12, 18), (13, 17)], 'K')
    return g.finish()

def heart():
    g = Grid()
    g.ell(7, 8, 5.5, 5.5); g.ell(16, 8, 5.5, 5.5)
    g.poly([(1.6, 10), (21.4, 10), (11.5, 21)])
    g.pts([(5, 5), (4, 6), (4, 7)], 'W')
    face(g, 11, 10, 3)
    return g.finish()

def star():
    g = Grid()
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 11 if i % 2 == 0 else 5
        pts.append((11.5 + math.cos(a) * r, 12.5 + math.sin(a) * r))
    g.poly(pts)
    face(g, 11, 12, 2, blush=False, mouth=False)
    g.pts([(11, 15), (12, 15)], 'K')
    g.pts([(7, 14), (16, 14)], 'A')
    return g.finish()

def mushroom():
    g = Grid()
    g.ell(11.5, 10, 10.5, 8)
    g.rect(0, 11, 23, 23, '.')
    g.rect(1, 10, 22, 11)
    g.ell(11.5, 16, 5, 5.5, 'W')
    g.rect(6, 12, 17, 12, '.')
    for cx, cy, r in ((6, 6, 1.6), (13, 4, 1.8), (18, 8, 1.4), (10, 9, 1.2)):
        g.ell(cx, cy, r, r, 'W')
    g.pts([(9, 15), (10, 15), (13, 15), (14, 15)], 'E')
    g.pts([(11, 17), (12, 17)], 'K')
    g.pts([(8, 17), (15, 17)], 'A')
    return g.finish()

def cherry():
    g = Grid()
    g.ell(6.5, 16, 5, 5); g.ell(17, 16, 5, 5)
    g.pts([(4, 13), (5, 12), (15, 13), (16, 12)], 'W')
    for (x, y) in [(7, 10), (8, 8), (9, 6), (10, 4), (11, 3), (12, 2), (16, 10), (15, 8), (14, 6), (13, 4)]:
        g.set(x, y, 'K')
    g.poly([(12, 2), (19, 0.5), (21, 3), (14, 4)], 'A')
    return g.finish()

def cloud():
    g = Grid()
    g.ell(11.5, 9, 6, 6); g.ell(5.5, 13, 4.5, 4.5); g.ell(18, 12, 5, 5)
    g.rect(3, 13, 20, 17)
    g.pts([(8, 5), (9, 4), (7, 6)], 'W')
    face(g, 11, 12, 3)
    return g.finish()

def moon():
    g = Grid()
    g.ell(12, 12, 10.5, 10.5)
    g.ell(17.5, 8, 9, 9, '.')
    g.pts([(5, 13), (6, 13), (5, 14)], 'E')
    g.pts([(6, 16), (7, 17), (8, 17)], 'K')
    g.pts([(3, 15), (8, 15)], 'A')
    return g.finish()

def flower():
    g = Grid()
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        g.ell(11.5 + math.cos(a) * 6.5, 11.5 + math.sin(a) * 6.5, 4.6, 4.6)
    g.ell(11.5, 11.5, 4.5, 4.5, 'A')
    g.pts([(10, 11), (13, 11)], 'E')
    g.pts([(11, 13), (12, 13)], 'K')
    return g.finish()

SPRITES = dict(bunny=bunny(), cat=cat(), bear=bear(), frog=frog(), ghost=ghost(),
               alien=alien(), heart=heart(), star=star(), mushroom=mushroom(),
               cherry=cherry(), cloud=cloud(), moon=moon(), flower=flower())

def export(here):
    # 1) for the clip (Arduino)
    h = ['// Made by ai/make_sprites.py. Change the drawings there, then run it again.',
         '// Letters: . empty  K outline  M main  D main shade  A accent  W white  E eye', '#pragma once', '']
    for n, rows in SPRITES.items():
        h.append(f'const char *const SPRITE_{n.upper()}[24] = {{')
        h += [f'  "{r}",' for r in rows]
        h.append('};')
    h.append('')
    h.append('struct SpriteDef { const char *name; const char *const *rows; };')
    h.append('const SpriteDef SPRITES[] = {')
    h += [f'  {{ "{n}", SPRITE_{n.upper()} }},' for n in SPRITES]
    h.append('};')
    h.append('const int SPRITE_COUNT = sizeof(SPRITES) / sizeof(SPRITES[0]);')
    open(os.path.join(here, '..', 'festival_clip', 'sprites.h'), 'w').write('\n'.join(h) + '\n')
    # 2) for the phone app preview (JavaScript)
    js = '// Made by ai/make_sprites.py. Same drawings as the clip uses.\nexport const SPRITES = ' + json.dumps(SPRITES, indent=1) + ';\n'
    open(os.path.join(here, '..', 'web-app', 'sprites.js'), 'w').write(js)

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    export(here)
    out = here
    # preview sheet: pink main, white accent... a few palettes
    pal = [(0xFF9CC8, 0xFFFFFF, 0x1A0033), (0x8FE36B, 0xFF6EA8, 0xFFF4D6), (0xB9A2FF, 0xFFE600, 0x14002B)]
    S = 6
    names = list(SPRITES)
    im = Image.new('RGB', (len(names) * 28 * S, len(pal) * 28 * S))
    def rgb(h): return ((h >> 16) & 255, (h >> 8) & 255, h & 255)
    def dark(h, f=0.72): return tuple(int(v * f) for v in rgb(h))
    d = ImageDraw.Draw(im)
    for r, (m, a, bg) in enumerate(pal):
        cols = dict(K=(43, 27, 46), M=rgb(m), D=dark(m), A=rgb(a), W=(255, 255, 255), E=(43, 27, 46))
        d.rectangle([0, r * 28 * S, im.width, (r + 1) * 28 * S], fill=rgb(bg))
        for i, n in enumerate(names):
            for y, row in enumerate(SPRITES[n]):
                for x, ch in enumerate(row):
                    if ch != '.':
                        X, Y = (i * 28 + 2 + x) * S, (r * 28 + 2 + y) * S
                        d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=cols[ch])
    im.save(os.path.join(out, 'sprites-preview.png'))
