"""Host-side checks for the rainy75-px/2 interactive pixel schemes.

Generated scheme directories live in the ignored build/ tree, so the heavy checks are
skipped on a clean checkout.  The toolkit and generator scripts are always checked.
SPDX-License-Identifier: MIT.
"""
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

try:
    import pixel_scheme as PS  # noqa: E402
    import verify_schemes as VS  # noqa: E402
except Exception as exc:  # noqa: BLE001 - Pillow may be missing on a host without deps
    PS = None
    VS = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

SCHEME_ROOT = ROOT / 'build/design-gallery'
FAMILY_SCRIPTS = ('px6_comfort.py', 'px6_vitality.py', 'px6_night.py',
                  'px6_slack.py', 'px6_romance.py', 'px6_fantasy.py')
EXPECTED_PER_FAMILY = {'治愈暖光': 8, '元气清晨': 8, '深夜陪伴': 8,
                       '摸鱼松弛': 8, '浪漫心动': 9, '幻想冒险': 9}


def v2_dirs():
    if not SCHEME_ROOT.is_dir():
        return []
    out = []
    for path in sorted(SCHEME_ROOT.glob('px6-*')):
        meta = path / 'meta.json'
        if not meta.is_file():
            continue
        try:
            import json
            if json.loads(meta.read_text(encoding='utf8')).get('schema') == 'rainy75-px/2':
                out.append(path)
        except Exception:  # noqa: BLE001 - broken dirs are reported by the verifier
            continue
    return out


@unittest.skipIf(PS is None, 'toolkit deps unavailable: %s' % IMPORT_ERROR)
class ToolkitTests(unittest.TestCase):
    def test_packbits_roundtrip(self):
        for data in (b'', b'\x00', b'\x00' * 300, bytes(range(256)),
                     b'\xff' * 200 + b'\x00' * 50 + b'\x01\x02\x03'):
            encoded = PS.packbits_encode(data)
            self.assertEqual(PS.packbits_decode(encoded), data)
            self.assertLessEqual(len(encoded), len(data) + len(data) // 128 + 1)

    def test_budget_constants(self):
        self.assertLessEqual(PS.ENCODED_BUDGET, 1200,
                            'flash mask budget must stay within the verified 1200 B')
        self.assertLessEqual(PS.MASK_RAM_BUDGET, 2560,
                            'decoded masks must fit the 4 KiB module state')
        self.assertEqual(PS.FRAMES, ('calm', 'caps', 'react', 'sleepy'))

    def test_family_scripts_present(self):
        for name in FAMILY_SCRIPTS:
            path = ROOT / 'tools/schemes' / name
            self.assertTrue(path.is_file(), '%s missing' % name)
            text = path.read_text(encoding='utf8')
            self.assertIn('def main', text, '%s has no main()' % name)
            self.assertIn('import pixel_scheme', text.replace('from pixel_scheme', 'import pixel_scheme'))


@unittest.skipIf(PS is None, 'toolkit deps unavailable: %s' % IMPORT_ERROR)
class GeneratedSchemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dirs = v2_dirs()
        if not cls.dirs:
            raise unittest.SkipTest(
                'no generated schemes; run `python tools/schemes/px6_*.py` first')

    def test_every_scheme_passes_verifier(self):
        failures = []
        for path in self.dirs:
            try:
                slug, problems, _meta = VS.check(path)
            except VS.NotV2:
                continue
            except Exception as exc:  # noqa: BLE001
                failures.append('%s: exception %s' % (path.name, exc))
                continue
            if problems:
                failures.append('%s: %s' % (slug, '; '.join(problems)))
        self.assertFalse(failures, '\n'.join(failures))

    def test_family_counts_and_total(self):
        counts = {}
        slugs = set()
        for path in self.dirs:
            meta = PS.load_scheme(path)
            slug = meta.get('slug')
            self.assertNotIn(slug, slugs, 'duplicate slug %s' % slug)
            slugs.add(slug)
            family = (meta.get('emotion') or {}).get('family')
            counts[family] = counts.get(family, 0) + 1
        self.assertGreaterEqual(len(slugs), 50, 'expected at least 50 v2 schemes')
        for family, expected in EXPECTED_PER_FAMILY.items():
            self.assertGreaterEqual(counts.get(family, 0), expected,
                                    'family %s has %d, expected %d'
                                    % (family, counts.get(family, 0), expected))

    def test_effect_and_frame_metadata(self):
        for path in self.dirs:
            meta = PS.load_scheme(path)
            self.assertEqual(meta['schema'], 'rainy75-px/2')
            self.assertEqual([f['id'] for f in meta['frames']],
                             list(PS.FRAMES))
            self.assertTrue(meta['masks']['encodedBytes'] <= PS.ENCODED_BUDGET)
            self.assertTrue(meta['masks']['decodedBytes'] <= PS.MASK_RAM_BUDGET)
            self.assertIn((meta.get('effect') or {}).get('mode'), PS.EFFECT_PRESETS)
            self.assertTrue(1 <= len(meta['layers']) <= PS.MAX_LAYERS)
            for layer in meta['layers']:
                self.assertEqual(len(layer['fg']), 4)
                self.assertEqual(len(layer['bg']), 4)
                self.assertEqual(len(layer['off']), 4)


if __name__ == '__main__':
    unittest.main()
