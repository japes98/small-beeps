# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
import unittest

from tests.helpers import ROOT, load_tool

am = load_tool("arp_model.py")
fp = load_tool("fm_patch.py")


def settings(**kw):
    return dict(fp.ARP_DEFAULT, on=True, **kw)


class ArpModelTest(unittest.TestCase):
    """Requirements: R-ARP-1, R-ARP-2"""

    def test_each_modes_order_by_hand(self):
        held = [67, 60, 64]                      # G4, C4, E4, as they came
        seq = lambda **kw: [s[0] for s in am.sequence(held, settings(**kw), 8)]
        self.assertEqual(seq(mode=am.UP), [60, 64, 67, 60, 64, 67, 60, 64])
        self.assertEqual(seq(mode=am.UP, octaves=2), [60, 64, 67, 72, 76, 79, 60, 64])
        self.assertEqual(seq(mode=am.DOWN), [67, 64, 60, 67, 64, 60, 67, 64])
        self.assertEqual(seq(mode=am.UPDOWN), [60, 64, 67, 64, 60, 64, 67, 64])
        self.assertEqual(seq(mode=am.ORDER), [67, 60, 64, 67, 60, 64, 67, 60])
        self.assertEqual(am.sequence(held, settings(mode=am.CHORD, octaves=2), 3),
                         [[60, 64, 67], [72, 76, 79], [60, 64, 67]])
        self.assertEqual(am.sequence([60], settings(mode=am.UPDOWN), 3), [[60], [60], [60]])

    def test_random_is_the_fixed_generator(self):
        # x = 1664525 x + 1013904223 from 1: 1015568748, 1586005467, ...
        r = am.Random()
        self.assertEqual([r.next() for _ in range(2)], [1015568748, 1586005467])
        held = [60, 64, 67]
        self.assertEqual([s[0] for s in am.sequence(held, settings(mode=am.RANDOM), 2)],
                         [held[(1015568748 >> 8) % 3], held[(1586005467 >> 8) % 3]])

    def test_notes_above_127_play_octaves_lower(self):
        self.assertEqual(am.sequence([120], settings(octaves=3), 3), [[120], [120], [120]])

    def test_the_clock_is_exact(self):
        # 1/16 at 120: 6 pulses, 125 ms, 5514.705... frames: never drifts.
        a = settings()
        self.assertEqual(am.step_frames(a, 5, 120), [0, 5515, 11030, 16545, 22059])
        k = 480                                   # a minute
        self.assertEqual(am.step_frames(a, k + 1, 120)[k], -(-k * 6 * am.UNIT // (34 * 120)))
        self.assertAlmostEqual(am.ideal_ms(a, 8, 120), 1000.0)
        self.assertEqual(am.RATE_PULSES, (48, 36, 24, 18, 12, 8, 9, 6, 4, 3))

    def test_a_step_at_the_end_of_a_block_plays_at_its_last_frame(self):
        # 63.5 frames in: block 0, frame 63 (not 64).
        r = 34 * 120
        self.assertEqual(am.frame_of(int(63.5 * r), 120), 63)
        self.assertEqual(am.frame_of(64 * r, 120), 64)
        self.assertEqual(am.frame_of(64 * r + 1, 120), 65)

    def test_swing_and_gate(self):
        a = settings(rate=4, swing=50, gate=30)   # 1/8: 12 pulses
        self.assertEqual(am.step_units(a, 1) - am.step_units(a, 0), 18 * am.UNIT)
        self.assertEqual(am.step_units(a, 2), 24 * am.UNIT)
        self.assertEqual(am.gate_units(a), 12 * am.UNIT * 30 // 100)
        full = settings(gate=100)
        self.assertEqual(am.off_frames(full, 3, 120), am.step_frames(full, 4, 120)[1:])

    def test_the_model_matches_the_firmware(self):
        """The constants the model shares with firmware/src/arp.c."""
        with open(os.path.join(ROOT, "firmware", "src", "arp.c")) as f:
            c = f.read()
        with open(os.path.join(ROOT, "firmware", "src", "arp.h")) as f:
            h = f.read()
        self.assertIn("{ %s }" % ", ".join(str(p) for p in am.RATE_PULSES), c)
        self.assertIn("rng = rng * 1664525u + 1013904223u;", c)
        self.assertIn("#define RANDOM_SEED %du" % am.RANDOM_SEED, c)
        self.assertIn("#define ARP_UNIT         %du" % am.UNIT, h)
        self.assertIn("#define ARP_UNIT_FRAME   %du" % am.UNIT_FRAME, h)
        self.assertRegex(h, r"enum \{ ARP_UP, ARP_DOWN, ARP_UPDOWN, ARP_ORDER, ARP_RANDOM, ARP_CHORD, ARP_MODES \}")
        self.assertEqual(len(fp.ARP_MODES), 6)
        self.assertTrue(re.search(r"34 t", h))


if __name__ == "__main__":
    unittest.main()
