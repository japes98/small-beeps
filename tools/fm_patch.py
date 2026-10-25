#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The FM engine's patch format, version 1, and our own test patches
(M5; docs/PATCH-FORMAT.md, R-FM-7).

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
VERSION = 1
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


def patch(name, algorithm, ops, feedback=0, mono=False, glide=0, transpose=0,
          pitch_depth=0, pitch_rates=(0, 0, 0), pitch_levels=(0, 0, 0, 0)):
    ops = list(ops) + [OFF] * (6 - len(ops))
    return {"name": name, "algorithm": algorithm, "feedback": feedback, "mono": mono,
            "glide": glide, "transpose": transpose, "pitch_depth": pitch_depth,
            "pitch_rates": tuple(pitch_rates), "pitch_levels": tuple(pitch_levels), "ops": ops}


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


# The preset bank (M8b; docs/M8-PROPOSAL.md, "Presets"): 64 presets in 8
# categories of 8, programs 25 to 88 after the test patches and the user
# slots. Written from scratch here, as the test patches are: ratios,
# levels and envelopes chosen by reasoning about each kind of sound, each
# with a line saying what it is for. No voice bank or SysEx dump was
# opened, converted or compared, and no names were borrowed. A modulator's
# level L gives an index of about 4 pi x 2^((L - 127) / 8): 127 4 pi, 119
# 2 pi, 111 pi, 103 pi/2, 95 pi/4. Time codes: 2^(t/8) ms over a stage's
# whole range (48 64 ms, 56 128 ms, 64 256 ms, 72 512 ms, 80 1 s, 88 2 s,
# 96 4 s).
CATEGORIES = ("keys", "bass", "bells and mallets", "brass and winds", "pads", "leads",
              "plucks and strings", "percussion and effects")
PRESETS = []   # (category, what it is for, patch)
# The carriers of each algorithm (firmware/src/fm.c, fm_algorithms), for
# the trims below.
CARRIERS = {1: (0,), 2: (0, 3), 3: (0, 2, 4), 4: (0,), 5: (0,), 6: (0, 1, 2), 7: (0, 3), 8: (0, 1, 2, 3, 4, 5),
            9: (0, 2, 3), 10: (0,)}
# Each preset's trim: its carriers' levels moved by this many steps (0.75
# dB each) so the bank plays at one level (tools/preset_suite.py measures
# it, TARGET_DB). Made by that tool's --calibrate, from a render.
TRIM = {
        'Brass': 40,
        'Bright EP': 23,
        'Buzz Sitar': 7,
        'Chip Lead': -11,
        'Choir': -5,
        'Church Bell': -11,
        'Clarinet': -13,
        'Cowbell': 46,
        'Crystal': 7,
        'Dark Pad': -2,
        'Drawbars': 28,
        'FM Bass': 12,
        'Fat Lead': -3,
        'Flute': 32,
        'Fretless': -9,
        'Funk Clav': 60,
        'Glass Pad': 4,
        'Glock': 6,
        'Harmonica': 2,
        'Harp': 14,
        'Harpsichord': 5,
        'Hi-Hat': 61,
        'Horns': -7,
        'Kalimba': 33,
        'Kick': 12,
        'Koto': -7,
        'Laser': -8,
        'Marimba': 35,
        'Metal Hit': -10,
        'Music Box': 13,
        'Nylon Gtr': 35,
        'Oboe': 5,
        'Organ Pad': 27,
        'Perc Organ': 25,
        'Pipe Lead': -5,
        'Pizzicato': 44,
        'Pluck': 35,
        'Pluck Bass': 29,
        'Reed Sax': 3,
        'Rubber Bass': -7,
        'Saw Bass': 10,
        'Saw Lead': -4,
        'Slap Bass': 64,
        'Snare': 58,
        'Soft Keys': -9,
        'Soft Lead': -9,
        'Space Pad': 9,
        'Square Lead': -11,
        'Steel Str': 10,
        'String Pad': 1,
        'Sub Bass': -11,
        'Sweep Pad': -6,
        'Sync Lead': -10,
        'Tine Piano': 19,
        'Tom': -6,
        'Toy Piano': 52,
        'Trumpet': 45,
        'Tubular': 13,
        'Twang': 40,
        'Vibes': 11,
        'Warm Pad': -3,
        'Whistle': -10,
        'Wind': -3,
        'Wood Bass': 43,
}

def add(category, purpose, p):
    for k in CARRIERS[p["algorithm"]]:
        o = p["ops"][k]
        if o["level"]:
            p["ops"][k] = dict(o, level=max(1, min(127, o["level"] + TRIM.get(p["name"], 0))))
    PRESETS.append((category, purpose, p))

