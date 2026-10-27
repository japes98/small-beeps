# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import struct
import tempfile
import unittest
import wave
import zlib

from tests.helpers import load_tool

gt = load_tool("goldtime.py")


def write_wav(path, frames):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(struct.pack("<%dh" % (2 * len(frames)), *[v for f in frames for v in f]))


def tone(n, k=0):
    return [((i * 37 + k) % 2000 - 1000, (i * 53 + k) % 1800 - 900) for i in range(n)]


def quiet(n):
    return [(0, 0)] * n


class EndTest(unittest.TestCase):
    """Requirements: R-GOLD-1"""

    ENDS = [gt.BLOCK_MS * (k + 1) + 0.0123 for k in range(100)]

    def test_margins(self):
        after, before = gt.end_margins(self.ENDS, self.ENDS[9] + 0.3)
        self.assertAlmostEqual(after, 0.3)
        self.assertAlmostEqual(before, gt.BLOCK_MS - 0.3)

    def test_an_end_just_after_a_block_or_just_before_the_next_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "ipb.csv"), "w") as f:
                f.write("block,end_ms,core0,core1\n")
                for k, e in enumerate(self.ENDS):
                    f.write("%d,%.3f,1,1\n" % (k, e))
            ok = self.ENDS[20] + 0.3
            self.assertEqual(gt.check_end("x", d, ok)[0], [])
            self.assertTrue(gt.check_end("x", d, self.ENDS[20] + 0.05)[0])     # 50 us after a block
            self.assertTrue(gt.check_end("x", d, self.ENDS[21] - 0.5)[0])      # 0.5 ms before the next
            for t in (40.0, 41.0, 42.0, 100.0):
                want = gt.suggest_end(self.ENDS, t)
                self.assertLess(abs(want - t), gt.BLOCK_MS)
                self.assertEqual(gt.check_end("x", d, want)[0], [])
                p, _ = gt.check_end("x", d, t)
                if p:
                    self.assertIn("fix: replace --ms %s with --ms %s" % (gt.fmt_ms(t), gt.fmt_ms(want)), p[0])

    def test_a_failed_end_says_the_exact_fix_and_where(self):
        # The owner's answer (2026-10-26): the check keeps failing CI, and
        # its message gives the replacement --ms in one step.
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "ipb.csv"), "w") as f:
                f.write("block,end_ms,core0,core1\n")
                for k, e in enumerate(self.ENDS):
                    f.write("%d,%.3f,1,1\n" % (k, e))
            t = round(self.ENDS[20] + 0.05, 3)
            want = gt.fmt_ms(gt.suggest_end(self.ENDS, t))
            p, _ = gt.check_end("x", d, t, lambda ms: "in FILE, line 7: change --ms %s to --ms %s" % (gt.fmt_ms(t), ms))
            self.assertEqual(len(p), 1)
            self.assertTrue(p[0].endswith("fix: in FILE, line 7: change --ms %s to --ms %s" % (gt.fmt_ms(t), want)), p[0])
            self.assertEqual(gt.check_end("x", d, float(want))[0], [])

    def test_no_ipb_no_check(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(gt.check_end("x", d, 10.0), ([], None))


class MidiTest(unittest.TestCase):
    """Requirements: R-GOLD-2, R-GOLD-3"""

    def rows(self, d, name, rows):
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write("ms,byte\n" + "".join("%.3f,%02x\n" % r for r in rows))
        return p

    def test_within_the_tolerance_passes_beyond_fails(self):
        g = [(100.0, 0x90), (100.32, 60), (100.64, 100)]
        self.assertEqual(gt.compare_rows("m", g, [(t + 1.451, b) for t, b in g])[0], [])
        self.assertTrue(gt.compare_rows("m", g, [(t + 2.2, b) for t, b in g])[0])
        self.assertTrue(gt.compare_rows("m", g, g[:2] + [(100.64, 101)])[0])
        self.assertTrue(gt.compare_rows("m", g, g[:2])[0])

    def test_a_shift_is_proven_and_a_new_byte_refused(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.rows(d, "g.csv", [(100.0, 0x90), (100.32, 60), (100.64, 100)])
            moved = self.rows(d, "n.csv", [(103.0, 0x90), (103.32, 60), (103.64, 100)])
            other = self.rows(d, "o.csv", [(100.0, 0x90), (100.32, 61), (100.64, 100)])
            self.assertTrue(gt.shift_midi(g, moved)[0])
            self.assertFalse(gt.shift_midi(g, other)[0])


def write_png(path, rows):
    """An 8-bit RGB PNG of rows of (r, g, b), filter 0."""
    h, w = len(rows), len(rows[0])
    raw = b"".join(b"\0" + bytes(v for px in row for v in px) for row in rows)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class ScreenTest(unittest.TestCase):
    """Requirements: R-GOLD-2, R-GOLD-3"""

    def test_only_the_live_spectrum_may_differ(self):
        with tempfile.TemporaryDirectory() as d:
            base = [[(0, 0, 0)] * 240 for _ in range(240)]
            live = [list(r) for r in base]
            live[170][20] = (0, 255, 255)                 # a bar inside the spectrum
            other = [list(r) for r in base]
            other[10][10] = (255, 255, 255)               # the header
            g = os.path.join(d, "golden-live", "x")
            os.makedirs(g)
            for name, rows in (("g.png", base), ("live.png", live), ("other.png", other)):
                write_png(os.path.join(g if name == "g.png" else d, name), rows)
            gp = os.path.join(g, "g.png")
            self.assertEqual(gt.screen_diff(gp, os.path.join(d, "live.png")), (0, 1))
            self.assertEqual(gt.compare_screen("x", gp, os.path.join(d, "live.png"))[0], [])
            self.assertTrue(gt.compare_screen("x", gp, os.path.join(d, "other.png"))[0])
            self.assertTrue(gt.shift_file(gp, os.path.join(d, "live.png"))[0])
            self.assertFalse(gt.shift_file(gp, os.path.join(d, "other.png"))[0])


class WavTest(unittest.TestCase):
    """Requirements: R-GOLD-3"""

    def test_sounds_moved_independently_are_a_shift(self):
        g = quiet(500) + tone(300) + quiet(400) + tone(200, 7) + quiet(300)
        n = quiet(564) + tone(300) + quiet(272) + tone(200, 7) + quiet(364)
        ok, detail = gt.shift_frames(g, n)
        self.assertTrue(ok, detail)

    def test_a_changed_sample_or_length_is_refused(self):
        g = quiet(500) + tone(300) + quiet(500)
        n = quiet(564) + tone(300) + quiet(436)
        n[700] = (n[700][0] + 1, n[700][1])
        self.assertFalse(gt.shift_frames(g, n)[0])
        self.assertTrue(gt.shift_frames(g, quiet(564) + tone(300) + quiet(500))[0])   # the end moved
        self.assertFalse(gt.shift_frames(g, quiet(564) + tone(300) + quiet(2000))[0])  # by too much
        self.assertFalse(gt.shift_frames(g, quiet(500) + tone(301) + quiet(499))[0])  # a longer sound
        far = quiet(500) + tone(300) + quiet(1500)
        self.assertFalse(gt.shift_frames(far, quiet(1800) + tone(300) + quiet(200))[0])        # moved too far

    def test_a_sound_cut_by_the_end_matches_as_far_as_both_go(self):
        g = quiet(500) + tone(300) + quiet(400) + tone(600, 3)
        n = quiet(564) + tone(300) + quiet(400) + tone(536, 3)
        self.assertTrue(gt.shift_frames(g, n)[0])

    def test_files(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
            write_wav(a, quiet(200) + tone(300) + quiet(200))
            write_wav(b, quiet(264) + tone(300) + quiet(136))
            self.assertTrue(gt.shift_file(a, b)[0])
            png_a, png_b = os.path.join(d, "lcd-1ms.png"), os.path.join(d, "x", "lcd-1ms.png")
            os.makedirs(os.path.dirname(png_b))
            for p, c in ((png_a, b"a"), (png_b, b"b")):
                with open(p, "wb") as f:
                    f.write(c)
            self.assertFalse(gt.shift_file(png_a, png_b)[0])


if __name__ == "__main__":
    unittest.main()
