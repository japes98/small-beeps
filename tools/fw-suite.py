#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Runs the firmware's fwtest suite and checks what it captured (check
C-FW-SUITE; R-BOOT-1 to R-BOOT-5, R-CLK-1, R-IRQ-1 to R-IRQ-4, R-LCD-1
to R-LCD-5, and since M3 R-KEY-1 to R-KEY-3, R-ENC-1, R-ENC-2, R-POT-1,
R-POT-2, R-LED-1 to R-LED-3, R-INPUT-1 to R-INPUT-3).

  fw-suite.py --build DIR --out DIR

Copies DIR/app.bin (a tools/build.sh output) to out/fw/app.bin and builds
the test images (TEST_BUILDS: the same source with one SB_TEST_* define
each) to out/fw/<name>.bin, where tests/fw/boot.suite expects them, runs
the suite through tools/fwtest (the pinned image), and then checks:

- every case: the outcome the suite expects, no unmodelled accesses, core
  1 never ran;
- boot: the marker; the vector table, every slot (HW-18): source 4 is
  sb_tick, source 16 lcd_spi_done, source 5 input_scan (since M3), every
  other source its own stub in crt0.S, by the ELF's
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
  wait returned at least once per tick and (since M3) at most once per
  interrupt, and core 0 ran at most IDLE_MAX_IPT instructions per tick
  (M0's polling heartbeat: M0_IPP per period);
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

- since M3, the panel (tests/fw/scripts/; docs/REQUIREMENTS.md has the
  limits): the input record after the beacon holds the counters, each
  control's value and the last 128 events, each stamped in time base ticks
  from when main started the time base. Each case's events (control, kind,
  value, never times) are compared with tests/fw/events/<case>.txt, and
  written as events.txt beside its outputs. Latencies run from the
  script's time of a change to the event's stamp, allowing for the time
  base starting anywhere within START_SLACK. keys: every key and button
  alone gives control n for fwtest key n, press and release, within
  KEY_LATENCY; its LED lit while held and dark otherwise (leds.csv), set
  within LED_LAG_MS of its event. chords: no ghost, chatter and a glitch
  debounced, encoders exact with keys held in their columns, the panel
  screen against its golden image. encoders: slow detents within
  ENC_LATENCY, exact positions after fast, shared-column and all-at-once
  turns, and every tick interval within INTERVAL_TOL meanwhile. pot:
  steps within POT_FIRST and POT_SETTLED, one way each, no events at rest
  with noise, a rising sweep to 1023. leds (a test build): every LED at its
  brightness step within LED_STEP_TOL.

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
               "test-badinsn": "SB_TEST_BADINSN", "test-flood": "SB_TEST_FLOOD",
               "test-leds": "SB_TEST_LEDS"}
# Each case's expected outcome (the suite says the same; checked twice).
EXPECT = {"boot": "completed", "heartbeat": "completed", "heartbeat2": "completed",
          "screen": "completed", "flood": "completed", "fault": "halt", "stray": "halt",
          "badinsn": "fault", "keys": "completed", "chords": "completed", "encoders": "completed",
          "pot": "completed", "leds": "completed"}

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
IDLE_MAX_IPT = 1280        # instructions per tick, in steady state (since M2;
                           # 100 until M3's scanning: DESIGN-NOTES.md, M3)