# --- keys ---------------------------------------------------------------
add(0, "an electric piano: a soft tine (ratio 14, fast decay) over a mellow pair",
    patch("Tine Piano", 3, [
        op(1.0, 127, velocity=3, rates=(0, 72, 88, 60), levels=(127, 104, 84)),
        op(1.0, 98, velocity=5, rates=(0, 64, 80, 60), levels=(127, 96, 80)),
        op(1.0, 116, detune=3, velocity=3, rates=(0, 76, 90, 60), levels=(127, 100, 84)),
        op(14.0, 84, velocity=6, rates=(0, 44, 56, 48), levels=(127, 50, 0))]))
add(0, "a brighter electric piano for comping: more index, a harder bark at high velocity",
    patch("Bright EP", 3, [
        op(1.0, 127, velocity=3, rates=(0, 70, 86, 58), levels=(127, 104, 86)),
        op(1.0, 108, velocity=6, rates=(0, 60, 78, 58), levels=(127, 92, 76)),
        op(1.0, 116, detune=-4, velocity=3, rates=(0, 74, 88, 58), levels=(127, 100, 84)),
        op(7.0, 92, velocity=7, rates=(0, 40, 56, 48), levels=(127, 56, 0))]))
add(0, "a drawbar organ: six sine carriers at 16', 8', 5 1/3', 4', 2 2/3', 2'",
    patch("Drawbars", 8, [
        op(0.5, 118, rates=(6, 0, 0, 30)), op(1.0, 127, rates=(6, 0, 0, 30)),
        op(1.5, 112, rates=(6, 0, 0, 30)), op(2.0, 116, rates=(6, 0, 0, 30)),
        op(3.0, 108, rates=(6, 0, 0, 30)), op(4.0, 110, rates=(6, 0, 0, 30))]))
add(0, "an organ with a percussive third harmonic that decays at each note",
    patch("Perc Organ", 8, [
        op(0.5, 112, rates=(6, 0, 0, 30)), op(1.0, 127, rates=(6, 0, 0, 30)),
        op(2.0, 112, rates=(6, 0, 0, 30)), op(3.0, 120, rates=(0, 72, 88, 30), levels=(127, 60, 0)),
        op(4.0, 104, rates=(6, 0, 0, 30))]))
add(0, "a clavinet-like funk key: a bright nasal pluck that dies quickly",
    patch("Funk Clav", 3, [
        op(1.0, 127, velocity=4, rates=(0, 64, 80, 40), levels=(127, 96, 0)),
        op(3.0, 112, velocity=6, rates=(0, 56, 72, 40), levels=(127, 84, 0))]))
add(0, "a harpsichord: two plucked stacks, the upper one an octave higher, no sustain",
    patch("Harpsichord", 2, [
        op(1.0, 127, rates=(0, 72, 92, 44), levels=(127, 100, 0)),
        op(3.0, 106, rates=(0, 60, 80, 44), levels=(127, 84, 0)),
        op(7.0, 92, rates=(0, 48, 64, 44), levels=(127, 64, 0)),
        op(2.0, 112, detune=4, rates=(0, 70, 90, 44), levels=(127, 98, 0)),
        op(5.0, 98, rates=(0, 56, 76, 44), levels=(127, 80, 0)),
        op(1.0, 92, rates=(0, 52, 70, 44), levels=(127, 72, 0))], feedback=3))
add(0, "a toy piano: a short inharmonic strike (a 3.5 modulator) on a sine",
    patch("Toy Piano", 3, [
        op(1.0, 127, velocity=3, rates=(0, 64, 80, 50), levels=(127, 92, 0)),
        op(3.5, 100, velocity=5, rates=(0, 48, 64, 48), levels=(127, 70, 0)),
        op(4.0, 100, rates=(0, 56, 72, 48), levels=(127, 80, 0)),
        op(1.0, 90, rates=(0, 48, 64, 48), levels=(127, 70, 0))]))
add(0, "soft keys for chords: a gentle attack and a warm, slowly fading tone",
    patch("Soft Keys", 5, [
        op(1.0, 127, rates=(12, 76, 96, 64), levels=(127, 112, 96)),
        op(1.0, 92, rates=(8, 72, 90, 64), levels=(127, 104, 90)),
        op(2.0, 84, rates=(8, 64, 80, 64), levels=(127, 96, 80))]))

# --- bass ---------------------------------------------------------------
add(1, "an FM bass: a punchy pluck whose brightness falls fast, with a sub an octave down",
    patch("FM Bass", 3, [
        op(1.0, 127, velocity=3, rates=(0, 80, 96, 44), levels=(127, 118, 110)),
        op(1.0, 110, velocity=5, rates=(0, 48, 64, 44), levels=(127, 90, 80)),
        op(0.5, 112, rates=(0, 84, 96, 44), levels=(127, 116, 110))], transpose=-12))
