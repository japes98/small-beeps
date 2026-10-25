# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import math
import os
import shutil
import struct
import tempfile
import unittest
import wave

from tests.helpers import load_tool

aa = load_tool("audio_analysis.py")


def tone(f, amp, n, phase=0.0, rate=aa.RATE):
    return [amp * math.sin(2 * math.pi * f * i / rate + phase) for i in range(n)]


def quantized(x):
    return [int(math.floor(v)) for v in x]   # fwtest's WAV floors (>> 8)


def gated(f, amp, start, attack, hold, release, n, rate=aa.RATE):
    """A sine started at phase 0 at `start`, with linear ramps of attack
    and release samples (0: a hard edge), as the instrument plays a note."""
    out = [0.0] * n
    for i in range(start, n):
        k = i - start
        if attack and k < attack:
            env = k / attack
        elif k < attack + hold:
            env = 1.0
        elif release and k < attack + hold + release:
            env = 1.0 - (k - attack - hold) / release
        else:
            break
        out[i] = env * amp * math.sin(2 * math.pi * f * k / rate)
    return quantized(out)


class AnalysisTest(unittest.TestCase):
    """Our own sound measurements (M4). Requirements: R-AUD-4, R-AUD-5"""

    def test_the_rate_is_the_outputs_not_the_headers(self):
        self.assertAlmostEqual(aa.RATE, 44117.647058823, places=6)

    def test_a_sine_fit_finds_frequency_level_and_phase(self):
        x = quantized(tone(1000.0, 16383.5, 30000, phase=0.7))
        fit = aa.sine_fit(x)
        self.assertLess(abs(aa.cents(fit["frequency"], 1000.0)), 1e-4)
        self.assertAlmostEqual(aa.dbfs(fit["amplitude"]), 20 * math.log10(0.5), delta=0.001)
        # 16-bit rounding alone: about -92 dB for a -6 dBFS tone
        self.assertLess(aa.thd_n_db(fit), -88)

    def test_a_first_guess_off_by_a_cent_is_refined(self):
        x = quantized(tone(440.0 * 2 ** (1 / 1200.0), 8000, 20000))
        fit = aa.sine_fit(x)
        self.assertLess(abs(aa.cents(fit["frequency"], 440.0) - 1.0), 1e-4)

    def test_distortion_shows_in_thd_n(self):
        x = [a + b for a, b in zip(tone(1000.0, 16000, 30000), tone(3000.0, 16, 30000))]
        self.assertAlmostEqual(aa.thd_n_db(aa.sine_fit(quantized(x))), -60.0, delta=0.5)

    def test_a_ramped_note_has_no_click_and_a_hard_edge_does(self):
        # The instrument's ramps (221 and 882 samples) pass at every pitch
        # it plays; the same note with a hard start (at phase 0) or a hard
        # stop fails, at the lowest and the highest note.
        for f in (aa.note_hz(29), aa.note_hz(60), aa.note_hz(103)):
            amp = 8192.0
            soft = gated(f, amp, 100, 221, 3000, 882, 6000)
            self.assertLessEqual(aa.max_second_difference(soft[50:100 + 221 + 50]), aa.click_bound(amp, f, 221))
            self.assertLessEqual(aa.max_second_difference(soft[3321 - 150:3321 + 882 + 50]),
                                 aa.click_bound(amp, f, 882))
            hard_start = gated(f, amp, 100, 0, 3000, 882, 6000)
            self.assertGreater(aa.max_second_difference(hard_start[50:100 + 221 + 50]),
                               aa.click_bound(amp, f, 221), f)
            # stopped hard at a quarter cycle past the end of the hold
            hold = 3000 + int(aa.RATE / f / 4)
            hard_stop = gated(f, amp, 100, 221, hold, 0, 9000)
            end = 100 + 221 + hold
            self.assertGreater(aa.max_second_difference(hard_stop[end - 882 - 150:end + 50]),
                               aa.click_bound(amp, f, 882), f)

    def test_sample_times_come_from_the_block_ends(self):
        ends = [1.451, 2.902]
        self.assertAlmostEqual(aa.sample_ms(0, ends), 1.451 - 64 * 1000 / aa.RATE)
        self.assertAlmostEqual(aa.sample_ms(63, ends), 1.451 - 1000 / aa.RATE)
        self.assertAlmostEqual(aa.sample_ms(64, ends), 2.902 - 64 * 1000 / aa.RATE)

    def test_equal_temperament(self):
        self.assertAlmostEqual(aa.note_hz(69), 440.0)
        self.assertAlmostEqual(aa.note_hz(81), 880.0)
        self.assertAlmostEqual(aa.cents(aa.note_hz(70), aa.note_hz(69)), 100.0)

    def test_wav_and_ipb_files_are_read(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "a.wav")
            with wave.open(p, "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(44100)
                w.writeframes(struct.pack("<6h", 1, 1, -2, -2, 3, 4))
            self.assertEqual(aa.read_wav(p), (44100, [1, -2, 3], [1, -2, 4]))
            with open(os.path.join(d, "ipb.csv"), "w") as f:
                f.write("block,end_ms,core0,core1\n0,1.799,85198,0\n1,3.250,1758,0\n")
            self.assertEqual(aa.read_ipb(os.path.join(d, "ipb.csv")), [1.799, 3.25])
        finally:
            shutil.rmtree(d)


class FmAnalysisTest(unittest.TestCase):
    """Requirements: R-FM-1"""

    def test_bessel_values(self):
        # Abramowitz and Stegun, table 9.1: J0(1) 0.7651977, J1(1) 0.4400506,
        # J2(1) 0.1149035; J0's first zero at 2.4048256.
        for n, x, v in ((0, 1.0, 0.7651977), (1, 1.0, 0.4400506), (2, 1.0, 0.1149035)):
            self.assertAlmostEqual(aa.bessel_j(n, x), v, places=6)
        self.assertAlmostEqual(aa.bessel_j(0, 2.4048256), 0.0, places=6)

    def test_amplitudes_at_known_frequencies(self):
        f = [440.0 * k for k in (1, 2, 3)]
        x = [sum(a * math.sin(2 * math.pi * fk * i / aa.RATE + 0.3 * k)
                 for k, (a, fk) in enumerate(zip((1000.0, 300.0, 20.0), f))) for i in range(4410)]
        got = aa.amplitudes_at(x, f)
        for g, want in zip(got, (1000.0, 300.0, 20.0)):
            self.assertAlmostEqual(g, want, places=6)

    def test_an_fm_tone_has_bessel_sidebands(self):
        # sin(wc t + I sin(wm t)): sideband n at J_n(I) (Chowning 1973).
        fm, fc, index = 440.0, 2640.0, math.pi / 2
        x = [math.sin(2 * math.pi * fc * i / aa.RATE + index * math.sin(2 * math.pi * fm * i / aa.RATE))
             for i in range(8820)]
        amp = aa.amplitudes_at(x, [fc + n * fm for n in range(-3, 4)])
        for n, a in zip(range(-3, 4), amp):
            self.assertAlmostEqual(a, abs(aa.bessel_j(abs(n), index)), places=4)

    def test_block_amplitudes_and_pitch_track(self):
        x = tone(440.0, 1000.0, 64 * 10)
        for a in aa.block_amplitudes(x, 440.0):
            self.assertAlmostEqual(a, 1000.0, places=3)
        y = tone(440.0, 1000.0, 4410)
        for _, f in aa.pitch_track(y, 0, len(y)):
            self.assertAlmostEqual(f, 440.0, places=3)



class MacroMeasuresTest(unittest.TestCase):
    """Requirements: R-UI-6 (the macros' measures, on signals whose answers
    are known)."""

    def test_fft_finds_a_sine(self):
        n = 1024
        re = [math.sin(2 * math.pi * 10 * i / n) for i in range(n)]
        im = [0.0] * n
        aa.fft(re, im)
        mags = [math.hypot(a, b) for a, b in zip(re, im)]
        self.assertEqual(max(range(n // 2), key=lambda k: mags[k]), 10)
        self.assertAlmostEqual(mags[10], n / 2, places=6)

    def test_share_above(self):
        f0 = 200.0
        low = tone(f0, 1000, 8192)
        both = [a + b for a, b in zip(low, tone(8 * f0, 1000, 8192))]
        self.assertLess(aa.share_above(low, 7.5 * f0), 0.001)
        self.assertAlmostEqual(aa.share_above(both, 7.5 * f0), 0.5, delta=0.02)

    def test_inharmonicity(self):
        f0 = 220.0
        harm = [a + b for a, b in zip(tone(f0, 1000, 8192), tone(3 * f0, 500, 8192))]
        off = [a + b for a, b in zip(tone(f0, 1000, 8192), tone(3.4 * f0, 500, 8192))]
        self.assertLess(aa.inharmonicity(harm, f0), 0.02)
        self.assertGreater(aa.inharmonicity(off, f0), 0.05)

    def test_attack_and_release(self):
        rate = aa.RATE
        attack, release = int(0.05 * rate), int(0.2 * rate)
        x = gated(440.0, 10000, 0, attack, int(0.3 * rate), release, int(0.8 * rate))
        self.assertAlmostEqual(aa.attack_ms(x, 0), 50 * 10 ** (-3 / 20), delta=3)
        off = attack + int(0.3 * rate)
        self.assertAlmostEqual(aa.release_ms(x, off, drop_db=20), 180, delta=5)

    def test_pitch_swing(self):
        rate, n = aa.RATE, int(0.5 * aa.RATE)
        steady = tone(440.0, 10000, n)
        phase, wobble = 0.0, []
        for i in range(n):
            f = 440.0 * 2 ** (30 / 1200 * math.sin(2 * math.pi * 5.5 * i / rate))
            phase += 2 * math.pi * f / rate
            wobble.append(10000 * math.sin(phase))
        self.assertLess(aa.pitch_swing_cents(steady, 0, n), 1)
        self.assertAlmostEqual(aa.pitch_swing_cents(wobble, 0, n), 30, delta=5)



if __name__ == "__main__":
    unittest.main()
