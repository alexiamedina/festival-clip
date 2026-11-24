"""
Alexia's pixel style engine: draws labeled 32x32 sprites in one consistent
style (dark cocoa outline, soft shading, little kawaii faces, blush).
These become the training pictures for her own text-to-pixel-art AI.

Every sprite = subject x color x expression x accessory, plus a caption
like "sleepy lavender cat with a crown". Run make_dataset.py to build the set.
"""
from PIL import Image, ImageDraw
import math, random

N = 32

# ---------- the 32-color palette (the model draws with these "crayons") ----------
# index 0 = empty (see-through). Each hue has a base and a shade.
HUES = {
    "pink": (0xFF9CC8, 0xD9709F), "hot pink": (0xFF4FA3, 0xC22F78), "red": (0xFF4A55, 0xC2283A),
    "orange": (0xFF9A3C, 0xD06A1C), "yellow": (0xFFE14D, 0xD6A920), "green": (0x8FE36B, 0x58AE45),
    "mint": (0x7DFFC8, 0x45C996), "blue": (0x5AA8FF, 0x2F6FD1), "purple": (0xA06BFF, 0x7041D1),
    "lavender": (0xC9B5FF, 0x9C86D6), "brown": (0xB07A50, 0x7E5234), "grey": (0xB8B8C4, 0x85858F),
    "black": (0x4A4A56, 0x2E2E38), "cream": (0xFFF4D6, 0xE3CFA4), "white": (0xFFFFFF, 0xD9DCE6),
}
PALETTE = [None, 0x2B1B2E]           # 0 empty, 1 outline
for base, shade in HUES.values():
    PALETTE += [base, shade]          # 2.. 31
assert len(PALETTE) == 32
def idx(hue, shade=False):
    return 2 + list(HUES).index(hue) * 2 + (1 if shade else 0)
OUTLINE = 1

# ---------- drawing on a 32x32 grid of labels ----------
# Labels: . empty  M main  A accent  W white  E eye(outline color)  K outline
#         B blush  G gold  L leaf  T tear  F fixed red  P dark pupil-ish
class Grid:
    def __init__(s):
        s.g = [['.'] * N for _ in range(N)]
    def _mask(s, fn, ch):
        im = Image.new('L', (N, N), 0)
        fn(ImageDraw.Draw(im))
        px = im.load()
        for y in range(N):
            for x in range(N):
                if px[x, y] > 127: s.g[y][x] = ch
    def ell(s, cx, cy, rx, ry, ch='M'):
        s._mask(lambda d: d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255), ch)
    def poly(s, pts, ch='M'):
        s._mask(lambda d: d.polygon(pts, fill=255), ch)
    def rect(s, x0, y0, x1, y1, ch='M'):
        for y in range(max(0, y0), min(N, y1 + 1)):
            for x in range(max(0, x0), min(N, x1 + 1)):
                s.g[y][x] = ch
    def line(s, pts, ch='K', w=1):
        s._mask(lambda d: d.line(pts, fill=255, width=w), ch)
    def set(s, x, y, ch):
        if 0 <= x < N and 0 <= y < N: s.g[y][x] = ch
    def pts(s, lst, ch):
        for x, y in lst: s.set(x, y, ch)
    def get(s, x, y):
        return s.g[y][x] if 0 <= x < N and 0 <= y < N else '.'
    def clear(s, x0, y0, x1, y1):
        s.rect(x0, y0, x1, y1, '.')

# A "Pose" tells faces and accessories where the head is.
class Pose:
    def __init__(s, cx, cy, gap=3, top=None, half=8, face=True):
        s.cx, s.cy, s.gap, s.top, s.half, s.face = cx, cy, gap, top if top is not None else cy - 8, half, face

# ---------- subjects ----------
def _round_head(g, cy=19, rx=10, ry=8.5):
    g.ell(15.5, cy, rx, ry)

def bunny(g):
    g.ell(11, 7, 3, 7); g.ell(20, 7, 3, 7)
    g.ell(11, 7, 1.2, 5, 'A'); g.ell(20, 7, 1.2, 5, 'A')
    _round_head(g); return Pose(15.5, 19, 3, top=11)