add(1, "a slap bass: a thumb's hard attack with a high pop that dies at once",
    patch("Slap Bass", 1, [
        op(1.0, 127, velocity=4, rates=(0, 64, 88, 40), levels=(127, 104, 84)),
        op(3.0, 112, velocity=6, rates=(0, 40, 56, 40), levels=(127, 72, 40)),
        op(9.0, 104, velocity=7, rates=(0, 24, 40, 32), levels=(127, 40, 0))], transpose=-12))
add(1, "a sub bass: an almost pure sine an octave down, for under a mix",
    patch("Sub Bass", 3, [
        op(1.0, 127, rates=(4, 0, 0, 40)), op(1.0, 72, rates=(4, 0, 0, 40))], transpose=-24))
add(1, "a wooden, acoustic-like bass: a soft thump and a short body",
    patch("Wood Bass", 3, [
        op(1.0, 127, velocity=4, rates=(4, 72, 92, 48), levels=(127, 104, 0)),
        op(1.0, 100, velocity=5, rates=(0, 56, 76, 48), levels=(127, 84, 0)),
        op(2.0, 90, rates=(4, 64, 84, 48), levels=(127, 90, 0))], transpose=-12))
add(1, "a synth bass: a feedback stack that reads as a sawtooth, plus a sine sub",
    patch("Saw Bass", 9, [
        op(0.5, 110, rates=(0, 0, 0, 40)), OFF,
        OFF,
        op(1.0, 124, rates=(0, 64, 80, 40), levels=(127, 112, 104)),
        op(1.0, 110, rates=(0, 56, 72, 40), levels=(127, 100, 92)),
        op(1.0, 100, rates=(0, 0, 0, 40))], feedback=6, transpose=-12))
add(1, "a rubber bass: the pitch drops a few semitones into each note",
    patch("Rubber Bass", 3, [
        op(1.0, 127, rates=(0, 72, 88, 44), levels=(127, 112, 100)),
        op(1.0, 104, rates=(0, 52, 68, 44), levels=(127, 84, 70))],
          transpose=-12, pitch_depth=4, pitch_rates=(56, 0, 40), pitch_levels=(127, 0, 0, 0)))
add(1, "a plucked bass: short, round, for fast lines",
    patch("Pluck Bass", 3, [
        op(1.0, 127, velocity=3, rates=(0, 60, 76, 40), levels=(127, 96, 0)),
        op(2.0, 100, velocity=5, rates=(0, 48, 64, 40), levels=(127, 76, 0))], transpose=-12))
add(1, "a fretless bass: a soft attack and a glide between held notes (mono)",
    patch("Fretless", 3, [
        op(1.0, 127, rates=(24, 80, 96, 48), levels=(127, 116, 108)),
        op(1.0, 96, rates=(40, 72, 88, 48), levels=(127, 104, 96))],
          mono=True, glide=56, transpose=-12))

# --- bells and mallets ----------------------------------------------------
add(2, "a tubular bell: three inharmonic pairs, long decays",
    patch("Tubular", 3, [
        op(1.0, 127, rates=(0, 96, 104, 80), levels=(127, 96, 0)),
        op(3.5, 104, rates=(0, 88, 100, 80), levels=(127, 84, 0)),
        op(2.0, 112, detune=5, rates=(0, 92, 102, 80), levels=(127, 92, 0)),
        op(5.19, 98, rates=(0, 84, 98, 80), levels=(127, 80, 0)),
        op(0.56, 104, rates=(0, 98, 106, 80), levels=(127, 96, 0)),
        op(1.41, 94, rates=(0, 90, 100, 80), levels=(127, 84, 0))]))
add(2, "a glockenspiel: high, bright and short-ringing",
    patch("Glock", 3, [
        op(1.0, 127, rates=(0, 80, 92, 72), levels=(127, 84, 0)),
        op(3.5, 96, rates=(0, 56, 72, 64), levels=(127, 64, 0)),
        op(4.0, 112, rates=(0, 72, 88, 64), levels=(127, 80, 0)),
        op(8.0, 90, rates=(0, 48, 64, 56), levels=(127, 56, 0))], transpose=12))
add(2, "a vibraphone: a soft mallet on a pure, sustaining bar",
    patch("Vibes", 3, [
        op(1.0, 127, rates=(0, 88, 100, 72), levels=(127, 104, 0)),
        op(4.0, 86, rates=(0, 56, 72, 64), levels=(127, 60, 0)),
        op(3.0, 96, rates=(0, 80, 96, 72), levels=(127, 92, 0)),
        op(1.0, 76, rates=(0, 60, 76, 64), levels=(127, 70, 0))]))
