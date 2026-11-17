"""Build the interactive pixel-scheme gallery: sheets, typing GIFs, index.json/HTML.

Usage:
    python tools/scheme_gallery.py [--dir build/design-gallery] [--out build/pixel-gallery]
                                   [--no-gifs] [--gif-limit N]

Reads only saved scheme directories (meta.json/masks.bin/previews), writes into the
ignored build tree.  No hardware access.  SPDX-License-Identifier: MIT.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pixel_scheme as PS  # noqa: E402

FAMILY_ORDER = ('治愈暖光', '元气清晨', '深夜陪伴', '摸鱼松弛', '浪漫心动', '幻想冒险')
FAMILY_EN = {'治愈暖光': 'COMFORT', '元气清晨': 'VITALITY', '深夜陪伴': 'NIGHT',
             '摸鱼松弛': 'SLACK', '浪漫心动': 'ROMANCE', '幻想冒险': 'FANTASY'}
FRAME_FILES = ('preview-idle.png', 'preview-caps.png', 'preview-react.png',
               'preview-sleepy.png')


def font(size):
    for name in ('msyh.ttc', 'simhei.ttf', 'segoeui.ttf', 'arial.ttf'):
        path = Path('C:/Windows/Fonts') / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def label(draw, xy, text, size=13, fill=(236, 236, 228)):
    draw.text(xy, text, font=font(size), fill=fill)


def load_schemes(root):
    out = []
    for path in sorted(root.glob('px6-*')):
        meta_path = path / 'meta.json'
        if not meta_path.is_file():
            continue
        try:
            meta = PS.load_scheme(path)
            if meta.get('schema') != 'rainy75-px/2':
                continue
            data = (path / meta['masks']['data']).read_bytes()
            decoded = PS.decode_scheme_masks(meta, data)
            bg = Image.open(path / 'background.png').convert('RGB')
        except Exception as exc:  # noqa: BLE001 - report and skip broken dirs
            print('skip %s: %s' % (path.name, exc))
            continue
        out.append(dict(path=path, meta=meta, decoded=decoded, bg=bg))
    return out


def scheme_home(scheme):
    return scheme['meta'].get('emotion', {}).get('family', '?')


def sheet(items, out, cols, per_item, title, scale=1):
    tw, th = 320 * scale, 172 * scale
    gap, head, foot = 10, 40, 22
    rows = (len(items) + cols - 1) // cols
    W = cols * (tw * per_item + gap * (per_item - 1)) + gap * (cols + 1)
    H = head + rows * (th + foot + gap) + gap
    canvas = Image.new('RGB', (W, H), (16, 16, 22))
    draw = ImageDraw.Draw(canvas)
    label(draw, (gap, 12), title, 16, (255, 220, 130))
    for i, s in enumerate(items):
        cx = gap + (i % cols) * (tw * per_item + gap * (per_item - 1) + gap)
        cy = head + gap + (i // cols) * (th + foot + gap)
        for k, path in enumerate(s['frames'][:per_item]):
            im = Image.open(path).convert('RGB')
            if scale != 1:
                im = im.resize((tw, th), Image.NEAREST)
            canvas.paste(im, (cx + k * (tw + gap), cy))
        meta = s['meta']
        label(draw, (cx + 2, cy + th + 4), '%s  %s' % (meta['slug'], meta.get('name', '')), 13)
    canvas.save(out)
    return out


def typing_gif(item, out, fps=25, seconds=3.4):
    meta, decoded, bg = item['meta'], item['decoded'], item['bg']
    eff = meta.get('effect') or PS.effect_preset('none')
    sim = PS.ParticleSim(eff, seed=11)
    keys = [0.25, 0.55, 0.85, 1.15, 1.45, 1.75]
    frames = []
    base = {f: PS.stamp(bg, meta, decoded, f) for f in range(4)}
    motion = any(L.get('motion') for L in meta['layers'])
    key_count = 0
    for i in range(int(seconds * fps)):
        t = i / fps
        while keys and keys[0] <= t:
            keys.pop(0)
            sim.burst()
            key_count += 1
        sim.step(1000 / fps)
        frame = 2 if t < 2.6 else 0
        if frame == 2 and motion:
            im = PS.stamp_motion(bg, meta, decoded, 2, t * 1000, key_count)
        else:
            im = base[frame].copy()
        sim.draw(im)
        frames.append(im)
    pal = [f.quantize(colors=255, method=Image.MEDIANCUT) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=int(1000 / fps),
                loop=0, optimize=False)
    return out


def _pulse_preview(im, meta, t_ms):
    """Model the firmware's breathing colour on the pulse layer."""
    pulse = meta['pulse']
    layer = next(L for L in meta['layers'] if L['name'] == pulse['layer'])
    k = PS._pulse_scale(t_ms, pulse['periodMs'], pulse['min'])
    im = im.copy()
    d = ImageDraw.Draw(im)
    off = layer['off'][2]
    fg = tuple(round(c * k) for c in PS.hexrgb(layer['fg'][2]))
    for yy in range(layer['h']):
        for xx in range(layer['w']):
            bit = yy * layer['w'] + xx
            if meta and (meta['masks'] and True):
                pass
            if off + (bit >> 3) < 0:
                continue
    # redraw from masks directly (fast enough for 50 gifs)
    data = (Path(meta['_dir']) / meta['masks']['data']).read_bytes()
    decoded = PS.decode_scheme_masks(meta, data)
    d.rectangle((layer['x'], layer['y'], layer['x'] + layer['w'] - 1,
                 layer['y'] + layer['h'] - 1), fill=PS.hexrgb(layer['bg'][2]))
    for yy in range(layer['h']):
        for xx in range(layer['w']):
            bit = yy * layer['w'] + xx
            if decoded[off + (bit >> 3)] & (0x80 >> (bit & 7)):
                im.putpixel((layer['x'] + xx, layer['y'] + yy), fg)
    return im


