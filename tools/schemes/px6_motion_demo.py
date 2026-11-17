"""Interactive MOTION demo: the cat actually runs when you type.

Schema rainy75-px/2 with the new optional layer ``motion``: while the mood is REACT
(typing), the firmware cycles through sprite frames and moves the whole layer along
the travel axis; calm/caps/sleepy use normal static masks.  No particles at all.

Usage: .venv/Scripts/python.exe tools/schemes/px6_motion_demo.py
SPDX-License-Identifier: MIT.
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402
from PIL import ImageDraw  # noqa: E402

W, H = 36, 24


def cat_sit():
    g = Grid(W, H)
    g.disc(17, 15, 8)
    g.rect(10, 15, 25, 23)
    g.disc(27, 9, 6)
    g.rect(23, 3, 25, 7)
    g.rect(29, 3, 31, 7)
    g.line(9, 17, 3, 22)
    g.rect(21, 22, 24, 23)
    g.rect(13, 22, 16, 23)
    return g


def cat_alert():
    g = Grid(W, H)
    g.disc(16, 14, 8)
    g.rect(9, 14, 25, 22)
    g.disc(28, 7, 6)
    g.rect(24, 1, 26, 5)
    g.rect(30, 1, 32, 5)
    g.line(8, 12, 3, 3)
    g.rect(12, 21, 15, 23)
    g.rect(21, 21, 24, 23)
    return g


def cat_sleep():
    g = Grid(W, H)
    g.disc(18, 19, 9)
    g.disc(29, 19, 5)
    g.line(9, 16, 2, 12)
    g.disc(9, 20, 3)
    return g


def cat_run(phase):
    """Six-frame side-view run cycle with body bob and alternating legs."""
    bob = (0, -1, 0, 0, -1, 0)[phase]
    g = Grid(W, H)
    g.disc(17, 12 + bob, 8)
    g.rect(10, 12 + bob, 26, 18 + bob)
    g.disc(28, 7 + bob, 6)
    g.rect(24, 1 + bob, 26, 5 + bob)
    g.rect(30, 1 + bob, 32, 5 + bob)
    g.line(8, 10 + bob, 2, 5 + bob)
    for x, shift in ((11, 0), (15, 3), (22, 3), (26, 0)):
        step = (phase + shift) % 6
        dx = (0, 1, 2, 2, 1, 0)[step]
        g.rect(x + dx, 18 + bob, x + dx + 2, 23)
    return g


def build_cat_run():
    bg = PS.vgrad('#151024', '#2a1c30', bands=14)
    PS.stars(bg, 16, '#f7f0dd', seed=4, area=(20, 12, 300, 70), size2=5)
    d = ImageDraw.Draw(bg)
    # window with moon, higher than the running corridor
    d.rectangle((28, 16, 122, 78), outline=PS.hexrgb('#4a3f5a'), width=3)
    d.rectangle((32, 20, 118, 74), fill=PS.hexrgb('#101a30'))
    PS.moon(bg, 104, 36, 9, '#f7f0dd', '#d8cfae') if hasattr(PS, 'moon') else None
    d = ImageDraw.Draw(bg)
    # warm lamp on the right wall
    d.rectangle((270, 40, 282, 52), fill=PS.hexrgb('#ffd27a'))
    # floor: keep the whole running corridor (y 104..134) perfectly flat
    d.rectangle((0, 104, 320, 171), fill=PS.hexrgb('#3a2630'))
    d.line([(0, 104), (320, 104)], fill=PS.hexrgb('#4a3440'))
    # rug and props live below/above the corridor
    d.rectangle((30, 140, 300, 160), fill=PS.hexrgb('#4a3440'))
    d.rectangle((40, 143, 290, 157), fill=PS.hexrgb('#5a4050'))
    d.rectangle((288, 88, 316, 104), fill=PS.hexrgb('#2a1c30'))
    d.rectangle((296, 92, 308, 100), fill=PS.hexrgb('#6a4a3a'))
    s = PS.Scheme(
        'px6-cat-run', '猫猫跑酷',
        dict(family='摸鱼松弛', tags=['陪伴', '活泼', '猫'],
             story='猫本来趴在键盘边打盹。你一敲字，它突然来了精神，沿着桌边一路小跑——像是替你把这股劲儿跑出去。'),
        '深夜桌面上的橘猫：平时坐着发呆、Caps 时竖起尾巴警觉，打字时用 6 帧跑步动画沿着地板跑过去，腿和身体一起动，跑完停在边上；你停下来，它又坐回去打盹。没有粒子，只有它真的在动。',
        ['#151024', '#2a1c30', '#e8a05a', '#ffd27a', '#3a2630', '#efe6ff'],
        bg, '原创像素图形，由 tools/schemes/px6_motion_demo.py 程序绘制')
    s.sticker('橘猫', 40, 110, cat_sit(), '#e8a05a', '#3a2630',
              caps=cat_alert(), caps_fg='#f0b070',
              sleepy=cat_sleep(), sleepy_fg='#b87a48')
    s.set_motion('橘猫',
                 frames=[(cat_run(p), 0, 0) for p in range(6)],
                 period_ms=260, key_period_ms=80, advance_per_key=1,
                 travel_range=200, step_per_key=14, axis='x')
    s.set_reaction(reactHoldMs=1400, sleepyAfterMs=20000)
    return s


def main():
    s = build_cat_run()
    d, meta = s.save()
    mo = meta['layers'][0]['motion']
    print('%s -> %s  enc %d B / dec %d B  motion frames %d  travel %d px'
          % (s.slug, d, meta['masks']['encodedBytes'], meta['masks']['decodedBytes'],
             mo['count'], mo['travelRange']))


if __name__ == '__main__':
    main()
