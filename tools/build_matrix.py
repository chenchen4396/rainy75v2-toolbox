"""Build every interactive pixel scheme and check the firmware flash budget.

Usage:
    python tools/build_matrix.py [--dir build/design-gallery] [--limit N]
    python tools/build_matrix.py --scheme px6-warm-coffee

For each scheme it runs tools/build.py with --fx, then parses module.elf and asserts
.text+.rodata <= 4976 B, .data == 0, .bss <= 4096 B.  No hardware access.
SPDX-License-Identifier: MIT.
"""
import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLANG = Path(r'E:\Code\toolchain\clang+llvm-23.1.5-x86_64-pc-windows-msvc\bin\clang.exe')
PY = ROOT / '.venv' / 'Scripts' / 'python.exe'
FLASH_LIMIT = 4976
RAM_LIMIT = 4096


def sections(path):
    data = Path(path).read_bytes()
    if data[:4] != b'\x7fELF' or data[4:6] != bytes([1, 1]):
        raise ValueError('not ELF32 LE: %s' % path)
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    shoff, shentsize, shnum, shstrndx = h[6], h[11], h[12], h[13]
    secs = [struct.unpack_from('<10I', data, shoff + i * shentsize) for i in range(shnum)]
    strtab = secs[shstrndx]
    names = data[strtab[4]:strtab[4] + strtab[5]]

    def name(s):
        return names[s[0]:names.find(b'\0', s[0])].decode('ascii', 'replace')

    out = {}
    for s in secs:
        n = name(s)
        if n in ('.text', '.rodata', '.data', '.bss'):
            out[n] = s[5]
    return out


def build_one(scheme, out_root):
    out = out_root / scheme.name
    cmd = [str(PY), str(ROOT / 'tools/build.py'), 'ips',
           '--stock', str(ROOT / 'inputs/ips-stock.bin'),
           '--pixel', str(scheme), '--fx',
           '--clang', str(CLANG), '--out', str(out)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    if proc.returncode:
        return None, (proc.stderr or proc.stdout or '').strip().splitlines()[-1:] or ['build failed']
    elf = out / 'ips' / 'module.elf'
    if not elf.is_file():
        return None, ['module.elf missing']
    sec = sections(elf)
    return sec, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(ROOT / 'build/design-gallery'))
    ap.add_argument('--out', default=str(ROOT / 'build/pixel-builds'))
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--scheme', default='')
    args = ap.parse_args()
    root = Path(args.dir)
    def is_v2(p):
        try:
            return json.loads((p / 'meta.json').read_text(encoding='utf8')).get('schema') == 'rainy75-px/2'
        except Exception:  # noqa: BLE001 - skip broken/other-schema dirs
            return False

    schemes = ([root / args.scheme] if args.scheme
               else sorted(p for p in root.glob('px6-*') if (p / 'meta.json').is_file() and is_v2(p)))
    if args.limit:
        schemes = schemes[:args.limit]
    if not schemes:
        print('no schemes found under', root)
        return 1
    if not (ROOT / 'inputs/ips-stock.bin').is_file():
        print('inputs/ips-stock.bin missing; cannot build')
        return 1
    out_root = Path(args.out)
    rows, failed = [], 0
    worst = None
    for scheme in schemes:
        sec, err = build_one(scheme, out_root)
        if sec is None:
            rows.append((scheme.name, None, err))
            failed += 1
            print('FAIL %-24s %s' % (scheme.name, err))
            continue
        flash = sec.get('.text', 0) + sec.get('.rodata', 0)
        ram = sec.get('.bss', 0)
        bad = []
        if flash > FLASH_LIMIT:
            bad.append('flash %d > %d' % (flash, FLASH_LIMIT))
        if sec.get('.data', 0) != 0:
            bad.append('.data=%d' % sec.get('.data', 0))
        if ram > RAM_LIMIT:
            bad.append('bss %d > %d' % (ram, RAM_LIMIT))
        if bad:
            failed += 1
            print('FAIL %-24s %s' % (scheme.name, '; '.join(bad)))
        else:
            head = FLASH_LIMIT - flash
            if worst is None or head < worst[1]:
                worst = (scheme.name, head, flash, ram)
            print('ok   %-24s flash %4d B (head %3d)  bss %3d B'
                  % (scheme.name, flash, head, ram))
        rows.append((scheme.name, sec, []))
    print('\n%d schemes, %d failed' % (len(schemes), failed))
    if worst:
        print('worst headroom: %s  flash %d B  head %d B  bss %d B'
              % (worst[0], worst[2], worst[1], worst[3]))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