def build_index(items, out, sheet_paths):
    families = {}
    for s in items:
        families.setdefault(scheme_home(s), []).append(s)
    catalogue = []
    for s in items:
        meta = s['meta']
        previews = {}
        for key, src in zip(('idle', 'caps', 'react', 'sleepy', 'typing'),
                            FRAME_FILES + ('preview-typing.png',)):
            dst_rel = 'previews/%s-%s.png' % (meta['slug'], key)
            src_path = s['path'] / src
            if src_path.is_file():
                shutil.copy2(src_path, out / dst_rel)
                previews[key] = dst_rel
        gif = 'gifs/%s.gif' % meta['slug']
        if (out / gif).is_file():
            previews['animation'] = gif
        catalogue.append(dict(slug=meta['slug'], name=meta.get('name'),
                              family=scheme_home(s), tags=meta['emotion'].get('tags', []),
                              story=meta['emotion'].get('story', ''),
                              description=meta.get('description', ''),
                              palette=meta.get('palette', []), previews=previews,
                              effect=(meta.get('effect') or {}).get('mode'),
                              reaction=meta.get('reaction'),
                              masks=meta['masks']))
    payload = dict(generated_by='tools/scheme_gallery.py', families=list(families),
                   count=len(catalogue), sheets=sheet_paths, schemes=catalogue)
    (out / 'index.json').write_text(json.dumps(payload, ensure_ascii=False, indent=1)
                                    + '\n', encoding='utf8')
    return payload


def html(payload):
    import html as H
    cards = []
    for s in payload['schemes']:
        p = s['previews']
        fam = s['family']
        sw = ''.join('<i style="background:%s"></i>' % H.escape(c) for c in s['palette'])
        tags = ''.join('<em>%s</em>' % H.escape(t) for t in s['tags'])
        gif = ('<img class="anim" loading="lazy" src="%s" alt="typing animation">'
               % p['animation']) if p.get('animation') else ''
        shots = ''.join('<img loading="lazy" src="%s" alt="%s">' % (p[k], k)
                        for k in ('idle', 'caps', 'react', 'sleepy') if k in p)
        cards.append(
            '<article class="card" data-family="%s" data-slug="%s">'
            '<header><h3>%s</h3><span class="slug">%s</span></header>'
            '<p class="story">%s</p>'
            '<div class="shots">%s</div>'
            '<div class="gifwrap">%s</div>'
            '<p class="desc">%s</p>'
            '<div class="meta"><div class="sw">%s</div><div class="tags">%s</div></div>'
            '</article>'
            % (H.escape(fam), H.escape(s['slug']), H.escape(s['name'] or ''),
               H.escape(s['slug']), H.escape(s['story']), shots, gif,
               H.escape(s['description']), sw, tags))
    filters = ''.join('<button data-f="%s">%s <b>%d</b></button>' % (
        H.escape(f), H.escape(FAMILY_EN.get(f, f)),
        sum(1 for s in payload['schemes'] if s['family'] == f))
        for f in FAMILY_ORDER if any(s['family'] == f for s in payload['schemes']))
    sheets = ''.join('<figure><img src="%s" alt="sheet"><figcaption>%s</figcaption></figure>'
                     % (H.escape(p), H.escape(Path(p).stem)) for p in payload['sheets'])
    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rainy75 V2 · 互动像素方案</title>
