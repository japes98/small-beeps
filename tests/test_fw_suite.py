# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import shutil
import struct
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

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
        # main's loop began at tick 502 and stored 498 wakes at tick 1000
        good = beacon(ticks=24169514, tick_count=1007, interval_min=24001, interval_max=24001,
                      wakes=498, loop_ticks=502, wakes_ticks=1000)
        self.assertEqual(fw.check_ticks(good, result)[0], [])
        self.assertEqual(fw.check_ticks(dict(good, wakes=499), result)[0], [])   # within one
        for bad in (dict(good, interval_max=24000 + fw.INTERVAL_TOL + 1),
                    dict(good, interval_min=24000 - fw.INTERVAL_TOL - 1),
                    dict(good, interval_min=23990, interval_max=24020),   # jitter 30
                    dict(good, wakes=200),                               # not idling per tick
                    dict(good, wakes=14 * 499),                          # more than one an interrupt
                    dict(good, wakes_ticks=0),                           # never stored
                    dict(good, tick_count=900)):                         # ticks and beats apart
            self.assertTrue(fw.check_ticks(bad, result)[0], bad)

    def test_steady_state_instructions_a_tick(self):
        def run(i):
            return {"run": {"instructions": {"core0": i}}}
        ok, lines = fw.check_steady([run(1116418), run(1181964)],
                                    [beacon(tick_count=1251), beacon(tick_count=2253)])
        self.assertEqual(ok, [])
        self.assertIn("65.415", lines[0])
        busy, _ = fw.check_steady([run(1000000), run(1000000 + 1002 * (fw.IDLE_MAX_IPT + 1))],
                                  [beacon(tick_count=1251), beacon(tick_count=2253)])
        self.assertTrue(busy)
        self.assertTrue(fw.check_steady([run(1), run(2)], [beacon(tick_count=5), beacon(tick_count=5)])[0])

    def test_start_slack_grows_with_what_startup_clears(self):
        self.assertEqual(fw.start_slack(0), 240)
        # M2's 115 336 bytes of bss: 28 834 words, 3 cycles each at most
        self.assertEqual(fw.start_slack(115336), 240 + 8651)

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
        self.syms = {"sb_irq_stubs": 0x0200004C, "sb_tick": 0x020002BC, "lcd_spi_done": 0x0200060E,
                     "input_scan": 0x0200047E}

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, b, table=None):
        with open(os.path.join(self.dir, "ram-01c00000-%x-end.bin" % fw.BEACON_LEN), "wb") as f:
            f.write(packed(b))
        if table is None:
            table = [self.syms["sb_irq_stubs"] + 2 * n for n in range(128)]
            table[4] = self.syms["sb_tick"]
            table[16] = self.syms["lcd_spi_done"]
            table[5] = self.syms["input_scan"]
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
        for n in (0, 4, 5, 16, 126, 127):
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


def png(rows, filters=(0,)):
    """An 8-bit RGB PNG of rows of (r, g, b), each row stored with the next
    filter type in turn (0 none, 1 sub, 2 up, 3 average, 4 Paeth)."""
    import zlib
    w, raw, prev = len(rows[0]), b"", bytes(len(rows[0]) * 3)
    for y, row in enumerate(rows):
        line = bytes(c for px in row for c in px)
        kind, out = filters[y % len(filters)], bytearray()
        for i, v in enumerate(line):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if kind == 1:
                v -= a
            elif kind == 2:
                v -= b
            elif kind == 3:
                v -= (a + b) // 2
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                v -= a if pa <= pb and pa <= pc else b if pb <= pc else c
            out.append(v & 255)
        raw += bytes([kind]) + bytes(out)
        prev = line

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, len(rows), 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def pattern():
    return [[fw.rgb8(x >> 3, y >> 2, (x & 7) << 2 | (y & 3)) for x in range(240)] for y in range(240)]


def test_screen():
    """The test screen's checked parts, on black (screen.c)."""
    rows = [[(0, 0, 0)] * 240 for _ in range(240)]
    for y in range(240):
        for x in range(240):
            if x in (0, 239) or y in (0, 239):
                rows[y][x] = fw.WHITE
    for (x0, y0), colour in fw.CORNERS:
        for y in range(y0, y0 + 12):
            for x in range(x0, x0 + 12):
                rows[y][x] = colour
    for y0, steps, width, colour in ((44, 32, 6, lambda i: fw.rgb8(i, 0, 0)), (60, 64, 3, lambda i: fw.rgb8(0, i, 0)),
                                     (76, 32, 6, lambda i: fw.rgb8(0, 0, i))):
        for i in range(steps):
            for x in range(24 + width * i, 24 + width * (i + 1)):
                for y in range(y0, y0 + 14):
                    rows[y][x] = colour(i)
    return rows


