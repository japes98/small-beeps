#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The arpeggiator's model (ARP; firmware/src/arp.c, docs/DESIGN-NOTES.md,
"ARP"): which notes each step plays, and at which frame, on the internal
clock. tools/arp_suite.py predicts the firmware's steps with it, exactly;
tests/test_arp_model.py checks it by hand.

The clock counts UNIT units a MIDI clock pulse (24 a beat); at t beats a
minute a frame is UNIT_FRAME x t units, so step k of a rate of L pulses is
at k x L x UNIT units (plus SWING% of a step on odd steps), and the
firmware plays it in the block that holds it, at the frame that rounds it
up (frame 63 at most).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm_patch  # noqa: E402  (tools/, our own)

UNIT = 3750000
UNIT_FRAME = 34
FRAMES = 64                  # a block (audio.h)
RATE_PULSES = tuple(p for _, p in fm_patch.ARP_RATES)
UP, DOWN, UPDOWN, ORDER, RANDOM, CHORD = range(6)
RANDOM_SEED = 1


class Random:
    """The random mode's generator (arp.c): a fixed linear congruential one."""

    def __init__(self):
        self.x = RANDOM_SEED

    def next(self):
        self.x = (self.x * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.x


def pattern(held, a, step, rng):
    """The notes step `step` plays (a list: one, or CHORD's), for the notes
    held (notes in the order they came) and the settings a (fm_patch.arp());
    rng is the Random, which RANDOM advances."""
    n, oct_ = len(held), a["octaves"]
    if not n:
        return []
    order = list(held) if a["mode"] == ORDER else sorted(held)
    count = n * oct_

    def fold(k):
        while k > 127:
            k -= 12
        return k
    if a["mode"] == CHORD:
        o = step % oct_
        return [fold(x + 12 * o) for x in order]
    if a["mode"] == DOWN:
        j = count - 1 - step % count
    elif a["mode"] == UPDOWN:
        if count == 1:
            j = 0
        else:
            i = step % (2 * count - 2)
            j = i if i < count else 2 * count - 2 - i
    elif a["mode"] == RANDOM:
        j = (rng.next() >> 8) % count
    else:
        j = step % count
    return [fold(order[j % n] + 12 * (j // n))]


def sequence(held, a, steps):
    """The first `steps` steps' notes, with the same notes held throughout."""
    rng = Random()
    return [pattern(held, a, k, rng) for k in range(steps)]


def step_units(a, k):
    """Step k's time from the grid's start, in units."""
    l = RATE_PULSES[a["rate"]]
    return k * l * UNIT + (l * (UNIT // 100) * a["swing"] if k % 2 else 0)


def gate_units(a):
    return RATE_PULSES[a["rate"]] * (UNIT // 100) * a["gate"]


def frame_of(t, tempo):
    """The frame (from the grid's start, which is a block's first frame)
    at which the firmware plays an event t units in: in the block that
    holds it, rounded up, at most that block's last frame."""
    r = UNIT_FRAME * tempo
    block = t // (FRAMES * r)
    at = -(-(t - block * FRAMES * r) // r)
    return block * FRAMES + min(at, FRAMES - 1)


def step_frames(a, steps, tempo):
    """Each step's frame from the first step's, on the internal clock."""
    return [frame_of(step_units(a, k), tempo) for k in range(steps)]


def off_frames(a, steps, tempo):
    """Each step's note off frame from the first step's: GATE% of a step
    after it, the next step at the latest."""
    out = []
    for k in range(steps):
        t = step_units(a, k) + gate_units(a)
        out.append(frame_of(min(t, step_units(a, k + 1)), tempo))
    return out


def ideal_ms(a, k, tempo):
    """Step k's ideal time from the first step's, in milliseconds."""
    return step_units(a, k) / (UNIT * 24.0 * tempo / 60000.0)
