"""Pack a pixel-layer scheme into firmware headers.

Two on-disk formats are understood:

* classic pixel scheme (no ``schema`` in meta.json): 4 mask sets, uppercase only
  -> ``ui_assets.h``          (used by native_ui_pixel.c / native_ui_typing.c)
* interactive pixel scheme (``schema == "rainy75-px/2"``): 4 mood frames with a
  decoded unique-mask buffer -> ``px_assets.h`` + ``px_font.h`` (used by
  native_ui_reactive.c)

Input : scheme dir with meta.json, masks.bin, preview-*.png (or background.gif)
Output: <out>/ui_assets.h   (v1) or <out>/px_assets.h + <out>/px_font.h (v2)
        <out>/background.gif (uploaded asset for the S1 player)
"""
import io
import json
import shutil
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_V2 = 'rainy75-px/2'
FRAME_IDS = ('calm', 'caps', 'react', 'sleepy')


def _is_interactive(meta):
    """v2.0 and v2.1 (sprite/strip motion) both use the interactive packer path."""
    schema = str(meta.get('schema') or '')
    return schema == SCHEMA_V2 or schema.startswith(SCHEMA_V2 + '.')
# Status cluster geometry: icon, battery bar, battery text. The interactive scheme
# keeps this area free of stickers, so its background pixels are flat.
STATUS_REGIONS = [(233, 12, 16, 16), (264, 17, 20, 8), (287, 17, 23, 7)]
EDGE_CODES = {'die': 0, 'wrap': 1, 'bounce': 2}
SHAPE_CODES = {'square': 0, 'plus': 1, 'x': 2, 'diamond': 3}
# Status-cluster font: digits, percent, minus, blank. Order defines pxglyph().
PX_FONT_CHARS = '0123456789%- '
# Key-panel font order (v2.2): 36 alphanumerics then the base-UI punctuation, fixed so the
# firmware can index it.  Order: '0'-'9', 'A'-'Z', then the punctuation below.
KEY_PANEL_ALNUM = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
# Only what the panel can actually label: single chars are A-Z/0-9 and the "--"
# placeholder; special keys use short labels that never need punctuation.
KEY_PANEL_PUNCT = ['%', '-', '.', ',', '/', ';', '=', '[', ']', '\\', "'", '`',
                   '!', '@', '#', '$', '^', '&', '*', '(', ')', '_', '+', '{', '}',
                   '|', ':', '"', '<', '>', '?', '~']
# v2.2 fixed top-bar layout agreed with the firmware: battery shell + caps badge.
TOPBAR_BATTERY_RECT = (14, 13, 28, 11)
TOPBAR_CAPS_RECT = (252, 10, 60, 17)
KEY_PANEL_CHARS = KEY_PANEL_ALNUM + ''.join(KEY_PANEL_PUNCT)
FX_NONE = dict(count=0, size=1, colors=['#ffffff'], vx=(0, 0), vy=(0, 0), gravity=0,
               lifeMs=600, edge='die', shape='square', spawn=(8, 48, 304, 60),
               trigger='key', continuous=False, energyBonus=False)


def rgb565(hex_color):
    c = hex_color.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


