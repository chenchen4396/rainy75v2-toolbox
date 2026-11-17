"""Rainy75 V2 interactive pixel-scheme toolkit (schema rainy75-px/2).

A scheme is a 320x172 static background plus a handful of "sticker" rectangles whose
1-bit masks and two solid colours can change per mood frame.  The firmware paints a
sticker rectangle with its background colour and then its mask colour, so every
rectangle must be flat in the background image.  Frame 0 (calm) is baked into the
uploaded GIF; the firmware only paints frames 1..3 when that mood is active.

Frames, in firmware order:
    0 calm   - everything already in the uploaded asset
    1 caps   - CapsLock on (sticker overrides)
    2 react  - typing momentum / charging (the "happy" reaction)
    3 sleepy - idle for a while (the "rest" reaction)

Per-key particles are described by ``effect`` and drawn by the firmware from the
generated numeric defines; modes are only presets for those numbers.

Saving writes:
    background.png          flat scene (no stickers) used for the flatness check
    background.gif          uploaded asset (calm composite, two identical frames)
    masks.bin               PackBits-compressed unique masks, in unique order
    meta.json               schema, layer/frame tables, effect/pulse/reaction
    preview-idle.png        frame 0 composite (== uploaded asset)
    preview-caps.png        frame 1
    preview-react.png       frame 2
    preview-sleepy.png      frame 3
    preview-typing.png      frame 2 + particles at 800 ms after one key press

No hardware access.  SPDX-License-Identifier: MIT.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/design-gallery'
SIZE = (320, 172)
STATUS = (233, 12, 310, 28)          # status cluster; stickers must not overlap
STATUS_INK = '#ffffff'
FRAMES = ('calm', 'caps', 'react', 'sleepy')
FRAME_NAMES = ('平静', 'Caps 亮起', '互动', '待机')
MASK_RAM_BUDGET = 2560               # decoded masks live in the 4 KiB module state
ENCODED_BUDGET = 1200                # compressed masks in flash
MAX_LAYERS = 6
TRIGGERS = ('key', 'continuous', 'both')
EDGES = {'die': 0, 'wrap': 1, 'bounce': 2}
SHAPES = {'square': 0, 'plus': 1, 'x': 2, 'diamond': 3}

FONT = json.loads((ROOT / 'profiles/font.json').read_text(encoding='utf8'))['ascii']


# --------------------------------------------------------------------------- colour
def hexrgb(color):
    c = color.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rgb565(color):
    r, g, b = hexrgb(color)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def rgb565_to_rgb(v):
    return (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)


def lerp(a, b, k):
    return tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(color, k):
    """Scale a colour by k (0..1) for pulse previews."""
    return tuple(max(0, min(255, round(ch * k))) for ch in hexrgb(color))


# ----------------------------------------------------------------------------- grid
class Grid:
    """Character grid: '#' foreground, '.' background. Becomes one sticker mask."""

    def __init__(self, w, h, fill='.'):
        self.w, self.h = w, h
        self.g = [[fill] * w for _ in range(h)]

    @classmethod
    def from_ascii(cls, rows, fill='.'):
        w = max(len(r) for r in rows)
        g = cls(w, len(rows), fill)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in '. ':
                    g.g[y][x] = '#'
        return g

    def set(self, x, y, ch='#'):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        return self.g[int(y)][int(x)]

    def rect(self, x0, y0, x1, y1, ch='#', fill=True, thick=1):
        x0, x1 = sorted((int(x0), int(x1)))
        y0, y1 = sorted((int(y0), int(y1)))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if fill or (x < x0 + thick or x > x1 - thick
                            or y < y0 + thick or y > y1 - thick):
                    self.set(x, y, ch)

    def hline(self, x0, x1, y, ch='#', thick=1):
        self.rect(x0, y, x1, y + thick - 1, ch)

    def vline(self, x, y0, y1, ch='#', thick=1):
        self.rect(x, y0, x + thick - 1, y1, ch)

    def line(self, x0, y0, x1, y1, ch='#', thick=1):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err, r = dx + dy, (thick - 1) // 2
        while True:
            self.rect(x0 - r, y0 - r, x0 - r + thick - 1, y0 - r + thick - 1, ch)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, ch='#'):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            for dx in range(-half, half + 1):
                self.set(cx + dx, cy + dy, ch)

    def ring(self, cx, cy, r, ch='#'):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.set(cx - half, cy + dy, ch)
            self.set(cx + half, cy + dy, ch)
        for dx in range(-r, r + 1):
            half = int((r * r - dx * dx) ** 0.5)
            self.set(cx + dx, cy - half, ch)
            self.set(cx + dx, cy + half, ch)

    def text(self, s, x, y, scale=1, ch='#', spacing=1):
        for i, c in enumerate(s):
            glyph = FONT.get(c) or FONT.get('?')
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == '1':
                        for dy in range(scale):
                            for dx in range(scale):
                                self.set(x + (i * (5 + spacing) + gx) * scale + dx,
                                         y + gy * scale + dy, ch)
        return (len(s) * 5 + (len(s) - 1) * spacing) * scale

    def rows(self):
        return [''.join(r) for r in self.g]

    def mask(self):
        im = Image.new('1', (self.w, self.h), 0)
        px = im.load()
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != '.':
                    px[x, y] = 1
        return im

    def copy(self):
        g = Grid(self.w, self.h)
        g.g = [list(r) for r in self.g]
        return g


# ----------------------------------------------------------------------- background
def blank(color='#101820'):
    return Image.new('RGB', SIZE, hexrgb(color))


def vgrad(top, bottom, bands=14, dither=True, size=SIZE):
    """Banded vertical gradient with one dithered row per band (pixel-art sky)."""
    w, h = size
    im = Image.new('RGB', size)
    d = ImageDraw.Draw(im)
    t, b = hexrgb(top), hexrgb(bottom)
    rows = []
    for y in range(h):
        k = y / max(1, h - 1)
        rows.append(lerp(t, b, k))
    bandh = max(1, h // bands)

    def bc(y):
        return rows[min(h - 1, min(bands - 1, y // bandh) * bandh + bandh // 2)]

    for y in range(h):
        d.line([(0, y), (w, y)], fill=bc(y))
    if dither:
        for k in range(1, bands):
            y = k * bandh
            if 0 < y < h:
                c0, c1 = bc(y - 1), bc(y)
                for x in range(w):
                    d.point((x, y - 1), fill=c1 if (x + y) % 2 == 0 else c0)
    return im


def stars(im, count=40, color='#f7f0dd', seed=1, area=None, size2=6):
    """Scatter single-pixel stars; a few get a 2px cross."""
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    x0, y0, x1, y1 = area or (0, 0, im.width, im.height)
    for _ in range(count):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        d.point((x, y), fill=hexrgb(color))
        if rng.randrange(size2) == 0:
            d.point((x + 1, y), fill=hexrgb(color))
            d.point((x, y + 1), fill=hexrgb(color))


def moon(im, cx, cy, r, color='#f7f0dd', crater='#d8cfae', halo=None):
    d = ImageDraw.Draw(im)
    if halo:
        d.ellipse((cx - r * 2, cy - r * 2, cx + r * 2, cy + r * 2), fill=hexrgb(halo))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hexrgb(color))
    for dx, dy, rr in ((-r // 3, -r // 4, max(1, r // 4)), (r // 4, r // 3, max(1, r // 5)),
                       (-r // 5, r // 2, max(1, r // 6))):
        d.ellipse((cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr), fill=hexrgb(crater))
    return im


def sun(im, cx, cy, r, color='#ffd27a', halo='#ff9f5a'):
    d = ImageDraw.Draw(im)
    for i in range(3, 0, -1):
        rr = r + i * max(2, r // 3)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=hexrgb(halo))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hexrgb(color))
    return im


def hills(im, y, color='#0d0b1e', amp=18, seed=2):
    """Two overlapping pixel hill silhouettes along the bottom."""
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    for layer in range(2):
        base = y + layer * 12
        pts = [(0, im.height)]
        x = 0
        while x < im.width:
            step = rng.randrange(20, 46)
            pts.append((x + step // 2, base - rng.randrange(0, amp)))
            pts.append((min(im.width, x + step), base + rng.randrange(0, amp // 2)))
            x += step
        pts.append((im.width, im.height))
        d.polygon(pts, fill=hexrgb(color))
    return im


def floor_grid(im, y0, color='#2a1f3d', line='#3d2f55', step=16):
    d = ImageDraw.Draw(im)
    d.rectangle((0, y0, im.width - 1, im.height - 1), fill=hexrgb(color))
    for x in range(0, im.width + 1, step * 2):
        d.line([(x, y0), (x - 40, im.height)], fill=hexrgb(line))
    for y in range(y0, im.height, max(1, step // 2)):
        d.line([(0, y), (im.width, y)], fill=hexrgb(line))
    return im


def window_frame(im, x0, y0, x1, y1, frame='#f0dfe8', sill='#c9a6b8'):
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0, x1, y1), outline=hexrgb(frame), width=3)
    d.line([(x0 + (x1 - x0) // 2, y0), (x0 + (x1 - x0) // 2, y1)], fill=hexrgb(frame), width=2)
    d.line([(x0, y0 + (y1 - y0) // 2), (x1, y0 + (y1 - y0) // 2)], fill=hexrgb(frame), width=2)
    d.rectangle((x0 - 4, y1, x1 + 4, y1 + 4), fill=hexrgb(sill))
    return im


def rain(im, count=60, color='#a9c7ff', seed=3, angle=2):
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    for _ in range(count):
        x, y = rng.randrange(-10, im.width), rng.randrange(0, im.height)
        ln = rng.randrange(4, 9)
        d.line([(x, y), (x + angle, y + ln)], fill=hexrgb(color))
    return im


def snow(im, count=60, color='#eef4ff', seed=4):
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    for _ in range(count):
        x, y = rng.randrange(0, im.width), rng.randrange(0, im.height)
        d.point((x, y), fill=hexrgb(color))
        if rng.randrange(4) == 0:
            d.point((x + 1, y), fill=hexrgb(color))
    return im


def bokeh(im, count=12, color='#ffd9a0', seed=5, rmax=6, area=None):
    d, rng = ImageDraw.Draw(im), random.Random(seed)
    x0, y0, x1, y1 = area or (0, 0, im.width, im.height)
    for _ in range(count):
        r = rng.randrange(1, rmax + 1)
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        d.ellipse((x - r, y - r, x + r, y + r), fill=hexrgb(color))
    return im


def scanlines(im, every=3, color='#000000', alpha=40):
    """Cheap CRT scanline veil (drawn as a dark overlay)."""
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(0, im.height, every):
        d.line([(0, y), (im.width, y)], fill=hexrgb(color) + (alpha,))
    im.paste(ov, (0, 0), ov)
    return im


def panel(im, box, fill, outline=None, radius=4, width=1):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=radius, fill=hexrgb(fill),
                        outline=hexrgb(outline) if outline else None, width=width)
    return im


def blob(im, cx, cy, r, color, squash=1.0):
    d = ImageDraw.Draw(im)
    d.ellipse((cx - r, cy - r * squash, cx + r, cy + r * squash), fill=hexrgb(color))
    return im


def river(im, y0, y1, color='#0a0e1c', hi='#232848'):
    d = ImageDraw.Draw(im)
    d.rectangle((0, y0, im.width - 1, y1), fill=hexrgb(color))
    for y in range(y0 + 3, y1, 5):
        for x in range(0, im.width, 24):
            d.line([(x + (y * 7) % 13, y), (x + 10 + (y * 5) % 11, y)], fill=hexrgb(hi))
    return im


def glow(im, cx, cy, r, color, steps=3):
    """Concentric dithered halo; keep it cheap for 256-colour GIFs."""
    d = ImageDraw.Draw(im)
    c = hexrgb(color)
    for i in range(steps, 0, -1):
        rr = r * i // steps
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=c)
    return im


# ------------------------------------------------------------------ mask utilities
def pack_mask(image):
    w, h = image.size
    out = bytearray((w * h + 7) // 8)
    px = image.load()
    for y in range(h):
        for x in range(w):
            if px[x, y]:
                bit = y * w + x
                out[bit >> 3] |= 0x80 >> (bit & 7)
    return bytes(out)


def packbits_encode(data):
    """PackBits: c<0x80 => repeat next byte c+1 times; c>=0x80 => literal c&0x7f+1."""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        run = 1
        while i + run < n and data[i + run] == data[i] and run < 0x80:
            run += 1
        if run >= 3:
            out.append(run - 1)
            out.append(data[i])
            i += run
            continue
        start = i
        i += 1
        while i < n and (i - start) < 0x80:
            if i + 2 < n and data[i] == data[i + 1] == data[i + 2]:
                break
            i += 1
        out.append(0x80 | (i - start - 1))
        out.extend(data[start:i])
    return bytes(out)


def packbits_decode(data):
    out = bytearray()
    i = 0
    while i < len(data):
        c = data[i]
        i += 1
        if c & 0x80:
            k = (c & 0x7f) + 1
            out.extend(data[i:i + k])
            i += k
        else:
            out.extend([data[i]] * (c + 1))
            i += 1
    return bytes(out)


def _normalise(rows_or_grid):
    if isinstance(rows_or_grid, Grid):
        return rows_or_grid
    return Grid.from_ascii(rows_or_grid)


# ------------------------------------------------------------------- effect presets
EFFECT_PRESETS = {
    'none': dict(count=0, size=1, colors=['#ffffff'], vx=(0, 0), vy=(0, 0),
                 gravity=0, lifeMs=600, edge='die', shape='square'),
    'petal': dict(count=6, size=4, colors=['#ffd0e2', '#ffffff', '#ff6fa6'], vx=(-46, 46),
                  vy=(50, 85), gravity=22, lifeMs=2600, edge='die', shape='square'),
    'snow': dict(count=5, size=2, colors=['#ffffff', '#dceaff'], vx=(-18, 18),
                 vy=(22, 44), gravity=0, lifeMs=4200, edge='wrap', shape='square'),
    'rain': dict(count=7, size=1, colors=['#a9c7ff', '#dceaff'], vx=(-12, 4),
                 vy=(170, 260), gravity=0, lifeMs=900, edge='die', shape='square'),
    'spark': dict(count=9, size=2, colors=['#ffe9a8', '#ffffff'], vx=(-170, 170),
                  vy=(-190, -40), gravity=210, lifeMs=1100, edge='bounce', shape='plus'),
    'confetti': dict(count=10, size=3, colors=['#ff6f9f', '#ffd27a', '#7ad7ff', '#b6ff9a'],
                     vx=(-150, 150), vy=(-170, -30), gravity=150, lifeMs=1500,
                     edge='bounce', shape='square'),
    'bubble': dict(count=5, size=3, colors=['#bfeaff', '#e9fbff'], vx=(-10, 10),
                   vy=(-48, -24), gravity=0, lifeMs=2400, edge='wrap', shape='diamond'),
    'ember': dict(count=4, size=2, colors=['#ffb347', '#ff7a3d', '#ffe0a3'], vx=(-24, 24),
                  vy=(-56, -22), gravity=-6, lifeMs=2200, edge='die', shape='square'),
    'firefly': dict(count=3, size=2, colors=['#d6ff8a', '#fff6b0'], vx=(-26, 26),
                    vy=(-26, 26), gravity=0, lifeMs=3200, edge='wrap', shape='plus'),
    'dust': dict(count=4, size=1, colors=['#efe6ff', '#d8c9ff'], vx=(-14, 14),
                 vy=(-16, -4), gravity=-2, lifeMs=3600, edge='wrap', shape='square'),
    'note': dict(count=4, size=3, colors=['#ffd6e8', '#ffffff'], vx=(-40, 40),
                 vy=(-80, -30), gravity=30, lifeMs=2000, edge='die', shape='diamond'),
    'heart': dict(count=3, size=3, colors=['#ff7f9f', '#ffb3c7'], vx=(-30, 30),
                  vy=(-70, -30), gravity=18, lifeMs=2200, edge='die', shape='plus'),
}


def effect_preset(kind, **overrides):
    base = dict(EFFECT_PRESETS.get(kind) or EFFECT_PRESETS['none'])
    base.update(overrides)
    base['mode'] = kind
    return base


# --------------------------------------------------------------------------- scheme
class Scheme:
    def __init__(self, slug, name, emotion, description, palette, background=None,
                 attribution=None):
        assert slug.startswith('px6-'), 'v2 schemes use the px6- slug prefix'
        self.slug = slug
        self.name = name
        self.emotion = emotion
        self.description = description
        self.palette = list(palette)
        self.bg = background if background is not None else blank()
        self.attribution = attribution or (
            '原创像素图形，全部由 tools/schemes/%s.py 程序绘制' % slug.split('-')[1])
        self.layers = []
        self.effect = None
        self.pulse = None
        self.reaction = dict(reactHoldMs=900, sleepyAfterMs=25000, energyKeys=3,
                             energyWindowMs=1500, chargeUsesReact=False)
        self.statusInk = STATUS_INK
        self.key_panel = None
        self.top_bar = None

    # -- authoring ---------------------------------------------------------
    def sticker(self, name, x, y, calm, fg, bg,
                caps=None, react=None, sleepy=None,
                caps_fg=None, react_fg=None, sleepy_fg=None,
                caps_bg=None, react_bg=None, sleepy_bg=None):
        """Add one solid-colour sticker changing over the four mood frames.

        ``calm`` rows define the rectangle; frames without art inherit the calm mask.
        Use ``Grid`` for large art or ASCII rows for small icons.
        """
        masks = {}
        masks[0] = _normalise(calm)
        for idx, art in ((1, caps), (2, react), (3, sleepy)):
            masks[idx] = _normalise(art) if art is not None else masks[0].copy()
        w, h = masks[0].w, masks[0].h
        for idx in range(1, 4):
            if masks[idx].w != w or masks[idx].h != h:
                raise ValueError('%s: frame %d size differs' % (name, idx))
        if x + w > SIZE[0] or y + h > SIZE[1]:
            raise ValueError('%s: outside screen' % name)
        fgv = [fg] + [f if f is not None else fg for f in (caps_fg, react_fg, sleepy_fg)]
        bgv = [bg] + [b if b is not None else bg for b in (caps_bg, react_bg, sleepy_bg)]
        self.layers.append(dict(name=name, x=x, y=y, w=w, h=h, fg=fgv, bg=bgv, masks=masks))
        return self

    def set_effect(self, kind='none', trigger='key', spawn=None, count=None, size=None,
                   colors=None, vx=None, vy=None, gravity=None, life_ms=None,
                   edge=None, shape=None, continuous=None, energy_bonus=True):
        eff = effect_preset(kind)
        # full-frame spawn is rarely what a scheme wants; default just under the art
        eff['spawn'] = list(spawn or (8, 48, 304, 60))
        for key, val in (('count', count), ('size', size), ('colors', colors), ('vx', vx),
                         ('vy', vy), ('gravity', gravity), ('edge', edge), ('shape', shape)):
            if val is not None:
                eff[key] = val
        if life_ms is not None:
            eff['lifeMs'] = life_ms
        eff['trigger'] = trigger
        eff['continuous'] = bool(trigger in ('continuous', 'both')) if continuous is None else bool(continuous)
        eff['energyBonus'] = bool(energy_bonus)
        eff['lifeMs'] = int(eff['lifeMs'])
        self.effect = eff
        return self

    def set_pulse(self, layer, period_ms=1800, minimum=140):
        """Gently breathe one sticker's foreground colour (heartbeat / glow)."""
        self.pulse = dict(layer=layer, periodMs=int(period_ms), min=int(minimum))
        return self

    def set_motion(self, layer, frames, period_ms=240, key_period_ms=90,
                   advance_per_key=1, travel_range=0, step_per_key=0, axis='x'):
        """Animate a sticker while the user is typing.

        ``frames`` is a list of ``(Grid, dx, dy)`` tuples drawn in sequence inside the
        layer rectangle; ``travel_range`` moves the whole layer up to that many pixels
        along ``axis`` as key presses accumulate (0 = run in place).  Only frame 2
        (react) animates; calm/caps/sleepy keep the static masks.
        """
        idx = self._layer(layer)
        if len(frames) < 2 or len(frames) > 8:
            raise ValueError('%s: motion needs 2..8 frames' % layer)
        self.layers[idx]['motion'] = dict(
            frames=[(_normalise(g), int(dx), int(dy)) for g, dx, dy in frames],
            periodMs=int(period_ms), keyPeriodMs=int(key_period_ms),
            advancePerKey=int(advance_per_key), travelRange=int(travel_range),
            stepPerKey=int(step_per_key), axis=axis)
        return self

    def set_key_panel(self, x, y, w, h, scale=6, fg='#22315e', bg='#ffffff'):
        """Reserve a flat rect where the firmware draws the last pressed key."""
        self.key_panel = dict(x=int(x), y=int(y), w=int(w), h=int(h), scale=int(scale),
                              fg=fg, bg=bg)
        return self

    def set_top_bar(self, battery=True, caps=True):
        """Ask the firmware to draw the top status strip (battery left, Caps right)."""
        self.top_bar = dict(battery=bool(battery), caps=bool(caps))
        return self

    def set_reaction(self, **kw):
        self.reaction.update({k: v for k, v in kw.items() if v is not None})
        return self

    # -- derived -----------------------------------------------------------
    def _layer(self, name):
        for i, L in enumerate(self.layers):
            if L['name'] == name:
                return i
        raise KeyError(name)

    def render(self, frame=0, time_ms=None):
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        pulse = self.pulse
        for L in self.layers:
            fg = L['fg'][frame]
            if pulse and pulse['layer'] == L['name'] and time_ms is not None:
                k = _pulse_scale(time_ms, pulse['periodMs'], pulse['min'])
                fg = tuple(round(ch * k) for ch in hexrgb(fg))
                fg = '#%02x%02x%02x' % fg
            d.rectangle((L['x'], L['y'], L['x'] + L['w'] - 1, L['y'] + L['h'] - 1),
                        fill=hexrgb(L['bg'][frame]))
            mask_src = L['masks'][frame]
            mdx = mdy = 0
            mo = L.get('motion')
            if mo and frame == 2:
                mask_src = mo['frames'][0][0]
                mdx, mdy = mo['frames'][0][1], mo['frames'][0][2]
            mp = mask_src.mask().load()
            fgc = hexrgb(fg)
            for yy in range(L['h']):
                for xx in range(L['w']):
                    px, py = L['x'] + xx + mdx, L['y'] + yy + mdy
                    if mp[xx, yy] and 0 <= px < SIZE[0] and 0 <= py < SIZE[1]:
                        im.putpixel((px, py), fgc)
        return im

    def _flat_check(self):
        for L in self.layers:
            crop = self.bg.crop((L['x'], L['y'], L['x'] + L['w'], L['y'] + L['h']))
            colors = crop.getcolors(1 << 20)
            if not colors or len(colors) != 1:
                raise ValueError('%s: rect %s not flat in background (%d colours)'
                                 % (self.slug, L['name'], len(colors) if colors else 0))
            flat = colors[0][1]
            for idx in range(1, 4):
                if hexrgb(L['bg'][idx]) != flat:
                    raise ValueError('%s: %s frame %d bg %s != flat %s'
                                     % (self.slug, L['name'], idx, L['bg'][idx], flat))

    def _validate(self):
        if not 1 <= len(self.layers) <= MAX_LAYERS:
            raise ValueError('%s: %d layers (1..%d)' % (self.slug, len(self.layers), MAX_LAYERS))
        x0, y0, x1, y1 = STATUS
        if self.key_panel:
            kp = self.key_panel
            if (kp['x'] < 0 or kp['y'] < 0 or kp['x'] + kp['w'] > SIZE[0]
                    or kp['y'] + kp['h'] > SIZE[1]):
                raise ValueError('%s: keyPanel outside screen' % self.slug)
            if not 2 <= kp['scale'] <= 10:
                raise ValueError('%s: keyPanel scale' % self.slug)
            if kp['x'] < x1 and kp['x'] + kp['w'] > x0 and kp['y'] < y1 and kp['y'] + kp['h'] > y0:
                raise ValueError('%s: keyPanel overlaps the status cluster' % self.slug)
            hexrgb(kp['fg'])
            hexrgb(kp['bg'])
        if self.top_bar is not None and not (self.top_bar['battery'] or self.top_bar['caps']):
            raise ValueError('%s: empty topBar' % self.slug)
        for L in self.layers:
            if L['x'] < x1 and L['x'] + L['w'] > x0 and L['y'] < y1 and L['y'] + L['h'] > y0:
                raise ValueError('%s: %s overlaps the status cluster' % (self.slug, L['name']))
            if L['w'] > 260 or L['h'] > 120:
                raise ValueError('%s: %s too large for the mask budget' % (self.slug, L['name']))
        eff = dict(self.effect or effect_preset('none'))
        eff.setdefault('trigger', 'key')
        eff.setdefault('continuous', False)
        eff.setdefault('energyBonus', False)
        eff.setdefault('lifeMs', 600)
        eff.setdefault('spawn', [8, 48, 304, 60])
        if eff['mode'] not in EFFECT_PRESETS:
            raise ValueError('%s: unknown effect mode %r' % (self.slug, eff['mode']))
        if eff['trigger'] not in TRIGGERS:
            raise ValueError('%s: bad trigger %r' % (self.slug, eff['trigger']))
        if eff['edge'] not in EDGES or eff['shape'] not in SHAPES:
            raise ValueError('%s: bad edge/shape' % self.slug)
        if not 0 <= eff['count'] <= 12 or not 1 <= eff['size'] <= 5:
            raise ValueError('%s: bad particle count/size' % self.slug)
        if not 1 <= len(eff['colors']) <= 6:
            raise ValueError('%s: 1..6 particle colours' % self.slug)
        for ch in eff['colors']:
            hexrgb(ch)
        sx, sy, sw, sh = eff['spawn']
        if not (0 <= sx and 0 <= sy and sx + sw <= SIZE[0] and sy + sh <= SIZE[1]
                and sw > 0 and sh > 0):
            raise ValueError('%s: spawnRect off screen' % self.slug)
        if sx < x1 and sx + sw > x0 and sy < y1 and sy + sh > y0:
            raise ValueError('%s: spawnRect overlaps the status cluster' % self.slug)
        for k in ('reactHoldMs', 'sleepyAfterMs', 'energyKeys', 'energyWindowMs'):
            if not isinstance(self.reaction[k], int) or self.reaction[k] < 0:
                raise ValueError('%s: bad reaction.%s' % (self.slug, k))
        if self.pulse:
            self._layer(self.pulse['layer'])
            if not 500 <= self.pulse['periodMs'] <= 6000:
                raise ValueError('%s: pulse period' % self.slug)
            if not 60 <= self.pulse['min'] <= 240:
                raise ValueError('%s: pulse min' % self.slug)
        # unique masks -> RAM / flash budgets
        uniq, index, layer_off, layer_bytes = {}, {}, [], []
        for L in self.layers:
            offs, sizes = [], []
            for frame in range(4):
                data = pack_mask(L['masks'][frame].mask())
                key = (L['h'], L['w'], data)
                if key not in uniq:
                    uniq[key] = len(index)
                    index[key] = data
                offs.append(_mask_offset(uniq, key))
                sizes.append(len(data))
            layer_off.append(offs)
            layer_bytes.append(sizes)
        motion = []
        for L in self.layers:
            mo = L.get('motion')
            if not mo:
                motion.append(None)
                continue
            offs, sizes = [], []
            for grid, dx, dy in mo['frames']:
                if grid.w != L['w'] or grid.h != L['h']:
                    raise ValueError('%s: motion frame size differs on %s'
                                     % (self.slug, L['name']))
                data = pack_mask(grid.mask())
                key = (L['h'], L['w'], data)
                if key not in uniq:
                    uniq[key] = len(index)
                    index[key] = data
                offs.append(_mask_offset(uniq, key))
                sizes.append(len(data))
            if not 40 <= mo['periodMs'] <= 2000:
                raise ValueError('%s: motion periodMs' % self.slug)
            if not 30 <= mo['keyPeriodMs'] <= 500:
                raise ValueError('%s: motion keyPeriodMs' % self.slug)
            if not 0 <= mo['advancePerKey'] <= 4:
                raise ValueError('%s: motion advancePerKey' % self.slug)
            if mo['axis'] not in ('x', 'y'):
                raise ValueError('%s: motion axis' % self.slug)
            if mo['travelRange'] < 0:
                raise ValueError('%s: motion travelRange' % self.slug)
            lo = L['x'] if mo['axis'] == 'x' else L['y']
            hi = SIZE[0] if mo['axis'] == 'x' else SIZE[1]
            if mo['travelRange'] and lo + mo['travelRange'] + L['w'] > hi:
                mo = dict(mo, travelRange=hi - lo - L['w'])
            motion.append(dict(
                count=len(mo['frames']), periodMs=mo['periodMs'],
                keyPeriodMs=mo['keyPeriodMs'], advancePerKey=mo['advancePerKey'],
                travelRange=mo['travelRange'], stepPerKey=mo['stepPerKey'],
                axis=mo['axis'], off=offs, maskBytes=sizes,
                dx=[f[1] for f in mo['frames']], dy=[f[2] for f in mo['frames']]))
        ram = sum((L['h'] * L['w'] + 7) // 8 for L in self.layers)
        decoded_unique = sum(len(d) for d in index.values())
        encoded = sum(len(packbits_encode(d)) for d in index.values())
        if decoded_unique > MASK_RAM_BUDGET:
            raise ValueError('%s: decoded masks %d B > %d B RAM'
                             % (self.slug, decoded_unique, MASK_RAM_BUDGET))
        if encoded > ENCODED_BUDGET:
            raise ValueError('%s: encoded masks %d B > %d B flash'
                             % (self.slug, encoded, ENCODED_BUDGET))
        return dict(unique=index, order=uniq, offsets=layer_off, layerBytes=layer_bytes,
                    motion=motion, decoded=decoded_unique, encoded=encoded, ram=ram)

    # -- save --------------------------------------------------------------
    def save(self, outdir=None):
        self._flat_check()
        budget = self._validate()
        d = Path(outdir) if outdir else OUT / self.slug
        d.mkdir(parents=True, exist_ok=True)

        previews = {}
        for frame, fname in enumerate(('preview-idle.png', 'preview-caps.png',
                                       'preview-react.png', 'preview-sleepy.png')):
            im = self.render(frame)
            im.save(d / fname)
            previews[FRAMES[frame]] = fname
        # typing snapshot: react frame plus one burst of particles
        typing = self.render(2)
        eff = self.effect or effect_preset('none')
        if eff['count']:
            sim = ParticleSim(eff, seed=7)
            sim.burst()
            for _ in range(20):
                sim.step(40)
            sim.draw(typing)
        typing.save(d / 'preview-typing.png')
        previews['typing'] = 'preview-typing.png'

        # uploaded asset: calm composite, two identical frames so the player advances
        idle = self.render(0)
        self.bg.save(d / 'background.png')
        q = idle.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        q.save(d / 'background.gif', save_all=True, append_images=[q], duration=40, loop=0)

        # masks.bin: unique encoded masks in unique order
        encoded, sizes = [], []
        for key, data in sorted(budget['unique'].items(), key=lambda kv: budget['order'][kv[0]]):
            blob = packbits_encode(data)
            encoded.append(blob)
            sizes.append(len(blob))
        (d / 'masks.bin').write_bytes(b''.join(encoded))

        meta = dict(
            schema='rainy75-px/2', slug=self.slug, name=self.name,
            description=self.description, emotion=self.emotion,
            attribution=self.attribution, palette=self.palette,
            statusInk=self.statusInk, size=list(SIZE),
            frames=[dict(id=f, name=FRAME_NAMES[i]) for i, f in enumerate(FRAMES)],
            layers=[dict(name=L['name'], x=L['x'], y=L['y'], w=L['w'], h=L['h'],
                         fg=list(L['fg']), bg=list(L['bg']),
                         off=list(budget['offsets'][i]), maskBytes=list(budget['layerBytes'][i]),
                         motion=budget['motion'][i])
                    for i, L in enumerate(self.layers)],
            masks=dict(data='masks.bin', unique=len(budget['unique']),
                       decodedBytes=budget['decoded'], encodedBytes=budget['encoded'],
                       encodedSizes=sizes, ramBytes=budget['ram']),
            effect=(self.effect or effect_preset('none')),
            keyPanel=self.key_panel,
            topBar=self.top_bar,
            pulse=self.pulse,
            reaction=self.reaction,
            previews=previews,
            budgets=dict(state1Bytes=budget['ram'], decodedMaskBytes=budget['decoded'],
                         encodedMaskBytes=budget['encoded']),
            note='帧0（平静）已烘焙进上传素材；固件只在上层覆盖帧1..3，并在按键时绘制粒子。',
        )
        (d / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1) + '\n',
                                     encoding='utf8')
        return d, meta


