# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import unittest

from tests.helpers import ROOT, load_tool

fp = load_tool("fm_patch.py")


class FmPatchTest(unittest.TestCase):
    """Requirements: R-FM-7, R-ARP-7"""

    def test_patches_c_is_what_the_tool_writes(self):
        with open(os.path.join(ROOT, "firmware", "src", "patches.c")) as f:
            self.assertEqual(f.read(), fp.source())

    def test_every_test_patch_is_valid_and_its_own_length(self):
        with open(os.path.join(ROOT, "firmware", "src", "fm.h")) as f:
            header = f.read()
        self.assertIn("#define FM_PATCHES    %du" % len(fp.TEST_PATCHES), header)
        for p in fp.TEST_PATCHES:
            b = fp.encode(p)
            self.assertEqual(len(b), fp.BYTES)
            self.assertEqual(fp.problems(b), [], p["name"])

    def test_damage_is_refused(self):
        good = bytearray(fp.encode(fp.TEST_PATCHES[1]))
        for at, value in ((0, ord("X")), (2, 3), (2, 1), (3, 111), (16, 0), (16, 11), (17, 8), (18, 2),
                          (29, 0x80), (29, 6 << 2), (30, 10), (31, 9), (31, 101),
                          (fp.OP_OFFSET, 2), (fp.OP_OFFSET + 4, 128), (fp.OP_OFFSET + 5, 8)):
            b = bytearray(good)
            b[at] = value
            s = fp.fletcher16(b[:fp.SUM_OFFSET])
            b[fp.SUM_OFFSET], b[fp.SUM_OFFSET + 1] = s & 0xFF, s >> 8
            self.assertTrue(fp.problems(bytes(b)), (at, value))
        b = bytearray(good)
        b[20] ^= 1                       # a changed byte, the sum left as it was
        self.assertEqual(fp.problems(bytes(b)), ["check sum"])
        self.assertTrue(fp.problems(bytes(good[:100])))

    def test_version_1_upgrades_with_the_arpeggiators_defaults(self):
        """Since ARP (version 2): a version 1 patch (bytes 29 to 31 zero)
        reads as version 2 with the defaults, as fm_patch_upgrade() does."""
        v2 = fp.encode(fp.TEST_PATCHES[4])
        v1 = bytearray(v2)
        v1[2], v1[29:32] = 1, b"\0\0\0"
        s = fp.fletcher16(v1[:fp.SUM_OFFSET])
        v1[fp.SUM_OFFSET], v1[fp.SUM_OFFSET + 1] = s & 0xFF, s >> 8
        self.assertTrue(fp.problems(bytes(v1)))
        self.assertEqual(fp.upgrade(bytes(v1)), v2)
        self.assertEqual(fp.upgrade(v2), v2)
        self.assertEqual(fp.arp_of(v2), fp.ARP_DEFAULT)
        self.assertEqual(v2[29:32], bytes([0, 7, 50]))
        bad = bytearray(v1)
        bad[29] = 1                      # a version 1 patch with a reserved byte set
        self.assertIsNone(fp.upgrade(bytes(bad)))
        src = open(os.path.join(ROOT, "firmware", "src", "fm_play.c")).read()
        self.assertIn("b[FMP_ARP_RATE] = ARP_RATE_DEFAULT;", src)
        self.assertIn("b[FMP_ARP_GATE] = ARP_GATE_DEFAULT;", src)
        h = open(os.path.join(ROOT, "firmware", "src", "arp.h")).read()
        self.assertIn("#define ARP_RATE_DEFAULT %du" % fp.ARP_DEFAULT["rate"], h)
        self.assertIn("#define ARP_GATE_DEFAULT %du" % fp.ARP_DEFAULT["gate"], h)

    def test_arpeggiator_settings_round_trip(self):
        for a in (fp.arp(on=True, latch=True, mode=5, octaves=4, rate=9, swing=75, gate=100),
                  fp.arp(mode=3, octaves=2, rate=0, swing=5, gate=10)):
            b = fp.encode(fp.patch("Arp", 8, [fp.op(1.0, 127)], arp_settings=a))
            self.assertEqual(fp.problems(b), [])
            self.assertEqual(fp.arp_of(b), a)

    def test_fletcher16(self):
        # Known values: "abcde" is 0xC8F0, "abcdef" 0x2057.
        self.assertEqual(fp.fletcher16(b"abcde"), 0xC8F0)
        self.assertEqual(fp.fletcher16(b"abcdef"), 0x2057)

    def test_units(self):
        self.assertAlmostEqual(fp.time_ms(0), 1.0)
        self.assertAlmostEqual(fp.time_ms(40), 32.0)
        self.assertAlmostEqual(fp.level_gain(127), 1.0)
        self.assertAlmostEqual(fp.level_gain(103), 0.125)
        self.assertEqual(fp.level_gain(0), 0.0)


class PresetBankTest(unittest.TestCase):
    """Requirements: R-PRESET-1"""

    def test_sixty_four_presets_eight_of_each_category(self):
        self.assertEqual(len(fp.PRESETS), 64)
        for c in range(len(fp.CATEGORIES)):
            self.assertEqual(sum(1 for cat, _, _ in fp.PRESETS if cat == c), 8, fp.CATEGORIES[c])

    def test_every_preset_is_valid_named_once_and_says_what_it_is_for(self):
        with open(os.path.join(ROOT, "firmware", "src", "fm.h")) as f:
            header = f.read()
        self.assertIn("#define FM_PRESETS    %du" % len(fp.PRESETS), header)
        names = [p["name"] for _, _, p in fp.PRESETS]
        self.assertEqual(len(set(names)), len(names))
        for _, purpose, p in fp.PRESETS:
            self.assertEqual(fp.problems(fp.encode(p)), [], p["name"])
            self.assertTrue(purpose.strip(), p["name"])


if __name__ == "__main__":
    unittest.main()