def cat(g):
    g.poly([(4, 3), (13, 11), (4, 16)]); g.poly([(27, 3), (18, 11), (27, 16)])
    g.poly([(6, 7), (10, 11), (6, 13)], 'A'); g.poly([(25, 7), (21, 11), (25, 13)], 'A')
    _round_head(g, 19, 11, 8.5)
    for y in (19, 21): g.set(2, y, 'K'); g.set(29, y, 'K')
    return Pose(15.5, 18, 3, top=10)
def bear(g):
    g.ell(7, 9, 4, 4); g.ell(24, 9, 4, 4); g.ell(7, 9, 2, 2, 'A'); g.ell(24, 9, 2, 2, 'A')
    _round_head(g, 18, 11, 9.5); g.ell(15.5, 22, 4.5, 3, 'W')
    return Pose(15.5, 16, 3, top=8)
def dog(g):
    _round_head(g, 18, 10, 9)
    g.ell(5, 15, 3.2, 6, 'A'); g.ell(26, 15, 3.2, 6, 'A')
    g.ell(15.5, 22, 4.5, 3, 'W')
    return Pose(15.5, 16, 3, top=9)
def fox(g):
    g.poly([(3, 2), (12, 10), (5, 15)]); g.poly([(28, 2), (19, 10), (26, 15)])
    g.poly([(5, 6), (9, 10), (6, 12)], 'W'); g.poly([(26, 6), (22, 10), (25, 12)], 'W')
    g.poly([(3, 13), (28, 13), (15.5, 29)]); g.ell(15.5, 16, 11, 6)
    g.poly([(8, 20), (23, 20), (15.5, 29)], 'W')
    return Pose(15.5, 16, 4, top=9)
def pig(g):
    g.poly([(5, 6), (11, 9), (6, 13)]); g.poly([(26, 6), (20, 9), (25, 13)])
    _round_head(g, 18, 11, 9)
    g.ell(15.5, 21, 3.5, 2.5, 'A'); g.pts([(14, 21), (17, 21)], 'K')
    return Pose(15.5, 16, 4, top=9)
def panda(g):
    g.ell(7, 9, 4, 4, 'K'); g.ell(24, 9, 4, 4, 'K')
    _round_head(g, 18, 11, 9.5)
    g.ell(10.5, 17.5, 3, 3.5, 'K'); g.ell(20.5, 17.5, 3, 3.5, 'K')
    return Pose(15.5, 17, 4, top=8)
def mouse(g):
    g.ell(7, 9, 6, 6); g.ell(24, 9, 6, 6); g.ell(7, 9, 3.5, 3.5, 'A'); g.ell(24, 9, 3.5, 3.5, 'A')
    _round_head(g, 20, 9.5, 8)
    for y in (21, 23): g.set(3, y, 'K'); g.set(28, y, 'K')
    return Pose(15.5, 19, 3, top=12)
def chick(g):
    g.ell(15.5, 17, 11, 11.5)
    g.pts([(14, 4), (15, 3), (16, 4), (17, 3)], 'M')
    g.poly([(13.5, 18), (17.5, 18), (15.5, 21)], 'G')
    g.ell(5, 21, 2.5, 4, 'M')
    return Pose(15.5, 15, 4, top=7)
def penguin(g):
    g.ell(15.5, 17, 11, 12.5)
    g.ell(15.5, 19, 8, 9, 'W')
    g.poly([(13.5, 17), (17.5, 17), (15.5, 20)], 'G')
    return Pose(15.5, 14, 3, top=6)
def frog(g):
    g.ell(8, 9, 5, 5); g.ell(23, 9, 5, 5)
    g.ell(15.5, 19, 13, 8.5)
    for ex in (8, 23):
        g.ell(ex, 9, 3, 3, 'W'); g.rect(ex - 1, 9, ex, 10, 'E')
    g.pts([(5, 20), (6, 20), (25, 20), (26, 20)], 'B')
    g.pts([(9, 21)] + [(x, 22) for x in range(10, 22)] + [(22, 21)], 'K')
    return Pose(15.5, 15, 3, top=5, face=False)