def _mask_offset(uniq, key):
    """Byte offset of this mask inside the decoded unique-mask buffer."""
    total = 0
    for k, idx in sorted(uniq.items(), key=lambda kv: kv[1]):
        if k == key:
            return total
        total += len(k[2])
    raise KeyError(key)


def _pulse_scale(t, period_ms, minimum):
    phase = (t % period_ms) / period_ms
    tri = phase * 2 if phase < 0.5 else 2 - phase * 2
    return (minimum + (255 - minimum) * tri) / 255.0


# --------------------------------------------------------------------- particle sim
class ParticleSim:
    """Host model of the firmware particle engine (40 ms Euler steps)."""

    def __init__(self, effect, seed=1):
        self.eff = effect
        self.rng = random.Random(seed)
        self.parts = []

    def _irange(self, a, b):
        if b <= a:
            return a
        return a + self.rng.randrange(b - a + 1)

    def burst(self, extra=0):
        eff = self.eff
        n = eff['count'] + extra
        for k in range(n):
            sx, sy, sw, sh = eff['spawn']
            self.parts.append(dict(
                x=self._irange(sx, sx + sw - 1), y=self._irange(sy, sy + sh - 1),
                vx=self._irange(eff['vx'][0], eff['vx'][1]),
                vy=self._irange(eff['vy'][0], eff['vy'][1]),
                life=eff['lifeMs'], color=eff['colors'][k % len(eff['colors'])]))

    def step(self, dt):
        eff = self.eff
        alive = []
        for q in self.parts:
            if q['life'] <= dt:
                continue
            q['life'] -= dt
            q['x'] += q['vx'] * dt / 1000.0
            q['y'] += q['vy'] * dt / 1000.0
            q['vy'] += eff['gravity'] * dt / 1000.0
            if eff['edge'] == 'wrap':
                q['x'] = q['x'] % SIZE[0]
                q['y'] = q['y'] % SIZE[1]
            elif eff['edge'] == 'bounce':
                if q['x'] < 0 or q['x'] >= SIZE[0]:
                    q['vx'] = -q['vx']
                    q['x'] = max(0, min(SIZE[0] - 1, q['x']))
                if q['y'] < 0 or q['y'] >= SIZE[1]:
                    q['vy'] = -q['vy']
                    q['y'] = max(0, min(SIZE[1] - 1, q['y']))
            alive.append(q)
        self.parts = alive

    def draw(self, im):
        """Draw current particles with the firmware's shape patterns."""
        d = ImageDraw.Draw(im)
        shape, size = self.eff['shape'], int(self.eff['size'])
        for q in self.parts:
            c = hexrgb(q['color'])
            x, y = int(q['x']), int(q['y'])
            if shape == 'square':
                d.rectangle((x, y, x + size - 1, y + size - 1), fill=c)
            elif shape == 'plus':
                d.line([(x, y), (x + size - 1, y)], fill=c)
                d.line([(x, y), (x, y + size - 1)], fill=c)
                d.line([(x + size - 1, y), (x + size - 1, y + size - 1)], fill=c)
                d.line([(x, y + size - 1), (x + size - 1, y + size - 1)], fill=c)
            elif shape == 'x':
                d.line([(x, y), (x + size - 1, y + size - 1)], fill=c)
                d.line([(x + size - 1, y), (x, y + size - 1)], fill=c)
            else:  # diamond
                if size <= 2:      # even/tiny sizes would otherwise render nothing
                    d.rectangle((x, y, x + 1, y + 1), fill=c)
                    continue
                r = (size - 1) / 2.0
                for dy in range(size):
                    for dx in range(size):
                        px, py = x + dx, y + dy
                        if (0 <= px < im.width and 0 <= py < im.height
                                and abs(dx - r) + abs(dy - r) <= r + 0.25):
                            im.putpixel((px, py), c)
        return im