add(2, "a marimba: a woody strike with its fourth-partial overtone and a quick click",
    patch("Marimba", 3, [
        op(1.0, 127, rates=(0, 66, 82, 50), levels=(127, 84, 0)),
        op(4.0, 100, rates=(0, 40, 56, 44), levels=(127, 60, 0)),
        op(10.0, 92, rates=(0, 32, 48, 40), levels=(127, 40, 0)),
        op(1.0, 80, rates=(0, 40, 56, 40), levels=(127, 50, 0))]))
add(2, "a music box: a tiny comb, bright and ringing",
    patch("Music Box", 3, [
        op(1.0, 127, rates=(0, 80, 96, 72), levels=(127, 90, 0)),
        op(5.0, 92, rates=(0, 56, 72, 64), levels=(127, 64, 0)),
        op(3.0, 104, rates=(0, 72, 88, 64), levels=(127, 84, 0)),
        op(7.0, 84, rates=(0, 48, 64, 56), levels=(127, 56, 0))], transpose=12))
add(2, "a church bell: five inharmonic modulators on one carrier, a long strike",
    patch("Church Bell", 5, [
        op(1.0, 127, rates=(0, 100, 108, 88), levels=(127, 96, 0)),
        op(0.56, 92, rates=(0, 96, 104, 88), levels=(127, 84, 0)),
        op(1.19, 90, rates=(0, 92, 100, 88), levels=(127, 80, 0)),
        op(2.0, 96, rates=(0, 88, 100, 88), levels=(127, 80, 0)),
        op(2.76, 86, rates=(0, 80, 96, 88), levels=(127, 72, 0)),
        op(5.4, 80, rates=(0, 72, 88, 88), levels=(127, 64, 0))]))
add(2, "crystal: glassy high partials that shimmer as they fade",
    patch("Crystal", 3, [
        op(1.0, 127, rates=(0, 88, 100, 76), levels=(127, 92, 0)),
        op(7.11, 96, rates=(0, 72, 88, 72), levels=(127, 76, 0)),
        op(2.0, 108, detune=7, rates=(0, 84, 96, 76), levels=(127, 88, 0)),
        op(11.3, 88, rates=(0, 64, 80, 72), levels=(127, 64, 0))]))
add(2, "a kalimba: a thumb piano's soft pluck and slightly odd overtone",
    patch("Kalimba", 3, [
        op(1.0, 127, rates=(0, 66, 84, 56), levels=(127, 90, 0)),
        op(6.0, 92, rates=(0, 40, 56, 48), levels=(127, 56, 0)),
        op(3.03, 90, rates=(0, 52, 68, 48), levels=(127, 70, 0)),
        op(1.0, 80, rates=(0, 40, 56, 48), levels=(127, 60, 0))]))

# --- brass and winds -----------------------------------------------------
add(3, "brass: the modulator's attack slower than the carrier's, so the tone brightens in",
    patch("Brass", 1, [
        op(1.0, 127, velocity=4, rates=(32, 64, 0, 48), levels=(127, 118, 118)),
        op(1.0, 116, velocity=6, rates=(40, 72, 0, 48), levels=(127, 106, 102)),
        op(1.0, 98, velocity=4, rates=(40, 0, 0, 48))], feedback=0))
add(3, "a trumpet: a bright brass with a scoop up into each note",
    patch("Trumpet", 1, [
        op(1.0, 127, velocity=4, rates=(24, 64, 0, 44), levels=(127, 120, 120)),
        op(1.0, 120, velocity=6, rates=(32, 64, 0, 44), levels=(127, 110, 106)),
        op(1.0, 104, velocity=5, rates=(32, 0, 0, 44))],
          pitch_depth=1, pitch_rates=(48, 0, 0), pitch_levels=(-127, 0, 0, 0)))
add(3, "horns: a mellow brass section, a slower swell",
    patch("Horns", 2, [
        op(1.0, 127, rates=(44, 0, 0, 56)), op(1.0, 104, rates=(52, 72, 0, 56), levels=(127, 98, 96)),
        op(1.0, 84, rates=(52, 0, 0, 56)),
        op(1.0, 120, detune=5, rates=(44, 0, 0, 56)), op(1.0, 100, rates=(52, 72, 0, 56), levels=(127, 96, 94)),
        op(2.0, 80, rates=(52, 0, 0, 56))]))
