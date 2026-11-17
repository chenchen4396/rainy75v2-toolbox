"""Fantasy/adventure family (幻想冒险) for the Rainy75 V2 320x172 IPS screen.

Eight interactive pixel schemes, all built with tools/pixel_scheme.py only:

    px6-space    太空      rocket drifting through a ringed-planet starfield
    px6-dungeon  地牢      portcullis gate, torches and a lit threshold
    px6-cyber    赛博霓虹  rain-soaked neon sign, window grid and puddle
    px6-forest   精灵森林  forest spirit, glowing mushrooms, fairy ring
    px6-arcade   街机      arcade cabinet, score screen, marquee and controls
    px6-mecha    机甲      idle mecha head, visor eye and reactor core
    px6-wizard   魔法师    floating wizard hat, staff crystal and rune circle
    px6-island   漂流岛    floating island, campfire, rowboat and moon

Every frame is a real mood: calm (baked into the asset), caps (powered-up),
react (typing momentum) and sleepy (idle rest).  Colours are deliberately muted;
no pure black or pure white is used.  Run:

    .venv/Scripts/python.exe tools/schemes/px6_fantasy.py
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-space' --dir build/design-gallery

SPDX-License-Identifier: MIT.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402

ATTR = '原创像素图形，全部由 tools/schemes/px6_fantasy.py 程序绘制'
WHITE_INK = '#f2ead8'


# --------------------------------------------------------------------------- helpers
def poly(g, pts, ch='#'):
    """Scanline-fill a polygon of float points into a Grid."""
    ys = [p[1] for p in pts]
    y0, y1 = int(math.floor(min(ys))), int(math.ceil(max(ys)))
    for y in range(y0, y1 + 1):
        yy = y + 0.5
        xs = []
        for i in range(len(pts)):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % len(pts)]
            if (ay <= yy < by) or (by <= yy < ay):
                xs.append(ax + (bx - ax) * (yy - ay) / (by - ay))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(int(round(xs[k])), int(round(xs[k + 1])) + 1):
                g.set(x, y, ch)


def ellipse(g, cx, cy, rx, ry, ch='#'):
    for y in range(int(cy - ry), int(cy + ry) + 1):
        dy = (y - cy) / float(ry)
        if abs(dy) > 1.0:
            continue
        half = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        for x in range(int(round(cx - half)), int(round(cx + half)) + 1):
            g.set(x, y, ch)


def carve_disc(g, cx, cy, r, ch='.'):
    for dy in range(-r, r + 1):
        half = int((r * r - dy * dy) ** 0.5)
        for dx in range(-half, half + 1):
            g.set(cx + dx, cy + dy, ch)


def star5(g, cx, cy, r, ch='#'):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    poly(g, pts, ch)


def sheared(g, k):
    """Lean a mask sideways: every row shifts by k*y."""
    out = Grid(g.w, g.h)
    for y in range(g.h):
        off = int(round(k * y))
        for x in range(g.w):
            if g.g[y][x] != '.':
                out.set(x + off, y)
    return out


def flame(g, cx, y0, widths, ch='#'):
    """Flame plume from a list of half-widths (top row first)."""
    for i, hw in enumerate(widths):
        g.hline(cx - hw, cx + hw - 1, y0 + i, ch)


def put(g, rows, x0, y0, ch='#'):
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == '#':
                g.set(x0 + x, y0 + y, ch)


def patch(im, ref, x, y, w, h, color=None):
    """Reserve one flat rectangle; returns its colour as '#rrggbb'.

    ``ref`` is the art-free base image used for colour sampling, so the patch
    blends into the scene instead of showing a random star or brick.
    """
    if color is None:
        color = ref.getpixel((x + w // 2, y + h // 2))
    if isinstance(color, str):
        color = PS.hexrgb(color)
    ImageDraw.Draw(im).rectangle((x, y, x + w - 1, y + h - 1), fill=tuple(color))
    return '#%02x%02x%02x' % tuple(color)


def bricks(d, x0, y0, x1, y1, fill, line, step_x=26, step_y=13):
    d.rectangle((x0, y0, x1, y1), fill=PS.hexrgb(fill))
    row = 0
    for y in range(y0, y1 + 1, step_y):
        d.line((x0, y, x1, y), fill=PS.hexrgb(line))
        off = (row % 2) * (step_x // 2)
        for x in range(x0 + off, x1 + 1, step_x):
            d.line((x, y, x, min(y1, y + step_y - 1)), fill=PS.hexrgb(line))
        row += 1


def grain(d, rng, count, x0, y0, x1, y1, colors, rmax=2):
    for _ in range(count):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        r = rng.randrange(1, rmax + 1)
        d.ellipse((x - r, y - r, x + r, y + r), fill=PS.hexrgb(rng.choice(colors)))


# =========================================================================== 太空
def space_rocket(state='calm'):
    g = Grid(36, 46)
    for i in range(0, 13):                      # nose cone
        half = 2.0 + i * 0.55
        g.hline(int(round(17.5 - half)), int(round(17.5 + half)), i)
    g.rect(9, 12, 26, 34)                       # hull
    g.hline(9, 26, 15, '.')                     # panel seams
    g.rect(9, 27, 26, 29, '.')
    g.disc(18, 20, 4, '.')                      # window hole
    poly(g, [(9, 25), (2, 38), (2, 43), (9, 37)])        # fins
    poly(g, [(26, 25), (33, 38), (33, 43), (26, 37)])
    g.rect(12, 36, 23, 44)                      # engine block
    g.rect(15, 40, 20, 44, '.')
    g.hline(11, 24, 35, '.')
    if state == 'react':
        g = sheared(g, 0.11)
    elif state == 'sleep':
        g.disc(18, 20, 4)                       # window shuttered
        g.rect(15, 40, 20, 44)                  # engine shut
    return g


def space_flame(state):
    g = Grid(24, 30)
    if state == 'off':
        return g
    widths = ([4, 5, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 1] if state == 'calm' else
              [5, 7, 9, 10, 10, 9, 8, 7, 6, 6, 5, 4, 3, 3, 2, 2, 1])
    flame(g, 12, 3, widths)
    if state == 'big':
        for dy, (a, b) in enumerate(((1, 4), (0, 4), (1, 3))):
            g.hline(a, b, 7 + dy)
            g.hline(23 - b, 23 - a, 7 + dy)
    return g


def space_window(state):
    g = Grid(12, 12)
    c = 5
    if state == 'calm':
        g.ring(c, c, 4)
        g.set(c, c)
    elif state == 'caps':
        g.disc(c, c, 4)
        for r in (0, 1):
            g.set(c - 5 - r, c)
            g.set(c + 5 + r, c)
            g.set(c, c - 5 - r)
            g.set(c, c + 5 + r)
    elif state == 'react':
        g.disc(c, c, 3)
        g.line(c - 5, c, c + 5, c)
        g.line(c, c - 5, c, c + 5)
        for dx, dy in ((4, 4), (4, -4), (-4, 4), (-4, -4)):
            g.set(c + dx, c + dy)
    else:
        g.ring(c, c, 2)
        g.hline(c - 2, c + 2, c)
    return g


def space_planet(state):
    g = Grid(36, 36)
    cx, cy, r = 18, 18, 12
    if state == 'sleep':
        g.disc(cx, cy, r)
        carve_disc(g, cx + 6, cy - 4, r)
        return g
    g.disc(cx, cy, r)
    g.disc(14, 14, 2, '.')
    g.disc(22, 20, 2, '.')
    g.disc(16, 24, 1, '.')
    for x in range(0, 36):
        yb = cy + (x - cx) * -0.42
        yf = cy + (x - cx) * 0.42
        if math.hypot(x - cx, yb - cy) > r + 1:
            g.set(x, yb)
            g.set(x, yb + 1)
        if math.hypot(x - cx, yf - cy) > r + 1:
            g.set(x, yf)
            g.set(x, yf + 1)
    if state == 'caps':
        for dx, dy in ((2, 8), (33, 27), (4, 28), (31, 7), (0, 17), (35, 19)):
            g.set(dx, dy)
    return g


def build_space():
    bg = PS.vgrad('#060a1c', '#141d42', bands=14)
    ref = bg.copy()
    PS.stars(bg, 76, '#dfe8ff', seed=12, size2=5)
    d = ImageDraw.Draw(bg)
    rng = random.Random(31)
    grain(d, rng, 130, 0, 0, 320, 118, ('#121a3c', '#17204a', '#1c2454', '#241f4e'), 3)
    for i in range(28):                                   # comet tail
        d.point((26 + i * 4, 24 + i * 2),
                fill=PS.hexrgb('#8fa6ea' if i % 3 == 0 else '#57689c'))
    PS.moon(bg, 33, 46, 9, '#e8efff', '#c0c9e6')
    d.ellipse((-92, 128, 98, 332), fill=PS.hexrgb('#0b1330'))
    d.arc((-92, 128, 98, 332), 290, 352, fill=PS.hexrgb('#2c3f7c'), width=2)
    for x, y, r in ((196, 138, 3), (214, 152, 2), (286, 150, 2), (168, 158, 2)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=PS.hexrgb('#1a2248'))
    rocket_bg = patch(bg, ref, 58, 56, 36, 46)
    win_bg = patch(bg, ref, 69, 69, 12, 12, rocket_bg)
    flame_bg = patch(bg, ref, 64, 102, 24, 30)
    planet_bg = patch(bg, ref, 250, 86, 36, 36)
    s = PS.Scheme(
        'px6-space', '星际漂流',
        dict(family='幻想冒险', tags=['远行', '探索', '星海'],
             story='它只是一枚很小的探测器，带着一封没人读过的信，慢慢飞过没有尽头的星海。'),
        '深蓝星海里，一枚小小的探测器独自漂向远方：碎星、彗尾和远处一颗带环的行星陪着它。'
        '每一次按键，尾焰就喷出一簇闪烁的星尘；CapsLock 亮起时舷窗和行星环一起发光；'
        '久不碰键盘，它会熄火，蜷在星海里打盹。',
        ['#060a1c', '#141d42', '#0b1330', '#cfe0ff', '#ffcf7a', '#8fd6ff', '#f2f0ff'],
        bg, ATTR)
    s.sticker('火箭', 58, 56, space_rocket('calm'), '#cfe0ff', rocket_bg,
              caps_fg='#f2f8ff', react=space_rocket('react'), react_fg='#dfe9ff',
              sleepy=space_rocket('sleep'), sleepy_fg='#7d8db4')
    s.sticker('尾焰', 64, 102, space_flame('calm'), '#ffcf7a', flame_bg,
              caps=space_flame('big'), caps_fg='#ffd98a',
              react=space_flame('big'), react_fg='#ffb347',
              sleepy=space_flame('off'), sleepy_fg='#5c4a3a')
    s.sticker('行星', 250, 86, space_planet('calm'), '#9db8ff', planet_bg,
              caps=space_planet('caps'), caps_fg='#c9d9ff',
              react_fg='#b7c8ff',
              sleepy=space_planet('sleep'), sleepy_fg='#6b7fb8')
    s.sticker('舷窗', 69, 69, space_window('calm'), '#7fe6ff', win_bg,
              caps=space_window('caps'), caps_fg='#c9f8ff',
              react=space_window('react'), react_fg='#ffe9a8',
              sleepy=space_window('sleep'), sleepy_fg='#5f7fa6')
    s.set_effect('dust', trigger='key', spawn=(62, 100, 26, 8), count=5, size=1,
                 colors=['#c9f2ff', '#fff3c4', '#a9c4ff'], vx=(-30, 30),
                 vy=(-42, -12), gravity=-6, life_ms=2200, edge='wrap')
    s.set_pulse('舷窗', period_ms=2200, minimum=150)
    s.set_reaction(reactHoldMs=850, sleepyAfterMs=22000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 地牢
def dungeon_gate(state):
    g = Grid(56, 58)
    bars = (8, 19, 30, 41, 52)
    if state == 'open':
        for x in bars:
            g.vline(x, 0, 14, '#', 4)
            for i in range(4):
                g.set(x + i, 15)
            g.set(x + 1, 16)
            g.set(x + 2, 16)
        g.hline(2, 54, 5)
        g.hline(2, 54, 13)
        g.vline(2, 0, 8, '#', 2)
        g.vline(51, 0, 8, '#', 2)
        return g
    for x in bars:
        g.vline(x, 2, 47, '#', 4)
        for i in range(4):
            g.set(x + i, 48)
        g.set(x + 1, 49)
        g.set(x + 2, 49)
        g.set(x + 1, 50)
    g.hline(2, 54, 11, '#', 2)
    g.hline(2, 54, 36, '#', 2)
    for x in bars:
        g.set(x + 1, 7)
        g.set(x + 1, 30)
        g.set(x + 1, 44)
    if state == 'react':
        g.rect(1, 20, 27, 31, '.')
        g.rect(31, 20, 54, 31, '.')
        for x in bars:
            g.set(x, 18)
            g.set(x + 3, 18)
            g.set(x, 33)
            g.set(x + 3, 33)
        g.rect(25, 19, 29, 25)
        g.rect(30, 27, 34, 32)
        g.set(3, 42)
        g.set(9, 44)
        g.set(44, 41)
        g.set(50, 43)
    return g


def dungeon_light(state):
    g = Grid(40, 14)
    if state == 'none':
        return g
    if state == 'open':
        for y in range(14):
            w = 4 + y
            g.hline(20 - w, 19 + w, y)
        for x in range(3, 38, 3):
            g.set(x, 13 - (x % 4))
        return g
    # react: a glowing ward circle on the threshold
    ellipse(g, 20, 9, 14, 3, '#')
    thin = Grid(40, 14)
    ellipse(thin, 20, 9, 11, 2)
    for y in range(14):
        for x in range(40):
            if thin.g[y][x] != '.':
                g.set(x, y, '.')
    star5(g, 20, 9, 4)
    for i in range(6):
        a = i * math.pi / 3
        g.set(20 + math.cos(a) * 16, 8 + math.sin(a) * 4.2)
    return g


def dungeon_torch(state):
    g = Grid(26, 34)
    if state == 'off':
        return g
    prof = {'calm': [2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 6],
            'big': [2, 3, 4, 5, 6, 6, 7, 8, 8, 9, 9, 8]}
    widths = prof[state if state in prof else 'calm']
    top = 30 - len(widths)
    flame(g, 13, top, widths)
    g.rect(11, 30, 15, 33)                             # ember base
    if state == 'big':
        for x, y in ((5, top - 2), (20, top - 4), (12, top - 5), (2, top + 1),
                     (23, top + 2)):
            g.set(x, y)
    return g


def build_dungeon():
    bg = Image.new('RGB', PS.SIZE, PS.hexrgb('#232836'))
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    bricks(d, 0, 0, 319, 150, '#262b38', '#1c212b', step_x=26, step_y=13)
    rng = random.Random(77)
    for _ in range(70):
        x = rng.randrange(4, 300, 4)
        y = rng.randrange(6, 142, 4)
        if rng.random() < 0.5:
            d.line((x, y, x + rng.choice((-16, -12, 12, 16)), y),
                   fill=PS.hexrgb('#2d3342'))
    # stone arch around a dark recess
    d.ellipse((118, 42, 202, 126), fill=PS.hexrgb('#3a4252'))
    d.rectangle((118, 84, 202, 138), fill=PS.hexrgb('#3a4252'))
    d.ellipse((128, 52, 192, 116), fill=PS.hexrgb('#0c1018'))
    d.rectangle((128, 84, 192, 138), fill=PS.hexrgb('#0c1018'))
    for i in range(9):                                     # voussoir seams
        a = math.pi + i * math.pi / 8
        d.line((160 + math.cos(a) * 32, 84 + math.sin(a) * 32,
                160 + math.cos(a) * 41, 84 + math.sin(a) * 41),
               fill=PS.hexrgb('#2b3240'), width=2)
    d.rectangle((118, 84, 202, 86), fill=PS.hexrgb('#4a5364'))
    d.rectangle((118, 84, 128, 138), fill=PS.hexrgb('#333a48'))
    d.rectangle((192, 84, 202, 138), fill=PS.hexrgb('#333a48'))
    d.rectangle((156, 42, 164, 52), fill=PS.hexrgb('#4a5364'))   # keystone
    # flagstone floor
    d.rectangle((0, 134, 319, 171), fill=PS.hexrgb('#20252f'))
    for y in (142, 152, 163):
        d.line((0, y, 319, y), fill=PS.hexrgb('#171b23'))
    for y in (137, 147, 157, 168):
        for x in range(0, 320, 34):
            xx = x + (y % 7) * 3
            d.line((xx, y, xx, min(171, y + 9)), fill=PS.hexrgb('#171b23'))
    for x, y in ((30, 150), (112, 158), (212, 148), (278, 162), (66, 165)):
        d.ellipse((x, y, x + 20, y + 7), fill=PS.hexrgb('#282e3a'))
        d.line((x + 1, y + 1, x + 18, y + 1), fill=PS.hexrgb('#333a48'))
    # recessed torch niches
    for tx in (92, 200):
        d.rectangle((tx, 64, tx + 26, 98), fill=PS.hexrgb('#161a23'))
        d.rectangle((tx, 64, tx + 26, 67), fill=PS.hexrgb('#2a303c'))
        d.rectangle((tx - 1, 63, tx + 27, 99), outline=PS.hexrgb('#333a48'))
    # torch brackets
    for tx in (92, 200):
        d.rectangle((tx + 10, 98, tx + 16, 132), fill=PS.hexrgb('#1a1e28'))
        d.rectangle((tx + 8, 98, tx + 18, 102), fill=PS.hexrgb('#2a2f3c'))
        d.line((tx + 11, 108, tx + 15, 108), fill=PS.hexrgb('#3a4150'))
        d.line((tx + 11, 116, tx + 15, 116), fill=PS.hexrgb('#3a4150'))
        glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((tx - 6, 62, tx + 32, 108), fill=(255, 176, 88, 18))
        bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    d.arc((118, 42, 202, 126), 180, 360, fill=PS.hexrgb('#4d5668'), width=3)
    # side plinths at the threshold
    for x0, x1 in ((118, 132), (188, 202)):
        d.rectangle((x0, 124, x1, 134), fill=PS.hexrgb('#2c3342'))
        d.line((x0, 124, x1, 124), fill=PS.hexrgb('#3d4556'))
    # chains
    for cx in (110, 212):
        for y in range(0, 34, 4):
            d.ellipse((cx - 2, y, cx + 2, y + 3), outline=PS.hexrgb('#3a4150'))
    # cobwebs in the top corners
    for flip in (0, 1):
        for i in range(18):
            x0 = 38 - i * 2 if flip == 0 else 282 + i * 2
            d.line((x0, 0, 38 if flip == 0 else 282, i * 2), fill=PS.hexrgb('#2c323f'))
        for rr in (10, 22, 34):
            cx, cy = (0, 0) if flip == 0 else (319, 0)
            d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 0, 90, fill=PS.hexrgb('#2c323f'))
    # floor clutter: rubble, a shield and a broken blade
    for x, y, w in ((20, 148, 14), (150, 166, 10), (240, 152, 12), (286, 164, 8)):
        d.polygon([(x, y), (x + w // 2, y - 6), (x + w, y)], fill=PS.hexrgb('#2b3240'))
        d.line((x, y, x + w, y), fill=PS.hexrgb('#3a4252'))
    d.polygon([(252, 140), (268, 140), (270, 158), (260, 166), (250, 158)],
              fill=PS.hexrgb('#3a3242'))
    d.line((260, 142, 260, 164), fill=PS.hexrgb('#54495e'))
    d.line((250, 150, 270, 150), fill=PS.hexrgb('#54495e'))
    d.line((286, 168, 304, 144), fill=PS.hexrgb('#4a5364'), width=2)
    d.line((304, 144, 310, 140), fill=PS.hexrgb('#5c6a80'))
    # moss in the damp corners
    for _ in range(40):
        x = rng.randrange(0, 320)
        y = rng.randrange(126, 172)
        if 126 <= x <= 200 and y < 140:
            continue
        d.point((x, y), fill=PS.hexrgb(rng.choice(('#2c3a2a', '#33402c', '#24322a'))))
    gate_bg = patch(bg, ref, 132, 70, 56, 58, '#0c1018')
    light_bg = patch(bg, ref, 140, 134, 40, 14, '#20252f')
    left_bg = patch(bg, ref, 92, 64, 26, 34, '#161a23')
    right_bg = patch(bg, ref, 200, 64, 26, 34, '#161a23')
    vin = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vin)
    for k, a in ((0, 70), (1, 46), (2, 26)):
        vd.rectangle((k * 7, k * 5, 319 - k * 7, 171 - k * 5),
                     outline=(8, 10, 16, a), width=7)
    bg.paste(vin, (0, 0), vin)
    s = PS.Scheme(
        'px6-dungeon', '地牢之门',
        dict(family='幻想冒险', tags=['守夜', '试炼', '回响'],
             story='铁栅门后的走廊很深，火把把石砖烘得暖暖的。今晚轮到你守夜，键盘声是唯一的动静。'),
        '古老城堡的地下石廊里，铁栅门沉沉落着，两侧火把把砖缝照成暖色。'
        '每敲一键，火把就迸出一簇向上飘的火星；CapsLock 亮起，铁栅门升起、门内透出走廊的暖光；'
        '久不输入，火把慢慢熄下去，门也重新落下。',
        ['#141826', '#262b38', '#0c1018', '#ffcf7a', '#ff8a4a', '#8b95a8', WHITE_INK],
        bg, ATTR)
    s.sticker('铁栅门', 132, 70, dungeon_gate('calm'), '#8b95a8', gate_bg,
              caps=dungeon_gate('open'), caps_fg='#b9c3d2',
              react=dungeon_gate('react'), react_fg='#a3adbd',
              sleepy_fg='#5c6676')
    s.sticker('门内光', 140, 134, dungeon_light('none'), '#ffcf7a', light_bg,
              caps=dungeon_light('open'), caps_fg='#ffd98a',
              react=dungeon_light('ward'), react_fg='#8fd6ff',
              sleepy=Grid(40, 14), sleepy_fg='#3a2f24')
    s.sticker('火把左', 92, 64, dungeon_torch('calm'), '#ffb347', left_bg,
              caps=dungeon_torch('big'), caps_fg='#ffd98a',
              react=dungeon_torch('big'), react_fg='#fff2c8',
              sleepy=dungeon_torch('off'), sleepy_fg='#3a2f24')
    s.sticker('火把右', 200, 64, dungeon_torch('calm'), '#ffb347', right_bg,
              caps=dungeon_torch('big'), caps_fg='#ffd98a',
              react=dungeon_torch('big'), react_fg='#fff2c8',
              sleepy=dungeon_torch('off'), sleepy_fg='#3a2f24')
    s.set_effect('ember', trigger='key', spawn=(94, 96, 124, 10), count=4, size=2,
                 colors=['#ffcf7a', '#ff8a4a', '#ffe9b0'], vx=(-24, 24),
                 vy=(-56, -22), gravity=-6, life_ms=2200)
    s.set_pulse('火把左', period_ms=1800, minimum=150)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=24000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 赛博霓虹
def cyber_sign(state):
    g = Grid(70, 40)
    g.rect(0, 0, 69, 39, fill=False, thick=2)
    g.rect(4, 4, 65, 35, fill=False, thick=1)
    if state == 'sleep':
        return g
    if state == 'glitch':
        g.rect(22, 2, 26, 37, '.')
        g.rect(45, 2, 48, 37, '.')
        for y in range(4, 19, 4):
            g.hline(2, 15, y, '.')
        poly(g, [(35, 4), (24, 15), (32, 15), (27, 21), (43, 11), (34, 11), (39, 4)])
        g.text('ERR!', 12, 21, scale=2)
        for x, y in ((6, 8), (60, 28), (10, 32)):
            star5(g, x, y, 2)
        return g
    poly(g, [(35, 4), (25, 14), (32, 14), (28, 19), (43, 10), (34, 10), (39, 4)])
    if state == 'caps':
        poly(g, [(35, 3), (23, 14), (31, 14), (26, 21), (44, 9), (34, 9), (41, 3)])
        g.hline(2, 67, 1)
        g.hline(2, 67, 38)
        for x in range(4, 67, 6):
            g.set(x, 2)
            g.set(x, 37)
        g.text('CYBER', 6, 21, scale=2)
        return g
    g.text('CYBER', 6, 21, scale=2)
    return g


def cyber_windows(state):
    g = Grid(40, 28)
    if state == 'off':
        return g
    cells = [(x, y) for y in (3, 10, 17, 24) for x in (4, 12, 20, 28, 36)]
    lit = cells if state == 'all' else [
        c for i, c in enumerate(cells)
        if i not in (2, 5, 9, 13, 16, 19)]
    for x, y in lit:
        g.rect(x, y, x + 3, y + 3)
    return g


def cyber_puddle(state):
    g = Grid(72, 14)
    if state == 'off':
        return g
    rows = (3, 7, 11) if state == 'calm' else (2, 4, 6, 8, 10, 12)
    for i, y in enumerate(rows):
        x = (i * 11) % 17
        while x < 70:
            g.hline(x, min(70, x + 5), y)
            x += 15 + (i * 3) % 7
    if state == 'caps':
        g.vline(34, 0, 13, '#', 2)
        g.vline(36, 0, 13, '#', 2)
        g.set(34, 1)
        g.set(37, 1)
    return g


def build_cyber():
    bg = PS.vgrad('#0a0718', '#1a1038', bands=12)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    rng = random.Random(9)
    PS.stars(bg, 22, '#6d7fc0', seed=4, area=(0, 0, 320, 62), size2=7)
    # near-left block, right block and a row of distant towers
    d.rectangle((0, 64, 126, 150), fill=PS.hexrgb('#060412'))
    d.rectangle((0, 64, 126, 66), fill=PS.hexrgb('#4a3a7a'))
    d.rectangle((232, 58, 319, 150), fill=PS.hexrgb('#050310'))
    d.rectangle((232, 58, 319, 60), fill=PS.hexrgb('#4a3a7a'))
    d.line((232, 58, 232, 150), fill=PS.hexrgb('#2a2050'))
    d.line((0, 64, 126, 64), fill=PS.hexrgb('#2a2050'))
    for x0, top in ((128, 78), (160, 66), (190, 86), (204, 74), (220, 90)):
        d.rectangle((x0, top, x0 + 30, 150), fill=PS.hexrgb('#04030e'))
        d.line((x0, top, x0 + 30, top), fill=PS.hexrgb('#4a3a7a'))
    for x0, top, c in ((128, 78, '#ff4fa8'), (160, 66, '#5fe0ff'), (204, 74, '#b48cff')):
        d.line((x0 + 15, top, x0 + 15, top - 16), fill=PS.hexrgb('#2a2050'))
        d.point((x0 + 15, top - 17), fill=PS.hexrgb(c))
    # lit windows on the near blocks
    for bx0, by0 in ((8, 72), (240, 68)):
        for ci in range(6):
            for ri in range(5):
                if rng.random() < 0.5:
                    x = bx0 + ci * 18
                    y = by0 + ri * 15
                    d.rectangle((x, y, x + 5, y + 6),
                                fill=PS.hexrgb(rng.choice(('#ffd98a', '#ff9ad0',
                                                           '#8ff0ff', '#b48cff'))))
    # billboard panel on the left roof (the sign rect sits flat on it)
    d.rectangle((24, 46, 110, 100), fill=PS.hexrgb('#150f2e'))
    d.rectangle((24, 46, 110, 100), outline=PS.hexrgb('#2a1e4a'))
    for x in (34, 62, 90):
        d.line((x, 100, x, 114), fill=PS.hexrgb('#1b1436'))
    # far windows
    for _ in range(150):
        x = rng.randrange(0, 320)
        y = rng.randrange(58, 146)
        d.point((x, y), fill=PS.hexrgb(rng.choice(('#4a3a7a', '#2a4a88',
                                                  '#6a4a8a', '#8a5a7a'))))
    # distant neon strips
    for x, c, y0, y1 in ((6, '#ff4fa8', 74, 98), (132, '#5fe0ff', 60, 96),
                         (168, '#b48cff', 74, 100), (246, '#ff4fa8', 64, 88),
                         (306, '#5fe0ff', 66, 104)):
        d.line((x, y0, x, y1), fill=PS.hexrgb(c))
        d.line((x + 1, y0, x + 1, y1), fill=PS.hexrgb(c))
    # wet street
    d.rectangle((0, 146, 319, 171), fill=PS.hexrgb('#0b0b1e'))
    d.line((0, 146, 319, 146), fill=PS.hexrgb('#171330'))
    for x in (12, 60, 148, 196, 258, 300):
        d.line((x, 150, x, 171), fill=PS.hexrgb('#141232'))
    for _ in range(80):
        x = rng.randrange(0, 320)
        y = rng.randrange(150, 172)
        d.point((x, y), fill=PS.hexrgb(rng.choice(('#2a2450', '#3a2a68'))))
    # neon reflection smeared on the wet pavement
    for x, c, top in ((38, '#ff5fb0', 156), (52, '#ff5fb0', 160), (70, '#5fe0ff', 158),
                      (84, '#ff5fb0', 164), (262, '#ffd98a', 158), (276, '#5fe0ff', 162)):
        for y in range(top, min(171, top + 8), 2):
            d.line((x, y, x + 3, y), fill=PS.hexrgb(c))
    # railing on the right sidewalk + a hydrant on the left
    for x in (286, 302, 318):
        d.line((x, 122, x, 150), fill=PS.hexrgb('#2a2050'))
    d.line((284, 126, 319, 126), fill=PS.hexrgb('#3a2a68'))
    d.line((284, 136, 319, 136), fill=PS.hexrgb('#2a2050'))
    d.rectangle((10, 134, 17, 146), fill=PS.hexrgb('#5a2a3a'))
    d.rectangle((8, 132, 19, 135), fill=PS.hexrgb('#7a3a4a'))
    # steam vent
    for i in range(10):
        d.point((204 + (i * 3) % 9, 146 - i * 2), fill=PS.hexrgb('#2a2450'))
    PS.rain(bg, 78, '#33406e', seed=5, angle=1)
    PS.rain(bg, 24, '#7b9bd8', seed=6, angle=1)
    sign_bg = patch(bg, ref, 31, 51, 70, 40, '#150f2e')
    win_bg = patch(bg, ref, 232, 92, 40, 28, '#0a071e')
    puddle_bg = patch(bg, ref, 116, 148, 72, 14, '#0b0b1e')
    s = PS.Scheme(
        'px6-cyber', '霓虹雨夜',
        dict(family='幻想冒险', tags=['夜行', '电流', '雨'],
             story='雨把整条街泡成一面镜子，只有那块旧霓虹还固执地亮着，等一个晚归的人。'),
        '深夜的赛博城区下着雨，高架桥下的霓虹牌滋着电流，对面楼里的窗格明明灭灭。'
        '每敲一键，霓虹就跟着闪一下，雨丝被染成粉蓝；CapsLock 亮起，招牌、窗格和积水里一齐通电；'
        '你离开后，霓虹一盏盏暗下去，只剩雨声。',
        ['#0a0718', '#150f2e', '#0b0b1e', '#ff4fa8', '#5fe0ff', '#b48cff', '#f2e6ff'],
        bg, ATTR)
    s.sticker('霓虹牌', 31, 51, cyber_sign('calm'), '#ff5fb0', sign_bg,
              caps=cyber_sign('caps'), caps_fg='#ff9ad0',
              react=cyber_sign('glitch'), react_fg='#8ff0ff',
              sleepy_fg='#4a2a5a')
    s.sticker('窗格', 232, 92, cyber_windows('calm'), '#ffd98a', win_bg,
              caps=cyber_windows('all'), caps_fg='#8ff0ff',
              react_fg='#ff9ad0',
              sleepy=cyber_windows('off'), sleepy_fg='#4a3a5a')
    s.sticker('积水', 116, 148, cyber_puddle('calm'), '#ff5fb0', puddle_bg,
              caps=cyber_puddle('caps'), caps_fg='#8ff0ff',
              react=cyber_puddle('caps'), react_fg='#ff9ad0',
              sleepy=cyber_puddle('off'), sleepy_fg='#3a2a44')
    s.set_effect('rain', trigger='key', spawn=(8, 34, 216, 12), count=7, size=1,
                 colors=['#7be7ff', '#ff6fd8', '#e0d4ff'], vx=(-14, 6),
                 vy=(100, 150), gravity=0, life_ms=1300)
    s.set_pulse('霓虹牌', period_ms=1600, minimum=130)
    s.set_reaction(reactHoldMs=800, sleepyAfterMs=20000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 精灵森林
SPIRIT_BODY = [
    (0, 15, 16), (1, 14, 17), (2, 12, 19), (3, 11, 20), (4, 10, 21),
    (5, 9, 22), (6, 9, 22), (7, 9, 22), (8, 9, 22), (9, 9, 22), (10, 9, 22),
    (11, 10, 21), (12, 10, 21), (13, 10, 21), (14, 9, 22), (15, 8, 23),
    (16, 7, 24), (17, 7, 24), (18, 6, 25), (19, 6, 25), (20, 6, 25),
    (21, 5, 26), (22, 5, 26), (23, 5, 26), (24, 4, 27), (25, 4, 27),
    (26, 4, 27), (27, 4, 27), (28, 4, 27), (29, 4, 27), (30, 3, 28),
    (31, 3, 28), (32, 4, 27), (33, 5, 26), (34, 6, 25),
    (35, 7, 12), (36, 8, 11), (37, 9, 10), (38, 10, 11),
    (35, 19, 24), (36, 20, 23), (37, 21, 22), (38, 21, 22),
]


def forest_spirit(state):
    g = Grid(32, 42)
    if state == 'sleep':
        g.disc(16, 27, 11)
        g.disc(16, 13, 7)
        g.hline(11, 13, 13, '.')
        g.hline(18, 20, 13, '.')
        g.line(24, 34, 30, 40)
        g.set(31, 38)
        g.set(28, 37)
        return g
    for y, a, b in SPIRIT_BODY:                        # hooded head + A-line robe
        g.hline(a, b, y)
    g.rect(11, 7, 12, 9, '.')                           # eyes
    g.rect(19, 7, 20, 9, '.')
    if state == 'calm':
        poly(g, [(9, 15), (1, 23), (9, 27)])           # folded wings
        poly(g, [(23, 15), (31, 23), (23, 27)])
    else:
        poly(g, [(9, 13), (0, 6), (1, 28), (9, 25)])   # spread wings
        poly(g, [(23, 13), (32, 6), (31, 28), (23, 25)])
        for i in range(12):
            a = math.pi * 2 * i / 12
            x = 16 + math.cos(a) * 13
            y = 11 + math.sin(a) * 13
            g.set(x, y)
    if state == 'react':
        for x, y in ((3, 34), (28, 35), (1, 20), (30, 21), (10, 1), (23, 1),
                     (5, 9), (27, 32)):
            g.set(x, y)
            g.set(x + 1, y)
    return g


def forest_mushrooms(state):
    g = Grid(42, 30)
    big = state == 'big'
    cx, cy, rx, ry = 14, 15 if not big else 14, 10 if big else 8, 6 if big else 5
    ellipse(g, cx, cy, rx, ry)
    g.rect(11, cy, 16, 28)
    for x in range(8, 21, 2):                          # gills carved under the cap
        g.set(x, cy + 4, '.')
    ellipse(g, 29, 17, 7, 4)
    g.rect(27, 17, 30, 28)
    ellipse(g, 38, 20, 4, 3)
    g.rect(37, 20, 39, 28)
    if big:
        ellipse(g, 3, 24, 3, 2)
        g.rect(2, 24, 4, 28)
        for x, y in ((14, 6), (22, 8), (30, 10), (35, 13), (6, 18)):
            g.set(x, y)
    return g


def forest_ring(state):
    g = Grid(56, 16)
    n = 20 if state == 'calm' else 32
    for i in range(n):
        a = math.pi * 2 * i / n
        x = 28 + math.cos(a) * 24
        y = 8 + math.sin(a) * 5
        g.set(x, y)
        if state == 'caps' and i % 3 == 0:
            g.set(x, y - 1)
    for i in range(5):
        a = math.pi * 2 * i / 5 - math.pi / 2
        if state == 'caps':
            star5(g, 28 + math.cos(a) * 15, 8 + math.sin(a) * 3, 2)
        else:
            g.set(28 + math.cos(a) * 15, 8 + math.sin(a) * 3)
    return g


def forest_hollow(state):
    g = Grid(24, 26)
    if state == 'sleep':
        g.hline(2, 9, 12)
        g.hline(14, 21, 11)
        g.set(1, 13)
        g.set(10, 13)
        g.set(13, 12)
        g.set(22, 12)
        return g
    for cx in (7, 17):
        ellipse(g, cx, 12, 4, 3)
        g.rect(cx - 1, 11, cx + 1, 13, '.')
    if state == 'caps':
        for cx in (7, 17):
            ellipse(g, cx, 11, 6, 4)
            g.rect(cx - 1, 10, cx + 1, 12, '.')
        g.set(11, 20)
        g.set(13, 20)
    return g


def build_forest():
    bg = PS.vgrad('#06120e', '#0f2419', bands=13)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    rng = random.Random(41)
    PS.stars(bg, 26, '#9fd6b8', seed=8, area=(0, 0, 320, 64), size2=8)
    # big backdrop trunk behind the spirit
    d.polygon([(58, 0), (154, 0), (162, 172), (52, 172)], fill=PS.hexrgb('#0a1710'))
    d.line((72, 0, 68, 172), fill=PS.hexrgb('#0e2016'))
    d.line((140, 0, 145, 172), fill=PS.hexrgb('#0e2016'))
    # distant trunks
    for x, w in ((18, 12), (190, 16), (226, 9), (252, 20), (300, 14)):
        d.rectangle((x, 0, x + w, 172), fill=PS.hexrgb('#0b1a12'))
        d.line((x + 2, 0, x + 2, 172), fill=PS.hexrgb('#16301f'))
    # canopy: dark mass, irregular leaf clumps and hanging leaves
    d.polygon([(0, 0), (320, 0), (320, 34), (292, 40), (268, 30), (240, 44),
               (214, 32), (188, 46), (160, 34), (132, 48), (104, 36), (76, 50),
               (48, 38), (22, 50), (0, 40)], fill=PS.hexrgb('#08160f'))
    for _ in range(64):
        x = rng.randrange(0, 320)
        y = rng.randrange(0, 56)
        rx = rng.randrange(5, 14)
        ry = rng.randrange(3, 7)
        c = rng.choice(('#0b1d13', '#0e2417', '#0a1910'))
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=PS.hexrgb(c))
    for x in range(0, 320, 3):
        edge = 28 + int(9 * math.sin(x * 0.11) + 6 * math.sin(x * 0.031))
        for k in range(rng.randrange(1, 4)):
            d.point((x, edge + k * 3), fill=PS.hexrgb('#123020'))
    for pts, w in (([(40, 44), (96, 30), (150, 38)], 3),
                   ([(250, 52), (300, 34), (320, 40)], 3),
                   ([(120, 62), (150, 50)], 2)):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d.line((x0, y0, x1, y1), fill=PS.hexrgb('#0d2016'), width=w)
    # light shafts
    for x0, x1 in ((8, 44), (196, 232), (274, 310)):
        for y in range(0, 120, 2):
            d.point((x0 + (y * 3) % (x1 - x0), y), fill=PS.hexrgb('#1c3a26'))
    # mist bands
    for y, c in ((96, '#13291c'), (118, '#16311f'), (134, '#173522')):
        for x in range(0, 320, 2):
            if (x + y) % 4 < 2:
                d.point((x, y + ((x // 20) % 3)), fill=PS.hexrgb(c))
    # foreground trunks
    d.polygon([(0, 0), (26, 0), (20, 172), (0, 172)], fill=PS.hexrgb('#07130c'))
    d.line((21, 0, 16, 172), fill=PS.hexrgb('#183121'))
    d.polygon([(296, 0), (319, 0), (319, 172), (306, 172)], fill=PS.hexrgb('#07130c'))
    d.line((305, 0, 307, 172), fill=PS.hexrgb('#183121'))
    # ground
    d.rectangle((0, 148, 319, 171), fill=PS.hexrgb('#08150f'))
    for y in (150, 156, 164):
        d.line((0, y, 319, y), fill=PS.hexrgb('#0c1d14'))
    for _ in range(46):                                  # grass tufts
        x = rng.randrange(0, 320)
        y = rng.randrange(150, 171)
        d.line((x, y, x + rng.choice((-2, -1, 1, 2)), y - rng.randrange(2, 6)),
               fill=PS.hexrgb(rng.choice(('#13291c', '#1b3a24'))))
    for x, y, r in ((56, 154, 4), (94, 166, 3), (156, 158, 4), (238, 164, 3),
                    (282, 152, 4), (196, 160, 3)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=PS.hexrgb('#101f28'))
        d.line((x - r + 1, y - r + 1, x + r - 1, y - r + 1), fill=PS.hexrgb('#2a3a44'))
    for _ in range(16):                                  # bg fireflies
        x, y = rng.randrange(0, 320), rng.randrange(60, 148)
        d.point((x, y), fill=PS.hexrgb(rng.choice(('#a8e08a', '#6fbf7a'))))
    # tree hollow: dark mouth with a bark rim (the eye sticker sits flat inside)
    d.ellipse((246, 90, 280, 124), fill=PS.hexrgb('#1d3324'))
    d.ellipse((249, 93, 277, 121), fill=PS.hexrgb('#0a1210'))
    for yy in (96, 101, 114, 118):
        d.line((247, yy, 250, yy + 2), fill=PS.hexrgb('#2c4a34'))
    # soft mushroom light on the ground
    glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((170, 118, 250, 168), fill=(120, 255, 170, 26))
    bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    spirit_bg = patch(bg, ref, 88, 64, 32, 42, '#0a1710')
    mush_bg = patch(bg, ref, 188, 118, 42, 30, '#0a1a12')
    ring_bg = patch(bg, ref, 56, 138, 56, 16, '#08150f')
    hollow_bg = patch(bg, ref, 252, 94, 24, 26, '#0a1210')
    s = PS.Scheme(
        'px6-forest', '林间精灵',
        dict(family='幻想冒险', tags=['栖息', '微光', '静谧'],
             story='森林把月光筛成碎屑，一只小小的精灵坐在蘑菇上，替你守着这片安静。'),
        '月光下的深林里，树影层层叠叠，树洞口有一双眼睛，蘑菇旁飘着萤火，地上留着发光的精灵环。'
        '每按一键，蘑菇旁就亮起一粒萤火；CapsLock 亮起，精灵张开翅膀、光环全部点亮；'
        '安静久了，它会把身体蜷成一颗发光的球睡去。',
        ['#06120e', '#0f2419', '#1d3a28', '#a8ffd0', '#eaffc9', '#5fe0a8', '#f2ffe8'],
        bg, ATTR)
    s.sticker('林间精灵', 88, 64, forest_spirit('calm'), '#a8ffd0', spirit_bg,
              caps=forest_spirit('caps'), caps_fg='#eaffc9',
              react=forest_spirit('react'), react_fg='#d8ffe0',
              sleepy=forest_spirit('sleep'), sleepy_fg='#5c9a78')
    s.sticker('发光蘑菇', 188, 118, forest_mushrooms('calm'), '#9ef0c8', mush_bg,
              caps=forest_mushrooms('big'), caps_fg='#dcffd0',
              sleepy_fg='#4f8a70')
    s.sticker('精灵环', 56, 138, forest_ring('calm'), '#7fe0a8', ring_bg,
              caps=forest_ring('caps'), caps_fg='#d8ffb0',
              sleepy_fg='#3f6f58')
    s.sticker('树洞眼睛', 252, 94, forest_hollow('calm'), '#ffe9a8', hollow_bg,
              caps=forest_hollow('caps'), caps_fg='#fff6c8',
              sleepy=forest_hollow('sleep'), sleepy_fg='#4f7a5e')
    s.set_effect('firefly', trigger='key', spawn=(150, 100, 76, 26), count=4, size=2,
                 colors=['#c8ff8a', '#fff6a8', '#8affc8'], vx=(-26, 26),
                 vy=(-26, 26), gravity=0, life_ms=3200, edge='wrap')
    s.set_pulse('林间精灵', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=23000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 街机
SHIP = ['..###..', '.#####.', '#######', '##.#.##', '#.....#']
INVADER = ['..#.#..', '.#####.', '#######', '#.###.#', '#.....#']


def arcade_screen(state):
    g = Grid(54, 40)
    if state == 'sleep':
        g.text('GAME OVER', 0, 13)
        g.set(20, 26)
        g.set(33, 26)
        g.hline(25, 28, 31)
        return g
    if state == 'react':
        g.text('NEW REC', 6, 2)
        star5(g, 27, 21, 12)
        carve_disc(g, 27, 21, 4)
        for x, y in ((4, 8), (48, 6), (8, 34), (44, 33), (2, 22), (50, 24)):
            g.set(x, y)
            g.set(x + 1, y)
        g.text('9999', 20, 31)
        return g
    if state == 'caps':
        g.text('1UP', 3, 2)
        g.text('2UP', 37, 2)
        g.text('9990', 3, 10)
        g.text('9999', 35, 10)
        for x in (4, 18, 32, 44):
            put(g, INVADER, x, 20)
        put(g, SHIP, 11, 31)
        put(g, SHIP, 34, 31)
        g.rect(20, 26, 26, 28)
        g.rect(27, 26, 33, 28)
        return g
    g.text('1UP', 3, 2)
    g.text('HI', 39, 2)
    g.text('0320', 3, 10)
    g.text('5600', 37, 10)
    for x in (9, 24, 39):
        put(g, INVADER, x, 21)
    put(g, SHIP, 23, 32)
    g.set(26, 27)
    g.set(27, 27)
    return g


def arcade_marquee(state):
    g = Grid(52, 18)
    if state == 'sleep':
        return g
    g.hline(0, 51, 0)
    g.hline(0, 51, 17)
    for x in range(2, 51, 5):
        g.set(x, 3)
        g.set(x, 14)
    if state == 'calm':
        g.text('PLAY', 15, 6)
    elif state == 'caps':
        g.text('PLAY', 13, 6)
        for x in range(2, 51, 4):
            g.set(x, 1)
            g.set(x, 16)
        g.set(0, 6)
        g.set(51, 6)
    else:
        g.text('PLAY!', 11, 6)
        for x in range(1, 52, 3):
            g.set(x, 1)
            g.set(x, 16)
    return g


def arcade_stick(state):
    g = Grid(20, 26)
    g.rect(2, 20, 17, 25)
    if state == 'caps':
        g.line(10, 20, 14, 8, '#', 3)
        g.disc(15, 6, 4)
    elif state == 'sleep':
        g.line(10, 20, 9, 11, '#', 3)
        g.disc(9, 9, 4)
    else:
        g.line(10, 20, 9, 8, '#', 3)
        g.disc(8, 6, 4)
    return g


def arcade_buttons(state):
    g = Grid(24, 12)
    if state == 'caps':
        for cx in (4, 12, 20):
            g.disc(cx, 6, 3)
        g.set(4, 1)
        g.set(12, 1)
        g.set(20, 1)
        return g
    if state == 'react':
        for cx in (4, 12, 20):
            g.rect(cx - 2, 5, cx + 2, 8)
        g.set(1, 3)
        g.set(23, 3)
        return g
    for cx in (4, 12, 20):
        g.ring(cx, 6, 3)
    return g


def build_arcade():
    bg = PS.vgrad('#0d0a1c', '#191233', bands=10)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    rng = random.Random(63)
    # wall neon decorations
    star5c = PS.hexrgb('#5fe0ff')
    for cx, cy, r, c in ((36, 46, 9, '#5fe0ff'), (76, 74, 5, '#ff5fa8'),
                         (286, 54, 8, '#ffe36a'), (252, 92, 4, '#b48cff')):
        import math as _m
        pts = []
        for i in range(10):
            a = -_m.pi / 2 + i * _m.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + _m.cos(a) * rr, cy + _m.sin(a) * rr))
        d.polygon(pts, outline=PS.hexrgb(c))
    for x0, y0, x1, y1 in ((22, 20, 30, 28), (266, 24, 274, 32), (16, 96, 24, 104),
                           (296, 108, 304, 116), (58, 30, 62, 34), (240, 40, 244, 44)):
        d.rectangle((x0, y0, x1, y1), outline=PS.hexrgb('#6a4fa8'))
    # ceiling lamp cone
    d.polygon([(150, 0), (250, 0), (286, 130), (114, 130)], fill=PS.hexrgb('#1c1638'))
    d.rectangle((150, 0, 250, 6), fill=PS.hexrgb('#2a2250'))
    d.ellipse((186, 2, 214, 12), fill=PS.hexrgb('#ffe9a8'))
    # carpet
    d.rectangle((0, 144, 319, 171), fill=PS.hexrgb('#1a1030'))
    for gy in range(144, 172, 8):
        for gx in range(0, 320, 16):
            if ((gx // 16) + (gy // 8)) % 2 == 0:
                d.rectangle((gx, gy, gx + 14, gy + 6), fill=PS.hexrgb('#241640'))
    # cabinet body
    d.rectangle((126, 24, 250, 172), fill=PS.hexrgb('#241a44'))
    d.rectangle((126, 24, 250, 172), outline=PS.hexrgb('#6a4fa8'), width=3)
    d.polygon([(126, 24), (146, 24), (150, 6), (150, 0), (126, 0)],
              fill=PS.hexrgb('#2a1f52'))
    d.polygon([(250, 24), (230, 24), (226, 6), (226, 0), (250, 0)],
              fill=PS.hexrgb('#2a1f52'))
    d.rectangle((138, 30, 238, 58), fill=PS.hexrgb('#2e2258'))
    d.rectangle((136, 56, 240, 110), fill=PS.hexrgb('#100a22'))
    d.rectangle((136, 56, 240, 110), outline=PS.hexrgb('#5a3f8a'), width=2)
    # side art
    for sxx, syy, c in ((130, 70, '#ff5fa8'), (246, 86, '#5fe0ff'),
                        (130, 120, '#ffe36a'), (246, 140, '#b48cff')):
        d.rectangle((sxx, syy, sxx + 8, syy + 8), fill=PS.hexrgb(c))
        d.rectangle((sxx + 2, syy + 2, sxx + 6, syy + 6), fill=PS.hexrgb('#241a44'))
    d.polygon([(138, 110), (238, 110), (246, 124), (130, 124)], fill=PS.hexrgb('#2e2258'))
    d.rectangle((130, 124, 246, 128), fill=PS.hexrgb('#6a4fa8'))
    d.rectangle((168, 128, 208, 156), fill=PS.hexrgb('#1c1338'))
    d.rectangle((176, 132, 200, 142), fill=PS.hexrgb('#0f0a1e'))
    d.rectangle((178, 146, 198, 150), fill=PS.hexrgb('#5a3f8a'))
    d.rectangle((150, 160, 226, 166), fill=PS.hexrgb('#2a1f52'))
    # floor glow from the screen
    glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((120, 136, 262, 186), fill=(255, 95, 168, 26))
    bg.paste(glow, (0, 0), glow)
    marquee_bg = patch(bg, ref, 142, 30, 52, 18, '#2e2258')
    screen_bg = patch(bg, ref, 142, 62, 54, 40, '#100a22')
    stick_bg = patch(bg, ref, 148, 126, 20, 26, '#2e2258')
    btn_bg = patch(bg, ref, 184, 132, 24, 12, '#2e2258')
    s = PS.Scheme(
        'px6-arcade', '深夜街机',
        dict(family='幻想冒险', tags=['复古', '闯关', '彩纸'],
             story='最后一枚硬币投进去，屏幕亮起 1UP——整条街只剩下按键声和你。'),
        '深夜的街机厅里只剩这一台机还亮着，屏幕里的小飞船等你按键开局。'
        '每敲一键，屏幕上方就蹦出一把彩色纸屑，跑马灯跟着节奏闪；CapsLock 亮起，双打模式、分数拉满；'
        '久不操作就跳出 GAME OVER，灯也慢慢暗下去。',
        ['#0d0a1c', '#241a44', '#6a4fa8', '#ff5fa8', '#5fe0ff', '#ffe36a', '#f2eaff'],
        bg, ATTR)
    s.sticker('街机屏', 142, 62, arcade_screen('calm'), '#7dffa8', screen_bg,
              caps=arcade_screen('caps'), caps_fg='#c8ffb0',
              react=arcade_screen('react'), react_fg='#ffe36a',
              sleepy=arcade_screen('sleep'), sleepy_fg='#4f6a6a')
    s.sticker('跑马灯', 142, 30, arcade_marquee('calm'), '#ffe36a', marquee_bg,
              caps=arcade_marquee('caps'), caps_fg='#fff6c8',
              react=arcade_marquee('react'), react_fg='#ff5fa8',
              sleepy=arcade_marquee('sleep'), sleepy_fg='#4a3a5a')
    s.sticker('摇杆', 148, 126, arcade_stick('calm'), '#ff5fa8', stick_bg,
              caps=arcade_stick('caps'), caps_fg='#ff9ad0',
              react=arcade_stick('caps'), react_fg='#ffd0e8',
              sleepy=arcade_stick('sleep'), sleepy_fg='#7a4a66')
    s.sticker('按键', 184, 132, arcade_buttons('calm'), '#5fe0ff', btn_bg,
              caps=arcade_buttons('caps'), caps_fg='#c8f8ff',
              react=arcade_buttons('react'), react_fg='#ffe36a',
              sleepy_fg='#3a4a5a')
    s.set_effect('confetti', trigger='key', spawn=(142, 40, 60, 18), count=8, size=3,
                 colors=['#ff5fa8', '#ffe36a', '#5fe0ff', '#b6ff9a'], vx=(-150, 150),
                 vy=(-170, -30), gravity=150, life_ms=1500, edge='bounce')
    s.set_pulse('跑马灯', period_ms=1400, minimum=140)
    s.set_reaction(reactHoldMs=950, sleepyAfterMs=21000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 机甲
def mecha_head(state):
    g = Grid(56, 42)
    poly(g, [(7, 13), (0, 20), (0, 30), (7, 26)])          # ear fins
    poly(g, [(48, 13), (55, 20), (55, 30), (48, 26)])
    ellipse(g, 28, 18, 17, 15)                             # dome
    g.rect(11, 18, 44, 37)
    g.rect(18, 37, 38, 42)                                 # jaw
    g.rect(16, 20, 39, 31, '.')                            # visor recess
    g.vline(5, 22, 33, '.', 2)                             # cheek vents
    g.vline(50, 22, 33, '.', 2)
    g.hline(22, 33, 39, '.')                               # mouth grill
    g.hline(22, 33, 41, '.')
    g.vline(27, 0, 4, '#', 2)                              # antenna
    g.disc(28, 0, 2)
    poly(g, [(19, 5), (28, 0), (37, 5), (33, 9), (23, 9)])  # crest
    if state == 'caps':
        g.vline(3, 20, 35, '.', 3)                         # vents open wider
        g.vline(52, 20, 35, '.', 3)
        g.hline(8, 11, 11)                                 # horn spikes
        g.hline(45, 48, 11)
        g.set(7, 9)
        g.set(49, 9)
        g.disc(15, 33, 2)
        g.disc(40, 33, 2)
    elif state == 'sleep':
        g = sheared(g, 0.06)
        g.rect(5, 22, 7, 33)                               # vents shut
        g.rect(49, 22, 51, 33)
    return g


def mecha_eye(state):
    g = Grid(22, 11)
    if state == 'caps':
        g.rect(0, 3, 21, 7)
        g.hline(3, 18, 2)
        return g
    if state == 'react':
        g.line(0, 0, 21, 10)
        g.line(21, 0, 0, 10)
        g.disc(11, 5, 3)
        g.disc(11, 5, 1, '.')
        return g
    if state == 'sleep':
        g.hline(3, 18, 6)
        return g
    g.rect(2, 4, 19, 6)
    g.vline(1, 3, 7)
    g.vline(20, 3, 7)
    return g


def mecha_core(state):
    g = Grid(24, 20)
    if state == 'sleep':
        return g
    g.ring(12, 10, 7)
    g.disc(12, 10, 2)
    for x in (12,):
        g.vline(12, 1, 4)
        g.vline(12, 16, 18)
        g.hline(2, 5, 10)
        g.hline(18, 21, 10)
    if state == 'caps':
        g.ring(12, 10, 9)
        for x, y in ((12, 0), (12, 19), (1, 10), (22, 10)):
            g.set(x, y)
    if state == 'react':
        star5(g, 12, 10, 9)
        carve_disc(g, 12, 10, 4)
        g.set(12, 10)
    return g


def mecha_beacon(state):
    g = Grid(18, 18)
    if state == 'sleep':
        return g
    g.disc(9, 9, 5)
    for x, y in ((9, 1), (9, 17), (1, 9), (17, 9)):
        g.set(x, y)
    if state == 'caps':
        g.disc(9, 9, 6)
        for i in range(3):
            g.set(9 - 6 - i, 3 + i)
            g.set(9 + 6 + i, 3 + i)
    return g


def build_mecha():
    bg = PS.vgrad('#070c16', '#101a2a', bands=10)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    rng = random.Random(88)
    # back wall panels
    for x in range(0, 320, 46):
        d.rectangle((x, 0, x + 44, 130), outline=PS.hexrgb('#16233a'))
    for y in (30, 62, 94):
        d.line((0, y, 319, y), fill=PS.hexrgb('#142138'))
    # gantry beams
    d.rectangle((0, 8, 319, 18), fill=PS.hexrgb('#1b2740'))
    d.rectangle((0, 8, 319, 11), fill=PS.hexrgb('#2c3c58'))
    for x in range(0, 320, 24):
        d.line((x, 12, x + 12, 18), fill=PS.hexrgb('#2c3c58'))
        d.line((x + 12, 12, x, 18), fill=PS.hexrgb('#2c3c58'))
    for x in (24, 292):
        d.rectangle((x, 18, x + 8, 62), fill=PS.hexrgb('#1b2740'))
        d.line((x + 2, 18, x + 2, 62), fill=PS.hexrgb('#2c3c58'))
    # hanging cables
    for x, ln in ((66, 46), (84, 62), (240, 54), (258, 40)):
        d.line((x, 18, x + 4, 18 + ln), fill=PS.hexrgb('#22304a'))
        d.line((x + 4, 18 + ln, x + 8, 18 + ln + 10), fill=PS.hexrgb('#22304a'))
    # hazard stripe band
    d.rectangle((0, 122, 319, 134), fill=PS.hexrgb('#232833'))
    for x in range(-20, 340, 20):
        d.polygon([(x, 134), (x + 10, 122), (x + 20, 122), (x + 10, 134)],
                  fill=PS.hexrgb('#a8862e'))
    # chest / shoulders silhouette behind the head
    d.polygon([(92, 172), (104, 128), (128, 114), (192, 114), (216, 128),
               (228, 172)], fill=PS.hexrgb('#131d2e'))
    d.line((104, 128, 92, 172), fill=PS.hexrgb('#2c3c58'))
    d.line((216, 128, 228, 172), fill=PS.hexrgb('#2c3c58'))
    d.polygon([(128, 114), (150, 104), (170, 104), (192, 114)],
              fill=PS.hexrgb('#1b2740'))
    d.polygon([(170, 100), (192, 100), (198, 122), (164, 122)],
              fill=PS.hexrgb('#1b2740'))
    d.polygon([(64, 172), (76, 138), (96, 128), (104, 172)],
              fill=PS.hexrgb('#162133'))
    d.polygon([(256, 172), (244, 138), (224, 128), (216, 172)],
              fill=PS.hexrgb('#162133'))
    d.rectangle((0, 134, 319, 171), fill=PS.hexrgb('#0e1626'))
    for y in (142, 152, 164):
        d.line((0, y, 319, y), fill=PS.hexrgb('#13203a'))
    for x in range(0, 320, 26):
        d.line((x, 134, x - 18, 171), fill=PS.hexrgb('#13203a'))
    # floor light pools
    glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((140, 132, 232, 178), fill=(95, 224, 255, 24))
    bg.paste(glow, (0, 0), glow)
    head_bg = patch(bg, ref, 154, 60, 56, 42, '#0b1220')
    eye_bg = patch(bg, ref, 171, 80, 22, 11, head_bg)
    core_bg = patch(bg, ref, 164, 118, 24, 20, '#131d2e')
    beacon_bg = patch(bg, ref, 52, 26, 18, 18, '#0b1220')
    s = PS.Scheme(
        'px6-mecha', '旧机甲',
        dict(family='幻想冒险', tags=['待机', '过载', '守护'],
             story='装甲上的每一道划痕都有人记得，它只是还想再替你站一班岗。'),
        '熄灯后的机库里，一台旧机甲立在检修架上，独眼还留着一线红光。'
        '敲下键盘，它的眼睛就亮一下、接口迸出火花；CapsLock 亮起，散热口全开、核心过载充能；'
        '你离开后，它低下头，把引擎一点点关掉。',
        ['#070c16', '#101a2a', '#9fb0c8', '#ff5a4a', '#5fe0ff', '#ffc454', '#e8f0ff'],
        bg, ATTR)
    s.sticker('机甲头', 154, 60, mecha_head('calm'), '#9fb0c8', head_bg,
              caps=mecha_head('caps'), caps_fg='#c6d8f0',
              react_fg='#b8c9e0',
              sleepy=mecha_head('sleep'), sleepy_fg='#5e6f8a')
    s.sticker('独眼', 171, 80, mecha_eye('calm'), '#ff5a4a', eye_bg,
              caps=mecha_eye('caps'), caps_fg='#ff8a6a',
              react=mecha_eye('react'), react_fg='#ffd27a',
              sleepy=mecha_eye('sleep'), sleepy_fg='#4a5a72')
    s.sticker('胸核', 164, 118, mecha_core('calm'), '#5fe0ff', core_bg,
              caps=mecha_core('caps'), caps_fg='#c8f8ff',
              react=mecha_core('react'), react_fg='#ffe9a8',
              sleepy=mecha_core('sleep'), sleepy_fg='#37506a')
    s.sticker('警示灯', 52, 26, mecha_beacon('calm'), '#ffc454', beacon_bg,
              caps=mecha_beacon('caps'), caps_fg='#ffe9a8',
              sleepy=mecha_beacon('sleep'), sleepy_fg='#4a4430')
    s.set_effect('spark', trigger='key', spawn=(166, 96, 34, 12), count=8, size=2,
                 colors=['#ff6a4a', '#ffd27a', '#9fe8ff'], vx=(-150, 150),
                 vy=(-170, -60), gravity=180, life_ms=1100, edge='bounce')
    s.set_pulse('独眼', period_ms=1500, minimum=150)
    s.set_reaction(reactHoldMs=800, sleepyAfterMs=19000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 魔法师
def wizard_hat(state):
    g = Grid(48, 40)
    poly(g, [(30, 0), (21, 4), (12, 26), (35, 26)])        # leaning cone
    g.set(31, 1)
    g.set(32, 3)
    g.set(33, 6)
    ellipse(g, 24, 28, 21, 5)                              # brim
    g.rect(6, 26, 42, 30)
    g.hline(11, 34, 20, '.')                               # hat band
    g.hline(12, 33, 21, '.')
    star5(g, 27, 11, 4, '.')                               # star cut-out
    g.set(22, 6)
    if state == 'caps':
        star5(g, 27, 11, 5, '.')
        for x, y in ((2, 22), (44, 22), (9, 16), (38, 14)):
            g.set(x, y)
        g.hline(0, 5, 25)
        g.hline(41, 47, 25)
        star5(g, 26, 2, 2)
    elif state == 'sleep':
        g = sheared(g, 0.10)
        g.rect(6, 26, 42, 29)
        g.hline(11, 34, 20, '.')
        carve_disc(g, 28, 28, 8)
    return g


def wizard_crystal(state):
    g = Grid(26, 26)
    if state == 'sleep':
        poly(g, [(13, 8), (19, 13), (13, 18), (7, 13)])
        return g
    poly(g, [(13, 1), (23, 10), (19, 25), (7, 25), (3, 10)])
    g.vline(13, 5, 23, '.')                              # facet
    g.line(4, 11, 10, 8, '.')
    g.line(22, 11, 16, 8, '.')
    if state == 'caps':
        for x, y in ((13, 0), (0, 10), (25, 10), (2, 2), (23, 2), (3, 24), (22, 24)):
            g.set(x, y)
        star5(g, 13, 13, 3, '.')
    return g


def wizard_circle(state):
    g = Grid(56, 16)
    ellipse(g, 28, 8, 25, 6)
    inner = Grid(56, 16)
    ellipse(inner, 28, 8, 21, 3)
    for y in range(16):
        for x in range(56):
            if inner.g[y][x] != '.':
                g.set(x, y, '.')
    star5(g, 28, 8, 5)
    for i in range(12):                                 # rune ticks on the ring
        a = math.pi * 2 * i / 12
        g.set(28 + math.cos(a) * 24, 8 + math.sin(a) * 5)
    if state == 'caps':
        star5(g, 28, 8, 7)
        for i in range(12):
            a = math.pi * 2 * i / 12
            g.set(28 + math.cos(a) * 27, 8 + math.sin(a) * 6)
            g.set(28 + math.cos(a) * 17, 8 + math.sin(a) * 3)
    return g


def wizard_book(state):
    g = Grid(30, 20)
    if state == 'sleep':
        poly(g, [(3, 6), (15, 8), (27, 6), (27, 17), (15, 16), (3, 17)])
        g.hline(5, 12, 10, '.')
        g.hline(18, 25, 10, '.')
        return g
    poly(g, [(1, 6), (14, 9), (14, 17), (1, 16)])
    poly(g, [(16, 9), (29, 6), (29, 16), (16, 17)])
    g.vline(15, 8, 17)
    for y in (10, 12, 14):
        g.hline(4, 11, y, '.')
        g.hline(19, 26, y, '.')
    if state == 'caps':
        star5(g, 15, 3, 3)
        for x, y in ((0, 13), (29, 13), (8, 6), (22, 6)):
            g.set(x, y)
    return g


def build_wizard():
    bg = PS.vgrad('#100c22', '#1a1330', bands=10)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    rng = random.Random(52)
    bricks(d, 0, 0, 319, 172, '#191330', '#221b3c', step_x=30, step_y=16)
    for _ in range(60):
        x = rng.randrange(0, 316, 6)
        y = rng.randrange(0, 168, 6)
        d.line((x, y, x + rng.choice((-18, -12, 12, 18)), y),
               fill=PS.hexrgb('#211a36'))
    # banner behind the floating hat
    d.rectangle((44, 30, 112, 92), fill=PS.hexrgb('#1c1436'))
    d.rectangle((44, 30, 112, 92), outline=PS.hexrgb('#3a2a5c'))
    d.rectangle((48, 34, 108, 88), outline=PS.hexrgb('#2a1f46'))
    for i in range(3):
        star5c = PS.hexrgb('#4a3a74')
        import math as _m
        cx, cy, r = 78, 62 + i * 0, 5
        pts = []
        for k in range(10):
            a = -_m.pi / 2 + k * _m.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((cx + _m.cos(a) * rr, cy + _m.sin(a) * rr))
        d.polygon(pts, fill=star5c)
    # arched window with night sky
    d.rectangle((222, 34, 296, 118), fill=PS.hexrgb('#1b1432'))
    d.rectangle((218, 34, 222, 122), fill=PS.hexrgb('#2e2448'))
    d.rectangle((296, 34, 300, 122), fill=PS.hexrgb('#2e2448'))
    d.rectangle((218, 30, 300, 34), fill=PS.hexrgb('#2e2448'))
    d.rectangle((226, 38, 292, 114), fill=PS.hexrgb('#0d1638'))
    d.ellipse((226, 26, 292, 76), fill=PS.hexrgb('#0d1638'))
    PS.stars(bg, 34, '#cfd8ff', seed=6, area=(228, 30, 292, 112), size2=5)
    PS.moon(bg, 272, 56, 9, '#e8efff', '#c0c9e6')
    gd = ImageDraw.Draw(bg)
    gd.line((259, 38, 259, 114), fill=PS.hexrgb('#2e2448'), width=2)
    gd.line((226, 76, 292, 76), fill=PS.hexrgb('#2e2448'), width=2)
    gd.arc((226, 26, 292, 76), 180, 360, fill=PS.hexrgb('#2e2448'), width=2)
    # window sill
    d.rectangle((210, 114, 306, 122), fill=PS.hexrgb('#241c40'))
    d.line((210, 114, 306, 114), fill=PS.hexrgb('#3a2f5c'))
    # shelf with candles beside the book
    d.rectangle((150, 112, 284, 120), fill=PS.hexrgb('#2e2038'))
    d.line((150, 112, 284, 112), fill=PS.hexrgb('#4a3355'))
    for cx in (152, 206):
        d.rectangle((cx, 104, cx + 4, 112), fill=PS.hexrgb('#c9b48a'))
        d.point((cx + 2, 101), fill=PS.hexrgb('#ffd98a'))
        d.point((cx + 2, 100), fill=PS.hexrgb('#fff2c8'))
    for i in range(3):
        d.rectangle((250, 100 - i * 11, 268, 108 - i * 11), fill=PS.hexrgb('#2a3a5c'))
        d.rectangle((252, 102 - i * 11, 266, 105 - i * 11), fill=PS.hexrgb('#4a5f8c'))
    # desk legs
    d.rectangle((150, 120, 156, 172), fill=PS.hexrgb('#241a2e'))
    d.rectangle((276, 120, 282, 172), fill=PS.hexrgb('#241a2e'))
    # floor planks
    d.rectangle((0, 138, 319, 171), fill=PS.hexrgb('#181128'))
    for y in (144, 152, 160, 168):
        d.line((0, y, 319, y), fill=PS.hexrgb('#120d1e'))
    for x in range(0, 320, 26):
        d.line((x, 138, x, 171), fill=PS.hexrgb('#120d1e'))
    # candle light on the shelf
    glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((138, 84, 168, 124), fill=(255, 210, 130, 16))
    gd.ellipse((192, 84, 222, 124), fill=(255, 210, 130, 14))
    bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    # staff leaning by the window
    d.line((208, 96, 226, 172), fill=PS.hexrgb('#4a3624'), width=3)
    d.line((209, 98, 224, 172), fill=PS.hexrgb('#6a4f34'))
    for x, y in ((212, 120), (218, 148), (222, 164)):
        d.point((x, y), fill=PS.hexrgb('#2e2114'))
    # floating motes
    for _ in range(26):
        d.point((rng.randrange(0, 320), rng.randrange(0, 130)),
                fill=PS.hexrgb(rng.choice(('#4a3a74', '#5a4a8c', '#3a2f5c'))))
    hat_bg = patch(bg, ref, 58, 40, 48, 40, '#1c1436')
    crys_bg = patch(bg, ref, 200, 74, 26, 26, '#191330')
    circ_bg = patch(bg, ref, 74, 138, 56, 16, '#181128')
    book_bg = patch(bg, ref, 168, 92, 30, 20, '#2e2038')
    s = PS.Scheme(
        'px6-wizard', '塔顶魔法师',
        dict(family='幻想冒险', tags=['咒语', '星尘', '深夜'],
             story='帽子浮在半空，宝石还剩一点余温——它把今天所有没说完的话都收进了咒语书。'),
        '高塔的深夜书房里，一顶会自己浮起来的巫师帽守在桌前，法杖顶端的宝石还留着一丝余温，'
        '窗外的月和地上的法阵一起亮着。每敲一键，宝石就炸开一小把星尘；'
        'CapsLock 亮起，帽尖的星星和法阵一起点亮；久不输入，帽子垂下来，宝石只剩一点微光。',
        ['#141026', '#191330', '#b48cff', '#ffd98a', '#5fe0ff', '#f4ecff', '#2e2038'],
        bg, ATTR)
    s.sticker('巫师帽', 58, 40, wizard_hat('calm'), '#b48cff', hat_bg,
              caps=wizard_hat('caps'), caps_fg='#d8c4ff',
              react_fg='#c9b0ff',
              sleepy=wizard_hat('sleep'), sleepy_fg='#6a5192')
    s.sticker('法杖宝石', 200, 74, wizard_crystal('calm'), '#ffd98a', crys_bg,
              caps=wizard_crystal('caps'), caps_fg='#fff2c8',
              react=wizard_crystal('caps'), react_fg='#9ff2ff',
              sleepy=wizard_crystal('sleep'), sleepy_fg='#7a6a54')
    s.sticker('魔法阵', 74, 138, wizard_circle('calm'), '#7a5fd0', circ_bg,
              caps=wizard_circle('caps'), caps_fg='#c9b0ff',
              react_fg='#9ff2ff',
              sleepy_fg='#4a3a6a')
    s.sticker('咒语书', 168, 92, wizard_book('calm'), '#e0cfa0', book_bg,
              caps=wizard_book('caps'), caps_fg='#fff2c8',
              sleepy=wizard_book('sleep'), sleepy_fg='#8a7a62')
    s.set_effect('dust', trigger='key', spawn=(198, 90, 28, 14), count=6, size=2,
                 colors=['#ffd98a', '#d8c4ff', '#9ff2ff'], vx=(-40, 40),
                 vy=(-70, -20), gravity=-4, life_ms=2400, edge='wrap', shape='plus')
    s.set_pulse('法杖宝石', period_ms=2000, minimum=140)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=25000)
    s.statusInk = WHITE_INK
    return s


# =========================================================================== 漂流岛
def island_palm(state):
    """Palm crown + grass cap (green sticker above the rock sticker)."""
    g = Grid(56, 22)
    g.rect(1, 15, 54, 20)                                  # grass shelf
    for x in range(1, 55, 2):
        if (x // 2) % 2 == 0:
            g.set(x, 21)
    for x in (7, 18, 37, 47, 51):
        g.set(x, 13)                                       # grass blades
    if state == 'sleep':
        poly(g, [(26, 15), (29, 15), (27, 7), (25, 7)])    # drooping crown
        poly(g, [(25, 5), (12, 4), (14, 8), (24, 9)])
        poly(g, [(25, 5), (4, 9), (6, 13), (24, 10)])
        poly(g, [(25, 5), (23, 2), (27, 4), (27, 8)])
        poly(g, [(26, 5), (39, 4), (37, 8), (27, 9)])
        poly(g, [(26, 5), (48, 9), (46, 13), (27, 10)])
        g.set(24, 12)
        return g
    poly(g, [(25, 15), (28, 15), (25, 6), (23, 6)])        # trunk
    poly(g, [(25, 5), (10, 1), (14, 5), (24, 9)])          # fronds
    poly(g, [(25, 5), (3, 6), (5, 10), (24, 9)])
    poly(g, [(25, 5), (24, 0), (28, 2), (27, 8)])
    poly(g, [(26, 5), (41, 0), (38, 4), (27, 8)])
    poly(g, [(26, 5), (50, 5), (48, 9), (27, 8)])
    poly(g, [(25, 7), (8, 12), (12, 14), (25, 9)])
    poly(g, [(26, 7), (44, 12), (40, 14), (26, 9)])
    g.set(25, 10)                                          # coconuts
    g.set(27, 11)
    if state == 'caps':
        for x, y in ((2, 2), (52, 2), (18, 0), (34, 0), (8, 15), (33, 17),
                     (45, 18), (21, 16), (30, 14), (14, 10)):
            g.set(x, y)
        g.set(1, 8)
        g.set(54, 9)
    return g


def island_rock(state):
    """Floating rock underside below the grass cap."""
    g = Grid(56, 18)
    poly(g, [(0, 0), (55, 0), (51, 5), (44, 10), (36, 13), (28, 17),
             (20, 13), (12, 10), (5, 5)])
    for y, x0, x1 in ((3, 3, 20), (6, 30, 52), (9, 8, 26), (11, 33, 48),
                      (13, 18, 30)):
        for x in range(x0, min(x1, 53), 2):
            g.set(x, y, '.')
    g.line(6, 0, 4, 6)                                     # hanging vines
    g.line(48, 0, 51, 7)
    if state == 'caps':
        for x, y in ((16, 12), (40, 8), (28, 15), (22, 6)):
            g.set(x, y)
            g.set(x + 1, y)
        for y in range(2, 14):
            g.set(27 + (y % 3), y, '.')
    return g


def island_fire(state):
    g = Grid(18, 24)
    g.rect(1, 18, 16, 22)                                  # log pile
    g.rect(3, 20, 14, 22, '.')
    g.set(4, 17)
    g.set(8, 17)
    g.set(12, 17)
    if state == 'sleep':
        g.rect(5, 18, 13, 21)
        g.rect(7, 19, 11, 21, '.')
        for x, y in ((4, 15), (13, 14)):
            g.set(x, y)
        return g
    widths = ([2, 2, 3, 3, 4, 4, 3, 3, 2, 2, 1] if state == 'calm' else
              [1, 2, 2, 3, 4, 5, 5, 6, 6, 5, 5, 4, 4, 3, 2, 2, 1])
    flame(g, 9, 18 - len(widths), widths)
    if state == 'caps':
        for x, y in ((2, 4), (15, 3), (7, 1), (12, 6)):
            g.set(x, y)
        g.set(1, 9)
        g.set(16, 10)
    return g


def island_boat(state):
    g = Grid(40, 14)
    poly(g, [(1, 8), (4, 12), (27, 12), (31, 8), (15, 10)])
    g.rect(23, 5, 24, 8)                                   # lantern post
    g.rect(22, 2, 25, 5)
    if state == 'caps':
        for x, y in ((21, 1), (26, 1), (23, 0), (24, 0)):
            g.set(x, y)
        g.set(20, 3)
        g.set(27, 3)
    g.line(6, 8, 6, 1)                                     # mast
    poly(g, [(6, 1), (19, 4), (6, 5)])
    return g


def build_island():
    bg = PS.vgrad('#0a1430', '#243b6a', bands=13)
    ref = bg.copy()
    d = ImageDraw.Draw(bg)
    PS.stars(bg, 62, '#dfe8ff', seed=17, size2=5)
    rng = random.Random(24)
    # clouds near the horizon
    for cx, cy, w in ((44, 92, 34), (150, 78, 26), (272, 100, 30), (204, 108, 18)):
        d.ellipse((cx - w, cy - 6, cx + w, cy + 6), fill=PS.hexrgb('#1a2a52'))
        d.ellipse((cx - w + 8, cy - 10, cx + w - 6, cy + 2),
                  fill=PS.hexrgb('#22335e'))
    # horizon glow + sea
    d.rectangle((0, 118, 319, 120), fill=PS.hexrgb('#2e4a7e'))
    for y in range(120, 172):
        k = (y - 120) / 52.0
        c = PS.lerp(PS.hexrgb('#16294e'), PS.hexrgb('#081226'), k)
        d.line((0, y, 319, y), fill=c)
    for y in range(124, 172, 5):
        for x in range(0, 320, 34):
            xx = x + (y * 7 + x) % 21
            d.line((xx, y, xx + 6 + (y % 3), y),
                   fill=PS.hexrgb(rng.choice(('#243d68', '#2f4d7e', '#1a3054'))))
    # moon reflection
    for i in range(16):
        y = 124 + i * 3
        w = 14 - i // 2
        if w <= 0:
            break
        d.line((262 - w, y, 262 + w, y), fill=PS.hexrgb('#8fa8d8'))
    # distant islands
    for x0, w, h in ((16, 42, 10), (198, 54, 13), (290, 26, 7)):
        d.polygon([(x0, 118), (x0 + w // 2, 118 - h), (x0 + w, 118)],
                  fill=PS.hexrgb('#0d1b36'))
    # rock outcrop that carries the campfire
    d.polygon([(126, 116), (154, 112), (162, 124), (156, 134), (128, 130)],
              fill=PS.hexrgb('#0c1c30'))
    d.polygon([(130, 120), (154, 116), (158, 124), (132, 126)],
              fill=PS.hexrgb('#152c44'))
    d.line((130, 120, 156, 117), fill=PS.hexrgb('#24445e'))
    # warm fire spill on the outcrop
    glow = Image.new('RGBA', PS.SIZE, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((120, 96, 172, 136), fill=(255, 190, 110, 26))
    bg.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(bg)
    # bg moon (kept in the scene so the stickers stay on the island itself)
    d.ellipse((249, 44, 279, 74), fill=PS.hexrgb('#1c2f5a'))
    d.ellipse((252, 47, 276, 71), fill=PS.hexrgb('#e8efff'))
    d.ellipse((257, 52, 262, 56), fill=PS.hexrgb('#c9d2ee'))
    d.ellipse((266, 62, 270, 66), fill=PS.hexrgb('#c9d2ee'))
    d.ellipse((255, 61, 257, 63), fill=PS.hexrgb('#c9d2ee'))
    # sea sparkle
    for _ in range(24):
        x, y = rng.randrange(0, 320), rng.randrange(124, 171)
        d.point((x, y), fill=PS.hexrgb(rng.choice(('#3a5a8c', '#5578a8'))))
    island_bg = patch(bg, ref, 60, 62, 56, 22, '#1a2a4e')
    rock_bg = patch(bg, ref, 60, 84, 56, 18, '#162445')
    fire_bg = patch(bg, ref, 135, 90, 18, 24, '#1a2a46')
    boat_bg = patch(bg, ref, 197, 138, 40, 14, '#0b1830')
    s = PS.Scheme(
        'px6-island', '漂流岛',
        dict(family='幻想冒险', tags=['漂流', '篝火', '夜海'],
             story='岛不大，刚好放得下一棵树、一堆火和一个人的心事，它就这么慢慢漂着。'),
        '海面安静得能听见浪声，一座小小的浮岛漂在星光里，棕榈叶下还燃着一堆篝火，一条小船拴在岸边。'
        '敲键盘时，火苗蹿高、火星飘向夜空；CapsLock 亮起，棕榈叶和船灯一起亮起来；'
        '很久没有输入，火慢慢熄灭，岛也垂下影子睡去。',
        ['#0a1430', '#1c2f5c', '#071226', '#ffcf7a', '#8fd6ff', '#7ee0b0', '#f2f6ff'],
        bg, ATTR)
    s.sticker('棕榈与草地', 60, 62, island_palm('calm'), '#7ee0b0', island_bg,
              caps=island_palm('caps'), caps_fg='#c8ffe0',
              react_fg='#a8f0c8',
              sleepy=island_palm('sleep'), sleepy_fg='#4f8a78')
    s.sticker('浮岛岩石', 60, 84, island_rock('calm'), '#7f92b0', rock_bg,
              caps=island_rock('caps'), caps_fg='#a8bcd8',
              react_fg='#93a8c4',
              sleepy_fg='#4f5f78')
    s.sticker('篝火', 135, 90, island_fire('calm'), '#ffcf7a', fire_bg,
              caps=island_fire('caps'), caps_fg='#ffe9a8',
              react=island_fire('caps'), react_fg='#ffb347',
              sleepy=island_fire('sleep'), sleepy_fg='#6a4432')
    s.sticker('小舟', 197, 138, island_boat('calm'), '#c9b48a', boat_bg,
              caps=island_boat('caps'), caps_fg='#ffe9a8',
              react_fg='#e8d8b0',
              sleepy_fg='#6a5f52')
    s.set_effect('ember', trigger='key', spawn=(132, 96, 26, 10), count=5, size=2,
                 colors=['#ffcf7a', '#ff8a4a', '#ffe9b0'], vx=(-26, 26),
                 vy=(-50, -18), gravity=-4, life_ms=2100)
    s.set_pulse('篝火', period_ms=1800, minimum=150)
    s.set_reaction(reactHoldMs=950, sleepyAfterMs=24000)
    s.statusInk = WHITE_INK
    return s


# ------------------------------------------------------------------------------ main
BUILDERS = (build_space, build_dungeon, build_cyber, build_forest,
            build_arcade, build_mecha, build_wizard, build_island)


def main():
    ok = 0
    for builder in BUILDERS:
        s = builder()
        d, meta = s.save()
        m = meta['masks']
        print('%-12s -> %-38s enc %4dB dec %4dB  %d layers' % (
            s.slug, meta['name'], m['encodedBytes'], m['decodedBytes'],
            len(meta['layers'])))
        ok += 1
    print('\n%d schemes written to %s' % (ok, PS.OUT))


if __name__ == '__main__':
    main()