SCAN_SLOTS = 12            # input scan interrupts a tick (input.c, since M3)
M0_IPP = 356.887           # M0's instructions per period (its last record)
STUB_SIZE = 2              # crt0.S's sb_irq_stubs
SRC_TICK = 4               # TIMER0 (HW-16, HW-19)
SRC_SPI1 = 16              # SPI1, the panel's transfers (HW-29)
SRC_SCAN = 5               # TIMER1, the input scan (HW-48, since M3)
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
    # Main counts its wakes in a register and stores the count with the
    # ticks taken whenever it has work (DESIGN-NOTES.md, M2 and M3). Since
    # M3 the scan wakes it too: at least once a tick, and at most once an
    # interrupt (the tick, SCAN_SLOTS scan slots, and an SPI1 transfer's
    # end a second), so it idles rather than spins.
    most = (SCAN_SLOTS + 1) * (loop + 1) + loop // 1000 + 2
    if not b["wakes_ticks"]:
        problems.append("heartbeat: main's idle loop never stored its wakes")
    elif not loop - 1 <= b["wakes"] <= most:
        problems.append("heartbeat: the idle wait returned %d times in %d ticks, not %d to %d"
                        % (b["wakes"], loop, loop - 1, most))
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
    want[SRC_SCAN] = symbols["input_scan"]
    wrong = [n for n in range(128) if table[n] != want[n]]
    lines.append("  vector table: %d of 128 slots as built (tick 0x%08x, SPI1 0x%08x, scan 0x%08x, stubs from 0x%08x)"
                 % (128 - len(wrong), symbols["sb_tick"], symbols["lcd_spi_done"], symbols["input_scan"],
                    symbols["sb_irq_stubs"]))
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


# Since M3: the panel's controls and LEDs (firmware/src/input.h).
INPUT_ADDR, INPUT_LEN = 0x01c00060, 0x4f0
INPUT_FIELDS = ("cycles", "events", "dropped", "taken", "led_calls", "led_time", "led_control",
                "led_lag_max", "pot_raw")
INPUT_VALUES = 51          # input_value() for 49 controls, padded
INPUT_LOG = 128
PRESS, RELEASE, TURN, MOVE = 1, 2, 3, 4
KINDS = {PRESS: "press", RELEASE: "release", TURN: "turn", MOVE: "move"}
# Control IDs (input.h): the 14 buttons, KEY1 to KEY27, then the knobs.
CONTROL_NAMES = (["OCT-", "OCT+", "FX", "SEL", "ENV", "LFO", "EDIT", "GLO", "HOME", "SAVE", "ARP",
                  "SEQ", "PLAY", "REC"] + ["KEY%d" % k for k in range(1, 28)]
                 + ["MASTER", "SELECT", "PRESETS", "ALGORITHM", "KNOB1", "KNOB2", "KNOB3", "KNOB4"])
MASTER, SELECT, PRESETS, ALGORITHM, KNOB1, KNOB2, KNOB3, KNOB4 = range(41, 49)
# fwtest's numbers -> our controls: keys and buttons 0-40 are controls 0-40
# (HW-37); encoders 0-6 (HW-39). The labels behind them are emulator-only:
# the keys case confirms number -> matrix contact -> control, by events.
FWTEST_ENCODER = (SELECT, ALGORITHM, KNOB1, KNOB2, KNOB3, KNOB4, PRESETS)
# HW-35: fwtest key -> (column, row), for the record of what was confirmed.
MATRIX = {}
for _row, _keys in ((1, (5, 11, 4, 10, 3, 9, 2, 8, None, None, None)),
                    (2, (34, 35, 36, 37, 38, 40, 39, 13, 7, 6, 12)),
                    (3, tuple(range(23, 34))),
                    (4, (0, 1, 15, 14, 17, 16, 19, 18, 20, 21, 22))):
    for _col, _k in enumerate(_keys):
        if _k is not None:
            MATRIX[_k] = (_col, _row)
# Limits (docs/REQUIREMENTS.md). Latencies are from the script's time of
# the change to the event's own time stamp; the stamp counts from when main
# started the time base, which is at most START_SLACK after fwtest's zero,
# so each check holds for any start within that (start_slack).
KEY_LATENCY = (2.5, 4.5)   # ms: four scans in a row, 1 ms apart
ENC_LATENCY = 1.5          # ms after a detent's last contact change
POT_FIRST, POT_SETTLED = 1.5, 4.5
LED_LAG_MS = 1.0           # from an event to its LED set by main
LED_FULL_DUTY = (75, 92)   # thousandths: lit in 1 of 12 scan slots (83.3)
LED_STEP = 1000.0 / 96     # one eighth of that
LED_STEP_TOL = 2
EVENTS_DIR = "tests/fw/events"


