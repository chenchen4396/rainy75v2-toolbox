"""Host self-check for the key-panel label mapping (firmware/ips/reactive_keylabel.h).

The mapping is pure C with no firmware dependencies, so it is compiled to WebAssembly
with the project clang and executed in Node - the same technique used for the glyph
table check. This catches wrong ranges/labels without flashing a device.

Expected codes come from profiles/keys.json (native profile 0.6.2): normal keys are USB
HID usage ids, modifiers are the negative 8-bit codes 0xF8..0xFF, Fn keys are 401..405.
Skips when clang or Node is unavailable.
SPDX-License-Identifier: MIT.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / 'firmware/ips/reactive_keylabel.h'

CASES = [
    (4, 'A'), (29, 'Z'), (30, '1'), (39, '0'),
    (40, 'ENTER'), (41, 'ESC'), (42, 'DEL'), (43, 'TAB'), (44, 'SPACE'),
    (45, '-'), (46, '+'), (47, '['), (48, ']'), (49, '\\'), (50, ';'),
    (51, "'"), (52, '~'), (53, ','), (54, '.'), (55, '/'),
    (57, 'CAPS'), (58, 'F1'), (69, 'F12'),
    (70, 'PRT'), (71, 'SCR'), (72, 'PAU'),
    (73, 'INS'), (76, 'DEL'), (75, 'PGU'), (78, 'PGD'),
    (83, 'NUM'), (84, 'KP'), (87, 'KP'),
    (89, 'KP1'), (98, 'KP0'), (99, 'KP.'),
    (227, 'WIN'),
    (0xF8, 'CTRL'), (0xF9, 'SHIFT'), (0xFA, 'ALT'), (0xFB, 'WIN'),
    (0xFC, 'CTRL'), (0xFD, 'SHIFT'), (0xFE, 'ALT'), (0xFF, 'WIN'),
    (0xE1, 'SHIFT'),
    (0xFFF9, 'SHIFT'), (0xFFFC, 'CTRL'), (0xFFFE, 'ALT'), (0xFFFF, 'WIN'),
    (0xFFF8, 'CTRL'), (0xFFFA, 'ALT'), (0xFFFB, 'WIN'), (0xFFFD, 'SHIFT'),
    (401, 'FN1'), (403, 'FN3'), (405, 'FN5'),
    (0x80, 'K80'),
]

RUNNER = r'''
const fs = require('fs');
WebAssembly.instantiate(fs.readFileSync(process.argv[2]))
  .then(({instance}) => {
    const bad = instance.exports.check();
    if (bad) { console.error('keylabel mismatches: ' + bad); process.exit(1); }
    console.log('keylabel ok');
  })
  .catch((e) => { console.error(String(e)); process.exit(1); });
'''


def find_tool(*candidates):
    for cand in candidates:
        if not cand:
            continue
        path = Path(cand)
        if path.is_file():
            return str(path)
        found = shutil.which(cand)
        if found:
            return found
    return None


class KeyLabelTest(unittest.TestCase):
    def test_mapping_matches_native_profile(self):
        clang = find_tool('E:/Code/toolchain/clang+llvm-23.1.5-x86_64-pc-windows-msvc/bin/clang.exe',
                          'clang')
        node = shutil.which('node')
        if not clang or not node:
            self.skipTest('host clang/node not available')

        cases_c = ''.join(
            '  {%du, "%s"},\n' % (k, w.replace('\\', '\\\\')) for k, w in CASES)
        src = (
            '#include "reactive_keylabel.h"\n'
            'static char buf[8];\n'
            'static int same(const char *a, const char *b) '
            '{ while (*a && *b) { if (*a != *b) return 0; a++; b++; } return *a == *b; }\n'
            'struct case_t { unsigned k; const char *want; };\n'
            'static const struct case_t cases[] = {\n' + cases_c + '  };\n'
            '__attribute__((export_name("check"))) int check(void) {\n'
            '  unsigned i; int bad = 0;\n'
            '  for (i = 0; i < sizeof(cases)/sizeof(cases[0]); i++) {\n'
            '    const char *got = rk_key_label(cases[i].k, buf);\n'
            '    if (!same(got, cases[i].want)) bad++;\n'
            '  }\n'
            '  return bad;\n'
            '}\n')

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            c_file = tmp / 'keylabel.c'
            wasm = tmp / 'keylabel.wasm'
            runner = tmp / 'run.cjs'
            c_file.write_text(src, encoding='utf8')
            runner.write_text(RUNNER, encoding='utf8')
            build = subprocess.run(
                [clang, '--target=wasm32', '-nostdlib', '-Wl,--no-entry',
                 '-Wl,--export=check', '-I', str(HEADER.parent),
                 str(c_file), '-o', str(wasm)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0,
                             'wasm compile failed:\n%s\n%s' % (build.stdout, build.stderr))
            run = subprocess.run([node, str(runner), str(wasm)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0,
                             'label mismatches:\n%s\n%s' % (run.stdout, run.stderr))


if __name__ == '__main__':
    unittest.main()
