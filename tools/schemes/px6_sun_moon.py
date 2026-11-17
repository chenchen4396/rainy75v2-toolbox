"""Two pixel schemes where CapsLock swaps the sky instead of showing a CAPS badge.

px6-sunset-moon : dusk sky -> sun (calm) / crescent moon + stars (caps), battery-only top bar.
px6-sunrain     : clear sky -> sun (calm) / rain cloud (caps), battery-only top bar.

The idea: no "CAPS" indicator; the scene itself tells lower/upper case. Both are zero-particle
stickers on flat sky plates so the uploaded calm frame stays valid.

Usage: .venv/Scripts/python.exe tools/schemes/px6_sun_moon.py
SPDX-License-Identifier: MIT.
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def disc_mask(w, h, cx, cy, r):
    g = Grid(w, h)
    for y in range(h):
        for x in range(w):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                g.set(x, y, '#')
    return g


def crescent_mask(w, h, cx, cy, r, ox, oy, cut):
    g = Grid(w, h)
    for y in range(h):
        for x in range(w):
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            cutout = (x - cx - ox) ** 2 + (y - cy - oy) ** 2 <= cut * cut
            if inside and not cutout:
                g.set(x, y, '#')
    return g


def sun_mask(w, h, r, ray):
    g = disc_mask(w, h, w // 2, h // 2, r)
    cx, cy = w // 2, h // 2
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
        for k in range(r + 2, r + ray):
            g.set(cx + dx * k, cy + dy * k, '#')
    return g


def star_mask(w, h, points):
    g = Grid(w, h)
    for x, y, r in points:
        for i in range(r):
            for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                g.set(x + sx * i, y + sy * i, '#')
    return g


def dusk_scene():
    W, H = PS.SIZE
    im = Image.new('RGB', (W, H), rgb('#3a2a4b'))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 112, W, H), fill=rgb('#1d1829'))
    # baked hills that stay clear of the flat sky plates
    d.polygon([(0, 118), (70, 108), (150, 118)], fill=rgb('#2a2036'))
    d.polygon([(150, 118), (240, 102), (320, 118)], fill=rgb('#241c30'))
    d.rectangle((0, 118, W, H), fill=rgb('#1d1829'))
    d.polygon([(0, 120), (80, 112), (170, 120)], fill=rgb('#2a2036'))
    d.polygon([(150, 120), (250, 106), (320, 120)], fill=rgb('#241c30'))
    d.rectangle((0, 120, W, 172), fill=rgb('#1d1829'))
    # small baked pier/bird silhouette
    d.rectangle((28, 116, 30, 130), fill=rgb('#141020'))
    d.point((40, 100), fill=rgb('#141020'))
    d.point((44, 102), fill=rgb('#141020'))
    d.point((36, 102), fill=rgb('#141020'))
    return im


def build_sunset_moon():
    bg = dusk_scene()
    s = PS.Scheme(
        'px6-sunset-moon', '日落·月升',
        dict(family='深夜陪伴', tags=['黄昏', '月亮', '安静'],
             story='黄昏时太阳挂在海面上；CapsLock 一开，天就黑了，月亮和星子替它值班。'),
        '用太阳/月亮互换来表示大小写：平静=落日，Caps=月夜；顶栏只留电量，不再显示 CAPS 徽标。零粒子。',
        ['#3a2a4b', '#ff9a4d', '#f3e9c8', '#f7f0dd', '#1d1829'],
        bg, '原创像素图形，由 tools/schemes/px6_sun_moon.py 程序绘制')
    sky = '#3a2a4b'
    s.sticker('日月', 216, 40, sun_mask(48, 48, 14, 6), '#ff9a4d', sky,
              caps=crescent_mask(48, 48, 25, 24, 14, -6, 4, 11), caps_fg='#f3e9c8',
              react=sun_mask(48, 48, 15, 9), react_fg='#ffd27a',
              sleepy=crescent_mask(48, 48, 25, 25, 11, -5, 3, 9), sleepy_fg='#c9c3b0')
    s.sticker('星星', 24, 20, Grid(64, 32), '#f7f0dd', sky,
              caps=star_mask(64, 32, [(8, 6, 2), (22, 14, 2), (34, 5, 1), (48, 18, 2),
                                      (58, 8, 1), (14, 24, 1), (42, 26, 1), (56, 24, 1)]),
              caps_fg='#f7f0dd',
              react=star_mask(64, 32, [(24, 12, 2), (50, 20, 1)]), react_fg='#ffe9b0',
              sleepy=Grid(64, 32), sleepy_fg='#f7f0dd')
    s.set_top_bar(battery=True, caps=False)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=22000)
    return s


def day_scene():
    W, H = PS.SIZE
    im = Image.new('RGB', (W, H), rgb('#8fd3ea'))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 118, W, H), fill=rgb('#7cc46a'))
    d.rectangle((0, 118, W, H), fill=rgb('#7cc46a'))
    d.rectangle((0, 146, W, H), fill=rgb('#69b25a'))
    # baked flowers / path
    for x, y in ((40, 132), (70, 140), (120, 136), (180, 142), (250, 132), (290, 140)):
        d.rectangle((x, y, x + 1, y + 3), fill=rgb('#4f8f44'))
        d.point((x - 1, y - 1), fill=rgb('#f2f7ff'))
        d.point((x + 2, y - 1), fill=rgb('#f2f7ff'))
    d.ellipse((46, 136, 150, 170), fill=rgb('#5aa9c9'))
    d.ellipse((60, 140, 136, 166), fill=rgb('#7cc6dd'))
    return im


def build_sunrain():
    bg = day_scene()
    s = PS.Scheme(
        'px6-sunrain', '晴·雨',
        dict(family='元气清晨', tags=['晴天', '下雨', '元气'],
             story='晴天出太阳，CapsLock 一开就下雨；不用看 CAPS 字母，抬头看天就知道大小写。'),
        '太阳 ↔ 雨云互换表示大小写：平静=晴天，Caps=雨天；顶栏只留电量。零粒子。',
        ['#8fd3ea', '#ffd166', '#5f7f9a', '#7cc46a', '#f4f9ff'],
        bg, '原创像素图形，由 tools/schemes/px6_sun_moon.py 程序绘制')
    sky = '#8fd3ea'
    s.sticker('天气', 204, 34, sun_mask(56, 48, 15, 6), '#ffd166', sky,
              caps=Grid(56, 48), caps_fg='#5f7f9a',
              react=sun_mask(56, 48, 16, 9), react_fg='#ffe08a',
              sleepy=Grid(56, 48), sleepy_fg='#cfe6f2')
    # rain cloud drawn as its own sticker so it can replace the sun while keeping the sky flat
    cloud = Grid(72, 32)
    for cx, cy, r in ((18, 20, 9), (34, 15, 12), (52, 20, 9)):
        for y in range(32):
            for x in range(72):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    cloud.set(x, y, '#')
    for x in range(6, 68, 9):
        for y in range(24, 32):
            if (y + x) % 4:
                cloud.set(x, y, '#')
    rain = cloud
    s.sticker('雨云', 198, 64, Grid(72, 32), '#5f7f9a', sky,
              caps=cloud, caps_fg='#5f7f9a',
              react=rain, react_fg='#7fb2d8',
              sleepy=Grid(72, 32), sleepy_fg='#9fc4d8')
    s.set_top_bar(battery=True, caps=False)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=22000)
    return s


def main():
    for build in (build_sunset_moon, build_sunrain):
        s = build()
        d, meta = s.save()
        print('%s -> %s  masks %d/%d B  topBar=%s'
              % (s.slug, d, meta['masks']['encodedBytes'], meta['masks']['decodedBytes'],
                 bool(meta.get('topBar'))))


if __name__ == '__main__':
    main()