def input_name(when):
    return "ram-%08x-%x-%s.bin" % (INPUT_ADDR, INPUT_LEN, when)


def input_record(path):
    """The input record (input.h): its counters, values and the logged
    events as [(seq, control, kind, value, ticks)], oldest first."""
    with open(path, "rb") as f:
        data = f.read()
    head = dict(zip(INPUT_FIELDS, struct.unpack_from("<%dI" % len(INPUT_FIELDS), data, 0)))
    off = 4 * len(INPUT_FIELDS)
    values = list(struct.unpack_from("<%di" % INPUT_VALUES, data, off))
    off += 4 * INPUT_VALUES
    n, log = head["events"], []
    for seq in range(max(0, n - INPUT_LOG), n):
        c, k, v, t = struct.unpack_from("<BBhI", data, off + 8 * (seq % INPUT_LOG))
        log.append((seq, c, k, v, t))
    return head, values, log


SAME_SCAN = TICKS_PER_MS * 11 // 10   # events this close were decided in one scan


def event_lines(log):
    """One line per event: its place in the log, control, kind, value.
    Events decided within one scan of the first of them come in the order
    the scan reached their columns, which moves with the scan's phase
    (and so with any change of code), so each such run of different
    controls is sorted; one control's events always keep their order."""
    runs, out = [], []
    for e in log:
        if runs and e[4] - runs[-1][0][4] <= SAME_SCAN and e[1] not in [r[1] for r in runs[-1]]:
            runs[-1].append(e)
        else:
            runs.append([e])
    for run in runs:
        for seq, (_, c, k, v, _) in zip([e[0] for e in run], sorted(run, key=lambda e: (e[2], e[1], e[3]))):
            out.append("%d %s %s %d" % (seq, CONTROL_NAMES[c] if c < len(CONTROL_NAMES) else "?%d" % c,
                                        KINDS.get(k, "?%d" % k), v))
    return out


