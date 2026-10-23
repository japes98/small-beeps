# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Our own analysis of fwtest's audio captures (M4; tools/fw-suite.py,
R-AUD-*). Python's standard library only: `wave` reads the file, the rest
is written here (docs/DESIGN-NOTES.md, M4, "How the sound is measured").

- The rate: fwtest's WAV header says 44 100 Hz, but the output plays a
  frame every 544 ticks of 24 MHz (HW-45), 44 117.647 Hz; every
  frequency here is computed at that rate (RATE).
- sine_fit: a four-parameter least-squares fit of a sine (amplitude,
  phase, offset and frequency), refined by Gauss-Newton steps from a
  first guess counted from zero crossings. Its frequency is the
  measurement; its residual is THD+N's distortion and noise.
- clicks: the largest second difference of the samples, against what a
  sine of that amplitude and frequency can give under the instrument's
  linear ramps. A step (a hard start or stop) gives a second difference
  of about the step itself, many times the bound.
"""
import math
import struct
import wave

RATE = 24000000 / 544          # frames a second (HW-45)
FULL = 32768                   # 16-bit full scale in the WAV
BLOCK = 64                     # stereo frames a block (firmware/src/audio.h)


def read_wav(path):
    """(header rate, left, right) of a 16-bit stereo WAV."""
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 2:
            raise ValueError("%s: not 16-bit stereo" % path)
        n = w.getnframes()
        data = struct.unpack("<%dh" % (2 * n), w.readframes(n))
        return w.getframerate(), list(data[0::2]), list(data[1::2])


def read_ipb(path):
    """The time each audio block ended, in ms, by block number (ipb.csv)."""
    with open(path) as f:
        rows = [l.strip().split(",") for l in f if l.strip()][1:]
    return [float(r[1]) for r in rows]


def sample_ms(n, ends):
    """When sample n began to play, in ms of emulated time: its block
    ended at ends[n // BLOCK], and its frames played one after another up
    to then."""
    return ends[n // BLOCK] - (BLOCK - n % BLOCK) * 1000.0 / RATE


def crossings(x):
    """Rising zero crossings, as fractional sample indices."""
    out = []
    for i in range(1, len(x)):
        if x[i - 1] < 0 <= x[i] and x[i] != x[i - 1]:
            out.append(i - 1 + (-x[i - 1]) / (x[i] - x[i - 1]))
    return out


def solve(m, v):
    """Solves the small linear system m x = v (Gaussian elimination)."""
    n = len(v)
    a = [list(m[i]) + [v[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        if a[c][c] == 0:
            raise ValueError("singular fit")
        for r in range(n):
            if r != c:
                f = a[r][c] / a[c][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[i][n] / a[i][i] for i in range(n)]


def sine_fit(x, rate=RATE, iterations=8):
    """{amplitude, frequency, phase, offset, residual}: the least-squares
    sine through samples x (residual: the RMS of what is left)."""
    c = crossings(x)
    if len(c) < 3:
        raise ValueError("too few cycles to fit")
    f = (len(c) - 1) / (c[-1] - c[0]) * rate
    t0 = len(x) / 2.0
    ts = [(i - t0) / rate for i in range(len(x))]
    a = b = d = 0.0
    for it in range(iterations):
        w = 2 * math.pi * f
        cs = [math.cos(w * t) for t in ts]
        sn = [math.sin(w * t) for t in ts]
        if it == 0:
            cols = [cs, sn, [1.0] * len(x)]
        else:
            cols = [cs, sn, [1.0] * len(x), [t * (-a * s + b * co) for t, s, co in zip(ts, sn, cs)]]
        m = [[sum(p * q for p, q in zip(ci, cj)) for cj in cols] for ci in cols]
        v = [sum(p * q for p, q in zip(ci, x)) for ci in cols]
        sol = solve(m, v)
        a, b, d = sol[0], sol[1], sol[2]
        if it:
            f += sol[3] / (2 * math.pi)
    w = 2 * math.pi * f
    res = [xi - (a * math.cos(w * t) + b * math.sin(w * t) + d) for xi, t in zip(x, ts)]
    return {"amplitude": math.hypot(a, b), "frequency": f, "phase": math.atan2(-b, a),
            "offset": d, "residual": math.sqrt(sum(r * r for r in res) / len(res))}


def thd_n_db(fit):
    """THD+N in dB: what the fitted sine leaves, against the sine (RMS)."""
    return 20 * math.log10(fit["residual"] / (fit["amplitude"] / math.sqrt(2)))


def dbfs(amplitude):
    """A sine's peak amplitude in dB of 16-bit full scale."""
    return 20 * math.log10(amplitude / FULL)


def cents(f, ref):
    return 1200 * math.log2(f / ref)


def note_hz(note):
    """Equal temperament, A4 (MIDI 69) = 440 Hz."""
    return 440.0 * 2 ** ((note - 69) / 12.0)


def max_second_difference(x):
    return max((abs(x[i] - 2 * x[i - 1] + x[i - 2]) for i in range(2, len(x))), default=0)


def click_bound(amplitude, f, ramp, rate=RATE, quantum=4):
    """The largest second difference a sine of this amplitude and
    frequency can show under a linear ramp of `ramp` samples (its own
    curvature, plus the ramp's corner and its slope against the sine's),
    and a few steps of the WAV's rounding."""
    w = 2 * math.pi * f / rate
    return amplitude * ((2 * math.sin(w / 2)) ** 2 + (1 + 2 * w) / ramp) + quantum
