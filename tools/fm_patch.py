#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The FM engine's patch format, version 2 (since ARP: the arpeggiator's
settings; version 1 is M5's), and our own test patches (M5;
docs/PATCH-FORMAT.md, R-FM-7).

  fm_patch.py write      writes firmware/src/patches.c from TEST_PATCHES
  fm_patch.py check      exits 1 if firmware/src/patches.c is not what
                         `write` would write, or a patch is not valid

The test patches are defined here, once, in readable units; the firmware
gets them as bytes (patches.c, generated), and tools/fw-suite.py takes
its expected values (levels, times, ratios) from the same definitions.
They are our own: none is, or is derived from, any synthesizer's factory
or published preset.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "firmware", "src", "patches.c")

BYTES = 112
VERSION = 2
OP_OFFSET, OP_BYTES, SUM_OFFSET = 32, 13, 110
ALGORITHMS = 10
RATIO, FIXED = 0, 1


def time_ms(code):
    """A time code's time: 2^(code / 8) ms (fm.h)."""
    return 2.0 ** (code / 8.0)


def level_gain(level):
    """A level's gain: 2^((level - 127) / 8); 0 is off."""
    return 0.0 if level == 0 else 2.0 ** ((level - 127) / 8.0)


def op(freq, level, mode=RATIO, detune=0, velocity=0, rates=(0, 0, 0, 0), levels=(127, 127, 127)):
    """An operator. freq: a ratio (mode RATIO) or Hz (FIXED)."""
    return {"mode": mode, "freq": freq, "detune": detune, "level": level, "velocity": velocity,
            "rates": tuple(rates), "levels": tuple(levels)}


OFF = op(1.0, 0)

# The arpeggiator's settings in a patch (since ARP, version 2; bytes 29 to
# 31, docs/PATCH-FORMAT.md): its modes, and its rates in MIDI clock pulses
# (24 a quarter note), in the order KNOB1 steps through them.
ARP_MODES = ("UP", "DOWN", "UP/DOWN", "ORDER", "RANDOM", "CHORD")
ARP_RATES = (("1/2", 48), ("1/4.", 36), ("1/4", 24), ("1/8.", 18), ("1/8", 12), ("1/8T", 8),
             ("1/16.", 9), ("1/16", 6), ("1/16T", 4), ("1/32", 3))
ARP_DEFAULT = {"on": False, "latch": False, "mode": 0, "octaves": 1, "rate": 7, "swing": 0, "gate": 50}


def arp(**kw):
    """A patch's arpeggiator settings: ARP_DEFAULT with these changed.
    mode an index of ARP_MODES, rate of ARP_RATES, octaves 1 to 4, swing
    0 to 75 (%, in steps of 5), gate 10 to 100 (%)."""
    a = dict(ARP_DEFAULT)
    for k in kw:
        assert k in a, k
    a.update(kw)
    return a