add(3, "a saxophone-like reed: a breathy, odd-rich stack",
    patch("Reed Sax", 1, [
        op(1.0, 127, velocity=4, rates=(20, 0, 0, 44)),
        op(1.0, 110, velocity=5, rates=(28, 64, 0, 44), levels=(127, 104, 100)),
        op(3.0, 92, velocity=4, rates=(28, 0, 0, 44))], feedback=0))
add(3, "a flute: a near-sine with a soft attack and a hint of breath",
    patch("Flute", 3, [
        op(1.0, 127, rates=(36, 0, 0, 44)), op(1.0, 80, rates=(40, 0, 0, 44)),
        op(2.0, 84, rates=(36, 0, 0, 44)), OFF,
        op(1.0, 70, rates=(28, 56, 0, 44), levels=(127, 50, 40)), op(9.3, 96, rates=(20, 0, 0, 44))],
          feedback=7))
add(3, "a clarinet: the 1:2 pair gives odd harmonics, the hollow woody tone",
    patch("Clarinet", 3, [
        op(1.0, 127, rates=(28, 0, 0, 44)), op(2.0, 106, rates=(32, 64, 0, 44), levels=(127, 104, 102))]))
add(3, "an oboe: a bright, nasal double reed",
    patch("Oboe", 3, [
        op(1.0, 127, rates=(28, 0, 0, 44)), op(1.0, 114, rates=(28, 64, 0, 44), levels=(127, 108, 106)),
        op(3.0, 92, rates=(28, 0, 0, 44)), op(2.0, 96, rates=(28, 0, 0, 44))]))
add(3, "a harmonica: reedy and a little detuned",
    patch("Harmonica", 3, [
        op(1.0, 127, rates=(20, 0, 0, 40)), op(1.0, 108, detune=6, rates=(24, 0, 0, 40)),
        op(2.0, 96, rates=(20, 0, 0, 40)), op(3.0, 90, rates=(24, 0, 0, 40))]))

# --- pads -------------------------------------------------------------------
add(4, "a warm pad: three gently modulated pairs, detuned, slow in and out",
    patch("Warm Pad", 3, [
        op(1.0, 120, detune=-6, rates=(80, 0, 0, 88)), op(1.0, 90, rates=(84, 0, 0, 88)),
        op(1.0, 120, rates=(80, 0, 0, 88)), op(2.0, 82, rates=(84, 0, 0, 88)),
        op(1.0, 120, detune=6, rates=(80, 0, 0, 88)), op(1.0, 90, rates=(84, 0, 0, 88))]))
add(4, "a string pad: two detuned carriers and a feedback stack, a slow bow",
    patch("String Pad", 6, [
        op(1.0, 118, detune=7, rates=(72, 0, 0, 84)), op(1.0, 118, detune=-7, rates=(72, 0, 0, 84)),
        op(1.0, 120, rates=(72, 0, 0, 84)), op(1.0, 104, rates=(76, 0, 0, 84)),
        op(1.0, 96, rates=(76, 0, 0, 84)), op(1.0, 92, rates=(76, 0, 0, 84))], feedback=5))
add(4, "a choir-like pad: soft, vowel-ish partials",
    patch("Choir", 7, [
        op(1.0, 124, rates=(76, 0, 0, 84)), op(2.0, 84, rates=(80, 0, 0, 84)),
        op(4.0, 76, rates=(80, 0, 0, 84)),
        op(1.0, 116, detune=5, rates=(76, 0, 0, 84)), op(3.0, 80, rates=(80, 0, 0, 84)),
        op(5.0, 72, rates=(80, 0, 0, 84))]))
add(4, "a glass pad: a bell's partials with a slow attack",
    patch("Glass Pad", 3, [
        op(1.0, 124, rates=(72, 0, 0, 90)), op(3.5, 86, rates=(76, 0, 0, 90)),
        op(2.0, 112, detune=4, rates=(72, 0, 0, 90)), op(7.0, 80, rates=(76, 0, 0, 90)),
        op(1.0, 108, detune=-4, rates=(72, 0, 0, 90)), op(1.41, 78, rates=(76, 0, 0, 90))]))
add(4, "a dark pad: low and soft, the modulators barely open",
    patch("Dark Pad", 3, [
        op(0.5, 124, rates=(84, 0, 0, 92)), op(0.5, 80, rates=(88, 0, 0, 92)),
        op(1.0, 116, detune=4, rates=(84, 0, 0, 92)), op(1.0, 76, rates=(88, 0, 0, 92))]))
add(4, "a sweep pad: the modulators' level rises over seconds, the tone opening up",
    patch("Sweep Pad", 3, [
        op(1.0, 122, detune=-5, rates=(64, 0, 0, 88)), op(1.0, 104, rates=(100, 0, 0, 88)),
        op(1.0, 122, detune=5, rates=(64, 0, 0, 88)), op(2.0, 98, rates=(104, 0, 0, 88))]))