def ghost(g):
    g.ell(15.5, 13, 11, 11); g.rect(5, 13, 26, 24)
    for x in range(5, 27, 4): g.ell(x + 2, 25, 2, 2.4)
    g.pts([(8, 7), (9, 6), (8, 8)], 'W')
    return Pose(15.5, 14, 4, top=3)
def alien(g):
    g.line([(10, 1), (12, 7)], 'M', 1); g.line([(21, 1), (19, 7)], 'M', 1)
    g.ell(10, 1, 1.5, 1.5, 'A'); g.ell(21, 1, 1.5, 1.5, 'A')
    g.ell(15.5, 15, 13, 9.5); g.poly([(6, 19), (25, 19), (15.5, 30)])
    for ex in (8, 19):
        g.poly([(ex - 1, 13), (ex + 4, 12), (ex + 5, 16), (ex, 17)], 'E'); g.set(ex + 1, 13, 'W')
    g.pts([(14, 22), (15, 23), (16, 23), (17, 22)], 'K')
    return Pose(15.5, 15, 4, top=6, face=False)
def slime(g):
    g.ell(15.5, 20, 13, 9); g.rect(3, 20, 28, 27); g.ell(15.5, 9, 3, 4)
    g.pts([(8, 15), (9, 14), (7, 16)], 'W')
    return Pose(15.5, 20, 4, top=12)
def heart(g):
    g.ell(9.5, 11, 7.5, 7.5); g.ell(21.5, 11, 7.5, 7.5)
    g.poly([(2.2, 13), (28.8, 13), (15.5, 28)])
    g.pts([(6, 7), (5, 8), (5, 9)], 'W')
    return Pose(15.5, 14, 4, top=4)
def star(g):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; r = 15 if i % 2 == 0 else 6.8
        pts.append((15.5 + math.cos(a) * r, 17 + math.sin(a) * r))
    g.poly(pts)
    return Pose(15.5, 17, 3, top=6)
def moon(g):
    g.ell(16, 16, 14, 14); g.ell(23.5, 10, 12, 12, '.')
    g.pts([(6, 17), (7, 17), (6, 18)], 'E'); g.pts([(7, 21), (8, 22), (9, 22), (10, 21)], 'K')
    g.pts([(4, 20), (10, 19)], 'B')
    return Pose(8, 18, 3, top=4, face=False)
def cloud(g):
    g.ell(15.5, 12, 8, 8); g.ell(7.5, 18, 6, 6); g.ell(24, 17, 6.5, 6.5); g.rect(4, 18, 27, 23)
    g.pts([(11, 7), (12, 6), (10, 8)], 'W')
    return Pose(15.5, 17, 4, top=5)
def sun(g):
    for i in range(8):
        a = i * math.pi / 4
        g.poly([(15.5 + math.cos(a - .25) * 9, 16 + math.sin(a - .25) * 9), (15.5 + math.cos(a) * 15, 16 + math.sin(a) * 15),
                (15.5 + math.cos(a + .25) * 9, 16 + math.sin(a + .25) * 9)], 'A')
    g.ell(15.5, 16, 9.5, 9.5)
    return Pose(15.5, 16, 3, top=6)
def flower(g):
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        g.ell(15.5 + math.cos(a) * 8.5, 15.5 + math.sin(a) * 8.5, 6, 6)
    g.ell(15.5, 15.5, 6, 6, 'A')
    return Pose(15.5, 15, 2, top=3)
def mushroom(g):
    g.ell(15.5, 13, 14, 10.5); g.clear(0, 14, 31, 31); g.rect(2, 13, 29, 14)
    g.ell(15.5, 21, 7, 7.5, 'W'); g.clear(8, 15, 23, 15)
    for cx, cy, r in ((8, 8, 2.2), (17, 5, 2.5), (24, 10, 2), (13, 11, 1.6)): g.ell(cx, cy, r, r, 'W')
    return Pose(15.5, 20, 3, top=3)
def cherry(g):
    g.ell(9, 22, 6.5, 6.5); g.ell(23, 22, 6.5, 6.5)
    g.pts([(6, 18), (7, 17), (20, 18), (21, 17)], 'W')
    g.line([(10, 15), (16, 3)], 'K'); g.line([(22, 15), (17, 4)], 'K')
    g.poly([(16, 3), (25, 1), (27, 4), (18, 5)], 'L')
    return Pose(9, 22, 2, top=3, face=True)