class FwSuiteScreenTest(unittest.TestCase):
    """Requirements: R-LCD-2, R-LCD-3, R-LCD-4"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_png_reader_undoes_every_filter(self):
        rows = [[((x * 7 + y) & 255, (x * y) & 255, (255 - x - y) & 255) for x in range(9)] for y in range(10)]
        path = os.path.join(self.dir, "t.png")
        with open(path, "wb") as f:
            f.write(png(rows, filters=(0, 1, 2, 3, 4)))
        self.assertEqual(fw.read_png(path), (9, 10, rows))

    def test_colours_scale_as_fwtest_writes_them(self):
        self.assertEqual(fw.rgb8(31, 63, 31), (255, 255, 255))
        self.assertEqual(fw.rgb8(1, 1, 1), (8, 4, 8))

    def test_the_address_pattern_is_checked_pixel_by_pixel(self):
        rows = pattern()
        self.assertEqual(fw.check_pattern(rows), [])
        rows[100][37] = rows[100][38]           # one pixel in the wrong place
        self.assertIn("(37, 100)", fw.check_pattern(rows)[0])
        flipped = [row[::-1] for row in pattern()]
        self.assertTrue(fw.check_pattern(flipped))
        swapped = [[(b, g, r) for r, g, b in row] for row in pattern()]
        self.assertTrue(fw.check_pattern(swapped))

    def test_the_test_screen_shows_orientation_colour_order_and_edges(self):
        rows = test_screen()
        self.assertEqual(fw.check_test_screen(rows), [])
        for broken in ([row[::-1] for row in rows],                       # mirrored
                       rows[::-1],                                        # upside down
                       [[(b, g, r) for r, g, b in row] for row in rows]):  # BGR
            self.assertTrue(fw.check_test_screen(broken))
        missing_edge = [list(r) for r in rows]
        missing_edge[239][120] = (0, 0, 0)
        self.assertTrue(any("edge" in p for p in fw.check_test_screen(missing_edge)))


class FwSuiteInputTest(unittest.TestCase):
    """Requirements: R-INPUT-1, R-KEY-2, R-ENC-2, R-POT-2"""

    def record(self, events, **head):
        h = dict.fromkeys(fw.INPUT_FIELDS, 0)
        h.update(head, events=len(events))
        data = struct.pack("<%dI" % len(fw.INPUT_FIELDS), *[h[k] for k in fw.INPUT_FIELDS])
        data += struct.pack("<%di" % fw.INPUT_VALUES, *range(fw.INPUT_VALUES))
        log = [b"\0" * 8] * fw.INPUT_LOG
        for seq, e in enumerate(events):
            log[seq % fw.INPUT_LOG] = struct.pack("<BBhI", *e)
        return data + b"".join(log)

    def test_the_record_layout(self):
        self.assertEqual(len(self.record([])), fw.INPUT_LEN)
        path = os.path.join(tempfile.mkdtemp(), "r.bin")
        try:
            # 130 events: the log keeps the last 128, oldest first
            with open(path, "wb") as f:
                f.write(self.record([(n % 49, 1, -n, 1000 * n) for n in range(130)], dropped=3))
            head, values, log = fw.input_record(path)
            self.assertEqual((head["events"], head["dropped"]), (130, 3))
            self.assertEqual(values[:3], [0, 1, 2])
            self.assertEqual(log[0], (2, 2, 1, -2, 2000))
            self.assertEqual(log[-1], (129, 129 % 49, 1, -129, 129000))
            self.assertEqual(fw.event_lines(log[:1]), ["2 FX press -2"])
        finally:
            shutil.rmtree(os.path.dirname(path))

    def test_events_of_one_scan_are_compared_as_a_set(self):
        # a chord decided in one scan comes in the scan's column order,
        # which moves with its phase: sorted. One control's events, and
        # events a scan or more apart, keep their order.
        t = fw.TICKS_PER_MS
        chord = [(0, 40, 1, 1, 100 * t), (1, 14, 1, 1, 100 * t + 2000), (2, 20, 1, 1, 100 * t + 20000)]
        self.assertEqual(fw.event_lines(chord), ["0 KEY1 press 1", "1 KEY7 press 1", "2 KEY27 press 1"])
        pot = [(0, 41, 4, 750, 100 * t), (1, 41, 4, 600, 101 * t)]
        self.assertEqual(fw.event_lines(pot), ["0 MASTER move 750", "1 MASTER move 600"])
        apart = [(0, 40, 1, 1, 100 * t), (1, 14, 1, 1, 102 * t)]
        self.assertEqual(fw.event_lines(apart), ["0 KEY27 press 1", "1 KEY1 press 1"])

    def test_the_record_fields_follow_input_h(self):
        # the counters' order in firmware/src/input.h's sb_input_record
        import re
        with open(os.path.join(ROOT, "firmware", "src", "input.h")) as f:
            text = f.read()
        body = text[text.index("struct sb_input_record {"):text.index("int values[")]
        self.assertEqual(tuple(re.findall(r"^\s*u32 (\w+);", body, re.M)), fw.INPUT_FIELDS)
        self.assertIn("int values[INPUT_CONTROLS + 1];", text)
        self.assertEqual(fw.INPUT_VALUES, 50)

    def test_latency_allows_for_the_time_base_start(self):
        lo, hi = fw.latency(103 * fw.TICKS_PER_MS, 100)
        self.assertAlmostEqual(lo, 3.0)
        self.assertAlmostEqual(hi - lo, fw.START_SLACK / fw.TICKS_PER_MS)

    def test_events_compare_with_their_golden(self):
        case = tempfile.mkdtemp()
        old = fw.ROOT
        try:
            fw.ROOT = case
            os.makedirs(os.path.join(case, fw.EVENTS_DIR))
            log = [(0, 2, 1, 1, 5), (1, 2, 2, 0, 9)]
            self.assertTrue(fw.check_events("t", case, log))          # no golden yet
            with open(os.path.join(case, "events.txt")) as f:
                written = f.read()
            self.assertEqual(written, "0 FX press 1\n1 FX release 0\n")
            with open(os.path.join(case, fw.EVENTS_DIR, "t.txt"), "w") as f:
                f.write("# a comment\n" + written)
            self.assertEqual(fw.check_events("t", case, log), [])
            # times never matter; anything else does
            self.assertEqual(fw.check_events("t", case, [(0, 2, 1, 1, 7), (1, 2, 2, 0, 99)]), [])
            self.assertTrue(fw.check_events("t", case, log[:1]))
            self.assertTrue(fw.check_events("t", case, [(0, 3, 1, 1, 5), (1, 2, 2, 0, 9)]))
        finally:
            fw.ROOT = old
            shutil.rmtree(case)