add(4, "a space pad: inharmonic and drifting",
    patch("Space Pad", 3, [
        op(1.0, 120, rates=(88, 0, 0, 96)), op(1.41, 88, rates=(96, 0, 0, 96)),
        op(1.5, 112, detune=9, rates=(88, 0, 0, 96)), op(2.76, 80, rates=(96, 0, 0, 96)),
        op(0.5, 112, rates=(88, 0, 0, 96)), op(3.17, 76, rates=(96, 0, 0, 96))]))
add(4, "an organ pad: drawbars with a slow swell",
    patch("Organ Pad", 8, [
        op(0.5, 112, rates=(72, 0, 0, 80)), op(1.0, 127, rates=(72, 0, 0, 80)),
        op(2.0, 112, rates=(72, 0, 0, 80)), op(3.0, 100, rates=(72, 0, 0, 80)),
        op(4.0, 100, rates=(72, 0, 0, 80))]))

# --- leads --------------------------------------------------------------
add(5, "a square-ish lead: the 1:2 pair at a high index, mono with a short glide",
    patch("Square Lead", 3, [
        op(1.0, 127, rates=(4, 0, 0, 40)), op(2.0, 116, rates=(4, 0, 0, 40))], mono=True, glide=40))
add(5, "a saw lead: a high-feedback carrier, mono",
    patch("Saw Lead", 8, [
        op(1.0, 116, detune=-4, rates=(4, 0, 0, 40)), OFF, OFF, OFF, OFF,
        op(1.0, 124, detune=4, rates=(4, 0, 0, 40))], feedback=6, mono=True, glide=40))
add(5, "a sync-like lead: a high-ratio modulator that falls in index over a note",
    patch("Sync Lead", 3, [
        op(1.0, 127, rates=(0, 0, 0, 40)), op(5.0, 118, rates=(0, 80, 96, 40), levels=(127, 96, 90))],
          mono=True, glide=32))
add(5, "a whistle: a pure, high sine with a soft start",
    patch("Whistle", 8, [op(2.0, 127, rates=(32, 0, 0, 40))], mono=True, glide=48))
add(5, "a fat lead: three detuned bright pairs",
    patch("Fat Lead", 3, [
        op(1.0, 120, detune=-8, rates=(4, 0, 0, 40)), op(1.0, 110, rates=(4, 0, 0, 40)),
        op(1.0, 120, rates=(4, 0, 0, 40)), op(2.0, 104, rates=(4, 0, 0, 40)),
        op(1.0, 120, detune=8, rates=(4, 0, 0, 40)), op(1.0, 110, rates=(4, 0, 0, 40))], mono=True, glide=36))
add(5, "a pipe lead: hollow and breathy, a little slower",
    patch("Pipe Lead", 3, [
        op(1.0, 127, rates=(28, 0, 0, 44)), op(2.0, 96, rates=(32, 0, 0, 44)),
        op(3.0, 90, rates=(28, 0, 0, 44)), op(1.0, 72, rates=(32, 0, 0, 44))], mono=True, glide=40))
add(5, "a chip lead: hard-edged and buzzy, like an old game",
    patch("Chip Lead", 3, [
        op(1.0, 127, rates=(0, 0, 0, 24)), op(1.0, 120, rates=(0, 0, 0, 24))], feedback=0, mono=True))
add(5, "a soft lead: round and gentle, for slow melodies",
    patch("Soft Lead", 3, [
        op(1.0, 127, rates=(24, 0, 0, 48)), op(1.0, 92, rates=(32, 0, 0, 48))], mono=True, glide=48))

# --- plucks and strings --------------------------------------------------------
add(6, "a pluck: a short, bright note with a fast-closing tone",
    patch("Pluck", 3, [
        op(1.0, 127, velocity=3, rates=(0, 64, 80, 48), levels=(127, 84, 0)),
        op(1.0, 112, velocity=5, rates=(0, 44, 60, 44), levels=(127, 70, 0))]))
add(6, "a nylon guitar: a soft pluck and a warm body",
    patch("Nylon Gtr", 2, [
        op(1.0, 127, velocity=3, rates=(0, 72, 92, 52), levels=(127, 100, 0)),
        op(3.0, 96, velocity=5, rates=(0, 52, 68, 48), levels=(127, 72, 0)),
        op(1.0, 84, rates=(0, 48, 64, 48), levels=(127, 64, 0)),
        op(2.0, 104, rates=(0, 64, 84, 52), levels=(127, 90, 0)),
        op(1.0, 92, rates=(0, 48, 64, 48), levels=(127, 70, 0))]))