def load_scheme(path):
    return json.loads((Path(path) / 'meta.json').read_text(encoding='utf8'))


def decode_scheme_masks(meta, data):
    """Return the decoded unique-mask buffer for a saved scheme."""
    sizes = meta['masks'].get('encodedSizes') or []
    out, pos = b'', 0
    for size in sizes:
        out += packbits_decode(data[pos:pos + size])
        pos += size
    if pos != len(data):
        raise ValueError('masks.bin size mismatch: %d decoded, %d bytes' % (pos, len(data)))
    return out


def stamp(im, meta, decoded, frame):
    """Re-stamp a frame the way the firmware does; used by the verifier."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    for L in meta['layers']:
        d.rectangle((L['x'], L['y'], L['x'] + L['w'] - 1, L['y'] + L['h'] - 1),
                    fill=hexrgb(L['bg'][frame]))
        off = L['off'][frame]
        fg = hexrgb(L['fg'][frame])
        dx = dy = 0
        mo = L.get('motion')
        if mo and frame == 2:
            off = mo['off'][0]
            dx, dy = mo['dx'][0], mo['dy'][0]
        for yy in range(L['h']):
            for xx in range(L['w']):
                bit = yy * L['w'] + xx
                px, py = L['x'] + xx + dx, L['y'] + yy + dy
                if (0 <= px < SIZE[0] and 0 <= py < SIZE[1]
                        and decoded[off + (bit >> 3)] & (0x80 >> (bit & 7))):
                    im.putpixel((px, py), fg)
    return im


def stamp_motion(im, meta, decoded, frame, t_ms, keys):
    """Draw a frame with active motion (host model used by gallery previews)."""
    im = im.copy()
    d = ImageDraw.Draw(im)
    for L in meta['layers']:
        mo = L.get('motion')
        use = bool(mo) and frame == 2
        if not use:
            d.rectangle((L['x'], L['y'], L['x'] + L['w'] - 1, L['y'] + L['h'] - 1),
                        fill=hexrgb(L['bg'][frame]))
            off = L['off'][frame]
            fg = hexrgb(L['fg'][frame])
            for yy in range(L['h']):
                for xx in range(L['w']):
                    bit = yy * L['w'] + xx
                    if decoded[off + (bit >> 3)] & (0x80 >> (bit & 7)):
                        im.putpixel((L['x'] + xx, L['y'] + yy), fg)
            continue
        period = mo['keyPeriodMs'] if keys else mo['periodMs']
        idx = (int(t_ms // period) + keys * mo['advancePerKey']) % mo['count']
        shift = min(mo['travelRange'], keys * mo['stepPerKey'])
        ox = shift if mo['axis'] == 'x' else 0
        oy = shift if mo['axis'] == 'y' else 0
        d.rectangle((L['x'] + ox, L['y'] + oy,
                     L['x'] + ox + L['w'] - 1, L['y'] + oy + L['h'] - 1),
                    fill=hexrgb(L['bg'][2]))
        off = mo['off'][idx]
        dx, dy = mo['dx'][idx], mo['dy'][idx]
        fg = hexrgb(L['fg'][2])
        for yy in range(L['h']):
            for xx in range(L['w']):
                bit = yy * L['w'] + xx
                px, py = L['x'] + ox + xx + dx, L['y'] + oy + yy + dy
                if (0 <= px < SIZE[0] and 0 <= py < SIZE[1]
                        and decoded[off + (bit >> 3)] & (0x80 >> (bit & 7))):
                    im.putpixel((px, py), fg)
    return im


def write_typing_gif(scheme, path, seconds=3.4, fps=25):
    """Render an animated typing preview (model check, not a hardware capture)."""
    eff = scheme.effect or effect_preset('none')
    sim = ParticleSim(eff, seed=11)
    frames = []
    key_times = [0.25, 0.55, 0.85, 1.15, 1.45, 1.75]
    total = int(seconds * fps)
    key_count = 0
    for i in range(total):
        t = i / fps
        while key_times and key_times[0] <= t:
            key_times.pop(0)
            sim.burst()
            key_count += 1
        sim.step(1000 / fps)
        # mood: react while typing recently, sleepy is not part of this preview
        frame = 2 if (t < 2.6) else 0
        im = scheme.render(frame, time_ms=int(t * 1000))
        sim.draw(im)
        frames.append(im)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps),
                   loop=0, optimize=True)
    return path
