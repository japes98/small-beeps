# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import struct
import unittest

from tests.helpers import load_tool

fw = load_tool("fw-suite.py")


def beacon(marker=fw.MARKER, beats=0, ticks=0, period=fw.TICKS_PER_MS):
    return struct.pack("<4I", marker, beats, ticks, period)


class FwSuiteCheckTest(unittest.TestCase):
    """Requirements: R-BOOT-1, R-BOOT-2, R-BOOT-3, R-BOOT-4"""

    def test_good_beacons_pass(self):
        self.assertEqual(fw.check_beacon(10, beacon(beats=11, ticks=269624)), [])
        self.assertEqual(fw.check_beacon(10, beacon(beats=9, ticks=240000 - 100)), [])
        self.assertEqual(fw.check_beacon(1000, beacon(beats=1000, ticks=24016282), 1000.678), [])

    def test_wrong_marker_or_period_fails(self):
        self.assertTrue(fw.check_beacon(10, beacon(marker=0x21444142, beats=10, ticks=240000)))
        self.assertTrue(fw.check_beacon(10, beacon(beats=10, ticks=240000, period=1000)))

    def test_beats_must_match_the_time_base(self):
        self.assertTrue(fw.check_beacon(10, beacon(beats=9, ticks=240000)))
        self.assertTrue(fw.check_beacon(10, beacon(beats=11, ticks=240000)))

    def test_capture_time_bounds(self):
        early = 240000 - fw.START_SLACK - 1
        late = (10 + fw.LATE_MS) * fw.TICKS_PER_MS + 1
        self.assertTrue(fw.check_beacon(10, beacon(beats=early // 24000, ticks=early)))
        self.assertTrue(fw.check_beacon(10, beacon(beats=late // 24000, ticks=late)))

    def test_end_must_agree_with_emulated_time(self):
        ticks = 24016272 + fw.START_SLACK + 1
        self.assertTrue(fw.check_beacon(1000, beacon(beats=ticks // 24000, ticks=ticks), 1000.678))

    def test_case_problems(self):
        good = {"run": {"outcome": "completed", "unmodelled_accesses": [],
                        "instructions": {"core0": 5, "core1": 0}}}
        self.assertEqual(fw.check_case("x", good), [])
        for run in ({"outcome": "halt"}, {"outcome": "fault"}, {"outcome": "hang"},
                    {"unmodelled_accesses": [{"address": "0x1"}]},
                    {"instructions": {"core0": 5, "core1": 3}}):
            bad = {"run": dict(good["run"], **run)}
            self.assertTrue(fw.check_case("x", bad), run)


if __name__ == "__main__":
    unittest.main()