# ------------------------------------------------------------------------ classic
def _pack_v1(scheme, out, meta):
    """Original pixel scheme: upload lowercase composite, overlay uppercase masks."""
    masks = (scheme / 'masks.bin').read_bytes()
    layers = meta['layers']

    # masks.bin layout: state0 layers in order, then state1 layers in order.
    # Only state 1 has to live in firmware flash: the uploaded asset already contains the
    # lowercase artwork, so the firmware just overlays the uppercase stickers.
    sizes = [(L['w'] * L['h'] + 7) // 8 for L in layers]
    state0 = sum(sizes)
    if len(masks) != state0 * 2:
        raise SystemExit(f'masks.bin size {len(masks)} != expected {state0 * 2}')
    state1 = masks[state0:]
    # trim every sticker to the bounding box of its set bits: the rectangle shrinks, the
    # rendered result is identical (the background under the rect is a flat colour).
    trimmed = []
    off = 0
    for L, size in zip(layers, sizes):
        blob = state1[off:off + size]
        off += size
        w, h = L['w'], L['h']
        x0, y0, x1, y1 = w, h, -1, -1
        for bit in range(w * h):
            if blob[bit >> 3] & (0x80 >> (bit & 7)):
                bx, by = bit % w, bit // w
                if bx < x0: x0 = bx
                if by < y0: y0 = by
                if bx > x1: x1 = bx
                if by > y1: y1 = by
        if x1 < 0:
            continue  # empty sticker: drop it
        nw, nh = x1 - x0 + 1, y1 - y0 + 1
        rows_px = []
        for yy in range(nh):
            row = 0
            for xx in range(nw):
                bit = (y0 + yy) * w + (x0 + xx)
                if blob[bit >> 3] & (0x80 >> (bit & 7)):
                    row |= 0x80 >> xx
            rows_px.append(row)
        packed = bytearray((nw * nh + 7) // 8)
        for yy in range(nh):
            for xx in range(nw):
                if rows_px[yy] & (0x80 >> xx):
                    bit = yy * nw + xx
                    packed[bit >> 3] |= 0x80 >> (bit & 7)
        trimmed.append(dict(x=L['x'] + x0, y=L['y'] + y0, w=nw, h=nh,
                            fg0=L['fg0'], bg0=L['bg0'], fg1=L['fg1'], bg1=L['bg1'],
                            blob=bytes(packed)))
    rows = []
    off1 = 0
    for T in trimmed:
        rows.append((T, 0, off1))
        off1 += len(T['blob'])
    total = off1
    if total > 1750:
        raise SystemExit(f'uppercase mask budget exceeded: {total} > 1750')

    # The uploaded asset is the LOWERCASE composite: preview-normal already contains the
    # background plus the lowercase stickers, so the firmware only overlays state 1.
    bg_src = scheme / 'preview-idle.png'
    if not bg_src.exists():
        bg_src = scheme / 'preview-normal.png'
    if not bg_src.exists():
        raise SystemExit('scheme has no preview-idle.png / preview-normal.png')
    bg = Image.open(bg_src).convert('RGB').resize((320, 172))
    q = bg.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    animated = scheme / 'background.gif'
    nframes = 0
    if animated.exists():
        try:
            nframes = getattr(Image.open(animated), 'n_frames', 1)
        except Exception:
            nframes = 0
    if nframes > 1:
        # keep the character animation frames as authored
        shutil.copy2(animated, out / 'background.gif')
    else:
        # two identical frames: a single-frame GIF may refuse to advance
        q.save(out / 'background.gif', save_all=True, append_images=[q], duration=40, loop=0)

    # status cluster colours: ink from meta, bg sampled from the background image
    ink = meta.get('statusInk') or '#ffffff'
    bg_colors = [bg.getpixel((x + w // 2, y + h // 2)) for (x, y, w, h) in STATUS_REGIONS]

    from assets import ICONS
    lines = ['/* SPDX-License-Identifier: MIT; generated from a pixel scheme. */',
             '#define UI_IDLE_MS 0u', '#define UI_USB_RAW 1', '#define UI_RF_RAW 0',
             f'#define PX_SCHEME "{meta.get("slug", "")}"',
             '#define PX_LAYER_COUNT %du' % len(layers),
             'typedef struct {u16 x,y,w,h,fg0,bg0,fg1,bg1;u16 off0,off1;} PxLayer;',
             'static const PxLayer px_layers[]={']
    for (L, o0, o1) in rows:
        lines.append(' {%d,%d,%d,%d,0x%04x,0x%04x,0x%04x,0x%04x,%d,%d},' % (
            L['x'], L['y'], L['w'], L['h'],
            rgb565(L['fg0']), rgb565(L['bg0']), rgb565(L['fg1']), rgb565(L['bg1']), o0, o1))
    lines.append('};')
    lines.append('#define PX_MASK_BYTES %du' % total)
    allbits = b''.join(T['blob'] for T in trimmed)
    lines.append('static const unsigned char px_masks[]={')
    for i in range(0, len(allbits), 24):
        lines.append(' ' + ','.join(str(b) for b in allbits[i:i + 24]) + ',')
    lines.append('};')
    lines.append('#define PX_STATUS_INK 0x%04xu' % rgb565(ink))
    lines.append('static const u16 px_status_bg[3]={%s};' % ','.join('0x%04x' % rgb565('#%02x%02x%02x' % c) for c in bg_colors))
    lines.append('#define PX_STATUS_MASK_BYTES 73u')
    frz = meta.get('idleFreeze')
    if isinstance(frz, (list, tuple)) and len(frz) >= 2:
        fx, fy = int(frz[0]), int(frz[1])
        try:
            gif0 = Image.open(out / 'background.gif').convert('RGB')
            pix = gif0.getpixel((fx, fy))
        except Exception:
            pix = bg.getpixel((fx, fy))
        lines.append('#define IDLE_FREEZE_X %du' % fx)
        lines.append('#define IDLE_FREEZE_Y %du' % fy)
        lines.append('#define IDLE_PIXEL 0x%04xu' % rgb565('#%02x%02x%02x' % pix))
    else:
        lines.append('#define IDLE_FREEZE_X 0xffffu')
        lines.append('#define IDLE_FREEZE_Y 0u')
        lines.append('#define IDLE_PIXEL 0u')
    anim = meta.get('animation') or {}
    parts = anim.get('particles') or {}
    sr = parts.get('spawnRect') or [0, 0, 320, 172]
    cols = parts.get('colors') or ['#ffffff']
    lines.append('#define ANIM_KIND "%s"' % anim.get('kind', 'particles'))
    lines.append('#define ANIM_COUNT %du' % int(parts.get('count', 0)))
    lines.append('#define ANIM_SIZE %du' % int(parts.get('size', 2)))
    lines.append('#define ANIM_SPAWN_X %du' % int(sr[0]))
    lines.append('#define ANIM_SPAWN_Y %du' % int(sr[1]))
    lines.append('#define ANIM_SPAWN_W %du' % int(sr[2]))
    lines.append('#define ANIM_SPAWN_H %du' % int(sr[3]))
    vx = parts.get('vx') or [0, 0]; vy = parts.get('vy') or [0, 0]
    lines.append('#define ANIM_VX_MIN %d' % int(vx[0]))
    lines.append('#define ANIM_VX_MAX %d' % int(vx[1]))
    lines.append('#define ANIM_VY_MIN %d' % int(vy[0]))
    lines.append('#define ANIM_VY_MAX %d' % int(vy[1]))
    lines.append('#define ANIM_GRAVITY %d' % int(parts.get('gravity', 0)))
    lines.append('#define ANIM_LIFE_MS %du' % int(parts.get('lifeMs', 700)))
    lines.append('#define ANIM_COLORS %du' % len(cols))
    lines.append('static const u16 anim_colors[%d]={%s};' % (len(cols), ','.join('0x%04x' % rgb565(c) for c in cols)))
    lines.append('static const u16 connection_icons[3][16]={')
    for row in ICONS:
        lines.append(' {' + ','.join(str(v) for v in row) + '},')
    lines.append('};')
    (out / 'ui_assets.h').write_text('\n'.join(lines) + '\n', encoding='utf8')
    return dict(scheme=meta.get('slug'), layers=len(layers), maskBytes=total, ink=ink)


# -------------------------------------------------------------------- interactive
def _gif_frame_span(data):
    """Locate the single image (plus its graphic-control extension) in a GIF byte string.

    Returns (frame_start, trailer_offset). Pillow >= 11 drops byte-identical appended
    frames, so the interactive asset duplicates the encoded frame block itself.
    """
    if data[:6] not in (b'GIF87a', b'GIF89a'):
        raise SystemExit('Pillow produced an unexpected GIF header')
    pos = 13
    screen_flags = data[10]
    if screen_flags & 0x80:
        pos += 3 << ((screen_flags & 7) + 1)          # 3 * 2**(N+1) global colour table
    frame_start = None
    while pos < len(data):
        tag = data[pos]
        if tag == 0x3B:                               # trailer
            if frame_start is None:
                raise SystemExit('Pillow produced a GIF without an image frame')
            return frame_start, pos
        if tag == 0x21:                               # extension block
            label = data[pos + 1]
            if frame_start is None and label == 0xF9:  # graphic control extension
                frame_start = pos
            pos += 2
            if label == 0xF9:
                pos += 1 + data[pos] + 1              # fixed-size block + terminator
            else:
                pos += 1 + data[pos]                  # app/comment/text header block
                while data[pos]:
                    pos += 1 + data[pos]
                pos += 1
        elif tag == 0x2C:                             # image descriptor
            if frame_start is None:
                frame_start = pos
            pos += 10
            if data[pos - 1] & 0x80:                  # local colour table
                pos += 3 << ((data[pos - 1] & 7) + 1)
            pos += 1                                  # LZW minimum code size
            while data[pos]:
                pos += 1 + data[pos]
            pos += 1
        else:
            raise SystemExit('Pillow produced an unexpected GIF block 0x%02x' % tag)
    raise SystemExit('Pillow produced a truncated GIF')


def _save_gif_two_identical_frames(image, path, duration_ms=40):
    """Write a 256-colour GIF with two visually identical frames of ``duration_ms``.

    The uploaded asset must keep the player advancing; a one-frame GIF can stall it.
    """
    buf = io.BytesIO()
    image.save(buf, format='GIF', duration=duration_ms, loop=0)
    data = buf.getvalue()
    start, trailer = _gif_frame_span(data)
    path.write_bytes(data[:trailer] + data[start:trailer] + b'\x3b')
    with Image.open(path) as check:
        if getattr(check, 'n_frames', 1) != 2:
            raise SystemExit('generated background.gif is not two frames')
        pixels = []
        for i in range(2):
            check.seek(i)
            pixels.append(check.convert('RGB').tobytes())
            delay = check.info.get('duration')
            if delay is not None and delay != duration_ms:
                raise SystemExit('background.gif frame %d duration %r != %d'
                                 % (i, delay, duration_ms))
        if pixels[0] != pixels[1]:
            raise SystemExit('generated background.gif frames differ')


def _font_rows(chars):
    """5x7 rows for ``chars``, straight from profiles/font.json."""
    ascii_font = json.loads((ROOT / 'profiles/font.json').read_text(encoding='utf8'))['ascii']
    rows = []
    for ch in chars:
        glyph = ascii_font.get(ch)
        if glyph is None or len(glyph) != 7 or any(len(r) != 5 for r in glyph):
            raise SystemExit(f'profiles/font.json has no usable 5x7 glyph for {ch!r}')
        rows.append([int(r, 2) for r in glyph])
    return rows


def _px_font_glyphs():
    return _font_rows(PX_FONT_CHARS)


def _c_string_literal(text):
    """C string literal for printable ASCII (escapes backslash and double quote)."""
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def _px_font_header():
    """Status-cluster font header (also used by the top-bar percent text).

    Always emitted: with a top bar the firmware still renders the battery percentage
    with px_font/pxglyph, and without a top bar the default status cluster uses them.
    """
    digits = ''.join(str(i) for i in range(10))
    pct = digits.index('9') + 1                    # 10
    minus = PX_FONT_CHARS.index('-')               # 11
    space = PX_FONT_CHARS.index(' ')               # 12
    lines = ['/* SPDX-License-Identifier: MIT; generated from profiles/font.json. */',
             '/* Status-cluster font: 5x7 glyphs, digit/%/-/space order. */',
             'static const unsigned char px_font[][7]={']
    for glyph in _px_font_glyphs():
        lines.append(' {' + ','.join(str(v) for v in glyph) + '},')
    lines.append('};')
    lines.append('static unsigned pxglyph(unsigned c){')
    lines.append(" if(c>='0'&&c<='9')return c-'0';")
    lines.append(" if(c=='%%')return %d;" % pct)
    lines.append(" if(c=='-')return %d;" % minus)
    lines.append(' return %d;' % space)
    lines.append('}')
    return '\n'.join(lines) + '\n'


def _v2_effect(meta):
    eff = dict(FX_NONE)
    eff.update(meta.get('effect') or {})
    return eff


def _v2_motion_tables(slug, layers, decoded):
    """Flatten per-layer motion metadata into the firmware tables.

    Each motion frame is a full layer-sized unique mask that pixel_scheme already appended
    to masks.bin; ``off`` entries are absolute byte offsets into the decoded buffer (the
    packer never recomputes them).  Returns (motions, layer_index, maskoff, dx, dy), where
    ``layer_index`` holds 0xffff for static layers and ``firstOff`` is an index into the
    three flattened per-frame arrays.
    """
    rows, layer_index = [], [0xffff] * len(layers)
    for i, L in enumerate(layers):
        mo = L.get('motion')
        if not mo:
            continue
        count = int(mo.get('count', 0))
        offs = [int(v) for v in (mo.get('off') or [])]
        sizes = [int(v) for v in (mo.get('maskBytes') or [])]
        dxs = [int(v) for v in (mo.get('dx') or [])]
        dys = [int(v) for v in (mo.get('dy') or [])]
        if count < 2 or len(offs) != count or len(sizes) != count:
            raise SystemExit('%s: layer %s motion table malformed (count %d, %d offsets, '
                             '%d sizes)' % (slug, L['name'], count, len(offs), len(sizes)))
        if len(dxs) != count or len(dys) != count:
            raise SystemExit('%s: layer %s motion needs %d dx/dy values, got %d/%d'
                             % (slug, L['name'], count, len(dxs), len(dys)))
        for off, size in zip(offs, sizes):
            if off < 0 or off + size > len(decoded):
                raise SystemExit('%s: layer %s motion mask escapes the decoded buffer'
                                 % (slug, L['name']))
        axis = mo.get('axis', 'x')
        if axis not in ('x', 'y'):
            raise SystemExit('%s: layer %s motion axis %r is not x/y'
                             % (slug, L['name'], axis))
        layer_index[i] = len(rows)
        rows.append(dict(name=L['name'], count=count,
                         periodMs=int(mo.get('periodMs', 240)),
                         keyPeriodMs=int(mo.get('keyPeriodMs', 90)),
                         advancePerKey=int(mo.get('advancePerKey', 1)),
                         travelRange=int(mo.get('travelRange', 0)),
                         stepPerKey=int(mo.get('stepPerKey', 0)),
                         axis=0 if axis == 'x' else 1,
                         off=offs, dx=dxs, dy=dys))
    motions, flat_off, flat_dx, flat_dy = [], [], [], []
    for row in rows:
        row = dict(row, firstOff=len(flat_off))
        flat_off += row.pop('off')
        flat_dx += row.pop('dx')
        flat_dy += row.pop('dy')
        motions.append(row)
    return motions, layer_index, flat_off, flat_dx, flat_dy


def _v2_flat_upload(scheme, bg_src, layers, hexrgb):
    """Upload image for a motion scheme: the flat scene, with every sticker rect flat.

    The firmware draws each layer's static mask for every mood frame (calm included) and
    the moving sprite for react, so baking any layer art into the upload would leave a
    ghost at the home position once the sprite travels.  ``background.png`` is exactly
    the flat scene; if it is missing, rebuild it by clearing every layer rectangle in the
    calm preview.
    """
    from PIL import ImageDraw
    base = scheme / 'background.png'
    if base.exists():
        return Image.open(base).convert('RGB').resize((320, 172))
    img = Image.open(bg_src).convert('RGB').resize((320, 172))
    dr = ImageDraw.Draw(img)
    for L in layers:
        x, y, w, h = int(L['x']), int(L['y']), int(L['w']), int(L['h'])
        dr.rectangle((x, y, x + w - 1, y + h - 1), fill=hexrgb(L['bg'][0]))
    return img


def _v2_key_panel(slug, meta):
    """Validate the optional v2.2 key-panel rectangle and return its packed values."""
    kp = meta.get('keyPanel')
    if not kp:
        return None
    try:
        x, y, w, h = (int(kp[k]) for k in ('x', 'y', 'w', 'h'))
        scale = int(kp.get('scale', 1))
        fg = rgb565(kp['fg'])
        bg = rgb565(kp['bg'])
    except (KeyError, TypeError, ValueError, AttributeError):
        raise SystemExit('%s: keyPanel needs integer x/y/w/h/scale and "#rrggbb" fg/bg'
                         % slug)
    if w <= 0 or h <= 0 or scale < 1:
        raise SystemExit('%s: keyPanel w/h must be positive and scale >= 1' % slug)
    if x < 0 or y < 0 or x + w > 320 or y + h > 172:
        raise SystemExit('%s: keyPanel (%d,%d,%d,%d) leaves the 320x172 screen'
                         % (slug, x, y, w, h))
    sx, sy, sw, sh = 233, 12, 310 - 233, 28 - 12
    if x < sx + sw and x + w > sx and y < sy + sh and y + h > sy:
        raise SystemExit('%s: keyPanel overlaps the status cluster 233,12-310,28'
                         % slug)
    if w < 5 * scale or h < 7 * scale:
        raise SystemExit('%s: keyPanel %dx%d too small for one 5x7 glyph at scale %d'
                         % (slug, w, h, scale))
    return dict(x=x, y=y, w=w, h=h, scale=scale, fg=fg, bg=bg,
                glyphs=len(KEY_PANEL_CHARS))


def _validate_key_panel_table():
    """Self-check the emitted glyph order against pxkey_index's hard-coded mapping.

    Guards labels (e.g. '/', '--', 'F1') against a future edit reordering or duplicating
    a punctuation character: indices must be exactly digits 0-9, A-Z 10-35, punctuation
    36-66 in the documented order, with every glyph used once.
    """
    punct = ''.join(KEY_PANEL_PUNCT)
    if len(punct) != len(KEY_PANEL_PUNCT) or len(set(punct)) != len(KEY_PANEL_PUNCT):
        raise SystemExit('internal: key-panel punctuation must be unique')
    if len(KEY_PANEL_CHARS) != 36 + len(KEY_PANEL_PUNCT) or len(set(KEY_PANEL_CHARS)) != 36 + len(KEY_PANEL_PUNCT):
        raise SystemExit('internal: key-panel glyph order must list alnum + punctuation')
    for ch in KEY_PANEL_PUNCT:
        if ch in KEY_PANEL_ALNUM:
            raise SystemExit('internal: key-panel punctuation overlaps alphanumerics')
    indices = set()
    for i, ch in enumerate(KEY_PANEL_CHARS):
        if ch.isdigit():
            expected = int(ch)                      # '0'..'9' -> 0..9
        elif 'A' <= ch <= 'Z':
            expected = 10 + ord(ch) - ord('A')      # 'A'..'Z' -> 10..35
        else:
            expected = 36 + KEY_PANEL_PUNCT.index(ch)
        if expected != i or expected in indices:
            raise SystemExit('internal: key-panel glyph %r expected index %d, got %d'
                             % (ch, expected, i))
        indices.add(expected)
    if indices != set(range(len(KEY_PANEL_CHARS))):
        raise SystemExit('internal: key-panel glyph indices are not 0..66')
    # The emitted C string must round-trip to the exact punctuation order.
    literal = _c_string_literal(punct)
    unescaped = literal[1:-1].replace('\\\\', '\\').replace('\\"', '"')
    if unescaped != punct:
        raise SystemExit('internal: key-panel punctuation literal does not round-trip')


def _v2_topbar(slug, meta, key_panel):
    """Validate the optional v2.2 top bar and return its element flags.

    The top bar reuses firmware-fixed geometry (battery shell 14,13,28,11 + tip + percent
    text; caps badge 252,10,60,17 + CAPS + chevron); the packer only enables it and
    validates that its two fixed rectangles fit and do not hit the key-panel rectangle.
    """
    tb = meta.get('topBar')
    if not tb:
        return None
    if not isinstance(tb, dict):
        raise SystemExit('%s: topBar must be an object like {"battery":true,"caps":true}'
                         % slug)
    for name, (x, y, w, h) in (('battery', TOPBAR_BATTERY_RECT),
                               ('caps', TOPBAR_CAPS_RECT)):
        if x < 0 or y < 0 or x + w > 320 or y + h > 172:
            raise SystemExit('%s: topBar %s rect (%d,%d,%d,%d) leaves the 320x172 screen'
                             % (slug, name, x, y, w, h))
        if key_panel and (x < key_panel['x'] + key_panel['w'] and x + w > key_panel['x']
                          and y < key_panel['y'] + key_panel['h']
                          and y + h > key_panel['y']):
            raise SystemExit('%s: topBar %s rect collides with the key panel'
                             % (slug, name))
    return dict(battery=bool(tb.get('battery', True)),
                caps=bool(tb.get('caps', True)))


def _v2_topbar_header(topbar):
    lines = ['#define PX_TOPBAR 1',
             '#define PX_TOPBAR_BATTERY %d' % (1 if topbar['battery'] else 0),
             '#define PX_TOPBAR_CAPS %d' % (1 if topbar['caps'] else 0)]
    return lines


def _v2_keypanel_header(kp):
    """px_assets.h lines for an enabled key panel (empty list when disabled)."""
    _validate_key_panel_table()
    lines = ['#define PX_KEYPANEL 1',
             '#define PX_KEY_X %d' % kp['x'],
             '#define PX_KEY_Y %d' % kp['y'],
             '#define PX_KEY_W %d' % kp['w'],
             '#define PX_KEY_H %d' % kp['h'],
             '#define PX_KEY_SCALE %d' % kp['scale'],
             '#define PX_KEY_FG 0x%04xu' % kp['fg'],
             '#define PX_KEY_BG 0x%04xu' % kp['bg'],
             '#define PX_KEY_GLYPH_COUNT %d' % len(KEY_PANEL_CHARS),
             'static const unsigned char px_key_font[][7]={']
    for glyph in _font_rows(KEY_PANEL_CHARS):
        lines.append(' {' + ','.join(str(v) for v in glyph) + '},')
    lines.append('};')
    lines.append('static unsigned pxkey_index(unsigned char c){')
    # Compact lookup: a 31-byte punctuation string plus linear scan costs far less flash
    # than a 31-case switch (no jump table), which keeps the full glyph set in budget.
    lines.append(' static const char p[]=%s;' % _c_string_literal(''.join(KEY_PANEL_PUNCT)))
    lines.append(' unsigned i;')
    lines.append(" if(c>='0'&&c<='9')return (unsigned)(c-'0');")
    lines.append(" if(c>='A'&&c<='Z')return (unsigned)(10u+(unsigned)(c-'A'));")
    lines.append(' for(i=0;p[i];i++)if((unsigned char)p[i]==c)return 36u+i;')
    # Unknown characters (space included) use the last glyph ('?'); never out of range.
    lines.append(' return (unsigned)(PX_KEY_GLYPH_COUNT-1u);')
    lines.append('}')
    return lines


def _pack_v2(scheme, out, meta):
    from pixel_scheme import decode_scheme_masks, rgb565 as px_rgb565, hexrgb

    slug = meta.get('slug') or scheme.name
    layers = meta.get('layers') or []
    if not 1 <= len(layers) <= 6:
        raise SystemExit(f'{slug}: expected 1..6 layers, got {len(layers)}')
    mdesc = meta.get('masks') or {}
    rle = (scheme / mdesc.get('data', 'masks.bin')).read_bytes()
    decoded = decode_scheme_masks(meta, rle)
    if len(decoded) != int(mdesc.get('decodedBytes', len(decoded))):
        raise SystemExit(f'{slug}: decoded masks {len(decoded)} B != meta decodedBytes '
                         f'{mdesc.get("decodedBytes")}')
    for L in layers:
        for frame in range(4):
            if L['off'][frame] + L['maskBytes'][frame] > len(decoded):
                raise SystemExit(f'{slug}: layer {L["name"]} frame {frame} mask escapes buffer')
    # v2.1 sprite/strip motion (static layers simply have motion: null / no motion key).
    motions, motion_index, motion_maskoff, motion_dx, motion_dy = \
        _v2_motion_tables(slug, layers, decoded)
    # v2.2 optional key panel: flat rect where the firmware renders the last pressed key.
    key_panel = _v2_key_panel(slug, meta)
    # v2.2 optional top bar: battery + caps indicators on firmware-fixed rectangles.
    topbar = _v2_topbar(slug, meta, key_panel)

    # Uploaded asset: frame 0 (calm) composite, two identical frames so the player advances.
    # For v2.1 motion schemes the motion-layer rectangles must stay FLAT in the upload:
    # the firmware paints a moving sprite there, so a baked calm sprite would leave a
    # ghost at the home position whenever travel>0.  Non-motion layers keep their calm
    # artwork baked, exactly like a v2.0 scheme.
    bg_src = scheme / 'preview-idle.png'
    if not bg_src.exists():
        bg_src = scheme / 'preview-normal.png'
    if not bg_src.exists():
        raise SystemExit(f'{slug}: scheme has no preview-idle.png / preview-normal.png')
    if motions:
        bg = _v2_flat_upload(scheme, bg_src, layers, hexrgb)
        upload_source = 'background.png'
    else:
        bg = Image.open(bg_src).convert('RGB').resize((320, 172))
        upload_source = bg_src.name
    q = bg.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
    _save_gif_two_identical_frames(q, out / 'background.gif')

    ink = meta.get('statusInk') or '#ffffff'
    bg_colors = [bg.getpixel((x + w // 2, y + h // 2)) for (x, y, w, h) in STATUS_REGIONS]

    eff = _v2_effect(meta)
    spawn = eff.get('spawn') or FX_NONE['spawn']
    vx = eff.get('vx') or [0, 0]
    vy = eff.get('vy') or [0, 0]
    colors = eff.get('colors') or ['#ffffff']
    trigger = eff.get('trigger') or 'key'
    count = int(eff.get('count', 0))
    react = meta.get('reaction') or {}
    pulse = meta.get('pulse')
    pulse_layer = -1
    if pulse:
        names = [L['name'] for L in layers]
        if pulse.get('layer') not in names:
            raise SystemExit(f'{slug}: pulse layer {pulse.get("layer")!r} not found')
        pulse_layer = names.index(pulse['layer'])

    from assets import ICONS
    lines = ['/* SPDX-License-Identifier: MIT; generated from an interactive pixel scheme. */']
    if motions:
        # Keep the upload traceable: motion layers stay flat so the moving sprite never
        # leaves a baked ghost at its home position.
        lines.append('/* upload: background.gif built from background.png '
                     '(flat sticker rects; firmware paints every layer). */')
    lines += ['#define UI_IDLE_MS 0u',
              '#define UI_USB_RAW 1',
              '#define UI_RF_RAW 0',
             '#define PX_SCHEME "%s"' % slug,
             '#define PX_LAYER_COUNT %d' % len(layers),
             '#define PX_FRAME_COUNT 4',
             '#define PX_FRAME_CALM 0',
             '#define PX_FRAME_CAPS 1',
             '#define PX_FRAME_REACT 2',
             '#define PX_FRAME_SLEEPY 3',
             'typedef struct {u16 x,y,w,h; u16 fg[4],bg[4],off[4]; u16 motion;} PxLayer;',
             'static const PxLayer px_layers[]={']
    for i, L in enumerate(layers):
        lines.append(' {%d,%d,%d,%d,{%s},{%s},{%s},%s},' % (
            int(L['x']), int(L['y']), int(L['w']), int(L['h']),
            ','.join('0x%04x' % px_rgb565(c) for c in L['fg']),
            ','.join('0x%04x' % px_rgb565(c) for c in L['bg']),
            ','.join(str(int(o)) for o in L['off']),
            '0xffff' if motion_index[i] == 0xffff else str(motion_index[i])))
    lines.append('};')
    # Motion tables: uniform across v2.0/v2.1 (count 0 + no arrays keeps old schemes
    # byte-identical and avoids unused-const warnings under -Werror).
    lines.append('#define PX_MOTION_COUNT %d' % len(motions))
    lines.append('typedef struct {u16 count, periodMs, keyPeriodMs, firstOff, travelRange, '
                 'stepPerKey; u8 advancePerKey, axis;} PxMotion;')
    if motions:
        lines.append('static const PxMotion px_motions[]={')
        for m in motions:
            lines.append(' {%d,%d,%d,%d,%d,%d,%d,%d},' % (
                m['count'], m['periodMs'], m['keyPeriodMs'], m['firstOff'],
                m['travelRange'], m['stepPerKey'], m['advancePerKey'], m['axis']))
        lines.append('};')
        for ctype, name, values in (('u16', 'px_motion_maskoff', motion_maskoff),
                                    ('short', 'px_motion_dx', motion_dx),
                                    ('short', 'px_motion_dy', motion_dy)):
            lines.append('static const %s %s[]={' % (ctype, name))
            for i in range(0, len(values), 16):
                lines.append(' ' + ','.join(str(v) for v in values[i:i + 16]) + ',')
            lines.append('};')
    lines.append('#define PX_MASK_RAM_BYTES %d' % len(decoded))
    lines.append('static const unsigned char px_mask_rle[]={')
    for i in range(0, len(rle), 24):
        lines.append(' ' + ','.join(str(b) for b in rle[i:i + 24]) + ',')
    lines.append('};')
    lines.append('#define PX_STATUS_INK 0x%04xu' % px_rgb565(ink))
    lines.append('static const u16 px_status_bg[3]={%s};' % ','.join(
        '0x%04x' % rgb565('#%02x%02x%02x' % c) for c in bg_colors))
    if topbar:
        # The top bar replaces the default status cluster, which was the only
        # connection_icons consumer; omitting it avoids -Wunused-const-variable.
        lines.append('/* PX_TOPBAR replaces the status cluster: connection_icons omitted. */')
    else:
        lines.append('static const u16 connection_icons[3][16]={')
        for row in ICONS:
            lines.append(' {' + ','.join(str(v) for v in row) + '},')
        lines.append('};')
    lines.append('#define FX_COUNT %d' % count)
    lines.append('#define FX_SIZE %d' % int(eff.get('size', 1)))
    lines.append('#define FX_SPAWN_X %d' % int(spawn[0]))
    lines.append('#define FX_SPAWN_Y %d' % int(spawn[1]))
    lines.append('#define FX_SPAWN_W %d' % int(spawn[2]))
    lines.append('#define FX_SPAWN_H %d' % int(spawn[3]))
    lines.append('#define FX_VX_MIN %d' % int(vx[0]))
    lines.append('#define FX_VX_MAX %d' % int(vx[1]))
    lines.append('#define FX_VY_MIN %d' % int(vy[0]))
    lines.append('#define FX_VY_MAX %d' % int(vy[1]))
    lines.append('#define FX_GRAVITY %d' % int(eff.get('gravity', 0)))
    lines.append('#define FX_LIFE_MS %d' % int(eff.get('lifeMs', 600)))
    # Fixed engine cap (also covers energy-bonus/continuous spawn); never derived from
    # the scheme so the firmware's static particle array is always well-defined.
    lines.append('#define FX_MAX_ALIVE 24')
    lines.append('#define FX_EDGE %d' % EDGE_CODES[eff.get('edge', 'die')])
    lines.append('#define FX_SHAPE %d' % SHAPE_CODES[eff.get('shape', 'square')])
    lines.append('#define FX_TRIGGER_KEY %d' % (1 if trigger in ('key', 'both') else 0))
    lines.append('#define FX_TRIGGER_CONT %d' % (1 if eff.get('continuous') else 0))
    lines.append('#define FX_ENERGY_BONUS %d' % (1 if eff.get('energyBonus') else 0))
    lines.append('#define FX_COLORS %d' % len(colors))
    lines.append('static const u16 fx_colors[%d]={%s};' % (
        len(colors), ','.join('0x%04x' % px_rgb565(c) for c in colors)))
    lines.append('#define FX_REACT_HOLD_MS %d' % int(react.get('reactHoldMs', 900)))
    lines.append('#define FX_SLEEPY_MS %d' % int(react.get('sleepyAfterMs', 25000)))
    lines.append('#define FX_CHARGE_REACT %d' % (1 if react.get('chargeUsesReact') else 0))
    lines.append('#define PX_PULSE_LAYER %d' % pulse_layer)
    lines.append('#define PX_PULSE_PERIOD_MS %d' % (int(pulse['periodMs']) if pulse else 0))
    lines.append('#define PX_PULSE_MIN %d' % (int(pulse['min']) if pulse else 0))
    # v2.2 key panel / top bar: a single define each when absent (no unused arrays
    # under -Werror); both features may coexist in one header.
    if key_panel:
        lines += _v2_keypanel_header(key_panel)
    else:
        lines.append('#define PX_KEYPANEL 0')
    if topbar:
        lines += _v2_topbar_header(topbar)
    else:
        lines.append('#define PX_TOPBAR 0')
    (out / 'px_assets.h').write_text('\n'.join(lines) + '\n', encoding='utf8')
    (out / 'px_font.h').write_text(_px_font_header(), encoding='utf8')

    return dict(scheme=slug, layers=len(layers), maskBytes=len(decoded),
                frames=len(FRAME_IDS), uploadSource=upload_source,
                motion=dict(count=len(motions), frames=len(motion_maskoff),
                            layers=[m['name'] for m in motions]),
                keyPanel=key_panel, topBar=topbar,
                effect=dict(mode=eff.get('mode'), count=count, size=int(eff.get('size', 1)),
                            trigger=trigger, continuous=bool(eff.get('continuous')),
                            edge=eff.get('edge'), shape=eff.get('shape'),
                            colors=len(colors), pulseLayer=pulse_layer))


def pack(scheme_dir, out_dir):
    scheme = Path(scheme_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((scheme / 'meta.json').read_text(encoding='utf8'))
    if _is_interactive(meta):
        return _pack_v2(scheme, out, meta)
    return _pack_v1(scheme, out, meta)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('usage: pixel_pack.py <scheme-dir> <out-dir>')
    print(json.dumps(pack(sys.argv[1], sys.argv[2]), ensure_ascii=False))
