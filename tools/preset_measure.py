#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Measures presets against what they are meant to do (M8b, the
candidates 65 to 70; docs/DESIGN-NOTES.md, "M8b: candidates 65 to 70"):
one note (C4, transposed as the patch says) held 2 s in fwtest by the
shipping image, at velocities 40 and 120, through MIDI in.

  preset_measure.py --image APP.bin --out DIR NUMBER ...

For each preset it prints, from the velocity 120 note:
- attack: ms to within 3 dB of the note's peak;
- level: dB under the peak at 10, 50, 150, 500, 1000 and 1900 ms;
- brightness: the spectral centroid of the power, in harmonics of the
  note (1 is a sine; a sawtooth's is about 2.3) at 5, 50, 300 and
  1500 ms (23 ms windows);
- beating: the swing, in dB, of the 20 ms level from 800 to 1900 ms
  about a straight line (a decay is not beating);
- vibrato: the fundamental's pitch from its phase (windows of whole
  periods, every 10 ms), 600 to 1900 ms: its rate (Hz) and depth
  (cents, half the swing);
- inharmonicity: the power-weighted distance of the partials from the
  harmonics, in harmonics (0 to 0.5), at 50 ms (186 ms window); and a
  stretched partial at 2.01 x f0 (-2 cents) against the 2nd harmonic,
  fitted together over 1 s;
- breath: the share of the power more than a tenth of a harmonic from
  any harmonic, at 600 ms;
and velocity: the brightness at 5 ms at velocity 40 and 120.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_analysis as aa  # noqa: E402  (tools/, our own)
import fm_patch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_PROGRAM = 25          # fm.h: FM_PRESET0
ON_MS, OFF_MS, RUN_MS = 300, 2300, 2600


