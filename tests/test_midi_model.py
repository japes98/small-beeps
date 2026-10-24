# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
import unittest

from tests.helpers import ROOT, load_tool

mm = load_tool("midi_model.py")
ms = load_tool("midi_scripts.py")


def run(*b):
    return mm.parse(b)


class MidiModelTest(unittest.TestCase):
    """Requirements: R-MIDI-1"""

    def test_running_status(self):
        p = run(0x90, 60, 100, 62, 90, 64, 0)
        self.assertEqual(p.log, [(0x90, 60, 100, 2), (0x90, 62, 90, 2), (0x90, 64, 0, 2)])

    def test_one_data_byte_messages(self):
        p = run(0xC3, 5, 6, 0xD0, 40)
        self.assertEqual(p.log, [(0xC3, 5, 0, 1), (0xC3, 6, 0, 1), (0xD0, 40, 0, 1)])

    def test_realtime_inside_a_message_changes_nothing(self):
        p = run(0x90, 0xF8, 60, 0xFE, 100, 0xFA, 61, 0xFC, 101)
        self.assertEqual(p.log, [(0xF8, 0, 0, 0), (0xFE, 0, 0, 0), (0x90, 60, 100, 2),
                                 (0xFA, 0, 0, 0), (0xFC, 0, 0, 0), (0x90, 61, 101, 2)])
        self.assertEqual(p.count["realtime"], 4)

    def test_realtime_inside_sysex(self):
        p = run(0xF0, 1, 0xF8, 2, 0xF7, 0x80, 1, 2)
        self.assertEqual(p.log, [(0xF8, 0, 0, 0), (0xF0, 2, 0, 2), (0x80, 1, 2, 2)])

    def test_sysex_ends_running_status(self):
        p = run(0x90, 60, 100, 0xF0, 1, 0xF7, 61, 100)
        self.assertEqual(p.log, [(0x90, 60, 100, 2), (0xF0, 1, 0, 2)])
        self.assertEqual(p.count["orphans"], 2)

    def test_status_cuts_sysex_and_partial_message(self):
        p = run(0xF0, 1, 2, 0x90, 60, 0xB0, 7, 100)
        self.assertEqual(p.log, [(0xB0, 7, 100, 2)])
        self.assertEqual((p.count["sysex_cut"], p.count["cut"]), (1, 1))

    def test_long_sysex(self):
        p = run(0xF0, *([0x55] * (mm.SYSEX_LIMIT + 10)), 0xF7, 0x90, 1, 2)
        n = mm.SYSEX_LIMIT + 10
        self.assertEqual(p.log, [(0xF0, n & 0x7F, min(n >> 7, 0x7F), 2), (0x90, 1, 2, 2)])
        self.assertEqual(p.count["sysex_long"], 1)

    def test_undefined_and_stray(self):
        p = run(0xF4, 1, 0xF5, 0xF9, 0xFD, 0xF7, 0x90, 1, 2)
        self.assertEqual(p.log, [(0x90, 1, 2, 2)])
        self.assertEqual(p.count["undefined"], 5)
        self.assertEqual(p.count["orphans"], 1)

    def test_system_common(self):
        p = run(0xF2, 1, 2, 3, 0xF1, 4, 5, 0xF6, 0xF3, 7)
        self.assertEqual(p.log, [(0xF2, 1, 2, 2), (0xF1, 4, 0, 1), (0xF6, 0, 0, 0), (0xF3, 7, 0, 1)])
        self.assertEqual(p.count["orphans"], 2)

    def test_reset_clears_running_status(self):
        p = run(0x90, 60, 0xFF, 100, 0x90, 1, 2)
        self.assertEqual(p.log, [(0xFF, 0, 0, 0), (0x90, 1, 2, 2)])
        self.assertEqual((p.count["cut"], p.count["orphans"]), (1, 1))

    def test_garbage_never_wedges(self):
        # After any bytes at all, a fresh status and its data still parse.
        x = 12345
        junk = []
        for _ in range(20000):
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
            junk.append(x >> 16 & 0xFF)
        p = run(*junk, 0x92, 70, 80)
        self.assertEqual(p.log[-1], (0x92, 70, 80, 2))
        self.assertEqual(p.count["parsed"], len(junk) + 3)

    def test_limits_match_the_firmware(self):
        with open(os.path.join(ROOT, "firmware", "src", "midi.h")) as f:
            h = f.read()
        self.assertEqual(int(re.search(r"#define MIDI_SYSEX_LIMIT (\d+)u", h).group(1)), mm.SYSEX_LIMIT)


class MidiScriptsTest(unittest.TestCase):
    """Requirements: R-MIDI-1, R-MIDI-4"""

    def test_scripts_are_what_the_tool_writes(self):
        for case in ms.CASES:
            s = case()
            with open(os.path.join(ms.SCRIPTS, s.name + ".txt")) as f:
                self.assertEqual(f.read(), s.text(), s.name)

    def test_perfload_midi_part_is_what_the_tool_writes(self):
        with open(ms.PERFLOAD) as f:
            text = f.read()
        self.assertIn(ms.PERFLOAD_MARK, text)
        self.assertEqual(text, ms.perfload_text(text))

    def test_no_two_midi_events_overlap(self):
        for case in ms.CASES:
            s = case()
            last = 0.0
            for line in s.lines:
                w = line.split()
                if w[1] != "midi":
                    continue
                t = float(w[0])
                self.assertGreaterEqual(t + 1e-6, last, "%s: %s" % (s.name, line))
                last = t + ms.BYTE_MS * (len(w) - 2)

    def test_dense_fills_the_wire(self):
        b = ms.stream(os.path.join(ms.SCRIPTS, "mididense.txt"))
        span = b[-1][0] - b[0][0]
        self.assertGreater(len(b) * ms.BYTE_MS / span, 0.99)


class MidiOutTest(unittest.TestCase):
    """Requirements: R-MIDIOUT-2, R-MIDIOUT-6"""

    def test_knob_value_is_the_maps_inverse(self):
        for k, (lo, hi) in enumerate(mm.KNOB_SPAN):
            for p in range(lo, hi + 1):
                v = mm.knob_value(k, p)
                self.assertTrue(0 <= v <= 127)
                self.assertEqual(mm.knob_offset(k, v), p, (k, p, v))
            self.assertEqual((mm.knob_value(k, lo - 5), mm.knob_value(k, hi + 5)), (0, 127))
            self.assertEqual(mm.knob_value(k, 0), 64)

    def test_knob_spans_match_the_firmware(self):
        with open(os.path.join(ROOT, "firmware", "src", "fm_play.c")) as f:
            c = f.read()
        spans = re.search(r"knob_span\[4\]\[2\] = \{(.*?)\};", c).group(1)
        self.assertEqual(tuple(tuple(int(x) for x in re.findall(r"-?\d+", g)) for g in re.findall(r"\{([^{}]*)\}", spans)),
                         mm.KNOB_SPAN)

    def test_round_trip_script_is_midiouts_capture(self):
        s = ms.midiround()
        b = ms.stream(os.path.join(ms.SCRIPTS, "midiround.txt"))
        with open(os.path.join(ROOT, "tests", "fw", "golden", "midiout", "midi-out.csv")) as f:
            rows = [l.strip().split(",") for l in f][1:]
        self.assertEqual([(round(float(t), 3), int(h, 16)) for t, h in rows], b)
        self.assertTrue(s.lines)


if __name__ == "__main__":
    unittest.main()