add(6, "a harp: a clear pluck that rings",
    patch("Harp", 3, [
        op(1.0, 127, rates=(0, 76, 96, 64), levels=(127, 96, 0)),
        op(2.0, 96, rates=(0, 52, 68, 56), levels=(127, 70, 0)),
        op(4.0, 92, rates=(0, 68, 88, 60), levels=(127, 84, 0)),
        op(1.0, 80, rates=(0, 44, 60, 56), levels=(127, 60, 0))]))
add(6, "a koto-like pluck: a twangy 3:1 modulator and a small bend down",
    patch("Koto", 3, [
        op(1.0, 127, rates=(0, 70, 88, 52), levels=(127, 92, 0)),
        op(3.0, 108, rates=(0, 48, 64, 48), levels=(127, 74, 0))],
          pitch_depth=1, pitch_rates=(40, 0, 0), pitch_levels=(64, 0, 0, 0)))
add(6, "a sitar-like drone pluck: a buzzing near-unison modulator",
    patch("Buzz Sitar", 3, [
        op(1.0, 127, rates=(0, 80, 96, 60), levels=(127, 104, 0)),
        op(1.0, 112, detune=9, rates=(0, 72, 88, 60), levels=(127, 96, 0)),
        op(2.0, 96, rates=(0, 72, 88, 60), levels=(127, 92, 0)),
        op(4.0, 92, detune=-6, rates=(0, 64, 80, 60), levels=(127, 84, 0))]))
add(6, "a banjo-like pluck: bright, short and twangy",
    patch("Twang", 3, [
        op(1.0, 127, rates=(0, 60, 76, 40), levels=(127, 84, 0)),
        op(4.0, 106, rates=(0, 40, 56, 40), levels=(127, 64, 0)),
        op(2.0, 98, rates=(0, 52, 68, 40), levels=(127, 80, 0)),
        op(7.0, 92, rates=(0, 32, 48, 40), levels=(127, 50, 0))]))
add(6, "pizzicato strings: a quick, round pluck",
    patch("Pizzicato", 3, [
        op(1.0, 127, rates=(0, 56, 72, 44), levels=(127, 80, 0)),
        op(1.0, 96, rates=(0, 44, 60, 44), levels=(127, 70, 0)),
        op(2.0, 104, rates=(0, 52, 68, 44), levels=(127, 76, 0)),
        op(3.0, 88, rates=(0, 40, 56, 44), levels=(127, 60, 0))]))
add(6, "a steel string: a bright metallic pluck with a long tail",
    patch("Steel Str", 3, [
        op(1.0, 127, rates=(0, 80, 96, 60), levels=(127, 96, 0)),
        op(4.0, 100, rates=(0, 44, 60, 56), levels=(127, 66, 0)),
        op(2.0, 108, rates=(0, 76, 92, 60), levels=(127, 92, 0)),
        op(1.0, 92, rates=(0, 52, 68, 56), levels=(127, 74, 0))]))

# --- percussion and effects ---------------------------------------------
add(7, "a kick: a low sine whose pitch drops two octaves in a few tens of ms",
    patch("Kick", 8, [op(1.0, 127, rates=(0, 56, 64, 40), levels=(127, 60, 0))],
          transpose=-24, pitch_depth=24, pitch_rates=(44, 0, 0), pitch_levels=(127, 0, 0, 0)))
add(7, "a snare: a short tone with a noisy, high-feedback modulator",
    patch("Snare", 3, [
        op(1.0, 120, rates=(0, 48, 56, 40), levels=(127, 60, 0)),
        op(1.5, 96, rates=(0, 40, 48, 40), levels=(127, 40, 0)),
        OFF, OFF,
        op(1.0, 124, rates=(0, 52, 60, 40), levels=(127, 60, 0)),
        op(7.7, 127, rates=(0, 48, 56, 40), levels=(127, 60, 0))], feedback=7))
add(7, "a tom: a pitched drum, its pitch falling a little",
    patch("Tom", 3, [
        op(1.0, 127, rates=(0, 64, 76, 48), levels=(127, 80, 0)),
        op(1.5, 92, rates=(0, 40, 56, 44), levels=(127, 56, 0))],
          transpose=-12, pitch_depth=7, pitch_rates=(56, 0, 0), pitch_levels=(127, 0, 0, 0)))
add(7, "a hi-hat: inharmonic high partials, very short",
    patch("Hi-Hat", 5, [
        op(9.3, 120, rates=(0, 48, 56, 32), levels=(127, 50, 0)),
        op(7.1, 116, rates=(0, 36, 44, 32), levels=(127, 50, 0)),
        op(11.7, 116, rates=(0, 36, 44, 32), levels=(127, 50, 0)),
        op(13.3, 112, rates=(0, 36, 44, 32), levels=(127, 50, 0)),
        op(5.9, 112, rates=(0, 36, 44, 32), levels=(127, 50, 0)),
        op(17.0, 120, rates=(0, 36, 44, 32), levels=(127, 50, 0))], feedback=7, transpose=12))