def check_events(name, case_dir, log):
    """Compares the events (control, kind, value: never their times, which
    move with any change of code) with tests/fw/events/<name>.txt, and
    writes them beside the case's outputs, to be checked by hand and
    copied there when a test is made."""
    lines = event_lines(log)
    with open(os.path.join(case_dir, "events.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    path = os.path.join(ROOT, EVENTS_DIR, name + ".txt")
    try:
        with open(path) as f:
            want = [l.rstrip("\n") for l in f if l.strip() and not l.startswith("#")]
    except OSError:
        return ["%s: no golden events %s" % (name, os.path.relpath(path, ROOT))]
    if want != lines:
        first = next((i for i, (a, b) in enumerate(zip(want, lines)) if a != b), min(len(want), len(lines)))
        return ["%s: events differ from %s at line %d: %s, expected %s (%d events, %d expected)"
                % (name, os.path.relpath(path, ROOT), first + 1, lines[first] if first < len(lines) else "none",
                   want[first] if first < len(want) else "none", len(lines), len(want))]
    return []


def latency(ticks, when_ms):
    """(earliest, latest) ms from when_ms to an event stamped ticks, for a
    time base started anywhere from fwtest's zero to START_SLACK."""
    low = ticks / TICKS_PER_MS - when_ms
    return low, low + START_SLACK / TICKS_PER_MS


def read_leds(case_dir):
    with open(os.path.join(case_dir, "leds.csv")) as f:
        rows = [l.strip().split(",") for l in f if l.strip()]
    return [(float(r[0]), [int(x) for x in r[1:]]) for r in rows[1:]]


def check_ticks_under_load(name, case_dir):
    with open(os.path.join(case_dir, "ram-01c00000-%x-end.bin" % BEACON_LEN), "rb") as f:
        b = beacon(f.read())
    lo, hi = b["interval_min"], b["interval_max"]
    line = "  ticks %d, interval %d to %d time base ticks (jitter %d)" % (b["tick_count"], lo, hi, hi - lo)
    if abs(lo - TICKS_PER_MS) > INTERVAL_TOL or abs(hi - TICKS_PER_MS) > INTERVAL_TOL:
        return ["%s: tick intervals %d to %d, not within %d of %d" % (name, lo, hi, INTERVAL_TOL, TICKS_PER_MS)], [line]
    return [], [line]


def check_keys(case_dir):
    """Every key and button alone (tests/fw/scripts/keys.txt)."""
    head, values, log = input_record(os.path.join(case_dir, input_name("end")))
    problems, lines, lats = [], [], []
    problems += check_events("keys", case_dir, log)
    if head["events"] != 82 or head["dropped"] or head["taken"] != head["events"]:
        problems.append("keys: %d events, %d dropped, %d taken: expected 82, 0, all"
                        % (head["events"], head["dropped"], head["taken"]))
    for seq, c, k, v, t in log:
        n, up = seq // 2, seq % 2
        if (c, k, v) != (n, RELEASE if up else PRESS, 0 if up else 1):
            problems.append("keys: event %d is %s %s %d, expected fwtest key %d (%s at %s) %s"
                            % (seq, CONTROL_NAMES[c] if c < 49 else c, KINDS.get(k), v, n, CONTROL_NAMES[n],
                               MATRIX[n], "release" if up else "press"))
            continue
        lo, hi = latency(t, 700 + 40 * n + 20 * up)
        lats.append((lo, hi))
        if lo < KEY_LATENCY[0] or hi > KEY_LATENCY[1]:
            problems.append("keys: key %d's %s came %.3f to %.3f ms after it, not within %s ms"
                            % (n, KINDS[k], lo, hi, KEY_LATENCY))
    if lats:
        lines.append("  41 keys and buttons, each alone: fwtest key n at its HW-35 contact gave control n"
                     " (HW-37), press and release; latency %.3f to %.3f ms"
                     % (min(l for l, _ in lats), max(h for _, h in lats)))
    lag = head["led_lag_max"] / TICKS_PER_MS
    lines.append("  LEDs: %d set by main, at most %.4f ms after their event" % (head["led_calls"], lag))
    if head["led_calls"] != 82 or lag > LED_LAG_MS:
        problems.append("keys: %d LED calls (82 expected), longest %.3f ms after the event (at most %s)"
                        % (head["led_calls"], lag, LED_LAG_MS))
    # Each LED lit for every sample inside its key's hold, once the event
    # and one scan are past, at a full share of its column's slot on
    # average over the hold (one sample's share varies: samples come late
    # while the core idles, docs/HARNESS.md "Time"); dark for every sample
    # clear of the hold.
    prev, lit, dark, held = 0.0, 0, 0, {}
    for ms, duty in read_leds(case_dir):
        for n in range(41):
            down = 700 + 40 * n
            if prev >= down + KEY_LATENCY[1] + LED_LAG_MS + 1.1 and ms <= down + 20:
                lit += 1
                held.setdefault(n, []).append(duty[n])
                if not duty[n]:
                    problems.append("leds: LED %d dark at %.0f ms while key %d is held" % (n, ms, n))
            elif ms <= down or prev >= down + 20 + KEY_LATENCY[1] + LED_LAG_MS + 1.1:
                dark += 1
                if duty[n]:
                    problems.append("leds: LED %d at %.0f ms: %d, not dark" % (n, ms, duty[n]))
        prev = ms
    for n in range(41):
        mean = sum(held.get(n, [0])) / len(held.get(n, [0]))
        if not LED_FULL_DUTY[0] <= mean <= LED_FULL_DUTY[1]:
            problems.append("leds: LED %d's mean share while held %.1f, not within %s" % (n, mean, LED_FULL_DUTY))
    means = [sum(v) / len(v) for v in held.values()]
    if means:
        lines.append("  leds.csv: each LED's mean share while held %.1f to %.1f thousandths" % (min(means), max(means)))
    lines.append("  leds.csv: %d samples lit as expected, %d dark as expected" % (lit, dark))
    if lit < 41:
        problems.append("keys: only %d LED samples inside holds" % lit)
    return problems[:20], lines


def check_chords(case_dir):
    """Chords, a would-be ghost, keys in the encoders' columns, chatter, a
    glitch (tests/fw/scripts/chords.txt)."""
    head, values, log = input_record(os.path.join(case_dir, input_name("end")))
    problems = check_events("chords", case_dir, log)
    lines = ["  %d events, %d dropped" % (head["events"], head["dropped"])]
    ghost = [e for e in log if e[1] == 35]
    if ghost:
        problems.append("chords: key 35, the rectangle's fourth corner, gave %d events" % len(ghost))
    k20 = [(e[2], e[4]) for e in log if e[1] == 20]
    if [k for k, _ in k20] != [PRESS, RELEASE]:
        problems.append("chords: the chattering key gave %s, not one press and one release" % k20)
    if any(e[1] == 21 and e[4] > 1150 * TICKS_PER_MS for e in log):
        problems.append("chords: the 1.5 ms glitch gave an event")
    if (values[SELECT], values[PRESETS]) != (3, -3):
        problems.append("chords: SELECT %d, PRESETS %d with keys held in their columns, not +3 and -3"
                        % (values[SELECT], values[PRESETS]))
    lines.append("  no ghost at the rectangle's fourth corner; chatter gave one press and one release;"
                 " the glitch none; encoders exact with keys held in their columns")
    return problems, lines


def check_encoders(case_dir):
    """Slow, fast, shared-column and all-at-once turns
    (tests/fw/scripts/encoders.txt)."""
    head, _, log = input_record(os.path.join(case_dir, input_name("1000ms")))
    problems = check_events("encoders", case_dir, log)
    lines, lats = [], []
    for seq, c, k, v, t in log:
        if seq < 14:
            enc = seq % 7
            if (c, k, v) != (FWTEST_ENCODER[enc], TURN, 1 if seq < 7 else -1):
                problems.append("encoders: event %d is %s, expected fwtest encoder %d (%s) %+d"
                                % (seq, event_lines([(seq, c, k, v, t)])[0], enc, CONTROL_NAMES[FWTEST_ENCODER[enc]],
                                   1 if seq < 7 else -1))
            lo, hi = latency(t, 700 + 20 * seq + 6)      # the detent's last change: 6 ms after its start
            lats.append((lo, hi))
            if hi < 0 or hi > ENC_LATENCY:
                problems.append("encoders: detent %d's event %.3f to %.3f ms after its last change, not within %s"
                                % (seq, lo, hi, ENC_LATENCY))
    head, values, _ = input_record(os.path.join(case_dir, input_name("end")))
    want = {SELECT: 1 - 1 + 50 - 30 + 5 + 20, PRESETS: 1 - 1 - 5 + 20, ALGORITHM: 1 - 1 - 20, KNOB1: 1 - 1 + 5 + 20,
            KNOB2: 1 - 1 - 5 - 20, KNOB3: 1 - 1 + 20, KNOB4: 1 - 1 - 20}
    got = {c: values[c] for c in want}
    if got != want or head["dropped"]:
        problems.append("encoders: positions %s, expected %s; %d dropped"
                        % ({CONTROL_NAMES[c]: v for c, v in got.items()},
                           {CONTROL_NAMES[c]: v for c, v in want.items()}, head["dropped"]))
    if lats:
        lines.append("  14 slow detents: fwtest encoder n gave its control (HW-39), +1 clockwise; latency %.3f to %.3f ms"
                     % (min(l for l, _ in lats), max(h for _, h in lats)))
    lines.append("  positions at the end: %s (%d events, %d dropped)"
                 % (", ".join("%s %+d" % (CONTROL_NAMES[c], v) for c, v in sorted(got.items())),
                    head["events"], head["dropped"]))
    more, l = check_ticks_under_load("encoders", case_dir)
    return problems + more, lines + l


def check_pot(case_dir):
    """Steps, ends, noise at rest and a sweep (tests/fw/scripts/pot.txt)."""
    _, _, log = input_record(os.path.join(case_dir, input_name("960ms")))
    problems = check_events("pot", case_dir, log)
    lines = []
    for step, target in ((700, 300), (750, 0), (800, 1023), (850, 512)):
        ev = [(v, t) for _, c, k, v, t in log if c == MASTER and step * TICKS_PER_MS - START_SLACK <= t < (step + 49) * TICKS_PER_MS]
        if not ev:
            problems.append("pot: no event after the step to %d at %d ms" % (target, step))
            continue
        first, last = latency(ev[0][1], step), latency(ev[-1][1], step)
        lines.append("  step to %4d at %d ms: %d events, the first %.3f to %.3f ms after, %d reached %.3f to %.3f ms after"
                     % (target, step, len(ev), first[0], first[1], ev[-1][0], last[0], last[1]))
        vals = [v for v, _ in ev]
        if vals != sorted(vals) and vals != sorted(vals, reverse=True):
            problems.append("pot: the step to %d went both ways: %s" % (target, vals))
        if ev[-1][0] != target or first[1] > POT_FIRST or last[1] > POT_SETTLED:
            problems.append("pot: the step to %d gave %s, first within %.3f ms, last within %.3f (limits %s, %s)"
                            % (target, [v for v, _ in ev], first[1], last[1], POT_FIRST, POT_SETTLED))
    noise = [e for e in log if e[1] == MASTER and e[4] >= 899 * TICKS_PER_MS]
    if noise:
        problems.append("pot: %d events while the reading wandered by 2 at rest" % len(noise))
    head, values, log = input_record(os.path.join(case_dir, input_name("end")))
    sweep = [v for _, c, k, v, t in log if c == MASTER and t >= 999 * TICKS_PER_MS]
    if sweep != sorted(sweep) or values[MASTER] != 1023 or head["dropped"]:
        problems.append("pot: the sweep gave %s ... ending at %d, not rising to 1023 (%d dropped)"
                        % (sweep[:8], values[MASTER], head["dropped"]))
    lines.append("  no events while the reading wandered by 2 at rest; the sweep rose in %d events to %d"
                 % (len(sweep), values[MASTER]))
    return problems, lines


def check_leds(case_dir):
    """The LED test build: LED n at (n mod 9) eighths of full."""
    problems, worst, rows = [], 0.0, read_leds(case_dir)
    for ms, duty in rows:
        if ms < 192:
            continue
        for n in range(41):
            d = abs(duty[n] - (n % 9) * LED_STEP)
            worst = max(worst, d)
            if d > LED_STEP_TOL:
                problems.append("leds: LED %d at %.0f ms: %d, not %.1f" % (n, ms, duty[n], (n % 9) * LED_STEP))
    lines = ["  41 LEDs at 9 brightness steps: every sample within %.2f thousandths of n/8 x 1000/12" % worst]
    if len(rows) < 5:
        problems.append("leds: %d samples" % len(rows))
    return problems[:20], lines


INPUT_CHECKS = {"keys": check_keys, "chords": check_chords, "encoders": check_encoders, "pot": check_pot,
                "leds": check_leds}


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
        if name in ("boot", "screen", "fault", "stray", "chords") and not result.get("golden"):
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
        elif name in INPUT_CHECKS and run.get("outcome") == EXPECT[name]:
            more, lines = INPUT_CHECKS[name](case_dir)
        problems += more
        if lines:
            print("\n".join(lines))

    for prob in problems:
        print("FAIL: " + prob)
    print("fw suite: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