def strawberry(g):
    g.poly([(4, 10), (27, 10), (24, 22), (15.5, 30), (7, 22)]); g.ell(15.5, 12, 11.5, 5)
    for x, y in ((9, 15), (15, 14), (21, 15), (12, 20), (19, 20), (15, 25)): g.set(x, y, 'G')
    g.poly([(8, 7), (15.5, 4), (23, 7), (19, 9), (15.5, 7), (12, 9)], 'L')
    return Pose(15.5, 17, 3, top=4)
def cupcake(g):
    g.poly([(7, 18), (24, 18), (22, 29), (9, 29)], 'A')
    for x in range(9, 23, 3): g.line([(x, 19), (x + 1, 28)], 'a')
    g.ell(15.5, 14, 11, 6); g.ell(15.5, 9, 7, 5); g.ell(15.5, 5, 3, 3, 'F')
    for x, y in ((9, 13), (20, 11), (14, 16), (23, 15)): g.set(x, y, 'W')
    return Pose(15.5, 22, 3, top=1, face=True)
def donut(g):
    g.ell(15.5, 17, 13.5, 11, 'A'); g.ell(15.5, 15.5, 12, 8.5)
    g.ell(15.5, 16, 3.5, 2.5, '.')
    for x, y in ((7, 13), (11, 9), (20, 9), (24, 14), (9, 19), (22, 20)): g.set(x, y, 'W')
    return Pose(15.5, 21, 3, top=5, face=False)
def icecream(g):
    g.poly([(8, 16), (23, 16), (15.5, 31)], 'G')
    g.line([(10, 18), (17, 29)], 'g'); g.line([(21, 18), (14, 29)], 'g')
    g.ell(15.5, 11, 9.5, 8); g.ell(15.5, 3, 2.5, 2.5, 'F')
    return Pose(15.5, 11, 3, top=3)
def boba(g):
    g.poly([(7, 7), (24, 7), (22, 30), (9, 30)], 'W'); g.poly([(8, 13), (23, 13), (22, 29), (9, 29)])
    for x, y in ((11, 26), (14, 27), (17, 26), (20, 27), (12, 23), (19, 23)): g.ell(x, y, 1, 1, 'K')
    g.rect(6, 5, 25, 7, 'A'); g.line([(17, 5), (21, 0)], 'A', 2)
    return Pose(15.5, 17, 3, top=5)
def gem(g):
    g.poly([(8, 6), (23, 6), (29, 13), (15.5, 29), (2, 13)])
    g.poly([(8, 6), (12, 13), (2, 13)], 'W'); g.line([(2, 13), (29, 13)], 'D')
    return Pose(15.5, 17, 3, top=6)
def planet(g):
    g.ell(15.5, 16, 10, 10)
    g.ell(15.5, 17, 15, 3.5, 'A'); g.ell(15.5, 16.2, 10, 2, 'M'); g.ell(15.5, 13, 10, 7, 'M'); g.clear(0, 0, 31, 3)
    return Pose(15.5, 13, 3, top=6)
def potion(g):
    g.ell(15.5, 21, 10, 9); g.rect(12, 4, 19, 13, 'W'); g.rect(11, 2, 20, 4, 'A')
    g.ell(15.5, 22, 8, 6.5, 'M'); g.ell(15.5, 17, 8, 2, 'W'); g.clear(0, 0, 31, 1)
    g.pts([(10, 21), (10, 22)], 'W')
    return Pose(15.5, 23, 3, top=2)
def cactus(g):
    g.rect(12, 5, 19, 24); g.ell(15.5, 6, 3.5, 3)
    g.rect(5, 11, 9, 17); g.rect(5, 17, 12, 20); g.rect(22, 9, 26, 15); g.rect(19, 15, 26, 18)
    g.poly([(8, 23), (23, 23), (21, 31), (10, 31)], 'A')
    return Pose(15.5, 13, 2, top=3)