add(7, "a cowbell: two inharmonic carriers, a short metallic clank",
    patch("Cowbell", 8, [
        op(1.0, 124, rates=(0, 56, 72, 44), levels=(127, 84, 0)),
        op(1.48, 120, rates=(0, 56, 72, 44), levels=(127, 84, 0))]))
add(7, "a laser: the pitch dives four octaves in a fraction of a second",
    patch("Laser", 3, [
        op(1.0, 127, rates=(0, 0, 0, 48)), op(2.0, 110, rates=(0, 0, 0, 48))],
          pitch_depth=24, pitch_rates=(64, 0, 0), pitch_levels=(127, -127, -127, -127)))
add(7, "wind: a slow, noisy swell from a feedback modulator",
    patch("Wind", 3, [
        OFF, OFF, OFF, OFF,
        op(1.0, 120, rates=(88, 0, 0, 96)), op(11.0, 127, rates=(88, 0, 0, 96))], feedback=7))
add(7, "a metal hit: an inharmonic strike that rings for a while",
    patch("Metal Hit", 5, [
        op(1.0, 127, rates=(0, 88, 100, 80), levels=(127, 80, 0)),
        op(1.41, 108, rates=(0, 80, 96, 80), levels=(127, 76, 0)),
        op(2.43, 104, rates=(0, 72, 92, 80), levels=(127, 72, 0)),
        op(3.71, 100, rates=(0, 64, 88, 80), levels=(127, 64, 0)),
        op(4.98, 96, rates=(0, 56, 80, 80), levels=(127, 60, 0)),
        op(6.33, 100, rates=(0, 48, 72, 80), levels=(127, 56, 0))], feedback=4))



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
    """Why b isn't a valid version 1 patch ([] if it is): the same rules
    as fm_patch_valid() in firmware/src/fm.c."""
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
    if any(x > 127 for x in b[22:25]) or any(s8(x) < -127 for x in b[25:29]) or any(b[29:32]):
        out.append("pitch envelope or reserved")
    for i in range(6):
        o = b[OP_OFFSET + OP_BYTES * i:OP_OFFSET + OP_BYTES * (i + 1)]
        if o[0] > 1 or not -100 <= s8(o[3]) <= 100 or o[4] > 127 or o[5] > 7 or any(x > 127 for x in o[6:13]):
            out.append("operator %d" % (i + 1))
    if b[SUM_OFFSET] | b[SUM_OFFSET + 1] << 8 != fletcher16(b[:SUM_OFFSET]):
        out.append("check sum")
    return out


def source():
    lines = ["/*", " * SPDX-License-Identifier: MIT", " * SPDX-FileCopyrightText: 2026 japes98", " *",
             " * The FM engine's test patches and (since M8b) its preset bank, in the",
             " * patch format's bytes (fm.h, docs/PATCH-FORMAT.md). Generated by",
             " * tools/fm_patch.py from its TEST_PATCHES and PRESETS, which say what",
             " * each one is for: edit those and run `tools/fm_patch.py write`, never",
             " * this file (C-UNIT checks it).", " */", "",
             '#include "fm.h"', "", "const u8 fm_patches[FM_PATCHES][FM_PATCH_BYTES] = {"]
    for i, p in enumerate(TEST_PATCHES):
        b = encode(p)
        lines.append("    /* %d: %s */ {" % (i, p["name"]))
        for k in range(0, BYTES, 16):
            lines.append("        " + " ".join("0x%02x," % x for x in b[k:k + 16]))
        lines.append("    },")
    lines.append("};")
    lines += ["", "const u8 fm_presets[FM_PRESETS][FM_PATCH_BYTES] = {"]
    for i, (category, purpose, p) in enumerate(PRESETS):
        b = encode(p)
        lines.append("    /* P%02d (%s): %s */ {" % (i + 1, CATEGORIES[category], p["name"]))
        for k in range(0, BYTES, 16):
            lines.append("        " + " ".join("0x%02x," % x for x in b[k:k + 16]))
        lines.append("    },")
    lines.append("};")
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 2 or argv[1] not in ("write", "check"):
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    bad = [(i, problems(encode(p))) for i, p in enumerate(TEST_PATCHES + [q for _, _, q in PRESETS])]
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
    print("fm patches: %d test patches and %d presets, valid, patches.c up to date" % (len(TEST_PATCHES), len(PRESETS)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
