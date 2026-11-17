"""Verify saved rainy75-px/2 schemes: budgets, masks, frames, previews, effects.

Usage:
    python tools/verify_schemes.py [--dir build/design-gallery] [--glob 'px6-*']
                                  [--expect 50] [--quiet]

Exit code 1 if any scheme fails.  No hardware access.
SPDX-License-Identifier: MIT.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pixel_scheme as PS  # noqa: E402

FAMILIES = ('治愈暖光', '元气清晨', '深夜陪伴', '摸鱼松弛', '浪漫心动', '幻想冒险')


class NotV2(Exception):
    """A scheme directory in an older/other schema; skipped, not a failure."""


def check(path):
    problems = []
    meta = PS.load_scheme(path)
    if meta.get('schema') != 'rainy75-px/2':
        raise NotV2(meta.get('slug') or path.name)
    slug = meta.get('slug', path.name)
    if slug != path.name:
        problems.append('slug != directory name')
    if not slug.startswith('px6-'):
        problems.append('slug prefix')
    for key in ('name', 'description', 'attribution'):
        if not str(meta.get(key, '')).strip():
            problems.append('missing ' + key)
    if len(meta.get('description', '')) < 40:
        problems.append('description too short for an emotional story')
    emotion = meta.get('emotion') or {}
    if emotion.get('family') not in FAMILIES:
        problems.append('emotion.family missing/unknown: %r' % emotion.get('family'))
    if not isinstance(emotion.get('tags'), list) or not emotion['tags']:
        problems.append('emotion.tags missing')
    if not 3 <= len(meta.get('palette') or []) <= 10:
        problems.append('palette size')
    for colour in meta.get('palette') or []:
        PS.hexrgb(colour)

    layers = meta['layers']
    if not 1 <= len(layers) <= PS.MAX_LAYERS:
        problems.append('layer count %d' % len(layers))
    x0, y0, x1, y1 = PS.STATUS
    for L in layers:
        if not (0 <= L['x'] and 0 <= L['y'] and L['x'] + L['w'] <= PS.SIZE[0]
                and L['y'] + L['h'] <= PS.SIZE[1]):
            problems.append('%s outside screen' % L['name'])
        if L['x'] < x1 and L['x'] + L['w'] > x0 and L['y'] < y1 and L['y'] + L['h'] > y0:
            problems.append('%s overlaps status' % L['name'])
        for idx in range(4):
            if not (isinstance(L['fg'][idx], str) and isinstance(L['bg'][idx], str)):
                problems.append('%s frame %d colours' % (L['name'], idx))
        if sum(1 for v in L['off'] if v == L['off'][0]) != len(L['off']):
            pass  # identical frames reuse offsets, which is expected

    # masks / budgets
    data = (Path(path) / meta['masks']['data']).read_bytes()
    decoded = PS.decode_scheme_masks(meta, data)
    if len(decoded) != meta['masks']['decodedBytes']:
        problems.append('decoded size %d != meta %d' % (len(decoded), meta['masks']['decodedBytes']))
    if len(data) != meta['masks']['encodedBytes']:
        problems.append('masks.bin size %d != meta %d' % (len(data), meta['masks']['encodedBytes']))
    if meta['masks']['decodedBytes'] > PS.MASK_RAM_BUDGET:
        problems.append('decoded masks over RAM budget')
    if meta['masks']['encodedBytes'] > PS.ENCODED_BUDGET:
        problems.append('encoded masks over flash budget')
    ram = sum((L['w'] * L['h'] + 7) // 8 for L in layers)
    if ram != meta['budgets']['state1Bytes']:
        problems.append('state1Bytes mismatch')
    for L in layers:
        for idx in range(4):
            need = (L['w'] * L['h'] + 7) // 8
            off = L['off'][idx]
            if off < 0 or off + need > len(decoded):
                problems.append('%s frame %d offset out of buffer' % (L['name'], idx))
            elif need != L['maskBytes'][idx]:
                problems.append('%s frame %d maskBytes mismatch' % (L['name'], idx))
            elif (idx > 0 and off == L['off'][0]
                  and L['maskBytes'][idx] == L['maskBytes'][0]):
                pass  # reused mask pointer

    # background flatness (firmware paints these rectangles flat on every frame)
    bg = Image.open(Path(path) / 'background.png').convert('RGB')
    if bg.size != PS.SIZE:
        problems.append('background size')
    for L in layers:
        crop = bg.crop((L['x'], L['y'], L['x'] + L['w'], L['y'] + L['h']))
        colours = crop.getcolors(1 << 20)
        if not colours or len(colours) != 1:
            problems.append('%s rect not flat' % L['name'])
            continue
        flat = colours[0][1]
        for idx in range(1, 4):
            if PS.hexrgb(L['bg'][idx]) != flat:
                problems.append('%s frame %d bg != flat' % (L['name'], idx))

    # preview round-trips
    for frame, name in enumerate(('preview-idle.png', 'preview-caps.png',
                                  'preview-react.png', 'preview-sleepy.png')):
        ref = Image.open(Path(path) / name).convert('RGB')
        got = PS.stamp(bg, meta, decoded, frame)
        if ImageChops.difference(ref, got).getbbox():
            problems.append('%s round-trip mismatch' % name)

    eff = meta.get('effect') or {}
    if eff.get('mode') not in PS.EFFECT_PRESETS:
        problems.append('effect mode %r' % eff.get('mode'))
    if not 0 <= eff.get('count', 0) <= 12 or not 1 <= eff.get('size', 0) <= 5:
        problems.append('effect count/size')
    if eff.get('count', 0):
        if eff.get('trigger') not in PS.TRIGGERS:
            problems.append('effect trigger')
        if eff.get('edge') not in PS.EDGES or eff.get('shape') not in PS.SHAPES:
            problems.append('effect edge/shape')
        sr = eff.get('spawn') or [0, 0, 0, 0]
        if not (0 <= sr[0] and 0 <= sr[1] and sr[0] + sr[2] <= PS.SIZE[0]
                and sr[1] + sr[3] <= PS.SIZE[1] and sr[2] > 0 and sr[3] > 0):
            problems.append('effect spawnRect')
        if sr[0] < x1 and sr[0] + sr[2] > x0 and sr[1] < y1 and sr[1] + sr[3] > y0:
            problems.append('effect spawnRect overlaps status')

    for L in layers:
        mo = L.get('motion')
        if not mo:
            continue
        if not 2 <= mo.get('count', 0) <= 8:
            problems.append('%s motion count' % L['name'])
        if not 40 <= mo.get('periodMs', 0) <= 2000:
            problems.append('%s motion period' % L['name'])
        if not 30 <= mo.get('keyPeriodMs', 0) <= 500:
            problems.append('%s motion key period' % L['name'])
        if mo.get('axis') not in ('x', 'y'):
            problems.append('%s motion axis' % L['name'])
        if len(mo.get('off', [])) != mo.get('count') or len(mo.get('maskBytes', [])) != mo.get('count'):
            problems.append('%s motion tables' % L['name'])
        if len(mo.get('dx', [])) != mo.get('count') or len(mo.get('dy', [])) != mo.get('count'):
            problems.append('%s motion offsets' % L['name'])
        for idx in range(mo.get('count', 0)):
            need = (L['w'] * L['h'] + 7) // 8
            off = mo['off'][idx]
            if off < 0 or off + need > len(decoded):
                problems.append('%s motion mask offset' % L['name'])
            if mo['maskBytes'][idx] != need:
                problems.append('%s motion mask size' % L['name'])
        if not 0 <= mo.get('travelRange', 0) <= 320:
            problems.append('%s motion travel' % L['name'])
        if not 0 <= mo.get('stepPerKey', 0) <= 40:
            problems.append('%s motion step' % L['name'])

    pulse = meta.get('pulse')
    if pulse:
        names = [L['name'] for L in layers]
        if pulse.get('layer') not in names:
            problems.append('pulse layer %r' % pulse.get('layer'))
        if not 500 <= pulse.get('periodMs', 0) <= 6000:
            problems.append('pulse period')
        if not 60 <= pulse.get('min', 0) <= 240:
            problems.append('pulse min')
    reaction = meta.get('reaction') or {}
    for key in ('reactHoldMs', 'sleepyAfterMs', 'energyKeys', 'energyWindowMs'):
        if not isinstance(reaction.get(key), int) or reaction[key] < 0:
            problems.append('reaction.' + key)

    # typing preview must differ and only add particle colours
    if eff.get('count'):
        idle = Image.open(Path(path) / 'preview-react.png').convert('RGB')
        typing = Image.open(Path(path) / 'preview-typing.png').convert('RGB')
        box = ImageChops.difference(idle, typing).getbbox()
        if not box:
            problems.append('preview-typing identical to preview-react')
        else:
            allowed = {PS.hexrgb(c) for c in eff.get('colors') or []}
            extra = set()
            for y in range(box[1], box[3]):
                for x in range(box[0], box[2]):
                    if typing.getpixel((x, y)) != idle.getpixel((x, y)):
                        extra.add(typing.getpixel((x, y)))
            if not extra <= allowed:
                problems.append('typing preview extra colours: %r' % (extra - allowed))
    return slug, problems, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(PS.OUT))
    ap.add_argument('--glob', default='px6-*')
    ap.add_argument('--expect', type=int, default=0)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    root = Path(args.dir)
    dirs = sorted(p for p in root.glob(args.glob) if (p / 'meta.json').is_file())
    if not dirs:
        print('no schemes found in %s matching %s' % (root, args.glob))
        return 1
    failures, families, slugs = [], {}, set()
    skipped = 0
    for path in dirs:
        try:
            slug, problems, meta = check(path)
        except NotV2:
            skipped += 1
            continue
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append((path.name, ['exception: %s' % exc]))
            continue
        if slug in slugs:
            problems.append('duplicate slug')
        slugs.add(slug)
        fam = (meta.get('emotion') or {}).get('family', '?')
        families[fam] = families.get(fam, 0) + 1
        if problems:
            failures.append((slug, problems))
        elif not args.quiet:
            print('ok   %-22s %s  masks %dB/%dB' % (
                slug, fam, meta['masks']['encodedBytes'], meta['masks']['decodedBytes']))
    print('\n%d schemes, %d ok, %d failed%s' % (
        len(dirs) - skipped, len(dirs) - skipped - len(failures), len(failures),
        (', %d other-schema skipped' % skipped) if skipped else ''))
    for fam, count in sorted(families.items()):
        print('  %-6s %d' % (fam, count))
    for slug, problems in failures:
        print('FAIL %s' % slug)
        for p in problems:
            print('     - %s' % p)
    if args.expect and len(dirs) - skipped != args.expect:
        print('expected %d schemes, found %d' % (args.expect, len(dirs) - skipped))
        return 1
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