def candle(g):
    g.rect(10, 11, 21, 30); g.ell(15.5, 5, 3, 5, 'G'); g.ell(15.5, 6, 1.4, 2.5, 'F')
    g.rect(15, 9, 16, 10, 'K'); g.rect(10, 11, 21, 12, 'W')
    return Pose(15.5, 19, 2, top=5)
def bow_subject(g):
    g.poly([(2, 6), (14, 13), (14, 18), (2, 25)]); g.poly([(29, 6), (17, 13), (17, 18), (29, 25)])
    g.ell(15.5, 15.5, 4, 4.5); g.poly([(12, 18), (9, 30), (13, 29), (15, 20)]); g.poly([(19, 18), (22, 30), (18, 29), (16, 20)])
    return Pose(15.5, 15, 1, top=6, face=False)

SUBJECTS = {
    "bunny": (bunny, ["bunny", "rabbit"]), "cat": (cat, ["cat", "kitty", "kitten"]), "bear": (bear, ["bear", "teddy bear"]),
    "dog": (dog, ["dog", "puppy"]), "fox": (fox, ["fox"]), "pig": (pig, ["pig", "piggy"]), "panda": (panda, ["panda"]),
    "mouse": (mouse, ["mouse"]), "chick": (chick, ["chick", "baby bird"]), "penguin": (penguin, ["penguin"]),
    "frog": (frog, ["frog", "toad"]), "ghost": (ghost, ["ghost"]), "alien": (alien, ["alien"]), "slime": (slime, ["slime", "blob"]),
    "heart": (heart, ["heart"]), "star": (star, ["star"]), "moon": (moon, ["moon", "crescent moon"]), "cloud": (cloud, ["cloud"]),
    "sun": (sun, ["sun"]), "flower": (flower, ["flower", "daisy"]), "mushroom": (mushroom, ["mushroom"]),
    "cherry": (cherry, ["cherries", "cherry"]), "strawberry": (strawberry, ["strawberry"]), "cupcake": (cupcake, ["cupcake"]),
    "donut": (donut, ["donut", "doughnut"]), "ice cream": (icecream, ["ice cream", "ice cream cone"]),
    "boba": (boba, ["boba", "bubble tea"]), "gem": (gem, ["gem", "crystal", "diamond"]), "planet": (planet, ["planet"]),
    "potion": (potion, ["potion", "magic potion"]), "cactus": (cactus, ["cactus"]), "candle": (candle, ["candle"]),
    "bow": (bow_subject, ["bow", "ribbon"]),
}
# The color each subject "usually" is, used when a caption doesn't name one.
NATURAL = {"bunny": "white", "cat": "orange", "bear": "brown", "dog": "brown", "fox": "orange", "pig": "pink",
           "panda": "white", "mouse": "grey", "chick": "yellow", "penguin": "black", "frog": "green", "ghost": "white",
           "alien": "green", "slime": "mint", "heart": "pink", "star": "yellow", "moon": "yellow", "cloud": "white",
           "sun": "yellow", "flower": "pink", "mushroom": "red", "cherry": "red", "strawberry": "red", "cupcake": "pink",
           "donut": "pink", "ice cream": "pink", "boba": "brown", "gem": "blue", "planet": "purple", "potion": "purple",
           "cactus": "green", "candle": "cream", "bow": "pink"}

# ---------- faces ----------
EXPRESSIONS = ["happy", "sleepy", "wink", "crying", "angry", "surprised", "in love"]

