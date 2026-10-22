# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import shutil
import struct
import tempfile
import unittest

from tests.helpers import load_tool

fw = load_tool("fw-suite.py")


def beacon(**kw):
    """A beacon dict as fw-suite reads it; a consistent heartbeat by default."""
    b = dict.fromkeys(fw.BEACON_FIELDS, 0)
    b.update(marker=fw.MARKER, period=fw.TICKS_PER_MS)
    ticks = kw.pop("ticks", 0)
    beats = kw.pop("beats", ticks // fw.TICKS_PER_MS)
    b.update(beats=beats, ticks=ticks, beats_b=beats, ticks_b=ticks)
    b.update(kw)
    return b


def packed(b):
    return struct.pack("<%dI" % len(fw.BEACON_FIELDS), *[b[k] for k in fw.BEACON_FIELDS])


class FwSuiteCheckTest(unittest.TestCase):
    """Requirements: R-BOOT-1, R-BOOT-2, R-BOOT-3, R-BOOT-4, R-IRQ-1, R-IRQ-2"""

    def test_good_beacons_pass(self):
        self.assertEqual(fw.check_beacon(10, beacon(ticks=264030, seq=22)), [])
        self.assertEqual(fw.check_beacon(10, beacon(ticks=9 * 24000 + 100, seq=18)), [])
        self.assertEqual(fw.check_beacon(1000, beacon(ticks=24016282, seq=2000), 1000.678), [])

    def test_wrong_marker_or_period_fails(self):
        self.assertTrue(fw.check_beacon(10, beacon(marker=0x21444142, ticks=240000)))
        self.assertTrue(fw.check_beacon(10, beacon(ticks=240000, period=1000)))

    def test_beats_must_match_the_time_base(self):
        self.assertTrue(fw.check_beacon(10, beacon(ticks=240000, beats=9)))
        self.assertTrue(fw.check_beacon(10, beacon(ticks=240000, beats=11)))

    def test_a_capture_mid_update_needs_one_consistent_copy(self):
        # copy a written, copy b not yet: b still holds the last tick's pair
        mid = beacon(ticks=264030, seq=23, beats_b=10, ticks_b=240029)
        self.assertEqual(fw.check_beacon(10, mid), [])
        # beats written but not ticks, in both copies: nothing to trust
        torn = beacon(ticks=240029, beats=11, beats_b=11, ticks_b=240029, seq=23)
        self.assertTrue(any("neither" in p for p in fw.check_beacon(10, torn)))
        # with seq even both copies must agree
        self.assertTrue(fw.check_beacon(10, dict(mid, seq=24)))

    def test_capture_time_bounds(self):
        early = 9 * fw.TICKS_PER_MS - fw.INTERVAL_TOL - fw.START_SLACK - 1
        late = (10 + fw.LATE_MS) * fw.TICKS_PER_MS + 1
        self.assertTrue(fw.check_beacon(10, beacon(ticks=early)))
        self.assertTrue(fw.check_beacon(10, beacon(ticks=late)))

    def test_end_must_follow_the_last_tick_within_a_period(self):
        end = round(1000.678 * fw.TICKS_PER_MS)
        self.assertEqual(fw.check_beacon(1000, beacon(ticks=end - 24001), 1000.678), [])
        self.assertTrue(fw.check_beacon(1000, beacon(ticks=end - 2 * 24001), 1000.678))
        self.assertTrue(fw.check_beacon(1000, beacon(ticks=end + fw.START_SLACK + 1), 1000.678))

    def test_tick_statistics(self):
        result = {"run": {"instructions": {"core0": 69641}}}
        good = beacon(ticks=24169514, tick_count=1007, interval_min=24001, interval_max=24001,
                      wakes=1006)
        self.assertEqual(fw.check_ticks(good, result)[0], [])
        for bad in (dict(good, interval_max=24000 + fw.INTERVAL_TOL + 1),
                    dict(good, interval_min=24000 - fw.INTERVAL_TOL - 1),
                    dict(good, interval_min=23990, interval_max=24020),   # jitter 30
                    dict(good, wakes=500),                               # not idling per tick
                    dict(good, tick_count=900)):                         # ticks and beats apart
            self.assertTrue(fw.check_ticks(bad, result)[0], bad)
        busy = {"run": {"instructions": {"core0": 1007 * (fw.IDLE_MAX_IPT + 1)}}}
        self.assertTrue(fw.check_ticks(good, busy)[0])

    def test_case_problems(self):
        good = {"run": {"outcome": "completed", "unmodelled_accesses": [],
                        "instructions": {"core0": 5, "core1": 0}}}
        self.assertEqual(fw.check_case("boot", good), [])
        for run in ({"outcome": "halt"}, {"outcome": "fault"}, {"outcome": "hang"},
                    {"unmodelled_accesses": [{"address": "0x1"}]},
                    {"instructions": {"core0": 5, "core1": 3}}):
            bad = {"run": dict(good["run"], **run)}
            self.assertTrue(fw.check_case("boot", bad), run)
        halted = {"run": dict(good["run"], outcome="halt")}
        self.assertEqual(fw.check_case("stray", halted), [])
        self.assertTrue(fw.check_case("stray", good))
        self.assertEqual(fw.check_case("badinsn", {"run": dict(good["run"], outcome="fault")}), [])


class FwSuiteBootTest(unittest.TestCase):
    """Requirements: R-BOOT-5, R-CLK-1, R-IRQ-1, R-IRQ-2, R-IRQ-3, R-IRQ-4"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.syms = {"sb_irq_stubs": 0x0200004C, "sb_tick": 0x020002BC}

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, b, table=None):
        with open(os.path.join(self.dir, "ram-01c00000-%x-end.bin" % fw.BEACON_LEN), "wb") as f:
            f.write(packed(b))
        if table is None:
            table = [self.syms["sb_irq_stubs"] + 2 * n for n in range(128)]
            table[4] = self.syms["sb_tick"]
        with open(os.path.join(self.dir, fw.VECTORS), "wb") as f:
            f.write(struct.pack("<128I", *table))
        return table

    def boot(self, **kw):
        b = beacon(ticks=360522, tick_count=15, interval_min=24001, interval_max=24001, clock=241)
        b.update(kw)
        return b

    def test_a_good_boot_passes(self):
        self.write(self.boot())
        self.assertEqual(fw.check_boot(self.dir, self.syms)[0], [])

    def test_clock_must_be_240_mhz(self):
        for clock in (120, 239, 242, 480):
            self.write(self.boot(clock=clock))
            self.assertTrue(fw.check_boot(self.dir, self.syms)[0], clock)

    def test_first_tick_must_come_soon(self):
        self.write(self.boot(tick_count=0))
        self.assertTrue(fw.check_boot(self.dir, self.syms)[0])
        self.write(self.boot(tick_count=12))     # first tick by 96 509 ticks: 4 ms
        self.assertTrue(fw.check_boot(self.dir, self.syms)[0])

    def test_every_vector_slot_is_checked(self):
        table = self.write(self.boot())
        for n in (0, 4, 126, 127):
            bad = list(table)
            bad[n] += 2
            self.write(self.boot(), bad)
            self.assertTrue(fw.check_boot(self.dir, self.syms)[0], n)

    def test_halts_are_told_apart(self):
        self.write(beacon(halt_reason=fw.HALT_STRAY, halt_source=127))
        self.assertEqual(fw.check_halt("stray", self.dir, fw.HALT_STRAY, 127)[0], [])
        self.assertTrue(fw.check_halt("stray", self.dir, fw.HALT_STRAY, 126)[0])
        self.assertTrue(fw.check_halt("fault", self.dir, fw.HALT_STACK, 1)[0])


if __name__ == "__main__":
    unittest.main()
