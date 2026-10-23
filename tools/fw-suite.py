#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Runs the firmware's fwtest suite and checks what it captured (check
C-FW-SUITE; R-BOOT-1 to R-BOOT-5, R-CLK-1, R-IRQ-1 to R-IRQ-4, R-LCD-1
to R-LCD-5).

  fw-suite.py --build DIR --out DIR

Copies DIR/app.bin (a tools/build.sh output) to out/fw/app.bin and builds
the test images (TEST_BUILDS: the same source with one SB_TEST_* define
each) to out/fw/<name>.bin, where tests/fw/boot.suite expects them, runs
the suite through tools/fwtest (the pinned image), and then checks:

- every case: the outcome the suite expects, no unmodelled accesses, core
  1 never ran;
- boot: the marker; the vector table, every slot (HW-18): source 4 is
  sb_tick, every other source its own stub in crt0.S, by the ELF's
  symbols; the clock measured at startup: SB_CLOCK_CYCLES core cycles take
  CLOCK_TICKS time base ticks (240 MHz against 24 MHz, HW-11, HW-13); the
  first tick within FIRST_TICK_MS of the start (from the last tick's time
  base, the ticks taken and the shortest interval, since the run itself
  ends late); nothing halted;
- heartbeat (one emulated second; the image idles between ticks, so
  captures come late, docs/HARNESS.md "Time"): at every capture at least
  one of the beacon's two heartbeat copies is consistent, beats ==
  ticks // 24000, and both are when its seq is even (the tick handler
  writes them in turn, DESIGN-NOTES.md M1); the consistent copy's ticks
  are no earlier than the time asked less one tick period and START_SLACK,
  and no more than LATE_MS after it; beats never go back. At the end:
  the last tick's time base lies within one tick period (and START_SLACK)
  before fwtest's emulated end time; every interval between two ticks is
  within INTERVAL_TOL of 24 000 time base ticks (1 ms), and so is their
  spread (jitter); beats and ticks taken differ by at most one; the idle
  wait returned once per tick, and core 0 ran at most IDLE_MAX_IPT
  instructions per tick (M0's polling heartbeat: M0_IPP per period);
- fault and stray: the halt recorded in the beacon (reason and source),
  and the console line, by golden file;
- badinsn: fwtest's own fault outcome for an undecodable instruction. A
  limit of the harness, not firmware behaviour: no handler of ours runs
  (SR-1).
- heartbeat2 (since M2): the heartbeat's checks again over 2.25 s; with
  heartbeat (1.25 s) its difference is the steady state, which may take
  at most IDLE_MAX_IPT instructions a tick. The idle loop's wakes, stored
  once a second, equal the ticks taken since it began, within one.
- screen (since M2): every pixel of the address pattern (300 ms) against
  its formula; the test screen's border, corners and ramps pixel by pixel
  (800 ms); one heartbeat later (1 500 ms) only the heartbeat's rows
  changed; the beacon's screen and seconds shown at each capture; and the
  three pictures against golden images.
- flood (since M2): a test build that sends whole frames back to back from
  500 ms: every tick interval still within INTERVAL_TOL, far more frames
  than ticks, and the picture still the test screen. Prints how long a
  whole frame takes.

Prints what it saw for the record, and exits 1 if anything failed.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = "tests/fw/boot.suite"
IMAGE = os.path.join("out", "fw", "app.bin")
# Test images: name -> define (firmware/src/probe.c).
TEST_BUILDS = {"test-fault": "SB_TEST_FAULT", "test-stray": "SB_TEST_STRAY",
               "test-badinsn": "SB_TEST_BADINSN", "test-flood": "SB_TEST_FLOOD"}
# Each case's expected outcome (the suite says the same; checked twice).
EXPECT = {"boot": "completed", "heartbeat": "completed", "heartbeat2": "completed",
          "screen": "completed", "flood": "completed", "fault": "halt", "stray": "halt",
          "badinsn": "fault"}

MARKER = 0x44304253        # "SB0D", firmware/src/sb.h
TICKS_PER_MS = 24000       # HW-13
START_SLACK = 240          # ticks: 10 microseconds (main starts the time base)
# Startup clears .bss before main starts the time base, at most this many
# core cycles a word (2 measured in M2), 10 cycles a time base tick: since
# M2's frame buffer that is about a quarter of a millisecond, so the slack
# grows with the image's bss (start_slack).
CLEAR_CYCLES_PER_WORD = 3
LATE_MS = 30               # a waiting core 0 crosses many ticks in one run
INTERVAL_TOL = 24          # ticks: 1 microsecond, 0.1% of a tick period
CLOCK_TICKS = (240, 241)   # SB_CLOCK_CYCLES = 2402 cycles at 10 a tick
FIRST_TICK_MS = 2          # the first tick: one period after main starts it
IDLE_MAX_IPT = 100         # instructions per tick, in steady state (since M2)
M0_IPP = 356.887           # M0's instructions per period (its last record)
STUB_SIZE = 2              # crt0.S's sb_irq_stubs
SRC_TICK = 4               # TIMER0 (HW-16, HW-19)
SRC_SPI1 = 16              # SPI1, the panel's transfers (HW-29)
HALT_STRAY, HALT_FAULT, HALT_STACK = 1, 2, 3

BEACON_FIELDS = ("marker", "beats", "ticks", "period", "seq", "beats_b", "ticks_b",
                 "tick_count", "interval_min", "interval_max", "wakes", "clock",
                 "halt_reason", "halt_source", "halt_reti",
                 # since M2 (firmware/src/sb.h)
                 "screen", "loop_ticks", "frames", "frame_ticks", "render_ticks", "beat_ticks",
                 "shown", "chunks", "wakes_ticks")
BEACON_LEN = 4 * len(BEACON_FIELDS)
CAPTURE = re.compile(r"^ram-01c00000-%x-(?P<when>[0-9.]+ms|end)\.bin$" % BEACON_LEN)
VECTORS = "ram-01c7fe00-200-end.bin"


def beacon(data):
    return dict(zip(BEACON_FIELDS, struct.unpack("<%dI" % len(BEACON_FIELDS), data)))


def elf_symbols(path):
    """name -> value, from an ELF32 little-endian file's symbol table."""
    with open(path, "rb") as f:
        elf = f.read()
    shoff, = struct.unpack_from("<I", elf, 0x20)
    shentsize, shnum = struct.unpack_from("<HH", elf, 0x2E)
    sections = [struct.unpack_from("<IIIIIIIIII", elf, shoff + i * shentsize) for i in range(shnum)]
    syms = {}
    for s in sections:
        if s[1] != 2:      # SHT_SYMTAB
            continue
        strtab = sections[s[6]]
        for off in range(s[4], s[4] + s[5], 16):
            name, value = struct.unpack_from("<II", elf, off)
            end = elf.index(b"\0", strtab[4] + name)
            syms[elf[strtab[4] + name:end].decode()] = value
    return syms


def check_case(name, result):
    """Problems with one case's result.json."""
    run = result.get("run", {})
    problems = []
    if run.get("outcome") != EXPECT[name]:
        problems.append("%s: outcome %s, not %s (%s)" % (name, run.get("outcome"), EXPECT[name],
                                                         run.get("detail")))
    if run.get("unmodelled_accesses"):
        problems.append("%s: unmodelled accesses %s" % (name, run["unmodelled_accesses"]))
    if run.get("instructions", {}).get("core1", 0) != 0:
        problems.append("%s: core 1 ran" % name)
    return problems


def consistent(b):
    """The heartbeat copies that are consistent: [(beats, ticks), ...]."""
    return [(be, ti) for be, ti in ((b["beats"], b["ticks"]), (b["beats_b"], b["ticks_b"]))
            if be == ti // TICKS_PER_MS]


def start_slack(bss):
    """Time base ticks by which main may start the time base after fwtest's
    emulated time began: START_SLACK and the clearing of bss."""
    return START_SLACK + (bss // 4 * CLEAR_CYCLES_PER_WORD + 9) // 10


def check_beacon(when_ms, b, end_ms=None):
    """Problems with one beacon captured at when_ms (the time asked; end_ms
    is result.json's emulated_ms for the capture at the end)."""
    problems = []
    if b["marker"] != MARKER:
        problems.append("marker 0x%08x, not 0x%08x" % (b["marker"], MARKER))
    if b["period"] != TICKS_PER_MS:
        problems.append("period %d, not %d" % (b["period"], TICKS_PER_MS))
        return problems
    good = consistent(b)
    if not good:
        return problems + ["neither heartbeat copy is consistent: %d beats after %d ticks, %d after %d"
                           % (b["beats"], b["ticks"], b["beats_b"], b["ticks_b"])]
    if b["seq"] % 2 == 0 and (len(good) != 2 or good[0] != good[1]):
        problems.append("seq %d is even, but the two heartbeat copies differ" % b["seq"])
    ticks = good[-1][1]
    if end_ms is not None:
        end = round(end_ms * TICKS_PER_MS)
        if not -START_SLACK <= end - ticks <= TICKS_PER_MS + INTERVAL_TOL + START_SLACK:
            problems.append("last tick at %d ticks, not within one tick period before the end (%d)"
                            % (ticks, end))
    else:
        low = round((when_ms - 1) * TICKS_PER_MS) - INTERVAL_TOL - START_SLACK
        high = round((when_ms + LATE_MS) * TICKS_PER_MS)
        if not low <= ticks <= high:
            problems.append("%d ticks at %s ms, not within %d to %d" % (ticks, when_ms, low, high))
    return problems


def check_ticks(b, result):
    """Problems with the end beacon's tick statistics, and lines to print."""
    problems = []
    n, lo, hi = b["tick_count"], b["interval_min"], b["interval_max"]
    loop = b["wakes_ticks"] - b["loop_ticks"]
    lines = ["  ticks %d, interval %d to %d time base ticks (jitter %d); the idle loop's wait returned"
             " %d times in its first %d ticks" % (n, lo, hi, hi - lo, b["wakes"], loop)]
    if n < 2:
        return ["heartbeat: %d ticks" % n], lines
    for name, v in (("shortest", lo), ("longest", hi)):
        if abs(v - TICKS_PER_MS) > INTERVAL_TOL:
            problems.append("heartbeat: %s tick interval %d, not within %d of %d"
                            % (name, v, INTERVAL_TOL, TICKS_PER_MS))
    if hi - lo > INTERVAL_TOL:
        problems.append("heartbeat: tick jitter %d, more than %d" % (hi - lo, INTERVAL_TOL))
    beats = consistent(b)[-1][0] if consistent(b) else b["beats"]
    if abs(beats - n) > 1:
        problems.append("heartbeat: %d beats but %d ticks" % (beats, n))
    # Since M2 main counts its wakes in a register and stores the count
    # once a second, with the ticks taken then (DESIGN-NOTES.md, M2).
    if not b["wakes_ticks"]:
        problems.append("heartbeat: main's idle loop never stored its wakes")
    elif b["wakes"] not in (loop - 1, loop, loop + 1):
        problems.append("heartbeat: the idle wait returned %d times in %d ticks" % (b["wakes"], loop))
    return problems, lines


def check_steady(results, ends):
    """Steady-state instructions per tick, from the two heartbeat cases
    (the same options but their length: R-IRQ-1 since M2), and lines."""
    (r1, r2), (b1, b2) = results, ends
    i1, i2 = r1["run"]["instructions"]["core0"], r2["run"]["instructions"]["core0"]
    dn = b2["tick_count"] - b1["tick_count"]
    if dn <= 0:
        return ["heartbeat2: no more ticks than heartbeat"], []
    ipt = (i2 - i1) / dn
    lines = ["  steady state: %d instructions for %d ticks between the two heartbeat runs: %.3f a tick"
             " (M0's polling heartbeat: %.1f a period)" % (i2 - i1, dn, ipt, M0_IPP)]
    if ipt > IDLE_MAX_IPT:
        return ["heartbeat: %.1f instructions a tick in steady state, more than %d" % (ipt, IDLE_MAX_IPT)], lines
    return [], lines


def check_heartbeat(case_dir, result):
    """Problems with the heartbeat case's captures, and lines to print."""
    end_ms = float(result["run"]["emulated_ms"])
    caps = []
    for n in os.listdir(case_dir):
        m = CAPTURE.match(n)
        if m:
            when = m.group("when")
            caps.append((end_ms if when == "end" else float(when[:-2]), when, n))
    caps.sort()
    problems, lines, last, end = [], [], -1, None
    if len(caps) < 2:
        problems.append("heartbeat: %d beacon captures, expected several" % len(caps))
    for when_ms, when, n in caps:
        with open(os.path.join(case_dir, n), "rb") as f:
            data = f.read()
        if len(data) != BEACON_LEN:
            problems.append("%s: %d bytes" % (n, len(data)))
            continue
        b = beacon(data)
        lines.append("  %-6s seq %5d  beats %5d  ticks %9d (%.3f ms)  copy b %5d %9d"
                     % (when, b["seq"], b["beats"], b["ticks"], b["ticks"] / TICKS_PER_MS,
                        b["beats_b"], b["ticks_b"]))
        problems += ["heartbeat %s: %s" % (when, p) for p in
                     check_beacon(when_ms, b, end_ms if when == "end" else None)]
        good = consistent(b)
        if good and good[-1][0] < last:
            problems.append("heartbeat %s: beats went back from %d to %d" % (when, last, good[-1][0]))
        last = good[-1][0] if good else last
        if when == "end":
            end = b
    if end is not None:
        more, tick_lines = check_ticks(end, result)
        problems += more
        lines += tick_lines
    return problems, lines


def check_boot(case_dir, symbols):
    """Problems with the boot case's beacon and vector table, and lines."""
    problems, lines = [], []
    with open(os.path.join(case_dir, "ram-01c00000-%x-end.bin" % BEACON_LEN), "rb") as f:
        b = beacon(f.read())
    lines.append("  clock: %d time base ticks for 2402 cycles; %d ticks by the end"
                 % (b["clock"], b["tick_count"]))
    if b["marker"] != MARKER:
        problems.append("boot: marker 0x%08x" % b["marker"])
    if b["clock"] not in CLOCK_TICKS:
        problems.append("boot: the clock measured %d time base ticks, not %s (240 MHz)"
                        % (b["clock"], " or ".join(map(str, CLOCK_TICKS))))
    good = consistent(b)
    if b["tick_count"] < 1 or not good:
        problems.append("boot: no tick (or no consistent heartbeat) by the end")
    else:
        # No later than this: every interval is at least interval_min.
        first = good[-1][1] - (b["tick_count"] - 1) * b["interval_min"]
        lines.append("  first tick by %d time base ticks (%.3f ms)" % (first, first / TICKS_PER_MS))
        if first > FIRST_TICK_MS * TICKS_PER_MS:
            problems.append("boot: the first tick came after %.3f ms, not within %d ms"
                            % (first / TICKS_PER_MS, FIRST_TICK_MS))
    if b["halt_reason"]:
        problems.append("boot: halted (reason %d)" % b["halt_reason"])
    with open(os.path.join(case_dir, VECTORS), "rb") as f:
        table = struct.unpack("<128I", f.read())
    want = [symbols["sb_irq_stubs"] + STUB_SIZE * n for n in range(128)]
    want[SRC_TICK] = symbols["sb_tick"]
    want[SRC_SPI1] = symbols["lcd_spi_done"]
    wrong = [n for n in range(128) if table[n] != want[n]]
    lines.append("  vector table: %d of 128 slots as built (tick 0x%08x, SPI1 0x%08x, stubs from 0x%08x)"
                 % (128 - len(wrong), symbols["sb_tick"], symbols["lcd_spi_done"], symbols["sb_irq_stubs"]))
    if wrong:
        problems.append("boot: vector table slots %s are not the handler built for them" % wrong)
    return problems, lines


def check_halt(name, case_dir, reason, source):
    with open(os.path.join(case_dir, "ram-01c00000-%x-end.bin" % BEACON_LEN), "rb") as f:
        b = beacon(f.read())
    line = "  halt: reason %d, source %d, reti 0x%08x" % (b["halt_reason"], b["halt_source"],
                                                          b["halt_reti"])
    if (b["halt_reason"], b["halt_source"]) != (reason, source):
        return ["%s: halted with reason %d source %d, not %d %d"
                % (name, b["halt_reason"], b["halt_source"], reason, source)], [line]
    return [], [line]


def read_png(path):
    """(width, height, rows of (r, g, b)) from an 8-bit RGB, non-interlaced
    PNG, as fwtest writes them (docs/HARNESS.md, lcd-WHEN.png)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, w = 8, b"", None
    while pos < len(data):
        n, kind = struct.unpack_from(">I4s", data, pos)
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if (depth, ctype, interlace) != (8, 2, 0):
                raise ValueError("not 8-bit RGB without interlace")
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw, stride, rows, prev = zlib.decompress(idat), w * 3, [], bytearray(w * 3)
    for y in range(h):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 3] if i >= 3 else 0
            b, c = prev[i], prev[i - 3] if i >= 3 else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[i:i + 3]) for i in range(0, stride, 3)])
        prev = line
    return w, h, rows


def rgb8(r5, g6, b5):
    """The colour fwtest's PNG shows for an RGB565 pixel."""
    return (r5 * 255 // 31, g6 * 255 // 63, b5 * 255 // 31)


# screen.c's layouts (firmware/src/screen.c): where the test screen puts
# what, in pixels from the top left.
WHITE, RED, GREEN, BLUE, YELLOW = (rgb8(31, 63, 31), rgb8(31, 0, 0), rgb8(0, 63, 0),
                                   rgb8(0, 0, 31), rgb8(31, 63, 0))
CORNERS = (((3, 3), RED), ((225, 3), GREEN), ((3, 225), BLUE), ((225, 225), YELLOW))
BEAT_ROWS = range(200, 216)


def check_pattern(rows):
    """Problems with the address pattern: every pixel's colour must say
    where it is (screen.c's screen_pattern), so the orientation, the
    colour order and every pixel's address are checked at once."""
    bad = [(x, y) for y in range(240) for x in range(240)
           if rows[y][x] != rgb8(x >> 3, y >> 2, (x & 7) << 2 | (y & 3))]
    if bad:
        return ["screen: %d pixels of the address pattern are wrong, the first at %s" % (len(bad), bad[0])]
    return []


def check_test_screen(rows):
    """Problems with the test screen's fixed parts: the border, the corner
    squares and the three ramps (screen.c's screen_test)."""
    problems = []
    edge = [(x, y) for y in range(240) for x in range(240)
            if (x in (0, 239) or y in (0, 239)) and rows[y][x] != WHITE]
    if edge:
        problems.append("screen: %d edge pixels are not white, the first at %s" % (len(edge), edge[0]))
    for (x0, y0), colour in CORNERS:
        wrong = [(x, y) for y in range(y0, y0 + 12) for x in range(x0, x0 + 12) if rows[y][x] != colour]
        if wrong:
            problems.append("screen: the corner square at %s is not %s (first wrong pixel %s: %s)"
                            % ((x0, y0), colour, wrong[0], rows[wrong[0][1]][wrong[0][0]]))
    for name, y0, steps, width, colour in (("red", 44, 32, 6, lambda i: rgb8(i, 0, 0)),
                                           ("green", 60, 64, 3, lambda i: rgb8(0, i, 0)),
                                           ("blue", 76, 32, 6, lambda i: rgb8(0, 0, i))):
        wrong = [(x, y) for i in range(steps) for x in range(24 + width * i, 24 + width * (i + 1))
                 for y in range(y0, y0 + 14) if rows[y][x] != colour(i)]
        if wrong:
            problems.append("screen: the %s ramp is wrong at %s" % (name, wrong[0]))
    return problems


def check_screen(case_dir):
    """Problems with the screen case: the address pattern at 300 ms, the
    test screen at 800 ms and 1 500 ms (the heartbeat one second on, and
    nothing else changed), and the beacon captured with each; lines."""
    problems, lines, shots, beacons = [], [], {}, {}
    for when in (300, 800, 1500):
        try:
            w, h, shots[when] = read_png(os.path.join(case_dir, "lcd-%dms.png" % when))
        except (OSError, ValueError) as e:
            return ["screen: lcd-%dms.png: %s" % (when, e)], lines
        if (w, h) != (240, 240):
            problems.append("screen: lcd-%dms.png is %dx%d" % (when, w, h))
        with open(os.path.join(case_dir, "ram-01c00000-%x-%dms.bin" % (BEACON_LEN, when)), "rb") as f:
            beacons[when] = beacon(f.read())
    if problems:
        return problems, lines
    problems += check_pattern(shots[300])
    problems += check_test_screen(shots[800])
    changed = {y for y in range(240) for x in range(240) if shots[800][y][x] != shots[1500][y][x]}
    if not changed or not changed <= set(BEAT_ROWS):
        problems.append("screen: from 800 to 1 500 ms rows %s changed, not some of the heartbeat's %d to %d only"
                        % (sorted(changed)[:8], BEAT_ROWS[0], BEAT_ROWS[-1]))
    for when, (screen, shown) in ((300, (1, None)), (800, (2, 0)), (1500, (2, 1))):
        b = beacons[when]
        good = consistent(b)
        seconds = good[-1][0] // 1000 if good else None
        lines.append("  %4d ms: screen %d, heartbeat shown %d s, beats %s" % (when, b["screen"], b["shown"],
                                                                            good[-1][0] if good else "?"))
        if b["screen"] != screen:
            problems.append("screen %d ms: the beacon says screen %d, not %d" % (when, b["screen"], screen))
        if shown is not None and (b["shown"] != shown or seconds != shown):
            problems.append("screen %d ms: heartbeat shown %d at %s whole seconds, expected %d"
                            % (when, b["shown"], seconds, shown))
    return problems, lines


def check_flood(case_dir, result, screen_dir):
    """Problems with the flood case (whole frames back to back): every tick
    interval still within INTERVAL_TOL, frames going out, and the picture
    still the test screen; lines with the frame time."""
    with open(os.path.join(case_dir, "ram-01c00000-%x-end.bin" % BEACON_LEN), "rb") as f:
        b = beacon(f.read())
    problems, lines = [], []
    n, lo, hi = b["tick_count"], b["interval_min"], b["interval_max"]
    ms = float(result["run"]["emulated_ms"])
    instr = result["run"]["instructions"]["core0"]
    flood = b["frames"] - 2       # the two frames before the flood
    lines.append("  ticks %d, interval %d to %d time base ticks (jitter %d), during %d whole frames"
                 % (n, lo, hi, hi - lo, flood))
    if flood > 0:
        lines.append("  a whole frame: %d time base ticks (%.2f us) from its window to its last transfer"
                     " started; %.0f core-0 instructions a frame over the run"
                     % (b["frame_ticks"], b["frame_ticks"] / 24.0, instr / b["frames"]))
    for name, v in (("shortest", lo), ("longest", hi)):
        if abs(v - TICKS_PER_MS) > INTERVAL_TOL:
            problems.append("flood: %s tick interval %d, not within %d of %d" % (name, v, INTERVAL_TOL, TICKS_PER_MS))
    # The flood starts with the test screen, at 500 ms; a frame is a few
    # microseconds of the core's time in fwtest, so far more frames than
    # ticks go out.
    if n < ms - 2 or flood < 10 * (n - 500):
        problems.append("flood: %d ticks and %d frames in %.3f ms, expected a tick a ms and more than ten"
                        " frames a tick after 500 ms" % (n, flood, ms))
    try:
        _, _, end = read_png(os.path.join(case_dir, "lcd-end.png"))
        _, _, ref = read_png(os.path.join(screen_dir, "lcd-800ms.png"))
        if end != ref:
            problems.append("flood: the picture at the end is not the test screen")
    except (OSError, ValueError) as e:
        problems.append("flood: %s" % e)
    return problems, lines


def build_tests(build):
    """Builds the test images; returns problems."""
    problems = []
    for name, define in sorted(TEST_BUILDS.items()):
        out = os.path.join(ROOT, "out", "fw", "build-" + name)
        p = subprocess.run(["sh", "tools/build.sh", "build", "--out", out, "--define", define],
                           cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            problems.append("%s: the build failed:\n%s" % (name, p.stdout.decode("utf-8", "replace")[-2000:]))
            continue
        shutil.copyfile(os.path.join(out, "app.bin"), os.path.join(ROOT, "out", "fw", name + ".bin"))
        print("built %s (-D%s)" % (name, define))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", required=True, help="a tools/build.sh output folder")
    ap.add_argument("--out", required=True, help="where the suite's outputs go (empty or new)")
    a = ap.parse_args()

    os.makedirs(os.path.join(ROOT, os.path.dirname(IMAGE)), exist_ok=True)
    shutil.copyfile(os.path.join(a.build, "app.bin"), os.path.join(ROOT, IMAGE))
    global START_SLACK
    size = os.path.join(a.build, "app.size")
    if os.path.exists(size):
        with open(size) as f:
            sizes = dict(l.split() for l in f if l.strip())
        print("image size: " + ", ".join("%s %s" % kv for kv in sizes.items()))
        START_SLACK = start_slack(int(sizes.get("bss", 0)))
        print("start slack: %d time base ticks (bss cleared before main starts the time base)" % START_SLACK)
    symbols = elf_symbols(os.path.join(a.build, "app.elf"))
    problems = build_tests(a.build)

    out = os.path.abspath(a.out)
    p = subprocess.run(["sh", "tools/fwtest", "suite", SUITE, "--out", out], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace").rstrip())
    if p.returncode != 0:
        problems.append("fwtest suite exited %d" % p.returncode)

    steady = {}
    for name in EXPECT:
        path = os.path.join(out, name, "result.json")
        if not os.path.exists(path):
            problems.append("%s: no result.json" % name)
            continue
        with open(path) as f:
            result = json.load(f)
        problems += check_case(name, result)
        run = result.get("run", {})
        print("%s: %s at %s ms, %s instructions on core 0"
              % (name, run.get("outcome"), run.get("emulated_ms"),
                 run.get("instructions", {}).get("core0")))
        for g in result.get("golden") or []:
            print("  golden %s: %s" % (g.get("name"), g.get("result")))
            if g.get("result") != "match":
                problems.append("%s: golden %s: %s" % (name, g.get("name"), g.get("detail")))
        if name in ("boot", "screen", "fault", "stray") and not result.get("golden"):
            problems.append("%s: no golden files compared" % name)
        case_dir = os.path.join(out, name)
        more, lines = [], []
        if name == "boot":
            more, lines = check_boot(case_dir, symbols)
        elif name in ("heartbeat", "heartbeat2") and "emulated_ms" in run:
            more, lines = check_heartbeat(case_dir, result)
            with open(os.path.join(case_dir, "ram-01c00000-%x-end.bin" % BEACON_LEN), "rb") as f:
                steady[name] = (result, beacon(f.read()))
            if len(steady) == 2:
                m, l = check_steady([steady["heartbeat"][0], steady["heartbeat2"][0]],
                                    [steady["heartbeat"][1], steady["heartbeat2"][1]])
                more, lines = more + m, lines + l
        elif name == "screen":
            more, lines = check_screen(case_dir)
        elif name == "flood" and "emulated_ms" in run:
            more, lines = check_flood(case_dir, result, os.path.join(out, "screen"))
        elif name == "fault":
            more, lines = check_halt(name, case_dir, HALT_STACK, 1)
        elif name == "stray":
            more, lines = check_halt(name, case_dir, HALT_STRAY, 127)
        problems += more
        if lines:
            print("\n".join(lines))

    for prob in problems:
        print("FAIL: " + prob)
    print("fw suite: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