def face(g, p, expr):
    if not p.face: return
    cx, cy, gap = int(round(p.cx - 0.5)), int(round(p.cy)), p.gap
    L, R = cx - gap - 1, cx + gap + 1     # left eye x, right eye x (2 px wide)
    def open_eye(x):
        g.rect(x, cy, x + 1, cy + 1, 'E'); g.set(x, cy, 'W')
    def closed_eye(x, up=False):
        if up: g.pts([(x - 1, cy + 1), (x, cy), (x + 1, cy), (x + 2, cy + 1)], 'K')
        else: g.pts([(x - 1, cy), (x, cy + 1), (x + 1, cy + 1), (x + 2, cy)], 'K')
    if expr == "happy": open_eye(L); open_eye(R)
    elif expr == "sleepy": closed_eye(L); closed_eye(R)
    elif expr == "wink": open_eye(L); closed_eye(R, up=True)
    elif expr == "crying":
        closed_eye(L, up=True); closed_eye(R, up=True)
        g.pts([(L, cy + 2), (L, cy + 3), (R + 1, cy + 2), (R + 1, cy + 3)], 'T')
    elif expr == "angry":
        open_eye(L); open_eye(R)
        g.pts([(L - 1, cy - 2), (L, cy - 2), (L + 1, cy - 1), (R + 2, cy - 2), (R + 1, cy - 2), (R, cy - 1)], 'K')
    elif expr == "surprised":
        g.rect(L, cy - 1, L + 1, cy + 1, 'E'); g.rect(R, cy - 1, R + 1, cy + 1, 'E'); g.set(L, cy - 1, 'W'); g.set(R, cy - 1, 'W')
    elif expr == "in love":
        for x in (L, R): g.pts([(x - 1, cy), (x + 1, cy), (x - 1, cy + 1), (x, cy + 1), (x + 1, cy + 1), (x, cy + 2)], 'F'); g.set(x, cy, 'F')
    # mouth
    if expr == "surprised": g.rect(cx, cy + 3, cx + 1, cy + 4, 'K')
    elif expr == "angry": g.pts([(cx - 1, cy + 4), (cx, cy + 3), (cx + 1, cy + 3), (cx + 2, cy + 4)], 'K')
    elif expr == "crying": g.pts([(cx - 1, cy + 4), (cx, cy + 3), (cx + 1, cy + 3), (cx + 2, cy + 4)], 'K')
    else: g.pts([(cx - 1, cy + 3), (cx, cy + 4), (cx + 1, cy + 4), (cx + 2, cy + 3)], 'K')
    # blush
    if expr not in ("angry",):
        g.pts([(L - 2, cy + 3), (L - 1, cy + 3), (R + 2, cy + 3), (R + 3, cy + 3)], 'B')

# ---------- accessories ----------
ACCESSORIES = ["none", "crown", "bow", "party hat", "sunglasses", "headphones", "halo", "flower", "horns", "hearts"]
ACC_WORDS = {"crown": ["a crown", "a tiny crown"], "bow": ["a bow", "a ribbon"], "party hat": ["a party hat"],
             "sunglasses": ["sunglasses", "shades"], "headphones": ["headphones"], "halo": ["a halo"],
             "flower": ["a flower", "a flower on its head"], "horns": ["devil horns", "little horns"], "hearts": ["hearts", "floating hearts"]}

def accessory(g, p, acc):
    cx, top = int(round(p.cx - 0.5)), int(p.top)
    if acc == "crown":
        y = max(1, top - 5)
        g.poly([(cx - 5, y + 5), (cx - 5, y), (cx - 2.5, y + 3), (cx + .5, y - 1), (cx + 3.5, y + 3), (cx + 6, y), (cx + 6, y + 5)], 'G')
        g.set(cx, y + 2, 'F')
    elif acc == "bow":
        y = max(1, top - 2); x = cx + 5
        g.poly([(x - 4, y - 2), (x, y + 1), (x - 4, y + 4)], 'F'); g.poly([(x + 4, y - 2), (x, y + 1), (x + 4, y + 4)], 'F'); g.rect(x - 1, y, x + 1, y + 2, 'F')
    elif acc == "party hat":
        y = max(0, top - 9)
        g.poly([(cx - 4, y + 9), (cx + .5, y), (cx + 5, y + 9)], 'A'); g.line([(cx - 2, y + 6), (cx + 3, y + 4)], 'W'); g.ell(cx + .5, y, 1.3, 1.3, 'G')
    elif acc == "sunglasses" and p.face:
        L, R = cx - p.gap - 1, cx + p.gap + 1
        g.rect(L - 2, p.cy - 1, L + 2, int(p.cy) + 2, 'K'); g.rect(R - 1, p.cy - 1, R + 3, int(p.cy) + 2, 'K')
        g.rect(L + 3, int(p.cy), R - 2, int(p.cy), 'K'); g.set(L - 1, int(p.cy) - 1, 'W'); g.set(R, int(p.cy) - 1, 'W')
    elif acc == "headphones" and p.face:
        y = int(p.cy)
        g.line([(cx - p.half - 2, y), (cx - p.half, top - 1), (cx + p.half + 1, top - 1), (cx + p.half + 3, y)], 'K', 2)
        g.rect(cx - p.half - 3, y - 2, cx - p.half, y + 3, 'A'); g.rect(cx + p.half + 1, y - 2, cx + p.half + 4, y + 3, 'A')
    elif acc == "halo":
        y = max(1, top - 4)
        g.ell(cx + .5, y, 6, 2, 'G'); g.ell(cx + .5, y, 3.5, .8, '.')
    elif acc == "flower":
        x, y = cx - 6, max(2, top - 1)
        for dx, dy in ((0, -2), (2, 0), (0, 2), (-2, 0)): g.ell(x + dx, y + dy, 1.4, 1.4, 'W')
        g.set(x, y, 'G')
    elif acc == "horns":
        y = max(1, top - 3)
        g.poly([(cx - 7, y + 4), (cx - 6, y - 1), (cx - 3, y + 4)], 'F'); g.poly([(cx + 4, y + 4), (cx + 7, y - 1), (cx + 8, y + 4)], 'F')
    elif acc == "hearts":
        for hx, hy in ((2, 3), (27, 6), (28, 24)):
            g.pts([(hx, hy), (hx + 2, hy), (hx - 0, hy + 1), (hx + 1, hy + 1), (hx + 2, hy + 1), (hx + 1, hy + 2)], 'F')
            g.set(hx + 1, hy + 1, 'F')