def render(image, out, i, velocity):
    d = os.path.join(out, "m%02d-v%d" % (i + 1, velocity))
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    s = d + ".txt"
    with open(s, "w") as f:
        f.write("100 midi c0 %02x\n%d midi 90 3c %02x\n%d midi 80 3c 00\n" % (FIRST_PROGRAM + i, ON_MS, velocity, OFF_MS))
    subprocess.run(["sh", "tools/fwtest", "run", os.path.relpath(image, ROOT), "--ms", str(RUN_MS), "--script",
                    os.path.relpath(s, ROOT), "--wav", "--out", os.path.relpath(d, ROOT)], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    _, x, _ = aa.read_wav(os.path.join(d, "audio.wav"))
    start = int(ON_MS * aa.RATE / 1000)
    while start < len(x) and abs(x[start]) < 2:
        start += 1
    return x[start:int(OFF_MS * aa.RATE / 1000)]


def at(ms):
    return int(ms * aa.RATE / 1000)


def rms(x):
    return math.sqrt(sum(v * v for v in x) / len(x)) if x else 0.0


def db(a, ref):
    return 20 * math.log10(a / ref) if a > 0 and ref > 0 else -200.0


def spectrum(x, ms, n):
    seg = x[at(ms):at(ms) + n]
    return aa.power_spectrum(seg, n) if len(seg) == n else []


def centroid(x, ms, f0, n=1024):
    sp = [(hz, p) for hz, p in spectrum(x, ms, n) if hz >= f0 / 2]   # (not DC)
    total = sum(p for _, p in sp)
    return sum(hz * p for hz, p in sp) / total / f0 if total else 0.0


def breath(x, ms, f0, n=8192):
    sp = spectrum(x, ms, n)
    total = sum(p for _, p in sp)
    off = sum(p for hz, p in sp if abs(hz / f0 - round(hz / f0)) > 0.1)
    return off / total if total else 0.0


def vibrato(x, f0):
    """The fundamental's pitch from its phase: x mixed down by f0 and
    summed over windows of whole periods (about 20 ms, so the other
    harmonics cancel and noise averages out) every 10 ms, the phase's
    steps between windows as frequency."""
    w, step = 2 * math.pi * f0 / aa.RATE, at(10)
    span = int(round(round(0.020 * f0) * aa.RATE / f0))
    ph = []
    for k in range(at(600), at(1900) - span, step):
        re = sum(x[n] * math.cos(w * n) for n in range(k, k + span))
        im = -sum(x[n] * math.sin(w * n) for n in range(k, k + span))
        ph.append(math.atan2(im, re))
    d = []
    for a_, b_ in zip(ph, ph[1:]):
        dp = (b_ - a_ + math.pi) % (2 * math.pi) - math.pi
        d.append(1200 * math.log2(1 + dp / (2 * math.pi * 0.010) / f0))
    if len(d) < 4:
        return 0.0, 0.0
    m = sum(d) / len(d)
    d = [v - m for v in d]
    ups = sum(1 for a, b in zip(d, d[1:]) if a < 0 <= b)
    return ups / (len(d) * 0.010), (max(d) - min(d)) / 2


def stretched(x, f0, ratio=2.01, cents=-2):
    """The 2nd harmonic and a partial at ratio x f0 moved by cents (the
    upper pair's carrier) fitted together over 1 s from 50 ms (1 Hz apart
    resolves them): the stretched one's amplitude over the harmonic's, dB."""
    seg = [float(v) for v in x[at(50):at(1050):2]]
    rate = aa.RATE / 2
    h, s_ = aa.amplitudes_at(seg, [2 * f0, ratio * f0 * 2 ** (cents / 1200.0)], rate=rate)
    return db(s_, h)


def measure(x, f0):
    win = at(20)
    levels = [rms(x[k:k + win]) for k in range(0, len(x) - win, at(5))]
    top = max(levels)
    held = [db(rms(x[k:k + win]), top) for k in range(at(800), at(1900), at(5))]
    # The level's swing about a straight line (in dB), so a note's own
    # decay doesn't count as beating.
    n = len(held)
    mx, my = (n - 1) / 2.0, sum(held) / n
    slope = sum((k - mx) * (v - my) for k, v in enumerate(held)) / sum((k - mx) ** 2 for k in range(n))
    dev = [v - (my + slope * (k - mx)) for k, v in enumerate(held)]
    rate, depth = vibrato(x, f0)
    return {
        "attack": aa.attack_ms(x, 0),
        "levels": [db(rms(x[at(t):at(t) + win]), top) for t in (10, 50, 150, 500, 1000, 1900)],
        "bright": [centroid(x, t, f0) for t in (5, 50, 300, 1500)],
        "beating": max(dev) - min(dev),
        "vibrato": (rate, depth),
        "inharm": aa.inharmonicity(x[at(50):at(50) + 8192], f0),
        "stretch": stretched(x, f0),
        "breath": breath(x, 600, f0),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("numbers", type=int, nargs="+")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for n in a.numbers:
        _, _, p = fm_patch.PRESETS[n - 1]
        f0 = aa.note_hz(60 + p["transpose"])
        loud, soft = render(os.path.abspath(a.image), out, n - 1, 120), render(os.path.abspath(a.image), out, n - 1, 40)
        m = measure(loud, f0)
        print("P%02d %s (C4%+d, %.1f Hz)" % (n, p["name"], p["transpose"], f0))
        print("  attack %.1f ms; level %s dB at 10, 50, 150, 500, 1000, 1900 ms"
              % (m["attack"], ", ".join("%.1f" % v for v in m["levels"])))
        print("  brightness %s harmonics at 5, 50, 300, 1500 ms; velocity 40: %.2f, 120: %.2f at 5 ms"
              % (", ".join("%.2f" % v for v in m["bright"]), centroid(soft, 5, f0), m["bright"][0]))
        print("  beating %.2f dB; vibrato %.1f Hz, %.1f cents; inharmonicity %.3f; a partial at 2.01 (-2 cents)"
              " %.1f dB from the 2nd harmonic; breath %.4f"
              % (m["beating"], m["vibrato"][0], m["vibrato"][1], m["inharm"], m["stretch"], m["breath"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
