"""Report and gate the appended-module section sizes of an IPS ``module.elf``.

The IPS patcher appends code into 0x0807EC90..0x08080000 (0x1370 = 4976 bytes for
``.text`` + ``.rodata``) and keeps module state in 0x2005F000..0x20060000 (4096
bytes for ``.bss``); ``.data`` is rejected by firmware/ips/linker.ld. This tool
parses the ELF32 little-endian section table directly, prints the sizes and the
remaining headroom, and exits nonzero when a budget is exceeded.

Usage:
    python tools/fx_size.py build/ips-fx/ips/module.elf
    python tools/fx_size.py build/ips-fx/ips/module.elf --json

SPDX-License-Identifier: MIT.
"""
import json
import struct
import sys
from pathlib import Path

TEXT_BUDGET = 4976      # .text + .rodata inside 0x0807EC90..0x08080000
DATA_BUDGET = 0         # no startup copy exists for initialised writable data
BSS_BUDGET = 4096       # module state reservation 0x2005F000..0x20060000
SECTIONS = ('.text', '.rodata', '.data', '.bss')


def read_sections(path):
    """Return {name: {'addr','offset','size','type'}} for an ELF32 little-endian file."""
    data = Path(path).read_bytes()
    if len(data) < 52 or data[:4] != b'\x7fELF' or data[4] != 1 or data[5] != 1:
        raise ValueError('expected a little-endian ELF32 file')
    hdr = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    shoff, shentsize, shnum, shstrndx = hdr[6], hdr[11], hdr[12], hdr[13]
    if not shoff or not shnum or shstrndx >= shnum or shentsize < 40:
        raise ValueError('ELF has no usable section table')
    if shoff + shnum * shentsize > len(data):
        raise ValueError('ELF section table is truncated')
    sections = [struct.unpack_from('<10I', data, shoff + i * shentsize) for i in range(shnum)]
    strings = sections[shstrndx]
    names = data[strings[4]:strings[4] + strings[5]]
    out = {}
    for sec in sections:
        start = sec[0]
        if start >= len(names):
            continue
        end = names.find(b'\0', start)
        name = names[start:end if end >= 0 else len(names)].decode('utf8', 'replace')
        out[name] = dict(addr=sec[3], offset=sec[4], size=sec[5], type=sec[1])
    return out


def measure(path):
    """Measure one module.elf and return the budget verdict as a dict."""
    sizes = {name: 0 for name in SECTIONS}
    for name, sec in read_sections(path).items():
        if name in sizes:
            sizes[name] += sec['size']
    code = sizes['.text'] + sizes['.rodata']
    verdict = dict(
        path=str(path), sections=sizes, code=code,
        textHeadroom=TEXT_BUDGET - code,
        dataHeadroom=DATA_BUDGET - sizes['.data'],
        bssHeadroom=BSS_BUDGET - sizes['.bss'],
        limits=dict(code=TEXT_BUDGET, data=DATA_BUDGET, bss=BSS_BUDGET),
        ok=code <= TEXT_BUDGET and sizes['.data'] == DATA_BUDGET and sizes['.bss'] <= BSS_BUDGET,
    )
    return verdict


def format_report(report):
    sizes = report['sections']
    limits = report['limits']
    lines = ['module section sizes: %s' % report['path'],
             '  .text            %6d B' % sizes['.text'],
             '  .rodata          %6d B' % sizes['.rodata'],
             '  .text+.rodata    %6d B / %d B   headroom %d B'
             % (report['code'], limits['code'], report['textHeadroom']),
             '  .data            %6d B (must be %d)' % (sizes['.data'], limits['data']),
             '  .bss             %6d B / %d B   headroom %d B'
             % (sizes['.bss'], limits['bss'], report['bssHeadroom'])]
    if report['ok']:
        lines.append('RESULT: OK')
    else:
        problems = []
        if report['code'] > limits['code']:
            problems.append('.text+.rodata %d B exceeds %d B' % (report['code'], limits['code']))
        if sizes['.data']:
            problems.append('.data is %d B (must be 0)' % sizes['.data'])
        if sizes['.bss'] > limits['bss']:
            problems.append('.bss %d B exceeds %d B' % (sizes['.bss'], limits['bss']))
        lines.append('RESULT: FAIL - ' + '; '.join(problems))
    return '\n'.join(lines)


def main(argv):
    args = [a for a in argv if a != '--json']
    as_json = len(args) != len(argv)
    if len(args) != 2:
        print('usage: fx_size.py <module.elf> [--json]', file=sys.stderr)
        return 2
    try:
        report = measure(args[1])
    except (OSError, ValueError, struct.error) as exc:
        print('fx_size: %s' % exc, file=sys.stderr)
        return 2
    print(json.dumps(report) if as_json else format_report(report))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
