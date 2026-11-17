"""px6-romance: nine interactive pixel schemes for the 浪漫心动 family.

Each scheme is a flat 320x172 background scene plus 2-5 single-colour sticker
sprites.  A sticker's 1-bit mask may change over the four moods:

    calm   baked into the uploaded GIF
    caps   a colour / variant shift (petals go vivid, a heart lights up)
    react  the love reaction (blush, a heart, the couple leaning in)
    sleepy a soft night version (closed eyes, dim light, fewer lights)

Run:
    .venv\\Scripts\\python.exe tools\\schemes\\px6_romance.py
    .venv\\Scripts\\python.exe tools\\schemes\\px6_romance.py px6-heartbeat --sheet build/romance-3.png
    .venv\\Scripts\\python.exe tools\\verify_schemes.py --glob 'px6-sakura-love' --dir build/design-gallery

No hardware access.  SPDX-License-Identifier: MIT.
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

W, H = PS.SIZE
ATTRIBUTION = '原创像素图形，全部由 tools/schemes/px6_romance.py 程序绘制'
FAMILY = '浪漫心动'
INK = '#ffe6f2'

# ---------------------------------------------------------------- tiny helpers
def rgb(c):
    return PS.hexrgb(c)


def flat(im, box, colour):
    """Reserve one flat rectangle; the firmware repaints stickers with this colour."""
    ImageDraw.Draw(im).rectangle((box[0], box[1], box[0] + box[2] - 1, box[1] + box[3] - 1),
                                 fill=rgb(colour))


def put(g, rows, ox=0, oy=0):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == '#':
                g.set(ox + x, oy + y, '#')
    return g


def sparkle(d, x, y, r, colour):
    c = rgb(colour)
    for i in range(1, r + 1):
        for px, py in ((x + i, y), (x - i, y), (x, y + i), (x, y - i)):
            if 0 <= px < W and 0 <= py < H:
                d.point((px, py), fill=c)
    if 0 <= x < W and 0 <= y < H:
        d.point((x, y), fill=c)


def dither_fade(im, y0, y1, colour, dens_from=7, dens_to=2, parity=0):
    """Stipple a colour in from the top of a band: a cheap pixel-art glow."""
    d = ImageDraw.Draw(im)
    c = rgb(colour)
    n = max(1, y1 - y0 - 1)
    for i, y in enumerate(range(int(y0), int(y1))):
        k = i / n
        dens = max(1, int(round(dens_from + (dens_to - dens_from) * k)))
        if dens <= 1:
            d.line([(0, y), (W, y)], fill=c)
        else:
            for x in range(W):
                if (x * 5 + y * 3 + parity) % dens == 0:
                    d.point((x, y), fill=c)


def dither_disc(im, cx, cy, r, colour, dens=3, parity=0):
    d = ImageDraw.Draw(im)
    c = rgb(colour)
    for y in range(int(cy - r), int(cy + r) + 1):
        if not 0 <= y < H:
            continue
        for x in range(int(cx - r), int(cx + r) + 1):
            if not 0 <= x < W:
                continue
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (x * 5 + y * 3 + parity) % dens == 0:
                d.point((x, y), fill=c)


def halo(im, cx, cy, r_in, r_out, colour, step=3, skip=2):
    """Dotted concentric halo (soft pixel-art light bloom)."""
    d = ImageDraw.Draw(im)
    c = rgb(colour)
    for i, r in enumerate(range(int(r_in), int(r_out), step)):
        n = max(12, int(r * 3.9))
        for k in range(n):
            if (k + i) % skip:
                continue
            a = math.tau * k / n
            x, y = round(cx + math.cos(a) * r), round(cy + math.sin(a) * r)
            if 0 <= x < W and 0 <= y < H:
                d.point((x, y), fill=c)


def stars(im, count, area, colours, seed=1, cross=8):
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    for i in range(count):
        x, y = rng.randrange(area[0], area[2]), rng.randrange(area[1], area[3])
        d.point((x, y), fill=rgb(rng.choice(colours)))
        if i % cross == 0:
            sparkle(d, x, y, 1, rng.choice(colours))


def ridge(im, y, colour, amp=12, seed=1):
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    pts = [(0, H)]
    x = 0
    while x < W:
        step = rng.randrange(26, 58)
        pts.append((x + step // 2, y - rng.randrange(0, amp)))
        pts.append((min(W, x + step), y + rng.randrange(0, amp // 2)))
        x += step
    pts.append((W, H))
    d.polygon(pts, fill=rgb(colour))


def limb(im, pts, w, colour, hi=None):
    d = ImageDraw.Draw(im)
    d.line(pts, fill=rgb(colour), width=w, joint='curve')
    if hi:
        d.line([(x, y - max(1, w // 3)) for x, y in pts], fill=rgb(hi), width=max(1, w // 3))


def blossom(im, x, y, r, light, mid, deep):
    """Small 5-petal blossom with two tones and a bright core."""
    d = ImageDraw.Draw(im)
    for k in range(5):
        a = -math.pi / 2 + k * math.tau / 5
        px, py = x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.55
        rr = max(0.8, r * 0.55)
        d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=rgb(mid))
        d.point((int(round(px + r * 0.25)), int(round(py + r * 0.2))), fill=rgb(deep))
    cr = max(0.8, r * 0.38)
    d.ellipse((x - cr, y - cr, x + cr, y + cr), fill=rgb(light))


def bokeh(im, points, colour, r=2):
    d = ImageDraw.Draw(im)
    for x, y in points:
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgb(colour))


# ------------------------------------------------------------------- sprites
def person(g, cx, ground, h, head_dx=0, skirt=False):
    """Pixel silhouette person; returns the head centre (x, y, r).

    ``head_dx`` leans the head/torso while the feet stay planted, which is how the
    couples lean towards each other.
    """
    hr = max(2, int(round(h * 0.15)))
    hx = int(round(cx + head_dx))
    hy = int(ground - h + hr)
    g.disc(hx, hy, hr)
    neck = hy + hr
    if skirt:
        for y in range(neck, ground + 1):
            t = (y - neck) / max(1.0, ground - neck)
            half = int(round(hr * (1.0 + 2.0 * max(0.0, t - 0.32) / 0.68)))
            x0 = int(round(cx + head_dx * (1 - t)))
            g.hline(x0 - half, x0 + half, y)
    else:
        hip = int(ground - max(2, round(h * 0.42)))
        for y in range(neck, hip + 1):
            t = (y - neck) / max(1.0, hip - neck)
            half = int(round(hr * (1.0 + 0.4 * t)))
            x0 = int(round(cx + head_dx * 0.5 * (1 - t)))
            g.hline(x0 - half, x0 + half, y)
        lw = max(1, hr // 2)
        for y in range(hip, ground + 1):
            lx = int(round(cx - hr * 0.55))
            rx = int(round(cx + hr * 0.55))
            g.hline(lx - lw + 1, lx, y)
            g.hline(rx, rx + lw - 1, y)
    return hx, hy, hr


def set_eyes(g, head, mode='open'):
    hx, hy, hr = head
    if mode == 'open':
        g.set(hx - 1, hy + 1, '.')
        g.set(hx + 1, hy + 1, '.')
    elif mode == 'closed':
        g.hline(hx - 1, hx + 1, hy + 1, '.')
    elif mode == 'shy':
        g.set(hx - 2, hy + 1, '.')
        g.set(hx, hy + 1, '.')
        g.set(hx + 2, hy + 1, '.')


def heart_shape(g, cx, cy, half, ch='#'):
    """Filled heart from two lobes + a taper; works at any size."""
    lobe = max(1, int(round(half * 0.58)))
    g.disc(cx - lobe - 1, cy - lobe, lobe, ch)
    g.disc(cx + lobe + 1, cy - lobe, lobe, ch)
    g.rect(cx - 2 * lobe - 1, cy - lobe, cx + 2 * lobe + 1, cy, ch)
    rows = max(2, int(round(half * 0.85)))
    top = cy - lobe
    for i in range(rows + 1):
        w = int(round((2 * lobe + 1) * (1 - i / (rows + 1.0)) ** 0.8))
        g.hline(cx - w, cx + w, top + i + lobe, ch)


HEART_S = ('.##...##.', '#########', '#########', '.#######.',
           '..#####..', '...###...', '....#....')
HEART_M = ('..##.....##..', '.#####.#####.', '#############', '#############',
           '.###########.', '.###########.', '..#########..', '...#######...',
           '....#####....', '.....###.....', '......#......')
HEART_L = ('..####.....####....', '.######...######...', '###################',
           '###################', '###################', '.#################.',
           '.#################.', '..###############..', '...#############...',
           '....###########....', '.....#########.....', '......#######......',
           '.......#####.......', '........###........', '.........#.........')


def heart_grid(w, h, rows, ox=None, oy=None):
    g = Grid(w, h)
    if not rows:
        return g
    rw, rh = len(rows[0]), len(rows)
    put(g, rows, (w - rw) // 2 if ox is None else ox, (h - rh) // 2 if oy is None else oy)
    return g


def flame_grid(w, h, state='lit'):
    """Candle / lamp flame: one solid colour, height depends on the mood."""
    g = Grid(w, h)
    cx = w // 2
    if state == 'tiny':
        g.disc(cx, h - 3, 1)
        g.set(cx, h - 6)
        return g
    if state == 'none':
        return g
    g.disc(cx, h - 4, max(1, min(2, w // 4)))
    for i in range(h - 5, 1, -1):
        x = cx + (1 if (i // 2) % 2 else 0) - (1 if state == 'wave' and i % 3 == 0 else 0)
        g.set(x, i)
    g.set(cx, 1)
    return g


def candle_body(im, x, y, w, h, body, wax_hi, wick):
    d = ImageDraw.Draw(im)
    d.rectangle((x, y + 6, x + w - 1, y + h - 1), fill=rgb(body))
    d.line([(x + 1, y + 7), (x + 1, y + h - 2)], fill=rgb(wax_hi))
    d.point((x + w // 2, y + 5), fill=rgb(wick))


# =============================================================== 1. 樱花告白
SAK_SKY = '#2c2752'
SAK_GROUND = '#2c2446'
SAK_PATH = '#3a2f56'
SAK_BRANCH_R = (102, 42, 78, 34)
SAK_GIRL_R = (145, 128, 28, 38)
SAK_BOY_R = (173, 128, 28, 38)
SAK_HEART_R = (200, 80, 20, 18)
SAK_MOON_R = (240, 62, 26, 26)


def sakura_branch(state):
    g = Grid(SAK_BRANCH_R[2], SAK_BRANCH_R[3])          # 78 x 34
    g.line(-1, 28, 22, 22, '#', 3)
    g.line(22, 22, 46, 18, '#', 2)
    g.line(46, 18, 77, 10, '#', 2)
    g.line(20, 22, 30, 11, '#', 2)
    g.line(30, 11, 37, 6, '#', 1)
    g.line(44, 18, 54, 8, '#', 2)
    g.line(54, 8, 60, 4, '#', 1)
    g.line(62, 15, 68, 20, '#', 1)

    def bloom(cx, cy, r=2):
        g.disc(cx, cy, r)

    def petal(cx, cy):
        g.rect(cx, cy, cx + 2, cy + 1)

    spots = {'calm': ((13, 12, 2), (24, 6, 2), (36, 11, 3), (49, 5, 2),
                      (60, 4, 2), (68, 12, 2), (7, 20, 2), (72, 14, 1)),
             'react': ((12, 11, 2), (22, 5, 2), (30, 12, 2), (38, 6, 3), (47, 4, 2),
                       (56, 6, 2), (64, 2, 2), (72, 11, 1), (5, 19, 2), (18, 18, 2)),
             'sleepy': ((16, 13, 2), (40, 10, 2), (62, 6, 2))}[state]
    for cx, cy, r in spots:
        bloom(cx, cy, r)
    if state == 'react':
        for cx, cy in ((9, 25), (30, 25), (48, 22), (65, 20), (56, 26), (22, 26)):
            petal(cx, cy)
    else:
        for cx, cy in ((26, 26), (60, 24)):
            petal(cx, cy)
    return g


def sakura_girl(state):
    g = Grid(SAK_GIRL_R[2], SAK_GIRL_R[3])              # 28 x 38
    base = 36
    if state == 'react':
        h = person(g, 13, base, 30, head_dx=7, skirt=True)
        set_eyes(g, h, 'shy')
    elif state == 'sleepy':
        h = person(g, 13, base, 27, head_dx=6, skirt=True)
        set_eyes(g, h, 'closed')
    else:
        h = person(g, 13, base, 30, skirt=True)
        set_eyes(g, h, 'open')
    hx, hy, hr = h
    g.disc(hx - 2, hy - hr, 2)                          # hair bun
    for y in range(hy + hr - 1, hy + hr + 6):           # hair falling to the shoulders
        g.set(hx - hr - 1, y, '#')
        g.set(hx + hr + 1, y, '#')
    g.line(hx + hr, hy + hr + 4, hx + hr + 2, hy + hr + 9, '#', 1)
    return g


def sakura_boy(state):
    g = Grid(SAK_BOY_R[2], SAK_BOY_R[3])                # 28 x 38
    base = 36
    if state == 'react':
        h = person(g, 15, base, 33, head_dx=-9)
        set_eyes(g, h, 'closed')
        g.line(h[0] - 4, h[1] + 7, h[0] - 7, h[1] + 10, '#', 2)   # arm round her
    elif state == 'sleepy':
        h = person(g, 15, base, 31, head_dx=-8)
        set_eyes(g, h, 'closed')
    else:
        h = person(g, 15, base, 33)
        set_eyes(g, h, 'open')
    return g


def sakura_heart(state):
    rows = {'calm': (), 'caps': HEART_S, 'react': HEART_M, 'sleepy': ()}[state]
    return heart_grid(SAK_HEART_R[2], SAK_HEART_R[3], rows)


def sakura_moon(state):
    g = Grid(SAK_MOON_R[2], SAK_MOON_R[3])              # 26 x 26
    g.disc(13, 13, 10)
    for cx, cy, r in ((9, 9, 2), (17, 14, 2), (10, 18, 1)):
        g.disc(cx, cy, r, '.')
    if state == 'sleepy':                                # thin crescent
        for y in range(26):
            for x in range(26):
                if (x - 17) ** 2 + (y - 10) ** 2 < 118:
                    g.set(x, y, '.')
    return g


def sakura_bg():
    bg = Image.new('RGB', (W, H), rgb(SAK_SKY))
    d = ImageDraw.Draw(bg)
    # dusk horizon glow: stippled rose light seeping up from behind the hill
    dither_fade(bg, 86, 116, '#5a3a66', dens_from=9, dens_to=2, parity=1)
    dither_fade(bg, 100, 122, '#8a4c62', dens_from=11, dens_to=3, parity=2)
    stars(bg, 40, (4, 6, 316, 104), ['#f7f0dd', '#e8d8ff', '#ffd9e8'], seed=5)
    # ground: hill silhouette + the stone path the couple stands on
    ridge(bg, 112, '#332a50', amp=13, seed=7)
    d.rectangle((0, 118, W - 1, H - 1), fill=rgb(SAK_GROUND))
    d.line([(0, 118), (W - 1, 118)], fill=rgb('#3d3158'))
    d.polygon([(96, 172), (128, 136), (146, 128), (200, 128), (222, 140),
               (254, 172)], fill=rgb(SAK_PATH))
    for y in range(132, 172, 7):
        d.line([(104 + (y - 132) // 4, y), (248 - (y - 132) // 4, y)],
               fill=rgb('#443a62'))
    # a wooden bench on the left under the branch
    d.rectangle((26, 138, 92, 146), fill=rgb('#3a2a44'))
    d.rectangle((24, 146, 100, 150), fill=rgb('#4a3550'))
    d.rectangle((24, 150, 100, 153), fill=rgb('#3a2a44'))
    for bx in (30, 86):
        d.rectangle((bx, 153, bx + 4, 168), fill=rgb('#3a2a44'))
    d.line([(24, 146), (100, 146)], fill=rgb('#5a4464'))
    for sx in (36, 50, 64, 78):                          # slats
        d.line([(sx, 138), (sx, 146)], fill=rgb('#33253e'))
    # a little stone lantern beside the path
    d.rectangle((258, 158, 282, 164), fill=rgb('#3d3158'))
    d.rectangle((264, 140, 276, 158), fill=rgb('#352b4e'))
    d.rectangle((258, 136, 282, 141), fill=rgb('#453760'))
    d.rectangle((266, 146, 274, 152), fill=rgb('#6b4a3e'))
    d.point((270, 149), fill=rgb('#ffd9a0'))
    halo(bg, 270, 149, 5, 16, '#4a3550', step=3)
    for i, y in enumerate(range(112, 120)):             # soft edge between hill and path
        dens = 2 + i % 3
        for x in range(W):
            if (x * 5 + y * 3) % dens == 0:
                d.point((x, y), fill=rgb('#352b4e'))
    # sakura tree: trunk on the left, limbs reaching into the sky
    trunk = [(0, 172), (6, 158), (14, 136), (22, 116), (32, 98), (43, 84), (52, 78),
             (46, 92), (38, 108), (32, 130), (27, 152), (25, 172)]
    d.polygon(trunk, fill=rgb('#2a1f36'))
    d.line([(8, 168), (16, 140), (26, 116), (40, 92), (50, 82)], fill=rgb('#3b2c4a'), width=2)
    limb(bg, [(34, 96), (54, 76), (78, 62), (108, 52), (140, 46)], 5, '#2e2339', '#40314f')
    limb(bg, [(40, 88), (58, 66), (74, 48), (88, 36)], 4, '#2e2339', '#40314f')
    limb(bg, [(24, 108), (10, 92), (2, 80)], 4, '#2e2339', '#40314f')
    limb(bg, [(30, 100), (24, 72), (22, 56)], 3, '#2e2339', '#40314f')
    limb(bg, [(78, 62), (70, 44), (66, 30)], 3, '#2e2339', '#40314f')
    rng = random.Random(20261115)
    canopy = [(6, 78, 4), (16, 66, 5), (28, 54, 4), (12, 52, 4), (30, 40, 4), (44, 46, 5),
              (56, 36, 4), (60, 52, 5), (46, 30, 3), (70, 42, 4), (22, 84, 3),
              (82, 34, 3), (36, 66, 4), (50, 58, 4), (68, 26, 3), (4, 62, 3)]
    for cx, cy, r in canopy:
        blossom(bg, cx, cy, r, '#ffe4ee', '#f4b6cf', '#d97ba6')
        for _ in range(2):
            blossom(bg, cx + rng.uniform(-r, r), cy + rng.uniform(-r, r),
                    rng.choice((1, 2)), '#fff2f7', '#f7c6da', '#c9688f')
    # a couple of lanterns hanging from the limb
    for lx, ly in ((96, 66), (128, 52)):
        d.line([(lx, ly - 10), (lx, ly)], fill=rgb('#3d3158'))
        d.rectangle((lx - 3, ly, lx + 3, ly + 7), fill=rgb('#c96a6a'))
        d.point((lx, ly + 3), fill=rgb('#ffd9a0'))
        halo(bg, lx, ly + 4, 5, 11, '#5a3a4e', step=2)
    # grass tufts + fallen petals along the foreground, kept clear of the stickers
    for gx, gy, gh in ((8, 172, 16), (16, 172, 11), (24, 172, 7), (208, 172, 14),
                       (218, 172, 9), (232, 172, 15), (244, 172, 7), (300, 172, 13),
                       (312, 172, 17), (120, 172, 11), (132, 172, 8), (110, 172, 6),
                       (286, 172, 8)):
        d.line([(gx, gy), (gx + rng.randint(-2, 2), gy - gh)], fill=rgb('#1f1830'))
        d.point((gx, gy - gh + 2), fill=rgb('#332a4e'))
    for gx in range(4, 320, 17):                         # low grass edge
        d.line([(gx, 172), (gx + rng.randint(-2, 2), 172 - rng.randrange(3, 7))],
               fill=rgb('#241c36'))
    for _ in range(40):
        x, y = rng.randrange(0, W), rng.randrange(120, H)
        d.point((x, y), fill=rgb(rng.choice(('#e0a8c0', '#c98fa8', '#f0c4d4'))))
    for fill_box in ((SAK_BRANCH_R, SAK_SKY), (SAK_GIRL_R, SAK_PATH),
                     (SAK_BOY_R, SAK_PATH), (SAK_HEART_R, SAK_SKY),
                     (SAK_MOON_R, SAK_SKY)):
        flat(bg, fill_box[0], fill_box[1])
    return bg


def build_sakura_love():
    s = PS.Scheme(
        'px6-sakura-love', '樱花告白',
        dict(family=FAMILY, tags=['告白', '春天', '夜樱'],
             story='约好在老樱树下见面，她还没来，风先把花瓣吹了一身。等到脚步声靠近，'
                   '整棵树好像一起亮了。'),
        '夜色里的樱花树下，两个人并肩站着看花。每次敲击键盘，樱枝上的花就亮一分、'
        '花瓣簌簌落下；敲得投入时他们靠得更近，头顶浮起一颗心；久不碰键盘，月亮变成'
        '弯月，两个人靠在一起睡意朦胧。',
        ['#2c2752', '#2c2446', '#f7c6d9', '#ff6f9f', '#f8ecdf', '#f2d7c8'],
        sakura_bg())
    s.sticker('樱枝', SAK_BRANCH_R[0], SAK_BRANCH_R[1], sakura_branch('calm'),
              '#f7c6d9', SAK_SKY,
              caps=sakura_branch('calm'), caps_fg='#ff6f9f',
              react=sakura_branch('react'), react_fg='#ff9ec0',
              sleepy_fg='#9a7695')
    s.sticker('她', SAK_GIRL_R[0], SAK_GIRL_R[1], sakura_girl('calm'), '#f6bcc6', SAK_PATH,
              caps_fg='#ffc9d2',
              react=sakura_girl('react'), react_fg='#ffdde2',
              sleepy=sakura_girl('react'), sleepy_fg='#b088a0')
    s.sticker('他', SAK_BOY_R[0], SAK_BOY_R[1], sakura_boy('calm'), '#f0dcc8', SAK_PATH,
              caps_fg='#f8e8d6',
              react=sakura_boy('react'), react_fg='#fff2e2',
              sleepy=sakura_boy('react'), sleepy_fg='#b6a696')
    s.sticker('心', SAK_HEART_R[0], SAK_HEART_R[1], sakura_heart('calm'),
              '#ffd0e2', SAK_SKY,
              caps=sakura_heart('caps'), caps_fg='#ff7aa8',
              react=sakura_heart('react'), react_fg='#fff2f6',
              sleepy=sakura_heart('sleepy'), sleepy_fg='#8a6b86')
    s.sticker('月亮', SAK_MOON_R[0], SAK_MOON_R[1], sakura_moon('full'),
              '#f8ecdf', SAK_SKY,
              caps_fg='#fff6e3', react_fg='#ffe9f0',
              sleepy=sakura_moon('sleepy'), sleepy_fg='#cfc4dc')
    s.set_effect('petal', trigger='key', spawn=(96, 34, 140, 20), count=5, size=3,
                 colors=['#ffd0e2', '#ffffff', '#ff6fa6'], vx=(-38, 38), vy=(48, 86),
                 gravity=18, life_ms=2800)
    s.set_pulse('心', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=25000)
    s.statusInk = INK
    return s


# ================================================================= 2. 情书
LET_WALL = '#2b2036'
LET_DESK = '#4a332a'
LET_PAPER_R = (146, 78, 34, 38)
LET_ENV_R = (136, 118, 50, 40)
LET_HEART_R = (156, 50, 18, 16)
LET_FLAME_R = (216, 106, 14, 16)


def letter_paper(state):
    g = Grid(LET_PAPER_R[2], LET_PAPER_R[3])            # 34 x 38
    if state == 'empty':
        return g
    top = 0 if state == 'out' else 20
    g.rect(2, top, 31, 37, '#')
    for y in range(top + 7, 37, 4):
        g.hline(6, 27, y, '.')
    if state == 'out':
        heart_shape(g, 17, 7, 5)
        for cx, cy in ((17, 7),):
            g.set(cx, cy, '.')
        for y in range(17, 36):
            g.set(17, y, '.')                           # ruled gap under the heart
    return g


def letter_envelope(state):
    g = Grid(LET_ENV_R[2], LET_ENV_R[3])                # 50 x 40
    g.rect(2, 15, 47, 38, '#')
    if state == 'closed':
        g.line(3, 16, 24, 27, '.', 2)
        g.line(46, 16, 25, 27, '.', 2)
        heart_shape(g, 24, 32, 3, '.')
    else:
        g.hline(4, 45, 16, '.')
        g.line(4, 16, 24, 26, '.', 1)
        g.line(45, 16, 25, 26, '.', 1)
        g.rect(6, 17, 43, 24, '.')
        g.hline(4, 45, 25, '#')
    return g


def letter_heart(state):
    rows = {'calm': (), 'caps': HEART_S, 'react': HEART_M, 'sleepy': ()}[state]
    return heart_grid(LET_HEART_R[2], LET_HEART_R[3], rows)


def letter_flame(state):
    g = Grid(LET_FLAME_R[2], LET_FLAME_R[3])            # 14 x 16
    if state == 'tiny':
        g.disc(7, 12, 1)
        g.set(7, 10)
        return g
    g.disc(7, 12, 2)
    g.rect(6, 6, 8, 12)
    g.set(7, 4)
    if state == 'wave':
        g.set(4, 9)
        g.set(10, 8)
    return g


def letter_bg():
    bg = Image.new('RGB', (W, H), rgb(LET_WALL))
    d = ImageDraw.Draw(bg)
    # wall: soft warm light falling from the upper right
    dither_disc(bg, 236, 112, 78, '#46304a', dens=4, parity=1)
    dither_disc(bg, 232, 116, 46, '#5c3c50', dens=4, parity=2)
    PS.window_frame(bg, 22, 12, 104, 66, frame='#6b4b3a', sill='#3a2830')
    d.rectangle((25, 15, 101, 63), fill=rgb('#1a2440'))
    PS.stars(bg, 26, '#e8f0ff', seed=12, area=(26, 16, 100, 62), size2=4)
    PS.moon(bg, 76, 30, 7, '#f4ead8', '#d8cdb8')
    rain_in(bg, (25, 15, 101, 63), 30, '#7f93c8', seed=8)
    # a small framed picture on the right wall
    d.rectangle((250, 36, 300, 76), fill=rgb('#3a2836'))
    d.rectangle((253, 39, 297, 73), fill=rgb('#553b46'))
    d.rectangle((262, 48, 288, 66), fill=rgb('#6d4a52'))
    d.point((275, 54), fill=rgb('#ffd9a0'))
    d.line([(262, 63), (275, 57), (288, 63)], fill=rgb('#4a333e'))
    # desk
    d.rectangle((0, 72, W - 1, H - 1), fill=rgb(LET_DESK))
    d.rectangle((0, 72, W - 1, 74), fill=rgb('#5f4233'))
    rng = random.Random(77)
    for gy in (86, 100, 148, 158, 168):
        x = rng.randrange(0, 60)
        while x < W:
            ln = rng.randrange(14, 48)
            d.line([(x, gy), (x + ln, gy)], fill=rgb('#3f2b23'))
            x += ln + rng.randrange(30, 70)
    # ink pot and quill to the left of the envelope
    d.ellipse((92, 122, 122, 146), fill=rgb('#2a2536'))
    d.ellipse((96, 120, 118, 136), fill=rgb('#3a3448'))
    d.line([(108, 124), (124, 84)], fill=rgb('#d8cbb8'), width=2)
    d.line([(124, 84), (131, 72)], fill=rgb('#f0e4d0'), width=1)
    d.line([(126, 80), (136, 76)], fill=rgb('#e0d2bd'), width=1)
    # a stack of books bottom right
    for x0, y0, x1, y1, c, page in ((244, 140, 314, 152, '#4a2f34', '#8a6a52'),
                                    (248, 128, 310, 140, '#5c3b3a', '#a07a5c'),
                                    (252, 118, 306, 128, '#6d4a46', '#b08a6a')):
        d.rectangle((x0, y0, x1, y1), fill=rgb(c))
        d.line([(x0 + 1, y0 + 1), (x1 - 1, y0 + 1)], fill=rgb(page))
        d.line([(x0 + 1, y1 - 1), (x1 - 1, y1 - 1)], fill=rgb('#33242a'))
        for bx in range(x0 + 8, x1 - 4, 9):
            d.line([(bx, y0 + 3), (bx, y1 - 2)], fill=rgb(page))
    # a pressed blossom and loose petals on the desk
    blossom(bg, 170, 166, 3, '#ffe4ee', '#e8a8c2', '#c9688f')
    for x, y in ((186, 160), (60, 154), (228, 98), (140, 100)):
        d.point((x, y), fill=rgb('#d99cb4'))
    # candle body (the flame is a sticker)
    candle_body(bg, 216, 118, 14, 26, '#e8d6bd', '#f6e8d2', '#5a4234')
    halo(bg, 223, 112, 8, 26, '#6b4a3e', step=3)
    for fill_box, colour in ((LET_PAPER_R, LET_DESK), (LET_ENV_R, LET_DESK),
                             (LET_HEART_R, LET_WALL), (LET_FLAME_R, LET_DESK)):
        flat(bg, fill_box, colour)
    return bg


def build_love_letter():
    s = PS.Scheme(
        'px6-love-letter', '情书',
        dict(family=FAMILY, tags=['暗恋', '写信', '夜'],
             story='台灯下写了一整夜，写完又不敢寄。火漆压下去的那一刻，烛火轻轻晃了一下，'
                   '像有人在心里点头。'),
        '深夜书桌上的情书：窗外下着雨，蜡烛昏黄，信封压在木桌中央。每次敲键，信纸就'
        '从信封里向上滑出一点，火漆上的心也跟着亮；敲得投入时整封信浮起来、心形印章'
        '变色，久不碰键盘，信收回去、烛火只剩一点点，陪你一起打盹。',
        ['#2b2036', '#4a332a', '#efdcc0', '#ff6f9f', '#e8a8c2', '#ffd9a0'],
        letter_bg())
    s.sticker('信封', LET_ENV_R[0], LET_ENV_R[1], letter_envelope('closed'),
              '#efdcc0', LET_DESK,
              caps=letter_envelope('open'), caps_fg='#f8ead2',
              react=letter_envelope('open'), react_fg='#fff4e0',
              sleepy=letter_envelope('closed'), sleepy_fg='#c2ad95')
    s.sticker('信纸', LET_PAPER_R[0], LET_PAPER_R[1], letter_paper('empty'),
              '#f8efdc', LET_DESK,
              caps=letter_paper('sliver'), caps_fg='#fbf3e2',
              react=letter_paper('out'), react_fg='#fffaf0',
              sleepy=letter_paper('empty'), sleepy_fg='#b8a892')
    s.sticker('心', LET_HEART_R[0], LET_HEART_R[1], letter_heart('calm'),
              '#ffd0e2', LET_WALL,
              caps=letter_heart('caps'), caps_fg='#ff7aa8',
              react=letter_heart('react'), react_fg='#fff2f6',
              sleepy=letter_heart('sleepy'), sleepy_fg='#7a6070')
    s.sticker('烛火', LET_FLAME_R[0], LET_FLAME_R[1], letter_flame('wave'),
              '#ffd9a0', LET_DESK,
              caps_fg='#ffe9bd', react_fg='#fff2cf',
              sleepy=letter_flame('tiny'), sleepy_fg='#c08a55')
    s.set_effect('heart', trigger='key', spawn=(150, 96, 26, 14), count=3, size=2,
                 colors=['#ff7f9f', '#ffb3c7', '#ffe0e8'], vx=(-14, 14), vy=(-46, -24),
                 gravity=10, life_ms=2200)
    s.set_pulse('烛火', period_ms=1700, minimum=120)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=26000)
    s.statusInk = INK
    return s


# ================================================================ 3. 心跳
HB_WALL = '#251a30'
HB_BED = '#3a2742'
HB_HEART_R = (138, 34, 44, 40)
HB_ECG_R = (108, 100, 84, 18)
HB_HAND_R = (92, 40, 30, 22)
HB_SPARK_R = (186, 74, 18, 14)


def hb_heart(state):
    g = Grid(HB_HEART_R[2], HB_HEART_R[3])              # 44 x 40
    if state == 'calm':
        heart_shape(g, 22, 20, 7)
    elif state == 'caps':
        heart_shape(g, 22, 20, 8)
    elif state == 'react':
        heart_shape(g, 22, 21, 11)
        for x0, y0, x1, y1 in ((22, 6, 22, 2), (8, 10, 5, 6), (36, 10, 39, 6),
                               (2, 20, 0, 20), (42, 20, 43, 20)):
            g.line(x0, y0, x1, y1, '#', 1)              # light rays
    else:                                                # sleepy
        heart_shape(g, 22, 23, 5)
    return g


def hb_ecg(state):
    g = Grid(HB_ECG_R[2], HB_ECG_R[3])                  # 84 x 18
    base = 12
    if state in ('calm', 'sleepy'):
        g.hline(0, 83, base, '#')
        for x in range(6, 84, 14):
            g.hline(x, x + 5, base, '#')
    elif state == 'caps':
        pts = [(0, 12), (24, 12), (28, 9), (32, 12), (40, 12), (44, 10),
               (52, 12), (60, 12), (64, 9), (68, 12), (83, 12)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            g.line(x0, y0, x1, y1, '#')
    else:                                                # react: full QRS complex
        pts = [(0, 12), (10, 12), (14, 8), (18, 13), (24, 13), (28, 3), (31, 17),
               (34, 12), (40, 11), (44, 12), (54, 12), (58, 9), (62, 12), (70, 12),
               (74, 9), (78, 12), (83, 12)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            g.line(x0, y0, x1, y1, '#')
    return g


def hb_hand(state):
    g = Grid(HB_HAND_R[2], HB_HAND_R[3])                # 30 x 22
    if state == 'away':
        return g
    lift = 3 if state == 'reach' else 0
    g.rect(0, 10, 9, 21, '#')                           # wrist / forearm
    g.rect(8, 6 + lift, 20, 20, '#')                    # palm
    if state == 'curl':
        g.rect(19, 8, 22, 12, '#')                      # curled fingers
        g.rect(16, 21, 26, 21, '#')
    else:
        for i, ln in enumerate((25, 27, 26, 23)):       # fingers reaching right
            top = 5 + lift + i * 3
            g.rect(19, top, ln, top + 1, '#')
        g.rect(12, 2 + lift, 17, 6 + lift, '#')         # thumb
    return g


def hb_sparks(state):
    g = Grid(HB_SPARK_R[2], HB_SPARK_R[3])              # 18 x 14
    if state == 'calm':
        for cx, cy in ((5, 8), (12, 4)):
            g.set(cx, cy)
    elif state == 'react':
        for cx, cy, r in ((5, 5, 2), (13, 9, 2), (9, 2, 1)):
            g.rect(cx - r, cy, cx + r, cy)
            g.rect(cx, cy - r, cx, cy + r)
    return g


def heartbeat_bg():
    bg = Image.new('RGB', (W, H), rgb(HB_WALL))
    d = ImageDraw.Draw(bg)
    # faint rose bloom around the heart (drawn outside the sticker rectangle)
    dither_disc(bg, 160, 62, 64, '#3a2038', dens=5, parity=1)
    dither_disc(bg, 160, 62, 40, '#4a2740', dens=5, parity=2)
    # window on the right: rainy city at night
    d.rectangle((236, 34, 312, 96), fill=rgb('#141a30'))
    d.rectangle((238, 36, 310, 94), fill=rgb('#1b2440'))
    rain_in(bg, (238, 36, 310, 94), 24, '#7f93c8', seed=21)
    for x, y, c in ((244, 88, '#ffb86a'), (252, 86, '#ffd27a'), (262, 90, '#ff9f6a'),
                    (272, 84, '#ffe3a0'), (284, 88, '#ffb86a'), (296, 82, '#ffd27a'),
                    (302, 90, '#ff9f6a'), (250, 78, '#c9d8ff'), (288, 74, '#c9d8ff')):
        d.point((x, y), fill=rgb(c))
        d.point((x + 1, y), fill=rgb(c))
    for x, y, rr in ((246, 60, 2), (284, 56, 3), (302, 66, 2)):
        dither_disc(bg, x, y, rr, '#5a6a9a', dens=2)
    d.rectangle((236, 33, 312, 35), fill=rgb('#4a3a55'))
    d.rectangle((233, 34, 235, 96), fill=rgb('#4a3a55'))
    d.rectangle((312, 34, 314, 96), fill=rgb('#4a3a55'))
    d.rectangle((233, 96, 314, 99), fill=rgb('#4a3a55'))
    # shelf and a little photo on the left wall
    d.rectangle((28, 70, 96, 73), fill=rgb('#3d2c46'))
    d.rectangle((34, 48, 62, 70), fill=rgb('#3a2836'))
    d.rectangle((36, 50, 60, 68), fill=rgb('#5a3a4a'))
    d.point((48, 56), fill=rgb('#ffd9a0'))
    d.rectangle((70, 56, 88, 70), fill=rgb('#2f2138'))
    d.rectangle((72, 58, 86, 68), fill=rgb('#4a3050'))
    # bedside lamp on the left: the only warm light in the room
    d.rectangle((14, 128, 42, 133), fill=rgb('#3d2a48'))
    d.polygon([(20, 104), (34, 104), (38, 114), (16, 114)], fill=rgb('#c98a5a'))
    d.line([(27, 114), (27, 128)], fill=rgb('#4a3050'), width=2)
    dither_disc(bg, 27, 110, 26, '#63443c', dens=9, parity=1)
    halo(bg, 27, 110, 12, 28, '#7a5040', step=4)
    for x, y in ((20, 24), (30, 18), (40, 26)):          # a few wall stars
        sparkle(d, x, y, 1, '#c9a0b8')
    # bed at the bottom: pillow, crumpled duvet with a sleeping bump
    d.rectangle((0, 136, W - 1, H - 1), fill=rgb(HB_BED))
    d.rectangle((0, 133, W - 1, 136), fill=rgb('#4a3354'))
    d.ellipse((196, 136, 256, 162), fill=rgb('#5b4062'))
    d.ellipse((201, 139, 251, 158), fill=rgb('#6a4a70'))
    d.polygon([(244, 172), (250, 148), (274, 140), (302, 146), (318, 156), (318, 172)],
              fill=rgb('#563c60'))
    for x, y in ((258, 148), (274, 144), (292, 147), (306, 152)):
        d.line([(x, y), (x - 5, y + 16)], fill=rgb('#4a3354'))
    d.line([(0, 140), (192, 140)], fill=rgb('#422e50'))
    halo(bg, 236, 46, 20, 46, '#3d2a48', step=5, skip=3)
    for fill_box, colour in ((HB_HEART_R, HB_WALL), (HB_ECG_R, HB_WALL),
                             (HB_HAND_R, HB_WALL), (HB_SPARK_R, HB_WALL)):
        flat(bg, fill_box, colour)
    return bg


def build_heartbeat():
    s = PS.Scheme(
        'px6-heartbeat', '心跳',
        dict(family=FAMILY, tags=['心动', '深夜', '期许'],
             story='半夜失眠，把手按在胸口，才发现心跳比想象中大声。原来喜欢一个人，是藏不住的'
                   '生理反应。'),
        '深夜里一间安静的房间：墙上浮着一颗会呼吸的心，下面是心跳曲线。每次敲键，心就'
        '亮起来、曲线跳一下，爱心往上飘；敲得投入时整颗心涨大、曲线剧烈起伏、指尖伸'
        '过去，久不碰键盘，心缩小变暗，曲线拉成一条平线。',
        ['#251a30', '#3a2742', '#ff6f9f', '#ffd0e2', '#f8ecdf', '#7a3e5e'],
        heartbeat_bg())
    s.sticker('心', HB_HEART_R[0], HB_HEART_R[1], hb_heart('calm'), '#e08aa8', HB_WALL,
              caps=hb_heart('caps'), caps_fg='#ff88b0',
              react=hb_heart('react'), react_fg='#fff0f5',
              sleepy=hb_heart('sleepy'), sleepy_fg='#8a5a72')
    s.sticker('心电图', HB_ECG_R[0], HB_ECG_R[1], hb_ecg('calm'), '#8a4a6a', HB_WALL,
              caps=hb_ecg('caps'), caps_fg='#c96a8a',
              react=hb_ecg('react'), react_fg='#ff9ec0',
              sleepy=hb_ecg('sleepy'), sleepy_fg='#5f3a50')
    s.sticker('手', HB_HAND_R[0], HB_HAND_R[1], hb_hand('calm'), '#d8a8a8', HB_WALL,
              caps_fg='#e8bcb8',
              react=hb_hand('reach'), react_fg='#ffe0d8',
              sleepy=hb_hand('curl'), sleepy_fg='#9a7088')
    s.sticker('火花', HB_SPARK_R[0], HB_SPARK_R[1], hb_sparks('calm'), '#ffd0e2', HB_WALL,
              caps_fg='#ffb3c7',
              react=hb_sparks('react'), react_fg='#ffe9f2',
              sleepy=hb_sparks('calm'), sleepy_fg='#7a5a72')
    s.set_effect('heart', trigger='key', spawn=(148, 78, 22, 10), count=4, size=2,
                 colors=['#ff7f9f', '#ffb3c7', '#ffe0e8'], vx=(-18, 18), vy=(-58, -30),
                 gravity=14, life_ms=2100)
    s.set_pulse('心', period_ms=1150, minimum=130)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=26000)
    s.statusInk = INK
    return s


# ============================================================== 4. 摩天轮
FW_SKY = '#1a2140'
FW_INNER = '#252d54'
FW_COUPLE_R = (134, 92, 50, 38)
FW_HEART_R = (150, 66, 20, 18)
FW_LAMP_R = (198, 88, 20, 30)
FW_ROOF_R = (104, 62, 26, 12)


def arc(im, cx, cy, r, k0, k1, colour, width=2, steps=120):
    d = ImageDraw.Draw(im)
    pts = [(cx + math.cos(k0 + (k1 - k0) * i / steps) * r,
            cy + math.sin(k0 + (k1 - k0) * i / steps) * r) for i in range(steps + 1)]
    d.line(pts, fill=rgb(colour), width=width, joint='curve')


def fw_couple(state):
    g = Grid(FW_COUPLE_R[2], FW_COUPLE_R[3])            # 50 x 38
    seat = 33
    lean1, lean2 = (0, 0) if state == 'calm' else (5, -7)

    def seated(cx, h, lean, skirt):
        hr = max(2, int(round(h * 0.18)))
        hx = int(round(cx + lean))
        hy = seat - h + hr
        g.disc(hx, hy, hr)
        neck = hy + hr
        if skirt:
            for y in range(neck, seat + 1):
                t = (y - neck) / max(1.0, seat - neck)
                half = int(round(hr * (1.0 + 1.7 * max(0.0, t - 0.3) / 0.7)))
                g.hline(hx - half, hx + half, y)
            g.rect(hx - 3, seat + 1, hx + 3, 37)
        else:
            g.rect(hx - hr, neck, hx + hr, seat)
            g.rect(hx - hr - 1, seat + 1, hx - 1, 37)
            g.rect(hx + 1, seat + 1, hx + hr + 1, 37)
        return hx, hy, hr

    a = seated(16, 23, lean1, True)
    b = seated(33, 25, lean2, False)
    set_eyes(g, a, 'closed' if state != 'calm' else 'open')
    set_eyes(g, b, 'closed' if state != 'calm' else 'open')
    if state != 'calm':
        g.line(25, 26, 29, 27, '#', 1)                  # held hands
    return g


def fw_heart(state):
    rows = {'calm': (), 'caps': HEART_S, 'react': HEART_M, 'sleepy': ()}[state]
    return heart_grid(FW_HEART_R[2], FW_HEART_R[3], rows)


def fw_lamp(state):
    g = Grid(FW_LAMP_R[2], FW_LAMP_R[3])                # 20 x 30
    g.vline(10, 0, 5, '#')                              # hook
    g.rect(4, 6, 15, 9, '#')                            # cap
    g.rect(5, 10, 14, 22, '#')                          # glass
    g.rect(6, 23, 13, 24, '#')                          # base
    g.rect(8, 12, 9, 14, '.')
    g.rect(12, 17, 13, 20, '.')
    if state == 'sleepy':
        g.rect(7, 14, 12, 21, '.')
    return g


def fw_roof(state):
    g = Grid(FW_ROOF_R[2], FW_ROOF_R[3])                # 26 x 12
    if state == 'sleepy':
        return g
    for x in range(1, 26, 3):
        g.set(x, 6 if state == 'react' else 7)
        if state == 'react':
            g.set(x, 4)
    return g


def ferris_bg():
    bg = Image.new('RGB', (W, H), rgb(FW_SKY))
    d = ImageDraw.Draw(bg)
    stars(bg, 60, (0, 0, W, 150), ['#f7f0dd', '#cfd8ff', '#ffe6d0'], seed=41)
    # the wheel: three rim arcs above us + hanging cabins
    for r, w in ((262, 2), (254, 3), (246, 2)):
        arc(bg, 160, 300, r, math.radians(-117), math.radians(-63), '#2f3760', w, 140)
    for k in range(-116, -62, 12):
        a = math.radians(k)
        d.line([(160 + math.cos(a) * 246, 300 + math.sin(a) * 246),
                (160 + math.cos(a) * 262, 300 + math.sin(a) * 262)],
               fill=rgb('#2b3358'), width=2)
    for k in (-112, -104, -76, -68):
        a = math.radians(k)
        bx, by = 160 + math.cos(a) * 254, 300 + math.sin(a) * 254
        d.line([(bx, by), (bx, by + 6)], fill=rgb('#3a4470'))
        d.rectangle((bx - 5, by + 6, bx + 5, by + 16), fill=rgb('#39426b'))
        d.rectangle((bx - 3, by + 8, bx + 3, by + 11), fill=rgb('#c9a86a'))
    # city far below, seen from the cabin
    d.rectangle((0, 144, W - 1, H - 1), fill=rgb('#0d1326'))
    rng = random.Random(19)
    x = 0
    while x < W:
        bw, bh = rng.randrange(9, 24), rng.randrange(8, 22)
        d.rectangle((x, 144 - bh, x + bw, 144), fill=rgb('#111930'))
        for wy in range(146 - bh, 142, 4):
            for wx in range(x + 2, x + bw - 1, 4):
                if rng.random() < 0.55:
                    d.point((wx, wy), fill=rgb(rng.choice(('#ffd27a', '#ffb86a', '#c9d8ff'))))
        x += bw + rng.randrange(2, 7)
    d.rectangle((0, 148, W - 1, H - 1), fill=rgb('#0a1022'))
    for y in range(152, H, 4):
        for x in range(0, W, 16):
            if rng.random() < 0.6:
                d.line([(x + rng.randrange(0, 8), y), (x + 12, y)], fill=rgb('#1b2a4e'))
    # the cabin we are sitting in: roof, frame and flat interior
    d.rectangle((92, 52, 228, 60), fill=rgb('#2b3358'))
    d.rectangle((92, 60, 228, 140), fill=rgb(FW_INNER))
    d.rectangle((92, 52, 96, 142), fill=rgb('#2b3358'))
    d.rectangle((224, 52, 228, 142), fill=rgb('#2b3358'))
    d.rectangle((92, 136, 228, 142), fill=rgb('#2b3358'))
    d.line([(160, 44), (160, 52)], fill=rgb('#3a4470'), width=3)
    for mx in (120, 188):
        d.rectangle((mx, 60, mx + 2, 136), fill=rgb('#303965'))
    d.line([(97, 62), (227, 62)], fill=rgb('#3a4470'))
    for x in range(98, 226, 7):                          # string lights on the roof
        d.point((x, 64 + (x % 3)), fill=rgb('#c9a86a'))
    d.rectangle((96, 128, 224, 131), fill=rgb('#2f3660'))   # the bench
    d.rectangle((96, 131, 224, 136), fill=rgb('#242b4c'))
    d.rectangle((96, 84, 224, 86), fill=rgb('#303965'))     # window sill line
    d.rectangle((186, 62, 194, 66), fill=rgb('#2b3358'))    # little hanging plant
    for i, x in enumerate((187, 190, 193)):
        d.line([(x, 66), (x - 2 + i, 84)], fill=rgb('#2f5a44'), width=1)
    d.point((188, 70), fill=rgb('#3f7050'))
    d.point((192, 74), fill=rgb('#3f7050'))
    # glass reflections on both sides
    for i, (x0, y0) in enumerate(((100, 66), (106, 92), (198, 70), (206, 98))):
        d.line([(x0, y0), (x0 + 8, y0 + 22)], fill=rgb('#313a68'))
        d.line([(x0 + 2, y0), (x0 + 10, y0 + 22)], fill=rgb('#2b335e'))
    for fill_box, colour in ((FW_COUPLE_R, FW_INNER), (FW_HEART_R, FW_INNER),
                             (FW_LAMP_R, FW_INNER), (FW_ROOF_R, FW_INNER)):
        flat(bg, fill_box, colour)
    return bg


def build_ferris_wheel():
    s = PS.Scheme(
        'px6-ferris-wheel', '摩天轮',
        dict(family=FAMILY, tags=['约会', '夜景', '高空'],
             story='摩天轮升到最高的那一格，城市变成脚下的银河。她假装看夜景，其实一直在看你'
                   '有没有靠近一点。'),
        '夜色里的摩天轮轿厢：脚下是万家灯火，头顶是轮缘灯串。每次敲键，轿厢顶的灯串会'
        '亮起来，久坐的两个人靠得更近；敲得投入时一颗心浮在窗边，久不碰键盘灯串熄灭，'
        '他们靠在一起睡着。',
        ['#1a2140', '#252d54', '#ff6f9f', '#ffd0e2', '#c9a86a', '#8a5a9a'],
        ferris_bg())
    s.sticker('情侣', FW_COUPLE_R[0], FW_COUPLE_R[1], fw_couple('calm'), '#f4d8c6', FW_INNER,
              caps_fg='#ffe4d2',
              react=fw_couple('react'), react_fg='#fff0e2',
              sleepy=fw_couple('react'), sleepy_fg='#b09a9a')
    s.sticker('心', FW_HEART_R[0], FW_HEART_R[1], fw_heart('calm'), '#ffd0e2', FW_INNER,
              caps=fw_heart('caps'), caps_fg='#ff7aa8',
              react=fw_heart('react'), react_fg='#fff2f6',
              sleepy=fw_heart('sleepy'), sleepy_fg='#7a5a70')
    s.sticker('小灯', FW_LAMP_R[0], FW_LAMP_R[1], fw_lamp('lit'), '#ffd9a0', FW_INNER,
              caps_fg='#ffe9bd', react_fg='#fff4d2',
              sleepy=fw_lamp('sleepy'), sleepy_fg='#8a6a48')
    s.sticker('灯串', FW_ROOF_R[0], FW_ROOF_R[1], fw_roof('dim'), '#c9a86a', FW_INNER,
              caps=fw_roof('lit'), caps_fg='#ffe0a0',
              react=fw_roof('lit'), react_fg='#fff0c0',
              sleepy=fw_roof('dim'), sleepy_fg='#6b5438')
    s.set_effect('spark', trigger='key', spawn=(148, 84, 22, 10), count=4, size=2,
                 colors=['#ffd9a0', '#fff3c4', '#ff9ec0'], vx=(-70, 70), vy=(-120, -40),
                 gravity=120, life_ms=1100, edge='bounce', shape='plus')
    s.set_pulse('小灯', period_ms=2600, minimum=160)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=24000)
    s.statusInk = INK
    return s


def px_text(im, s, x, y, colour, scale=1):
    """Draw tiny 5x7 pixel text straight into the background."""
    d = ImageDraw.Draw(im)
    c = rgb(colour)
    for i, ch in enumerate(s):
        glyph = PS.FONT.get(ch) or PS.FONT.get('?')
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == '1':
                    for dy in range(scale):
                        for dx in range(scale):
                            px, py = x + (i * 6 + gx) * scale + dx, y + gy * scale + dy
                            if 0 <= px < W and 0 <= py < H:
                                d.point((px, py), fill=c)


def rain_in(im, box, count=40, colour='#a9c7ff', seed=1, angle=1):
    """Rain streaks confined to one window rectangle."""
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    x0, y0, x1, y1 = box
    for _ in range(count):
        x, y = rng.randrange(x0, max(x0 + 1, x1 - 2)), rng.randrange(y0, max(y0 + 1, y1 - 4))
        ln = rng.randrange(4, 9)
        d.line([(x, y), (x + angle, y + ln)], fill=rgb(colour))


# ================================================================= 5. 萤火
FF_SKY = '#16223c'
FF_GROUND = '#1e2a44'
FF_SWARM_R = (110, 58, 64, 36)
FF_JAR_R = (66, 68, 26, 34)
FF_HAND_R = (46, 106, 34, 22)


def ff_swarm(state):
    g = Grid(FF_SWARM_R[2], FF_SWARM_R[3])              # 64 x 36
    if state == 'heart':
        pts = [(24, 8), (28, 5), (32, 8), (36, 5), (40, 8),
               (18, 14), (16, 20), (17, 26), (21, 31), (26, 34), (32, 35),
               (38, 34), (43, 31), (47, 26), (48, 20), (46, 14),
               (13, 17), (51, 17)]
    else:
        pts = [(18, 16), (26, 8), (34, 20), (42, 10), (50, 22), (56, 12),
               (12, 8), (30, 28), (44, 30), (54, 30), (8, 26), (22, 24),
               (48, 4), (38, 32)]
    for cx, cy in pts:
        g.disc(cx, cy, 1)
    return g


def ff_jar(state):
    g = Grid(FF_JAR_R[2], FF_JAR_R[3])                  # 26 x 34
    g.rect(3, 12, 22, 29)
    g.disc(6, 28, 3)
    g.disc(19, 28, 3)
    g.rect(4, 9, 21, 12)
    g.rect(6, 6, 19, 9)                                 # neck
    if state == 'closed':
        g.rect(5, 2, 20, 4)
        g.rect(6, 4, 19, 6)
    else:
        g.rect(8, 0, 17, 2)                             # lid lifted off
    g.rect(7, 14, 8, 24, '.')                           # glass shine
    g.rect(16, 20, 17, 25, '.')
    g.hline(10, 17, 27, '.')
    g.rect(4, 15, 22, 15, '.')
    return g


def ff_hand(state):
    g = Grid(FF_HAND_R[2], FF_HAND_R[3])                # 34 x 22
    g.rect(0, 14, 16, 21)                               # forearm
    g.disc(21, 16, 6)                                   # cupped palm
    g.rect(13, 10, 29, 16)
    if state == 'open':
        for x, top in ((12, 3), (16, 1), (21, 1), (26, 3)):
            g.rect(x, top, x + 2, 10)
    else:
        for x, top in ((13, 6), (17, 4), (22, 4), (26, 6)):
            g.rect(x, top, x + 2, 10)
    g.rect(7, 12, 10, 16)                               # thumb
    return g


def firefly_bg():
    bg = Image.new('RGB', (W, H), rgb(FF_SKY))
    d = ImageDraw.Draw(bg)
    dither_fade(bg, 74, 106, '#243354', dens_from=8, dens_to=2, parity=1)
    stars(bg, 54, (0, 0, W, 92), ['#f7f0dd', '#d8e6ff', '#ffe6c8'], seed=61)
    PS.moon(bg, 282, 34, 12, '#f4ecdc', '#d8ccb8')
    halo(bg, 282, 34, 16, 34, '#2c3a5a', step=4)
    # distant tree line
    ridge(bg, 104, '#101a30', amp=15, seed=62)
    d.rectangle((0, 106, W - 1, H - 1), fill=rgb(FF_GROUND))
    d.line([(0, 106), (W - 1, 106)], fill=rgb('#2a3a58'))
    rng = random.Random(63)
    for i, x in enumerate(range(0, W, 9)):              # foreground grass blades
        hgt = rng.randrange(12, 34) if (x < 40 or x > 186) else rng.randrange(5, 11)
        d.line([(x, H), (x + rng.randint(-3, 3), H - hgt)], fill=rgb('#141f34'))
        d.point((x + rng.randint(-2, 2), H - hgt + 2), fill=rgb('#2c4260'))
    for x in range(96, 320, 11):                         # taller mid-ground reeds
        hgt = rng.randrange(20, 46)
        gx = x + rng.randint(-3, 3)
        d.line([(gx, H), (gx + rng.randint(-5, 5), H - hgt)], fill=rgb('#13203a'))
        if rng.random() < 0.4:
            d.point((gx + 1, H - hgt + 3), fill=rgb('#3a5070'))
    for fx, fy in ((96, 130), (128, 146), (152, 120), (86, 148), (168, 136),
                   (206, 126), (238, 140), (274, 118)):
        d.point((fx, fy), fill=rgb('#a8d060'))
        d.point((fx + 1, fy), fill=rgb('#6f9a40'))
    for fill_box, colour in ((FF_SWARM_R, FF_SKY), (FF_JAR_R, FF_SKY),
                             (FF_HAND_R, FF_GROUND)):
        flat(bg, fill_box, colour)
    return bg


def build_firefly():
    s = PS.Scheme(
        'px6-firefly', '萤火',
        dict(family=FAMILY, tags=['夏夜', '心愿', '悄悄话'],
             story='抓了一整晚的萤火虫，最后还是把瓶子打开了。它们没有飞走，反而在你面前'
                   '排成了一颗心。'),
        '夏夜的草地上，手里捧着一只装满萤火的玻璃瓶。每次敲键，瓶盖会松开、萤火一点点'
        '飞出来；敲得投入时整片萤火在夜空里排成一颗心，久不碰键盘，萤火变暗回到草丛里。',
        ['#16223c', '#1e2a44', '#d6ff8a', '#fff6b0', '#f4ecdc', '#ffb3c7'],
        firefly_bg())
    s.sticker('萤群', FF_SWARM_R[0], FF_SWARM_R[1], ff_swarm('few'), '#b8e06a', FF_SKY,
              caps_fg='#e0ff9a',
              react=ff_swarm('heart'), react_fg='#fff6b0',
              sleepy=ff_swarm('few'), sleepy_fg='#5a6a48')
    s.sticker('萤火罐', FF_JAR_R[0], FF_JAR_R[1], ff_jar('closed'), '#cbe87a', FF_SKY,
              caps=ff_jar('open'), caps_fg='#e8ff9a',
              react=ff_jar('open'), react_fg='#f4ffc0',
              sleepy=ff_jar('closed'), sleepy_fg='#6a7450')
    s.sticker('手', FF_HAND_R[0], FF_HAND_R[1], ff_hand('hold'), '#d8b0a0', FF_GROUND,
              caps_fg='#e8c4b0',
              react=ff_hand('open'), react_fg='#f8dcc8',
              sleepy=ff_hand('hold'), sleepy_fg='#8a7468')
    s.set_effect('firefly', trigger='key', spawn=(120, 62, 44, 24), count=4, size=2,
                 colors=['#d6ff8a', '#fff6b0'], vx=(-20, 20), vy=(-22, 22),
                 gravity=0, life_ms=3000, edge='wrap', shape='plus')
    s.set_pulse('萤火罐', period_ms=2200, minimum=150)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=24000)
    s.statusInk = '#e6ffd0'
    return s


# =========================================================== 6. 咖啡店偶遇
CF_WALL = '#3a2a30'
CF_TABLE = '#5a3f33'
CF_CUPS_R = (134, 112, 54, 30)
CF_STEAM_R = (150, 80, 20, 24)
CF_HEART_R = (168, 58, 16, 14)


def cf_cups(state):
    g = Grid(CF_CUPS_R[2], CF_CUPS_R[3])                # 54 x 30

    def cup(cx):
        g.hline(cx - 10, cx + 10, 26)                   # saucer
        g.hline(cx - 8, cx + 8, 27)
        g.hline(cx - 6, cx + 6, 28)
        for i in range(15):                             # tapered body
            half = 6 - i // 6
            g.hline(cx - half, cx + half, 10 + i)
        g.rect(cx + 6, 12, cx + 9, 19)                  # handle
        g.rect(cx + 7, 13, cx + 8, 18, '.')
        g.hline(cx - 4, cx + 4, 11, '.')                # coffee surface
        if state == 'one':
            g.set(cx - 1, 11, '.')

    if state == 'one':
        cup(25)
    else:
        cup(14)
        cup(39)
    return g


def cf_steam(state):
    g = Grid(CF_STEAM_R[2], CF_STEAM_R[3])              # 20 x 24
    if state == 'heart':
        heart_shape(g, 10, 13, 5)
    elif state == 'two':
        for y in range(3, 20):
            g.set(5 + (1 if (y // 3) % 2 else 0), y)
            g.set(14 - (1 if (y // 3) % 2 else 0), y)
    elif state == 'faint':
        for y in range(12, 20):
            g.set(9 + (1 if (y // 4) % 2 else 0), y)
    else:                                                # calm: one wisp
        for y in range(3, 20):
            g.set(9 + (1 if (y // 3) % 2 else 0), y)
    return g


def cf_heart(state):
    rows = {'calm': (), 'caps': HEART_S, 'react': HEART_M, 'sleepy': ()}[state]
    return heart_grid(CF_HEART_R[2], CF_HEART_R[3], rows)


def cafe_bg():
    bg = Image.new('RGB', (W, H), rgb(CF_WALL))
    d = ImageDraw.Draw(bg)
    dither_disc(bg, 64, 40, 58, '#4c3636', dens=5, parity=1)
    # rainy window on the right
    d.rectangle((196, 18, 310, 98), fill=rgb('#20182a'))
    d.rectangle((200, 22, 306, 94), fill=rgb('#1a2440'))
    for x, y, rr in ((210, 44, 5), (232, 34, 4), (258, 48, 6), (282, 38, 4),
                     (298, 58, 5), (222, 76, 4)):
        dither_disc(bg, x, y, rr, '#5a5a8a', dens=2)
    for x, y, c in ((206, 82, '#ffb86a'), (216, 78, '#ffd27a'), (230, 86, '#ff9f6a'),
                    (246, 76, '#ffe3a0'), (258, 84, '#ffb86a'), (272, 76, '#ffd27a'),
                    (288, 88, '#ff9f6a'), (298, 70, '#c9d8ff'), (240, 66, '#c9d8ff')):
        d.point((x, y), fill=rgb(c))
        d.point((x + 1, y), fill=rgb(c))
    rain_in(bg, (201, 23, 305, 93), 42, '#7f93c8', seed=31)
    d.line([(252, 22), (252, 94)], fill=rgb('#20182a'), width=2)
    d.line([(200, 58), (306, 58)], fill=rgb('#20182a'), width=2)
    d.rectangle((192, 96, 314, 101), fill=rgb('#2e2128'))
    d.rectangle((196, 14, 310, 18), fill=rgb('#2e2128'))
    px_text(bg, 'LOVE', 210, 62, '#ff9ec0')             # little neon sign
    halo(bg, 222, 64, 8, 20, '#5a3a4a', step=3, skip=2)
    # chalkboard menu on the left wall
    d.rectangle((28, 34, 100, 82), fill=rgb('#6b4a3a'))
    d.rectangle((32, 38, 96, 78), fill=rgb('#26202a'))
    px_text(bg, 'COFFEE', 40, 46, '#e8d0a8')
    px_text(bg, 'latte 12', 40, 60, '#c9a882')
    d.line([(40, 56), (88, 56)], fill=rgb('#7a6a5a'))
    d.point((86, 44), fill=rgb('#ff9ec0'))
    # wainscot band between wall and table
    d.rectangle((0, 96, W - 1, 108), fill=rgb('#332430'))
    d.line([(0, 96), (W - 1, 96)], fill=rgb('#4a3438'))
    # pendant lamps
    for lx, ly, lr in ((56, 12, 5), (170, 8, 4)):
        d.line([(lx, 0), (lx, ly)], fill=rgb('#2a1e26'))
        d.rectangle((lx - lr - 2, ly, lx + lr + 2, ly + 4), fill=rgb('#c98a5a'))
        halo(bg, lx, ly + 12, 6, 26, '#5a3f34', step=4)
    # chairs and a table plant
    for cx in (112, 204):
        d.rectangle((cx - 9, 82, cx + 9, 88), fill=rgb('#2e2128'))
        d.rectangle((cx - 8, 88, cx + 8, 108), fill=rgb('#332530'))
        d.rectangle((cx - 8, 98, cx + 8, 102), fill=rgb('#3d2c38'))
        d.line([(cx - 8, 88), (cx - 8, 108)], fill=rgb('#241a20'))
        d.line([(cx + 8, 88), (cx + 8, 108)], fill=rgb('#241a20'))
    d.rectangle((222, 96, 240, 108), fill=rgb('#7a4a44'))
    blossom(bg, 231, 92, 4, '#ffd9e2', '#e88aa8', '#c9688f')
    d.line([(231, 96), (231, 108)], fill=rgb('#4a5a3a'), width=1)
    d.line([(231, 100), (226, 96)], fill=rgb('#4a5a3a'), width=1)
    # table top, grain and warm reflections
    d.rectangle((0, 108, W - 1, H - 1), fill=rgb(CF_TABLE))
    d.rectangle((0, 108, W - 1, 111), fill=rgb('#6d4d3e'))
    rng = random.Random(87)
    for gy in (148, 158, 168):
        x = rng.randrange(0, 60)
        while x < W:
            ln = rng.randrange(16, 52)
            d.line([(x, gy), (x + ln, gy)], fill=rgb('#4c352a'))
            x += ln + rng.randrange(30, 80)
    for x in (110, 190, 216):
        dither_disc(bg, x, 118, 8, '#6b4a3c', dens=3)
    d.rectangle((196, 120, 214, 126), fill=rgb('#e8d8c0'))       # napkin
    d.polygon([(196, 120), (205, 126), (214, 120)], fill=rgb('#d8c4a8'))
    d.rectangle((96, 132, 122, 138), fill=rgb('#8a6a52'))        # little plate
    blossom(bg, 109, 134, 2, '#f8e8d0', '#e0b8a0', '#c08070')
    for fill_box, colour in ((CF_CUPS_R, CF_TABLE), (CF_STEAM_R, CF_WALL),
                             (CF_HEART_R, CF_WALL)):
        flat(bg, fill_box, colour)
    return bg


def build_cafe_meet():
    s = PS.Scheme(
        'px6-cafe-meet', '咖啡店偶遇',
        dict(family=FAMILY, tags=['偶遇', '雨天', '咖啡'],
             story='下雨的下午躲进咖啡店，抬头发现对面坐下的正是那个人。两杯拿铁的热气'
                   '绕在一起，比任何台词都先说了话。'),
        '雨天咖啡店的靠窗座位：窗外霓虹模糊，桌上只有一杯拿铁。每次敲键，第二只杯子会'
        '出现在对面，热气变浓；敲得投入时两股热气缠成一颗心、杯子挪近，久不碰键盘只剩'
        '一杯，静静等你回来。',
        ['#3a2a30', '#5a3f33', '#f4e3c8', '#ff6f9f', '#ffd27a', '#8ac0c8'],
        cafe_bg())
    s.sticker('杯子', CF_CUPS_R[0], CF_CUPS_R[1], cf_cups('one'), '#f4e3c8', CF_TABLE,
              caps=cf_cups('two'), caps_fg='#fff0d8',
              react=cf_cups('two'), react_fg='#fffaf0',
              sleepy=cf_cups('one'), sleepy_fg='#c9b49c')
    s.sticker('热气', CF_STEAM_R[0], CF_STEAM_R[1], cf_steam('calm'), '#f7e6cd', CF_WALL,
              caps=cf_steam('two'), caps_fg='#fff2df',
              react=cf_steam('heart'), react_fg='#ffb0c6',
              sleepy=cf_steam('faint'), sleepy_fg='#a8917e')
    s.sticker('心', CF_HEART_R[0], CF_HEART_R[1], cf_heart('calm'), '#ffd0e2', CF_WALL,
              caps=cf_heart('caps'), caps_fg='#ff7aa8',
              react=cf_heart('react'), react_fg='#fff2f6',
              sleepy=cf_heart('sleepy'), sleepy_fg='#7a6070')
    s.set_effect('note', trigger='key', spawn=(152, 66, 20, 16), count=3, size=3,
                 colors=['#ffd0e2', '#fff2df', '#ff9ec0'], vx=(-24, 24), vy=(-46, -20),
                 gravity=16, life_ms=2100)
    s.set_pulse('心', period_ms=2000, minimum=150)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=25000)
    s.statusInk = INK
    return s


# =============================================================== 7. 海边日落
SB_BANDS = ((0, 30, '#3f2c5e'), (30, 56, '#7a4266'), (56, 88, '#c2667a'),
            (88, 100, '#e89078'))
SB_SEA = '#8a5474'
SB_SAND = '#d99a76'
SB_SUN_R = (142, 58, 36, 30)
SB_COUPLE_R = (132, 130, 60, 42)
SB_GLITTER_R = (134, 104, 52, 14)
SB_BIRD_R = (36, 62, 22, 10)


def sb_sun(state):
    g = Grid(SB_SUN_R[2], SB_SUN_R[3])                  # 36 x 30
    if state == 'calm':
        g.disc(18, 14, 11)
    elif state == 'caps':
        g.disc(18, 16, 13)
    elif state == 'react':
        g.disc(18, 19, 12)                              # dipping into the sea
    else:
        return g                                        # set
    return g


def sb_sit(g, cx, base, h, head_dx=0, skirt=False):
    hr = max(2, int(round(h * 0.17)))
    hx = int(round(cx + head_dx))
    hy = base - h + hr
    g.disc(hx, hy, hr)
    neck = hy + hr
    for y in range(neck, base - 7):                      # torso taper
        t = (y - neck) / max(1.0, base - 7 - neck)
        half = int(round(hr * (0.85 + 0.5 * t)))
        g.hline(hx - half, hx + half, y)
    if skirt:                                            # dress over bent knees
        g.rect(hx - hr - 3, base - 8, hx + hr + 1, base - 2)
    else:                                                # two knees with a gap
        g.rect(hx - hr - 1, base - 9, hx - 1, base - 1)
        g.rect(hx + 1, base - 9, hx + hr + 1, base - 1)
    g.line(hx - hr, neck + 3, hx - hr - 2, base - 8, '#', 1)   # arm on the knee
    return hx, hy, hr


def sb_couple(state):
    g = Grid(SB_COUPLE_R[2], SB_COUPLE_R[3])            # 60 x 42
    base = 39
    if state == 'calm':
        a = sb_sit(g, 20, base, 30, skirt=True)
        b = sb_sit(g, 40, base, 32)
        set_eyes(g, a, 'open')
        set_eyes(g, b, 'open')
    elif state == 'react':
        a = sb_sit(g, 21, base, 30, head_dx=6, skirt=True)
        b = sb_sit(g, 40, base, 32, head_dx=-8)
        set_eyes(g, a, 'closed')
        set_eyes(g, b, 'closed')
    else:                                                # sleepy: closer, dimmer
        a = sb_sit(g, 21, base, 29, head_dx=5, skirt=True)
        b = sb_sit(g, 39, base, 31, head_dx=-6)
        set_eyes(g, a, 'closed')
        set_eyes(g, b, 'closed')
    return g


def sb_glitter(state):
    g = Grid(SB_GLITTER_R[2], SB_GLITTER_R[3])          # 52 x 14
    cols = {'calm': (10, 24, 38), 'caps': (6, 15, 24, 33, 42),
            'react': (4, 12, 20, 28, 36, 44), 'sleepy': (14, 32)}[state]
    for x in cols:
        g.hline(x, min(51, x + 5), 3)
        g.hline(min(51, x + 1), min(51, x + 4), 6)
        g.hline(min(51, x + 2), min(51, x + 3), 9)
    if state == 'react':
        g.hline(20, 30, 1)
        g.hline(23, 28, 12)
    return g


def sb_birds(state):
    g = Grid(SB_BIRD_R[2], SB_BIRD_R[3])                # 22 x 10
    if state == 'sleepy':
        return g

    def bird(x, y):
        g.set(x, y + 1)
        g.set(x + 1, y)
        g.set(x + 2, y + 1)
        g.set(x + 3, y)
        g.set(x + 4, y + 1)

    bird(1, 6)
    bird(12, 3)
    return g


def sunset_bg():
    bg = Image.new('RGB', (W, H), rgb('#3f2c5e'))
    d = ImageDraw.Draw(bg)
    for y0, y1, c in SB_BANDS:
        d.rectangle((0, y0, W - 1, y1 - 1), fill=rgb(c))
    for y, c in ((29, '#4a3160'), (55, '#8f4e6c')):
        for x in range(W):
            if (x + y) % 2 == 0:
                d.point((x, y), fill=rgb(c))
    rng = random.Random(2026)
    for _ in range(9):                                   # long sunset clouds
        cx = rng.randrange(0, W)
        cy = rng.randrange(4, 52)
        ln = rng.randrange(24, 74)
        col = rng.choice(('#5a3a6e', '#8a4a6a', '#b0607a'))
        d.line([(cx, cy), (min(W - 1, cx + ln), cy)], fill=rgb(col))
        d.line([(cx + 4, cy + 1), (min(W - 1, cx + ln - 6), cy + 1)], fill=rgb(col))
    for _ in range(28):                                  # sea sparkle off the sun
        x, y = rng.randrange(0, W), rng.randrange(100, 130)
        d.point((x, y), fill=rgb(rng.choice(('#b06a7e', '#c87a86', '#9a5a76'))))
    d.line([(0, 100), (W - 1, 100)], fill=rgb('#e09078'))
    for y in (104, 109, 115, 121, 127):                  # wave dashes
        for x in range(0, W, 18):
            d.line([(x + rng.randrange(0, 8), y), (x + rng.randrange(9, 15), y)],
                   fill=rgb('#a8627e'))
    d.rectangle((0, 130, W - 1, H - 1), fill=rgb(SB_SAND))
    d.line([(0, 130), (W - 1, 130)], fill=rgb('#f0b48a'))
    for x in range(0, W, 14):                            # wet sand edge
        d.point((x + rng.randrange(0, 6), 131 + rng.randrange(0, 2)), fill=rgb('#c98a68'))
    # dunes and dry-sand shading
    d.polygon([(0, 172), (0, 146), (46, 140), (96, 148), (140, 142), (196, 150),
               (250, 144), (300, 152), (319, 146), (319, 172)], fill=rgb('#d0906e'))
    d.polygon([(0, 172), (0, 158), (54, 152), (110, 160), (168, 154), (232, 162),
               (288, 156), (319, 160), (319, 172)], fill=rgb('#c9855f'))
    for x in range(0, W, 22):                            # dune highlight glints
        d.line([(x + 4, 146 + (x // 22) % 3), (x + 14, 146 + (x // 22) % 3)],
               fill=rgb('#e8b08a'))
    for i in range(9):                                   # footsteps from the towels
        fx = 96 + i * 7
        fy = 166 - i * 3
        d.point((fx, fy), fill=rgb('#c07a58'))
        d.point((fx + 1, fy + 1), fill=rgb('#c07a58'))
    for _ in range(46):                                  # pebbles and shells
        x, y = rng.randrange(0, W), rng.randrange(150, H)
        d.point((x, y), fill=rgb(rng.choice(('#c9855f', '#e8b08a', '#b87658'))))
    # palm tree silhouette on the right
    trunk = [(288, 172), (292, 152), (298, 132), (306, 112), (312, 96), (318, 88),
             (314, 100), (308, 118), (302, 140), (298, 160), (296, 172)]
    d.polygon(trunk, fill=rgb('#5a3448'))
    for ex, ey, dx, dy in ((318, 88, -22, -10), (318, 88, -6, -22), (318, 88, 16, -14),
                           (318, 88, -26, 4), (318, 88, 10, -2)):
        d.line([(ex, ey), (ex + dx, ey + dy)], fill=rgb('#5a3448'), width=3)
        for i in range(3):
            d.line([(ex + dx * (i + 1) / 4, ey + dy * (i + 1) / 4 + 4),
                    (ex + dx * (i + 1) / 4 - 6, ey + dy * (i + 1) / 4 + 8)],
                   fill=rgb('#5a3448'))
    # two beach towels and a little bag
    d.polygon([(60, 168), (88, 156), (100, 162), (72, 172)], fill=rgb('#e8a08a'))
    d.polygon([(62, 166), (86, 157), (90, 160), (66, 169)], fill=rgb('#f0c0a0'))
    d.rectangle((236, 148, 254, 166), fill=rgb('#a85a52'))
    d.line([(236, 150), (254, 162)], fill=rgb('#c9746a'))
    for fill_box, colour in ((SB_SUN_R, '#c2667a'), (SB_COUPLE_R, SB_SAND),
                             (SB_GLITTER_R, SB_SEA), (SB_BIRD_R, '#c2667a')):
        flat(bg, fill_box, colour)
    return bg


def build_sunset_beach():
    s = PS.Scheme(
        'px6-sunset-beach', '海边日落',
        dict(family=FAMILY, tags=['日落', '海边', '并肩'],
             story='退潮以后坐在还温着的沙子上，看太阳一点点掉进海里。谁也没说话，但肩膀'
                   '靠在一起就够了。'),
        '海边落日：天空从紫烧到橘，海面拉出一条碎金的光。每次敲键，太阳往下沉一点、'
        '海面的光更密；敲得投入时两个人靠在一起、头挨着头，久不碰键盘太阳沉进海里，'
        '只剩一点余温和飞鸟。',
        ['#3f2c5e', '#c2667a', '#e89078', '#8a5474', '#d99a76', '#5a3448'],
        sunset_bg())
    s.sticker('落日', SB_SUN_R[0], SB_SUN_R[1], sb_sun('calm'), '#ffd27a', '#c2667a',
              caps=sb_sun('caps'), caps_fg='#ffe0a0',
              react=sb_sun('react'), react_fg='#ffbe6a',
              sleepy=sb_sun('sleepy'), sleepy_fg='#8a5a70')
    s.sticker('恋人', SB_COUPLE_R[0], SB_COUPLE_R[1], sb_couple('calm'), '#5a3448', SB_SAND,
              caps_fg='#6b3e52',
              react=sb_couple('react'), react_fg='#452838',
              sleepy=sb_couple('sleepy'), sleepy_fg='#7a5068')
    s.sticker('海光', SB_GLITTER_R[0], SB_GLITTER_R[1], sb_glitter('calm'), '#ffd9a0', SB_SEA,
              caps=sb_glitter('caps'), caps_fg='#ffe8b8',
              react=sb_glitter('react'), react_fg='#fff2cc',
              sleepy=sb_glitter('sleepy'), sleepy_fg='#9a6a78')
    s.sticker('飞鸟', SB_BIRD_R[0], SB_BIRD_R[1], sb_birds('calm'), '#5a3448', '#c2667a',
              caps_fg='#6b3e52', react_fg='#452838',
              sleepy=sb_birds('sleepy'), sleepy_fg='#8a5a70')
    s.set_effect('dust', trigger='key', spawn=(140, 92, 40, 12), count=4, size=1,
                 colors=['#ffe8b8', '#ffd9a0'], vx=(-14, 14), vy=(-18, -6),
                 gravity=-2, life_ms=3200, edge='wrap')
    s.set_pulse('落日', period_ms=3000, minimum=170)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=26000)
    s.statusInk = '#fff0d0'
    return s


# =============================================================== 8. 拍立得
PO_WALL = '#4a3230'
PO_PHOTO_R = (152, 84, 32, 32)
PO_HEART_R = (196, 68, 14, 12)
PO_LIGHTS_R = (96, 50, 40, 14)
PO_MINI_R = (238, 92, 24, 24)
PO_PHOTO_BG = '#8a7a72'


def po_photo(state):
    g = Grid(PO_PHOTO_R[2], PO_PHOTO_R[3])              # 32 x 32

    def bust(cx, cy, hr):
        g.disc(cx, cy, hr)
        g.hline(cx - hr - 3, cx + hr + 3, 28)
        g.rect(cx - hr - 3, 23, cx + hr + 3, 31)
        g.set(cx - 2, cy + 1, '.')
        g.set(cx + 2, cy + 1, '.')

    if state == 'calm':
        bust(10, 13, 4)
        bust(23, 11, 4)
    elif state == 'react':
        bust(12, 12, 5)
        bust(20, 11, 5)
        heart_shape(g, 16, 3, 2)
    else:
        bust(10, 13, 4)
        bust(23, 11, 4)
    return g


def po_heart(state):
    rows = {'calm': (), 'caps': HEART_S, 'react': HEART_M, 'sleepy': ()}[state]
    return heart_grid(PO_HEART_R[2], PO_HEART_R[3], rows)


def po_lights(state):
    g = Grid(PO_LIGHTS_R[2], PO_LIGHTS_R[3])            # 40 x 14
    if state == 'sleepy':
        return g
    for i, x in enumerate(range(2, 40, 6)):
        y = 8 + (i % 2) * 2
        g.set(x, y)
        g.set(x + 1, y)
        if state in ('react',):
            g.set(x, y - 1)
    return g


def po_mini(state):
    g = Grid(PO_MINI_R[2], PO_MINI_R[3])                # 24 x 24
    g.hline(3, 20, 18)
    for cx in (8, 15):
        g.disc(cx, 11, 2)
        g.rect(cx - 2, 13, cx + 2, 18)
    if state == 'react':
        heart_shape(g, 12, 5, 2)
    return g


def polaroid_bg():
    bg = Image.new('RGB', (W, H), rgb(PO_WALL))
    d = ImageDraw.Draw(bg)
    dither_disc(bg, 132, 104, 100, '#57393c', dens=11, parity=1)
    dither_disc(bg, 286, 44, 56, '#5f4038', dens=9, parity=2)
    # string of fairy lights across the wall (the bulbs are a sticker)
    pts = [(92, 58), (110, 62), (132, 64), (144, 64)]
    d.line([(88, 56), (120, 62), (150, 64)], fill=rgb('#6b5040'), width=1)
    d.line([(150, 64), (184, 60), (206, 56)], fill=rgb('#6b5040'), width=1)
    d.line([(206, 56), (240, 62), (268, 66)], fill=rgb('#6b5040'), width=1)
    # the polaroid on the wall
    d.rectangle((150, 80, 194, 134), fill=rgb('#3a2626'))
    d.rectangle((146, 76, 190, 130), fill=rgb('#f0e2c8'))
    d.rectangle((152, 84, 184, 116), fill=rgb(PO_PHOTO_BG))
    d.rectangle((150, 120, 186, 126), fill=rgb('#d8c4a8'))
    d.polygon([(154, 76), (168, 76), (160, 84)], fill=rgb('#c9a882'))
    # other little photos and postcards on the wall
    for x0, y0, w, h, c in ((24, 30, 34, 42, '#6d4a46'), (60, 24, 26, 32, '#7a5460'),
                            (216, 96, 30, 36, '#6d4a46'), (250, 34, 34, 40, '#7a5a52')):
        d.rectangle((x0, y0, x0 + w, y0 + h), fill=rgb('#3a2626'))
        d.rectangle((x0 - 2, y0 - 2, x0 + w - 2, y0 + h - 2), fill=rgb(c))
        d.rectangle((x0 + 2, y0 + 2, x0 + w - 4, y0 + h - 10), fill=rgb('#4a3a3a'))
    d.polygon([(70, 56), (84, 52), (88, 60), (74, 64)], fill=rgb('#b08a6a'))
    # wooden shelf with a plant and a jar of memories
    d.rectangle((0, 138, 76, 142), fill=rgb('#6b4a3a'))
    d.rectangle((8, 118, 30, 138), fill=rgb('#7a4444'))
    d.line([(19, 118), (19, 106)], fill=rgb('#4a5a3a'), width=1)
    for ex, ey in ((13, 112), (25, 110), (19, 104)):
        d.ellipse((ex - 4, ey - 3, ex + 4, ey + 3), fill=rgb('#5a6a44'))
    d.rectangle((40, 122, 62, 138), fill=rgb('#8a7a62'))
    d.rectangle((43, 118, 59, 122), fill=rgb('#a89578'))
    for x, y in ((46, 130), (52, 126), (57, 132)):
        d.point((x, y), fill=rgb('#e8c060'))
    dither_disc(bg, 150, 100, 60, '#6a4a44', dens=7, parity=2)
    for fill_box, colour in ((PO_PHOTO_R, PO_PHOTO_BG), (PO_HEART_R, PO_WALL),
                             (PO_LIGHTS_R, PO_WALL), (PO_MINI_R, PO_WALL)):
        flat(bg, fill_box, colour)
    return bg


def build_polaroid():
    s = PS.Scheme(
        'px6-polaroid', '拍立得',
        dict(family=FAMILY, tags=['纪念', '照片', '怀旧'],
             story='墙上的拍立得里，两个人总是差一点点没靠在一起。直到有一天你在照片上'
                   '画了一颗心，才发现那天他们确实笑了。'),
        '暖色墙面挂着一串小灯和几张旧拍立得。每次敲键，灯串亮一点、照片里的人靠近一点；'
        '敲得投入时照片上浮出一颗心、旁边的爱心贴纸也亮起来；久不碰键盘灯慢慢暗掉，'
        '照片褪成温柔的颜色。',
        ['#4a3230', '#8a7a72', '#f0e2c8', '#ff6f9f', '#e8c060', '#ffd0e2'],
        polaroid_bg())
    s.sticker('相片', PO_PHOTO_R[0], PO_PHOTO_R[1], po_photo('calm'), '#4a3230', PO_PHOTO_BG,
              caps_fg='#5a3a38',
              react=po_photo('react'), react_fg='#3a2422',
              sleepy=po_photo('sleepy'), sleepy_fg='#7a6a62')
    s.sticker('心', PO_HEART_R[0], PO_HEART_R[1], po_heart('calm'), '#ffd0e2', PO_WALL,
              caps=po_heart('caps'), caps_fg='#ff7aa8',
              react=po_heart('react'), react_fg='#fff2f6',
              sleepy=po_heart('sleepy'), sleepy_fg='#7a6070')
    s.sticker('小灯', PO_LIGHTS_R[0], PO_LIGHTS_R[1], po_lights('lit'), '#ffd9a0', PO_WALL,
              caps_fg='#ffe9bd',
              react=po_lights('lit'), react_fg='#fff4d2',
              sleepy=po_lights('dim'), sleepy_fg='#7a5a48')
    s.sticker('小拍立得', PO_MINI_R[0], PO_MINI_R[1], po_mini('calm'), '#5a3a38', PO_WALL,
              caps_fg='#6b4440',
              react=po_mini('react'), react_fg='#4a2c2a',
              sleepy=po_mini('calm'), sleepy_fg='#8a7068')
    s.set_effect('spark', trigger='key', spawn=(190, 74, 14, 8), count=3, size=2,
                 colors=['#ffd9a0', '#fff3c4', '#ffb3c7'], vx=(-46, 46), vy=(-90, -30),
                 gravity=110, life_ms=1100, edge='bounce', shape='plus')
    s.set_pulse('小灯', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=25000)
    s.statusInk = '#fff0d8'
    return s


# ================================================================= 9. 舞会
DN_WALL = '#2e1f33'
DN_FLOOR = '#5c4048'
DN_COUPLE_R = (132, 114, 50, 46)
DN_CHAND_R = (140, 22, 40, 30)
DN_NOTE_R = (204, 84, 18, 16)


def dn_couple(state):
    g = Grid(DN_COUPLE_R[2], DN_COUPLE_R[3])            # 50 x 46
    base = 44
    if state == 'calm':
        a = person(g, 16, base, 30, skirt=True)
        b = person(g, 36, base, 33)
        set_eyes(g, a, 'open')
        set_eyes(g, b, 'open')
        g.line(22, 24, 27, 24, '#', 1)                  # joined hands
        g.line(23, 19, 21, 16, '#', 1)
    elif state == 'caps':                                # dance hold, arms up
        a = person(g, 15, base, 30, skirt=True)
        b = person(g, 37, base, 33)
        set_eyes(g, a, 'closed')
        set_eyes(g, b, 'open')
        g.line(22, 19, 27, 11, '#', 2)                  # raised hands
        g.line(28, 19, 26, 10, '#', 2)
        g.line(11, 24, 5, 18, '#', 1)
        g.line(42, 24, 48, 29, '#', 1)
    elif state == 'react':                               # spinning
        g.disc(16, 39, 12)                              # the skirt flies out
        a = person(g, 16, base - 1, 28, skirt=True)
        b = person(g, 35, base, 32, head_dx=-2)
        set_eyes(g, a, 'closed')
        set_eyes(g, b, 'closed')
        g.line(30, 19, 40, 11, '#', 2)
        g.line(11, 21, 4, 14, '#', 1)
        g.line(23, 26, 28, 26, '#', 1)
    else:                                                # sleepy slow dance
        a = person(g, 16, base, 29, skirt=True)
        b = person(g, 35, base, 32, head_dx=-4)
        set_eyes(g, a, 'closed')
        set_eyes(g, b, 'closed')
        g.line(23, 24, 27, 24, '#', 1)
        g.line(27, 20, 23, 19, '#', 1)
    return g


def dn_chandelier(state):
    g = Grid(DN_CHAND_R[2], DN_CHAND_R[3])              # 40 x 30
    if state == 'sleepy':
        g.vline(20, 0, 9, '#')
        g.rect(13, 9, 27, 13, '#')
        g.disc(20, 17, 3, '#')
        return g
    g.vline(20, 0, 8, '#')                              # chain
    g.rect(12, 8, 28, 11, '#')                          # canopy
    g.disc(20, 16, 5, '#')                              # body
    g.rect(19, 10, 21, 27, '#')                         # stem
    for x in (5, 12, 28, 35):                           # arms and candles
        g.line(20, 19, x, 21, '#', 1)
        g.vline(x, 14, 21, '#')
        g.rect(x - 2, 11, x + 2, 14, '#')
    for x in (16, 24):                                  # inner tier
        g.vline(x, 13, 18, '#')
        g.rect(x - 1, 10, x + 1, 13, '#')
    g.disc(20, 27, 3, '#')
    return g


def dn_notes(state):
    g = Grid(DN_NOTE_R[2], DN_NOTE_R[3])                # 18 x 16
    if state == 'sleepy':
        return g
    for ox, oy in ((1, 8), (10, 5)):
        g.disc(ox + 2, oy + 5, 2)
        g.vline(ox + 4, oy - 2, oy + 4, '#')
        g.line(ox + 4, oy - 2, ox + 6, oy, '#', 1)
    return g


def dance_bg():
    bg = Image.new('RGB', (W, H), rgb(DN_WALL))
    d = ImageDraw.Draw(bg)
    # tall arched windows with night outside
    for wx, ww in ((20, 76), (222, 78)):
        d.rectangle((wx, 26, wx + ww, 108), fill=rgb('#3a2836'))
        d.ellipse((wx, 6, wx + ww, 46), fill=rgb('#3a2836'))
        d.rectangle((wx + 4, 30, wx + ww - 4, 104), fill=rgb('#1b2648'))
        d.ellipse((wx + 4, 10, wx + ww - 4, 46), fill=rgb('#1b2648'))
        PS.stars(bg, 14, '#e8f0ff', seed=wx, area=(wx + 6, 12, wx + ww - 6, 100), size2=5)
        PS.moon(bg, wx + ww // 2 + 12, 34, 6, '#f4ecdc', '#d8ccb8')
        d.line([(wx + ww // 2, 12), (wx + ww // 2, 104)], fill=rgb('#3a2836'), width=2)
        d.line([(wx + 4, 62), (wx + ww - 4, 62)], fill=rgb('#3a2836'), width=2)
        # curtain
        d.polygon([(wx - 12, 100), (wx - 4, 20), (wx + 2, 24), (wx + 4, 100)],
                  fill=rgb('#5a2430'))
        d.polygon([(wx + ww - 2, 100), (wx + ww - 8, 24), (wx + ww + 6, 22),
                   (wx + ww + 12, 100)], fill=rgb('#5a2430'))
    # wall panels and a warm chandelier bloom
    for px in (110, 190):
        d.rectangle((px, 24, px + 2, 110), fill=rgb('#3d2a40'))
    d.rectangle((104, 20, 216, 23), fill=rgb('#3d2a40'))
    halo(bg, 160, 44, 24, 64, '#4a3244', step=5, skip=3)
    dither_disc(bg, 160, 46, 44, '#472f42', dens=6, parity=1)
    # floor
    d.rectangle((0, 112, W - 1, H - 1), fill=rgb(DN_FLOOR))
    d.line([(0, 112), (W - 1, 112)], fill=rgb('#7a5a62'))
    for y in range(114, H, 8):                           # floor boards
        d.line([(0, y), (W - 1, y)], fill=rgb('#4a343c'))
    for x in range(-40, W + 40, 46):
        d.line([(160 + (x - 160) * 0.4, 112), (x, H)], fill=rgb('#4a343c'))
    for x, y, rr in ((104, 134, 10), (226, 142, 12), (166, 156, 11)):
        dither_disc(bg, x, y, rr, '#6d4c56', dens=3)     # reflections of the lights
    for x, y in ((60, 60), (250, 72), (300, 40), (30, 96), (120, 84)):
        sparkle(d, x, y, 1, '#c9a0b8')
    for fill_box, colour in ((DN_COUPLE_R, DN_FLOOR), (DN_CHAND_R, DN_WALL),
                             (DN_NOTE_R, DN_WALL)):
        flat(bg, fill_box, colour)
    return bg


def build_dance():
    s = PS.Scheme(
        'px6-dance', '舞会',
        dict(family=FAMILY, tags=['舞会', '勇敢', '浪漫'],
             story='鼓起勇气请她跳一支舞，手心全是汗。音乐响起的第一秒，整个世界只剩下'
                   '两个人的脚步。'),
        '夜里的舞厅：高窗、吊灯和打磨过的地板。每次敲键，吊灯亮一些、两个人开始转圈，'
        '裙摆散开；敲得投入时他们旋转、音符飘起，久不碰键盘吊灯暗下来，只剩慢慢的'
        '拥抱式的慢舞。',
        ['#2e1f33', '#3d2a3a', '#f2d0c8', '#ff6f9f', '#ffd9a0', '#8a5a9a'],
        dance_bg())
    s.sticker('舞伴', DN_COUPLE_R[0], DN_COUPLE_R[1], dn_couple('calm'), '#2a1a24', DN_FLOOR,
              caps=dn_couple('caps'), caps_fg='#3a2430',
              react=dn_couple('react'), react_fg='#1f141c',
              sleepy=dn_couple('react'), sleepy_fg='#4a3540')
    s.sticker('吊灯', DN_CHAND_R[0], DN_CHAND_R[1], dn_chandelier('lit'), '#ffd9a0', DN_WALL,
              caps_fg='#ffe9bd', react_fg='#fff4d2',
              sleepy=dn_chandelier('sleepy'), sleepy_fg='#8a6a4a')
    s.sticker('音符', DN_NOTE_R[0], DN_NOTE_R[1], dn_notes('calm'), '#ffd0e2', DN_WALL,
              caps_fg='#ffb0c8',
              react=dn_notes('calm'), react_fg='#fff2f6',
              sleepy=dn_notes('sleepy'), sleepy_fg='#7a6070')
    s.set_effect('confetti', trigger='key', spawn=(130, 60, 60, 20), count=5, size=2,
                 colors=['#ff6f9f', '#ffd27a', '#ffd0e2', '#8ad0ff'], vx=(-90, 90),
                 vy=(-110, -30), gravity=130, life_ms=1500, edge='bounce', shape='square')
    s.set_pulse('吊灯', period_ms=2800, minimum=160)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=25000)
    s.statusInk = INK
    return s


BUILDERS = [build_sakura_love, build_love_letter, build_heartbeat,
            build_ferris_wheel, build_firefly, build_cafe_meet,
            build_sunset_beach, build_polaroid, build_dance]


# ---------------------------------------------------------------------- runner
def contact_sheet(built, path, frames=('preview-idle.png', 'preview-caps.png',
                                       'preview-react.png', 'preview-sleepy.png')):
    im = Image.new('RGB', (W * len(frames), H * len(built)), (14, 10, 20))
    for r, (_, d, _meta) in enumerate(built):
        for c, name in enumerate(frames):
            im.paste(Image.open(Path(d) / name), (c * W, r * H))
    im.save(path)
    print('sheet -> %s' % path)


def main(argv):
    only, sheet, i = [], None, 1
    while i < len(argv):
        a = argv[i]
        if a == '--sheet' and i + 1 < len(argv):
            sheet = argv[i + 1]
            i += 2
            continue
        if not a.startswith('--'):
            only.append(a)
        i += 1
    built = []
    for build in BUILDERS:
        scheme = build()
        if only and scheme.slug not in only and scheme.slug[4:] not in only:
            continue
        d, meta = scheme.save()
        built.append((scheme, d, meta))
        print('%-20s masks %4dB enc / %4dB dec  layers %d  rect %s'
              % (scheme.slug, meta['masks']['encodedBytes'], meta['masks']['decodedBytes'],
                 len(meta['layers']),
                 ' '.join('%dx%d' % (L['w'], L['h']) for L in meta['layers'])))
    if sheet and built:
        contact_sheet(built, sheet)
    return 0 if built else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
