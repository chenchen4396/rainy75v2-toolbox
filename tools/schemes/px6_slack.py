"""Interactive px6 schemes: 摸鱼松弛 family (slacking / relaxing at work).

Eight 320x172 pixel schemes, four mood frames each (calm / caps / react / sleepy).
Every scheme is an "office slacking" scene: a lazy fish tank, a cat asleep on the
keyboard, an open bag of chips, a phone feed, a desk plant, a doodle pad, an old
CRT TV and a sheet of bubble wrap.

Run:
    .venv/Scripts/python.exe tools/schemes/px6_slack.py
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-*' --dir build/design-gallery

No hardware access.  SPDX-License-Identifier: MIT.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402

ATTRIB = '原创像素图形，全部由 tools/schemes/px6_slack.py 程序绘制'


# --------------------------------------------------------------------- helpers
def hexrgb(c):
    return PS.hexrgb(c)


def flat(im, x, y, w, h, colour):
    """Reserve a flat rectangle: the firmware repaints sticker rects with this colour."""
    ImageDraw.Draw(im).rectangle((x, y, x + w - 1, y + h - 1), fill=hexrgb(colour))


def ellipse(g, cx, cy, rx, ry, ch='#'):
    for dy in range(-ry, ry + 1):
        if ry <= 0:
            half = rx
        else:
            half = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / float(ry * ry))))
        g.rect(cx - half, cy + dy, cx + half, cy + dy, ch)


def heart(g, cx, cy, r, ch='#'):
    g.disc(cx - r, cy - r // 2, r, ch)
    g.disc(cx + r, cy - r // 2, r, ch)
    for i in range(r * 2 + 1):
        g.hline(cx - (r * 2 + 1 - i), cx + (r * 2 + 1 - i), cy + i, ch)


def star4(g, cx, cy, r):
    for i in range(1, r + 1):
        g.set(cx + i, cy); g.set(cx - i, cy)
        g.set(cx, cy + i); g.set(cx, cy - i)
    g.set(cx, cy)


def cross_hole(g, cx, cy, r):
    for i in range(1, r + 1):
        g.set(cx + i, cy, '.'); g.set(cx - i, cy, '.')
        g.set(cx, cy + i, '.'); g.set(cx, cy - i, '.')


# ===================================================================== 1 摸鱼缸
WATER = '#1a566b'
TANK_WATER_FG = '#ffb05c'


def fish_grid(state):
    g = Grid(46, 30)
    if state == 'sleepy':
        cy, ry = 21, 6
    elif state == 'react':
        cy, ry = 8, 6
    elif state == 'caps':
        cy, ry = 12, 7
    else:
        cy, ry = 16, 7
    ellipse(g, 24, cy, 12, ry)
    g.disc(34, cy, 5)
    if state == 'react':
        g.line(13, cy, 3, cy - 9, thick=2)
        g.line(13, cy, 4, cy + 8, thick=2)
    elif state == 'caps':
        g.line(13, cy, 4, cy - 7, thick=2)
        g.line(13, cy, 4, cy + 7, thick=2)
    elif state == 'sleepy':
        g.line(13, cy, 7, cy + 8, thick=2)
        g.line(13, cy, 4, cy - 1, thick=2)
    else:
        g.line(13, cy, 5, cy - 6, thick=2)
        g.line(13, cy, 6, cy + 9, thick=2)
    g.line(22, cy - ry, 28, cy - ry - 4, thick=2)      # dorsal fin
    g.line(23, cy + ry, 28, cy + ry + 3, thick=1)      # belly fin
    if state in ('calm', 'sleepy'):
        g.rect(32, cy - 2, 35, cy - 2, '.')            # closed eye
    else:
        g.rect(32, cy - 3, 33, cy - 2, '.')            # open eye
    if state == 'react':
        g.rect(38, cy - 1, 40, cy + 3, '.')            # wide open mouth
    else:
        g.rect(38, cy + 1, 39, cy + 1, '.')
    if state == 'react':
        for x0, y0 in ((4, cy + 11), (10, cy + 14), (2, cy + 7)):
            g.hline(x0, x0 + 5, y0)                    # speed streaks
        for x0, y0 in ((16, cy - 7), (25, cy - 8), (10, cy - 5)):
            g.set(x0, y0); g.set(x0 + 1, y0)           # splash droplets
    return g


def tank_bubble_grid(state):
    g = Grid(14, 46)

    def ring(cx, cy, r):
        g.ring(cx, cy, r)
        g.set(cx - 1, cy - 1, '.')

    if state == 'calm':
        ring(5, 38, 2)
        ring(9, 27, 2)
    elif state == 'caps':
        ring(5, 40, 2)
        ring(9, 31, 3)
        ring(5, 18, 2)
        ring(9, 7, 2)
    elif state == 'sleepy':
        ring(7, 24, 3)
    else:                                              # burst
        for cx, cy, r in ((6, 36, 3), (8, 22, 2), (4, 12, 2)):
            for k in range(8):
                a = k * math.pi / 4
                if k % 2:
                    g.set(round(cx + math.cos(a) * r), round(cy + math.sin(a) * r))
        for x, y in ((2, 30), (10, 28), (3, 18), (11, 15), (7, 5)):
            g.set(x, y)
    return g


def tank_weed_grid(state):
    g = Grid(22, 32)
    lean = {'calm': 0.0, 'caps': 2.5, 'react': 5.0, 'sleepy': -4.5}[state]
    for i, (x0, top) in enumerate(((6, 7), (11, 13), (16, 9))):
        direction = lean * (1 if i != 1 else -0.7)
        for y in range(top, 32):
            t = (y - top) / float(31 - top)
            xx = int(round(x0 + direction * t))
            g.set(xx, y)
            if y % 4 == 1 and 5 < y < 30:
                side = 1 if (y // 4) % 2 else -1
                g.line(xx, y, xx + side * 3, y - 2)
    return g


def tank_zzz_grid(state):
    g = Grid(20, 12)
    if state == 'calm':
        g.text('z', 7, 3)
    elif state == 'caps':
        g.text('zz', 3, 2)
    elif state == 'react':
        g.text('!', 7, 2)
    else:
        g.text('zz', 1, 2)
        g.text('z', 13, 5)
    return g


def build_fish_tank():
    bg = PS.vgrad('#0b1f28', '#123642', bands=10)
    d = ImageDraw.Draw(bg)
    for x in range(0, 320, 34):
        d.line([(x, 0), (x, 135)], fill=hexrgb('#102b36'))
    d.ellipse((34, 18, 78, 62), fill=hexrgb('#17333e'),
              outline=hexrgb('#5fb8c8'), width=2)
    d.line((56, 40, 56, 27), fill=hexrgb('#dff8ff'))
    d.line((56, 40, 66, 45), fill=hexrgb('#dff8ff'))
    d.rectangle((0, 136, 319, 171), fill=hexrgb('#2b2219'))
    d.rectangle((0, 136, 319, 138), fill=hexrgb('#4a3626'))
    for y in (148, 158, 167):
        d.line([(0, y), (319, y)], fill=hexrgb('#3a2c1f'))
    # tank body / water / sand
    d.rectangle((92, 46, 228, 133), fill=hexrgb('#0d3644'))
    d.rectangle((92, 61, 228, 133), fill=hexrgb(WATER))
    d.rectangle((92, 120, 228, 133), fill=hexrgb('#c9a878'))
    for x in range(92, 229, 4):
        d.point((x, 119), fill=hexrgb('#d9bc8c'))
    for px, py in ((98, 126), (146, 129), (176, 126), (214, 130), (126, 131)):
        d.rectangle((px, py, px + 3, py + 1), fill=hexrgb('#a98a5e'))
    for x in range(94, 228, 9):
        d.point((x, 128), fill=hexrgb('#b89a6a'))
    # little treasure chest on the sand
    d.rectangle((206, 104, 226, 119), fill=hexrgb('#5a3a28'))
    d.rectangle((205, 101, 227, 107), fill=hexrgb('#6b4632'))
    d.rectangle((214, 107, 218, 111), fill=hexrgb('#ffd27a'))
    # water surface
    d.line([(93, 61), (227, 61)], fill=hexrgb('#7fd8e8'))
    for x in range(96, 226, 14):
        d.point((x, 60), fill=hexrgb('#bff0f8'))
    # glass frame + reflections
    d.rectangle((88, 42, 232, 135), outline=hexrgb('#8fb8c0'), width=3)
    d.line((96, 48, 96, 112), fill=hexrgb('#2f6b7d'))
    d.line((224, 52, 224, 108), fill=hexrgb('#2f6b7d'))
    for x, y in ((98, 58), (222, 66), (98, 104), (222, 100)):
        d.point((x, y), fill=hexrgb('#cfeef4'))
    for r in ((100, 74, 46, 30), (152, 86, 22, 32), (186, 60, 14, 46), (100, 62, 20, 12)):
        flat(bg, r[0], r[1], r[2], r[3], WATER)

    s = PS.Scheme(
        'px6-fish-tank', '摸鱼缸',
        dict(family='摸鱼松弛', tags=['摸鱼', '水族', '陪伴', '放空'],
             story='鱼缸里的金鱼每天只做三件事：漂着、吐泡、假装很忙。它知道你也在假装很忙，'
                   '所以你们谁都不揭穿谁。'),
        '办公室桌角的摸鱼小缸：一条懒得动的金鱼、会冒泡的水草和沙底的小宝藏。每按一个键，'
        '气泡就从水底成群升起；敲得越久金鱼越兴奋，安静下来它就沉到沙上打瞌睡。',
        ['#0b1f28', '#1a566b', '#ffb05c', '#7fd8e8', '#c9a878', '#6fd08a', '#dff8ff'],
        bg, ATTRIB)
    s.sticker('金鱼', 100, 74, fish_grid('calm'), TANK_WATER_FG, WATER,
              caps=fish_grid('caps'), caps_fg='#ffc978',
              react=fish_grid('react'), react_fg='#ffe0a0',
              sleepy=fish_grid('sleepy'), sleepy_fg='#c98a52')
    s.sticker('水草', 152, 86, tank_weed_grid('calm'), '#6fd08a', WATER,
              caps=tank_weed_grid('caps'), caps_fg='#8ef0a8',
              react=tank_weed_grid('react'), react_fg='#b6ffc4',
              sleepy=tank_weed_grid('sleepy'), sleepy_fg='#4a9a6a')
    s.sticker('气泡', 186, 60, tank_bubble_grid('calm'), '#dff8ff', WATER,
              caps=tank_bubble_grid('caps'), caps_fg='#ffffff',
              react=tank_bubble_grid('react'), react_fg='#bfeaff',
              sleepy=tank_bubble_grid('sleepy'), sleepy_fg='#a9d8e8')
    s.sticker('瞌睡符', 100, 62, tank_zzz_grid('calm'), '#e9fbff', WATER,
              caps=tank_zzz_grid('caps'), caps_fg='#dff8ff',
              react=tank_zzz_grid('react'), react_fg='#ffe0a0',
              sleepy=tank_zzz_grid('sleepy'), sleepy_fg='#e9fbff')
    s.set_effect('bubble', trigger='key', spawn=(104, 64, 82, 34), count=5, size=3,
                 colors=['#bfeaff', '#e9fbff'], vx=(-12, 12), vy=(-46, -22),
                 gravity=0, life_ms=2400, edge='wrap', shape='diamond')
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=20000)
    s.statusInk = '#dff8ff'
    return s


# ======================================================================= 2 午睡
DESK_NAP = '#c08a54'


def nap_cat_grid(state):
    g = Grid(72, 28)
    if state == 'sleepy':
        ellipse(g, 26, 20, 20, 6)
    elif state == 'react':
        ellipse(g, 28, 20, 18, 7)
    else:
        ellipse(g, 28, 20, 19, 7)
    if state == 'react':
        g.line(5, 18, 1, 9, thick=2)
        g.line(1, 9, 7, 5, thick=2)
    elif state == 'sleepy':
        g.line(5, 21, 13, 25, thick=2)
        g.line(13, 25, 29, 26, thick=2)
    else:
        g.line(5, 19, 7, 25, thick=2)
        g.line(7, 25, 22, 26, thick=2)
    if state == 'react':
        hx, hy = 52, 12
    elif state == 'sleepy':
        hx, hy = 54, 18
    elif state == 'caps':
        hx, hy = 53, 15
    else:
        hx, hy = 52, 16
    g.disc(hx, hy, 9)
    g.line(hx - 7, hy - 5, hx - 9, hy - 11, thick=2)
    g.line(hx - 9, hy - 11, hx - 3, hy - 8, thick=2)
    g.line(hx + 2, hy - 7, hx + 4, hy - 12, thick=2)
    g.line(hx + 4, hy - 12, hx + 7, hy - 6, thick=2)
    if state == 'react':
        g.rect(hx - 5, hy - 3, hx - 4, hy - 2, '.')
        g.rect(hx + 1, hy - 3, hx + 2, hy - 2, '.')
        g.set(hx - 1, hy + 2, '.')
        g.rect(hx - 2, hy + 4, hx + 1, hy + 5, '.')
    elif state == 'caps':
        g.rect(hx - 5, hy - 1, hx - 2, hy - 1, '.')
        g.rect(hx + 1, hy - 2, hx + 2, hy - 1, '.')
    else:
        g.rect(hx - 5, hy - 1, hx - 2, hy - 1, '.')
        g.rect(hx + 1, hy - 1, hx + 4, hy - 1, '.')
    for dy in (hy - 1, hy + 2):
        g.hline(hx + 7, hx + 11, dy, '.')
    for cx in (14, 21, 28):
        g.rect(cx, 15, cx + 1, 19, '.')
    g.rect(38, 24, 42, 27)
    g.rect(46, 25, 50, 27)
    return g


def nap_keyboard_grid(state):
    g = Grid(84, 20)
    g.rect(0, 2, 83, 18)
    for ry in (7, 12):
        g.hline(1, 82, ry, '.')
    for base in (4, 16):
        x = base
        while x < 82:
            g.vline(x, 3, 6, '.')
            g.vline(x, 8, 11, '.')
            x += 12
    for x in range(1, 82, 18):
        g.vline(x, 13, 18, '.')
    if state == 'react':
        g.rect(15, 3, 22, 6, '.')
        g.rect(39, 3, 46, 6, '.')
        g.rect(63, 3, 70, 6, '.')
        g.rect(27, 13, 40, 18, '.')
    return g


def nap_zzz_grid(state):
    g = Grid(20, 20)
    if state == 'calm':
        g.text('z', 7, 10)
    elif state == 'caps':
        g.text('z', 2, 3)
        g.text('z', 11, 12)
    elif state == 'react':
        g.text('!', 5, 4, scale=2)
    else:
        g.text('z', 0, 2, scale=2)
        g.text('z', 13, 11)
    return g


def nap_sun_grid(state):
    g = Grid(46, 18)
    if state == 'sleepy':
        for y in range(6, 12):
            off = (y * 3) // 18
            g.hline(8 - off, 30 - off, y)
        return g
    for y in range(18):
        off = (y * 12) // 17
        x0, x1 = 15 - off, 44 - off
        g.hline(x0, x1, y)
        g.set(x0 + 10, y, '.')
        g.set(x0 + 21, y, '.')
    return g


def build_nap():
    bg = PS.blank('#f4dbb4')
    d = ImageDraw.Draw(bg)
    d.rectangle((16, 16, 108, 94), fill=hexrgb('#cfe8ff'))
    d.rectangle((16, 16, 108, 94), outline=hexrgb('#b07a4a'), width=4)
    d.line((62, 20, 62, 90), fill=hexrgb('#b07a4a'), width=3)
    d.line((20, 56, 104, 56), fill=hexrgb('#b07a4a'), width=3)
    for cx, cy in ((30, 34), (44, 34), (86, 70)):
        d.ellipse((cx, cy, cx + 18, cy + 7), fill=hexrgb('#eef6ff'))
    # wall shelf with a tiny plant, right of the window
    d.rectangle((248, 46, 306, 49), fill=hexrgb('#b07a4a'))
    d.rectangle((250, 49, 254, 54), fill=hexrgb('#96643c'))
    d.rectangle((300, 49, 304, 54), fill=hexrgb('#96643c'))
    d.rectangle((268, 34, 288, 46), fill=hexrgb('#c9542f'))
    d.rectangle((266, 32, 290, 36), fill=hexrgb('#e06a40'))
    for lx, ly in ((270, 23), (277, 19), (284, 24)):
        d.ellipse((lx, ly, lx + 9, ly + 9), fill=hexrgb('#7aa060'))
    # desk
    d.rectangle((0, 98, 319, 171), fill=hexrgb(DESK_NAP))
    d.rectangle((0, 98, 319, 101), fill=hexrgb('#d9a06a'))
    for y in (112, 132, 146, 160):
        for x0, x1 in ((0, 96), (184, 208), (258, 319)):
            d.line([(x0, y), (x1, y)], fill=hexrgb('#b07a48'))
    d.rectangle((282, 112, 306, 133), fill=hexrgb('#f2efe6'))
    d.rectangle((282, 112, 306, 117), fill=hexrgb('#e0dccc'))
    d.line((306, 118, 313, 118), fill=hexrgb('#f2efe6'), width=4)
    d.line((306, 124, 313, 124), fill=hexrgb('#f2efe6'), width=4)
    d.arc((306, 116, 316, 128), 270, 90, fill=hexrgb('#f2efe6'), width=2)
    d.line((288, 108, 286, 102), fill=hexrgb('#ffffff'))
    d.line((296, 108, 298, 100), fill=hexrgb('#ffffff'))
    flat(bg, 98, 128, 84, 20, DESK_NAP)
    flat(bg, 110, 102, 72, 28, DESK_NAP)
    flat(bg, 210, 128, 46, 18, DESK_NAP)
    flat(bg, 120, 66, 20, 20, '#f4dbb4')

    s = PS.Scheme(
        'px6-nap', '午睡',
        dict(family='摸鱼松弛', tags=['午睡', '猫', '治愈', '放空'],
             story='猫把键盘当成了热乎乎的枕头。你打字，它就跟着呼噜；你停下，它就把尾巴搭在你手边，'
                   '说这一天还长，先睡一会儿。'),
        '午后两点的工位，键盘还在发光，猫已经趴上去睡了。按键像在给它顺毛：它耳朵抖一抖、眼睛半睁，'
        '敲得久了会猛地抬头看你；你一停手，它又卷成一团睡回去。',
        ['#f4dbb4', '#c08a54', '#f0b37e', '#e8eef8', '#3a3f4a', '#ffe9b0', '#b07a4a'],
        bg, ATTRIB)
    s.sticker('键盘', 98, 128, nap_keyboard_grid('calm'), '#e8eef8', DESK_NAP,
              caps_fg='#fff6d8', react_fg='#dfeaff',
              sleepy_fg='#8f96a8')
    s.sticker('小猫', 110, 102, nap_cat_grid('calm'), '#f0b37e', DESK_NAP,
              caps_fg='#ffd9a8',
              react=nap_cat_grid('react'), react_fg='#ffd49e',
              sleepy=nap_cat_grid('sleepy'), sleepy_fg='#c98f5f')
    s.sticker('瞌睡符', 120, 66, nap_zzz_grid('calm'), '#8a6a4a', '#f4dbb4',
              caps=nap_zzz_grid('caps'), caps_fg='#a07a52',
              react=nap_zzz_grid('react'), react_fg='#c9542f',
              sleepy=nap_zzz_grid('sleepy'), sleepy_fg='#a07a52')
    s.sticker('午后光斑', 210, 128, nap_sun_grid('calm'), '#ffe9b0', DESK_NAP,
              caps_fg='#fff3c8',
              sleepy=nap_sun_grid('sleepy'), sleepy_fg='#c99a5a')
    s.set_effect('dust', trigger='key', spawn=(62, 58, 176, 48), count=4, size=1,
                 colors=['#fff4d0', '#ffe6b0'], vx=(-14, 14), vy=(-16, -4),
                 gravity=-2, life_ms=3600, edge='wrap', shape='square')
    s.set_pulse('午后光斑', period_ms=3000, minimum=150)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=22000)
    s.statusInk = '#6b4a2a'
    return s


# ======================================================================= 3 薯片
WALL_SNACK = '#2a2230'
DESK_SNACK = '#4a3a44'


def snack_bag_grid(state):
    g = Grid(32, 46)
    if state == 'sleepy':
        g.rect(1, 22, 29, 45)
        g.rect(1, 18, 21, 30)
        g.rect(20, 21, 29, 33, '.')
        for x in (5, 10, 15):
            g.line(x, 30, x + 4, 34, '.')
        return g
    for y in range(9, 46):
        t = (y - 9) / 36.0
        wide = int(2 * t)
        g.rect(4 - wide, y, 27 + wide, y)
    if state == 'caps':
        g.rect(9, 4, 22, 17, '.')
        for x in (9, 13, 17, 21):
            g.set(x, 8, '.')
    elif state == 'react':
        g.rect(7, 4, 24, 15, '.')
        for x in (7, 12, 17, 22):
            g.line(x, 15, x + 2, 18, '.')
    else:
        for x in range(1, 31, 3):
            g.rect(x, 4, x + 1, 8)
    # dark label band with a red fish logo (摸鱼 brand)
    g.rect(6, 25, 25, 39, '.')
    ellipse(g, 15, 32, 5, 3)
    g.line(10, 32, 6, 28)
    g.line(10, 32, 6, 36)
    g.set(18, 31, '.')
    for x in (4, 10, 16, 22, 28):
        g.set(x, 43, '.')
        g.set(x, 41, '.')
    return g


def snack_chip_grid(state):
    g = Grid(30, 36)

    def chip(cx, cy):
        widths = (2, 5, 7, 7, 6, 4, 2)
        for dy, half in enumerate(widths):
            g.rect(cx - half, cy + dy - 3, cx + half, cy + dy - 3)
        for dx, dy in ((-5, 0), (6, 0), (-2, -3), (3, -3), (1, 3)):
            g.set(cx + dx, cy + dy, '.')

    if state == 'calm':
        chip(14, 30)
    elif state == 'caps':
        chip(8, 30)
        chip(20, 18)
    elif state == 'react':
        chip(8, 9)
        chip(20, 17)
        chip(13, 29)
    return g


def snack_crumb_grid(state):
    g = Grid(60, 14)
    spots = {
        'calm': ((4, 10), (9, 18), (15, 12), (31, 16), (44, 10), (52, 14)),
        'caps': ((3, 9), (8, 15), (14, 11), (20, 14), (27, 9), (36, 13), (45, 11), (54, 15)),
        'react': ((2, 8), (7, 13), (12, 9), (18, 15), (24, 11), (30, 8), (36, 14),
                  (42, 10), (48, 14), (54, 9), (58, 13)),
        'sleepy': ((6, 9), (22, 13), (40, 10)),
    }[state]
    for x, w in spots:
        g.hline(x, x + w % 3 + 1, 6)
    for x, w in spots[::2]:
        g.hline(x + 1, x + 4, 8)
    for x, w in spots[1::3]:
        g.set(x + 2, 3)
    return g


def snack_can_grid(state):
    g = Grid(20, 28)
    g.rect(3, 5, 16, 27)
    g.rect(2, 3, 17, 6)
    g.rect(2, 24, 17, 27)
    if state == 'caps':
        g.rect(7, 2, 13, 5, '.')
        g.line(14, 1, 17, 5, thick=2)
    elif state == 'react':
        g.rect(7, 2, 13, 5, '.')
        for x, y in ((4, 1), (9, 0), (15, 1)):
            g.set(x, y)
        g.set(8, 8, '.')
    else:
        g.rect(8, 8, 12, 10, '.')
        g.hline(5, 14, 18, '.')
    return g


def build_snack():
    bg = PS.blank('#2a2230')
    d = ImageDraw.Draw(bg)
    # wall shelf with the snack stash
    d.rectangle((14, 62, 132, 65), fill=hexrgb('#3d3345'))
    d.rectangle((18, 60, 24, 62), fill=hexrgb('#3d3345'))
    d.rectangle((24, 42, 44, 60), fill=hexrgb('#5a4a3a'))
    d.rectangle((24, 42, 44, 46), fill=hexrgb('#6b5a46'))
    d.rectangle((48, 50, 66, 60), fill=hexrgb('#7a5c46'))
    d.rectangle((48, 50, 66, 53), fill=hexrgb('#8f6c52'))
    d.rectangle((70, 46, 84, 60), fill=hexrgb('#4a3a4a'))
    d.rectangle((73, 40, 80, 47), fill=hexrgb('#4a3a4a'))
    # framed fish poster (office humour)
    d.rectangle((152, 34, 210, 76), fill=hexrgb('#3a3040'))
    d.rectangle((155, 37, 207, 73), fill=hexrgb('#4a3f5c'))
    d.ellipse((170, 48, 196, 64), fill=hexrgb('#ffd27a'))
    d.polygon([(170, 56), (160, 46), (160, 66)], fill=hexrgb('#ffd27a'))
    d.rectangle((186, 51, 189, 54), fill=hexrgb('#4a3f5c'))
    for x in range(158, 205, 9):
        d.point((x, 70), fill=hexrgb('#8a7aa0'))
    # desk
    d.rectangle((0, 136, 319, 171), fill=hexrgb(DESK_SNACK))
    d.rectangle((0, 136, 319, 139), fill=hexrgb('#5f4a56'))
    for y in (154, 162, 170):
        d.line([(0, y), (319, y)], fill=hexrgb('#42343e'))
    for r in ((198, 90, 32, 46), (150, 100, 30, 36), (150, 136, 60, 14),
              (256, 108, 20, 28)):
        flat(bg, r[0], r[1], r[2], r[3], WALL_SNACK if r[1] < 136 else DESK_SNACK)

    s = PS.Scheme(
        'px6-snack', '薯片',
        dict(family='摸鱼松弛', tags=['零食', '摸鱼', '解压', '办公室'],
             story='薯片袋一开，整个工位都听得见。你一边心虚一边把袋子转了半圈，'
                   '仿佛这样就没有人发现——就像没有人发现你已经摸了半小时鱼。'),
        '偷偷开袋的薯片是下午的底气。每按一个键，就有一小把薯片碎屑从袋口蹦出来，敲得越欢撒得越远；'
        '袋子慢慢见底，最后只剩桌上一层碎屑和一只空袋。',
        ['#241d2b', '#4a3a44', '#e8563f', '#f2c063', '#ffe9a8', '#c9b09a', '#8a6a4a'],
        bg, ATTRIB)
    s.sticker('薯片袋', 198, 90, snack_bag_grid('calm'), '#e8563f', WALL_SNACK,
              caps=snack_bag_grid('caps'), caps_fg='#f26a50',
              react=snack_bag_grid('react'), react_fg='#d94a35',
              sleepy=snack_bag_grid('sleepy'), sleepy_fg='#b8493a')
    s.sticker('薯片', 150, 100, snack_chip_grid('calm'), '#f2c063', WALL_SNACK,
              caps_fg='#ffd88a',
              react=snack_chip_grid('react'), react_fg='#ffe9a8',
              sleepy=snack_chip_grid('sleepy'), sleepy_fg='#c9a05a')
    s.sticker('碎屑', 150, 136, snack_crumb_grid('calm'), '#e8c98a', DESK_SNACK,
              caps=snack_crumb_grid('caps'), caps_fg='#ffe9b8',
              react=snack_crumb_grid('react'), react_fg='#fff4d0',
              sleepy=snack_crumb_grid('sleepy'), sleepy_fg='#b89a72')
    s.sticker('可乐罐', 256, 108, snack_can_grid('calm'), '#5fc8b0', WALL_SNACK,
              caps=snack_can_grid('caps'), caps_fg='#7fe0c8',
              react=snack_can_grid('react'), react_fg='#8ff0d8',
              sleepy_fg='#3f9a88')
    s.set_effect('confetti', trigger='key', spawn=(198, 80, 30, 10), count=7, size=2,
                 colors=['#f2c063', '#e8a94a', '#ffe9a8', '#e8563f'],
                 vx=(-150, 150), vy=(-170, -60), gravity=190, life_ms=1200,
                 edge='bounce', shape='square')
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=18000)
    s.statusInk = '#ffe9c0'
    return s


# ==================================================================== 4 刷手机
WALL_PHONE = '#1b2030'
SCREEN_BG = WALL_PHONE


def phone_feed_grid(state):
    g = Grid(28, 40)
    if state == 'calm':
        g.hline(1, 26, 1)
        g.disc(5, 6, 2)
        g.hline(9, 20, 5)
        g.hline(9, 15, 8)
        g.rect(2, 12, 25, 26)
        g.disc(14, 18, 4, '.')
        g.rect(10, 13, 11, 15, '.')
        g.rect(16, 13, 17, 15, '.')
        g.rect(11, 21, 17, 25, '.')
        heart(g, 5, 30, 1)
        g.hline(9, 18, 31)
        g.hline(2, 22, 35)
    elif state == 'caps':
        g.hline(1, 26, 1)
        g.rect(2, 4, 25, 16)
        g.disc(13, 10, 4, '.')
        g.rect(9, 6, 10, 8, '.')
        g.rect(15, 6, 16, 8, '.')
        g.hline(2, 19, 19)
        g.hline(2, 24, 22)
        g.rect(2, 26, 25, 37)
        g.text('z', 11, 30)
        g.hline(2, 20, 39, '.')
    elif state == 'react':
        g.hline(1, 26, 1)
        heart(g, 13, 11, 5)
        for r in (8, 11):
            g.ring(12, 12, r)
        g.text('99', 7, 25)
        g.hline(2, 24, 35)
    else:
        g.hline(1, 26, 1)
        g.text('z', 9, 8, scale=2)
        g.hline(4, 14, 26)
        g.hline(4, 10, 30)
        g.hline(4, 20, 35)
    return g


def phone_heart_grid(state):
    g = Grid(14, 16)
    if state == 'caps':
        heart(g, 5, 6, 3)
    elif state == 'react':
        heart(g, 5, 5, 4)
        for x, y in ((12, 1), (12, 9), (1, 13)):
            g.set(x, y)
    return g


def phone_finger_grid(state):
    g = Grid(18, 26)
    if state == 'sleepy':
        return g
    if state == 'caps':
        g.rect(8, 4, 17, 13)
        g.rect(2, 6, 8, 11)
        g.disc(3, 8, 3)
        g.rect(1, 7, 3, 8, '.')
        g.disc(11, 14, 3)
    elif state == 'react':
        g.rect(7, 8, 17, 18)
        g.rect(2, 10, 7, 16)
        g.disc(2, 13, 3)
        g.line(0, 8, 2, 9)
        g.line(0, 18, 2, 17)
        g.set(0, 13)
    else:
        g.rect(8, 8, 17, 17)
        g.rect(2, 10, 8, 15)
        g.disc(3, 12, 3)
        g.rect(1, 11, 3, 12, '.')
        g.disc(12, 18, 3)
    return g


def build_phone():
    bg = PS.blank('#1b2030')
    d = ImageDraw.Draw(bg)
    # night window on the left
    d.rectangle((30, 30, 108, 100), fill=hexrgb('#0e1a2e'))
    d.rectangle((30, 30, 108, 100), outline=hexrgb('#3a3448'), width=3)
    d.line((69, 33, 69, 97), fill=hexrgb('#3a3448'), width=2)
    d.line((33, 65, 105, 65), fill=hexrgb('#3a3448'), width=2)
    d.ellipse((78, 38, 94, 54), fill=hexrgb('#f2e4c0'))
    for sx, sy in ((42, 42), (56, 54), (96, 82), (46, 84), (62, 46), (88, 44)):
        d.point((sx, sy), fill=hexrgb('#cfe2ff'))
    d.polygon([(20, 26), (30, 30), (30, 100), (20, 104)], fill=hexrgb('#2a3350'))
    d.polygon([(112, 28), (120, 24), (120, 106), (112, 100)], fill=hexrgb('#2a3350'))
    # desk
    d.rectangle((0, 131, 319, 171), fill=hexrgb('#262b3a'))
    d.rectangle((0, 131, 319, 133), fill=hexrgb('#3a4257'))
    for y in (146, 158, 168):
        d.line([(0, y), (238, y)], fill=hexrgb('#202533'))
        d.line((266, y, 319, y), fill=hexrgb('#202533'))
    PS.glow(bg, 169, 100, 62, '#232c46', steps=2)
    d.rectangle((252, 108, 276, 130), fill=hexrgb('#2f3444'))
    d.rectangle((252, 108, 276, 113), fill=hexrgb('#3a4257'))
    d.line((276, 114, 283, 114), fill=hexrgb('#2f3444'), width=3)
    d.line((276, 122, 283, 122), fill=hexrgb('#2f3444'), width=3)
    d.arc((276, 112, 285, 124), 270, 90, fill=hexrgb('#2f3444'), width=2)
    d.line((256, 104, 254, 98), fill=hexrgb('#ffffff'))
    d.line((268, 104, 270, 96), fill=hexrgb('#ffffff'))
    for r in ((150, 75, 38, 56), (155, 83, 28, 40), (168, 58, 14, 16),
              (188, 86, 18, 26)):
        flat(bg, r[0], r[1], r[2], r[3], WALL_PHONE)

    s = PS.Scheme(
        'px6-phone', '刷手机',
        dict(family='摸鱼松弛', tags=['手机', '摸鱼', '夜', '上瘾'],
             story='你把手机竖起来假装在看资料，其实在看猫。屏幕光打在脸上，'
                   '像一个小小的、属于你自己的晚上。'),
        '会议间隙的那五分钟，全给了手机。屏幕里的猫片一条接一条，每按一个键就有一个红心飘起来；'
        '刷到精彩处手指狂点，放空久了屏幕就暗下去，只剩一个小小的 z。',
        ['#1b2030', '#262b3a', '#e8dcc8', '#dfeaff', '#ff6f9f', '#7ad7ff', '#2a3350'],
        bg, ATTRIB)
    s.sticker('手机', 150, 75, phone_grid_art(), '#e8dcc8', SCREEN_BG,
              caps_fg='#f4ecd8', react_fg='#fff6e0', sleepy_fg='#8f8a7c')
    s.sticker('屏幕', 155, 83, phone_feed_grid('calm'), '#dfeaff', SCREEN_BG,
              caps=phone_feed_grid('caps'), caps_fg='#eaf2ff',
              react=phone_feed_grid('react'), react_fg='#ff8fb0',
              sleepy=phone_feed_grid('sleepy'), sleepy_fg='#5f6b85')
    s.sticker('爱心', 168, 58, phone_heart_grid('calm'), '#ff6f9f', WALL_PHONE,
              caps=phone_heart_grid('caps'), caps_fg='#ff8fb0',
              react=phone_heart_grid('react'), react_fg='#ffb3c7')
    s.sticker('手指', 188, 86, phone_finger_grid('calm'), '#f0c8a0', WALL_PHONE,
              caps=phone_finger_grid('caps'), caps_fg='#ffd9b8',
              react=phone_finger_grid('react'), react_fg='#ffd9b8',
              sleepy=phone_finger_grid('sleepy'))
    s.set_effect('heart', trigger='key', spawn=(156, 52, 30, 10), count=3, size=3,
                 colors=['#ff6f9f', '#ffb3c7'], vx=(-30, 30), vy=(-70, -30),
                 gravity=18, life_ms=2200, edge='die', shape='plus')
    s.set_pulse('爱心', period_ms=1600, minimum=150)
    s.set_reaction(reactHoldMs=850, sleepyAfterMs=20000)
    s.statusInk = '#cfe2ff'
    return s


def phone_grid_art():
    g = Grid(38, 56)
    g.rect(1, 0, 36, 55)
    for cx, cy in ((0, 0), (36, 0), (0, 54), (36, 54)):
        g.rect(cx, cy, cx + 1, cy + 1, '.')
    g.rect(15, 2, 22, 3, '.')
    g.rect(27, 5, 29, 7, '.')
    g.rect(4, 7, 33, 47, '.')
    g.rect(15, 50, 22, 51, '.')
    return g


# ======================================================================= 5 绿植
WALL_PLANT = '#efe3cc'
DESK_PLANT = '#a8744a'


def plant_pot_grid(state):
    g = Grid(30, 30)
    g.rect(1, 2, 28, 8)
    for y in range(9, 30):
        t = (y - 9) / 20.0
        half = int(10 - 4 * t)
        g.rect(15 - half, y, 15 + half, y)
    if state == 'sleepy':
        for y in range(9, 30):
            t = (y - 9) / 20.0
            g.set(int(5 + 4 * t), y, '.')
    g.hline(5, 24, 13, '.')
    g.hline(5, 21, 15, '.')
    g.set(11, 19, '.')
    return g


def plant_leaf_grid(state):
    g = Grid(40, 38)
    dy = {'calm': 0, 'caps': -4, 'react': -1, 'sleepy': 6}[state]
    lean = {'calm': 0, 'caps': -1, 'react': 4, 'sleepy': 8}[state]
    base_x, base_y = 20, 37
    spec = ((3, 20, 6, 4), (12, 9, 6, 5), (26, 6, 5, 6), (35, 19, 5, 4))
    for i, (tx, ty, rx, ry) in enumerate(spec):
        ty = max(4, ty + dy + (3 if i % 2 else 0))
        tx = min(37, max(2, tx + int(lean * (0.4 + 0.2 * i))))
        g.line(base_x, base_y - 2, tx, ty + ry - 2, thick=2)
        ellipse(g, tx, ty, rx, ry)
        g.line(tx, ty - ry + 1, tx, ty - 1, '.')
    for x, y in ((20, 33), (19, 29), (21, 26)):
        g.set(x, y)
    return g


def plant_flower_grid(state):
    g = Grid(14, 14)
    if state == 'calm':
        ellipse(g, 7, 8, 2, 3)
        g.line(7, 11, 7, 13)
    elif state == 'caps':
        for k in range(5):
            a = -math.pi / 2 + k * math.tau / 5
            g.disc(round(7 + math.cos(a) * 3), round(6 + math.sin(a) * 3), 2)
        g.set(7, 6, '.')
    elif state == 'react':
        for k in range(5):
            a = -math.pi / 2 + k * math.tau / 5
            g.disc(round(8 + math.cos(a) * 4), round(7 + math.sin(a) * 4), 2)
        g.set(8, 7, '.')
        g.set(2, 2)
        g.set(13, 3)
    else:
        ellipse(g, 7, 10, 2, 3)
        g.line(7, 13, 7, 13)
    return g


def plant_note_grid(state):
    g = Grid(24, 22)
    g.rect(1, 1, 22, 20)
    g.rect(18, 16, 22, 20, '.')
    g.line(18, 16, 22, 16, '.')
    if state == 'calm':
        ellipse(g, 10, 11, 5, 3, '.')
        g.line(5, 11, 2, 8, '.')
        g.line(5, 11, 2, 14, '.')
        g.set(12, 10)
    elif state == 'caps':
        heart(g, 9, 10, 3, '.')
    elif state == 'react':
        star4(g, 10, 9, 4)
        g.text('!', 17, 13)
    else:
        g.text('zz', 6, 9)
    return g


def build_plant():
    bg = PS.blank(WALL_PLANT)
    d = ImageDraw.Draw(bg)
    d.rectangle((18, 18, 106, 96), fill=hexrgb('#cfe8ff'))
    d.rectangle((18, 18, 106, 96), outline=hexrgb('#b07a4a'), width=4)
    d.line((62, 22, 62, 92), fill=hexrgb('#b07a4a'), width=3)
    d.line((22, 58, 102, 58), fill=hexrgb('#b07a4a'), width=3)
    for cx, cy in ((30, 32), (74, 72)):
        d.ellipse((cx, cy, cx + 20, cy + 8), fill=hexrgb('#eef6ff'))
    d.rectangle((0, 136, 319, 171), fill=hexrgb(DESK_PLANT))
    d.rectangle((0, 136, 319, 139), fill=hexrgb('#c08a5a'))
    for y in (152, 164):
        d.line([(0, y), (319, y)], fill=hexrgb('#96643c'))
    for r in ((130, 68, 40, 38), (150, 106, 30, 30), (146, 58, 14, 14),
              (204, 104, 24, 22)):
        flat(bg, r[0], r[1], r[2], r[3], WALL_PLANT)

    s = PS.Scheme(
        'px6-plant', '绿植',
        dict(family='摸鱼松弛', tags=['绿植', '办公室', '呼吸', '治愈'],
             story='绿植不会催你交表，也不会问你进度。它只是在你敲字的时候摇一摇叶子，'
                   '提醒你：光照够了，水也够了，人也是。'),
        '工位上的绿植比你更会摸鱼。键盘一响，叶片就跟着轻轻晃，阳光里的粉尘也飘起来；'
        '认真打字时它会精神起来，久久不动它就蔫下去，和加班的你一起叹气。',
        ['#f3e8d4', '#a8744a', '#c9542f', '#6fd08a', '#3f7a4a', '#ffd27a', '#d9f7a8'],
        bg, ATTRIB)
    s.sticker('叶片', 130, 68, plant_leaf_grid('calm'), '#6fd08a', WALL_PLANT,
              caps_fg='#8ee8a8',
              react=plant_leaf_grid('react'), react_fg='#b6ffc4',
              sleepy=plant_leaf_grid('sleepy'), sleepy_fg='#4a9a62')
    s.sticker('花盆', 150, 106, plant_pot_grid('calm'), '#c9542f', WALL_PLANT,
              caps_fg='#e06a40', sleepy=plant_pot_grid('sleepy'), sleepy_fg='#a8442a')
    s.sticker('小花', 146, 58, plant_flower_grid('calm'), '#ffd27a', WALL_PLANT,
              caps=plant_flower_grid('caps'), caps_fg='#ffe49a',
              react=plant_flower_grid('react'), react_fg='#fff0b8',
              sleepy=plant_flower_grid('sleepy'), sleepy_fg='#c9a05a')
    s.sticker('便签', 204, 104, plant_note_grid('calm'), '#f2b03a', WALL_PLANT,
              caps=plant_note_grid('caps'), caps_fg='#ffc85a',
              react=plant_note_grid('react'), react_fg='#ffd27a',
              sleepy_fg='#b8913c')
    s.set_effect('dust', trigger='key', spawn=(120, 58, 62, 44), count=4, size=1,
                 colors=['#d9f7a8', '#fff6b0'], vx=(-16, 16), vy=(-18, -5),
                 gravity=-2, life_ms=3600, edge='wrap', shape='square')
    s.set_reaction(reactHoldMs=950, sleepyAfterMs=19000)
    s.statusInk = '#5a4a30'
    return s


# ====================================================================== 6 涂鸦
PAPER = '#f4efe2'
DESK_DOODLE = '#3a3148'


def doodle_cat(g, ox, oy):
    ellipse(g, ox + 12, oy + 12, 9, 8)
    g.line(ox + 4, oy + 6, ox + 2, oy - 1, thick=2)
    g.line(ox + 2, oy - 1, ox + 8, oy + 4, thick=2)
    g.line(ox + 20, oy + 6, ox + 22, oy - 1, thick=2)
    g.line(ox + 22, oy - 1, ox + 16, oy + 4, thick=2)
    g.rect(ox + 7, oy + 9, ox + 8, oy + 10, '.')
    g.rect(ox + 15, oy + 9, ox + 16, oy + 10, '.')
    g.set(ox + 12, oy + 14, '.')
    g.line(ox + 12, oy + 15, ox + 12, oy + 17, '.')
    g.line(ox + 8, oy + 16, ox + 4, oy + 15, '.')
    g.line(ox + 16, oy + 16, ox + 20, oy + 15, '.')


def doodle_fish(g, ox, oy):
    ellipse(g, ox + 16, oy + 8, 12, 6)
    g.line(ox + 4, oy + 8, ox - 4, oy + 1, thick=2)
    g.line(ox + 4, oy + 8, ox - 4, oy + 15, thick=2)
    g.set(ox + 24, oy + 6, '.')
    g.set(ox + 27, oy + 9, '.')


def doodle_main_grid(state):
    g = Grid(68, 38)
    if state == 'calm':
        doodle_cat(g, 8, 8)
        g.text('zz', 46, 24)
        star4(g, 56, 8, 3)
    elif state == 'caps':
        doodle_cat(g, 6, 6)
        star4(g, 50, 6, 3)
        star4(g, 60, 16, 2)
        heart(g, 52, 28, 3)
        g.hline(4, 30, 34)
    elif state == 'react':
        doodle_fish(g, 6, 12)
        g.text('!!', 48, 8)
        star4(g, 58, 14, 2)
        for x, y in ((20, 30), (34, 32), (44, 26)):
            g.set(x, y)
    else:
        doodle_cat(g, 10, 8)
        for x in range(4, 62, 7):
            g.line(x, 32, x + 4, 35, '.')
        g.text('..', 52, 12)
    return g


def doodle_side_grid(state):
    g = Grid(56, 34)
    if state == 'calm':
        star4(g, 10, 10, 3)
        star4(g, 26, 20, 2)
        g.line(36, 8, 52, 8, '.')
        g.line(36, 10, 48, 10, '.')
    elif state == 'caps':
        heart(g, 14, 12, 4)
        heart(g, 36, 20, 3)
        g.text('Y', 44, 6)
    elif state == 'react':
        for cx, cy, r in ((8, 8, 3), (24, 6, 2), (40, 10, 3), (16, 24, 2), (34, 22, 2)):
            star4(g, cx, cy, r)
        g.line(4, 30, 52, 30, '.')
    else:
        g.text('...', 6, 8)
        g.line(6, 24, 48, 24, '.')
        g.line(6, 27, 30, 27, '.')
    return g


def doodle_pen_grid(state):
    g = Grid(36, 14)
    g.line(6, 11, 30, 4, thick=2)
    g.line(31, 3, 34, 3, thick=2)
    g.rect(2, 9, 7, 13)
    g.set(4, 11, '.')
    g.set(3, 10, '.')
    g.line(12, 9, 13, 7, '.')
    if state == 'caps':
        g.set(0, 10)
        g.set(1, 13)
    elif state == 'react':
        g.line(2, 8, 0, 6, thick=1)
        for x, y in ((0, 4), (4, 3), (8, 12)):
            g.set(x, y)
        g.line(8, 12, 11, 13, '.')
    return g


def build_doodle():
    bg = PS.vgrad('#221f30', '#2a273a', bands=10)
    d = ImageDraw.Draw(bg)
    d.line((30, 0, 30, 20), fill=hexrgb('#3a3446'))
    d.polygon([(18, 20), (42, 20), (50, 38), (10, 38)], fill=hexrgb('#ffd27a'))
    d.polygon([(21, 22), (39, 22), (45, 34), (15, 34)], fill=hexrgb('#ffe9b8'))
    for r in (4, 7, 10):
        d.arc((30 - r * 2, 38 - r, 30 + r * 2, 38 + r), 200, 340,
              fill=hexrgb('#5a4a3a'), width=1)
    for x in range(0, 320, 36):
        d.line([(x, 0), (x, 117)], fill=hexrgb('#282535'))
    d.rectangle((0, 118, 319, 171), fill=hexrgb(DESK_DOODLE))
    d.rectangle((0, 118, 319, 120), fill=hexrgb('#4a3f5e'))
    for y in (134, 152, 166):
        d.line([(0, y), (319, y)], fill=hexrgb('#322a44'))
    # sketch pad (static): shadow, sheet, spiral binding
    d.rounded_rectangle((58, 74, 270, 154), radius=5, fill=hexrgb('#241f2e'))
    d.rounded_rectangle((54, 70, 266, 150), radius=4, fill=hexrgb(PAPER))
    d.rounded_rectangle((54, 70, 266, 150), radius=4, outline=hexrgb('#d8d0bc'))
    for x in range(64, 258, 13):
        d.ellipse((x, 66, x + 5, 72), fill=hexrgb('#8f8fa8'))
    for y in (80, 146):
        d.line((66, y, 258, y), fill=hexrgb('#e4ddcc'))
    d.line((62, 78, 62, 146), fill=hexrgb('#e0d8c4'))
    for r in ((72, 88, 68, 38), (152, 88, 56, 34), (210, 120, 36, 14)):
        flat(bg, r[0], r[1], r[2], r[3], PAPER)

    s = PS.Scheme(
        'px6-doodle', '涂鸦',
        dict(family='摸鱼松弛', tags=['涂鸦', '开会', '摸鱼', '手账'],
             story='本子角落的涂鸦越积越多，一只猫、两颗星、一条假装在认真工作的鱼。'
                   '等会议开完，它们就变成你这一天最诚实的记录。'),
        '开会时偷偷在便签本上涂鸦，画猫、画星星、画一条摸鱼的鱼。每按一个键笔尖就溅出一点墨星，'
        '敲得入神时画面自己长出新涂鸦；停下来只剩一片空白的纸。',
        ['#221f30', '#3a3148', '#f4efe2', '#2a2a38', '#ff8fb0', '#7ad7ff', '#ffe9a8'],
        bg, ATTRIB)
    s.sticker('涂鸦', 72, 88, doodle_main_grid('calm'), '#2a2a38', PAPER,
              caps=doodle_main_grid('caps'), caps_fg='#3a3a4c',
              react=doodle_main_grid('react'), react_fg='#ff8fb0',
              sleepy=doodle_main_grid('sleepy'), sleepy_fg='#9a94a8')
    s.sticker('小涂鸦', 152, 88, doodle_side_grid('calm'), '#2a2a38', PAPER,
              caps=doodle_side_grid('caps'), caps_fg='#ff8fb0',
              react=doodle_side_grid('react'), react_fg='#7ad7ff',
              sleepy=doodle_side_grid('sleepy'), sleepy_fg='#9a94a8')
    s.sticker('铅笔', 210, 120, doodle_pen_grid('calm'), '#ffe9a8', PAPER,
              caps=doodle_pen_grid('caps'), caps_fg='#fff3c8',
              react=doodle_pen_grid('react'), react_fg='#ff8fb0',
              sleepy_fg='#c9bfa0')
    s.set_effect('spark', trigger='key', spawn=(204, 114, 30, 12), count=8, size=2,
                 colors=['#ff8fb0', '#7ad7ff', '#ffe9a8'], vx=(-140, 140),
                 vy=(-150, -50), gravity=180, life_ms=1000, edge='bounce', shape='plus')
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=17000)
    s.statusInk = '#f4efe2'
    return s


# =================================================================== 7 老电视
BEIGE_TV = '#e8cfa8'
SCREEN_DARK = '#0f1c22'
CABINET_TV = '#4a3628'
WALL_TV = '#1b1a24'


def tv_screen_grid(state):
    g = Grid(62, 44)
    if state == 'calm':
        g.line(2, 16, 59, 16, thick=1)
        for x in range(4, 58, 9):
            g.set(x, 15)
        ellipse(g, 30, 22, 12, 6)
        g.line(20, 22, 12, 16, thick=2)
        g.line(20, 22, 12, 28, thick=2)
        g.set(38, 19, '.')
        g.ring(46, 12, 2)
        g.ring(52, 18, 1)
        g.line(2, 34, 59, 34)
        for x in range(6, 56, 11):
            g.line(x, 38, x + 3, 38)
    elif state == 'caps':
        for i in range(8):
            x0 = 1 + i * 8
            g.rect(x0, 2, x0 + 5, 41)
        g.hline(0, 61, 0)
        g.hline(0, 61, 43)
    elif state == 'react':
        for y in range(0, 44, 2):
            off = (y // 2) % 4
            for x in range(0, 62, 8):
                x0 = (x + off * 2) % 62
                g.hline(x0, min(61, x0 + 3), y)
        g.line(4, 4, 16, 20, thick=2)
        g.line(16, 20, 8, 26, thick=2)
        g.line(8, 26, 20, 38, thick=2)
    else:
        for y in (6, 14, 22):
            g.line(0, y, 61, y, '.')
        g.text('z', 24, 10, scale=2)
        g.hline(6, 22, 32)
        g.hline(38, 56, 30)
    return g


def tv_antenna_grid(state):
    g = Grid(30, 26)
    if state == 'caps':
        g.line(15, 24, 12, 2, thick=2)
        g.line(15, 24, 18, 2, thick=2)
    elif state == 'react':
        g.line(15, 24, 10, 14, thick=2)
        g.line(10, 14, 12, 6, thick=2)
        g.line(15, 24, 20, 14, thick=2)
        g.line(20, 14, 18, 6, thick=2)
    elif state == 'sleepy':
        g.line(15, 24, 6, 20, thick=2)
        g.line(15, 24, 24, 20, thick=2)
    else:
        g.line(15, 24, 5, 4, thick=2)
        g.line(15, 24, 25, 4, thick=2)
    g.set(5, 3)
    g.set(25, 3)
    return g


def tv_remote_grid(state):
    g = Grid(26, 11)
    g.rect(1, 1, 24, 9)
    g.rect(4, 3, 8, 6)
    g.rect(11, 3, 15, 6)
    g.rect(18, 3, 22, 6)
    if state == 'react':
        g.rect(11, 3, 15, 6, '.')
        g.line(9, 0, 11, 0)
        g.line(15, 0, 17, 0)
    return g


def tv_knob_grid(state):
    g = Grid(12, 12)
    g.disc(5, 6, 4)
    g.set(5, 6, '.')
    tips = {'calm': (5, 1), 'caps': (9, 3), 'react': (9, 8), 'sleepy': (2, 9)}
    g.line(5, 5, tips[state][0], tips[state][1], thick=1)
    return g


def build_old_tv():
    bg = PS.blank('#1b1a24')
    d = ImageDraw.Draw(bg)
    # wallpaper panel lines kept off the sticker rects
    for x in (20, 76, 240, 296):
        d.line([(x, 0), (x, 143)], fill=hexrgb('#232230'))
    # wall picture
    d.rectangle((252, 52, 300, 92), fill=hexrgb('#2a2836'))
    d.rectangle((256, 56, 296, 88), fill=hexrgb('#3a3850'))
    d.ellipse((268, 60, 284, 76), fill=hexrgb('#f2e4c0'))
    d.polygon([(256, 88), (268, 78), (280, 88)], fill=hexrgb('#2a2836'))
    # cabinet
    d.rectangle((0, 144, 319, 171), fill=hexrgb(CABINET_TV))
    d.rectangle((0, 144, 319, 147), fill=hexrgb('#6b4d34'))
    for x in range(0, 320, 44):
        d.line([(x, 148), (x, 171)], fill=hexrgb('#3d2c20'))
    # tv body
    d.rounded_rectangle((110, 56, 218, 139), radius=9, fill=hexrgb(BEIGE_TV))
    d.rounded_rectangle((111, 57, 217, 138), radius=8, outline=hexrgb('#c8ac80'))
    d.rounded_rectangle((120, 66, 206, 124), radius=6, fill=hexrgb(SCREEN_DARK))
    d.rounded_rectangle((120, 66, 206, 124), radius=6, outline=hexrgb('#8f7a56'))
    for y in range(128, 137, 4):
        d.line((122, y, 154, y), fill=hexrgb('#b89a70'))
    d.rectangle((124, 139, 140, 143), fill=hexrgb('#8a6a46'))
    d.rectangle((188, 139, 204, 143), fill=hexrgb('#8a6a46'))
    d.rectangle((120, 128, 130, 136), fill=hexrgb('#d8bc94'))
    for rect, colour in (((124, 70, 62, 44), SCREEN_DARK),
                         ((122, 30, 30, 26), WALL_TV),
                         ((56, 146, 26, 11), CABINET_TV),
                         ((190, 126, 12, 12), BEIGE_TV)):
        flat(bg, rect[0], rect[1], rect[2], rect[3], colour)

    s = PS.Scheme(
        'px6-old-tv', '老电视',
        dict(family='摸鱼松弛', tags=['老电视', '摸鱼', '雪花', '深夜'],
             story='老电视的雪花像下了一场小雨。你调着天线，鱼在屏幕里慢慢地游，'
                   '时间也跟着慢了半拍——反正那个表还要再填一遍。'),
        '工位角落那台老电视还开着，播着一条很慢的鱼。按键时屏幕冒出细碎雪花，天线跟着抖；'
        '看得入迷时它闪着雪花，睡着了就只剩暗屏和一点点静电。',
        ['#1b1a24', '#4a3628', '#e8cfa8', '#0f1c22', '#dff6ff', '#7fd8e8', '#c8b48a'],
        bg, ATTRIB)
    s.sticker('屏幕', 124, 70, tv_screen_grid('calm'), '#bfe9d8', SCREEN_DARK,
              caps=tv_screen_grid('caps'), caps_fg='#ffffff',
              react=tv_screen_grid('react'), react_fg='#dff6ff',
              sleepy=tv_screen_grid('sleepy'), sleepy_fg='#3f6068')
    s.sticker('天线', 122, 30, tv_antenna_grid('calm'), '#c8c8d8', WALL_TV,
              caps=tv_antenna_grid('caps'), caps_fg='#e0e0f0',
              react=tv_antenna_grid('react'), react_fg='#f0f0ff',
              sleepy=tv_antenna_grid('sleepy'), sleepy_fg='#8a8a9a')
    s.sticker('遥控器', 56, 146, tv_remote_grid('calm'), '#8a8a9a', CABINET_TV,
              caps_fg='#b0b0c0',
              react=tv_remote_grid('react'), react_fg='#dff6ff',
              sleepy_fg='#5a5a68')
    s.sticker('旋钮', 190, 126, tv_knob_grid('calm'), '#5a4632', BEIGE_TV,
              caps=tv_knob_grid('caps'), caps_fg='#6b5440',
              react=tv_knob_grid('react'), react_fg='#7a6048',
              sleepy=tv_knob_grid('sleepy'), sleepy_fg='#4a3828')
    s.set_effect('spark', trigger='key', spawn=(124, 32, 28, 16), count=8, size=2,
                 colors=['#dff6ff', '#ffffff', '#9ad7ff'], vx=(-140, 140),
                 vy=(-150, -50), gravity=170, life_ms=1000, edge='bounce', shape='plus')
    s.set_reaction(reactHoldMs=950, sleepyAfterMs=21000)
    s.statusInk = '#dff6ff'
    return s


# ================================================================= 8 泡泡纸
WALL_WRAP = '#1a1e2a'
DESK_WRAP = '#232838'
SHEET = '#a8c8d4'


def wrap_grid(state):
    g = Grid(72, 44)
    for r in range(4):
        for c in range(6):
            cx = 6 + c * 12
            cy = 6 + r * 11
            if state == 'calm':
                popped = False
            elif state == 'caps':
                popped = False
            elif state == 'react':
                popped = (r + c) % 2 == 0
            else:
                popped = (r * 3 + c) % 5 < 2
            if not popped:
                g.ring(cx, cy, 3)
                if state == 'caps':
                    g.set(cx - 2, cy - 2)
                else:
                    g.set(cx + 2, cy + 2)
            else:
                for k in range(6):
                    a = k * math.pi / 3
                    g.set(round(cx + math.cos(a) * 3), round(cy + math.sin(a) * 3))
                g.set(cx, cy + 1)
                g.line(cx - 4, cy + 4, cx - 2, cy + 5)
                g.line(cx + 4, cy + 4, cx + 2, cy + 5)
    return g


def wrap_finger_grid(state):
    g = Grid(15, 22)
    if state == 'sleepy':
        return g
    if state == 'caps':
        # finger lifted, ready to press
        g.rect(8, 3, 14, 12)
        g.rect(3, 5, 8, 10)
        g.disc(3, 7, 3)
        g.rect(1, 6, 3, 7, '.')
        g.disc(10, 14, 3)
    elif state == 'react':
        # pressing hard: squashed tip + impact ticks
        g.rect(7, 7, 14, 17)
        g.rect(2, 9, 7, 15)
        g.disc(2, 12, 3)
        g.line(0, 6, 2, 7)
        g.line(0, 17, 2, 16)
        g.set(0, 11)
    else:
        g.rect(8, 6, 14, 15)
        g.rect(3, 8, 8, 13)
        g.disc(3, 10, 3)
        g.rect(1, 9, 3, 10, '.')
        g.disc(10, 17, 3)
    return g


def wrap_paw_grid(state):
    g = Grid(22, 14)
    if state == 'sleepy':
        return g
    g.disc(11, 9, 5)
    for cx, cy, r in ((4, 4, 3), (11, 2, 3), (18, 4, 3)):
        g.disc(cx, cy, r)
    g.rect(8, 8, 9, 10, '.')
    g.rect(13, 8, 14, 10, '.')
    g.rect(4, 11, 5, 12, '.')
    if state == 'caps':
        g.set(0, 6)
        g.set(21, 6)
    elif state == 'react':
        g.line(0, 1, 3, 4)
        g.line(21, 1, 18, 4)
        g.set(0, 9)
        g.set(21, 9)
    return g


def wrap_label_grid(state):
    g = Grid(26, 14)
    if state == 'sleepy':
        return g
    g.text('POP', 4, 4)
    if state in ('caps', 'react'):
        g.text('!', 20, 4)
    return g


def build_bubble_wrap():
    bg = PS.blank('#1a1e2a')
    d = ImageDraw.Draw(bg)
    # cardboard delivery box on the right (static)
    d.rectangle((246, 88, 319, 171), fill=hexrgb('#6b4a32'))
    d.rectangle((246, 88, 319, 96), fill=hexrgb('#8a6444'))
    d.polygon([(246, 88), (270, 74), (319, 74), (319, 88)], fill=hexrgb('#7a5638'))
    d.line((282, 74, 282, 171), fill=hexrgb('#c9b48a'), width=3)
    d.line((252, 100, 252, 168), fill=hexrgb('#5a3c28'))
    # desk
    d.rectangle((0, 110, 319, 171), fill=hexrgb(DESK_WRAP))
    d.rectangle((0, 110, 319, 112), fill=hexrgb('#2e3444'))
    for y in (128, 146, 160, 168):
        d.line([(0, y), (130, y)], fill=hexrgb('#1c2029'))
        d.line([(156, y), (246, y)], fill=hexrgb('#1c2029'))
    # the bubble-wrap sheet (static)
    d.rounded_rectangle((86, 84, 188, 140), radius=6, fill=hexrgb(SHEET))
    d.rounded_rectangle((86, 84, 188, 140), radius=6, outline=hexrgb('#cfe4ea'))
    d.line((89, 92, 89, 132), fill=hexrgb('#c2dae2'))
    d.line((90, 135, 184, 135), fill=hexrgb('#96b4c0'))
    d.polygon([(188, 126), (188, 140), (174, 140)], fill=hexrgb(DESK_WRAP))
    for r, colour in (((94, 90, 74, 44), SHEET), ((172, 90, 14, 22), SHEET),
                      ((254, 102, 26, 14), '#6b4a32'), ((132, 142, 22, 14), DESK_WRAP)):
        flat(bg, r[0], r[1], r[2], r[3], colour)

    s = PS.Scheme(
        'px6-bubble-wrap', '泡泡纸',
        dict(family='摸鱼松弛', tags=['解压', '泡泡纸', '手痒', '办公室'],
             story='一捏一个响，捏完就回不去。你把泡泡纸铺在键盘旁边，假装只是随手一放——'
                   '但它已经替你捏碎了今天份的 KPI。'),
        '快递箱里的泡泡纸是最好的解压道具。每按一个键，就有一个泡泡「啵」地破掉，敲得越急爆得越多；'
        '手指离开后，剩下的泡泡安静地鼓在那里，等你回来继续捏。',
        ['#1a1e2a', '#232838', '#a8c8d4', '#eafaff', '#f0c8a0', '#7ad7ff', '#cfe4ea'],
        bg, ATTRIB)
    s.sticker('泡泡纸', 94, 90, wrap_grid('calm'), '#eafaff', SHEET,
              caps=wrap_grid('caps'), caps_fg='#ffffff',
              react=wrap_grid('react'), react_fg='#bfe8f2',
              sleepy=wrap_grid('sleepy'), sleepy_fg='#9ec8d4')
    s.sticker('手指', 172, 90, wrap_finger_grid('calm'), '#f0c8a0', SHEET,
              caps=wrap_finger_grid('caps'), caps_fg='#ffd9b8',
              react=wrap_finger_grid('react'), react_fg='#ffc8a0',
              sleepy=wrap_finger_grid('sleepy'))
    s.sticker('猫爪', 132, 142, wrap_paw_grid('calm'), '#f2c8a0', DESK_WRAP,
              caps=wrap_paw_grid('caps'), caps_fg='#ffd9b8',
              react=wrap_paw_grid('react'), react_fg='#ffc8a0',
              sleepy=wrap_paw_grid('sleepy'))
    s.sticker('标签', 254, 102, wrap_label_grid('calm'), '#7ad7ff', '#6b4a32',
              caps=wrap_label_grid('caps'), caps_fg='#a8ecff',
              react=wrap_label_grid('react'), react_fg='#ff8fb0',
              sleepy=wrap_label_grid('sleepy'), sleepy_fg='#5a8a9a')
    s.set_effect('bubble', trigger='key', spawn=(98, 82, 62, 22), count=6, size=3,
                 colors=['#bfeaff', '#eaffff'], vx=(-12, 12), vy=(-44, -20),
                 gravity=0, life_ms=2200, edge='wrap', shape='diamond')
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=17000)
    s.statusInk = '#eafaff'
    return s


# ------------------------------------------------------------------------ main
BUILDERS = (build_fish_tank, build_nap, build_snack, build_phone,
            build_plant, build_doodle, build_old_tv, build_bubble_wrap)


def main():
    for build in BUILDERS:
        s = build()
        d, meta = s.save()
        biggest = max(((L['w'] * L['h'], L['name'], L['w'], L['h'])
                       for L in meta['layers']), key=lambda t: t[0])
        print('%-18s layers %d  masks %4dB enc /%4dB dec  largest %s %dx%d  -> %s'
              % (meta['slug'], len(meta['layers']), meta['masks']['encodedBytes'],
                 meta['masks']['decodedBytes'], biggest[1], biggest[2], biggest[3], d))


if __name__ == '__main__':
    main()
