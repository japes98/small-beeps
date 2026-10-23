# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import random
import re
import struct
import unittest
from fractions import Fraction

from tests.helpers import ROOT, load_tool

pb = load_tool("plaits-bench.py")


def f32(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class ReferenceTest(unittest.TestCase):
    """Requirements: R-PLAITS-2"""

    def test_rounding_matches_the_hosts_float(self):
        # struct packs a double to the nearest float, ties to even; every
        # value here is in range, so it is an independent reference.
        rnd = random.Random(7)
        for _ in range(3000):
            x = rnd.uniform(-1, 1) * 2.0 ** rnd.randint(-140, 120)
            self.assertEqual(pb.round32(Fraction(x)), f32(x), x)

    def test_ties_subnormals_and_overflow(self):
        one = Fraction(1)
        ulp = Fraction(1, 1 << 23)
        self.assertEqual(pb.round32(one + ulp / 2), 0x3F800000)        # tie: to even
        self.assertEqual(pb.round32(one + 3 * ulp / 2), 0x3F800002)    # tie: to even
        self.assertEqual(pb.round32(Fraction(1, 1 << 149)), 1)         # smallest subnormal
        self.assertEqual(pb.round32(Fraction(1, 1 << 150)), 0)         # half of it: to even, 0
        self.assertEqual(pb.round32(-Fraction(3, 1 << 151)), 0x80000001)
        self.assertEqual(pb.round32(Fraction(2) ** 128), 0x7F800000)
        biggest = Fraction(2) ** 127 * (2 - ulp)
        self.assertEqual(pb.round32(biggest), 0x7F7FFFFF)
        self.assertEqual(pb.round32(biggest + Fraction(2) ** 103), 0x7F800000)   # rounds up to inf

    def test_operations(self):
        self.assertEqual(pb.ref_add(f32(1.0), f32(2.0)), f32(3.0))
        self.assertEqual(pb.ref_add(f32(1.0), f32(1.0), sub=True), 0)
        self.assertEqual(pb.ref_add(0x80000000, 0x80000000), 0x80000000)   # -0 + -0
        self.assertEqual(pb.ref_add(0x7F800000, 0xFF800000), pb.QNAN)
        self.assertEqual(pb.ref_mul(0x7F7FFFFF, f32(2.0)), 0x7F800000)
        self.assertEqual(pb.ref_mul(0x7F800000, 0), pb.QNAN)
        self.assertEqual(pb.ref_div(0, 0), pb.QNAN)
        self.assertEqual(pb.ref_div(f32(1.0), 0x80000000), 0xFF800000)
        self.assertEqual(pb.ref_div(f32(1.0), f32(3.0)), f32(1.0 / 3.0))
        self.assertEqual(pb.ref_sqrt(f32(2.0)), f32(2.0 ** 0.5))
        self.assertEqual(pb.ref_sqrt(0x80000000), 0x80000000)
        self.assertEqual(pb.ref_sqrt(f32(-1.0)), pb.QNAN)
        self.assertEqual(pb.ref_sqrt(1), f32(2.0 ** -74.5))
        self.assertEqual(pb.ref_i2f(0x80000000, True), 0xCF000000)
        self.assertEqual(pb.ref_i2f(0xFFFFFFFF, False), 0x4F800000)
        self.assertEqual(pb.ref_f2i(f32(-2.5), True), (-2) & 0xFFFFFFFF)
        self.assertEqual(pb.ref_f2i(0x7F800000, True), 0x7FFFFFFF)
        self.assertEqual(pb.ref_f2i(pb.QNAN, True), 0)
        self.assertEqual(pb.ref_f2i(f32(-1.0), False), 0)
        self.assertIsNone(pb.ref_cmp(pb.QNAN, 0))
        self.assertEqual(pb.ref_cmp(0x80000000, 0)[0], pb.ref_cmp(0x80000000, 0)[1])   # -0 == +0

    def test_the_operands_match_the_image(self):
        # The C generator in sftest.c and the Python one in plaits-bench.py
        # must give the same pairs: the specials, then the four kinds.
        with open(os.path.join(ROOT, "firmware", "demos", "plaits", "sftest.c")) as f:
            src = f.read()
        self.assertIn("seed = seed * 1664525u + 1013904223u;", src)
        self.assertIn("static u32 seed = 0x5EEDF10Au;", src)
        special = [int(x, 16) for x in re.findall(r"0x([0-9A-F]{8})u", src.split("special[] = {")[1].split("};")[0])]
        self.assertEqual(special, pb.SPECIAL)
        self.assertIn("#define CASES  %du" % pb.CASES, src)
        pairs = list(pb.operands())
        self.assertEqual(len(pairs), pb.CASES)
        self.assertEqual(pairs[0], (0, 0))
        self.assertEqual(pairs[len(pb.SPECIAL)], (0x80000000, 0))


class BenchParseTest(unittest.TestCase):
    """Requirements: R-PLAITS-3, R-PLAITS-4"""

    CONSOLE = ("small-beeps M4 \nPLAITS-BENCH 00000001 00000018 00000009 00000004 00000040 00000010 00000000\n"
               "E 00000000 000c0350 000f5898 000ea7a1 9e91c54d 00000000 000068f8   \n"
               "FLAGS 00000000 00000000 00000000   \nCORE1 00000001 \n"
               "D 00000000 001b581e 000ed670   \nEND\n")

    def test_parse(self):
        b = pb.parse_bench(self.CONSOLE)
        self.assertEqual((b["count"], b["points"], b["blocks"], b["hwfloat"]), (24, 9, 4, 0))
        self.assertEqual(b["engines"][0], {"set_up": 0xC0350, "max": 0xF5898, "mean": 0xEA7A1,
                                           "checksum": "9e91c54d", "clipped": 0, "peak": 0x68F8})
        self.assertEqual(b["flags"], {"invalid": 0, "overflow": 0, "convert": 0})
        self.assertTrue(b["core1"] and b["end"])
        self.assertEqual(b["dual"], [{"engine": 0, "apart": 0x1B581E, "both": 0xED670}])

    def test_the_engine_list_is_plaits_order(self):
        with open(os.path.join(ROOT, "vendor", "plaits", "eurorack", "plaits", "dsp", "voice.cc")) as f:
            order = re.findall(r"RegisterInstance\(&(\w+)_engine_", f.read())
        self.assertEqual(len(order), len(pb.ENGINES))
        short = {"virtual_analog_vcf": "virtual analog VCF", "six_op": "six-op FM", "hi_hat": "hi-hat",
                 "bass_drum": "bass drum", "snare_drum": "snare drum"}
        for code, name in zip(order, pb.ENGINES):
            want = short.get(code, code.replace("_", " "))
            self.assertTrue(name.lower().startswith(want.lower()) or (code == "chord" and name == "chords"), (code, name))

    def test_platform_costs_fall_back(self):
        self.assertEqual(pb.platform_costs("/nonexistent")[:2], (1812.939, None))


class DemoSourceTest(unittest.TestCase):
    """Requirements: R-PLAITS-1"""

    def test_the_demo_is_compiled_only_into_its_own_image(self):
        # main.c's hooks are under SB_DEMO_PLAITS, which only
        # tools/build.sh --demo plaits defines; the firmware's own sources
        # never name the demo otherwise.
        with open(os.path.join(ROOT, "firmware", "src", "main.c")) as f:
            text = f.read()
        guard = []
        for line in text.splitlines():
            m = re.match(r"#(?:el)?if (.*)", line)
            if line.startswith("#if"):
                guard.append(m.group(1))
            elif line.startswith("#elif") and guard:
                guard[-1] = m.group(1)
            elif line.startswith("#endif") and guard:
                guard.pop()
            elif "plaits" in line:
                self.assertTrue(any("SB_DEMO_PLAITS" in g for g in guard), line)
        with open(os.path.join(ROOT, "tools", "build.sh")) as f:
            build = f.read()
        self.assertIn('CFLAGS="$CFLAGS -DSB_DEMO_PLAITS', build)
        self.assertRegex(build, r'if \[ -n "\$\{SB_DEMO:-\}" \]; then\s+CFLAGS="\$CFLAGS -DSB_DEMO_PLAITS')


if __name__ == "__main__":
    unittest.main()
