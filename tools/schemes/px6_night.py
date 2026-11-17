"""px6 night-family schemes: 深夜陪伴 (8 interactive pixel schemes).

Written for schema rainy75-px/2; family 深夜陪伴.  Every scene shares the same recipe:
deep night background, a small hero (cat / skyline / train window / stars / lamp / rain /
clock / dream cloud), four mood frames (calm, caps colour-shift, react wake-up, sleepy rest)
and a scene-tied particle effect.

Usage: .venv/Scripts/python.exe tools/schemes/px6_night.py
SPDX-License-Identifier: MIT.
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import pixel_scheme as PS  # noqa: E402
from pixel_scheme import Grid  # noqa: E402
from PIL import ImageDraw  # noqa: E402

FAMILY = '深夜陪伴'
OUT = PS.OUT


def flat(im, x, y, w, h, colour):
    ImageDraw.Draw(im).rectangle((x, y, x + w - 1, y + h - 1), fill=PS.hexrgb(colour))


def sky(w, h, top, bottom, stars_n=46, seed=1, hills_y=None, floor_y=None,
        floor='#141228', hill='#0a0a1c'):
    bg = PS.vgrad(top, bottom, bands=14)
    if stars_n:
        PS.stars(bg, stars_n, '#f7f0dd', seed=seed)
    if hills_y:
        PS.hills(bg, hills_y, hill, amp=16, seed=seed + 3)
    if floor_y:
        ImageDraw.Draw(bg).rectangle((0, floor_y, w - 1, h - 1), fill=PS.hexrgb(floor))
        ImageDraw.Draw(bg).line([(0, floor_y), (w, floor_y)], fill=PS.hexrgb('#242040'))
    return bg


def star_grid(w, h, points, seed=1):
    g = Grid(w, h)
    for x, y, r in points:
        if r <= 1:
            g.set(x, y)
        else:
            g.line(x - r, y, x + r, y)
            g.line(x, y - r, x, y + r)
            if r > 2:
                g.line(x - r + 1, y - r + 1, x + r - 1, y + r - 1)
    return g


def text_grid(s, scale=1):
    g = Grid(5 * len(s) + (len(s) - 1) * 1, 7)
    g.text(s, 0, 0, scale)
    return g


def eyes_grid(kind):
    g = Grid(18, 7)
    if kind == 'open':
        g.rect(2, 1, 4, 3); g.rect(11, 1, 13, 3)
    elif kind == 'wide':
        g.rect(2, 0, 5, 4); g.rect(10, 0, 13, 4)
        g.set(3, 1, '.'); g.set(11, 1, '.')
    elif kind == 'closed':
        g.hline(1, 5, 3); g.hline(10, 14, 3)
    else:  # sleepy half
        g.hline(2, 5, 3); g.hline(10, 13, 3)
        g.hline(3, 4, 4); g.hline(11, 12, 4)
    return g


def make(slug, name, story, desc, palette, bg, status_ink='#efe6ff'):
    return PS.Scheme(slug, name,
                     dict(family=FAMILY, tags=['安静', '陪伴', '夜'], story=story),
                     desc, palette, bg,
                     '原创像素图形，由 tools/schemes/px6_night.py 程序绘制')


# ---------------------------------------------------------------- 1 moon cat
def moon_cat():
    bg = sky(320, 172, '#0b1026', '#1d1b3e', 48, seed=2, hills_y=108, floor_y=130)
    flat(bg, 248, 32, 28, 28, '#201a45')       # moon card
    flat(bg, 118, 120, 48, 26, '#141228')      # cat patch
    flat(bg, 172, 104, 24, 18, '#141228')      # z patch
    cat = Grid(48, 26)
    cat.disc(23, 14, 10)          # head
    cat.disc(14, 7, 7)            # ear cap left
    cat.disc(30, 7, 7)            # ear cap right
    cat.rect(8, 2, 13, 9, '.')
    cat.rect(20, 2, 25, 9, '.')
    cat.disc(14, 7, 5)
    cat.disc(30, 7, 5)
    cat.rect(10, 16, 40, 25)      # body
    cat.rect(6, 22, 44, 25)       # paws base
    cat.line(38, 22, 46, 4, '#', 3)
    cat.set(22, 12, '.')
    cat.set(32, 12, '.')
    zz = Grid(24, 18); zz.text('z', 4, 2); zz.text('z', 12, 8)
    s = make('px6-moon-cat', '月下猫',
             '屋顶上只有月亮和一只猫。你敲字，它抬头看你一眼；你停下，它就缩成一团继续睡。',
             '深蓝屋顶与满月：猫背对城市坐着。按键时月边飘下星尘，敲得投入它睁眼竖尾；久不按键就闭眼趴下，飘出两个 z。',
             ['#0b1026', '#1d1b3e', '#f7f0dd', '#ffd9a0', '#8a7bd8', '#efe6ff'], bg)
    s.sticker('满月', 248, 32, moon_blank(28, 28), '#f7f0dd', '#201a45',
              caps_fg='#fff6d8', sleepy_fg='#c9c2e8')
    s.sticker('猫', 118, 120, cat, '#0e0c20', '#141228',
              caps_fg='#161232', react_fg='#1a1640', sleepy_fg='#0a0918')
    s.sticker('猫眼', 126, 126, eyes_grid('closed'), '#ffd27a', '#141228',
              caps=eyes_grid('open'), react=eyes_grid('wide'), sleepy=eyes_grid('closed'))
    s.sticker('Zzz', 172, 104, Grid(24, 18), '#c9c2e8', '#141228',
              caps=Grid(24, 18), react=Grid(24, 18), sleepy=zz)
    s.set_effect('dust', trigger='key', spawn=(238, 30, 50, 34), count=4, size=1,
                 colors=['#f7f0dd', '#c9b8ff', '#ffd9a0'], vx=(-14, 14), vy=(-12, 12),
                 gravity=0, life_ms=3200, edge='wrap')
    s.set_pulse('满月', period_ms=2800, minimum=170)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=20000)
    return s


# ---------------------------------------------------------------- 2 city night
def city_night():
    bg = sky(320, 172, '#0a0e24', '#2a1a3e', 42, seed=4, floor_y=142, floor='#15112a')
    d = ImageDraw.Draw(bg)
    for x0, w, h in ((20, 42, 70), (70, 34, 96), (112, 52, 58), (172, 40, 84),
                     (220, 60, 64), (286, 34, 92)):
        d.rectangle((x0, 140 - h, x0 + w, 140), fill=PS.hexrgb('#120f26'))
    flat(bg, 60, 78, 34, 30, '#171232')        # window cluster patch
    flat(bg, 196, 34, 34, 16, '#171232')       # shooting star patch
    flat(bg, 250, 96, 26, 26, '#171232')       # moon patch
    wins = Grid(34, 30)
    for y in range(1, 30, 6):
        for x in range(1, 34, 5):
            if (x * 7 + y * 3) % 4:
                wins.rect(x, y, x + 2, y + 3)
    wins_caps = wins.copy()
    wins_react = Grid(34, 30)
    for y in range(1, 30, 5):
        for x in range(1, 34, 4):
            wins_react.rect(x, y, x + 2, y + 2)
    star = Grid(34, 16); star.line(2, 14, 30, 3); star.line(6, 12, 12, 10); star.line(16, 8, 22, 5)
    s = make('px6-city-night', '城市夜景',
             '整座城市都睡了，只有你的窗还亮着。远处偶尔有一扇亮起的窗，像有人在陪你熬夜。',
             '紫蓝夜空下的城市剪影：亮窗、月亮与流星。按键时窗口灯光闪动，流星划过；敲得更起劲就有一整片楼亮起来，安静下来只剩零星几盏。',
             ['#0a0e24', '#2a1a3e', '#ffd27a', '#7ad7ff', '#f7f0dd', '#171232'], bg)
    s.sticker('亮窗', 60, 78, wins, '#ffd27a', '#171232',
              caps=wins_caps, caps_fg='#ffe9a8', react=wins_react, react_fg='#7ad7ff',
              sleepy=Grid(34, 30))
    s.sticker('流星', 196, 34, star, '#fff3c4', '#171232',
              caps=star, react=Grid(34, 16), sleepy=Grid(34, 16))
    s.sticker('月亮', 250, 96, moon_blank(26, 26), '#f7f0dd', '#171232',
              caps_fg='#fff6d8', sleepy=moon_blank(26, 26))
    s.set_effect('dust', trigger='key', spawn=(52, 60, 70, 70), count=4, size=1,
                 colors=['#ffd27a', '#7ad7ff', '#fff3c4'], vx=(-10, 10), vy=(-8, 8),
                 gravity=0, life_ms=2600, edge='wrap')
    s.set_pulse('亮窗', period_ms=3200, minimum=150)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=22000)
    return s


def moon_blank(w, h):
    g = Grid(w, h)
    g.disc(w // 2, h // 2, min(w, h) // 2 - 1)
    for x, y in ((w // 3, h // 3), (w - w // 3, h // 2)):
        g.set(x, y, '.')
    return g


# ---------------------------------------------------------------- 3 last train
def last_train():
    bg = sky(320, 172, '#0a0d20', '#1a1430', 26, seed=6, floor_y=124, floor='#231a34')
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, 320, 30), fill=PS.hexrgb('#141026'))
    flat(bg, 40, 46, 62, 32, '#0e1526')        # outside window
    flat(bg, 210, 108, 40, 28, '#231a34')      # seat/head patch
    flat(bg, 120, 24, 30, 10, '#141026')       # line sign
    d.rectangle((36, 42, 106, 82), outline=PS.hexrgb('#3a3150'), width=2)
    lights = Grid(62, 32)
    for x in range(2, 62, 10):
        lights.rect(x, 22, x + 3, 25)
    lights_caps = lights.copy()
    lights_react = Grid(62, 32)
    for x in range(2, 62, 15):
        lights_react.rect(x, 8, x + 26, 10)
    lights_sleep = Grid(62, 32)
    for x in range(4, 62, 18):
        lights_sleep.rect(x, 24, x + 1, 25)
    seat = Grid(40, 28)
    seat.disc(16, 12, 8)
    seat.rect(3, 8, 30, 26)
    seat.line(30, 22, 38, 10, '#', 3)
    seat_react = seat.copy()
    seat_react.rect(8, 5, 24, 7, '.')
    seat_react.disc(16, 9, 7)
    seat_sleep = seat.copy()
    seat_sleep.rect(6, 12, 34, 26, '.')
    seat_sleep.disc(20, 18, 11)
    sign = Grid(30, 10); sign.text('E', 2, 2); sign.text('N', 11, 2); sign.text('D', 20, 2)
    s = make('px6-last-train', '末班车',
             '末班车快进站了，车厢里只剩你。窗外的灯一盏盏退后，你知道到家就能睡了。',
             '深紫车厢与车窗外掠过的站台灯：末班车标志亮着。按键时窗外灯串流动、速度线拉长；靠站时灯全暗，只剩你靠着窗打盹。',
             ['#0a0d20', '#1a1430', '#ffd27a', '#7ad7ff', '#3a3150', '#efe6ff'], bg)
    s.sticker('窗外', 40, 46, lights, '#ffd27a', '#0e1526',
              caps=lights_caps, react=lights_react, sleepy=lights_sleep)
    s.sticker('乘客', 210, 108, seat, '#1a1430', '#231a34',
              caps_fg='#241a3c', react=seat_react, react_fg='#2a1f45',
              sleepy=seat_sleep, sleepy_fg='#161226')
    s.sticker('站牌', 120, 24, sign, '#7ad7ff', '#141026',
              caps_fg='#a8e6ff', react=sign, sleepy=Grid(30, 10))
    s.set_effect('dust', trigger='key', spawn=(40, 40, 62, 36), count=3, size=1,
                 colors=['#ffd27a', '#fff3c4', '#7ad7ff'], vx=(-40, -18), vy=(-6, 6),
                 gravity=0, life_ms=1400, edge='wrap')
    s.set_pulse('站牌', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=18000)
    return s


# ---------------------------------------------------------------- 4 starfield
def starfield():
    bg = PS.vgrad('#070a1c', '#171433', bands=14)
    PS.stars(bg, 90, '#f7f0dd', seed=9)
    flat(bg, 46, 48, 58, 42, '#0e0b22')        # constellation area
    flat(bg, 226, 96, 26, 26, '#0e0b22')       # big star
    flat(bg, 168, 30, 28, 28, '#0e0b22')       # moon
    const = Grid(58, 42)
    pts = [(8, 32), (18, 18), (30, 26), (40, 12), (50, 22)]
    for i, (x, y) in enumerate(pts):
        const.disc(x, y, 2)
        if i:
            const.line(pts[i - 1][0], pts[i - 1][1], x, y)
    big = star_grid(26, 26, [(13, 13, 9), (13, 13, 5)], seed=1)
    big_react = star_grid(26, 26, [(13, 13, 12), (13, 13, 7), (13, 13, 2)], seed=2)
    s = make('px6-starfield', '星空',
             '关掉房间的灯，窗外的星星就亮起来。你每敲一下，它们就连接成新的星座。',
             '深空星野：散落的星点、一轮安静的月。按键时星尘聚拢，星座连线逐条亮起，最亮的一颗开始呼吸；安静下来连线隐去，只剩月亮眨眼。',
             ['#070a1c', '#171433', '#f7f0dd', '#7ad7ff', '#ffd27a', '#c9b8ff'], bg)
    s.sticker('星座', 46, 48, Grid(58, 42), '#7ad7ff', '#0e0b22',
              caps=const, react=const, sleepy=Grid(58, 42))
    s.sticker('最亮的星', 226, 96, big, '#f7f0dd', '#0e0b22',
              caps_fg='#fff6d8', react=big_react, react_fg='#fff3c4')
    s.sticker('月亮', 168, 30, moon_blank(28, 28), '#f7f0dd', '#0e0b22',
              caps_fg='#fff6d8')
    s.set_effect('firefly', trigger='key', spawn=(40, 36, 200, 100), count=3, size=2,
                 colors=['#7ad7ff', '#c9b8ff', '#fff3c4'], vx=(-20, 20), vy=(-16, 16),
                 gravity=0, life_ms=3000, edge='wrap')
    s.set_pulse('最亮的星', period_ms=2200, minimum=140)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=20000)
    return s


# ---------------------------------------------------------------- 5 desk lamp
def desk_lamp():
    bg = sky(320, 172, '#14101e', '#2a1c2e', 16, seed=12, floor_y=112, floor='#3a2630')
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, 320, 8), fill=PS.hexrgb('#1a1424'))
    flat(bg, 228, 56, 36, 48, '#3a2630')       # lamp
    flat(bg, 70, 116, 26, 20, '#3a2630')       # cup
    flat(bg, 118, 128, 52, 20, '#3a2630')      # notebook
    flat(bg, 176, 84, 16, 12, '#2a1c2e')       # moth
    shade = Grid(32, 24)
    for i in range(7):
        shade.hline(9 - i, 22 + i, i)
    shade.hline(8, 23, 7)
    shade.rect(14, 8, 17, 23)
    glow = shade.copy()
    for i in range(6):
        glow.hline(11 - i, 20 + i, 1 + i)
        glow.hline(11 - i, 20 + i, 23 - i)
    cup = Grid(26, 20)
    cup.rect(5, 6, 20, 19)
    cup.rect(20, 9, 25, 16, '.')
    cup.hline(6, 19, 8)
    book = Grid(52, 20)
    book.rect(2, 6, 49, 18)
    for y in range(9, 17, 3):
        book.hline(6, 45, y)
    moth = Grid(16, 12)
    moth.disc(5, 5, 4); moth.disc(11, 5, 4)
    s = make('px6-desk-lamp', '深夜台灯',
             '台灯把桌面照出一小块暖黄，剩下的事都可以明天再说。',
             '深紫房间里的一盏台灯、一杯热饮和摊开的笔记。按键时灯边浮起暖色微粒，灯罩呼吸；敲得久一点有飞蛾绕灯，安静后台灯变暗、只剩月光。',
             ['#14101e', '#2a1c2e', '#ffd27a', '#ffb347', '#3a2630', '#efe6ff'], bg)
    s.sticker('灯罩', 230, 58, shade, '#ffd27a', '#3a2630',
              caps_fg='#fff0c8', react=glow, react_fg='#ffe9a8', sleepy_fg='#8a6b4a')
    s.sticker('杯子', 70, 116, cup, '#e8d8c8', '#3a2630',
              caps_fg='#fff3e0', react_fg='#ffeedd', sleepy_fg='#b8a898')
    s.sticker('笔记', 118, 128, book, '#d8c8f0', '#3a2630',
              caps_fg='#e8ddff', react_fg='#efe6ff', sleepy_fg='#8f84a8')
    s.sticker('飞蛾', 176, 84, Grid(16, 12), '#fff3c4', '#2a1c2e',
              caps=Grid(16, 12), react=moth, sleepy=Grid(16, 12))
    s.set_effect('ember', trigger='key', spawn=(226, 52, 40, 30), count=3, size=2,
                 colors=['#ffd27a', '#ffb347', '#fff3c4'], vx=(-10, 10), vy=(-30, -14),
                 gravity=-2, life_ms=2200, edge='die')
    s.set_pulse('灯罩', period_ms=2400, minimum=150)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=20000)
    return s


# ---------------------------------------------------------------- 6 rain window
def rain_window():
    bg = sky(320, 172, '#0b1124', '#22203c', 30, seed=14, floor_y=126, floor='#2a2030')
    d = ImageDraw.Draw(bg)
    d.rectangle((26, 26, 300, 116), outline=PS.hexrgb('#4a3f5a'), width=3)
    d.rectangle((30, 30, 296, 112), fill=PS.hexrgb('#101a30'))
    flat(bg, 44, 44, 56, 34, '#101a30')        # rain layer area
    flat(bg, 206, 52, 22, 18, '#101a30')       # warm light
    flat(bg, 240, 118, 34, 34, '#2a2030')      # plant
    ImageDraw.Draw(bg).rectangle((30, 30, 296, 112), outline=None)
    PS.bokeh(bg, 14, '#ffd27a', seed=6, rmax=5, area=(110, 36, 198, 104))
    rain = Grid(56, 34)
    for i in range(10):
        x = (i * 13) % 54
        rain.line(x, 2, x - 2, 30)
    rain2 = Grid(56, 34)
    for i in range(16):
        x = (i * 7) % 54
        rain2.line(x, 1, x - 3, 31)
    plant = Grid(34, 34)
    plant.rect(12, 18, 21, 33)
    plant.disc(14, 14, 7); plant.disc(21, 12, 6); plant.disc(8, 18, 5)
    s = make('px6-rain-window', '雨窗',
             '雨敲在窗上，城市化成一团团光。你不用说话，就听一会儿雨。',
             '夜雨打在玻璃上，窗外是模糊的暖色灯光和一株绿植。按键时雨丝变密、窗上流过水痕；暖和起来，窗角亮起一小块暖光；安静下来只剩雾气和漏进来的月光。',
             ['#0b1124', '#22203c', '#ffd27a', '#ffb347', '#7ad7ff', '#efe6ff'], bg)
    s.sticker('雨丝', 44, 44, rain, '#7ad7ff', '#101a30',
              caps=rain, caps_fg='#a8e6ff', react=rain2, react_fg='#cfeaff',
              sleepy=Grid(56, 34))
    s.sticker('暖窗', 206, 52, Grid(22, 18), '#ffd27a', '#101a30',
              caps=Grid(22, 18), react=Grid(22, 18), sleepy=Grid(22, 18))
    s.sticker('绿植', 240, 118, plant, '#3f8a5a', '#2a2030',
              caps_fg='#4f9a6a', react_fg='#5aa878', sleepy_fg='#2f5a42')
    s.set_effect('rain', trigger='key', spawn=(30, 30, 270, 80), count=7, size=1,
                 colors=['#a9c7ff', '#dceaff'], vx=(-10, 2), vy=(80, 120),
                 gravity=0, life_ms=1200, edge='die')
    s.set_pulse('暖窗', period_ms=2600, minimum=150)
    s.set_reaction(reactHoldMs=1000, sleepyAfterMs=22000)
    return s


# ---------------------------------------------------------------- 7 insomnia
def insomnia():
    bg = sky(320, 172, '#0a0c1c', '#181430', 34, seed=16, floor_y=132, floor='#1c1830')
    d = ImageDraw.Draw(bg)
    d.rectangle((0, 112, 130, 172), fill=PS.hexrgb('#241c34'))
    d.rectangle((0, 96, 130, 112), fill=PS.hexrgb('#2e2440'))
    d.ellipse((18, 92, 66, 118), fill=PS.hexrgb('#2e2440'))
    d.rectangle((150, 118, 300, 160), fill=PS.hexrgb('#201a32'))
    flat(bg, 172, 62, 44, 20, '#1c1830')       # clock patch
    flat(bg, 52, 74, 30, 16, '#1c1830')         # eyes patch
    flat(bg, 240, 40, 26, 14, '#1c1830')       # stars patch
    clock = Grid(40, 16)
    clock.text('03:17', 2, 4, scale=1)
    clock_react = Grid(40, 16)
    clock_react.text('04:52', 2, 4, scale=1)
    eyes_open = Grid(26, 12)
    eyes_open.rect(3, 2, 8, 7); eyes_open.rect(17, 2, 22, 7)
    eyes_open.set(5, 4, '.'); eyes_open.set(19, 4, '.')
    eyes_closed = Grid(26, 12)
    eyes_closed.hline(2, 9, 6); eyes_closed.hline(16, 23, 6)
    eyes_closed.hline(3, 8, 7); eyes_closed.hline(17, 22, 7)
    stars = Grid(26, 14)
    for x, y in ((2, 10), (8, 4), (14, 8), (20, 2), (23, 11)):
        stars.line(x - 1, y, x + 1, y); stars.line(x, y - 1, x, y + 1)
    s = make('px6-insomnia', '失眠',
             '凌晨三点十七分，你还没睡着。没关系，屏幕亮着，就当有人陪你数羊。',
             '黑暗卧室里床头柜上的时钟和一双还睁着的眼。按键时星点在床边浮现、时钟继续走；敲着敲着你终于闭上眼，星星聚成一小片梦。',
             ['#0a0c1c', '#181430', '#7ad7ff', '#ffd27a', '#efe6ff', '#241c34'], bg)
    s.sticker('时钟', 172, 62, clock, '#7ad7ff', '#1c1830',
              caps_fg='#a8e6ff', react=clock_react, react_fg='#cfeaff',
              sleepy=Grid(40, 16))
    s.sticker('眼睛', 52, 74, eyes_open, '#efe6ff', '#1c1830',
              caps=eyes_open, react=eyes_open, sleepy=eyes_closed)
    s.sticker('星点', 240, 40, Grid(26, 14), '#ffd27a', '#1c1830',
              caps=Grid(26, 14), react=stars, sleepy=Grid(26, 14))
    s.set_effect('dust', trigger='key', spawn=(44, 60, 60, 100), count=3, size=1,
                 colors=['#7ad7ff', '#c9b8ff', '#fff3c4'], vx=(-12, 12), vy=(-10, 10),
                 gravity=0, life_ms=3000, edge='wrap')
    s.set_pulse('时钟', period_ms=2000, minimum=150)
    s.set_reaction(reactHoldMs=1200, sleepyAfterMs=24000)
    return s


# ---------------------------------------------------------------- 8 dream cloud
def dream_cloud():
    bg = sky(320, 172, '#0a0e22', '#221c40', 60, seed=20)
    flat(bg, 100, 108, 60, 28, '#141230')      # cloud bed
    flat(bg, 112, 92, 28, 18, '#141230')       # sleeper
    flat(bg, 190, 56, 26, 20, '#141230')       # drift stars
    flat(bg, 250, 30, 26, 26, '#141230')       # moon
    cloud = Grid(60, 28)
    cloud.disc(14, 18, 9); cloud.disc(26, 12, 11); cloud.disc(40, 16, 10)
    cloud.rect(8, 18, 52, 27)
    sleeper = Grid(28, 18)
    sleeper.disc(9, 8, 6)
    sleeper.rect(10, 10, 26, 16)
    sleeper_react = sleeper.copy()
    sleeper_react.rect(6, 6, 14, 10, '.')
    sleeper_react.disc(9, 8, 5)
    stars = Grid(26, 20)
    for x, y in ((3, 16), (10, 8), (17, 13), (22, 4)):
        stars.line(x - 1, y, x + 1, y); stars.line(x, y - 1, x, y + 1)
    s = make('px6-dream-cloud', '梦',
             '睡着之前，你把今天放上一朵云。它会慢慢漂远，明天再还给你。',
             '紫夜里的浮云和小小的人影，月亮在云后面。按键时云边飘出星屑，云朵轻轻呼吸；敲着敲着人影躺平，星星和云一起变暗，沉进梦里。',
             ['#0a0e22', '#221c40', '#c9b8ff', '#f7f0dd', '#7ad7ff', '#141230'], bg)
    s.sticker('浮云', 100, 108, cloud, '#c9b8ff', '#141230',
              caps_fg='#d8caff', react_fg='#e2d6ff', sleepy_fg='#8a7bb8')
    s.sticker('人', 112, 92, sleeper, '#efe6ff', '#141230',
              caps_fg='#fff6ff', react=sleeper_react, react_fg='#ffffff',
              sleepy_fg='#b8aed8')
    s.sticker('星屑', 190, 56, Grid(26, 20), '#7ad7ff', '#141230',
              caps=Grid(26, 20), react=stars, sleepy=Grid(26, 20))
    s.sticker('月亮', 250, 30, moon_blank(26, 26), '#f7f0dd', '#141230',
              caps_fg='#fff6d8', sleepy=moon_blank(26, 26))
    s.set_effect('dust', trigger='key', spawn=(96, 96, 76, 36), count=4, size=1,
                 colors=['#c9b8ff', '#f7f0dd', '#7ad7ff'], vx=(-14, 14), vy=(-10, 10),
                 gravity=0, life_ms=3400, edge='wrap')
    s.set_pulse('浮云', period_ms=3000, minimum=160)
    s.set_reaction(reactHoldMs=1100, sleepyAfterMs=24000)
    return s


def main():
    for build in (moon_cat, city_night, last_train, starfield, desk_lamp,
                  rain_window, insomnia, dream_cloud):
        s = build()
        d, meta = s.save()
        print('%-22s %-10s enc %4d B / dec %4d B / layers %d'
              % (s.slug, s.name, meta['masks']['encodedBytes'],
                 meta['masks']['decodedBytes'], len(meta['layers'])))


if __name__ == '__main__':
    main()