<style>
:root{--bg:#111018;--card:#1b1924;--ink:#ece9f1;--dim:#9a93a8;--acc:#ffd27a;--pink:#ff7fa8;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 "Microsoft YaHei",system-ui,sans-serif}
header.top{padding:38px 24px 10px;max-width:1280px;margin:0 auto}
h1{margin:0;font-size:30px;letter-spacing:.06em}h1 b{color:var(--pink)}
.sub{color:var(--dim);max-width:760px}.note{color:var(--acc);font-size:13px;max-width:760px}
.filters{display:flex;flex-wrap:wrap;gap:8px;max-width:1280px;margin:18px auto;padding:0 24px}
.filters button{background:#211f2c;color:var(--ink);border:1px solid #35314a;border-radius:999px;
padding:6px 14px;cursor:pointer}.filters button.on,.filters button:hover{border-color:var(--acc);color:var(--acc)}
main{max-width:1280px;margin:0 auto;padding:0 24px 60px;display:grid;
grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px}
.card{background:var(--card);border:1px solid #2a2739;border-radius:14px;padding:14px}
.card header{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.card h3{margin:0;font-size:18px}.slug{color:var(--dim);font-size:12px}
.story{margin:8px 0;color:var(--acc);font-size:13px}
.shots{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.shots img{width:100%%;image-rendering:pixelated;border-radius:6px;border:1px solid #2f2b40}
.gifwrap img{width:100%%;margin-top:8px;image-rendering:pixelated;border-radius:6px}
.desc{color:var(--dim);font-size:13px;margin:8px 0}
.meta{display:flex;justify-content:space-between;gap:8px;align-items:center}
.sw i{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:3px}
.tags em{font-style:normal;font-size:11px;color:#c9c3da;background:#252233;border-radius:999px;
padding:2px 7px;margin-left:4px}
section.sheets{max-width:1280px;margin:10px auto 40px;padding:0 24px}
section.sheets img{width:100%%;border-radius:10px;border:1px solid #2a2739}
footer{color:var(--dim);text-align:center;padding:24px;font-size:12px}
</style></head><body>
<header class="top"><h1>RAINY75 V2 · <b>互动像素方案</b></h1>
<p class="sub">%d 套情绪化像素界面：平静、Caps、打字互动、久坐待机四个状态，按键会触发粒子，英雄物件会呼吸。<br>
全部预览由源码程序渲染，同一份源码生成固件与网页预览，<b>不是实机拍摄</b>。</p>
<p class="note">说明：真机效果仍需实机确认；本页仅做离线模型检查。</p></header>
<div class="filters"><button data-f="" class="on">全部 <b>%d</b></button>%s</div>
<main>%s</main>
<section class="sheets"><h2 style="color:#ffd27a">总览</h2>%s</section>
<footer>Rainy75 V2 · 社区实验项目 · MIT 源码 · 原创像素素材</footer>
<script>
const cards=[...document.querySelectorAll('.card')];
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.filters button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
 const f=b.dataset.f;cards.forEach(c=>c.style.display=(!f||c.dataset.family===f)?'':'none');
});
</script></body></html>""" % (payload['count'], payload['count'], filters, ''.join(cards), sheets)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(PS.OUT))
    ap.add_argument('--out', default=str(ROOT / 'build/pixel-gallery'))
    ap.add_argument('--no-gifs', action='store_true')
    ap.add_argument('--gif-limit', type=int, default=0)
    args = ap.parse_args()
    root, out = Path(args.dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'previews').mkdir(exist_ok=True)
    (out / 'gifs').mkdir(exist_ok=True)
    schemes = load_schemes(root)
    if not schemes:
        print('no schemes found in', root)
        return 1
    for s in schemes:
        meta = s['meta']
        meta['_dir'] = str(s['path'])
        s['frames'] = [s['path'] / f for f in FRAME_FILES]
    sheets = []
    by_family = {}
    for s in schemes:
        by_family.setdefault(scheme_home(s), []).append(s)
    for fam in FAMILY_ORDER:
        group = by_family.get(fam)
        if not group:
            continue
        out_path = out / ('sheet-%s.png' % FAMILY_EN[fam].lower())
        sheets.append(sheet(group, out_path, 4, 2, '%s / %s  (%d)'
                            % (FAMILY_EN[fam], fam, len(group)), scale=1).name)
    sheets.insert(0, sheet(schemes, out / 'sheet-all.png', 4, 1,
                           'ALL PIXEL SCHEMES (%d)' % len(schemes)).name)
    limit = args.gif_limit or len(schemes)
    made = 0
    if not args.no_gifs:
        for s in schemes[:limit]:
            try:
                typing_gif(s, out / 'gifs' / ('%s.gif' % s['meta']['slug']))
                made += 1
            except Exception as exc:  # noqa: BLE001
                print('gif failed %s: %s' % (s['meta']['slug'], exc))
    payload = build_index(schemes, out, sheets)
    (out / 'index.html').write_text(html(payload), encoding='utf8')
    print('gallery: %d schemes, %d gifs, sheets=%s -> %s'
          % (len(schemes), made, sheets, out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
