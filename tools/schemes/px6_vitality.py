"""元气清晨 family — eight interactive pixel schemes (schema rainy75-px/2).

Bright, optimistic morning scenes for the Rainy75 V2 320x172 IPS screen.  Every
scheme is a flat background plus 2-5 sticker rectangles with four mood frames
(calm / caps / react / sleepy), typing particles tied to the scene and an
optional breathing pulse.  Run:

    .venv/Scripts/python.exe tools/schemes/px6_vitality.py
    .venv/Scripts/python.exe tools/schemes/px6_vitality.py px6-sunrise   # subset
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-sunrise' \
        --dir build/design-gallery

Sticker rectangles are sized so their mask bytes stay inside the firmware
budget (decoded <= 2560 B, encoded <= 1350 B).  No hardware access.
SPDX-License-Identifier: MIT.
"""
import math
import random
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

FAMILY = '元气清晨'
AUTHOR = '原创像素图形，由 tools/schemes/px6_vitality.py 程序绘制'
W, H_ = PS.SIZE[0], PS.SIZE[1]
CLOUD = ('..####..', '.######.', '########', '########', '.######.')


# --------------------------------------------------------------------------- draw
def hx(c):
    return PS.hexrgb(c)


def drect(d, x, y, w, h, colour):
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=hx(colour))


def beam(d, pts, colour):
    d.polygon([tuple(p) for p in pts], fill=hx(colour))


def reserve(im, specs):
    """Paint every sticker rectangle flat, exactly the background the firmware repaints."""
    d = ImageDraw.Draw(im)
    for s in specs:
        d.rectangle((s['x'], s['y'], s['x'] + s['w'] - 1, s['y'] + s['h'] - 1),
                    fill=hx(s['bg']))


def finish(im, specs):
    """Assert every sticker rectangle is already one flat colour, then flatten it.

    Catching this before ``reserve`` matters: a rectangle that accidentally sits on
    top of background art would erase that art on every frame, leaving a hole.
    """
    for s in specs:
        crop = im.crop((s['x'], s['y'], s['x'] + s['w'], s['y'] + s['h']))
        colours = crop.getcolors(1 << 20)
        if not colours or len(colours) != 1:
            raise AssertionError('%s rect is not flat in background: %r'
                                 % (s['name'], colours))
        if colours[0][1] != hx(s['bg']):
            raise AssertionError('%s flat colour %r != declared bg %s'
                                 % (s['name'], colours[0][1], s['bg']))
    reserve(im, specs)
    return im



def pix_disc(d, cx, cy, r, colour):
    c = hx(colour)
    for dy in range(-r, r + 1):
        half = int((r * r - dy * dy) ** 0.5)
        d.rectangle((cx - half, cy + dy, cx + half, cy + dy), fill=c)


def pix_ring(d, cx, cy, r, colour):
    c = hx(colour)
    for dy in range(-r, r + 1):
        half = int((r * r - dy * dy) ** 0.5)
        d.point((cx - half, cy + dy), fill=c)
        d.point((cx + half, cy + dy), fill=c)
    for dx in range(-r, r + 1):
        half = int((r * r - dx * dx) ** 0.5)
        d.point((cx + dx, cy - half), fill=c)
        d.point((cx + dx, cy + half), fill=c)


def sun_rays(d, cx, cy, r0, r1, count, colour, phase=0.0):
    c = hx(colour)
    for k in range(count):
        a = phase + k * math.tau / count
        x0, y0 = cx + math.cos(a) * r0, cy + math.sin(a) * r0
        x1, y1 = cx + math.cos(a) * r1, cy + math.sin(a) * r1
        d.line((round(x0), round(y0), round(x1), round(y1)), fill=c)


def sparkle(d, x, y, r, colour):
    c = hx(colour)
    for i in range(1, r + 1):
        for px, py in ((x + i, y), (x - i, y), (x, y + i), (x, y - i)):
            if 0 <= px < W and 0 <= py < H_:
                d.point((px, py), fill=c)
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        d.point((x + dx * r, y + dy * r), fill=c)


def cloud_puff(d, x, y, s, colour):
    c = hx(colour)
    for ry, row in enumerate(CLOUD):
        for rx, ch in enumerate(row):
            if ch == '#':
                d.rectangle((x + rx * s, y + ry * s,
                             x + rx * s + s - 1, y + ry * s + s - 1), fill=c)


def bird(d, x, y, colour, s=1, droop=False):
    c = hx(colour)
    rows = ((0, 2, 4), (1, 3)) if droop else ((1, 3), (0, 2, 4))
    for ry, cols in enumerate(rows):
        for cx in cols:
            d.rectangle((x + cx * s, y + ry * s,
                         x + cx * s + s - 1, y + ry * s + s - 1), fill=c)


def grass_tuft(d, x, base, height, colour):
    c = hx(colour)
    d.line((x, base, x, base - height), fill=c)
    d.line((x, base, x - 3, base - height + 2), fill=c)
    d.line((x, base, x + 3, base - height + 3), fill=c)


def sky_bands(im, stops):
    """Flat horizontal sky bands with a one-row dithered seam (pixel-art dawn)."""
    d = ImageDraw.Draw(im)
    for i, (y0, colour) in enumerate(stops):
        y1 = stops[i + 1][0] if i + 1 < len(stops) else im.height
        d.rectangle((0, y0, im.width - 1, y1 - 1), fill=hx(colour))
    for i in range(1, len(stops)):
        y = stops[i][0]
        ca, cb = hx(stops[i - 1][1]), hx(stops[i][1])
        for x in range(0, im.width):
            d.point((x, y - 1), fill=ca if (x + y) % 2 == 0 else cb)


# ------------------------------------------------------------------- grid helpers
def gcloud(g, x, y, s):
    for ry, row in enumerate(CLOUD):
        for rx, ch in enumerate(row):
            if ch == '#':
                g.rect(x + rx * s, y + ry * s, x + rx * s + s - 1, y + ry * s + s - 1)


def gsparkle(g, x, y, r=1):
    for i in range(1, r + 1):
        g.set(x + i, y)
        g.set(x - i, y)
        g.set(x, y + i)
        g.set(x, y - i)
    g.set(x, y)


def gz(g, x, y):
    for dx, row in enumerate(('###', '..#', '.#.', '###')):
        for dy, ch in enumerate(row):
            if ch == '#':
                g.set(x + dy, y + dx)


def gnote(g, x, y):
    g.rect(x, y + 6, x + 3, y + 9)
    g.rect(x + 3, y, x + 4, y + 8)
    g.rect(x + 4, y, x + 6, y + 2)


def gheart(g, x, y):
    for dy, row in enumerate(('.xx.xx.', 'xxxxxxx', 'xxxxxxx', '.xxxxx.', '..xxx..', '...x...')):
        for dx, ch in enumerate(row):
            if ch == 'x':
                g.set(x + dx, y + dy)


def gdrop(g, x, y, h=7):
    for i in range(h):
        w = 0 if i < 2 else (1 if i < h - 1 else 0)
        g.hline(x - w, x + w, y + i)


# ---------------------------------------------------------------------- 1 sunrise
def sunrise_face(kind):
    g = Grid(28, 14)
    if kind == 'calm':
        for ex in (4, 17):
            g.hline(ex, ex + 3, 5)
            g.set(ex + 1, 4)
            g.set(ex + 2, 4)
        g.hline(9, 18, 9)
        g.set(8, 8)
        g.set(19, 8)
        g.hline(11, 16, 10)
        g.set(13, 7)
        g.set(5, 9)
        g.set(22, 9)
    elif kind == 'caps':
        g.rect(3, 3, 9, 5)
        g.rect(16, 3, 22, 5)
        g.hline(10, 15, 4)
        g.hline(9, 18, 9)
        g.set(8, 8)
        g.set(19, 8)
        g.set(13, 7)
    elif kind == 'react':
        g.rect(4, 3, 8, 6)
        g.rect(16, 3, 20, 6)
        gsparkle(g, 1, 1)
        gsparkle(g, 26, 1)
        g.hline(9, 18, 9)
        g.set(8, 8)
        g.set(19, 8)
        g.hline(11, 16, 10)
        g.hline(12, 15, 11)
        g.set(5, 9)
        g.set(22, 9)
    else:
        g.hline(4, 7, 5)
        g.set(7, 6)
        g.hline(17, 20, 5)
        g.set(17, 6)
        g.hline(11, 16, 9)
        g.set(13, 10)
        gz(g, 21, 1)
    return g


def sunrise_cloud(kind):
    g = Grid(52, 16)
    if kind == 'calm':
        gcloud(g, 8, 4, 2)
        gcloud(g, 28, 6, 2)
    elif kind == 'caps':
        gcloud(g, 4, 3, 2)
        gcloud(g, 24, 2, 2)
        gcloud(g, 42, 8, 1)
    elif kind == 'react':
        gcloud(g, 14, 3, 2)
        gcloud(g, 32, 6, 2)
        for i in range(4):
            g.hline(0, 8 - i * 2, 5 + i * 2)
        gsparkle(g, 47, 3)
    else:
        gcloud(g, 26, 9, 1)
        gz(g, 42, 3)
        gz(g, 46, 7)
    return g


def sunrise_sea(kind):
    g = Grid(60, 18)
    cx = 30
    if kind == 'calm':
        for y, w in ((3, 2), (6, 1), (9, 3), (12, 1), (15, 2)):
            g.hline(cx - w, cx + w, y)
    elif kind == 'caps':
        for y, w in ((2, 3), (4, 1), (6, 2), (8, 4), (10, 1), (12, 3), (14, 2), (16, 4)):
            g.hline(cx - w, cx + w, y)
        g.set(cx - 10, 8)
        g.set(cx + 11, 5)
    elif kind == 'react':
        for y, w in ((1, 4), (3, 2), (5, 5), (7, 3), (9, 6), (11, 2), (13, 4), (15, 3),
                     (16, 5)):
            g.hline(cx - w, cx + w, y)
        gsparkle(g, cx - 13, 4)
        gsparkle(g, cx + 13, 11)
        gsparkle(g, cx - 3, 8, 2)
    else:
        for y, w in ((7, 1), (10, 2), (13, 1), (16, 1)):
            g.hline(cx - w, cx + w, y)
    return g


def gbird(g, x, y, s=2, droop=False):
    rows = ((0, 2, 4), (1, 3)) if droop else ((1, 3), (0, 2, 4))
    for ry, cols in enumerate(rows):
        for cx in cols:
            g.rect(x + cx * s, y + ry * s, x + cx * s + s - 1, y + ry * s + s - 1)