# ---------- finishing: shade, outline, colors ----------
def finish(g, main, accent):
    src = g.g
    out = [r[:] for r in src]
    for y in range(N):
        for x in range(N):
            ch = src[y][x]
            if ch in 'MAGL':
                nxt = lambda xx, yy: g.get(xx, yy)
                if nxt(x + 1, y) == '.' or nxt(x, y + 1) == '.' or nxt(x + 1, y + 1) == '.':
                    out[y][x] = ch.lower()
    g.g = out
    out = [r[:] for r in g.g]
    for y in range(N):
        for x in range(N):
            if g.g[y][x] == '.' and any(g.get(x + dx, y + dy) != '.' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = 'K'
    g.g = out
    blush = "hot pink" if main in ("pink", "red", "hot pink") else "pink"
    leaf = "mint" if main == "green" else "green"
    gold = "orange" if main == "yellow" else "yellow"
    fixed = "hot pink" if main in ("red",) else "red"
    tear = "white" if main == "blue" else "blue"
    cmap = {'.': 0, 'K': OUTLINE, 'E': OUTLINE, 'W': idx("white"), 'w': idx("white", True),
            'M': idx(main), 'm': idx(main, True), 'D': idx(main, True),
            'A': idx(accent), 'a': idx(accent, True), 'B': idx(blush), 'G': idx(gold), 'g': idx(gold, True),
            'L': idx(leaf), 'l': idx(leaf, True), 'F': idx(fixed), 'T': idx(tear)}
    return [[cmap[ch] for ch in row] for row in g.g]

ACCENT_FOR = {"pink": "white", "hot pink": "pink", "red": "pink", "orange": "cream", "yellow": "orange", "green": "pink",
              "mint": "lavender", "blue": "white", "purple": "lavender", "lavender": "pink", "brown": "cream",
              "grey": "pink", "black": "white", "cream": "pink", "white": "pink"}

def draw(subject, main, expr="happy", acc="none", accent=None, flip=False):
    g = Grid()
    pose = SUBJECTS[subject][0](g)
    face(g, pose, expr)
    accessory(g, pose, acc)
    if flip:
        g.g = [r[::-1] for r in g.g]
    return finish(g, main, accent or ACCENT_FOR[main])

def to_image(grid, scale=1, bg=None):
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0) if bg is None else bg)
    px = im.load()
    for y in range(N):
        for x in range(N):
            c = PALETTE[grid[y][x]]
            if c is not None: px[x, y] = ((c >> 16) & 255, (c >> 8) & 255, c & 255, 255)
    return im.resize((N * scale, N * scale), Image.NEAREST) if scale > 1 else im