def arp_bytes(a):
    """Bytes 29 to 31 for these settings."""
    assert 0 <= a["mode"] < len(ARP_MODES) and 1 <= a["octaves"] <= 4 and 0 <= a["rate"] < len(ARP_RATES)
    assert a["swing"] % 5 == 0 and 0 <= a["swing"] <= 75 and 10 <= a["gate"] <= 100
    return bytes((int(a["on"]) | int(a["latch"]) << 1 | a["mode"] << 2 | (a["octaves"] - 1) << 5,
                  a["rate"] | (a["swing"] // 5) << 4, a["gate"]))


def arp_of(b):
    """A version 2 patch's arpeggiator settings, as arp() gives them."""
    return {"on": bool(b[29] & 1), "latch": bool(b[29] & 2), "mode": b[29] >> 2 & 7,
            "octaves": (b[29] >> 5 & 3) + 1, "rate": b[30] & 15, "swing": (b[30] >> 4) * 5, "gate": b[31]}


def patch(name, algorithm, ops, feedback=0, mono=False, glide=0, transpose=0,
          pitch_depth=0, pitch_rates=(0, 0, 0), pitch_levels=(0, 0, 0, 0), arp_settings=None):
    ops = list(ops) + [OFF] * (6 - len(ops))
    return {"name": name, "algorithm": algorithm, "feedback": feedback, "mono": mono,
            "glide": glide, "transpose": transpose, "pitch_depth": pitch_depth,
            "pitch_rates": tuple(pitch_rates), "pitch_levels": tuple(pitch_levels), "ops": ops,
            "arp": dict(arp_settings or ARP_DEFAULT)}


# The test patches, in PRESETS order. Times are time codes (time_ms),
# levels 0 to 127 (level_gain). Each one is there for a test or to hear
# a kind of sound the algorithms make.
TEST_PATCHES = [
    # 0: one sine carrier at full level, a 5.2 ms attack (linear in
    # amplitude) and a 64 ms release over 96 dB: pitch, level and click
    # tests, and the engine's default.
    patch("Sine", 8, [op(1.0, 127, rates=(19, 0, 0, 48))]),
    # 1: two operators, a modulator at the note's frequency into a carrier
    # at 6 times it, index pi/2 exactly (level 103: a gain of 1/8, of the
    # full scale's 4 pi), flat envelopes: the Bessel test.
    patch("Two-op", 1, [op(6.0, 127, rates=(8, 0, 0, 48)), op(1.0, 103, rates=(8, 0, 0, 48))]),
    # 2: an envelope with every stage: attack 32 ms to 0 dB, decay 1 to
    # level 103 (-18 dB) at 64 ms a 96 dB range, decay 2 to level 87
    # (-30 dB) at 128 ms, release at 256 ms: the envelope timing test.
    patch("Env test", 8, [op(1.0, 127, rates=(40, 48, 56, 64), levels=(127, 103, 87))]),
    # 3: mono, legato, a 181 ms glide: a carrier and one light modulator
    # (index 0.21), so the fundamental's pitch can be followed through the
    # glide: the mono test.
    patch("Glide lead", 1, [op(1.0, 127, rates=(10, 60, 0, 50), levels=(127, 120, 120)),
                            op(1.0, 80, rates=(10, 0, 0, 50))],
          mono=True, glide=60),
    # 4: a struck, inharmonic sound: three pairs, slow decays.
    patch("Bell", 3, [op(1.0, 127, rates=(4, 88, 96, 72), levels=(127, 104, 0)),
                      op(3.5, 100, rates=(4, 80, 90, 72), levels=(127, 96, 0)),
                      op(2.0, 120, detune=7, rates=(4, 84, 92, 72), levels=(127, 100, 0)),
                      op(5.0, 95, rates=(4, 76, 88, 72), levels=(127, 92, 0)),
                      op(3.0, 112, detune=-5, rates=(4, 80, 90, 72), levels=(127, 96, 0)),
                      op(9.2, 90, rates=(4, 72, 84, 72), levels=(127, 90, 0))]),
    # 5: a plucked bass: a three-operator stack and a pair, feedback on
    # the stack's top, fast modulator decays.
    patch("Bass", 9, [op(1.0, 127, rates=(6, 70, 0, 44), levels=(127, 116, 116)),
                      op(1.0, 108, rates=(6, 56, 0, 44), levels=(127, 92, 92)),
                      op(0.5, 120, rates=(6, 0, 0, 44)),
                      op(1.0, 127, rates=(6, 68, 0, 44), levels=(127, 112, 112)),
                      op(1.0, 104, rates=(6, 52, 0, 44), levels=(127, 84, 84)),
                      op(3.0, 96, rates=(6, 48, 0, 44), levels=(127, 80, 80))],
          feedback=5),
    # 6: six carriers at harmonic ratios, an organ-like additive sound;
    # also the heaviest: every operator sounds (the load tests).
    patch("Organ", 8, [op(0.5, 112, rates=(8, 0, 0, 40)), op(1.0, 127, rates=(8, 0, 0, 40)),
                       op(2.0, 116, rates=(8, 0, 0, 40)), op(3.0, 108, rates=(8, 0, 0, 40)),
                       op(4.0, 104, rates=(8, 0, 0, 40)), op(6.0, 100, rates=(8, 0, 0, 40))],
          feedback=2),
    # 7: a brassy stack with a pitch envelope rising a semitone into the
    # note, and velocity sensitivity on every operator: louder and brighter
    # with velocity.
    patch("Brass", 4, [op(1.0, 127, velocity=7, rates=(20, 64, 0, 52), levels=(127, 118, 118)),
                       op(1.0, 108, velocity=7, rates=(24, 64, 0, 52), levels=(127, 104, 104)),
                       op(1.0, 100, velocity=4, rates=(24, 0, 0, 52)),
                       op(2.0, 96, velocity=4, rates=(24, 0, 0, 52)),
                       op(1.0, 98, velocity=4, rates=(24, 0, 0, 52)),
                       op(1.0, 94, velocity=4, rates=(28, 0, 0, 52))],
          feedback=4, pitch_depth=1, pitch_rates=(40, 0, 50), pitch_levels=(-127, 0, 0, 0)),
    # 8: one sine carrier with velocity sensitivity 7 and a flat envelope:
    # the velocity test (its level is the carrier's alone).
    patch("Velocity", 8, [op(1.0, 127, velocity=7, rates=(8, 0, 0, 40))]),
]


def fletcher16(data):
    a = b = 0
    for x in data:
        a = (a + x) % 255
        b = (b + a) % 255
    return b << 8 | a


def encode(p):
    """The patch's FM_PATCH_BYTES bytes (docs/PATCH-FORMAT.md)."""
    b = bytearray(BYTES)
    b[0:4] = bytes((ord("F"), ord("M"), VERSION, BYTES))
    name = p["name"].encode("ascii")
    assert len(name) <= 12 and all(32 <= c < 127 for c in name), p["name"]
    b[4:4 + len(name)] = name
    b[16] = p["algorithm"]
    b[17] = p["feedback"]
    b[18] = 1 if p["mono"] else 0
    b[19] = p["glide"]
    b[20] = p["transpose"] & 0xFF
    b[21] = p["pitch_depth"] & 0xFF
    b[22:25] = bytes(p["pitch_rates"])
    b[25:29] = bytes(v & 0xFF for v in p["pitch_levels"])
    b[29:32] = arp_bytes(p.get("arp", ARP_DEFAULT))
    for i, o in enumerate(p["ops"]):
        at = OP_OFFSET + OP_BYTES * i
        if o["mode"] == RATIO:
            f = int(round(o["freq"] * 256))
        else:
            f = int(round(o["freq"] * 4))
        assert 0 <= f < 65536
        b[at] = o["mode"]
        b[at + 1], b[at + 2] = f & 0xFF, f >> 8
        b[at + 3] = o["detune"] & 0xFF
        b[at + 4] = o["level"]
        b[at + 5] = o["velocity"]
        b[at + 6:at + 10] = bytes(o["rates"])
        b[at + 10:at + 13] = bytes(o["levels"])
    s = fletcher16(b[:SUM_OFFSET])
    b[SUM_OFFSET], b[SUM_OFFSET + 1] = s & 0xFF, s >> 8
    return bytes(b)


def s8(x):
    return x - 256 if x > 127 else x


def problems(b):
    """Why b isn't a valid version 2 patch ([] if it is): the same rules
    as fm_patch_valid() in firmware/src/fm_play.c. A version 1 patch is
    taken through upgrade() first, as the firmware's store does."""
    out = []
    if len(b) != BYTES:
        return ["%d bytes, not %d" % (len(b), BYTES)]
    if b[0:4] != bytes((ord("F"), ord("M"), VERSION, BYTES)):
        out.append("header")
    if any(not (c == 0 or 32 <= c < 127) for c in b[4:16]):
        out.append("name")
    if not 1 <= b[16] <= ALGORITHMS:
        out.append("algorithm")
    if b[17] > 7 or b[18] > 1 or b[19] > 127:
        out.append("feedback, flags or glide")
    if not -24 <= s8(b[20]) <= 24 or not -48 <= s8(b[21]) <= 48:
        out.append("transpose or pitch depth")
    if any(x > 127 for x in b[22:25]) or any(s8(x) < -127 for x in b[25:29]):
        out.append("pitch envelope")
    if b[29] >> 2 & 7 >= len(ARP_MODES) or b[29] & 0x80 or b[30] & 15 >= len(ARP_RATES) \
            or not 10 <= b[31] <= 100:
        out.append("arpeggiator")
    for i in range(6):
        o = b[OP_OFFSET + OP_BYTES * i:OP_OFFSET + OP_BYTES * (i + 1)]
        if o[0] > 1 or not -100 <= s8(o[3]) <= 100 or o[4] > 127 or o[5] > 7 or any(x > 127 for x in o[6:13]):
            out.append("operator %d" % (i + 1))
    if b[SUM_OFFSET] | b[SUM_OFFSET + 1] << 8 != fletcher16(b[:SUM_OFFSET]):
        out.append("check sum")
    return out


def upgrade(b):
    """A version 1 patch (M5's, bytes 29 to 31 reserved) as version 2:
    the arpeggiator's defaults there, the version and the check sum
    anew; a version 2 patch as it is; anything else None. The firmware's
    fm_patch_upgrade() does the same (since ARP)."""
    b = bytes(b)
    if len(b) != BYTES or b[0:2] != b"FM" or b[3] != BYTES:
        return None
    if b[2] == VERSION:
        return b
    if b[2] != 1 or any(b[29:32]) or b[SUM_OFFSET] | b[SUM_OFFSET + 1] << 8 != fletcher16(b[:SUM_OFFSET]):
        return None
    c = bytearray(b)
    c[2] = VERSION
    c[29:32] = arp_bytes(ARP_DEFAULT)
    s = fletcher16(c[:SUM_OFFSET])
    c[SUM_OFFSET], c[SUM_OFFSET + 1] = s & 0xFF, s >> 8
    return bytes(c)


def source():
    lines = ["/*", " * SPDX-License-Identifier: MIT", " * SPDX-FileCopyrightText: 2026 japes98", " *",
             " * The FM engine's test patches, in the patch format's bytes (fm.h,",
             " * docs/PATCH-FORMAT.md). Generated by tools/fm_patch.py from its",
             " * TEST_PATCHES, which says what each one is for: edit those and run",
             " * `tools/fm_patch.py write`, never this file (C-UNIT checks it).", " */", "",
             '#include "fm.h"', "", "const u8 fm_patches[FM_PATCHES][FM_PATCH_BYTES] = {"]
    for i, p in enumerate(TEST_PATCHES):
        b = encode(p)
        lines.append("    /* %d: %s */ {" % (i, p["name"]))
        for k in range(0, BYTES, 16):
            lines.append("        " + " ".join("0x%02x," % x for x in b[k:k + 16]))
        lines.append("    },")
    lines.append("};")
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 2 or argv[1] not in ("write", "check"):
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    bad = [(i, problems(encode(p))) for i, p in enumerate(TEST_PATCHES)]
    bad = [(i, p) for i, p in bad if p]
    if bad:
        print("invalid test patches: %s" % bad, file=sys.stderr)
        return 1
    if argv[1] == "write":
        with open(OUT, "w") as f:
            f.write(source())
        return 0
    with open(OUT) as f:
        if f.read() != source():
            print("firmware/src/patches.c is not what tools/fm_patch.py writes", file=sys.stderr)
            return 1
    print("fm patches: %d test patches, valid, patches.c up to date" % len(TEST_PATCHES))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