def sunrise_birds(kind):
    g = Grid(30, 12)
    if kind == 'calm':
        gbird(g, 1, 1)
        gbird(g, 16, 6)
    elif kind == 'caps':
        gbird(g, 1, 1)
        gbird(g, 12, 6)
        gbird(g, 19, 0, 1)
    elif kind == 'react':
        gbird(g, 0, 3)
        gbird(g, 17, 0)
        g.hline(12, 16, 7)
        gsparkle(g, 22, 9)
    else:
        gbird(g, 14, 6, 2, droop=True)
    return g


def build_sunrise():
    im = Image.new('RGB', PS.SIZE, hx('#ff8f74'))
    sky_bands(im, [(0, '#ff8f74'), (40, '#ffb083'), (78, '#ffd0a0'), (104, '#ffe8c8')])
    d = ImageDraw.Draw(im)
    for r, col in ((46, '#ffcf9a'), (42, '#ffd9a8')):
        pix_ring(d, 160, 92, r, col)
    sun_rays(d, 160, 92, 33, 44, 16, '#ffd2a0', 0.12)
    pix_disc(d, 160, 92, 30, '#ffe6a6')
    pix_disc(d, 160, 92, 20, '#fff7dc')
    for bx, by in ((60, 52), (76, 46), (214, 56), (98, 34)):
        bird(d, bx, by, '#c96a58')
    # hills left / right, sea in front of them
    d.ellipse((-40, 80, 128, 162), fill=hx('#6b4f7a'))
    d.ellipse((-34, 82, 112, 140), fill=hx('#8a6b9e'))
    d.ellipse((206, 84, 366, 160), fill=hx('#5d4670'))
    d.ellipse((216, 88, 340, 140), fill=hx('#7a5f8e'))
    d.rectangle((0, 112, W - 1, H_ - 1), fill=hx('#5b90bd'))
    d.rectangle((0, 112, W - 1, 113), fill=hx('#ffe9c6'))
    rng = random.Random(20261115)
    for y in (118, 126, 134, 142, 150, 158, 166):
        x = rng.randrange(0, 18)
        while x < W - 4:
            ln = rng.randint(3, 7)
            d.line((x, y, x + ln, y), fill=hx('#79aed4'))
            x += ln + rng.randint(9, 20)
    for y in range(120, 172, 7):                       # sun path on the water
        w = 9 - abs(y - 140) // 8
        x0 = 160 - w + rng.randint(-2, 2)
        d.line((x0, y, x0 + 2 * w, y), fill=hx('#ffd98a'))
    # foreground headlands
    beam(d, [(0, 172), (0, 148), (14, 144), (30, 150), (46, 160), (58, 172)], '#4a3559')
    d.line((0, 148, 14, 144), fill=hx('#6b4f7a'))
    d.line((14, 144, 30, 150), fill=hx('#6b4f7a'))
    beam(d, [(238, 172), (252, 156), (272, 150), (296, 146), (320, 142), (320, 172)],
         '#3f2e50')
    d.line((252, 156, 272, 150), fill=hx('#5d4670'))
    d.line((272, 150, 296, 146), fill=hx('#5d4670'))
    # tiny sailboat
    beam(d, [(242, 130), (262, 130), (258, 134), (246, 134)], '#3a2f52')
    d.line((252, 121, 252, 130), fill=hx('#3a2f52'))
    beam(d, [(253, 121), (253, 129), (261, 128)], '#fff4e6')
    for sx, sy in ((30, 162), (214, 168), (286, 158), (124, 166)):
        d.point((sx, sy), fill=hx('#fff4e6'))

    specs = [
        dict(name='太阳表情', x=146, y=86, w=28, h=14, bg='#fff7dc', fg='#b0522e',
             masks=[sunrise_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='晨云', x=214, y=44, w=52, h=16, bg='#ffb083', fg='#fff4e6',
             masks=[sunrise_cloud(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='海面晨光', x=130, y=132, w=60, h=18, bg='#5b90bd', fg='#ffd98a',
             masks=[sunrise_sea(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='早起的鸟', x=24, y=44, w=30, h=12, bg='#ffb083', fg='#5a3440',
             masks=[sunrise_birds(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    reserve(im, specs)
    s = PS.Scheme(
        'px6-sunrise', '日出',
        dict(family=FAMILY, tags=['清晨', '日出', '希望'],
             story='天刚亮，风还是凉的，太阳却已经在认真上班。海面亮起来的那一小段路，'
                   '是它每天给你的第一句早安。'),
        '清晨的海平线上，太阳从两座小山之间一点点升起来，海面把金色光铺成一条路。'
        '每次敲键，太阳会溅起几粒暖金色晨光粒子；敲得投入时它睁大眼睛笑开，'
        '久不打字就眯起眼睛打盹。',
        ['#ff8f74', '#ffb083', '#ffd0a0', '#ffe6a6', '#5b90bd', '#fff7dc'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('spark', trigger='key', spawn=(104, 100, 112, 14), count=7, size=2,
                 colors=['#ffd98a', '#fff7dc', '#ffb083'], vx=(-110, 110),
                 vy=(-120, -40), gravity=120, life_ms=1100, edge='die', shape='plus')
    s.set_pulse('太阳表情', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=24000)
    s.statusInk = '#5a2c33'
    return s


# -------------------------------------------------------------------- 2 breakfast
def breakfast_face(kind):
    g = Grid(26, 14)
    if kind == 'calm':
        for ex in (7, 16):
            g.set(ex, 5)
            g.set(ex + 1, 4)
            g.set(ex + 2, 5)
        g.hline(10, 17, 9)
        g.set(9, 8)
        g.set(18, 8)
        g.set(5, 9)
        g.set(21, 9)
    elif kind == 'caps':
        g.rect(6, 4, 9, 6)
        g.rect(16, 4, 19, 6)
        g.set(5, 3)
        g.set(20, 3)
        g.ring(13, 9, 2)
        g.set(12, 11)
    elif kind == 'react':
        gsparkle(g, 7, 5)
        gsparkle(g, 18, 5)
        g.hline(9, 18, 9)
        g.set(8, 8)
        g.set(19, 8)
        g.set(12, 10)
        g.set(13, 10)
        g.set(14, 10)
        g.set(3, 2)
        g.set(23, 2)
    else:
        g.hline(6, 9, 5)
        g.set(9, 6)
        g.hline(15, 18, 5)
        g.set(15, 6)
        g.hline(11, 15, 9)
        g.set(13, 10)
    return g


def breakfast_egg(kind):
    g = Grid(14, 10)
    if kind == 'calm':
        for ex in (3, 9):
            g.set(ex, 4)
            g.set(ex + 1, 3)
            g.set(ex + 2, 4)
        g.hline(5, 8, 7)
        g.set(4, 6)
        g.set(9, 6)
    elif kind == 'caps':
        g.rect(2, 3, 4, 5)
        g.rect(9, 3, 11, 5)
        g.hline(6, 8, 7)
        g.set(5, 6)
        g.set(9, 6)
    elif kind == 'react':
        gsparkle(g, 3, 4)
        gsparkle(g, 10, 4)
        g.hline(5, 9, 7)
        g.set(4, 6)
        g.set(10, 6)
        g.set(7, 8)
    else:
        g.hline(2, 4, 4)
        g.hline(9, 11, 4)
        g.hline(6, 8, 7)
        g.set(7, 6)
    return g


def breakfast_milk(kind):
    g = Grid(14, 16)
    if kind == 'calm':
        for ex in (4, 9):
            g.set(ex, 6)
            g.set(ex + 1, 5)
            g.set(ex + 2, 6)
        g.hline(5, 9, 10)
        g.set(4, 9)
        g.set(10, 9)
    elif kind == 'caps':
        g.rect(3, 5, 5, 7)
        g.rect(9, 5, 11, 7)
        g.ring(7, 10, 2)
    elif kind == 'react':
        gsparkle(g, 4, 6)
        gsparkle(g, 10, 6)
        g.hline(5, 9, 10)
        g.set(4, 9)
        g.set(10, 9)
        g.set(7, 11)
        g.set(7, 13)
    else:
        g.hline(3, 5, 6)
        g.set(5, 7)
        g.hline(9, 11, 6)
        g.hline(5, 9, 10)
        g.set(6, 11)
    return g


def steam_wave(g, x, y, h):
    for i in range(h):
        g.set(x + (1 if (i // 3) % 2 else 0), y + i)


def breakfast_steam(kind):
    g = Grid(24, 30)
    if kind == 'calm':
        for x in (7, 15):
            steam_wave(g, x, 8, 20)
    elif kind == 'caps':
        for x in (5, 12, 19):
            steam_wave(g, x, 4, 24)
    elif kind == 'react':
        for x in (4, 11, 18):
            steam_wave(g, x, 6, 20)
        gheart(g, 8, 2)
        gsparkle(g, 17, 3)
    else:
        steam_wave(g, 12, 16, 12)
        g.set(10, 18)
        g.set(14, 21)
    return g


def breakfast_light(kind):
    g = Grid(66, 14)
    if kind == 'calm':
        g.hline(14, 49, 4)
        g.hline(9, 55, 5)
        g.hline(6, 59, 6)
        g.hline(4, 61, 7)
        g.hline(6, 59, 8)
        g.hline(10, 54, 9)
        for x, y in ((20, 5), (46, 5), (33, 8)):
            g.set(x, y)
    elif kind == 'caps':
        g.hline(10, 55, 3)
        g.hline(5, 60, 4)
        g.hline(2, 63, 5)
        g.hline(1, 64, 6)
        g.hline(2, 63, 7)
        g.hline(5, 60, 8)
        g.hline(10, 55, 9)
        gsparkle(g, 13, 6)
        gsparkle(g, 52, 6)
    elif kind == 'react':
        g.hline(2, 63, 6)
        g.hline(0, 65, 7)
        g.hline(1, 64, 8)
        for x in range(4, 64, 7):
            g.set(x, 4)
            g.set(x + 2, 5)
            g.set(x, 10)
        gsparkle(g, 9, 7)
        gsparkle(g, 56, 6)
        gsparkle(g, 33, 9)
    else:
        g.hline(20, 45, 8)
        g.hline(24, 41, 9)
        g.set(31, 7)
    return g


def build_breakfast():
    im = Image.new('RGB', PS.SIZE, hx('#f6dcb8'))
    d = ImageDraw.Draw(im)
    # kitchen window: morning sun, green garden, curtains
    d.rectangle((10, 4, 114, 94), fill=hx('#fff6e8'))
    d.rectangle((16, 10, 108, 88), fill=hx('#bfe4ff'))
    pix_disc(d, 40, 40, 13, '#ffe28a')
    pix_ring(d, 40, 40, 19, '#ffe9b8')
    sun_rays(d, 40, 40, 21, 27, 8, '#ffe9b8', 0.2)
    beam(d, [(16, 66), (16, 88), (108, 88), (108, 74)], '#a8d98a')
    d.rectangle((58, 10, 62, 88), fill=hx('#fff6e8'))
    d.rectangle((16, 44, 108, 48), fill=hx('#fff6e8'))
    d.rectangle((20, 12, 25, 42), fill=hx('#ffd3b0'))
    d.rectangle((101, 12, 106, 42), fill=hx('#ffd3b0'))
    d.rectangle((6, 88, 118, 96), fill=hx('#f0dcc0'))
    # wall shelf with little breakfast jars
    d.rectangle((232, 58, 316, 63), fill=hx('#e0b98a'))
    d.rectangle((232, 63, 316, 66), fill=hx('#c9986a'))
    for bx, bw, col in ((238, 12, '#f2b0c0'), (256, 10, '#ffd27a'), (272, 16, '#fff3d6'),
                        (294, 14, '#ffb3a0')):
        d.rectangle((bx, 44, bx + bw - 1, 57), fill=hx(col))
        d.rectangle((bx - 1, 42, bx + bw, 45), fill=hx('#f7f0e2'))
        d.point((bx + 2, 48), fill=hx('#fffaf0'))
    # table and the long morning light beam
    d.rectangle((0, 97, W - 1, H_ - 1), fill=hx('#d99a5c'))
    d.rectangle((0, 97, W - 1, 100), fill=hx('#eab27a'))
    beam(d, [(20, 94), (104, 94), (186, 172), (58, 172)], '#e8ad72')
    beam(d, [(34, 97), (90, 97), (152, 172), (82, 172)], '#efb97f')
    # plate, toast hero
    d.ellipse((24, 116, 150, 166), fill=hx('#d8a06a'))
    d.ellipse((26, 114, 148, 162), fill=hx('#f4efe6'))
    d.ellipse((33, 120, 141, 156), fill=hx('#fffaf0'))
    d.ellipse((44, 140, 92, 156), fill=hx('#bf7c45'))
    d.ellipse((38, 96, 68, 116), fill=hx('#c9793a'))
    d.ellipse((66, 96, 96, 116), fill=hx('#c9793a'))
    d.rectangle((40, 106, 94, 148), fill=hx('#c9793a'))
    d.ellipse((40, 138, 94, 152), fill=hx('#c9793a'))
    d.ellipse((46, 102, 66, 118), fill=hx('#f7e0b0'))
    d.ellipse((64, 102, 84, 118), fill=hx('#f7e0b0'))
    d.rectangle((46, 110, 84, 143), fill=hx('#f7e0b0'))
    d.ellipse((46, 134, 84, 146), fill=hx('#f7e0b0'))
    d.rectangle((48, 112, 62, 117), fill=hx('#ffd94a'))
    d.rectangle((50, 113, 58, 114), fill=hx('#ffe98a'))
    # fried egg
    d.ellipse((104, 120, 146, 158), fill=hx('#f0e6d6'))
    d.ellipse((100, 118, 142, 154), fill=hx('#fffaf0'))
    pix_disc(d, 122, 134, 13, '#ffb830')
    d.ellipse((112, 122, 120, 128), fill=hx('#ffd27a'))
    # milk glass with a straw
    d.rectangle((166, 100, 196, 150), fill=hx('#dceef7'))
    d.rectangle((169, 108, 193, 148), fill=hx('#fff6e2'))
    d.rectangle((167, 102, 195, 106), fill=hx('#fffaf0'))
    d.line((170, 108, 170, 147), fill=hx('#fffaf0'))
    d.line((196, 103, 203, 88), fill=hx('#ff9f9f'))
    d.line((198, 104, 205, 89), fill=hx('#ff9f9f'))
    # jam jar
    d.rectangle((214, 116, 240, 150), fill=hx('#e0576f'))
    d.rectangle((212, 110, 242, 117), fill=hx('#f2f2f2'))
    d.rectangle((218, 126, 236, 142), fill=hx('#fff3d6'))
    d.rectangle((224, 130, 230, 135), fill=hx('#e0576f'))
    d.line((216, 120, 216, 148), fill=hx('#f08aa0'))
    # napkin, fork, crumbs
    d.rectangle((150, 152, 176, 164), fill=hx('#fff3d6'))
    d.rectangle((14, 126, 21, 156), fill=hx('#d9cbb2'))
    for fx in (15, 18, 21):
        d.line((fx, 126, fx, 136), fill=hx('#c0b197'))
    rng = random.Random(41)
    for _ in range(14):
        x, y = rng.randrange(28, 148), rng.randrange(154, 170)
        d.point((x, y), fill=hx('#c9884a'))
    for _ in range(6):
        x, y = rng.randrange(180, 236), rng.randrange(154, 166)
        d.point((x, y), fill=hx('#c9884a'))

    specs = [
        dict(name='吐司表情', x=53, y=118, w=26, h=14, bg='#f7e0b0', fg='#8a4a22',
             masks=[breakfast_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='煎蛋表情', x=115, y=129, w=14, h=10, bg='#ffb830', fg='#a85a12',
             masks=[breakfast_egg(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='牛奶杯', x=172, y=114, w=14, h=16, bg='#fff6e2', fg='#5f8fa8',
             masks=[breakfast_milk(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='热气', x=176, y=58, w=24, h=30, bg='#f6dcb8', fg='#fff7ea',
             masks=[breakfast_steam(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='晨光', x=248, y=152, w=66, h=14, bg='#d99a5c', fg='#ffe4a8',
             masks=[breakfast_light(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-breakfast', '早餐',
        dict(family=FAMILY, tags=['清晨', '早餐', '治愈'],
             story='刚烤好的吐司还带着热气，煎蛋的蛋黄亮得像小太阳。晨光落在木桌上，'
                   '一天的第一口甜，从有人认真准备早餐开始。'),
        '木桌上摆着吐司、流心煎蛋和一杯热牛奶，晨光从厨房窗子斜斜照进来。'
        '每敲一键，桌面会冒出暖金色的早餐星光；敲得投入时吐司和煎蛋一起笑开，'
        '久不打字它们就慢慢犯困，热气也变小了。',
        ['#f6dcb8', '#d99a5c', '#c9793a', '#f7e0b0', '#ffb830', '#fff6e2'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('spark', trigger='key', spawn=(60, 98, 120, 16), count=7, size=2,
                 colors=['#ffd27a', '#fff3c4', '#ffb830'], vx=(-90, 90),
                 vy=(-140, -50), gravity=150, life_ms=1200, edge='die', shape='plus')
    s.set_pulse('晨光', period_ms=2600, minimum=160)
    s.set_reaction(reactHoldMs=950, sleepyAfterMs=25000)
    s.statusInk = '#7a4a2a'
    return s


# ------------------------------------------------------------------- 3 sneaker
def sneaker_face(kind):
    g = Grid(20, 10)
    if kind == 'calm':
        for ex in (3, 12):
            g.hline(ex, ex + 2, 5)
            g.set(ex + 1, 4)
        g.hline(7, 12, 8)
        g.set(6, 7)
        g.set(13, 7)
        g.set(2, 7)
        g.set(17, 7)
    elif kind == 'caps':
        g.rect(2, 2, 4, 4)
        g.rect(13, 2, 15, 4)
        g.ring(9, 8, 1)
        g.set(1, 1)
        g.set(18, 1)
    elif kind == 'react':
        gsparkle(g, 4, 4)
        gsparkle(g, 15, 4)
        g.hline(5, 12, 8)
        g.hline(7, 10, 9)
        g.set(4, 7)
        g.set(13, 7)
        gsparkle(g, 1, 1)
        gsparkle(g, 18, 8)
    else:
        g.hline(2, 5, 4)
        g.set(5, 5)
        g.hline(12, 15, 4)
        g.ring(9, 8, 1)
        gz(g, 16, 0)
    return g


def sneaker_laces(kind):
    g = Grid(44, 12)
    if kind == 'calm':
        for i in range(3):
            g.line(3 + i * 12, 2, 13 + i * 12, 9)
            g.line(3 + i * 12, 9, 13 + i * 12, 2)
        g.set(40, 6)
    elif kind == 'caps':
        for i in range(3):
            g.line(3 + i * 12, 1, 13 + i * 12, 8)
            g.line(3 + i * 12, 8, 13 + i * 12, 1)
        g.ring(39, 5, 2)
        g.set(36, 2)
        g.set(42, 2)
    elif kind == 'react':
        for i in range(3):
            g.line(3 + i * 12, 3, 13 + i * 12, 10)
            g.line(3 + i * 12, 10, 13 + i * 12, 3)
        for x, y in ((5, 1), (17, 0), (29, 1), (41, 0)):
            g.set(x, y)
            g.set(x + 1, y)
        gsparkle(g, 37, 8)
    else:
        for i in range(2):
            g.line(4 + i * 14, 4, 14 + i * 14, 10)
            g.line(4 + i * 14, 10, 14 + i * 14, 4)
        g.line(33, 2, 36, 9)
    return g


def sneaker_speed(kind):
    g = Grid(58, 12)
    if kind == 'calm':
        g.hline(8, 22, 3)
        g.hline(18, 34, 7)
    elif kind == 'caps':
        g.hline(6, 22, 2)
        g.hline(14, 34, 6)
        g.hline(26, 42, 9)
    elif kind == 'react':
        g.hline(2, 26, 2)
        g.hline(0, 30, 5)
        g.hline(6, 44, 8)
        g.hline(24, 50, 11)
        gsparkle(g, 52, 4)
        gsparkle(g, 44, 9)
    else:
        g.hline(12, 28, 5)
    return g


def sneaker_dust(kind):
    g = Grid(44, 10)
    if kind == 'calm':
        g.hline(18, 24, 7)
        g.hline(16, 26, 8)
    elif kind == 'caps':
        g.hline(14, 28, 6)
        g.hline(12, 30, 7)
        g.hline(14, 28, 8)
    elif kind == 'react':
        g.hline(6, 18, 4)
        g.hline(3, 24, 5)
        g.hline(0, 32, 6)
        g.hline(2, 36, 7)
        g.hline(8, 30, 8)
        g.set(20, 2)
        g.set(30, 3)
        g.set(12, 2)
    return g


def build_sneaker():
    im = Image.new('RGB', PS.SIZE, hx('#c8ecff'))
    d = ImageDraw.Draw(im)
    pix_disc(d, 46, 30, 15, '#ffe9a0')
    pix_ring(d, 46, 30, 20, '#ffd9a0')
    sun_rays(d, 46, 30, 22, 29, 10, '#ffd9a0', 0.2)
    cloud_puff(d, 222, 34, 2, '#fffdf6')
    cloud_puff(d, 266, 50, 2, '#fffdf6')
    cloud_puff(d, 298, 64, 1, '#fffdf6')
    # park hills and trees
    d.ellipse((-30, 82, 150, 190), fill=hx('#9fd77f'))
    d.ellipse((90, 88, 250, 190), fill=hx('#b6e38a'))
    d.ellipse((210, 82, 370, 190), fill=hx('#9fd77f'))
    for tx in (46, 268):
        d.rectangle((tx - 3, 96, tx + 3, 128), fill=hx('#8a5a3a'))
        for ox, oy, r in ((-12, -14, 14), (2, -22, 16), (14, -12, 13), (0, -6, 12)):
            pix_disc(d, tx + ox, 96 + oy, r, '#4f9a4a' if (ox + 2) % 3 else '#66b45a')
    # running track
    d.rectangle((0, 116, W - 1, H_ - 1), fill=hx('#d98a5f'))
    d.rectangle((0, 116, W - 1, 119), fill=hx('#eab08a'))
    for x in range(6, W, 28):
        d.rectangle((x, 119, x + 12, 120), fill=hx('#f6e0c8'))
    # three creamy feathers sweep up behind the heel (shoe covers their base)
    feathers = [[(108, 116), (94, 96), (86, 76), (88, 64), (96, 60), (102, 68),
                 (104, 84), (112, 104)],
                [(114, 116), (108, 96), (108, 74), (114, 64), (122, 68),
                 (124, 84), (122, 100)],
                [(118, 116), (122, 98), (128, 84), (136, 84), (134, 98), (128, 110)]]
    for f in feathers:
        d.polygon(f, fill=hx('#fff3d6'))
        d.line([(f[0][0], f[0][1]), (f[1][0], f[1][1]), (f[2][0], f[2][1])],
               fill=hx('#c9a97a'))
    # the sneaker: shadow, gum sole, upper, panels, toe cap, swoosh, contour
    d.ellipse((94, 146, 268, 160), fill=hx('#b8683f'))
    d.polygon([(98, 142), (104, 136), (160, 134), (210, 136), (250, 140), (260, 144),
               (258, 156), (100, 156)], fill=hx('#f0d9b8'))
    d.polygon([(100, 156), (258, 156), (254, 150), (104, 150)], fill=hx('#c9a97e'))
    for tx in range(108, 252, 14):
        d.line((tx, 150, tx + 3, 155), fill=hx('#a8895e'))
    upper = [(98, 142), (102, 116), (110, 102), (124, 96), (140, 98), (150, 104),
             (160, 96), (176, 92), (196, 100), (222, 116), (240, 126), (250, 134),
             (254, 141)]
    d.polygon(upper, fill=hx('#fbfdff'))
    d.polygon([(98, 142), (102, 116), (110, 102), (124, 102), (124, 142)],
              fill=hx('#e4f2fa'))
    d.polygon([(140, 92), (152, 88), (160, 96), (150, 102)], fill=hx('#eef7fb'))
    d.polygon([(224, 132), (251, 137), (245, 121), (226, 117)], fill=hx('#d6ecf6'))
    d.polygon([(118, 140), (152, 132), (190, 126), (206, 132), (156, 142)],
              fill=hx('#4fd0c0'))
    d.line([(102, 116), (110, 102), (124, 96), (140, 98), (150, 104), (160, 96),
            (176, 92), (196, 100), (222, 116), (240, 126), (250, 134), (254, 141)],
           fill=hx('#2a4a5a'), width=2)
    d.line([(98, 142), (102, 116)], fill=hx('#2a4a5a'), width=2)
    d.line([(98, 142), (254, 141)], fill=hx('#2a4a5a'), width=2)
    d.line([(226, 117), (245, 121)], fill=hx('#9fc4d8'))
    d.rectangle((99, 108, 106, 116), fill=hx('#4fd0c0'))
    d.line((124, 104, 124, 142), fill=hx('#c9dbe6'))
    # collar padding (the laces themselves are the sticker)
    d.line([(112, 100), (124, 96), (140, 98)], fill=hx('#fff3d6'), width=3)
    # little grass blades along the track edge
    for gx in (6, 30, 54, 196, 226, 250, 288, 312):
        grass_tuft(d, gx, 116, 8, '#7fbf5a')

    specs = [
        dict(name='鞋跟表情', x=104, y=118, w=20, h=10, bg='#e4f2fa', fg='#2a4a5a',
             masks=[sneaker_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='鞋带', x=140, y=108, w=44, h=12, bg='#fbfdff', fg='#2a4a5a',
             masks=[sneaker_laces(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='速度线', x=18, y=126, w=58, h=12, bg='#d98a5f', fg='#fff0dc',
             masks=[sneaker_speed(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='尘土', x=102, y=161, w=44, h=10, bg='#d98a5f', fg='#ffe9d0',
             masks=[sneaker_dust(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-sneaker', '晨跑',
        dict(family=FAMILY, tags=['清晨', '晨跑', '元气'],
             story='天刚亮，跑道上只有自己的脚步声。鞋带系紧一点，翅膀也精神起来，'
                   '今天的第一公里，风是甜的。'),
        '晨光里的公园跑道，一双系好鞋带、背上小翅膀的球鞋正要出发。每按一键，鞋后'
        '踢起一撮尘土和星点；敲得越起劲鞋带越飞扬、速度线越长，久不碰键盘它就'
        '把鞋带垂下来歇口气。',
        ['#c8ecff', '#9fd77f', '#d98a5f', '#4fd0c0', '#fbfdff', '#ffe9c0'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('spark', trigger='key', spawn=(70, 120, 60, 20), count=8, size=2,
                 colors=['#fff0dc', '#ffe9c0', '#4fd0c0'], vx=(-150, -40),
                 vy=(-30, 30), gravity=90, life_ms=900, edge='die', shape='square')
    s.set_pulse('鞋跟表情', period_ms=1600, minimum=170)
    s.set_reaction(reactHoldMs=780, sleepyAfterMs=19000)
    s.statusInk = '#2a5570'
    return s


# ---------------------------------------------------------------------- 4 soda
def soda_face(kind):
    g = Grid(22, 14)
    if kind == 'calm':
        for ex in (4, 14):
            g.hline(ex, ex + 2, 6)
            g.set(ex + 1, 5)
        g.hline(8, 13, 10)
        g.set(7, 9)
        g.set(14, 9)
        g.set(2, 10)
        g.set(19, 10)
    elif kind == 'caps':
        g.rect(3, 4, 6, 6)
        g.rect(14, 4, 17, 6)
        g.ring(10, 10, 2)
        g.set(2, 3)
        g.set(19, 3)
    elif kind == 'react':
        gsparkle(g, 5, 5)
        gsparkle(g, 16, 5)
        g.hline(7, 14, 9)
        g.hline(9, 12, 10)
        g.set(6, 8)
        g.set(15, 8)
        gsparkle(g, 1, 2)
        gsparkle(g, 20, 11)
    else:
        g.hline(2, 5, 6)
        g.set(5, 7)
        g.hline(14, 17, 6)
        g.set(14, 7)
        g.ring(10, 10, 1)
        gz(g, 18, 1)
    return g


def soda_bubbles(kind):
    g = Grid(18, 20)
    if kind == 'calm':
        for bx, by, r in ((5, 14, 1), (10, 8, 2), (13, 16, 1)):
            g.disc(bx, by, r)
    elif kind == 'caps':
        for bx, by, r in ((4, 15, 1), (8, 10, 1), (12, 6, 2), (14, 16, 1), (9, 17, 1)):
            g.disc(bx, by, r)
    elif kind == 'react':
        for bx, by, r in ((3, 16, 2), (8, 12, 2), (13, 8, 2), (16, 14, 1), (6, 7, 1),
                          (11, 3, 1)):
            g.disc(bx, by, r)
        g.hline(2, 6, 2)
        g.hline(12, 16, 1)
    else:
        g.disc(5, 16, 1)
        g.disc(11, 13, 1)
    return g


def soda_splash(kind):
    g = Grid(44, 14)
    if kind == 'calm':
        gdrop(g, 9, 8, 5)
        gdrop(g, 22, 9, 4)
    elif kind == 'caps':
        gdrop(g, 7, 6, 6)
        gdrop(g, 19, 8, 5)
        gdrop(g, 31, 9, 4)
    elif kind == 'react':
        g.hline(2, 42, 12)
        gdrop(g, 6, 3, 6)
        gdrop(g, 15, 2, 7)
        gdrop(g, 25, 4, 6)
        gdrop(g, 35, 5, 5)
        gsparkle(g, 20, 1)
        gsparkle(g, 40, 3)
    else:
        g.hline(6, 34, 11)
        gdrop(g, 28, 8, 3)
    return g


def soda_lemon(kind):
    g = Grid(30, 30)
    cx = cy = 15

    def wheel(r, seg, phase, thick=2):
        for dy in range(-r - 1, r + 2):
            for dx in range(-r - 1, r + 2):
                dd = (dx * dx + dy * dy) ** 0.5
                if r - thick < dd <= r:
                    g.set(cx + dx, cy + dy)
        for k in range(seg):
            a = phase + k * math.tau / seg
            for rr in range(3, r - 1):
                px = cx + int(round(math.cos(a) * rr))
                py = cy + int(round(math.sin(a) * rr))
                g.set(px, py)
                g.set(px + 1, py)
                g.set(px, py + 1)
        g.disc(cx, cy, 2)

    if kind == 'calm':
        wheel(14, 8, 0.0)
        wheel(10, 8, 0.0, 1)
    elif kind == 'caps':
        wheel(14, 10, 0.2)
        gsparkle(g, 27, 3)
    elif kind == 'react':
        wheel(14, 10, 0.35)
        wheel(9, 10, 0.35, 1)
        gsparkle(g, 3, 4)
        gsparkle(g, 26, 26)
    else:
        wheel(14, 6, 0.5)
        wheel(9, 6, 0.5, 1)
    return g


def build_soda():
    im = Image.new('RGB', PS.SIZE, hx('#ffd7e6'))
    d = ImageDraw.Draw(im)
    # bunting high up, clear of the status corners
    d.line((0, 2, W - 1, 2), fill=hx('#e08aa8'))
    flags = ('#ffd27a', '#9fe8ff', '#fffaf0', '#ffb3a0')
    for i, x in enumerate(range(4, 316, 22)):
        d.polygon([(x, 3), (x + 14, 3), (x + 7, 11)], fill=hx(flags[i % 4]))
    # wall poster
    d.rectangle((244, 44, 296, 88), fill=hx('#fffaf0'))
    d.rectangle((248, 48, 292, 84), fill=hx('#ffe28a'))
    pix_disc(d, 270, 62, 9, '#ffcf7a')
    for wx in range(254, 288, 8):
        d.line((wx, 78, wx + 4, 78), fill=hx('#ffb3a0'))
    # mint table
    d.rectangle((0, 95, W - 1, H_ - 1), fill=hx('#a8ead8'))
    d.rectangle((0, 95, W - 1, 99), fill=hx('#8fd8c4'))
    # soda glass: glass body, bowl bottom, liquid, foam, ice, cherry
    d.rectangle((126, 52, 184, 138), fill=hx('#e8fbff'))
    d.ellipse((126, 126, 184, 150), fill=hx('#e8fbff'))
    d.rectangle((131, 68, 179, 130), fill=hx('#7ad7ff'))
    d.ellipse((131, 118, 179, 138), fill=hx('#7ad7ff'))
    d.rectangle((131, 68, 179, 71), fill=hx('#b8efff'))
    d.rectangle((160, 78, 170, 88), fill=hx('#e6fbff'))
    d.rectangle((134, 112, 144, 122), fill=hx('#e6fbff'))
    for bx, by, r in ((166, 102, 2), (150, 124, 2), (172, 120, 1), (158, 130, 1)):
        pix_disc(d, bx, by, r, '#eafcff')
    d.ellipse((126, 52, 184, 66), outline=hx('#dff7fb'), width=2)
    d.line((126, 60, 126, 134), fill=hx('#dff7fb'))
    d.line((184, 56, 184, 134), fill=hx('#dff7fb'))
    d.ellipse((132, 144, 178, 154), fill=hx('#8fd8c4'))
    pix_disc(d, 156, 60, 5, '#e0486b')
    d.point((154, 58), fill=hx('#f08aa0'))
    d.line((157, 55, 163, 44), fill=hx('#6f9a4a'))
    pix_disc(d, 180, 58, 13, '#ffe066')
    pix_disc(d, 180, 58, 10, '#fff3a0')
    pix_disc(d, 180, 58, 3, '#ffe066')
    for k in range(4):
        a = k * math.tau / 4 + 0.3
        d.line((180 + math.cos(a) * 4, 58 + math.sin(a) * 4,
                180 + math.cos(a) * 9, 58 + math.sin(a) * 9), fill=hx('#ffe066'))
    # striped straw
    d.line((150, 62, 194, 26), fill=hx('#fffaf0'), width=4)
    for t in (0.22, 0.45, 0.68):
        sx = 150 + (194 - 150) * t
        sy = 62 + (26 - 62) * t
        d.line((sx - 2, sy + 2, sx + 2, sy - 2), fill=hx('#ff7f9f'), width=3)
    # puddle shine + a napkin on the table
    d.ellipse((138, 140, 176, 150), fill=hx('#8fd8c4'))
    d.rectangle((196, 148, 220, 160), fill=hx('#fffaf0'))

    specs = [
        dict(name='汽水表情', x=136, y=92, w=22, h=14, bg='#7ad7ff', fg='#2a7a9a',
             masks=[soda_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='气泡', x=142, y=72, w=18, h=20, bg='#7ad7ff', fg='#eafcff',
             masks=[soda_bubbles(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='柠檬片', x=36, y=112, w=30, h=30, bg='#a8ead8', fg='#ffe066',
             masks=[soda_lemon(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='溅出的汽水', x=200, y=118, w=44, h=14, bg='#a8ead8', fg='#eafcff',
             masks=[soda_splash(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-soda', '汽水',
        dict(family=FAMILY, tags=['清晨', '汽水', '清爽'],
             story='早上第一口冰汽水，气泡在杯壁上排队往上升。柠檬片浮在杯口，'
                   '整个早晨都咕嘟咕嘟冒着凉丝丝的甜。'),
        '薄荷色小桌上放着一杯橘子汽水，柠檬片和吸管都透着凉气。每按一键，杯口就涌起'
        '一串亮晶晶的气泡；打字投入时整杯汽水跟着冒泡欢呼，安静下来只剩几颗小气泡慢慢往上飘。',
        ['#ffd7e6', '#a8ead8', '#7ad7ff', '#ffe066', '#eafcff', '#2a7a9a'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('bubble', trigger='key', spawn=(136, 56, 40, 10), count=7, size=3,
                 colors=['#eafcff', '#b8efff', '#fffaf0'], vx=(-8, 8), vy=(-52, -26),
                 gravity=0, life_ms=2200, edge='die', shape='diamond')
    s.set_pulse('柠檬片', period_ms=1800, minimum=160)
    s.set_reaction(reactHoldMs=850, sleepyAfterMs=21000)
    s.statusInk = '#7a2a48'
    return s


# --------------------------------------------------------------------- 5 radio
def radio_face(kind):
    g = Grid(44, 18)
    if kind == 'calm':
        for cx in (10, 33):
            g.ring(cx, 8, 4)
            g.set(cx, 8)
        g.hline(18, 25, 13)
        g.set(17, 12)
        g.set(26, 12)
        for x in range(4, 41, 4):
            g.set(x, 16)
        g.set(4, 12)
        g.set(39, 12)
    elif kind == 'caps':
        for cx in (10, 33):
            g.ring(cx, 8, 5)
            g.rect(cx - 1, 7, cx + 1, 9)
        g.ring(21, 13, 2)
        for x in range(4, 41, 4):
            g.set(x, 16)
        g.set(8, 1)
        g.set(35, 1)
    elif kind == 'react':
        gsparkle(g, 10, 8)
        gsparkle(g, 33, 8)
        g.hline(16, 27, 12)
        g.hline(18, 25, 13)
        g.set(15, 11)
        g.set(28, 11)
        for x in range(4, 41, 4):
            g.set(x, 16)
        gsparkle(g, 4, 2)
        gsparkle(g, 39, 1)
        g.set(21, 3)
    else:
        g.hline(6, 14, 8)
        g.set(13, 9)
        g.hline(29, 37, 8)
        g.set(30, 9)
        g.ring(21, 13, 1)
        gz(g, 38, 1)
        for x in range(8, 37, 8):
            g.set(x, 16)
    return g


def radio_notes(kind):
    g = Grid(24, 28)
    if kind == 'calm':
        gnote(g, 1, 4)
        gnote(g, 13, 14)
    elif kind == 'caps':
        gnote(g, 0, 1)
        gnote(g, 8, 9)
        gnote(g, 16, 3)
    elif kind == 'react':
        gnote(g, 0, 0)
        gnote(g, 7, 8)
        gnote(g, 14, 16)
        gsparkle(g, 21, 3)
        gsparkle(g, 3, 24)
        g.hline(0, 5, 24)
    else:
        gnote(g, 6, 16)
        gz(g, 17, 1)
    return g


def radio_wave(kind):
    g = Grid(22, 22)

    def arc(r):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            g.set(half, 11 + dy)

    if kind == 'calm':
        arc(6)
    elif kind == 'caps':
        arc(6)
        arc(10)
    elif kind == 'react':
        arc(5)
        arc(9)
        arc(13)
        gsparkle(g, 3, 2)
        gsparkle(g, 16, 19)
    else:
        arc(4)
        g.set(2, 5)
    return g


def radio_pool(kind):
    g = Grid(48, 12)
    if kind == 'calm':
        g.hline(14, 33, 3)
        g.hline(10, 37, 4)
        g.hline(7, 40, 5)
        g.hline(6, 41, 6)
        g.hline(7, 40, 7)
        g.hline(11, 36, 8)
    elif kind == 'caps':
        g.hline(10, 37, 2)
        g.hline(5, 42, 3)
        g.hline(2, 45, 4)
        g.hline(1, 46, 5)
        g.hline(1, 46, 6)
        g.hline(2, 45, 7)
        g.hline(5, 42, 8)
        g.hline(10, 37, 9)
        gsparkle(g, 14, 5)
        gsparkle(g, 33, 6)
    elif kind == 'react':
        g.hline(2, 45, 3)
        g.hline(0, 47, 4)
        g.hline(0, 47, 5)
        g.hline(0, 47, 6)
        g.hline(2, 45, 7)
        gsparkle(g, 8, 3)
        gsparkle(g, 40, 7)
        gsparkle(g, 24, 1)
    else:
        g.hline(16, 31, 7)
        g.hline(19, 28, 8)
    return g


def build_radio():
    im = Image.new('RGB', PS.SIZE, hx('#ffeacb'))
    d = ImageDraw.Draw(im)
    # morning window
    d.rectangle((6, 4, 106, 94), fill=hx('#fffaf0'))
    d.rectangle((12, 10, 100, 88), fill=hx('#bfe4ff'))
    pix_disc(d, 34, 36, 11, '#ffe28a')
    pix_ring(d, 34, 36, 16, '#ffe9b8')
    beam(d, [(12, 70), (12, 88), (100, 88), (100, 76)], '#a8d98a')
    d.rectangle((54, 10, 58, 88), fill=hx('#fffaf0'))
    d.rectangle((12, 46, 100, 50), fill=hx('#fffaf0'))
    d.rectangle((16, 12, 21, 44), fill=hx('#ffd3b0'))
    d.rectangle((92, 12, 97, 44), fill=hx('#ffd3b0'))
    d.rectangle((2, 90, 110, 98), fill=hx('#f0d8b4'))
    # wall clock
    d.rectangle((250, 50, 290, 82), fill=hx('#fffaf0'))
    pix_disc(d, 270, 66, 12, '#ffe9c4')
    pix_ring(d, 270, 66, 12, '#8a4a2a')
    d.line((270, 66, 270, 58), fill=hx('#5a3020'))
    d.line((270, 66, 276, 69), fill=hx('#5a3020'))
    # wooden desk
    d.rectangle((0, 103, W - 1, H_ - 1), fill=hx('#c98a52'))
    d.rectangle((0, 103, W - 1, 106), fill=hx('#e0a866'))
    # retro radio body (rounded corners so it reads as a box, not a poster)
    d.rectangle((110, 64, 214, 150), fill=hx('#e07a4a'))
    pix_disc(d, 112, 66, 8, '#ffeacb')
    pix_disc(d, 212, 66, 8, '#ffeacb')
    d.rectangle((112, 62, 212, 150), fill=hx('#e07a4a'))
    pix_disc(d, 112, 148, 8, '#c98a52')
    pix_disc(d, 212, 148, 8, '#c98a52')
    d.rectangle((110, 138, 214, 148), fill=hx('#c9693c'))
    d.line([(112, 62), (212, 62)], fill=hx('#c9693c'), width=2)
    d.rectangle((122, 88, 200, 126), fill=hx('#fff3d6'))
    d.rectangle((124, 128, 160, 150), fill=hx('#a85a32'))
    for gx in range(126, 160, 4):
        d.rectangle((gx, 130, gx + 1, 148), fill=hx('#d98a5a'))
    for kx in (170, 192):
        pix_disc(d, kx, 136, 7, '#8a4a2a')
        pix_disc(d, kx, 136, 2, '#c98a52')
    d.rectangle((116, 150, 128, 156), fill=hx('#8a4a2a'))
    d.rectangle((196, 150, 208, 156), fill=hx('#8a4a2a'))
    d.line((206, 64, 238, 22), fill=hx('#8a4a2a'), width=2)
    pix_disc(d, 238, 21, 3, '#ffcf7a')
    # desk plant
    d.rectangle((292, 118, 318, 150), fill=hx('#c9693c'))
    d.rectangle((290, 114, 320, 120), fill=hx('#e0956f'))
    for lx, ly, r in ((298, 104, 7), (308, 110, 6), (290, 110, 6)):
        pix_disc(d, lx, ly, r, '#5fae3f')

    specs = [
        dict(name='收音机表情', x=130, y=92, w=44, h=18, bg='#fff3d6', fg='#b06a3a',
             masks=[radio_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='音符', x=226, y=52, w=24, h=28, bg='#ffeacb', fg='#e08a4a',
             masks=[radio_notes(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='声波', x=222, y=110, w=22, h=22, bg='#c98a52', fg='#ffb347',
             masks=[radio_wave(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='晨光', x=20, y=142, w=48, h=12, bg='#c98a52', fg='#ffe7b8',
             masks=[radio_pool(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-radio', '电台',
        dict(family=FAMILY, tags=['清晨', '电台', '音乐'],
             story='老收音机被晨光晒得暖暖的，旋钮一拧，喇叭里就飘出橘子味的音符。'
                   '早间的歌不着急，慢慢听就好。'),
        '木头收音机摆在被晨光照亮的桌面上，天线歪着，喇叭里飘出橘色音符。'
        '每敲一个键，它就轻轻放出两三个音符；敲得越投入音符越密，久不打字它就眯起眼'
        '调低音量，只留下窗外的阳光。',
        ['#ffeacb', '#c98a52', '#e07a4a', '#fff3d6', '#ffb347', '#8a4a2a'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('note', trigger='key', spawn=(130, 80, 80, 14), count=6, size=3,
                 colors=['#ffb347', '#ffe0a0', '#ff8f6a'], vx=(-40, 40),
                 vy=(-90, -34), gravity=34, life_ms=2000, edge='die', shape='diamond')
    s.set_pulse('晨光', period_ms=2600, minimum=150)
    s.set_reaction(reactHoldMs=820, sleepyAfterMs=20000)
    s.statusInk = '#7a4a2a'
    return s


# --------------------------------------------------------------------- 6 lemon
def lemon_face(kind):
    g = Grid(30, 18)
    if kind == 'calm':
        for ex in (5, 17):
            g.hline(ex, ex + 3, 8)
            g.set(ex + 1, 7)
            g.set(ex + 2, 7)
        g.hline(11, 19, 13)
        g.set(10, 12)
        g.set(20, 12)
        g.set(3, 12)
        g.set(26, 12)
    elif kind == 'caps':
        g.rect(4, 6, 8, 8)
        g.rect(18, 6, 22, 8)
        g.hline(5, 10, 4)
        g.hline(19, 24, 4)
        g.ring(15, 13, 2)
    elif kind == 'react':
        g.hline(4, 7, 8)
        g.set(6, 7)
        gsparkle(g, 20, 8)
        g.hline(10, 20, 13)
        g.hline(12, 18, 14)
        g.set(9, 12)
        g.set(21, 12)
        gsparkle(g, 1, 3)
        gsparkle(g, 27, 2)
    else:
        g.hline(4, 8, 8)
        g.set(8, 9)
        g.hline(19, 23, 8)
        g.set(19, 9)
        g.ring(15, 13, 1)
        gz(g, 25, 1)
    return g


def lemon_leaf(kind):
    g = Grid(32, 22)

    def leaf(cx, cy, rx, ry):
        for y in range(-ry, ry + 1):
            half = int(rx * (1 - (y / float(ry)) ** 2) ** 0.8)
            g.hline(cx - half, cx + half, cy + y)
        for y in range(-ry + 1, ry):
            g.set(cx, cy + y, '.')

    if kind == 'calm':
        leaf(8, 14, 6, 4)
        leaf(17, 8, 7, 4)
        leaf(25, 14, 5, 3)
        g.line(3, 20, 30, 6)
    elif kind == 'caps':
        leaf(8, 12, 6, 4)
        leaf(17, 6, 7, 4)
        leaf(27, 11, 5, 3)
        g.line(3, 18, 30, 4)
        gsparkle(g, 30, 1)
    elif kind == 'react':
        leaf(7, 16, 7, 4)
        leaf(15, 7, 8, 4)
        leaf(25, 11, 6, 3)
        g.line(2, 20, 30, 5)
        gsparkle(g, 2, 3)
        gsparkle(g, 29, 17)
    else:
        leaf(8, 17, 6, 4)
        leaf(18, 14, 7, 4)
        leaf(27, 17, 5, 3)
        g.line(5, 20, 30, 16)
    return g


def lemon_splash(kind):
    g = Grid(44, 14)
    if kind == 'calm':
        gdrop(g, 10, 8, 5)
        gdrop(g, 26, 9, 4)
    elif kind == 'caps':
        gdrop(g, 8, 6, 6)
        gdrop(g, 21, 8, 5)
        gdrop(g, 34, 9, 4)
    elif kind == 'react':
        g.hline(2, 42, 12)
        gdrop(g, 5, 4, 6)
        gdrop(g, 14, 2, 7)
        gdrop(g, 24, 3, 6)
        gdrop(g, 34, 5, 5)
        gsparkle(g, 19, 1)
        gsparkle(g, 40, 2)
    else:
        g.hline(4, 40, 11)
        g.hline(10, 30, 12)
        gdrop(g, 30, 8, 3)
    return g


def lemon_glass(kind):
    g = Grid(16, 20)
    if kind == 'calm':
        for bx, by, r in ((5, 14, 1), (10, 8, 2)):
            g.disc(bx, by, r)
    elif kind == 'caps':
        for bx, by, r in ((4, 15, 1), (8, 11, 1), (12, 6, 2), (11, 16, 1), (6, 6, 1)):
            g.disc(bx, by, r)
    elif kind == 'react':
        for bx, by, r in ((3, 16, 2), (8, 12, 2), (13, 8, 2), (15, 15, 1), (6, 7, 1)):
            g.disc(bx, by, r)
        g.hline(2, 6, 3)
        g.hline(11, 14, 2)
    else:
        g.disc(5, 16, 1)
        g.disc(11, 14, 1)
    return g


def build_lemon():
    im = Image.new('RGB', PS.SIZE, hx('#fff6d5'))
    d = ImageDraw.Draw(im)
    # window with morning light
    d.rectangle((10, 4, 112, 90), fill=hx('#fffaf0'))
    d.rectangle((16, 10, 106, 84), fill=hx('#cfefff'))
    pix_disc(d, 38, 34, 12, '#ffe28a')
    pix_ring(d, 38, 34, 17, '#ffe9b8')
    beam(d, [(16, 66), (16, 84), (106, 84), (106, 72)], '#a8d98a')
    d.rectangle((58, 10, 62, 84), fill=hx('#fffaf0'))
    d.rectangle((16, 44, 106, 48), fill=hx('#fffaf0'))
    d.rectangle((20, 12, 25, 42), fill=hx('#ffe6b0'))
    d.rectangle((98, 12, 103, 42), fill=hx('#ffe6b0'))
    d.rectangle((6, 86, 116, 94), fill=hx('#f0e0b8'))
    # wall poster with a lemon on it
    d.rectangle((252, 40, 302, 86), fill=hx('#fffaf0'))
    d.rectangle((256, 44, 298, 82), fill=hx('#fff3c4'))
    d.ellipse((264, 54, 290, 74), fill=hx('#ffe45c'))
    d.rectangle((272, 60, 280, 64), fill=hx('#fff3a0'))
    d.line((277, 54, 281, 48), fill=hx('#6f9a3a'))
    # cream counter + sunlit beam
    d.rectangle((0, 97, W - 1, H_ - 1), fill=hx('#f4ead6'))
    d.rectangle((0, 97, W - 1, 100), fill=hx('#e6d8bc'))
    beam(d, [(20, 94), (100, 94), (158, 172), (62, 172)], '#f9e8c4')
    # lemon hero
    d.ellipse((84, 104, 172, 160), fill=hx('#e6c93e'))
    d.ellipse((86, 102, 170, 157), fill=hx('#ffe45c'))
    d.ellipse((92, 108, 112, 126), fill=hx('#fff3a0'))
    d.ellipse((110, 140, 160, 158), fill=hx('#e6c93e'))
    pix_disc(d, 168, 128, 5, '#e6c93e')
    d.line((150, 104, 168, 86), fill=hx('#6f9a3a'), width=2)
    d.ellipse((154, 88, 168, 96), fill=hx('#6fbf4a'))
    d.ellipse((164, 82, 178, 90), fill=hx('#6fbf4a'))
    # little droplets on the peel
    for dx, dy in ((98, 136), (154, 112), (120, 146)):
        d.point((dx, dy), fill=hx('#fff8d0'))
        d.point((dx + 1, dy + 1), fill=hx('#fff8d0'))
    # glass of lemonade: tumbler, liquid, ice, straw, lemon wheel on the rim
    d.rectangle((238, 104, 272, 148), fill=hx('#eaf6fb'))
    d.ellipse((238, 138, 272, 154), fill=hx('#eaf6fb'))
    d.rectangle((241, 112, 269, 140), fill=hx('#ffe98a'))
    d.ellipse((241, 132, 269, 148), fill=hx('#ffe98a'))
    d.rectangle((241, 118, 247, 126), fill=hx('#fff8d0'))
    d.rectangle((242, 132, 248, 140), fill=hx('#fff8d0'))
    d.ellipse((238, 102, 272, 116), outline=hx('#cfe8f2'), width=2)
    d.line((238, 110, 238, 148), fill=hx('#cfe8f2'))
    d.line((272, 110, 272, 148), fill=hx('#cfe8f2'))
    d.line((250, 116, 258, 96), fill=hx('#6fbf4a'), width=2)
    pix_disc(d, 240, 108, 7, '#ffe066')
    pix_disc(d, 240, 108, 4, '#fff3a0')
    # zest curls on the counter
    for zx, zy in ((84, 162), (100, 166), (196, 158), (210, 164)):
        d.line((zx, zy, zx + 3, zy - 2), fill=hx('#e6c93e'))

    specs = [
        dict(name='柠檬表情', x=114, y=122, w=30, h=18, bg='#ffe45c', fg='#8a6a1a',
             masks=[lemon_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='柠檬叶', x=154, y=58, w=32, h=22, bg='#fff6d5', fg='#5fae3f',
             masks=[lemon_leaf(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='柠檬汁', x=176, y=128, w=44, h=14, bg='#f4ead6', fg='#8fdbe8',
             masks=[lemon_splash(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='柠檬水气泡', x=249, y=120, w=16, h=20, bg='#ffe98a', fg='#fffaf0',
             masks=[lemon_glass(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-lemon', '柠檬',
        dict(family=FAMILY, tags=['清晨', '柠檬', '清新'],
             story='清晨切一颗柠檬，果皮上的水珠还没干。酸味一下子把人叫醒，'
                   '连窗外的光都像被柠檬汁洗过一遍。'),
        '奶油色台面上摆着一颗带叶子的新鲜柠檬，旁边是刚倒好的柠檬水。每按一键，'
        '空气里会迸出一小把清亮的柠檬星屑；敲得投入时柠檬挤着眼睛笑，'
        '安静下来它就靠在水杯边打瞌睡。',
        ['#fff6d5', '#f4ead6', '#ffe45c', '#6fbf4a', '#ffe98a', '#8fdbe8'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('spark', trigger='key', spawn=(90, 104, 96, 20), count=8, size=2,
                 colors=['#ffe45c', '#fff3a0', '#8fdbe8'], vx=(-120, 120),
                 vy=(-130, -40), gravity=170, life_ms=1200, edge='bounce', shape='plus')
    s.set_pulse('柠檬表情', period_ms=2200, minimum=170)
    s.set_reaction(reactHoldMs=880, sleepyAfterMs=23000)
    s.statusInk = '#7a6a30'
    return s


# ----------------------------------------------------------------------- 7 bee
def bee_face(kind):
    g = Grid(16, 12)
    if kind == 'calm':
        for ex in (2, 9):
            g.hline(ex, ex + 2, 5)
            g.set(ex + 1, 4)
        g.hline(5, 10, 8)
        g.set(4, 7)
        g.set(11, 7)
    elif kind == 'caps':
        g.rect(2, 3, 4, 5)
        g.rect(10, 3, 12, 5)
        g.ring(7, 9, 1)
        g.set(1, 2)
        g.set(13, 2)
    elif kind == 'react':
        gsparkle(g, 3, 5)
        gsparkle(g, 11, 5)
        g.hline(4, 11, 8)
        g.hline(5, 10, 9)
        gsparkle(g, 1, 1)
        gsparkle(g, 14, 10)
    else:
        g.hline(2, 5, 5)
        g.set(5, 6)
        g.hline(9, 12, 5)
        g.set(9, 6)
        g.ring(7, 9, 1)
    return g


def bee_wing(kind):
    g = Grid(20, 10)
    if kind == 'calm':
        g.line(1, 4, 6, 6)
        g.line(6, 6, 11, 7)
        g.line(11, 7, 15, 6)
        g.line(15, 6, 18, 4)
    elif kind == 'caps':
        g.line(1, 7, 6, 5)
        g.line(6, 5, 11, 3)
        g.line(11, 3, 15, 4)
        g.line(15, 4, 18, 6)
    elif kind == 'react':
        g.line(1, 8, 6, 5)
        g.line(6, 5, 11, 2)
        g.line(11, 2, 15, 3)
        g.line(15, 3, 18, 6)
        g.set(3, 7)
        g.set(9, 3)
        g.set(14, 4)
        gsparkle(g, 18, 1)
    else:
        g.line(2, 5, 7, 8)
        g.line(7, 8, 12, 8)
        g.line(12, 8, 17, 6)
    return g


def bee_trail(kind):
    g = Grid(40, 12)
    if kind == 'calm':
        g.set(6, 5)
        g.set(8, 4)
        g.hline(14, 20, 6)
    elif kind == 'caps':
        g.set(4, 5)
        g.set(7, 4)
        g.set(10, 6)
        g.hline(16, 25, 7)
    elif kind == 'react':
        g.hline(0, 8, 4)
        g.hline(5, 14, 7)
        g.hline(12, 22, 5)
        g.hline(20, 30, 8)
        gsparkle(g, 33, 3)
        gsparkle(g, 27, 10)
        g.set(16, 2)
    return g


def bee_flower(kind):
    g = Grid(18, 18)
    if kind == 'calm':
        for ex in (4, 11):
            g.hline(ex, ex + 2, 7)
            g.set(ex + 1, 6)
        g.hline(7, 11, 11)
        g.set(6, 10)
        g.set(12, 10)
        g.set(3, 11)
        g.set(15, 11)
    elif kind == 'caps':
        g.rect(3, 5, 6, 7)
        g.rect(11, 5, 14, 7)
        g.ring(9, 11, 2)
    elif kind == 'react':
        gsparkle(g, 4, 6)
        gsparkle(g, 13, 6)
        g.hline(5, 12, 10)
        g.hline(7, 10, 11)
        gsparkle(g, 1, 2)
        gsparkle(g, 16, 3)
        g.set(9, 14)
    else:
        g.hline(3, 6, 7)
        g.set(6, 8)
        g.hline(11, 14, 7)
        g.set(11, 8)
        g.hline(6, 11, 11)
    return g


def bee_honey(kind):
    g = Grid(14, 18)
    if kind == 'calm':
        gdrop(g, 7, 9, 6)
    elif kind == 'caps':
        gdrop(g, 7, 5, 10)
        g.set(4, 4)
        g.set(10, 4)
    elif kind == 'react':
        gdrop(g, 7, 3, 12)
        gsparkle(g, 2, 2)
        gsparkle(g, 11, 13)
        g.hline(4, 10, 1)
    else:
        g.set(7, 3)
    return g


def build_bee():
    im = Image.new('RGB', PS.SIZE, hx('#c9ecff'))
    d = ImageDraw.Draw(im)
    pix_disc(d, 56, 26, 15, '#ffe9a0')
    pix_ring(d, 56, 26, 20, '#ffd9a0')
    sun_rays(d, 56, 26, 22, 28, 10, '#ffd9a0', 0.15)
    cloud_puff(d, 224, 34, 2, '#fffdf6')
    cloud_puff(d, 272, 52, 2, '#fffdf6')
    cloud_puff(d, 12, 58, 1, '#fffdf6')
    # meadow
    d.rectangle((0, 102, W - 1, H_ - 1), fill=hx('#a6e06f'))
    d.rectangle((0, 102, W - 1, 105), fill=hx('#bceb85'))
    # static sunflower that the bee visits
    d.line((52, 140, 52, 172), fill=hx('#4f9a4a'), width=3)
    d.ellipse((36, 148, 52, 160), fill=hx('#63b04f'))
    d.ellipse((54, 156, 70, 166), fill=hx('#63b04f'))
    for k in range(10):
        a = k * math.tau / 10
        px = 52 + math.cos(a) * 21
        py = 128 + math.sin(a) * 21
        pix_disc(d, int(px), int(py), 6, '#ffcf4a')
    pix_disc(d, 52, 128, 14, '#8a5a2a')
    # grass, tiny flowers
    for gx, gy, gh in ((96, 172, 14), (120, 168, 10), (180, 172, 12), (214, 170, 9),
                       (248, 172, 13), (288, 168, 10), (304, 172, 8), (76, 166, 9)):
        grass_tuft(d, gx, gy, gh, '#7fbf5a')
    for fx, fy in ((100, 150), (212, 146), (286, 136), (130, 164), (240, 122)):
        pix_disc(d, fx, fy, 3, '#fff6c8')
        d.point((fx, fy), fill=hx('#ffcf4a'))
    # bee: wings, striped body, cream head, antennae, legs, stinger
    d.ellipse((152, 26, 196, 50), fill=hx('#eaf9ff'))
    d.ellipse((158, 32, 190, 52), fill=hx('#eaf9ff'))
    d.ellipse((146, 46, 188, 76), fill=hx('#ffcf4a'))
    for y in range(46, 77):
        dy = (y - 61) / 15.0
        if abs(dy) > 1:
            continue
        half = int(21 * (1 - dy * dy) ** 0.5)
        for x0, x1 in ((158, 164), (172, 178)):
            d.line((max(167 - half, x0), y, min(167 + half, x1), y), fill=hx('#4a3520'))
    d.polygon([(146, 58), (138, 61), (146, 66)], fill=hx('#8a5a2a'))
    pix_disc(d, 184, 58, 11, '#fff0c0')
    d.line((188, 48, 196, 36), fill=hx('#4a3520'))
    d.point((197, 35), fill=hx('#4a3520'))
    d.line((192, 50, 202, 42), fill=hx('#4a3520'))
    d.point((203, 41), fill=hx('#4a3520'))
    for lx0, ly0, lx1, ly1 in ((156, 74, 150, 82), (166, 76, 162, 86), (176, 74, 180, 84)):
        d.line((lx0, ly0, lx1, ly1), fill=hx('#4a3520'))
    # leaf holding a honey drop
    d.ellipse((204, 72, 222, 82), fill=hx('#6fbf4a'))

    specs = [
        dict(name='蜜蜂表情', x=176, y=54, w=16, h=12, bg='#fff0c0', fg='#5a3a20',
             masks=[bee_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='翅膀', x=162, y=32, w=20, h=10, bg='#eaf9ff', fg='#fffaf0',
             masks=[bee_wing(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='飞行轨迹', x=84, y=58, w=40, h=12, bg='#c9ecff', fg='#ffd66b',
             masks=[bee_trail(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='向日葵花心', x=43, y=119, w=18, h=18, bg='#8a5a2a', fg='#ffcf4a',
             masks=[bee_flower(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='蜜滴', x=206, y=84, w=14, h=18, bg='#c9ecff', fg='#ffb347',
             masks=[bee_honey(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-bee', '小蜜蜂',
        dict(family=FAMILY, tags=['清晨', '蜜蜂', '活力'],
             story='太阳刚把草地晒暖，小蜜蜂就出门了。它在一朵向日葵和一滴蜂蜜之间'
                   '来回飞，翅膀嗡嗡的，像给早晨配了一段小旋律。'),
        '阳光下的草地上有一大朵向日葵，小蜜蜂扇着翅膀在花心与蜜滴之间来回。'
        '每敲一键，空气里飘起金色的花粉星点；敲得越起劲它飞得越欢，'
        '久不打字它就趴在花瓣上打盹。',
        ['#c9ecff', '#a6e06f', '#ffcf4a', '#8a5a2a', '#fff0c0', '#ffb347'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('spark', trigger='key', spawn=(120, 44, 90, 34), count=8, size=2,
                 colors=['#ffd66b', '#fff3b0', '#ffb347'], vx=(-46, 46),
                 vy=(-64, -6), gravity=24, life_ms=1400, edge='die', shape='plus')
    s.set_pulse('向日葵花心', period_ms=2000, minimum=150)
    s.set_reaction(reactHoldMs=800, sleepyAfterMs=19000)
    s.statusInk = '#2a5570'
    return s


# --------------------------------------------------------------------- 8 daisy
def daisy_face(kind):
    g = Grid(22, 16)
    if kind == 'calm':
        for ex in (3, 14):
            g.hline(ex, ex + 2, 7)
            g.set(ex + 1, 6)
        g.hline(8, 13, 12)
        g.set(7, 11)
        g.set(14, 11)
        g.set(1, 11)
        g.set(20, 11)
    elif kind == 'caps':
        g.rect(3, 5, 6, 7)
        g.rect(15, 5, 18, 7)
        g.ring(10, 12, 2)
    elif kind == 'react':
        gsparkle(g, 4, 6)
        gsparkle(g, 17, 6)
        g.hline(7, 14, 11)
        g.hline(9, 12, 12)
        g.set(6, 10)
        g.set(15, 10)
        gsparkle(g, 1, 1)
        gsparkle(g, 20, 14)
    else:
        g.hline(2, 6, 7)
        g.set(6, 8)
        g.hline(15, 19, 7)
        g.set(15, 8)
        g.ring(10, 12, 1)
    return g


def daisy_petals(kind):
    g = Grid(36, 18)

    def petal(x, y):
        for dy, row in enumerate(('.xx.', 'xxxx', 'xxxx', '.xx.')):
            for dx, ch in enumerate(row):
                if ch == 'x':
                    g.set(x + dx, y + dy)

    if kind == 'calm':
        petal(3, 6)
        petal(22, 9)
    elif kind == 'caps':
        petal(2, 4)
        petal(13, 10)
        petal(27, 5)
    elif kind == 'react':
        petal(1, 8)
        petal(9, 2)
        petal(17, 11)
        petal(25, 4)
        petal(31, 12)
        gsparkle(g, 32, 1)
        gsparkle(g, 14, 15)
    else:
        petal(16, 10)
    return g


def daisy_butterfly(kind):
    g = Grid(26, 22)

    def wings(span_rows, body_top, body_bottom):
        g.hline(13, 13, body_top, thick=body_bottom - body_top + 1)
        for wy, span in span_rows:
            g.hline(13 - span, 12, wy, thick=2)
            g.hline(14, 13 + span, wy, thick=2)

    if kind == 'calm':
        wings(((9, 3), (12, 4), (15, 3)), 7, 17)
        g.line(13, 7, 9, 2)
        g.line(13, 7, 17, 2)
        g.set(11, 8)
        g.set(15, 8)
    elif kind == 'caps':
        wings(((7, 5), (10, 7), (13, 6), (16, 3)), 6, 17)
        g.line(13, 6, 8, 1)
        g.line(13, 6, 18, 1)
        gsparkle(g, 2, 12)
    elif kind == 'react':
        wings(((6, 6), (9, 8), (12, 7), (15, 5), (18, 3)), 5, 19)
        g.line(13, 5, 7, 1)
        g.line(13, 5, 19, 1)
        gsparkle(g, 2, 10)
        gsparkle(g, 23, 8)
        g.hline(0, 3, 20)
    else:
        wings(((16, 3), (18, 2)), 13, 20)
        g.line(13, 13, 10, 20)
        g.line(13, 13, 16, 20)
    return g


def daisy_beam(kind):
    g = Grid(52, 14)
    if kind == 'calm':
        g.hline(14, 37, 4)
        g.hline(9, 42, 5)
        g.hline(6, 45, 6)
        g.hline(5, 46, 7)
        g.hline(6, 45, 8)
        g.hline(10, 41, 9)
    elif kind == 'caps':
        g.hline(10, 41, 3)
        g.hline(5, 46, 4)
        g.hline(2, 49, 5)
        g.hline(1, 50, 6)
        g.hline(2, 49, 7)
        g.hline(5, 46, 8)
        g.hline(10, 41, 9)
        gsparkle(g, 14, 6)
        gsparkle(g, 38, 6)
    elif kind == 'react':
        g.hline(2, 49, 6)
        g.hline(0, 51, 7)
        g.hline(1, 50, 8)
        for x in range(4, 50, 7):
            g.set(x, 3)
            g.set(x + 2, 4)
        gsparkle(g, 10, 7)
        gsparkle(g, 41, 5)
    else:
        g.hline(18, 34, 8)
        g.hline(21, 31, 9)
    return g


def daisy_dew(kind):
    g = Grid(18, 12)

    def drop(x, y, h):
        for i in range(h):
            w = 0 if i == 0 else (1 if i < h - 1 else 1)
            g.hline(x - w, x + w, y + i)

    if kind == 'calm':
        drop(5, 6, 5)
        drop(12, 8, 4)
    elif kind == 'caps':
        drop(4, 5, 6)
        drop(12, 7, 5)
        gsparkle(g, 15, 2)
    elif kind == 'react':
        drop(5, 2, 8)
        g.hline(1, 9, 11)
        g.hline(10, 17, 10)
        gsparkle(g, 15, 4)
    return g


def build_daisy():
    im = Image.new('RGB', PS.SIZE, hx('#d4ecff'))
    d = ImageDraw.Draw(im)
    pix_disc(d, 44, 28, 17, '#ffe9a0')
    pix_ring(d, 44, 28, 22, '#ffd9a0')
    sun_rays(d, 44, 28, 24, 31, 12, '#ffd9a0', 0.1)
    cloud_puff(d, 196, 42, 2, '#fffdf6')
    cloud_puff(d, 296, 58, 2, '#fffdf6')
    # meadow
    d.rectangle((0, 100, W - 1, H_ - 1), fill=hx('#a8e07a'))
    d.rectangle((0, 100, W - 1, 104), fill=hx('#b8ea8e'))
    # hero daisy: stem, leaves, white petals, warm centre
    d.line((150, 104, 146, 172), fill=hx('#6fbf4a'), width=4)
    d.ellipse((118, 124, 148, 142), fill=hx('#6fbf4a'))
    d.ellipse((146, 140, 178, 154), fill=hx('#6fbf4a'))
    for k in range(12):
        a = k * math.tau / 12
        for off in (0, 2):
            pix_disc(d, int(150 + math.cos(a) * (30 + off)),
                     int(86 + math.sin(a) * (30 + off)), 11, '#efe6d0')
    for k in range(12):
        a = k * math.tau / 12 + 0.12
        pix_disc(d, int(150 + math.cos(a) * 30), int(86 + math.sin(a) * 30), 11, '#fffaf0')
    pix_disc(d, 150, 86, 20, '#ffd94a')
    pix_ring(d, 150, 86, 19, '#f0c040')
    # a second, smaller daisy in the meadow
    d.line((272, 142, 272, 172), fill=hx('#6fbf4a'), width=3)
    for k in range(8):
        a = k * math.tau / 8
        pix_disc(d, int(272 + math.cos(a) * 12), int(126 + math.sin(a) * 12), 6, '#fffaf0')
    pix_disc(d, 272, 126, 7, '#ffd94a')
    # grass and tiny blossoms
    for gx, gy, gh in ((100, 160, 12), (120, 168, 9), (180, 152, 11), (222, 170, 7),
                       (240, 142, 8), (300, 160, 13), (30, 142, 10), (68, 168, 9),
                       (196, 170, 10), (160, 164, 8)):
        grass_tuft(d, gx, gy, gh, '#7fbf5a')
    for fx, fy in ((120, 146), (190, 162), (300, 150), (210, 128)):
        pix_disc(d, fx, fy, 3, '#fff6c8')
        d.point((fx, fy), fill=hx('#ffcf4a'))
    specs = [
        dict(name='雏菊表情', x=140, y=80, w=22, h=16, bg='#ffd94a', fg='#b07a1a',
             masks=[daisy_face(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='飘落花瓣', x=244, y=32, w=36, h=18, bg='#d4ecff', fg='#fffaf0',
             masks=[daisy_petals(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='小蝴蝶', x=62, y=112, w=26, h=22, bg='#a8e07a', fg='#ff9ec4',
             masks=[daisy_butterfly(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='草地晨光', x=204, y=148, w=52, h=14, bg='#a8e07a', fg='#fff2b8',
             masks=[daisy_beam(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
        dict(name='露珠', x=40, y=150, w=18, h=12, bg='#a8e07a', fg='#cdf3ff',
             masks=[daisy_dew(k) for k in ('calm', 'caps', 'react', 'sleepy')]),
    ]
    finish(im, specs)
    s = PS.Scheme(
        'px6-daisy', '雏菊',
        dict(family=FAMILY, tags=['清晨', '雏菊', '温柔'],
             story='草地上的雏菊刚睡醒，花瓣上还挂着露水。蝴蝶绕了一圈又一圈，'
                   '风也轻轻，早晨可以慢慢来。'),
        '清晨草地上的大雏菊刚睡醒，蝴蝶在花影里绕圈，风把花瓣吹得轻轻往下落。'
        '每按一键，天空就飘下几片白色花瓣；敲得投入时雏菊笑得更亮，'
        '安静下来它就垂着花瓣打起小盹。',
        ['#d4ecff', '#a8e07a', '#fffaf0', '#ffd94a', '#ff9ec4', '#6fbf4a'],
        im, AUTHOR)
    for sp in specs:
        s.sticker(sp['name'], sp['x'], sp['y'], sp['masks'][0], sp['fg'], sp['bg'],
                  caps=sp['masks'][1], react=sp['masks'][2], sleepy=sp['masks'][3])
    s.set_effect('petal', trigger='key', spawn=(70, 30, 150, 12), count=6, size=3,
                 colors=['#fffaf0', '#ffe9f0', '#ffd94a'], vx=(-44, 44),
                 vy=(46, 76), gravity=16, life_ms=2800, edge='die', shape='square')
    s.set_pulse('草地晨光', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=760, sleepyAfterMs=18000)
    s.statusInk = '#2a5570'
    return s


def main(argv):
    builders = [build_sunrise, build_breakfast, build_sneaker, build_soda,
                build_radio, build_lemon, build_bee, build_daisy]
    wanted = set(argv[1:])
    for fn in builders:
        scheme = fn()
        if wanted and scheme.slug not in wanted:
            continue
        d, meta = scheme.save()
        print('%-14s masks %4dB enc / %4dB dec  layers %d  -> %s' % (
            scheme.slug, meta['masks']['encodedBytes'],
            meta['masks']['decodedBytes'], len(meta['layers']), d))


if __name__ == '__main__':
    main(sys.argv)
