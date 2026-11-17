"""Seven comfort/healing pixel schemes (family 治愈暖光) for the Rainy75 V2 IPS screen.

Each scheme is a small cosy scene with one recognisable hero (lamp, blanket cat, sun,
rubber duck, teapot, hugging cloud, candle).  The hero body is baked into the calm
background with warm multi-tone shading; only the parts that must change between mood
frames are stickers, so the 1-bit mask budget stays tiny:

    * face layer      - eyes / mouth, four expressions (calm / caps / react / sleepy)
    * glow layer      - recolours a flat patch of the hero (bright, golden, dim)
    * prop layer      - steam / foam / flame / fluff, amount follows typing
    * glyph layer     - hearts, sparkles or Zzz on a flat piece of wall / sky
    * window layer    - moon or sky colour change on a flat glass patch

Every sticker rectangle is a flat single-colour patch in background.png (the firmware
repaints it flat before stamping the mask).  No sticker or particle spawn rect touches
the status cluster at (233, 12)-(310, 28).

Run:
    .venv/Scripts/python.exe tools/schemes/px6_comfort.py [slug-filter]
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-soft-lamp' --dir build/design-gallery

SPDX-License-Identifier: MIT.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402

STATUS = tuple(PS.STATUS)
ATTRIB = '原创像素图形，由 tools/schemes/px6_comfort.py 程序绘制'


# --------------------------------------------------------------------- helpers
def H(c):
    return PS.hexrgb(c)


def blocked(x, y, rects, pad=0):
    for (rx, ry, rw, rh) in rects:
        if rx - pad <= x < rx + rw + pad and ry - pad <= y < ry + rh + pad:
            return True
    return False


def patch(im, x, y, w, h, colour):
    """Reserve a flat sticker rectangle in the background image."""
    ImageDraw.Draw(im).rectangle((x, y, x + w - 1, y + h - 1), fill=H(colour))


def rect(im, x0, y0, x1, y1, colour):
    ImageDraw.Draw(im).rectangle((x0, y0, x1, y1), fill=H(colour))


def grad(im, x, y, w, h, top, bottom, bands=6, dither=True):
    d = ImageDraw.Draw(im)
    rows = [PS.lerp(H(top), H(bottom), yy / max(1, h - 1)) for yy in range(h)]
    bandh = max(1, h // bands)

    def bc(yy):
        return rows[min(h - 1, min(bands - 1, yy // bandh) * bandh + bandh // 2)]

    for yy in range(h):
        d.line([(x, y + yy), (x + w - 1, y + yy)], fill=bc(yy))
    if dither:
        for k in range(1, bands):
            yy = k * bandh
            if 0 < yy < h:
                c0, c1 = bc(yy - 1), bc(yy)
                for xx in range(x, x + w):
                    d.point((xx, y + yy - 1), fill=c1 if (xx + yy) % 2 == 0 else c0)


def pool(im, cx, cy, rx, ry, colour, strength=0.5, seed=1):
    """Dithered warm light puddle (drawn on furniture, never under a sticker)."""
    px = im.load()
    c = H(colour)
    for yy in range(max(0, cy - ry), min(im.height, cy + ry + 1)):
        for xx in range(max(0, cx - rx), min(im.width, cx + rx + 1)):
            dd = ((xx - cx) / float(rx)) ** 2 + ((yy - cy) / float(ry)) ** 2
            if dd >= 1.0:
                continue
            k = (1.0 - dd) ** 1.2 * strength
            if ((xx * 7 + yy * 13 + seed * 3) % 29) / 29.0 < k:
                base = px[xx, yy]
                t = min(0.8, k * 1.6)
                px[xx, yy] = tuple(round(base[i] + (c[i] - base[i]) * t) for i in range(3))


def blob(im, cx, cy, rx, ry, colour, skip=()):
    c = H(colour)
    for yy in range(int(cy - ry), int(cy + ry) + 1):
        for xx in range(int(cx - rx), int(cx + rx) + 1):
            if 0 <= xx < im.width and 0 <= yy < im.height \
                    and ((xx - cx) / float(rx)) ** 2 + ((yy - cy) / float(ry)) ** 2 <= 1.0 \
                    and not blocked(xx, yy, skip):
                im.putpixel((xx, yy), c)


def bokeh_sparse(im, count, colour, area, skip=(), seed=1, rmax=2):
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    x0, y0, x1, y1 = area
    for _ in range(count):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        if blocked(x, y, skip, pad=2):
            continue
        r = rng.randrange(1, rmax + 1)
        d.ellipse((x - r, y - r, x + r, y + r), fill=H(colour))


def starfield(im, count, colour, seed, area=None, skip=(), size2=6):
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    x0, y0, x1, y1 = area or (0, 0, im.width, im.height)
    c = H(colour)
    for _ in range(count):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        if blocked(x, y, skip, pad=1):
            continue
        d.point((x, y), fill=c)
        if rng.randrange(size2) == 0:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((x + dx, y + dy), fill=c)


def wood_floor(im, y0, base, dark, light, seed=1, x0=0, x1=320):
    d = ImageDraw.Draw(im)
    rng = random.Random(seed)
    d.rectangle((x0, y0, x1 - 1, 171), fill=H(base))
    plank = 15
    for yy in range(y0, 172, plank):
        d.line([(x0, yy), (x1 - 1, yy)], fill=H(dark))
    for row, yy in enumerate(range(y0, 172, plank)):
        off = (row * 53) % 70
        for xx in range(x0 + off, x1, 70):
            d.line([(xx, yy), (xx, min(171, yy + plank - 1))], fill=H(dark))
    for _ in range(46):
        xx = rng.randrange(x0, max(x0 + 1, x1 - 10))
        yy = rng.randrange(y0 + 1, 171)
        d.line([(xx, yy), (xx + rng.randrange(3, 12), yy)], fill=H(light))


def rug(im, cx, cy, rx, ry, base, ring, inner):
    blob(im, cx, cy, rx, ry, ring)
    blob(im, cx, cy, rx - 3, ry - 2, base)
    blob(im, cx, cy, rx - 9, max(2, ry - 5), inner)


def curtain(im, x, y, w, h, base, fold, seed=0):
    d = ImageDraw.Draw(im)
    d.rectangle((x, y, x + w - 1, y + h - 1), fill=H(base))
    for fx in range(x + 2, x + w, 4):
        d.line([(fx, y), (fx, y + h - 1)], fill=H(fold))
    rng = random.Random(seed)
    for fx in range(x, x + w, 3):
        d.point((fx, y + h - 1 - rng.randrange(0, 3)), fill=H(fold))


def tiles(im, y0, y1, grout, step=26, skip=()):
    d = ImageDraw.Draw(im)
    g = H(grout)
    for yy in range(y0, y1):
        for xx in range(0, 320):
            if blocked(xx, yy, skip):
                continue
            if xx % step == 0 or yy % step == y0 % step:
                d.point((xx, yy), fill=g)


def soft_cloud(im, cx, cy, scale, colour, skip=()):
    for (ox, oy, rx, ry) in ((-11, 2, 9, 5), (0, -2, 11, 6), (10, 2, 8, 4), (-2, 4, 13, 4)):
        blob(im, cx + ox * scale, cy + oy * scale, rx * scale, ry * scale, colour, skip)


def paste(dst, src, x, y):
    for yy, row in enumerate(src.rows()):
        for xx, ch in enumerate(row):
            if ch != '.':
                dst.set(x + xx, y + yy, ch)


def plus(g, cx, cy, r=1):
    g.hline(cx - r, cx + r, cy)
    g.vline(cx, cy - r, cy + r)


def zee(g, x, y, s):
    g.hline(x, x + s - 1, y)
    g.hline(x, x + s - 1, y + s - 1)
    for i in range(s):
        g.set(x + s - 1 - i, y + i)


HEART_ROWS = ['.##.##.', '#######', '#######', '.#####.', '..###..', '...#...']


def heart_art():
    return Grid.from_ascii(HEART_ROWS)


def glyph_art(state, w=32, h=18):
    """Empty calm, sparkle caps, heart react, Zzz sleepy."""
    g = Grid(w, h)
    if state == 'heart':
        paste(g, heart_art(), (w - 7) // 2, 5)
    elif state == 'zzz':
        zee(g, w - 15, 2, 7)
        zee(g, w - 10, 8, 5)
        zee(g, w - 4, 12, 3)
    elif state == 'spark':
        plus(g, w - 7, 4, 2)
        plus(g, 4, h - 5, 1)
        plus(g, w // 2, h - 3, 1)
    return g


def face_art(w, h, state, eye_y=4, mouth_y=None):
    """Cute face: open, wide, happy, closed eyes + matching mouth."""
    g = Grid(w, h)
    lx = max(2, w // 2 - 6)
    rx = min(w - 4, w // 2 + 3)
    if mouth_y is None:
        mouth_y = eye_y + max(4, h - eye_y - 4)
    if state == 'sleepy':
        g.hline(lx - 1, lx + 2, eye_y, '#')
        g.hline(rx - 1, rx + 2, eye_y, '#')
        g.hline(lx + 2, rx - 2, mouth_y, '#')
    elif state == 'react':
        g.set(lx - 1, eye_y + 1, '#')
        g.set(lx, eye_y, '#')
        g.set(lx + 1, eye_y + 1, '#')
        g.set(rx - 1, eye_y + 1, '#')
        g.set(rx, eye_y, '#')
        g.set(rx + 1, eye_y + 1, '#')
        g.hline(lx + 2, rx - 2, mouth_y, '#')
        g.hline(lx + 3, rx - 3, mouth_y - 1, '#')
    elif state == 'caps':
        g.rect(lx - 1, eye_y, lx + 1, eye_y + 2, '#')
        g.rect(rx - 1, eye_y, rx + 1, eye_y + 2, '#')
        g.rect(lx + 3, mouth_y - 1, lx + 4, mouth_y, '#')
    else:
        g.rect(lx, eye_y, lx + 1, eye_y + 1, '#')
        g.rect(rx, eye_y, rx + 1, eye_y + 1, '#')
        g.hline(lx + 2, rx - 2, mouth_y, '#')
        g.set(lx + 1, mouth_y - 1, '#')
        g.set(rx - 1, mouth_y - 1, '#')
    return g


def glow_art(w, h, level):
    """Soft round bloom inside a flat patch; level 0..3 grows the bloom."""
    g = Grid(w, h)
    if level < 0:
        return g
    rx = (w - 4) / 2.0
    ry = (h - 2) / 2.0 * (0.55 + 0.15 * level)
    cx, cy = w / 2.0, h / 2.0
    for yy in range(h):
        for xx in range(w):
            if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                g.set(xx, yy, '#')
    return g


# ------------------------------------------------------------------ lamp scene
def build_soft_lamp():
    WALL = '#3a2a2e'
    WALL_D = '#241a1e'
    WALL_S = '#2e2024'
    WOOD = '#5a4038'
    WOOD_D = '#3f2b26'
    WOOD_L = '#6f4c3f'
    FLOOR = '#2a1d1d'
    SHADE = '#f2cf9c'
    SHADE_HI = '#ffeac6'
    SHADE_LO = '#d9a874'
    SHADE_DP = '#b8805a'
    CREAM = '#ffe9c4'
    GOLD = '#ffd9a0'
    TERRA = '#c96f52'
    SAGE = '#8aa878'
    SAGE_D = '#6b8560'
    PLUM = '#4a2f34'
    INK = '#5a3a30'
    FACE = (186, 74, 24, 14)
    GLOW = (178, 88, 36, 12)
    GLYPH = (232, 48, 32, 18)
    MOON = (70, 28, 24, 24)
    rects = [FACE, GLOW, GLYPH, MOON]

    bg = PS.blank(WALL)
    grad(bg, 0, 0, 320, 46, WALL_D, WALL, bands=6)
    ImageDraw.Draw(bg).line([(0, 45), (319, 45)], fill=H(WALL_S))
    # night window (flat glass, stars only outside the moon sticker patch)
    patch(bg, 19, 21, 82, 68, '#1b2340')
    starfield(bg, 15, '#e8ecff', seed=3, area=(22, 24, 98, 86), skip=rects)
    PS.window_frame(bg, 16, 18, 104, 92, frame='#6b4a3e', sill='#4a3430')
    curtain(bg, 6, 10, 12, 98, PLUM, '#39202a')
    curtain(bg, 104, 10, 12, 98, PLUM, '#39202a')
    d = ImageDraw.Draw(bg)
    # floor + rug on the left
    wood_floor(bg, 150, FLOOR, '#1e1414', '#3a2828', seed=7, x0=0, x1=112)
    rug(bg, 58, 160, 46, 12, '#5a3038', '#7a4048', '#47262c')
    # wall art
    d.rectangle((120, 62, 162, 96), fill=H('#3f2c30'))
    d.rectangle((124, 66, 158, 92), fill=H('#2a1c22'))
    d.ellipse((134, 72, 148, 86), fill=H(GOLD))
    d.point((141, 79), fill=H('#fff3d0'))
    d.point((130, 88), fill=H(TERRA))
    # wall shelf with books, right
    d.rectangle((268, 96, 316, 99), fill=H('#4a3430'))
    for bx, bh, bc in ((274, 14, '#8a5a4a'), (283, 11, '#a8764e'), (292, 16, '#6f4c5a')):
        d.rectangle((bx, 97 - bh, bx + 7, 96), fill=H(bc))
    # nightstand
    d.rectangle((112, 140, 319, 147), fill=H(WOOD))
    d.line([(112, 141), (319, 141)], fill=H(WOOD_L))
    d.rectangle((112, 147, 319, 171), fill=H(WOOD_D))
    for x0 in (122, 190, 258):
        d.rectangle((x0, 151, x0 + 58, 168), outline=H(WOOD), width=2)
        d.point((x0 + 29, 159), fill=H(GOLD))
        d.point((x0 + 30, 159), fill=H(GOLD))
    # little book + mug on the nightstand, left of the lamp
    d.rectangle((124, 133, 152, 140), fill=H('#8a5a4a'))
    d.rectangle((124, 136, 152, 139), fill=H('#d0b8a0'))
    d.rectangle((160, 130, 176, 140), fill=H('#e8d6c0'))
    d.rectangle((176, 132, 180, 138), fill=H('#e8d6c0'))
    # potted plant on the nightstand, right of the lamp
    d.rectangle((256, 132, 272, 140), fill=H(TERRA))
    d.rectangle((258, 128, 270, 133), fill=H(SAGE_D))
    for (lx, ly, lr) in ((258, 120, 5), (270, 118, 5), (264, 112, 5), (252, 124, 4),
                         (276, 124, 4)):
        blob(bg, lx, ly, lr, lr, SAGE)
    blob(bg, 260, 122, 3, 3, '#a8c48e')
    # lamp: pole, base, dome shade
    d.rectangle((194, 104, 202, 140), fill=H('#6b4a3a'))
    d.rectangle((194, 104, 196, 140), fill=H('#8a6550'))
    d.ellipse((168, 126, 228, 142), fill=H('#4a3428'))
    d.ellipse((170, 124, 226, 139), fill=H('#7a5a46'))
    d.ellipse((176, 126, 220, 136), fill=H('#8a6a52'))
    d.arc((170, 124, 226, 139), 200, 340, fill=H('#a8805a'))
    for yy in range(54, 58):
        half = int(round(5 + (yy - 54) * 1.7))
        d.line([(198 - half, yy), (198 + half, yy)], fill=H(SHADE))
    for yy in range(58, 104):
        half = int(round(11 + (yy - 58) * 0.455))
        d.line([(198 - half, yy), (198 + half, yy)], fill=H(SHADE))
    for cx in (174, 184, 194, 204, 214):
        blob(bg, cx, 104, 5, 4, SHADE)
    # side shading stays outside the flat face / glow patches
    for yy in range(58, 100):
        half = int(round(11 + (yy - 58) * 0.455))
        for k in range(4):
            d.point((198 - half + k, yy), fill=H(SHADE_HI))
            d.point((198 + half - k, yy), fill=H(SHADE_LO))
    for yy in range(100, 104):
        d.line([(170, yy), (226, yy)], fill=H(SHADE_DP))
    bokeh_sparse(bg, 12, '#4a3436', area=(136, 50, 264, 132),
                 skip=rects + [STATUS], seed=4)
    d.line([(158, 146), (238, 146)], fill=H('#7a5a46'))
    d.line([(170, 144), (226, 144)], fill=H('#6f4c3f'))
    for (x, y, w, h), c in zip(rects, (SHADE, SHADE, WALL, '#1b2340')):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-soft-lamp', '小夜灯',
        dict(family='治愈暖光', tags=['陪伴', '深夜', '放松'],
             story='关掉大灯，只留床头那盏小夜灯。它把房间烘成蜜糖色，'
                   '连窗外的月亮都显得不那么冷了。'),
        '昏暗的卧室里只剩床头一盏小夜灯。每次敲键，灯罩会亮一点，几粒暖色光点从灯下慢慢飘起来；'
        '敲得投入时小灯会眯起眼睛笑；你停下手，它慢慢变暗，陪你把这一晚轻轻收好。',
        ['#1b2340', '#3a2a2e', '#f2cf9c', '#ffe9c4', '#ffd9a0', '#c96f52', '#8aa878'],
        bg, ATTRIB)
    add_sticker(s, '灯罩暖光', GLOW, glow_art(36, 12, 2), '#ffe4b0', SHADE,
                caps=glow_art(36, 12, 3), caps_fg='#fff6dd',
                react=glow_art(36, 12, 3), react_fg='#ffcf8a',
                sleepy=glow_art(36, 12, 0), sleepy_fg='#b98f6a')
    add_sticker(s, '小表情', FACE, face_art(24, 14, 'calm', 4, 9), INK, SHADE,
                caps=face_art(24, 14, 'caps', 4, 9), caps_fg='#6a4638',
                react=face_art(24, 14, 'react', 4, 9), react_fg='#8a4a3a',
                sleepy=face_art(24, 14, 'sleepy', 4, 9), sleepy_fg='#6a4a40')
    add_sticker(s, '晚安符号', GLYPH, glyph_art('calm'), GOLD, WALL,
                caps=glyph_art('caps'), caps_fg=GOLD,
                react=glyph_art('react'), react_fg='#ff9fae',
                sleepy=glyph_art('sleepy'), sleepy_fg='#c9b8d8')
    add_sticker(s, '窗边的月亮', MOON, moon_art('calm'), '#e8e4d6', '#1b2340',
                caps=moon_art('caps'), caps_fg='#fff6dd',
                react=moon_art('react'), react_fg='#ffe6a8',
                sleepy=moon_art('sleepy'), sleepy_fg='#8f96b8')
    s.set_effect('dust', trigger='key', spawn=(180, 42, 40, 14), count=4, size=1,
                 colors=[CREAM, GOLD, TERRA], vx=(-12, 12), vy=(-16, -5), gravity=0,
                 life_ms=3200, edge='wrap')
    s.set_pulse('灯罩暖光', period_ms=2600, minimum=170)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=22000)
    s.statusInk = CREAM
    return s


def moon_art(state, w=24, h=24):
    """Moon phase / mood inside a flat glass patch."""
    g = Grid(w, h)
    cx, cy, r = w / 2.0, h / 2.0, w / 2.0 - 2
    for yy in range(h):
        for xx in range(w):
            if ((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r:
                g.set(xx, yy, '#')
    if state in ('calm', 'sleepy'):
        g.disc(cx + 6, cy - 5, 8, '.')
    if state == 'react':
        g.hline(7, 9, 11, '.')
        g.hline(13, 15, 11, '.')
        g.set(10, 16, '.')
        g.set(11, 16, '.')
    elif state == 'caps':
        for (x, y) in ((7, 8), (14, 10), (10, 15)):
            g.set(x, y, '.')
    else:
        for (x, y) in ((8, 9), (14, 12), (10, 16)):
            g.set(x, y, '.')
    return g


# ------------------------------------------------------------- blanket cat scene
def build_blanket_cat():
    WALL = '#3a2830'
    WALL_D = '#241a22'
    BED = '#4a323a'
    BED_L = '#5a3e46'
    BED_HI = '#6a4a52'
    CAT = '#f0c9a0'
    CAT_HI = '#fadcb8'
    CAT_LO = '#d9a874'
    CAT_STRIPE = '#c98f5e'
    BLANKET = '#b87f8a'
    BLANKET_HI = '#d0959f'
    BLANKET_LO = '#8f6068'
    GOLD = '#ffd9a0'
    PLUM = '#4a2f34'
    INK = '#5a3a30'
    FACE = (100, 84, 24, 16)
    ACCENT = (146, 128, 40, 16)
    GLYPH = (166, 56, 32, 18)
    rects = [FACE, ACCENT, GLYPH]

    bg = PS.blank(WALL)
    grad(bg, 0, 0, 320, 40, WALL_D, WALL, bands=6)
    wood_floor(bg, 118, '#241a1e', '#191114', '#3a2828', seed=5, x0=0, x1=70)
    rug(bg, 34, 154, 30, 16, '#5a3038', '#7a4048', '#47262c')
    # dusk window
    grad(bg, 15, 17, 66, 62, '#2a2440', '#4a3a5a', bands=5)
    starfield(bg, 10, '#e8ecff', seed=8, area=(18, 20, 80, 76), skip=rects)
    PS.moon(bg, 70, 30, 5, '#f7f0dd', '#d8cfae')
    PS.window_frame(bg, 12, 14, 84, 80, frame='#6b4a3e', sill='#4a3430')
    curtain(bg, 3, 8, 10, 84, PLUM, '#39202a')
    curtain(bg, 84, 8, 10, 84, PLUM, '#39202a')
    d = ImageDraw.Draw(bg)
    # bed quilt
    d.rectangle((70, 118, 319, 171), fill=H(BED))
    d.line([(70, 118), (319, 118)], fill=H(BED_L))
    d.line([(70, 119), (319, 119)], fill=H(BED_HI))
    for yy in range(126, 172, 9):
        for xx in range(72, 320, 12):
            if not blocked(xx, yy, rects):
                d.line([(xx, yy), (min(319, xx + 6), yy)], fill=H('#543842'))
    for xx in range(74, 320, 22):
        d.line([(xx, 122), (xx + 6, 130)], fill=H('#5f424c'))
    # pillow on the right
    d.rounded_rectangle((236, 124, 312, 148), radius=9, fill=H('#e8d6c0'),
                        outline=H('#d0b8a0'))
    d.arc((240, 128, 308, 146), 200, 340, fill=H('#f6e8d6'))
    # wall sconce
    d.rectangle((262, 58, 292, 62), fill=H('#4a3430'))
    d.polygon([(262, 58), (276, 50), (292, 58)], fill=H('#8a5a4a'))
    d.rectangle((274, 62, 279, 76), fill=H('#4a3430'))
    for x, y in ((268, 54), (284, 55), (276, 48)):
        d.point((x, y), fill=H('#ffe9c4'))
    bokeh_sparse(bg, 7, '#4a343c', area=(250, 44, 310, 84),
                 skip=rects + [STATUS], seed=13)
    # picture
    d.rectangle((198, 30, 232, 54), fill=H('#4a3430'))
    d.rectangle((202, 34, 228, 50), fill=H('#5a4048'))
    d.point((215, 41), fill=H(GOLD))
    # cat: head, chest and paws, then the blanket mound
    d.ellipse((86, 70, 140, 124), fill=H(CAT))
    for cx in (100, 126):
        d.polygon([(cx - 10, 86), (cx - 2, 64), (cx + 8, 86)], fill=H(CAT))
        d.polygon([(cx - 6, 84), (cx - 2, 71), (cx + 4, 84)], fill=H(CAT_LO))
    d.arc((88, 72, 138, 122), 200, 320, fill=H(CAT_HI))
    d.arc((88, 90, 138, 126), 20, 140, fill=H(CAT_LO))
    for (x, y) in ((94, 80), (102, 76), (120, 77), (133, 82), (94, 98), (135, 96)):
        d.point((x, y), fill=H(CAT_STRIPE))
        d.point((x, y + 1), fill=H(CAT_STRIPE))
    # chest fur tucked over the blanket edge
    d.ellipse((112, 108, 148, 132), fill=H(CAT))
    d.arc((112, 110, 148, 134), 200, 340, fill=H(CAT_HI))
    # front paws resting on the blanket
    d.ellipse((138, 118, 158, 128), fill=H(CAT))
    d.ellipse((160, 116, 180, 126), fill=H(CAT))
    for (x, y) in ((144, 122), (150, 122), (166, 120), (172, 120)):
        d.point((x, y), fill=H(CAT_LO))
    # blanket mound
    d.ellipse((132, 108, 230, 166), fill=H(BLANKET))
    d.rectangle((140, 138, 224, 164), fill=H(BLANKET))
    d.arc((132, 106, 230, 158), 190, 350, fill=H(BLANKET_HI))
    d.arc((132, 124, 230, 172), 10, 170, fill=H(BLANKET_LO))
    for yy in range(122, 160, 5):
        for xx in range(140, 224, 6):
            if not blocked(xx, yy, rects) and not blocked(xx + 2, yy, rects):
                d.line([(xx, yy), (xx + 2, yy)], fill=H(BLANKET_LO))
    d.line([(150, 122), (146, 156)], fill=H(BLANKET_LO))
    d.line([(198, 120), (202, 156)], fill=H(BLANKET_LO))
    bokeh_sparse(bg, 7, '#4a343c', area=(90, 60, 240, 114),
                 skip=rects + [STATUS], seed=6)
    for (x, y, w, h), c in zip(rects, (CAT, BLANKET, WALL)):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-blanket-cat', '毛毯猫',
        dict(family='治愈暖光', tags=['陪伴', '困倦', '拥抱'],
             story='把猫和自己一起裹进毛毯。它只露出一双圆眼睛，'
                   '呼吸声比键盘声还轻，像在提醒你也可以慢一点。'),
        '把猫和自己一起裹进毛毯的夜晚。每次敲键，毯子边会冒出小小的爱心，猫咪抬起头眯眼蹭你；'
        '打字久了它的耳朵会动，停下之后又缩回毛毯里呼呼睡去，只剩呼吸的起伏陪着你。',
        ['#241a22', '#3a2830', '#f0c9a0', '#b87f8a', '#4a323a', '#ffd9a0', '#4a2f34'],
        bg, ATTRIB)
    add_sticker(s, '猫咪表情', FACE, face_art(24, 16, 'calm', 5, 11), INK, CAT,
                caps=face_art(24, 16, 'caps', 5, 11), caps_fg='#6a4638',
                react=face_art(24, 16, 'react', 5, 11), react_fg='#8a4a3a',
                sleepy=face_art(24, 16, 'sleepy', 5, 11), sleepy_fg='#6a4a40')
    add_sticker(s, '毯子花纹', ACCENT, blanket_pattern('calm'), BLANKET_HI, BLANKET,
                caps=blanket_pattern('caps'), caps_fg='#e0a8b0',
                react=blanket_pattern('react'), react_fg='#ffb0a0',
                sleepy=blanket_pattern('sleepy'), sleepy_fg='#7a5058')
    add_sticker(s, '晚安符号', GLYPH, glyph_art('calm'), GOLD, WALL,
                caps=glyph_art('caps'), caps_fg=GOLD,
                react=glyph_art('react'), react_fg='#ff9fae',
                sleepy=glyph_art('sleepy'), sleepy_fg='#c9b8d8')
    s.set_effect('heart', trigger='key', spawn=(100, 54, 44, 16), count=3, size=3,
                 colors=['#f79aa8', '#ffc4cf', '#ffe9c4'], vx=(-24, 24),
                 vy=(-64, -34), gravity=14, life_ms=2200, edge='die')
    s.set_pulse('毯子花纹', period_ms=2800, minimum=200)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=20000)
    s.statusInk = '#ffe9c4'
    return s


def blanket_pattern(state, w=40, h=16):
    g = Grid(w, h)
    if state == 'sleepy':
        return g
    if state == 'caps':
        for xx in range(2, w - 2, 6):
            g.line(xx, 2, xx + 5, h - 3)
    elif state == 'react':
        for xx in range(6, w - 6, 10):
            paste(g, heart_art(), xx, 5)
    else:
        for yy in range(3, h - 2, 5):
            for xx in range(2, w - 3, 7):
                g.rect(xx, yy, xx + 3, yy + 1)
    return g


# ---------------------------------------------------------------- sunbeam scene
def sun_face_art(state):
    return face_art(24, 16, state, 5, 11)


def build_sunbeam():
    WALL = '#f0d8b8'
    SKY = '#f7b46a'
    SKY_HI = '#ffd08a'
    SUN = '#fff3cf'
    SUN_HI = '#fffbe8'
    SUN_LO = '#ffe2a8'
    WOOD = '#a8703e'
    WOOD_D = '#8a5730'
    WOOD_L = '#c98f52'
    SAGE = '#7d9a6e'
    SAGE_D = '#5f7a54'
    TERRA = '#c96f52'
    GOLD = '#ffd27a'
    INK = '#5a3a24'
    FACE = (106, 54, 24, 14)
    GLOW = (106, 70, 32, 12)
    RAYS = (156, 52, 32, 24)
    GLYPH = (268, 86, 32, 18)
    rects = [FACE, GLOW, RAYS, GLYPH]

    bg = PS.blank(WALL)
    d = ImageDraw.Draw(bg)
    # window: one flat golden pane without mullions (the sun lives in the glass)
    d.rectangle((28, 14, 200, 108), fill=H('#8a5a3a'))
    d.rectangle((33, 19, 194, 102), fill=H(SKY))
    d.line([(31, 17), (196, 17)], fill=H('#a8764e'))
    d.line([(31, 17), (31, 104)], fill=H('#a8764e'))
    d.line([(31, 105), (196, 105)], fill=H('#6f4a32'))
    d.rectangle((24, 106, 204, 112), fill=H('#6f4a32'))
    d.line([(24, 106), (203, 106)], fill=H('#8a5a3a'))
    soft_cloud(bg, 50, 96, 1.0, SKY_HI, rects)
    soft_cloud(bg, 172, 30, 0.7, SKY_HI, rects)
    # the sun: round disc, calm spiky rim, warm rim shading
    scx, scy, sr = 122, 64, 26
    for yy in range(scy - sr, scy + sr + 1):
        half = int(round(math.sqrt(max(0.0, sr * sr - (yy - scy) ** 2))))
        d.line([(scx - half, yy), (scx + half, yy)], fill=H(SUN))
    for i in range(16):
        a = i * math.tau / 16
        for rr in range(sr + 2, sr + 6):
            d.point((scx + math.cos(a) * rr, scy + math.sin(a) * rr), fill=H(GOLD))
    for yy in range(scy - sr, scy + sr + 1):
        half = int(round(math.sqrt(max(0.0, sr * sr - (yy - scy) ** 2))))
        if yy < scy:
            d.point((scx - half, yy), fill=H(SUN_HI))
            d.point((scx - half + 1, yy), fill=H(SUN_HI))
        else:
            d.point((scx + half, yy), fill=H(SUN_LO))
            d.point((scx + half - 1, yy), fill=H(SUN_LO))
    # wall picture (framed mini sun)
    d.rectangle((250, 36, 314, 80), fill=H('#e6c49c'))
    d.rectangle((254, 40, 310, 76), fill=H('#f7e6c8'))
    d.ellipse((270, 48, 294, 72), fill=H(GOLD))
    for i in range(8):
        a = i * math.tau / 8
        d.line([(282 + math.cos(a) * 13, 60 + math.sin(a) * 13),
                (282 + math.cos(a) * 16, 60 + math.sin(a) * 16)], fill=H('#d99a52'))
    # floor, rug and the sunlight beam
    wood_floor(bg, 118, WOOD, WOOD_D, WOOD_L, seed=11)
    rug(bg, 58, 152, 48, 18, '#c96f52', '#e0a07a', '#a8583e')
    beam = [(34, 112), (196, 112), (276, 172), (96, 172)]
    mask = Image.new('1', PS.SIZE, 0)
    ImageDraw.Draw(mask).polygon(beam, fill=1)
    mpx = mask.load()
    px = bg.load()
    warm = H('#fff3cf')
    bayer = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
    for yy in range(112, 172):
        inten = 0.55 * (1.0 - 0.35 * (yy - 112) / 60.0)
        for xx in range(0, 320):
            if not mpx[xx, yy]:
                continue
            k = inten * (0.35 + 0.65 * bayer[yy % 4][xx % 4] / 15.0)
            base = px[xx, yy]
            px[xx, yy] = tuple(round(base[i] + (warm[i] - base[i]) * k)
                               for i in range(3))
    # potted plant and a mug waiting in the warm light
    d = ImageDraw.Draw(bg)
    d.rectangle((272, 152, 306, 170), fill=H(TERRA))
    d.rectangle((274, 148, 304, 153), fill=H('#a8583e'))
    for (lx, ly, lr) in ((280, 138, 6), (296, 136, 6), (288, 126, 7), (272, 142, 5),
                         (304, 142, 5)):
        blob(bg, lx, ly, lr, lr, SAGE)
    blob(bg, 284, 132, 4, 4, '#93b07c')
    blob(bg, 292, 127, 3, 3, SAGE_D)
    d.rectangle((240, 150, 260, 166), fill=H('#fff3cf'))
    d.rectangle((260, 154, 265, 162), fill=H('#fff3cf'))
    d.rectangle((242, 152, 258, 155), fill=H('#c96f52'))
    for yy in range(136, 150):
        d.point((246 + int(2 * math.sin(yy * 0.7)), yy), fill=H('#fffbe8'))
        d.point((254 + int(2 * math.sin(yy * 0.5)), yy), fill=H('#fffbe8'))
    d.point((40, 104), fill=H('#5a3a24'))
    d.point((43, 103), fill=H('#5a3a24'))
    d.point((46, 104), fill=H('#5a3a24'))
    for (x, y, w, h), c in zip(rects, (SUN, SUN, SKY, WALL)):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-sunbeam', '午后阳光',
        dict(family='治愈暖光', tags=['午后', '慵懒', '治愈'],
             story='午后三点的窗台，阳光把木地板晒得暖烘烘的。'
                   '尘埃在光里慢慢打转，时间也跟着变慢。'),
        '午后三点的窗边，阳光把地板晒得暖烘烘。按键时空气里的细小尘埃会跟着亮起来，'
        '在光柱里慢慢打转；敲得越起劲，窗上的太阳笑得越开心；安静下来，它就慢慢落到窗前，光线也柔和下来。',
        ['#f0d8b8', '#f7b46a', '#fff3cf', '#a8703e', '#c96f52', '#7d9a6e', '#8a5a3a'],
        bg, ATTRIB)
    add_sticker(s, '太阳表情', FACE, sun_face_art('calm'), '#8a4a30', SUN,
                caps=sun_face_art('caps'), caps_fg='#9a5538',
                react=sun_face_art('react'), react_fg='#b85a3a',
                sleepy=sun_face_art('sleepy'), sleepy_fg='#8a6040')
    add_sticker(s, '太阳暖光', GLOW, glow_art(32, 12, 1), '#ffe9a8', SUN,
                caps=glow_art(32, 12, 2), caps_fg='#fffbe8',
                react=glow_art(32, 12, 2), react_fg='#ffd27a',
                sleepy=glow_art(32, 12, -1), sleepy_fg='#e8a45e')
    add_sticker(s, '太阳光线', RAYS, ray_art('calm'), SKY, SKY,
                caps=ray_art('caps'), caps_fg='#ffe2a8',
                react=ray_art('react'), react_fg='#fff3cf',
                sleepy=ray_art('sleepy'), sleepy_fg=SKY)
    add_sticker(s, '光的碎屑', GLYPH, glyph_art('calm'), GOLD, WALL,
                caps=glyph_art('caps'), caps_fg=GOLD,
                react=glyph_art('react'), react_fg='#f79aa8',
                sleepy=glyph_art('calm'))
    s.set_effect('dust', trigger='key', spawn=(90, 104, 140, 18), count=5, size=1,
                 colors=['#fff3cf', '#ffd27a', '#c96f52'], vx=(-10, 10),
                 vy=(-14, -3), gravity=0, life_ms=3400, edge='wrap')
    s.set_pulse('太阳暖光', period_ms=3000, minimum=190)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=24000)
    s.statusInk = '#5a3a24'
    return s


def ray_art(state, w=32, h=24):
    g = Grid(w, h)
    if state == 'sleepy':
        return g
    n = 5 if state in ('caps', 'react') else 3
    for i in range(n):
        y = 4 + i * (h - 8) // max(1, n - 1)
        ln = 14 if state in ('caps', 'react') else 10
        for xx in range(2, 2 + ln):
            g.set(xx, y + (xx // 6) % 2)
    return g


# ----------------------------------------------------------------- bath scene
def build_bath_bubble():
    WALL = '#4a4038'
    WALL_HI = '#5a4e42'
    GROUT = '#3a332c'
    TUB = '#e8d8c0'
    TUB_HI = '#f6ecda'
    TUB_LO = '#c9b294'
    WATER = '#7fb8b0'
    WATER_HI = '#9fcfc6'
    DUCK = '#ffd98a'
    DUCK_HI = '#ffe9b0'
    DUCK_LO = '#e0b45e'
    BEAK = '#e8894a'
    FOAM = '#fdf2e2'
    GOLD = '#ffd9a0'
    TERRA = '#c96f52'
    INK = '#5a4030'
    FACE = (118, 112, 24, 12)
    FOAM_R = (176, 112, 64, 20)
    STEAM = (110, 58, 32, 26)
    FLAME = (286, 56, 24, 22)
    rects = [FACE, FOAM_R, STEAM, FLAME]

    bg = PS.blank(WALL)
    tiles(bg, 0, 100, GROUT, step=26, skip=rects)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 94, 319, 100), fill=H('#564a3e'))
    # steamy window
    grad(bg, 23, 18, 62, 44, '#20283c', '#3a4458', bands=4)
    starfield(bg, 8, '#dfe8ff', seed=4, area=(26, 20, 82, 58), skip=rects)
    PS.moon(bg, 70, 30, 5, '#f0f0e0', '#cfcfb8')
    PS.window_frame(bg, 20, 14, 86, 66, frame='#6b5a4a', sill='#5a4a3c')
    # towel hook, right wall
    d.rectangle((296, 20, 316, 54), fill=H(TERRA))
    d.line([(302, 22), (302, 52)], fill=H('#a8583e'))
    d.line([(308, 22), (308, 52)], fill=H('#a8583e'))
    d.rectangle((292, 18, 318, 21), fill=H('#8a6550'))
    # shelf + candle, right of the tub
    d.rectangle((272, 96, 316, 101), fill=H('#5a4a3c'))
    d.rectangle((288, 74, 306, 96), fill=H('#f4e2c4'))
    d.rectangle((288, 74, 291, 96), fill=H('#ffefd4'))
    d.point((297, 70), fill=H('#ffd9a0'))
    d.point((297, 71), fill=H('#ff9f4a'))
    # tub
    d.rounded_rectangle((44, 96, 296, 158), radius=18, fill=H(TUB))
    d.rounded_rectangle((48, 100, 292, 150), radius=14, outline=H(TUB_HI), width=2)
    d.rounded_rectangle((54, 112, 286, 152), radius=12, fill=H(WATER))
    d.rounded_rectangle((54, 112, 286, 152), radius=12, outline=H(TUB_LO))
    for yy in (120, 130, 140, 148):
        for xx in range(60, 282, 16):
            if not blocked(xx, yy, rects) and not blocked(xx + 5, yy, rects):
                d.line([(xx, yy), (xx + 5, yy)], fill=H(WATER_HI))
    d.arc((50, 138, 290, 178), 20, 160, fill=H(TUB_LO))
    for fx in (68, 272):
        d.ellipse((fx - 11, 152, fx + 11, 168), fill=H(TUB_LO))
    # duck
    d.ellipse((108, 120, 166, 150), fill=H(DUCK))
    d.ellipse((110, 124, 162, 146), fill=H(DUCK_HI))
    d.ellipse((112, 106, 144, 136), fill=H(DUCK))
    d.arc((112, 106, 144, 136), 200, 330, fill=H(DUCK_HI))
    d.ellipse((110, 118, 128, 128), fill=H(BEAK))
    d.point((114, 122), fill=H('#c96f3a'))
    d.arc((130, 126, 162, 148), 20, 140, fill=H(DUCK_LO))
    # floor
    wood_floor(bg, 158, '#6b4a38', '#54382a', '#8a6048', seed=3)
    d.rounded_rectangle((116, 158, 224, 170), radius=5, fill=H(TERRA))
    # shampoo bottles on the far rim
    d.rectangle((62, 84, 74, 96), fill=H('#c96f52'))
    d.rectangle((62, 84, 65, 96), fill=H('#e08a62'))
    d.rectangle((63, 80, 73, 84), fill=H('#e8d6c0'))
    d.rectangle((80, 88, 90, 96), fill=H('#7fb8b0'))
    d.rectangle((80, 88, 82, 96), fill=H('#9fcfc6'))
    d.rectangle((81, 85, 89, 88), fill=H('#e8d6c0'))
    bokeh_sparse(bg, 7, '#5a5044', area=(90, 30, 270, 96),
                 skip=rects + [STATUS], seed=7)
    for (x, y, w, h), c in zip(rects, (DUCK, WATER, WALL, WALL)):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-bath-bubble', '泡泡浴',
        dict(family='治愈暖光', tags=['放松', '治愈', '独处'],
             story='放一缸热水，看泡泡慢慢浮上来。小黄鸭在旁边晃呀晃，'
                   '一整天的紧绷都泡软了。'),
        '热气腾腾的泡澡时间。每敲一次键，水面上就升起一串泡泡，小黄鸭高兴地晃一晃；'
        '打字投入时泡泡更多，鸭子会眯眼笑；你停手之后泡泡慢慢散掉，只剩一池温水和一点点余温。',
        ['#4a4038', '#e8d8c0', '#7fb8b0', '#ffd98a', '#fdf2e2', '#ffd9a0', '#c96f52'],
        bg, ATTRIB)
    add_sticker(s, '鸭子表情', FACE, face_art(24, 12, 'calm', 3, 8), INK, DUCK,
                caps=face_art(24, 12, 'caps', 3, 8), caps_fg='#6a4a30',
                react=face_art(24, 12, 'react', 3, 8), react_fg='#8a4a30',
                sleepy=face_art(24, 12, 'sleepy', 3, 8), sleepy_fg='#6a5038')
    add_sticker(s, '泡泡', FOAM_R, foam_art('calm'), FOAM, WATER,
                caps=foam_art('caps'), caps_fg='#ffffff',
                react=foam_art('react'), react_fg='#fff4e4',
                sleepy=foam_art('sleepy'), sleepy_fg='#d8d2c0')
    add_sticker(s, '热气', STEAM, steam_art('calm'), FOAM, WALL,
                caps=steam_art('caps'), caps_fg='#ffffff',
                react=steam_art('react'), react_fg='#ffd0dc',
                sleepy=steam_art('sleepy'))
    add_sticker(s, '小蜡烛', FLAME, bath_flame('calm'), '#ffd9a0', WALL,
                caps=bath_flame('caps'), caps_fg='#fff0c0',
                react=bath_flame('react'), react_fg='#ffdc9a',
                sleepy=bath_flame('sleepy'), sleepy_fg='#c98a4a')
    s.set_effect('bubble', trigger='key', spawn=(150, 102, 110, 14), count=5, size=3,
                 colors=['#bfeaff', '#fdf2e2', '#ffd98a'], vx=(-10, 10),
                 vy=(-48, -24), gravity=0, life_ms=2400, edge='wrap', shape='diamond')
    s.set_pulse('小蜡烛', period_ms=2400, minimum=160)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=23000)
    s.statusInk = '#ffe9c4'
    return s


def foam_art(state, w=64, h=20):
    g = Grid(w, h)
    specs = {
        'calm': ((6, 13, 6), (19, 8, 5), (32, 13, 7), (46, 9, 5), (57, 14, 6)),
        'caps': ((5, 12, 7), (16, 6, 5), (28, 12, 7), (42, 6, 6), (54, 12, 7),
                 (61, 8, 4)),
        'react': ((8, 12, 6), (22, 6, 5), (35, 13, 7), (48, 8, 6), (58, 13, 5)),
        'sleepy': ((10, 16, 5), (27, 13, 6), (43, 17, 5), (56, 14, 5)),
    }
    for (cx, cy, r) in specs[state]:
        g.disc(cx, cy, r)
    if state == 'react':
        paste(g, heart_art(), 30, 2)
    if state == 'caps':
        for (cx, cy, r) in specs[state][:3]:
            for k in range(2):
                a = k * math.pi + cx * 0.2
                g.set(cx + math.cos(a) * r * 0.5, cy + math.sin(a) * r * 0.5, '.')
    return g


def steam_art(state, w=32, h=26):
    g = Grid(w, h)
    if state == 'sleepy':
        return g
    n = {'calm': 3, 'caps': 4, 'react': 3}.get(state, 2)
    for i in range(n):
        x = 5 + i * 9
        for yy in range(3, h):
            xx = x + int(2 * math.sin(yy * 0.5 + i))
            g.set(xx, yy)
            if state == 'caps':
                g.set(xx + 3, yy)
    if state == 'react':
        paste(g, heart_art(), 12, 2)
    return g


def bath_flame(state, w=24, h=22):
    g = Grid(w, h)
    if state == 'sleepy':
        cx, top, bot = 12, 12, 20
    else:
        cx, top, bot = 12, 3, 20
    for yy in range(top, bot + 1):
        t = (yy - top) / max(1.0, bot - top)
        half = int(round(2 + 3.0 * t))
        g.hline(cx - half, cx + half, yy)
    if state in ('caps', 'react'):
        g.set(4, 6)
        g.set(20, 5)
        if state == 'react':
            g.set(18, 12)
    return g


# ---------------------------------------------------------------- hot tea scene
def build_hot_tea():
    WALL = '#3a2a2a'
    WALL_D = '#2a1e1e'
    TABLE = '#7a4f38'
    TABLE_D = '#5f3a28'
    TABLE_L = '#8a6048'
    CREAM = '#f4e2c4'
    CREAM_HI = '#fff0d8'
    CREAM_LO = '#d0b891'
    TEA = '#c9812f'
    TERRA = '#c96f52'
    GOLD = '#ffd9a0'
    INK = '#5a3a2c'
    FACE = (94, 92, 24, 14)
    TINT = (88, 106, 40, 16)
    STEAM = (152, 72, 32, 26)
    GLYPH = (202, 60, 32, 18)
    rects = [FACE, TINT, STEAM, GLYPH]

    bg = PS.blank(WALL)
    grad(bg, 0, 0, 320, 40, WALL_D, WALL, bands=5)
    # evening window
    grad(bg, 23, 17, 66, 60, '#1e2740', '#3a3450', bands=5)
    starfield(bg, 9, '#e8ecff', seed=5, area=(26, 20, 84, 74), skip=rects)
    PS.moon(bg, 76, 28, 5, '#f7f0dd', '#d8cfae')
    PS.window_frame(bg, 16, 14, 96, 80, frame='#6b4a3e', sill='#4a3430')
    curtain(bg, 6, 8, 12, 84, '#4a2f34', '#39202a')
    d = ImageDraw.Draw(bg)
    # table
    d.rectangle((0, 124, 319, 171), fill=H(TABLE))
    d.line([(0, 124), (319, 124)], fill=H(TABLE_L))
    for yy in (134, 146, 158, 170):
        d.line([(0, yy), (319, yy)], fill=H(TABLE_D))
    for xx, yy in ((18, 130), (88, 141), (160, 133), (236, 151), (54, 163),
                   (288, 137), (120, 168)):
        d.line([(xx, yy), (xx + 28, yy)], fill=H('#8a5f44'))
    # shelf, jars + picture
    d.rectangle((240, 84, 312, 89), fill=H('#4a3430'))
    for bx, bh, bc in ((246, 18, '#8a5a4a'), (262, 12, '#a8764e'),
                       (276, 16, '#6f4c5a'), (292, 10, '#8a5a4a')):
        d.rectangle((bx, 88 - bh, bx + 11, 87), fill=H(bc))
    d.rectangle((198, 34, 236, 58), fill=H('#4a3430'))
    d.rectangle((202, 38, 232, 54), fill=H('#5a4048'))
    d.point((217, 45), fill=H(GOLD))
    # teapot: body, spout, handle, lid
    d.ellipse((72, 120, 140, 130), fill=H('#5f3a28'))
    d.ellipse((75, 78, 135, 124), fill=H(CREAM))
    d.ellipse((79, 82, 126, 118), fill=H(CREAM_HI))
    d.arc((75, 94, 135, 124), 20, 130, fill=H(CREAM_LO))
    d.arc((75, 84, 135, 118), 190, 300, fill=H('#fff6e6'))
    # spout: thick and attached to the belly
    d.line([(86, 98), (64, 84)], fill=H(CREAM), width=7)
    d.line([(86, 100), (68, 88)], fill=H(CREAM_HI), width=2)
    d.ellipse((58, 78, 74, 94), fill=H(CREAM))
    d.ellipse((60, 80, 70, 90), fill=H(CREAM_HI))
    # handle
    d.arc((126, 86, 154, 116), 270, 90, fill=H(CREAM))
    d.arc((129, 89, 151, 113), 270, 90, fill=H(CREAM_LO))
    # lid + knob
    d.ellipse((92, 70, 118, 88), fill=H(CREAM))
    d.ellipse((94, 72, 116, 84), fill=H(CREAM_HI))
    d.ellipse((99, 60, 111, 72), fill=H(CREAM))
    d.ellipse((101, 62, 109, 70), fill=H(CREAM_HI))
    d.point((104, 66), fill=H(CREAM_LO))
    # teacup + saucer
    d.ellipse((160, 100, 190, 124), fill=H(CREAM))
    d.ellipse((162, 102, 188, 120), fill=H(CREAM_LO))
    d.ellipse((165, 102, 185, 112), fill=H(TEA))
    d.arc((180, 104, 196, 118), 270, 90, fill=H(CREAM))
    d.ellipse((156, 118, 194, 128), fill=H(CREAM_LO))
    # cookies on a small plate
    d.ellipse((196, 114, 236, 126), fill=H(CREAM_LO))
    for cx, cy in ((204, 116), (216, 118), (226, 115)):
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 3), fill=H('#c98a52'))
        d.point((cx - 1, cy - 1), fill=H('#8a5a34'))
        d.point((cx + 2, cy + 1), fill=H('#8a5a34'))
    # spoon + folded napkin + a book on the table
    d.polygon([(18, 126), (46, 126), (42, 132), (22, 132)], fill=H('#e8d6c0'))
    d.line([(26, 129), (40, 129)], fill=H('#d0b8a0'))
    d.ellipse((150, 128, 180, 134), fill=H('#c9b294'))
    d.ellipse((152, 129, 176, 133), fill=H('#e8d6c0'))
    d.rectangle((252, 126, 306, 134), fill=H('#8a5a4a'))
    d.rectangle((254, 123, 304, 127), fill=H('#e8d6c0'))
    d.line([(254, 127), (304, 127)], fill=H('#d0b8a0'))
    bokeh_sparse(bg, 8, '#4a3330', area=(20, 50, 240, 116),
                 skip=rects + [STATUS], seed=8)
    for (x, y, w, h), c in zip(rects, (CREAM, CREAM, WALL, WALL)):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-hot-tea', '热茶',
        dict(family='治愈暖光', tags=['暖手', '夜话', '陪伴'],
             story='晚饭后给自己泡一壶热茶。茶雾一圈圈升起来，'
                   '屋子里的冷气就散了，连心里那点毛躁也被熨平。'),
        '晚饭后给自己泡一壶热茶。按键时壶嘴和杯口会飘起暖色茶雾，茶叶的香气像跟着光一起上升；'
        '敲得久了茶壶会开心得脸红；你离开一阵，热气散去，茶壶也安静下来等你回来。',
        ['#2a1e1e', '#3a2a2a', '#7a4f38', '#f4e2c4', '#c9812f', '#ffd9a0', '#c96f52'],
        bg, ATTRIB)
    add_sticker(s, '茶壶表情', FACE, face_art(24, 14, 'calm', 4, 9), INK, CREAM,
                caps=face_art(24, 14, 'caps', 4, 9), caps_fg='#6a4636',
                react=face_art(24, 14, 'react', 4, 9), react_fg='#8a4a3a',
                sleepy=face_art(24, 14, 'sleepy', 4, 9), sleepy_fg='#6a4a40')
    add_sticker(s, '茶壶暖色', TINT, glow_art(40, 16, 2), '#f4e2c4', CREAM,
                caps=glow_art(40, 16, 3), caps_fg='#fff6e6',
                react=glow_art(40, 16, 3), react_fg='#ffc4a0',
                sleepy=glow_art(40, 16, 0), sleepy_fg='#c9b08a')
    add_sticker(s, '茶雾', STEAM, steam_art('calm'), '#f4e2c4', WALL,
                caps=steam_art('caps'), caps_fg='#fff0d8',
                react=steam_art('react'), react_fg='#ffc4d0',
                sleepy=steam_art('sleepy'))
    add_sticker(s, '晚安符号', GLYPH, glyph_art('calm'), GOLD, WALL,
                caps=glyph_art('caps'), caps_fg=GOLD,
                react=glyph_art('react'), react_fg='#f79aa8',
                sleepy=glyph_art('sleepy'), sleepy_fg='#c9b8d8')
    s.set_effect('ember', trigger='key', spawn=(154, 64, 34, 12), count=4, size=2,
                 colors=['#ffd9a0', '#ff9f6a', '#f4e2c4'], vx=(-10, 10),
                 vy=(-40, -18), gravity=-4, life_ms=2100, edge='die')
    s.set_pulse('茶壶暖色', period_ms=3000, minimum=180)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=25000)
    s.statusInk = '#ffe9c4'
    return s


# --------------------------------------------------------------- cloud hug scene
def build_cloud_hug():
    SKY = '#241f3a'
    SKY_L = '#2e2850'
    CLOUD = '#f6e8dc'
    CLOUD_HI = '#fdf4ea'
    CLOUD_LO = '#e2d4d2'
    MOON = '#ffe6a8'
    MOON_HI = '#fff2c8'
    MOON_LO = '#e8c47a'
    HILL = '#171330'
    HILL_D = '#100d20'
    STAR = '#fff3cf'
    GOLD = '#ffd9a0'
    INK = '#6a4a44'
    FACE = (102, 64, 24, 16)
    TINT = (120, 80, 40, 16)
    GLYPH = (148, 26, 32, 18)
    MOON_R = (184, 66, 24, 14)
    rects = [FACE, TINT, GLYPH, MOON_R]

    bg = PS.blank(SKY)
    starfield(bg, 62, STAR, seed=6, area=(0, 0, 320, 152),
              skip=rects + [STATUS], size2=7)
    d = ImageDraw.Draw(bg)
    for (x, y, r) in ((52, 24, 2), (206, 40, 2), (286, 62, 2), (120, 16, 2)):
        d.line([(x - r, y), (x + r, y)], fill=H(STAR))
        d.line([(x, y - r), (x, y + r)], fill=H(STAR))
    soft_cloud(bg, 300, 118, 1.3, SKY_L, rects + [STATUS])
    sk = rects + [STATUS]
    d = ImageDraw.Draw(bg)
    # the hugged moon (the cloud arms wrap its left side)
    mcx, mcy, mr = 194, 72, 16
    for yy in range(mcy - mr, mcy + mr + 1):
        half = int(round(math.sqrt(max(0.0, mr * mr - (yy - mcy) ** 2))))
        d.line([(mcx - half, yy), (mcx + half, yy)], fill=H(MOON))
    for (ox, oy, rr, cc) in ((-9, -8, 6, MOON_HI), (-4, -11, 4, MOON_HI),
                             (7, 6, 5, MOON_LO), (2, 10, 4, MOON_LO),
                             (-8, 6, 3, MOON_LO)):
        blob(bg, mcx + ox, mcy + oy, rr, rr, cc, sk)
    d = ImageDraw.Draw(bg)
    # fluffy cloud body
    for (cx, cy, r) in ((112, 82, 17), (128, 72, 15), (146, 80, 15), (96, 90, 11),
                        (160, 88, 12), (132, 92, 14), (118, 94, 12)):
        blob(bg, cx, cy, r, r, CLOUD, sk)
    for (cx, cy, r) in ((128, 66, 8), (146, 74, 8), (160, 84, 7)):
        blob(bg, cx, cy, r, r, CLOUD_HI, sk)
    for (cx, cy, r) in ((104, 100, 10), (132, 102, 12), (156, 100, 9)):
        blob(bg, cx, cy, r, int(r * 0.7), CLOUD_LO, sk)
    # arms hugging the moon
    blob(bg, 175, 62, 9, 8, CLOUD, sk)
    blob(bg, 175, 84, 9, 8, CLOUD, sk)
    blob(bg, 170, 73, 8, 9, CLOUD, sk)
    blob(bg, 176, 61, 5, 4, CLOUD_HI, sk)
    blob(bg, 168, 96, 8, 5, CLOUD, sk)
    # hills with tiny warm windows
    d = ImageDraw.Draw(bg)
    d.polygon([(0, 172), (0, 152), (36, 144), (84, 150), (132, 144), (188, 152),
               (240, 146), (292, 152), (319, 146), (319, 172)], fill=H(HILL))
    d.polygon([(0, 172), (0, 160), (60, 154), (130, 160), (200, 154), (270, 161),
               (319, 156), (319, 172)], fill=H(HILL_D))
    for x, y in ((38, 156), (56, 161), (118, 158), (206, 163), (268, 158),
                 (150, 164), (300, 162)):
        d.rectangle((x, y, x + 2, y + 2), fill=H(GOLD))
    for x, y in ((86, 138), (286, 138)):
        d.polygon([(x, y), (x - 5, y + 12), (x + 5, y + 12)], fill=H(HILL_D))
    for (x, y, w, h), c in zip(rects, (CLOUD, CLOUD, SKY, MOON)):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-cloud-hug', '云朵抱抱',
        dict(family='治愈暖光', tags=['拥抱', '晚安', '柔软'],
             story='一朵云把月亮抱进怀里。夜里所有的疲惫，'
                   '都被它轻轻接住，像被好好拍了一下背。'),
        '把月亮抱进怀里的云朵。每敲一下键，就会有软软的暖色云絮落下，像被轻轻拍了一下背；'
        '敲得投入时云朵会脸红、把月亮抱得更紧，然后打个哈欠一起睡着。',
        ['#100d20', '#171330', '#241f3a', '#f6e8dc', '#ffe6a8', '#ffd9a0', '#f9d9d2'],
        bg, ATTRIB)
    add_sticker(s, '云朵表情', FACE, face_art(24, 16, 'calm', 5, 11), INK, CLOUD,
                caps=face_art(24, 16, 'caps', 5, 11), caps_fg='#7a5650',
                react=face_art(24, 16, 'react', 5, 11), react_fg='#9a5a5a',
                sleepy=face_art(24, 16, 'sleepy', 5, 11), sleepy_fg='#7a5c58')
    add_sticker(s, '云朵脸色', TINT, glow_art(40, 16, 2), '#f6e8dc', CLOUD,
                caps=glow_art(40, 16, 3), caps_fg='#fff2e8',
                react=glow_art(40, 16, 3), react_fg='#ffc4bc',
                sleepy=glow_art(40, 16, 0), sleepy_fg='#cfc0bb')
    add_sticker(s, '晚安符号', GLYPH, glyph_art('calm'), GOLD, SKY,
                caps=glyph_art('caps'), caps_fg=GOLD,
                react=glyph_art('react'), react_fg='#f79aa8',
                sleepy=glyph_art('sleepy'), sleepy_fg='#c9b8d8')
    add_sticker(s, '月亮颜色', MOON_R, moon_glow('calm'), '#ffe6a8', MOON,
                caps=moon_glow('caps'), caps_fg='#fff2c8',
                react=moon_glow('react'), react_fg='#ffd9a0',
                sleepy=moon_glow('sleepy'), sleepy_fg='#c9a864')
    s.set_effect('snow', trigger='key', spawn=(100, 34, 60, 14), count=5, size=2,
                 colors=['#fff3e0', '#ffe1c4', '#e8d9ff'], vx=(-16, 16),
                 vy=(18, 34), gravity=0, life_ms=4200, edge='wrap', shape='square')
    s.set_pulse('云朵脸色', period_ms=3200, minimum=190)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=21000)
    s.statusInk = '#fff3cf'
    return s


def moon_glow(state, w=24, h=14):
    g = Grid(w, h)
    if state == 'sleepy':
        return g
    rx = 10 if state != 'caps' else 11
    for yy in range(h):
        for xx in range(w):
            if ((xx - w / 2.0) / rx) ** 2 + ((yy - h / 2.0) / 6.0) ** 2 <= 1.0:
                g.set(xx, yy, '#')
    return g


# ----------------------------------------------------------------- candle scene
def build_candle():
    WALL = '#241a22'
    WALL_D = '#1a1218'
    TABLE = '#5a3a2c'
    TABLE_D = '#432a1e'
    TABLE_L = '#6b4632'
    CREAM = '#f4dfb8'
    CREAM_HI = '#ffefd0'
    CREAM_LO = '#d8b98c'
    FLAME = '#ffcf6a'
    GOLD = '#ffd9a0'
    MOON = '#dce6ff'
    PLUM = '#4a2f34'
    INK = '#5a3a2a'
    FACE = (152, 98, 24, 14)
    FLAME_R = (152, 52, 32, 30)
    SMOKE = (184, 44, 32, 22)
    MOON_R = (34, 28, 24, 24)
    rects = [FACE, FLAME_R, SMOKE, MOON_R]

    bg = PS.blank(WALL)
    grad(bg, 0, 0, 320, 40, WALL_D, WALL, bands=5)
    # window with flat glass (moon sticker lives there)
    patch(bg, 23, 17, 64, 56, '#141a30')
    starfield(bg, 11, '#e8ecff', seed=9, area=(25, 19, 86, 72), skip=rects)
    PS.window_frame(bg, 20, 14, 86, 72, frame='#4a3430', sill='#3a2620')
    d = ImageDraw.Draw(bg)
    # table
    d.rectangle((0, 126, 319, 171), fill=H(TABLE))
    d.line([(0, 126), (319, 126)], fill=H(TABLE_L))
    for yy in (136, 148, 160):
        d.line([(0, yy), (319, yy)], fill=H(TABLE_D))
    for xx, yy in ((14, 131), (86, 143), (160, 135), (250, 153), (58, 165),
                   (300, 141)):
        d.line([(xx, yy), (xx + 26, yy)], fill=H(TABLE_L))
    # shelf with books
    d.rectangle((240, 92, 314, 97), fill=H('#4a3430'))
    for bx, bh, bc in ((246, 15, '#8a5a4a'), (256, 11, '#6f4c5a'),
                       (267, 17, '#a8764e'), (280, 12, '#8a5a4a'),
                       (291, 15, '#6f4c5a')):
        d.rectangle((bx, 91 - bh, bx + 8, 90), fill=H(bc))
    # candle: saucer, wax column with drips, wick
    d.ellipse((132, 116, 196, 132), fill=H(CREAM_LO))
    d.ellipse((136, 117, 192, 128), fill=H(CREAM))
    d.rectangle((148, 86, 180, 124), fill=H(CREAM))
    d.rectangle((148, 86, 154, 124), fill=H(CREAM_HI))
    d.rectangle((174, 86, 180, 124), fill=H(CREAM_LO))
    d.ellipse((148, 80, 180, 92), fill=H(CREAM))
    d.ellipse((151, 82, 177, 90), fill=H(CREAM_HI))
    for (dx, dy, dh) in ((152, 88, 8), (160, 88, 12), (172, 88, 6), (177, 88, 10)):
        for yy in range(dy, dy + dh):
            d.point((dx, yy), fill=H(CREAM_HI))
        d.point((dx, dy + dh), fill=H(CREAM_LO))
    d.point((164, 86), fill=H(CREAM_LO))
    d.line([(163, 80), (163, 84)], fill=H('#4a3020'))
    # little things on the table: mug, book, matchbox
    d.rectangle((92, 112, 112, 126), fill=H('#c96f52'))
    d.rectangle((92, 112, 95, 126), fill=H('#e08a62'))
    d.rectangle((112, 116, 118, 122), fill=H('#c96f52'))
    d.rectangle((206, 118, 240, 126), fill=H('#8a5a4a'))
    d.rectangle((208, 115, 238, 119), fill=H('#e8d6c0'))
    d.rectangle((246, 120, 264, 126), fill=H('#d99a52'))
    d.rectangle((248, 117, 262, 121), fill=H('#e8b06a'))
    # warm light dots on the wall around the flame
    bokeh_sparse(bg, 18, '#4a3230', area=(120, 30, 250, 120),
                 skip=rects + [STATUS], seed=5, rmax=1)
    pool(bg, 162, 130, 58, 9, GOLD, 0.42)
    for (x, y, w, h), c in zip(rects, (CREAM, WALL, WALL, '#141a30')):
        patch(bg, x, y, w, h, c)

    s = PS.Scheme(
        'px6-candle', '小蜡烛',
        dict(family='治愈暖光', tags=['安静', '深夜', '微光'],
             story='停电的夜晚，桌上点着一支小蜡烛。'
                   '火苗一晃一晃，把墙照成蜂蜜色，好像整间屋子都在轻轻呼吸。'),
        '停电的夜晚，桌上点着一支小蜡烛。每敲一次键，火苗就跟着轻轻晃一下，几点火星飘上去；'
        '敲得多了烛光会亮起来、像在对你眨眼；你停手以后火苗缩成小小一颗，只剩一缕白烟。',
        ['#141a30', '#241a22', '#5a3a2c', '#f4dfb8', '#ffcf6a', '#ffd9a0', '#dce6ff'],
        bg, ATTRIB)
    add_sticker(s, '蜡烛表情', FACE, face_art(24, 14, 'calm', 4, 9), INK, CREAM,
                caps=face_art(24, 14, 'caps', 4, 9), caps_fg='#6a4636',
                react=face_art(24, 14, 'react', 4, 9), react_fg='#8a4a3a',
                sleepy=face_art(24, 14, 'sleepy', 4, 9), sleepy_fg='#6a4a40')
    add_sticker(s, '火苗', FLAME_R, flame_with_glow('calm'), FLAME, WALL,
                caps=flame_with_glow('caps'), caps_fg='#ffdc8a',
                react=flame_with_glow('react'), react_fg='#ffb25a',
                sleepy=flame_with_glow('sleepy'), sleepy_fg='#c98a4a')
    add_sticker(s, '火星与烟', SMOKE, smoke_art('calm'), GOLD, WALL,
                caps=smoke_art('caps'), caps_fg='#ffdc8a',
                react=smoke_art('react'), react_fg='#ff9fae',
                sleepy=smoke_art('sleepy'), sleepy_fg='#9a8c8c')
    add_sticker(s, '窗边的月亮', MOON_R, moon_art('calm'), MOON, '#141a30',
                caps=moon_art('caps'), caps_fg='#f4f0ff',
                react=moon_art('react'), react_fg='#f4f0ff',
                sleepy=moon_art('sleepy'), sleepy_fg='#a8b4d8')
    s.set_effect('ember', trigger='key', spawn=(152, 42, 32, 14), count=4, size=2,
                 colors=['#ffcf6a', '#ff9f4a', '#ffd9a0'], vx=(-14, 14),
                 vy=(-46, -22), gravity=-5, life_ms=2200, edge='die')
    s.set_pulse('火苗', period_ms=1800, minimum=140)
    s.set_reaction(reactHoldMs=800, sleepyAfterMs=20000)
    s.statusInk = '#ffe9c4'
    return s


def flame_with_glow(state, w=32, h=30):
    g = Grid(w, h)
    if state == 'sleepy':
        cx, top, bot = 16, 18, 28
    else:
        cx, top, bot = 16, 4, 28
    for yy in range(top, bot + 1):
        t = (yy - top) / max(1.0, bot - top)
        half = int(round(1 + 4.6 * (t ** 0.55) * (1.0 - 0.22 * t)))
        sway = int(round(1.2 * math.sin(yy * 0.55)))
        g.hline(cx + sway - half, cx + sway + half, yy)
    if state in ('caps', 'react'):
        for (x, y) in ((6, 7), (26, 5), (4, 15), (27, 13)):
            g.set(x, y)
        if state == 'react':
            g.set(11, 2)
            g.set(21, 1)
    return g


def smoke_art(state, w=32, h=22):
    g = Grid(w, h)
    if state == 'caps':
        plus(g, 24, 5, 2)
        plus(g, 6, 9, 1)
    elif state == 'react':
        paste(g, heart_art(), 18, 3)
        plus(g, 6, 6, 1)
        plus(g, 26, 15, 1)
    elif state == 'sleepy':
        for yy in range(2, 20):
            xx = 15 + int(2.4 * math.sin(yy * 0.55))
            g.set(xx, yy)
            if yy < 10:
                g.set(xx + 1, yy)
    return g


# ------------------------------------------------------------------------- main
def add_sticker(s, name, rect, calm, fg, bg, **kw):
    """Sticker helper taking an (x, y, w, h) rectangle."""
    return s.sticker(name, rect[0], rect[1], calm, fg, bg, **kw)


BUILDERS = (
    build_soft_lamp,
    build_blanket_cat,
    build_sunbeam,
    build_bath_bubble,
    build_hot_tea,
    build_cloud_hug,
    build_candle,
)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for build in BUILDERS:
        scheme = build()
        if only and only not in scheme.slug:
            continue
        d, meta = scheme.save()
        print('%s -> %s  masks %dB enc/%dB dec  layers %d' % (
            scheme.slug, d, meta['masks']['encodedBytes'],
            meta['masks']['decodedBytes'], len(meta['layers'])))


if __name__ == '__main__':
    main()
