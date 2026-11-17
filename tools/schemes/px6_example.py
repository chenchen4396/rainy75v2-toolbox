"""Reference schemes for the v2 interactive pixel toolkit (schema rainy75-px/2).

Two complete examples that scheme authors can copy from:
  px6-warm-coffee  - 治愈暖光 family, ember particles from the mug, breathing lamp
  px6-pixel-dragon - 幻想冒险 family, spark burst from the dragon's mouth

Every frame is a real mood: calm (baked into the uploaded GIF), caps (sticker swap),
react (typing momentum), sleepy (idle rest).  Run:

    .venv/Scripts/python.exe tools/schemes/px6_example.py
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-example*' --dir build/design-gallery
    .venv/Scripts/python.exe tools/verify_schemes.py --glob 'px6-warm-coffee*' --dir build/design-gallery
SPDX-License-Identifier: MIT.
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402


# --------------------------------------------------------------------- helpers
def mug_grid():
    g = Grid(30, 30)
    g.rect(4, 8, 23, 27, '#')
    g.rect(6, 10, 21, 12, '.')
    g.rect(6, 25, 21, 26, '.')
    for y in range(15, 22):
        g.set(24, y, '#')
        g.set(29, y, '#')
    g.hline(24, 29, 14)
    g.hline(24, 29, 22)
    return g


def coffee_grid():
    g = Grid(18, 4)
    g.hline(0, 17, 0)
    g.hline(0, 17, 1)
    g.set(3, 0, '.'); g.set(9, 1, '.'); g.set(14, 0, '.')
    return g


def steam_grid(kind):
    g = Grid(18, 22)
    if kind == 'heart':
        rows = ['..##...##..', '.####.####.', '.#########.', '..#######..',
                '...#####...', '....###....', '.....#.....']
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == '#':
                    g.set(x + 3, y + 8, '#')
        return g
    for i, x in enumerate((3, 8, 13)):
        top = 17 - i * 2 if kind != 'full' else 14 - i
        for y in range(top, 20):
            g.set(x + (1 if (y // 3) % 2 else 0), y, '#')
    if kind == 'full':
        for i, x in enumerate((3, 8, 13)):
            for y in range(11 + i, 20):
                g.set(x + 2, y, '#')
    return g


def cat_grid(state):
    g = Grid(52, 26)
    g.disc(24, 17, 12)
    g.disc(13, 9, 9)
    g.rect(5, 3, 9, 9, '.')       # left ear notch (empty)
    g.rect(17, 3, 21, 9, '.')
    g.disc(13, 9, 7)
    g.poly = None
    if state == 'sleep':
        g.hline(9, 13, 9)
        g.hline(16, 20, 9)
    else:
        g.set(10, 8, '.'); g.set(12, 8, '.')
        g.set(17, 8, '.'); g.set(19, 8, '.')
    g.hline(9, 22, 21, '.', thick=2)   # paws gap
    if state == 'react':
        g.rect(1, 12, 6, 14)           # tail tip up
    else:
        g.line(4, 16, 0, 20)
    return g


def lamp_grid(state):
    g = Grid(28, 40)
    g.rect(3, 0, 24, 2, '.')
    for i in range(10):
        g.hline(3 + i // 2, 24 - i // 2, 1 + i, '#')
    g.rect(13, 11, 14, 30, '#')
    g.rect(5, 30, 22, 32, '#')
    if state == 'dim':
        g.rect(7, 6, 20, 10, '.')
    if state == 'spark':
        for i in range(1, 5):
            g.set(0 + i, 6 - i, '#')
            g.set(27 - i, 6 - i, '#')
    return g


def flat(im, x, y, w, h, colour):
    """Reserve a flat rectangle: the firmware repaints sticker rects with this colour."""
    from PIL import ImageDraw
    ImageDraw.Draw(im).rectangle((x, y, x + w - 1, y + h - 1), fill=PS.hexrgb(colour))


def build_coffee():
    from PIL import ImageDraw
    bg = PS.vgrad('#241a1c', '#3a2a24', bands=14)
    PS.window_frame(bg, 22, 16, 96, 78, frame='#6b4b3a', sill='#4a332a')
    ImageDraw.Draw(bg).rectangle((25, 19, 93, 75), fill=PS.hexrgb('#1a2338'))
    PS.stars(bg, 22, '#dce8ff', seed=9, area=(26, 20, 92, 74), size2=4)
    PS.snow(bg, 26, '#eef4ff', seed=5)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 84, 320, 172), fill=PS.hexrgb('#4a332a'))
    d.rectangle((0, 84, 320, 86), fill=PS.hexrgb('#5f4233'))
    for x, y in ((0, 0), ):
        pass
    for y in (128, 148, 164):
        d.line([(0, y), (70, y)], fill=PS.hexrgb('#3d2a22'))
        d.line([(106, y), (144, y)], fill=PS.hexrgb('#3d2a22'))
        d.line([(200, y), (232, y)], fill=PS.hexrgb('#3d2a22'))
        d.line([(302, y), (319, y)], fill=PS.hexrgb('#3d2a22'))
    PS.panel(bg, (10, 116, 62, 152), '#3c2a24', '#6b4b3a', radius=2)
    for y in (122, 130, 138, 146):
        d.line([(14, y), (58, y)], fill=PS.hexrgb('#4e382c'))
    for rect in ((74, 112, 30, 30), (78, 122, 20, 5), (80, 84, 18, 28),
                 (236, 100, 28, 40), (146, 116, 52, 26)):
        flat(bg, *rect, '#4a332a')
    s = PS.Scheme(
        'px6-warm-coffee', '深夜咖啡',
        dict(family='治愈暖光', tags=['陪伴', '放松', '深夜'],
             story='加班到很晚，桌上那杯咖啡还冒着热气。小猫睡在键盘边，台灯把影子拉得很长——这一刻只需要慢慢呼吸。'),
        '暖棕色的深夜桌面：窗外落雪、台灯昏黄、咖啡冒着热气，小橘猫蜷在桌角打盹。每一次敲键，咖啡杯口飘起几点暖色微光；敲得投入时猫会抬头，久不碰键盘它就继续睡。',
        ['#241a1c', '#4a332a', '#f4e3c8', '#ffb08a', '#d8cbb8', '#ffd9a0', '#6b4b3a'],
        bg, '原创像素图形，由 tools/schemes/px6_example.py 程序绘制')
    s.sticker('咖啡杯', 74, 112, mug_grid(), '#f4e3c8', '#4a332a',
              caps_fg='#ffd9b0', react_fg='#ffe9d2', sleepy_fg='#d8cbb8')
    s.sticker('咖啡液面', 80, 122, coffee_grid(), '#6b3f2a', '#4a332a',
              caps_fg='#8a4f33', react_fg='#a05c3a', sleepy_fg='#5a3525')
    s.sticker('热气', 80, 84, steam_grid('calm'), '#f7e6cd', '#4a332a',
              caps=steam_grid('full'), caps_fg='#fff2df',
              react=steam_grid('heart'), react_fg='#ff9fb5',
              sleepy=Grid(18, 22))
    s.sticker('台灯', 236, 100, lamp_grid('on'), '#ffd9a0', '#4a332a',
              caps_fg='#fff0c8', react=lamp_grid('spark'), react_fg='#ffe28a',
              sleepy=lamp_grid('dim'), sleepy_fg='#8a6b4a')
    s.sticker('小猫', 146, 116, cat_grid('sleep'), '#e8b07a', '#4a332a',
              caps=cat_grid('open'), react=cat_grid('react'), react_fg='#ffc48f',
              sleepy=cat_grid('sleep'), sleepy_fg='#c99a6b')
    s.set_effect('ember', trigger='key', spawn=(82, 70, 20, 14), count=3, size=2,
                 colors=['#ffd9a0', '#ff9f6a', '#fff2df'], vx=(-8, 8), vy=(-34, -16),
                 gravity=-3, life_ms=2100)
    s.set_pulse('台灯', period_ms=2200, minimum=150)
    s.set_reaction(reactHoldMs=900, sleepyAfterMs=22000)
    return s


def dragon_grid(state):
    g = Grid(64, 50)
    g.disc(20, 14, 11)              # head
    g.disc(9, 12, 6)                # snout
    g.rect(8, 22, 34, 44)           # body
    g.line(34, 40, 56, 30, '#', 5)  # tail
    g.line(56, 30, 62, 22, '#', 3)
    g.rect(12, 44, 18, 49)          # legs
    g.rect(26, 44, 32, 49)
    g.rect(15, 4, 19, 10, '.')      # horn notch
    g.set(24, 10, '.')              # eye
    if state == 'sleep':
        g.hline(22, 27, 11)
        g.rect(8, 22, 34, 44, '.')
        g.disc(20, 30, 12)
        g.line(32, 38, 52, 36, '#', 5)
    if state == 'caps':
        g.line(38, 26, 62, 10, '#', 4)
        g.line(40, 24, 60, 6, '#', 2)
    if state == 'react':
        g.line(38, 26, 62, 10, '#', 4)
        g.line(40, 24, 60, 6, '#', 2)
        g.set(20, 17, '#')
        g.hline(22, 27, 16)
    return g


def flame_grid(state):
    g = Grid(22, 16)
    if state == 'none':
        return g
    scale = 1.0 if state == 'small' else 1.6
    g.disc(11, 11, int(4 * scale))
    g.line(11, 15, 11, 3, '#', 2)
    g.line(7, 9, 3, 3, '#', 2)
    g.line(15, 9, 19, 2, '#', 2)
    return g


def moon_grid(state):
    g = Grid(22, 22)
    g.disc(11, 11, 10)
    if state == 'sleep':
        for y in range(22):
            for x in range(22):
                if x + y < 12:
                    g.set(x, y, '.')
        return g
    for x, y in ((7, 7), (14, 9), (9, 15)):
        g.set(x, y, '.')
    return g


def build_dragon():
    from PIL import ImageDraw
    bg = PS.vgrad('#12102a', '#2a1f45', bands=14)
    PS.stars(bg, 52, '#f7f0dd', seed=3)
    PS.hills(bg, 92, '#0d0b1e', amp=16, seed=8)
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 108, 320, 172), fill=PS.hexrgb('#1a1533'))
    d.rectangle((0, 108, 320, 110), fill=PS.hexrgb('#241d42'))
    for y in (122, 140, 158):
        d.line([(0, y), (54, y)], fill=PS.hexrgb('#241d42'))
        d.line([(126, y), (128, y)], fill=PS.hexrgb('#241d42'))
        d.line([(254, y), (319, y)], fill=PS.hexrgb('#241d42'))
    for rect in ((250, 38, 22, 22), (58, 110, 64, 50), (104, 118, 22, 16)):
        flat(bg, *rect, '#1a1533' if rect[1] >= 108 else '#201a45')
    d.rectangle((250, 38, 271, 59), fill=PS.hexrgb('#161232'))
    s = PS.Scheme(
        'px6-pixel-dragon', '像素幼龙',
        dict(family='幻想冒险', tags=['陪伴', '勇气', '夜谈'],
             story='它还在学喷火，喷出来只是一点点星星。每次你敲键盘，它就跟着吐一口气，好像也在努力给你打气。'),
        '紫夜深谷里的小幼龙：星空、山影、脚下发光的法阵。按键时它向空中喷出一点星火；敲得越起劲，星火越密；你安静下来，它就蜷起来打盹，只剩月亮陪着你。',
        ['#12102a', '#2a1f45', '#8a5cff', '#ffcf7a', '#7ad7ff', '#f7f0dd'],
        bg, '原创像素图形，由 tools/schemes/px6_example.py 程序绘制')
    s.sticker('幼龙', 58, 110, dragon_grid('calm'), '#8a5cff', '#1a1533',
              caps=dragon_grid('caps'), caps_fg='#a878ff',
              react=dragon_grid('react'), react_fg='#b98cff',
              sleepy=dragon_grid('sleep'), sleepy_fg='#5f43a8')
    s.sticker('龙息', 104, 118, flame_grid('none'), '#ffcf7a', '#1a1533',
              caps=flame_grid('small'), caps_fg='#ffe0a0',
              react=flame_grid('big'), react_fg='#ffb347',
              sleepy=flame_grid('none'))
    s.sticker('月亮', 250, 38, moon_grid('full'), '#f7f0dd', '#161232',
              caps_fg='#fff6d8', sleepy=moon_grid('sleep'), sleepy_fg='#c9c2e8')
    s.set_effect('spark', trigger='key', spawn=(102, 114, 26, 14), count=8, size=2,
                 colors=['#ffcf7a', '#fff3c4', '#7ad7ff'], vx=(-150, 150), vy=(-170, -60),
                 gravity=180, life_ms=1000, edge='bounce', shape='plus')
    s.set_pulse('月亮', period_ms=2600, minimum=170)
    s.set_reaction(reactHoldMs=800, sleepyAfterMs=18000)
    return s


def main():
    for scheme in (build_coffee(), build_dragon()):
        d, meta = scheme.save()
        print('%s -> %s  masks %dB enc/%dB dec  layers %d' % (
            scheme.slug, d, meta['masks']['encodedBytes'],
            meta['masks']['decodedBytes'], len(meta['layers'])))


if __name__ == '__main__':
    main()
