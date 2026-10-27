#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The timing goldens' policy (docs/DESIGN-NOTES.md, "Timing goldens"),
for the suites that compare fwtest's outputs with golden files.

A bigger or slower image starts a few microseconds later, and every
event of the firmware's that waits on an audio block can then move by a
block (1.451 ms) or by a MIDI byte (0.320 ms). The rules:

1. A run's end clears the audio blocks: the end asked for (--ms) falls
   at least END_BEFORE_MS before the next block's end and at least
   END_AFTER_MS after the last one. An end comes late, never early, while
   core 0 waits (docs/HARNESS.md, "Time"), and start-up only moves the
   blocks later, so the margins say how far either can go before the run
   takes one block more or less (check_end, from the run's ipb.csv).
2. MIDI out's captures are compared with a stated tolerance: the same
   bytes in the same order (the same messages, decoded), each at its
   golden time within MIDI_TOL_MS: a block and two bytes (compare_midi).
   Screens that show the live spectrum while a sound plays are compared
   exactly outside its rectangle (LIVE), which shows the sound's last
   few blocks and so moves with them; the spectrum case checks the bars
   themselves through the interface's record (compare_screen).
3. Goldens are written again only by tools/regolden.py, which proves the
   change a pure time shift first (the same bytes, notes and sound) and
   writes nothing otherwise (the shift_* functions here).
"""

import hashlib
import json
import os
import struct
import wave
import zlib

BLOCK_FRAMES = 64                       # stereo frames a block (firmware/src/audio.h)
BLOCK_MS = BLOCK_FRAMES * 544 / 24000.0  # 1.451 ms (HW-45)
BYTE_MS = 0.32                          # a MIDI byte on the wire
END_BEFORE_MS = 1.0
END_AFTER_MS = 0.2
MIDI_TOL_MS = BLOCK_MS + 2 * BYTE_MS    # 2.091 ms
QUIET = 1                               # |sample| at or under this is quiet: a level held at -96 dB leaves +-1
GAP_FRAMES = 2 * BLOCK_FRAMES           # quiet frames that part two sounds
MAX_SHIFT_FRAMES = 16 * BLOCK_FRAMES    # how far one sound may move (23 ms)
# The live spectrum on the patch view (firmware/src/views.c: SPEC_X,
# SPEC_Y, SPEC_BARS bars 4 pixels apart, SPEC_H): x, y, width, height.
LIVE = [(8, 150, 56 * 4, 40)]


# --- 1. A run's end -------------------------------------------------------

def block_ends(case_dir):
    """The time each audio block ended (ipb.csv's end_ms), or None."""
    path = os.path.join(case_dir, "ipb.csv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = [l.strip().split(",") for l in f if l.strip()][1:]
    return [float(r[1]) for r in rows]


def end_margins(ends, asked_ms):
    """(ms after the last block end at or before the end asked, ms to the
    next one), from a run's block ends; the next is extrapolated a block
    on when the run ended before it."""
    before = [e for e in ends if e <= asked_ms]
    after = [e for e in ends if e > asked_ms]
    last = before[-1] if before else 0.0
    nxt = after[0] if after else last + BLOCK_MS
    return asked_ms - last, nxt - asked_ms


def check_end(name, case_dir, asked_ms, where=None):
    """Rule 1 for one run: problems (empty if it holds, or if the run kept
    no ipb.csv), and a line saying the margins. A problem gives the fix in
    one step (the owner's answer, 2026-10-26): the exact replacement end,
    and where it goes if where(new_ms) says ("in FILE, ...")."""
    ends = block_ends(case_dir)
    if not ends:
        return [], None
    after, before = end_margins(ends, asked_ms)
    line = "  %s: ends %.3f ms after a block, %.3f ms before the next" % (name, after, before)
    if after < END_AFTER_MS or before < END_BEFORE_MS:
        ok = suggest_end(ends, asked_ms)
        if ok is None:
            fix = "no end within 1.4 ms of it keeps the policy: look at the run's ipb.csv"
        elif where:
            fix = "fix: %s" % where(fmt_ms(ok))
        else:
            fix = "fix: replace --ms %s with --ms %s" % (fmt_ms(asked_ms), fmt_ms(ok))
        return ["%s: --ms %s ends %.3f ms after a block and %.3f before the next; the policy needs %.1f and %.1f;"
                " %s" % (name, fmt_ms(asked_ms), after, before, END_AFTER_MS, END_BEFORE_MS, fix)], line
    return [], line


def suggest_end(ends, asked_ms):
    """The tenth of a millisecond that keeps rule 1 on these block ends
    with the most room both ways (the nearest to the middle of the window
    after a block's end, so the blocks can move by about 0.1 ms either way
    before the rule needs a new end), in the block asked_ms is in if it
    can be (then the run takes the same blocks as at asked_ms, and only
    its own end captures change), else the nearest (None without ends).
    Blocks past the run's last are a block period apart, exactly."""
    if not ends:
        return None
    ends = list(ends)
    while ends[-1] < asked_ms + 3:
        ends.append(ends[-1] + BLOCK_MS)
    mid = (END_AFTER_MS + BLOCK_MS - END_BEFORE_MS) / 2.0
    home = end_margins(ends, asked_ms)[0]
    best = None
    for k in range(-14, 15):
        t = round(round(asked_ms * 10) / 10.0 + k / 10.0, 1)
        a, b = end_margins(ends, t)
        if a >= END_AFTER_MS and b >= END_BEFORE_MS:
            same = abs((t - a) - (asked_ms - home)) < 1e-6
            key = (not same, abs(a - mid), abs(t - asked_ms))
            if best is None or key < best[0]:
                best = (key, t)
    return best[1] if best else None


def fmt_ms(ms):
    return ("%d" % ms) if float(ms).is_integer() else ("%g" % ms)


# --- 2. MIDI out against a golden capture, with a tolerance ------------------

def midi_csv(path):
    """midi-out.csv's rows: (ms, byte)."""
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()][1:]
    return [(float(a), int(b, 16)) for a, b in (l.split(",") for l in lines)]


def midi_txt(path):
    """midi-out.txt's lines: (ms, the message as fwtest decoded it)."""
    out = []
    with open(path) as f:
        for l in f:
            l = l.rstrip("\n")
            if l.strip():
                t, msg = l.split(" ", 1)
                out.append((float(t), msg))
    return out


def compare_rows(what, golden, got, tol=MIDI_TOL_MS):
    """(problems, the largest time difference): the same values in the same
    order, each time within tol of the golden one."""
    if [v for _, v in golden] != [v for _, v in got]:
        k = next((i for i, (a, b) in enumerate(zip(golden, got)) if a[1] != b[1]), min(len(golden), len(got)))
        return ["%s: differs from its golden file from row %d on (%d rows, golden %d)"
                % (what, k + 1, len(got), len(golden))], None
    worst = max([abs(a[0] - b[0]) for a, b in zip(golden, got)] or [0.0])
    if worst > tol + 1e-9:
        return ["%s: a row %.3f ms from its golden time (tolerance %.3f)" % (what, worst, tol)], worst
    return [], worst


def compare_midi(name, case_dir, golden_dir, tol=MIDI_TOL_MS):
    """Rule 2: the run's midi-out.csv and midi-out.txt against golden_dir's.
    (problems, a line)."""
    problems, worst = [], 0.0
    for fname, read in (("midi-out.csv", midi_csv), ("midi-out.txt", midi_txt)):
        g, o = os.path.join(golden_dir, fname), os.path.join(case_dir, fname)
        if not os.path.exists(g):
            problems.append("%s: no golden %s" % (name, fname))
            continue
        if not os.path.exists(o):
            problems.append("%s: no %s" % (name, fname))
            continue
        p, w = compare_rows("%s: %s" % (name, fname), read(g), read(o), tol)
        problems += p
        worst = max(worst, w or 0.0)
    return problems, "  %s: MIDI out as its golden capture, every byte within %.3f ms (tolerance %.3f)" % (
        name, worst, tol)


# --- 3. Proving a change a pure time shift ---------------------------------

def shift_midi(golden_path, new_path):
    """(proven, detail) for midi-out.csv or .txt: the same bytes (or
    messages) in the same order, only their times moved."""
    read = midi_csv if golden_path.endswith(".csv") else midi_txt
    g, n = read(golden_path), read(new_path)
    if [v for _, v in g] != [v for _, v in n]:
        p, _ = compare_rows(os.path.basename(new_path), g, n, tol=float("inf"))
        return False, p[0] if p else "different"
    moves = [round(b[0] - a[0], 3) for a, b in zip(g, n)]
    return True, "the same %d rows, moved %s to %s ms" % (len(g), min(moves or [0]), max(moves or [0]))


def read_frames(path):
    """A 16-bit stereo WAV's frames: [(left, right), ...]."""
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 2:
            raise ValueError("%s: not 16-bit stereo" % path)
        n = w.getnframes()
        d = struct.unpack("<%dh" % (2 * n), w.readframes(n))
    return list(zip(d[0::2], d[1::2]))


def sounds(frames):
    """The sounds: (first, end) frame ranges whose frames aren't all quiet,
    parted by at least GAP_FRAMES quiet frames."""
    out, start, quiet = [], None, 0
    for i, (l, r) in enumerate(frames):
        if abs(l) > QUIET or abs(r) > QUIET:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= GAP_FRAMES:
                out.append((start, i - quiet + 1))
                start, quiet = None, 0
    if start is not None:
        out.append((start, len(frames) - quiet))
    return out


def shift_frames(g, n):
    """(proven, detail): every sound of g is in n, frame for frame, each
    moved by a whole number of frames (at most MAX_SHIFT_FRAMES), the same
    sounds in the same order; a sound cut by the end of either run need
    only match as far as both go (so a run whose end moved, by rule 1,
    proves too: its length may differ by up to MAX_SHIFT_FRAMES). Between
    sounds both are quiet."""
    sg, sn = sounds(g), sounds(n)
    if len(sg) != len(sn):
        return False, "%d sounds, golden %d" % (len(sn), len(sg))
    moves = []
    for k, ((a0, a1), (b0, b1)) in enumerate(zip(sg, sn)):
        d = b0 - a0
        if abs(d) > MAX_SHIFT_FRAMES:
            return False, "sound %d moved %d frames (more than %d)" % (k + 1, d, MAX_SHIFT_FRAMES)
        cut = a1 == len(g) or b1 == len(n)
        if not cut and a1 - a0 != b1 - b0:
            return False, "sound %d is %d frames long, golden %d" % (k + 1, b1 - b0, a1 - a0)
        m = min(a1 - a0, b1 - b0)
        if g[a0:a0 + m] != n[b0:b0 + m]:
            i = next(i for i in range(m) if g[a0 + i] != n[b0 + i])
            return False, "sound %d differs at its frame %d" % (k + 1, i)
        moves.append(d)
    if abs(len(g) - len(n)) > MAX_SHIFT_FRAMES:
        return False, "%d frames, golden %d" % (len(n), len(g))
    return True, "the same %d sounds, moved %s to %s frames" % (len(sg), min(moves or [0]), max(moves or [0]))


def shift_wav(golden_path, new_path):
    return shift_frames(read_frames(golden_path), read_frames(new_path))


def read_png_rows(path):
    """An 8-bit RGB PNG as fwtest writes it: (width, height, rows of bytes)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s: not a PNG" % path)
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        n, kind = struct.unpack_from(">I4s", data, pos)
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, ctype, interlace) != (8, 2, 0):
                raise ValueError("%s: not 8-bit RGB, non-interlaced" % path)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw, rows, prev, stride = zlib.decompress(idat), [], bytearray(w * 3), w * 3
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, rows


def screen_diff(golden_path, new_path, rects=LIVE):
    """The pixels that differ outside rects, and inside them."""
    gw, gh, g = read_png_rows(golden_path)
    nw, nh, n = read_png_rows(new_path)
    if (gw, gh) != (nw, nh):
        return None, None
    out = inside = 0
    for y in range(gh):
        if g[y] == n[y]:
            continue
        for x in range(gw):
            if g[y][3 * x:3 * x + 3] != n[y][3 * x:3 * x + 3]:
                if any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in rects):
                    inside += 1
                else:
                    out += 1
    return out, inside


def compare_screen(name, golden_path, new_path):
    """Rule 2 for a screen with the live spectrum: problems (exact outside
    LIVE), and a line."""
    if not os.path.exists(new_path):
        return ["%s: no %s" % (name, os.path.basename(new_path))], None
    out, inside = screen_diff(golden_path, new_path)
    base = os.path.basename(new_path)
    if out is None:
        return ["%s: %s is another size than its golden image" % (name, base)], None
    if out:
        return ["%s: %s differs from its golden image in %d pixels outside the live spectrum" % (name, base, out)], None
    return [], "  %s: %s as its golden image outside the live spectrum (%d pixels in it differ)" % (name, base, inside)


def identical(a, b):
    with open(a, "rb") as f, open(b, "rb") as g:
        return f.read() == g.read()


def shift_file(golden_path, new_path):
    """(proven, detail) for a golden file and the run's output of that name:
    identical, or a pure time shift (MIDI captures and WAVs). Anything
    else (screens, RAM, console) is proven only if identical."""
    if not os.path.exists(new_path):
        return False, "no such output"
    if identical(golden_path, new_path):
        return True, "identical"
    base = os.path.basename(golden_path)
    if base in ("midi-out.csv", "midi-out.txt"):
        return shift_midi(golden_path, new_path)
    if base.endswith(".wav"):
        return shift_wav(golden_path, new_path)
    if base.endswith(".png") and os.sep + "golden-live" + os.sep in golden_path:
        out, inside = screen_diff(golden_path, new_path)
        if out == 0:
            return True, "the same outside the live spectrum (%d pixels in it differ)" % inside
        return False, "differs outside the live spectrum" if out else "another size"
    return False, "differs, and is no MIDI capture or WAV: not a time shift"


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)
