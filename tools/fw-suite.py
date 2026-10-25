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

- every case: the outcome the suite expects, no unmodelled accesses
  (until M5 also that core 1 never ran: since M5 it runs the FM engine);
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
  within LED_LAG_MS of its event (the firmware's own measure). chords: no ghost, chatter and a glitch
  debounced, encoders exact with keys held in their columns, the panel
  screen against its golden image. encoders: slow detents within
  ENC_LATENCY, exact positions after fast, shared-column and all-at-once
  turns, and every tick interval within INTERVAL_TOL meanwhile. pot:
  steps within POT_FIRST and POT_SETTLED, one way each, no events at rest
  with noise, a rising sweep to 1023. leds (a test build): every LED at its
  brightness step within LED_STEP_TOL. ledshow (a test build, the keys
  script): from input_led to the scan first driving that LED, within
  LED_SHOW_MS (one scan).

- since M7, the store's cases (R-STORE-1 to R-STORE-9): runs chained
  through the flash fwtest saves, by tools/store_suite.py after the
  suite (its docstring says what each checks);

- since M5, the FM engine (tests/fw/scripts/fm*.txt; R-FM-*; the engine's
  record follows the audio record; the test patches' values come from
  tools/fm_patch.py): fmbessel, test patch 1's sidebands against
  |J_n(pi/2)| by a least-squares fit at the known frequencies; fmenv,
  test patch 2's stages (each end where its fitted line meets its level,
  its rate, the held level, the attack's linearity, no click); fmmono,
  legato and glide (one sound, one note, the pitch along the glide, no
  new attack); fmsteal, 17 notes on 16 voices, one stolen with no click;
  fmvel, the velocity test build's levels; fmgold and fmgold2, every test
  patch against a golden WAV, twice, the same bytes. audioload is the
  heaviest input on all 16 voices, and checks that core 1 renders. The
  notes case plays test patch 0.

- since M6b, MIDI out (R-MIDIOUT-*; the record at 0x01c00734, fwtest's
  --midi-out): in every case the wire's timing, one run of bytes per
  transfer of at most MIDI_OUT_CHUNK, whole messages, and a status after
  the wire went quiet (midi_out_common); midiout's messages against its
  script; midiround (midiout's golden capture into MIDI in) ends with
  midiout's engine state and pitches; midithru passes on every message
  but the SysEx, in order; midilocal plays nothing from the panel while
  local control is off; midiburst's policy leaves no note on unended;
  midioutlat's key-to-wire latency within MIDI_OUT_LATENCY_MS.

Prints what it saw for the record, and exits 1 if anything failed.
"""
import argparse
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_analysis as aa  # noqa: E402  (tools/, our own)
import fm_patch  # noqa: E402  (tools/, our own, since M5)
import midi_model  # noqa: E402  (tools/, our own, since M6a)
import midi_scripts  # noqa: E402  (tools/, our own, since M6a)
import store_suite  # noqa: E402  (tools/, our own, since M7)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = "tests/fw/boot.suite"
IMAGE = os.path.join("out", "fw", "app.bin")
# Test images: name -> define (firmware/src/probe.c).
TEST_BUILDS = {"test-fault": "SB_TEST_FAULT", "test-stray": "SB_TEST_STRAY",
               "test-badinsn": "SB_TEST_BADINSN", "test-flood": "SB_TEST_FLOOD",
               "test-leds": "SB_TEST_LEDS", "test-ledshow": "SB_TEST_LED_SHOW",
               "test-underrun": "SB_TEST_UNDERRUN", "test-velocity": "SB_TEST_VELOCITY",
               "test-midich": "SB_TEST_MIDI_CHANNEL", "test-midithru": "SB_TEST_MIDI_THRU",
               "test-midiburst": "SB_TEST_MIDI_BURST", "test-storecut": "SB_TEST_STORE_CUT",
               "test-storebusy": "SB_TEST_STORE_BUSY", "test-storewipe": "SB_TEST_STORE_WIPE"}
# Each case's expected outcome (the suite says the same; checked twice).
EXPECT = {"boot": "completed", "heartbeat": "completed", "heartbeat2": "completed",
          "screen": "completed", "flood": "completed", "fault": "halt", "stray": "halt",
          "badinsn": "fault", "keys": "completed", "chords": "completed", "encoders": "completed",
          "pot": "completed", "leds": "completed", "ledshow": "completed",
          "tone": "completed", "notes": "completed", "audioload": "completed",
          "audiogold": "completed", "underrun": "completed",
          "fmbessel": "completed", "fmenv": "completed", "fmmono": "completed", "fmsteal": "completed",
          "fmvel": "completed", "fmgold": "completed", "fmgold2": "completed",
          "midimsg": "completed", "midirun": "completed", "midisysex": "completed",
          "midijunk": "completed", "mididense": "completed", "midisustain": "completed",
          "midichan": "completed", "midipanel": "completed", "midilat": "completed",
          "midiout": "completed", "midiround": "completed", "midithru": "completed",
          "midilocal": "completed", "midiburst": "completed", "midioutlat": "completed",
          "views": "completed", "viewsload": "completed", "macros": "completed"}

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
IDLE_MAX_IPT = 1536        # instructions per tick, in steady state (since M2;
                           # 100 until M3's scanning, 1 280 until M4's audio:
                           # DESIGN-NOTES.md, M3 and M4)
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
    # Since M4 the audio output's blocks wake it too.
    most = (SCAN_SLOTS + 1) * (loop + 1) + loop // 1000 + 2 + loop * TICKS_PER_MS // BLOCK_TICKS + 2
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
    want[SRC_AUDIO] = symbols["audio_block"]
    wrong = [n for n in range(128) if table[n] != want[n]]
    lines.append("  vector table: %d of 128 slots as built (tick 0x%08x, SPI1 0x%08x, scan 0x%08x, audio 0x%08x,"
                 " stubs from 0x%08x)"
                 % (128 - len(wrong), symbols["sb_tick"], symbols["lcd_spi_done"], symbols["input_scan"],
                    symbols["audio_block"], symbols["sb_irq_stubs"]))
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
                "led_lag_max", "pot_raw", "led_show_max")   # input.h's order
INPUT_VALUES = 50          # input_value() for 49 controls, padded
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
LED_SHOW_MS = 1.01         # from input_led to the scan driving it: one scan
LED_FULL_DUTY = (75, 92)   # thousandths: lit in 1 of 12 scan slots (83.3)
# The keys script's LED changes: each of the 41 pressed and let go (82),
# and since M8a three more as the screens change (ENV, EDIT, GLO, HOME
# pressed in turn: HOME lit at the first event, then the previous screen's
# button and OP1's key at half going dark or lit).
LED_CALLS_KEYS = 85
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
    u = ui_record(case_dir)
    lines.append("  LEDs: %d set by main, at most %.4f ms after their event" % (head["led_calls"], lag))
    if head["led_calls"] != u["leds"] or head["led_calls"] != LED_CALLS_KEYS or lag > LED_LAG_MS:
        problems.append("keys: %d LED calls (the screens counted %d, %d expected), longest %.3f ms after"
                        " the event (at most %s)" % (head["led_calls"], u["leds"], LED_CALLS_KEYS, lag, LED_LAG_MS))
    # Since M8a an LED is lit while its key is held, and also while its
    # screen shows (HOME from the first event at 700 ms, then ENV, EDIT,
    # GLO and HOME as each is pressed), and OP1's key at half while EDIT
    # or ENV shows. Each LED lit for every sample inside its key's hold,
    # once the event and one scan are past, at a full share of its
    # column's slot on average over the hold (one sample's share varies:
    # samples come late while the core idles, docs/HARNESS.md "Time");
    # dark for every sample clear of the hold and of its screen.
    screens = [(700, 8), (860, 4), (940, 6), (980, 7), (1020, 8)]
    edges = [t for t, _ in screens]

    def lit_by_screen(n, ms):
        on = [b for t, b in screens if t <= ms]
        if on and on[-1] == n:
            return "full"
        if n == OP1_KEY and on and on[-1] in (4, 6):
            return "half"
        return None

    prev, lit, dark, held = 0.0, 0, 0, {}
    for ms, duty in read_leds(case_dir):
        near = any(t - 1 <= ms <= t + 6 for t in edges)
        for n in range(41):
            down = 700 + 40 * n
            screen = lit_by_screen(n, ms)
            if prev >= down + KEY_LATENCY[1] + LED_LAG_MS + 1.1 and ms <= down + 20:
                lit += 1
                held.setdefault(n, []).append(duty[n])
                if not duty[n]:
                    problems.append("leds: LED %d dark at %.0f ms while key %d is held" % (n, ms, n))
            elif ms <= down or prev >= down + 20 + KEY_LATENCY[1] + LED_LAG_MS + 1.1:
                if near:
                    continue
                if screen and not duty[n]:
                    problems.append("leds: LED %d dark at %.0f ms while its screen shows" % (n, ms))
                elif screen is None and duty[n]:
                    problems.append("leds: LED %d at %.0f ms: %d, not dark" % (n, ms, duty[n]))
                else:
                    dark += screen is None
        prev = ms
    for n in range(41):
        mean = sum(held.get(n, [0])) / len(held.get(n, [0]))
        if not LED_FULL_DUTY[0] <= mean <= LED_FULL_DUTY[1]:
            problems.append("leds: LED %d's mean share while held %.1f, not within %s" % (n, mean, LED_FULL_DUTY))
    means = [sum(v) / len(v) for v in held.values()]
    if means:
        lines.append("  leds.csv: each LED's mean share while held %.1f to %.1f thousandths" % (min(means), max(means)))
    lines.append("  leds.csv: %d samples lit as expected, %d dark as expected; the screens' buttons lit while their"
                 " screen shows, OP1's key at half on ENV and EDIT" % (lit, dark))
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


def check_ledshow(case_dir):
    """The keys script on the test build that times, in the scan, when an
    LED just set is first driven: from the event to main's input_led, and
    from there to the scan's slot for that LED's column (R-LED-3)."""
    head, _, _ = input_record(os.path.join(case_dir, input_name("end")))
    lag, show = head["led_lag_max"] / TICKS_PER_MS, head["led_show_max"] / TICKS_PER_MS
    lines = ["  %d LED changes: set by main at most %.4f ms after their event, then driven by the scan"
             " at most %.4f ms later: %.4f ms from event to LED at most" % (LED_CALLS_KEYS, lag, show, lag + show)]
    if head["led_calls"] != LED_CALLS_KEYS or not 0 < show <= LED_SHOW_MS or lag > LED_LAG_MS:
        return ["ledshow: %d LED calls (85 expected); event to input_led %.4f ms (at most %s), input_led to"
                " the scan %.4f ms (more than 0, at most %s)"
                % (head["led_calls"], lag, LED_LAG_MS, show, LED_SHOW_MS)], lines
    return [], lines


# Since M4: the audio output and the test instrument (firmware/src/audio.h,
# synth.c; docs/REQUIREMENTS.md R-AUD-*). The sound is measured by our own
# analysis (tools/audio_analysis.py), at the output's true rate.
AUDIO_ADDR, AUDIO_LEN = 0x01c00550, 0x40
AUDIO_FIELDS = ("marker", "start", "blocks", "underruns", "fill_last", "fill_max", "dropped",
                "voices_on", "notes", "tone", "master", "taken", "stolen", "octave", "first_on",
                "last_off")                                   # audio.h's order
AUDIO_MARKER = 0x34445541  # "AUD4"
SRC_AUDIO = 11             # the audio link (HW-19, HW-43)
BLOCK_TICKS = aa.BLOCK * 544   # time base ticks a block (HW-45): 1.451 ms
HELLO = "small-beeps M5 \n"
# Limits (docs/REQUIREMENTS.md, R-AUD-4 to R-AUD-6).
TONE_HZ, TONE_DBFS = 1000.0, 20 * math.log10(0.5)
TONE_CENTS, NOTE_CENTS = 0.05, 0.1
LEVEL_DB = 0.1
TONE_THDN_DB, NOTE_THDN_DB = -85.0, -70.0
ATTACK_SAMPLES, RELEASE_SAMPLES = 221, 882   # the instrument's ramps (synth.c)
SOUND_FROM_KEY = (2.5, 7.5)     # ms from the key's contact to its first sample
SOUND_FROM_EVENT = 2 * BLOCK_TICKS / TICKS_PER_MS + 0.2   # ms: two blocks, and 0.2
SILENCE_RUN = 200               # zero samples in a row that end a sound
NOTES_SILENCE = 2000            # in the notes case (since M5's releases)


def audio_record(path):
    with open(path, "rb") as f:
        return dict(zip(AUDIO_FIELDS, struct.unpack("<%dI" % len(AUDIO_FIELDS), f.read()[:AUDIO_LEN])))


def audio_name(when="end"):
    return "ram-%08x-%x-%s.bin" % (AUDIO_ADDR, AUDIO_LEN, when)


def check_audio_common(name, case_dir, underruns=0):
    """Every audio case: the output ran, each block was filled once, the
    console holds nothing but the start line (and the underruns expected),
    and the WAV is mono in stereo (left equals right). Returns (problems,
    lines, record, wav) where wav is (left, block ends) or None."""
    problems, lines = [], []
    a = audio_record(os.path.join(case_dir, audio_name()))
    ends = aa.read_ipb(os.path.join(case_dir, "ipb.csv"))
    if a["marker"] != AUDIO_MARKER:
        problems.append("%s: the audio record's marker is 0x%08x" % (name, a["marker"]))
    # The end capture can come while the last block's fill is still going.
    if not len(ends) - 1 <= a["blocks"] <= len(ends):
        problems.append("%s: %d blocks filled, fwtest finished %d" % (name, a["blocks"], len(ends)))
    if a["underruns"] != underruns:
        problems.append("%s: %d underruns, expected %d" % (name, a["underruns"], underruns))
    if a["dropped"]:
        problems.append("%s: the engine's queue dropped %d events" % (name, a["dropped"]))
    gaps = [i for i in range(1, len(ends)) if not 0 < ends[i] - ends[i - 1] < 2 * BLOCK_TICKS / TICKS_PER_MS]
    if gaps:
        problems.append("%s: blocks %s ended more than a block after the one before" % (name, gaps[:5]))
    with open(os.path.join(case_dir, "console.txt")) as f:
        console = f.read()
    if not console.startswith(HELLO):
        problems.append("%s: the console doesn't start with the start line" % name)
    lines.append("  audio: %d blocks filled (fwtest: %d), %d underruns, longest fill %.1f us, "
                 "%d events to the engine"
                 % (a["blocks"], len(ends), a["underruns"], a["fill_max"] / 24.0, a["taken"]))
    wav = None
    path = os.path.join(case_dir, "audio.wav")
    if os.path.exists(path):
        rate, left, right = aa.read_wav(path)
        if left != right:
            problems.append("%s: left and right differ" % name)
        if len(left) != aa.BLOCK * len(ends):
            problems.append("%s: %d samples for %d blocks" % (name, len(left), len(ends)))
        lines.append("  audio.wav: %d frames (header %d Hz; measured at %.3f Hz)" % (len(left), rate, aa.RATE))
        wav = (left, ends)
    return problems, lines, a, console, wav


def sounds(x, run=SILENCE_RUN):
    """[(first, last)] sample of each sound: from a non-zero sample to the
    last before run zeros (SILENCE_RUN unless a check says otherwise)."""
    out, i, n = [], 0, len(x)
    while i < n:
        while i < n and not x[i]:
            i += 1
        if i >= n:
            break
        first, zeros, j = i, 0, i
        while j < n and zeros < run:
            zeros = zeros + 1 if not x[j] else 0
            j += 1
        out.append((first, j - zeros - 1))
        i = j
    return out


def check_clicks(name, x, first, last, fit):
    """No click where a sound starts and stops: the largest second
    difference over the attack and the release within click_bound."""
    a, f = fit["amplitude"], fit["frequency"]
    problems = []
    for what, lo, hi, ramp in (("start", first - 50, first + ATTACK_SAMPLES + 50, ATTACK_SAMPLES),
                               ("stop", last - RELEASE_SAMPLES - 150, last + 50, RELEASE_SAMPLES)):
        d2 = aa.max_second_difference(x[max(0, lo):hi])
        bound = aa.click_bound(a, f, ramp)
        if d2 > bound:
            problems.append("%s: a click at the %s of the sound at sample %d: second difference %d, "
                            "more than %.1f" % (name, what, first if what == "start" else last, d2, bound))
    return problems


def check_tone(case_dir):
    """The test tone (tests/fw/scripts/tone.txt): frequency, level, THD+N,
    a clean start and stop, and digital silence at rest around it."""
    problems, lines, a, _, wav = check_audio_common("tone", case_dir)
    if wav is None:
        return problems + ["tone: no audio.wav"], lines
    x, ends = wav
    s = sounds(x)
    if len(s) != 1:
        return problems + ["tone: %d sounds, expected one" % len(s)], lines
    first, last = s[0]
    fit = aa.sine_fit(x[int(0.5 * aa.RATE):int(2.2 * aa.RATE)])
    c, lvl, thdn = aa.cents(fit["frequency"], TONE_HZ), aa.dbfs(fit["amplitude"]), aa.thd_n_db(fit)
    lines.append("  test tone: %.6f Hz (%+.5f cents), %.3f dBFS, THD+N %.1f dB, from %.3f to %.3f ms;"
                 " silence (every sample 0) before and after"
                 % (fit["frequency"], c, lvl, thdn, aa.sample_ms(first, ends), aa.sample_ms(last, ends)))
    if abs(c) > TONE_CENTS:
        problems.append("tone: %.6f Hz, %+.4f cents from %s Hz (at most %s)" % (fit["frequency"], c, TONE_HZ, TONE_CENTS))
    if abs(lvl - TONE_DBFS) > LEVEL_DB:
        problems.append("tone: %.3f dBFS, not within %s dB of %.3f" % (lvl, LEVEL_DB, TONE_DBFS))
    if thdn > TONE_THDN_DB:
        problems.append("tone: THD+N %.1f dB, above %s" % (thdn, TONE_THDN_DB))
    problems += check_clicks("tone", x, first, last, fit)
    on = aa.sample_ms(first, ends)
    if not SOUND_FROM_KEY[0] <= on - 100 <= SOUND_FROM_KEY[1]:
        problems.append("tone: began %.3f ms after PLAY, not within %s" % (on - 100, SOUND_FROM_KEY))
    return problems, lines


# tests/fw/scripts/notes.txt: (key down ms, fwtest key, MIDI note, MASTER).
NOTES = [(100, 21, 60, 900), (500, 30, 69, 900), (900, 14, 53, 900), (1300, 40, 79, 900),
         (1700, 30, 69, 1023), (2100, 30, 69, 512), (2700, 40, 103, 512), (3500, 14, 29, 512)]


def master_gain(pot):
    """synth.c's MASTER law: the square of its position, full at 1023."""
    return 1.0 if pot >= 1023 else pot * pot * 16 / float(1 << 24)


def check_notes(case_dir):
    """Single notes (tests/fw/scripts/notes.txt): each one's pitch, level
    and latency, its start and stop, and silence between them."""
    problems, lines, a, _, wav = check_audio_common("notes", case_dir)
    if wav is None:
        return problems + ["notes: no audio.wav"], lines
    x, ends = wav
    _, _, log = input_record(os.path.join(case_dir, input_name("end")))
    # Since M5 a release falls exponentially, so its last samples flicker
    # between 0 and 1 for a while: a low note's zeros run longer than
    # SILENCE_RUN (NOTES_SILENCE, 45 ms, is still less than any gap).
    s = sounds(x, NOTES_SILENCE)
    if len(s) != len(NOTES):
        return problems + ["notes: %d sounds, expected %d" % (len(s), len(NOTES))], lines
    # Where fwtest's time and the time base's meet: the output started one
    # block before its first block ended, sb_audio.start time base ticks
    # after main started the time base.
    base_ms = ends[0] - BLOCK_TICKS / TICKS_PER_MS - a["start"] / TICKS_PER_MS
    lines.append("  the time base started at %.3f ms of fwtest's time" % base_ms)
    lats, evs = [], []
    for (down, key, note, pot), (first, last) in zip(NOTES, s):
        fit = aa.sine_fit(x[first + int(0.01 * aa.RATE):first + int(0.2 * aa.RATE)])
        want = aa.note_hz(note)
        c = aa.cents(fit["frequency"], want)
        lvl = aa.dbfs(fit["amplitude"])
        want_lvl = aa.dbfs(aa.FULL / 4.0 * master_gain(pot))
        on = aa.sample_ms(first, ends)
        press = [t for _, ctl, k, _, t in log if ctl == key and k == PRESS and t / TICKS_PER_MS < on - base_ms]
        ev = on - (base_ms + press[-1] / TICKS_PER_MS) if press else None
        lats.append(on - down)
        if ev is not None:
            evs.append(ev)
        lines.append("  note %3d (%s): %.4f Hz (%+.4f cents), %.3f dBFS (MASTER %d: %.3f), THD+N %.1f dB, "
                     "sound %.3f ms after the key, %s after its event"
                     % (note, CONTROL_NAMES[key], fit["frequency"], c, lvl, pot, want_lvl, aa.thd_n_db(fit),
                        on - down, "%.3f ms" % ev if ev is not None else "?"))
        if abs(c) > NOTE_CENTS:
            problems.append("notes: note %d at %.4f Hz, %+.3f cents from %.4f (at most %s)"
                            % (note, fit["frequency"], c, want, NOTE_CENTS))
        if abs(lvl - want_lvl) > LEVEL_DB:
            problems.append("notes: note %d at %.3f dBFS, not within %s dB of %.3f"
                            % (note, lvl, LEVEL_DB, want_lvl))
        if aa.thd_n_db(fit) > NOTE_THDN_DB:
            problems.append("notes: note %d's THD+N %.1f dB, above %s" % (note, aa.thd_n_db(fit), NOTE_THDN_DB))
        if not SOUND_FROM_KEY[0] <= on - down <= SOUND_FROM_KEY[1]:
            problems.append("notes: note %d sounded %.3f ms after its key, not within %s"
                            % (note, on - down, SOUND_FROM_KEY))
        if ev is None or not 0 < ev <= SOUND_FROM_EVENT:
            problems.append("notes: note %d sounded %s after its press event, not within %.3f ms"
                            % (note, "?" if ev is None else "%.3f ms" % ev, SOUND_FROM_EVENT))
        # Test patch 0's attack is linear over its time code's time; its
        # release falls more slowly than that (R-FM-3).
        problems += check_clicks_fm("notes", x[:last + 50], first, last + 50, [fit["frequency"]], fit["amplitude"],
                                    1000.0 / (fm_patch.time_ms(fm_patch.TEST_PATCHES[0]["ops"][0]["rates"][0])
                                              * aa.RATE))
    lines.append("  latency: key to sound %.3f to %.3f ms, press event to sound %.3f to %.3f ms; "
                 "every sample between the notes 0" % (min(lats), max(lats), min(evs or [0]), max(evs or [0])))
    return problems, lines


def check_audioload(case_dir):
    """The heaviest input with every voice and the test tone for 10 s
    (tests/fw/scripts/audioload.txt): no underrun, every tick on time,
    every event to the engine."""
    problems, lines, a, console, _ = check_audio_common("audioload", case_dir)
    head, _, _ = input_record(os.path.join(case_dir, input_name("end")))
    more, tl = check_ticks_under_load("audioload", case_dir)
    problems += more
    lines += tl
    seconds = a["blocks"] * BLOCK_TICKS / 24e6
    lines.append("  %.2f s of audio under load: %d notes (%d took a sounding voice), %d events to the engine,"
                 " %d to main; longest fill %.1f us of a %.1f us block"
                 % (seconds, a["notes"], a["stolen"], a["taken"], head["taken"], a["fill_max"] / 24.0,
                    BLOCK_TICKS / 24.0))
    if seconds < 10:
        problems.append("audioload: only %.2f s of audio" % seconds)
    if a["taken"] != head["events"]:
        problems.append("audioload: the engine took %d events of %d" % (a["taken"], head["events"]))
    if not a["stolen"] or a["notes"] < 100:
        problems.append("audioload: %d notes, %d took a sounding voice" % (a["notes"], a["stolen"]))
    if console != HELLO:
        problems.append("audioload: the console has more than the start line")
    # Since M5: the heaviest patch on all 16 voices, on both cores.
    more, f = fm_common("audioload", case_dir, 6)
    problems += more
    with open(os.path.join(case_dir, "ipb.csv")) as fi:
        core1 = sum(int(r.split(",")[3]) for r in list(fi)[1:] if r.strip())
    lines.append("  FM: %d voices at most, %d stolen; core 1 rendered %d blocks (%d instructions); core 0 waited"
                 " for it at most %.1f us" % (f["voices_max"], f["stolen"], f["core1_blocks"], core1,
                                              f["wait_max"] / 24.0))
    if f["voices_max"] != FM_VOICES or f["core1_blocks"] <= 0 or core1 <= 0:
        problems.append("audioload: %d voices at most, core 1 rendered %d blocks" % (f["voices_max"], f["core1_blocks"]))
    return problems, lines


def check_audiogold(case_dir):
    problems, lines, _, _, _ = check_audio_common("audiogold", case_dir)
    return problems, lines


UNDERRUN_LINE = re.compile(r"^AUDIO UNDERRUN ([0-9a-f]{4})$")


def check_underrun(case_dir):
    """A test build whose engine is late for one block in 64: each late
    block counted once and reported on the console, and the output goes on
    (R-AUD-3)."""
    a = audio_record(os.path.join(case_dir, audio_name()))
    late = (a["blocks"] - 32 + 63) // 64 if a["blocks"] > 32 else 0
    problems, lines, _, console, _ = check_audio_common("underrun", case_dir, underruns=late)
    reports = console[len(HELLO):].splitlines()
    nums = [int(m.group(1), 16) for m in map(UNDERRUN_LINE.match, reports) if m]
    lines.append("  %d blocks late on purpose: %d underruns counted, %d reported (%s)"
                 % (late, a["underruns"], len(nums), ", ".join(reports[:3]) + (", ..." if len(reports) > 3 else "")))
    if late < 4 or nums != list(range(1, late + 1)) or len(reports) != late:
        problems.append("underrun: %d late blocks, reports %s" % (late, reports[:8]))
    return problems, lines


# Since M5: the FM engine (firmware/src/fm.h, fm.c, fm_play.c; R-FM-*).
# Its record follows the audio record; the test patches' values come from
# tools/fm_patch.py, the same definitions patches.c is generated from.

FM_ADDR, FM_LEN = 0x01c00590, 0x40
FM_FIELDS = ("marker", "core1", "core1_blocks", "patch", "algorithm", "mono", "voices0", "voices1",
             "voices_max", "stolen", "notes", "wait_max", "pitch_knob", "glide", "depth", "feedback")
FM_MARKER = 0x354D4653     # "SFM5"
FM_VOICES = 16
# Limits (docs/REQUIREMENTS.md, R-FM-1 to R-FM-9).
BESSEL_DB = (0.05, 0.5)    # sidebands -4 to 4; -5 and 5 (near the folded -7)
BESSEL_LEVEL_DB = 0.01     # the sidebands' total against the carrier's level
ENV_LATE_MS = BLOCK_TICKS / TICKS_PER_MS   # a stage ends within a block (the measurement's own)
ENV_RATE = 0.03            # a stage's slope within 3%
ENV_LEVEL_DB = 0.1
GLIDE_SEMI = 0.15          # semitones from the straight line, during the glide
HELD_SEMI = 0.02           # and from the note, outside it
LEGATO_DB = 0.5            # the level across a legato note (no new attack)
VELOCITY_DB = 0.05


def fm_record(path):
    with open(path, "rb") as f:
        return dict(zip(FM_FIELDS, struct.unpack("<%di" % len(FM_FIELDS), f.read()[:FM_LEN])))


def fm_name(when="end"):
    return "ram-%08x-%x-%s.bin" % (FM_ADDR, FM_LEN, when)


def fm_common(name, case_dir, patch):
    """Every FM case: the engine's record is there, the patch the script
    chose is in force, and core 1 runs the engine's loop."""
    f = fm_record(os.path.join(case_dir, fm_name()))
    problems = []
    if f["marker"] != FM_MARKER:
        problems.append("%s: the FM record's marker is 0x%08x" % (name, f["marker"] & 0xFFFFFFFF))
    if f["patch"] != patch:
        problems.append("%s: patch %d in force, not %d" % (name, f["patch"], patch))
    if f["core1"] != 1:
        problems.append("%s: core 1 doesn't run the engine" % name)
    return problems, f


def note_start(x):
    s = sounds(x)
    return s[0] if s else (None, None)


def check_fmbessel(case_dir):
    """Test patch 1 (R-FM-1): a modulator at the note's frequency into a
    carrier at 6 times it, at index pi/2: each sideband (6 + n) f for n
    from -5 to 5 against |J_n(pi/2)| of the whole, and the whole against
    the carrier's level."""
    problems, lines, a, _, wav = check_audio_common("fmbessel", case_dir)
    more, _ = fm_common("fmbessel", case_dir, 1)
    problems += more
    if wav is None:
        return problems + ["fmbessel: no audio.wav"], lines
    x, ends = wav
    first, _ = note_start(x)
    if first is None:
        return problems + ["fmbessel: no sound"], lines
    p = fm_patch.TEST_PATCHES[1]
    f0 = aa.note_hz(69)
    index = fm_patch.level_gain(p["ops"][1]["level"]) * 4 * math.pi
    seg = x[first + int(0.2 * aa.RATE):first + int(0.45 * aa.RATE)]
    ns = list(range(-5, 6))
    amp = aa.amplitudes_at(seg, [(p["ops"][0]["freq"] + n) * f0 for n in ns])
    total = math.sqrt(sum(v * v for v in amp))
    want = aa.FULL / 4.0 * master_gain(900)
    worst = 0.0
    for n, v in zip(ns, amp):
        j = abs(aa.bessel_j(abs(n), index))
        d = 20 * math.log10(v / total / j)
        tol = BESSEL_DB[0] if abs(n) <= 4 else BESSEL_DB[1]
        worst = max(worst, abs(d)) if abs(n) <= 4 else worst
        if abs(d) > tol:
            problems.append("fmbessel: sideband %+d at %.5f of the whole, |J_%d(%.4f)| %.5f: %+.3f dB (at most %s)"
                            % (n, v / total, abs(n), index, j, d, tol))
    lvl = 20 * math.log10(total / want)
    lines.append("  index %.5f (pi/2): sidebands -4 to 4 within %.4f dB of |J_n|, -5 %+.3f dB, +5 %+.3f dB;"
                 " their total %.2f (%+.4f dB of the carrier's level)"
                 % (index, worst, 20 * math.log10(amp[0] / total / aa.bessel_j(5, index)),
                    20 * math.log10(amp[-1] / total / aa.bessel_j(5, index)), total, lvl))
    if abs(lvl) > BESSEL_LEVEL_DB:
        problems.append("fmbessel: the sidebands' total %+.4f dB from the carrier's level" % lvl)
    return problems, lines


def line(points):
    """The least-squares line through [(x, y)]: (slope, y at x = 0)."""
    n = float(len(points))
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    k = sum((p[0] - mx) * (p[1] - my) for p in points) / sum((p[0] - mx) ** 2 for p in points)
    return k, my - k * mx


def check_fmenv(case_dir):
    """Test patch 2 (R-FM-3): the attack (linear in gain), decay 1 and
    decay 2 (linear in dB) at their rates and levels, the held level, and
    the release's rate, each stage ending within ENV_LATE_MS."""
    problems, lines, a, _, wav = check_audio_common("fmenv", case_dir)
    more, _ = fm_common("fmenv", case_dir, 2)
    problems += more
    if wav is None:
        return problems + ["fmenv: no audio.wav"], lines
    x, ends = wav
    first, _ = note_start(x)
    if first is None:
        return problems + ["fmenv: no sound"], lines
    o = fm_patch.TEST_PATCHES[2]["ops"][0]
    t_ms = [fm_patch.time_ms(r) for r in o["rates"]]
    full_db = 16 * 20 * math.log10(2)             # a stage's whole range: 16 octaves
    lv = [20 * math.log10(fm_patch.level_gain(v)) for v in o["levels"]]
    amp = aa.block_amplitudes(x, aa.note_hz(69))
    peak = aa.FULL / 4.0 * master_gain(900)       # the patch's full level, at 0 dB
    db = [20 * math.log10(v / peak) if v > 0 else -200.0 for v in amp]
    b0 = first // aa.BLOCK

    def ms(b):
        return (b * aa.BLOCK + aa.BLOCK / 2.0 - first) * 1000.0 / aa.RATE

    def reach(level, start):
        """The first block at or below level, and when the level was
        crossed (interpolated between block centres), in ms."""
        for b in range(start + 1, len(db)):
            if db[b] <= level + 0.01:
                lo, hi = db[b - 1], db[b]
                return b, ms(b - 1) + (ms(b) - ms(b - 1)) * ((lo - level) / (lo - hi) if lo != hi else 1)
        return None, None
    # The attack ends in the loudest block (the peak lies within it).
    bp = max(range(b0, b0 + int(2 * t_ms[0] * aa.RATE / 1000 / aa.BLOCK) + 2), key=lambda b: db[b])
    b1, _ = reach(lv[1], bp)
    b2, _ = reach(lv[2], b1 or bp)
    if None in (b1, b2):
        return problems + ["fmenv: the envelope never reached its levels"], lines
    want = [t_ms[0], t_ms[0] + t_ms[1] * (lv[0] - lv[1]) / full_db,
            t_ms[0] + (t_ms[1] * (lv[0] - lv[1]) + t_ms[2] * (lv[1] - lv[2])) / full_db]
    # A decay ends where the line through its blocks meets its level.
    got = [ms(bp)]
    held = sum(db[b2 + 5:b2 + 200]) / 195.0
    half = amp[b0 + int(round(t_ms[0] / 2 * aa.RATE / 1000 / aa.BLOCK))] / peak
    rates = []
    for name, lo, hi, t, start, end_at in (("decay 1", lv[0] - 2, lv[1] + 2, t_ms[1], bp, lv[1]),
                                           ("decay 2", lv[1] - 1, lv[2] + 1, t_ms[2], b1, lv[2]),
                                           ("release", lv[2] - 2, lv[2] - 26, t_ms[3], b2 + 20, None)):
        pts = [(ms(b), db[b]) for b in range(start, len(db)) if hi <= db[b] <= lo and ms(b) < 1000]
        if len(pts) < 3:
            problems.append("fmenv: too few points to time the %s" % name)
            continue
        k, c = line(pts)
        r, w = -k * 1000, full_db / t * 1000
        rates.append("%s %.1f dB/s (%.1f)" % (name, r, w))
        if end_at is not None:
            got.append((end_at - c) / k)
        if abs(r / w - 1) > ENV_RATE:
            problems.append("fmenv: the %s falls %.1f dB/s, not within %d%% of %.1f" % (name, r, ENV_RATE * 100, w))
    lines.append("  stages end at %s ms (nominal %s); halfway through the attack %.4f of the peak; held %.3f dB"
                 " (%.3f); %s" % (", ".join("%.2f" % g for g in got), ", ".join("%.2f" % w for w in want),
                                  half, held, lv[2], "; ".join(rates)))
    for g, w, what in zip(got, want, ("the attack", "decay 1", "decay 2")):
        if abs(g - w) > ENV_LATE_MS:
            problems.append("fmenv: %s ended at %.2f ms, not within %.2f ms of %.2f" % (what, g, ENV_LATE_MS, w))
    if abs(held - lv[2]) > ENV_LEVEL_DB:
        problems.append("fmenv: held at %.3f dB, not %.3f" % (held, lv[2]))
    if abs(half - 0.5) > 0.03:
        problems.append("fmenv: halfway through the attack at %.4f of the peak, not 0.5 (linear)" % half)
    # The fastest stage bounds how fast the level may move: the attack's
    # gain a sample, or a decay's or the release's fraction a sample.
    fastest = max([1000.0 / (t_ms[0] * aa.RATE)] +
                  [full_db / t / (20 / math.log(10)) * 1000.0 / aa.RATE for t in t_ms[1:]])
    problems += check_clicks_fm("fmenv", x, first, len(x), [aa.note_hz(69)], peak, fastest)
    return problems, lines


def click_bound_fm(amplitudes, freqs, ramp_per_sample, rate=aa.RATE, quantum=4):
    """The largest second difference a sum of sines can show when each
    amplitude moves by at most ramp_per_sample of itself a sample: their
    curvature, and the ramp's corners and slope against them."""
    return sum(a * ((2 * math.sin(math.pi * f / rate)) ** 2 + ramp_per_sample * (1 + 4 * math.pi * f / rate))
               for a, f in zip(amplitudes, freqs)) + quantum


def check_clicks_fm(name, x, first, last, freqs, amplitude, ramp_per_sample):
    d2 = aa.max_second_difference(x[max(0, first - 50):last])
    bound = click_bound_fm([amplitude] * len(freqs), freqs, ramp_per_sample)
    if d2 > bound:
        return ["%s: a click: second difference %d, more than %.1f" % (name, d2, bound)]
    return []


def rms_db(x):
    return 10 * math.log10(sum(v * v for v in x) / float(len(x)) + 1e-12)


def check_fmmono(case_dir):
    """Test patch 3 (R-FM-5): mono, legato and glide. C4 held, then E4:
    one voice, no new note and no new attack (its level goes on), a glide
    up over the patch's glide time; E4 released: a glide back to C4."""
    problems, lines, a, _, wav = check_audio_common("fmmono", case_dir)
    more, f = fm_common("fmmono", case_dir, 3)
    problems += more
    if wav is None:
        return problems + ["fmmono: no audio.wav"], lines
    x, ends = wav
    s = sounds(x)
    if len(s) != 1:
        return problems + ["fmmono: %d sounds, expected one" % len(s)], lines
    first, last = s[0]
    _, _, log = input_record(os.path.join(case_dir, input_name("end")))
    base_ms = ends[0] - BLOCK_TICKS / TICKS_PER_MS - a["start"] / TICKS_PER_MS

    def event_ms(key, kind):
        t = [e[4] for e in log if e[1] == key and e[2] == kind]
        return base_ms + t[0] / TICKS_PER_MS if t else None
    up, back, rel = event_ms(25, PRESS), event_ms(25, RELEASE), event_ms(21, RELEASE)
    glide = fm_patch.time_ms(fm_patch.TEST_PATCHES[3]["glide"])
    blk = BLOCK_TICKS / TICKS_PER_MS
    track = [(t + aa.sample_ms(first, ends), 69 + 12 * math.log2(hz / 440.0))
             for t, hz in aa.pitch_track(x, first, last)]
    worst_held = worst_glide = 0.0

    def expect(t):
        """The pitch the script asks for at t (ms), allowing for when the
        engine takes each event (within two blocks of it)."""
        for start, frm, to in ((up, 60, 64), (back, 64, 60)):
            if start + 2 * blk + 10 <= t <= start + glide - 10:
                return frm + (to - frm) * (t - start) / glide, 2 * blk / glide * 4 + GLIDE_SEMI
        if aa.sample_ms(first, ends) + 40 <= t <= up - 10 or back + glide + 2 * blk + 10 <= t <= rel - 10:
            return 60, HELD_SEMI
        if up + glide + 2 * blk + 10 <= t <= back - 10:
            return 64, HELD_SEMI
        return None, None
    for t, semi in track:
        want, tol = expect(t)
        if want is None:
            continue
        d = abs(semi - want)
        if tol == HELD_SEMI:
            worst_held = max(worst_held, d)
        else:
            worst_glide = max(worst_glide, d)
        if d > tol:
            problems.append("fmmono: at %.1f ms the pitch is note %.3f, not %.3f (within %.3f)" % (t, semi, want, tol))
            break
    w = int(0.02 * aa.RATE)
    at = lambda ms: first + int((ms - aa.sample_ms(first, ends)) * aa.RATE / 1000)
    before, after = rms_db(x[at(up - 30):at(up - 30) + w]), max(rms_db(x[at(up + d):at(up + d) + w]) for d in (0, 10, 20, 40))
    lines.append("  one sound, %d note started; held notes within %.4f semitones, the glides (%.1f ms) within %.3f"
                 " of a straight line; level %+.3f dB across the legato note"
                 % (a["notes"], worst_held, glide, worst_glide, after - before))
    if a["notes"] != 1 or f["mono"] != 1:
        problems.append("fmmono: %d notes started (mono %d), expected 1: legato starts no note" % (a["notes"], f["mono"]))
    if after - before > LEGATO_DB:
        problems.append("fmmono: the level rose %.2f dB at the legato note: a new attack" % (after - before))
    return problems, lines


def check_fmsteal(case_dir):
    """Test patch 0, 17 notes held on 16 voices (R-FM-4): the 17th takes
    the oldest voice, which fades over a block first; no click anywhere,
    all 16 voices sound, half of them on core 1."""
    problems, lines, a, _, wav = check_audio_common("fmsteal", case_dir)
    more, f = fm_common("fmsteal", case_dir, 0)
    problems += more
    if wav is None:
        return problems + ["fmsteal: no audio.wav"], lines
    x, ends = wav
    first, last = note_start(x)
    notes = list(range(53, 70))
    amp = aa.FULL / 4.0 * master_gain(200)
    attack = fm_patch.time_ms(fm_patch.TEST_PATCHES[0]["ops"][0]["rates"][0]) * aa.RATE / 1000
    d2 = aa.max_second_difference(x[max(0, first - 50):last + 50])
    bound = click_bound_fm([amp] * len(notes), [aa.note_hz(n) for n in notes], 1.0 / aa.BLOCK) + \
        click_bound_fm([amp], [aa.note_hz(69)], 1.0 / attack)
    lines.append("  %d notes, %d took a sounding voice, at most %d voices at once (%d and %d on the cores at the end"
                 " of the last block with notes); largest second difference %d (bound %.1f)"
                 % (a["notes"], f["stolen"], f["voices_max"], f["voices0"], f["voices1"], d2, bound))
    if a["notes"] != 17 or f["stolen"] != 1 or f["voices_max"] != FM_VOICES:
        problems.append("fmsteal: %d notes, %d stolen, %d voices at most; expected 17, 1, %d"
                        % (a["notes"], f["stolen"], f["voices_max"], FM_VOICES))
    if d2 > bound:
        problems.append("fmsteal: a click: second difference %d, more than %.1f" % (d2, bound))
    if f["core1_blocks"] <= 0:
        problems.append("fmsteal: core 1 rendered no block")
    return problems, lines


VELOCITIES = (127, 100, 64, 32, 1)    # the test build's KEY1 to KEY5 (fm_play.c)


def check_fmvel(case_dir):
    """The velocity test build, test patch 8 (R-FM-3): each note's level
    (its RMS: the patch is one sine carrier) against its velocity
    sensitivity: 8 octaves (48.2 dB) at
    velocity 0 for a sensitivity of 7, in proportion."""
    problems, lines, a, _, wav = check_audio_common("fmvel", case_dir)
    more, _ = fm_common("fmvel", case_dir, 8)
    problems += more
    if wav is None:
        return problems + ["fmvel: no audio.wav"], lines
    x, ends = wav
    s = sounds(x)
    if len(s) != len(VELOCITIES):
        return problems + ["fmvel: %d sounds, expected %d" % (len(s), len(VELOCITIES))], lines
    sens = fm_patch.TEST_PATCHES[8]["ops"][0]["velocity"]
    lv = [rms_db(x[f + int(0.1 * aa.RATE):f + int(0.25 * aa.RATE)]) for f, _ in s]
    got = []
    for v, l in zip(VELOCITIES, lv):
        soft = (127 - v) * (8 * 65536 // 7) // 127 * sens
        want = -20 * math.log10(2) * soft / 65536.0
        d = l - lv[0]
        got.append("%d: %+.3f (%+.3f)" % (v, d, want))
        if abs(d - want) > VELOCITY_DB:
            problems.append("fmvel: velocity %d is %+.3f dB from velocity 127, not %+.3f" % (v, d, want))
    lines.append("  level against velocity 127, dB (expected): " + ", ".join(got))
    return problems, lines


def check_fmgold(case_dir):
    """Every test patch against the golden WAV (R-FM-8); and fmgold2,
    the same run again, gives the same bytes (R-FM-9)."""
    problems, lines, _, _, _ = check_audio_common(os.path.basename(case_dir), case_dir)
    more, _ = fm_common(os.path.basename(case_dir), case_dir, 8)
    problems += more
    other = os.path.join(os.path.dirname(case_dir), "fmgold")
    if os.path.basename(case_dir) == "fmgold2":
        with open(os.path.join(case_dir, "audio.wav"), "rb") as f1, open(os.path.join(other, "audio.wav"), "rb") as f2:
            same = f1.read() == f2.read()
        lines.append("  the second run's audio.wav is %s the first's" % ("byte for byte" if same else "NOT"))
        if not same:
            problems.append("fmgold2: the output differs from fmgold's")
    return problems, lines


# --- MIDI in (M6a; R-MIDI-*) ---------------------------------------------

MIDI_ADDR, MIDI_LEN = 0x01c005d0, 0x164
MIDI_FIELDS = ("marker", "bytes", "ring_dropped", "parsed", "messages", "realtime", "sysex",
               "sysex_bytes", "sysex_long", "sysex_cut", "orphans", "undefined", "cut", "filtered",
               "notes_on", "notes_off", "held", "pedal", "bend", "mod", "volume", "expression",
               "program", "last_note_tick", "log_count")
MIDI_MARKER = 0x3649444D      # "MDI6", firmware/src/midi.h
MIDI_LOG = 64
MIDI_LATENCY_MS = 3.0         # a note on's last byte to its first sample (R-MIDI-7)
MIDI_BEND_SEMI = 0.05         # a bent pitch, against the range asked
MIDI_LEVEL_DB = 0.1           # volume and expression against their curve
MIDI_SOUND_OFF_MS = 6.0       # all sound off: silent within this of its last byte


def midi_record(path):
    with open(path, "rb") as f:
        b = f.read()
    n = len(MIDI_FIELDS)
    r = dict(zip(MIDI_FIELDS, struct.unpack("<%dI" % n, b[:4 * n])))
    r["bend"] = struct.unpack("<i", struct.pack("<I", r["bend"]))[0]
    r["log"] = [tuple(b[4 * n + 4 * i:4 * n + 4 * i + 4]) for i in range(MIDI_LOG)]
    return r


def midi_name(when="end"):
    return "ram-%08x-%x-%s.bin" % (MIDI_ADDR, MIDI_LEN, when)


def midi_logged(r):
    """The messages still in the record's log, oldest first."""
    n = r["log_count"]
    return [r["log"][i % MIDI_LOG] for i in range(max(0, n - MIDI_LOG), n)]


def midi_notes(model, channel=None):
    """(note ons, note offs) the engine should take from the model's log."""
    on = off = 0
    for s, d1, d2, _ in model.log:
        if s >= 0xF0 or (channel is not None and s & 15 != channel):
            continue
        if s & 0xF0 == 0x90 and d2:
            on += 1
        elif s & 0xF0 in (0x80, 0x90):
            off += 1
    return on, off


def midi_common(name, case_dir, idle=True, channel=None):
    """Every MIDI case: fwtest dropped no byte; the firmware received and
    parsed every byte of the script, and its counters and its log of
    messages are the model's (tools/midi_model.py) for the same bytes; it
    took the note ons and offs the model's messages hold; and, if idle,
    nothing is held and no voice sounds at the end."""
    problems, lines = [], []
    with open(os.path.join(case_dir, "result.json")) as f:
        run = json.load(f).get("run", {})
    if run.get("midi_bytes_dropped"):
        problems.append("%s: fwtest dropped %s MIDI bytes" % (name, run["midi_bytes_dropped"]))
    stream = [b for _, b in midi_scripts.stream(os.path.join(ROOT, "tests", "fw", "scripts", name + ".txt"))]
    model = midi_model.parse(stream)
    r = midi_record(os.path.join(case_dir, midi_name()))
    if r["marker"] != MIDI_MARKER:
        return problems + ["%s: the MIDI record's marker is 0x%08x" % (name, r["marker"])], lines, r, model
    if (r["bytes"], r["ring_dropped"], r["parsed"]) != (len(stream), 0, len(stream)):
        problems.append("%s: %d bytes received, %d dropped, %d parsed; the script sends %d"
                        % (name, r["bytes"], r["ring_dropped"], r["parsed"], len(stream)))
    for k in midi_model.COUNTERS:
        if r[k] != model.count[k]:
            problems.append("%s: %s %d, the model says %d" % (name, k, r[k], model.count[k]))
    if r["log_count"] != len(model.log):
        problems.append("%s: %d messages logged, the model has %d" % (name, r["log_count"], len(model.log)))
    elif midi_logged(r) != model.log[-MIDI_LOG:]:
        problems.append("%s: the logged messages differ from the model's" % name)
    on, off = midi_notes(model, channel)
    if (r["notes_on"], r["notes_off"]) != (on, off):
        problems.append("%s: %d note ons and %d offs taken, expected %d and %d"
                        % (name, r["notes_on"], r["notes_off"], on, off))
    f = fm_record(os.path.join(case_dir, fm_name()))
    if idle and (r["held"] or r["pedal"] or f["voices0"] or f["voices1"]):
        problems.append("%s: at the end %d notes held, pedal %d, %d + %d voices sounding: a stuck note"
                        % (name, r["held"], r["pedal"], f["voices0"], f["voices1"]))
    lines.append("  midi: %d bytes, %d messages (%d realtime), %d SysEx (%d bytes, %d too long, %d cut), "
                 "%d orphans, %d undefined, %d cut, %d filtered; %d note ons, %d offs; model: same"
                 % (r["bytes"], r["messages"], r["realtime"], r["sysex"], r["sysex_bytes"], r["sysex_long"],
                    r["sysex_cut"], r["orphans"], r["undefined"], r["cut"], r["filtered"],
                    r["notes_on"], r["notes_off"]) if not problems else
                 "  midi: %d bytes, %d messages" % (r["bytes"], r["messages"]))
    return problems, lines, r, model


def midi_times(name, status, d1=None):
    """Arrival times (ms) of the last byte of each message in a script
    whose status (high nibble for channel messages) and first data byte
    match, running status included."""
    out, cur, have = [], 0, []
    for t, b in midi_scripts.stream(os.path.join(ROOT, "tests", "fw", "scripts", name + ".txt")):
        if b >= 0xF8:
            continue
        if b >= 0x80:
            cur, have = (b if b < 0xF0 else 0), []
            continue
        if not cur:
            continue
        have.append(b)
        if len(have) == midi_model.data_bytes(cur):
            if (cur & 0xF0) == status and (d1 is None or have[0] == d1):
                out.append((t, have))
            have = []
    return out


def pitch_at(x, ends, t0, t1):
    """The median pitch (MIDI note) of the sound between t0 and t1 ms."""
    first = next(i for i in range(len(x)) if aa.sample_ms(i, ends) >= t0)
    last = next(i for i in range(first, len(x)) if aa.sample_ms(i, ends) >= t1)
    track = sorted(69 + 12 * math.log2(hz / 440.0) for _, hz in aa.pitch_track(x, first, last))
    return track[len(track) // 2] if track else None, track


def level_at(x, ends, t0, t1):
    at = lambda ms: next(i for i in range(len(x)) if aa.sample_ms(i, ends) >= ms)
    return rms_db(x[at(t0):at(t1)])


def check_midimsg(case_dir):
    """Every message the engine takes (R-MIDI-2, R-MIDI-3): the bends at
    the default range and after RPN 0 sets 12, the mod wheel's vibrato,
    volume and expression, all sound off, the program change."""
    problems, lines, a, _, wav = check_audio_common("midimsg", case_dir)
    more, l2, r, _ = midi_common("midimsg", case_dir)
    problems, lines = problems + more, lines + l2
    f = fm_record(os.path.join(case_dir, fm_name()))
    if r["program"] != 8 or f["patch"] != 8:
        problems.append("midimsg: program %d, patch %d in force; expected 8 (9 is ignored)" % (r["program"], f["patch"]))
    if (r["bend"], r["mod"], r["volume"], r["expression"]) != (0, 0, 127, 127):
        problems.append("midimsg: at the end bend %d, mod %d, volume %d, expression %d"
                        % (r["bend"], r["mod"], r["volume"], r["expression"]))
    if wav is None:
        return problems + ["midimsg: no audio.wav"], lines
    x, ends = wav
    bends = midi_times("midimsg", 0xE0)
    ccs = {(d[0], d[1]): t for t, d in midi_times("midimsg", 0xB0)}
    # Note 64 bent to the top (+2), and note 65 at range 12 (+12).
    want = []
    for t, d in bends:
        if d == [0x7F, 0x7F]:
            nxt = min(u for u, _ in bends if u > t)
            want.append((t, nxt))
    got = []
    for (t0, t1), note in zip(want, (66, 77)):
        p, _ = pitch_at(x, ends, t0 + 5, t1 - 2)
        got.append(p)
        if p is None or abs(p - note) > MIDI_BEND_SEMI:
            problems.append("midimsg: bent to the top, note %s, not %d" % (p, note))
    # Vibrato: CC 1 at 127 swings note 64 by half a semitone.
    _, track = pitch_at(x, ends, ccs[(1, 127)] + 20, ccs[(1, 0)] - 5)
    swing = (track[-1] - track[0]) / 2 if track else 0
    if not 0.4 <= swing <= 0.55:
        problems.append("midimsg: vibrato swings %.3f semitones, not about 0.5" % swing)
    # Volume 64 and expression 100: (64/127)^2 (100/127)^2 against note 60's level.
    ons = midi_times("midimsg", 0x90)
    t60 = ons[0][0]
    t67 = next(t for t, d in ons if d[0] == 67)
    ref, low = level_at(x, ends, t60 + 30, t60 + 120), level_at(x, ends, t67 + 30, t67 + 90)
    expect = 40 * math.log10(64 / 127.0) + 40 * math.log10(100 / 127.0)
    if abs((low - ref) - expect) > MIDI_LEVEL_DB:
        problems.append("midimsg: volume and expression take %.2f dB, not %.2f" % (low - ref, expect))
    # All sound off: silent soon after its last byte.
    t_off = ccs[(120, 0)]
    after = [i for i in range(len(x)) if t_off + MIDI_SOUND_OFF_MS <= aa.sample_ms(i, ends) < t_off + 50]
    loud = max(abs(x[i]) for i in after) if after else 0
    if loud:
        problems.append("midimsg: still sounding %.1f ms after all sound off (peak %d)" % (MIDI_SOUND_OFF_MS, loud))
    lines.append("  bent to notes %s (66, 77 asked); vibrato +-%.3f semitones; volume and expression %.2f dB "
                 "(%.2f); silent %.0f ms after all sound off; program 8 in force"
                 % (", ".join("%.3f" % g for g in got if g is not None), swing, low - ref, expect, MIDI_SOUND_OFF_MS))
    return problems, lines


def midi_only(name, last_only=False):
    """A parser case: midi_common's checks, and the notes after the junk
    sound: each note on (or, after random junk, only the last) has sound
    within MIDI_LATENCY_MS of its last byte."""
    def check(case_dir):
        problems, lines, a, _, wav = check_audio_common(name, case_dir)
        more, l2, r, model = midi_common(name, case_dir)
        problems, lines = problems + more, lines + l2
        if wav is None:
            return problems + ["%s: no audio.wav" % name], lines
        x, ends = wav
        ons = [t for t, d in midi_times(name, 0x90) if d[1]]
        if last_only:
            ons = ons[-1:]
        silent = [t for t in ons
                  if not any(x[i] for i in range(len(x)) if t <= aa.sample_ms(i, ends) <= t + MIDI_LATENCY_MS)]
        if silent:
            problems.append("%s: no sound within %.1f ms of the note ons at %s ms"
                            % (name, MIDI_LATENCY_MS, ", ".join("%.2f" % t for t in silent)))
        lines.append("  %d note ons checked: each sounds within %.1f ms" % (len(ons), MIDI_LATENCY_MS))
        return problems, lines
    return check


def check_mididense(case_dir):
    """The wire full for 6 s (R-MIDI-4): every byte taken, every note on
    and off, no underrun, all 16 voices used, nothing stuck at the end."""
    problems, lines, a, _, _ = check_audio_common("mididense", case_dir)
    more, l2, r, model = midi_common("mididense", case_dir)
    f = fm_record(os.path.join(case_dir, fm_name()))
    if f["voices_max"] != FM_VOICES:
        more.append("mididense: at most %d voices at once, not %d" % (f["voices_max"], FM_VOICES))
    lines = lines + l2 + ["  %d voices at most; %d notes started; longest fill %.1f us"
                          % (f["voices_max"], f["notes"], a["fill_max"] / 24.0)]
    return problems + more, lines


# midisustain's captures: (ms, notes MIDI or the pedal holds, pedal down).
SUSTAIN_AT = ((300, 1, 1), (560, 2, 1), (700, 3, 1), (1000, 0, 0), (1300, 1, 1))


def check_midisustain(case_dir):
    """The sustain pedal (R-MIDI-3): a note released under it held on, a
    note struck again under it, a panel key released under it, all notes
    off with it down; the pedal up ends them."""
    problems, lines, a, _, _ = check_audio_common("midisustain", case_dir)
    more, l2, r, _ = midi_common("midisustain", case_dir)
    problems, lines = problems + more, lines + l2
    seen = []
    for ms, held, pedal in SUSTAIN_AT:
        c = midi_record(os.path.join(case_dir, midi_name("%dms" % ms)))
        f = fm_record(os.path.join(case_dir, fm_name("%dms" % ms)))
        on = f["voices0"] + f["voices1"]
        seen.append("%d ms: %d held, pedal %d, %d sounding" % (ms, c["held"], c["pedal"], on))
        if (c["held"], c["pedal"]) != (held, pedal) or (held and on < held):
            problems.append("midisustain: at %d ms %d held, pedal %d, %d voices sounding; expected %d, %d"
                            % (ms, c["held"], c["pedal"], on, held, pedal))
    lines.append("  " + "; ".join(seen))
    return problems, lines


def check_midichan(case_dir):
    """The channel test build, on channel 10 (R-MIDI-5): everything on the
    other 15 channels filtered, channel 10's note played."""
    problems, lines, a, _, _ = check_audio_common("midichan", case_dir)
    more, l2, r, model = midi_common("midichan", case_dir, channel=9)
    problems, lines = problems + more, lines + l2
    others = sum(1 for s, _, _, _ in model.log if s < 0xF0 and s & 15 != 9)
    if r["filtered"] != others:
        problems.append("midichan: %d messages filtered, %d were for other channels" % (r["filtered"], others))
    if r["volume"] != 127 or r["program"] != 0xFFFFFFFF or r["notes_on"] != 1:
        problems.append("midichan: volume %d, program 0x%x, %d note ons: another channel got through"
                        % (r["volume"], r["program"], r["notes_on"]))
    return problems, lines


# midipanel's captures: (ms, voices sounding at least).
PANEL_AT = ((200, 1), (300, 1), (500, 1), (600, 1), (900, 3))


def check_midipanel(case_dir):
    """MIDI and the panel together (R-MIDI-6): the same note held from
    both, each released while the other holds it, sounds on; the screen
    (golden) shows MIDI's notes; nothing stuck at the end."""
    problems, lines, a, _, _ = check_audio_common("midipanel", case_dir)
    more, l2, r, _ = midi_common("midipanel", case_dir)
    problems, lines = problems + more, lines + l2
    seen = []
    for ms, voices in PANEL_AT:
        f = fm_record(os.path.join(case_dir, fm_name("%dms" % ms)))
        on = f["voices0"] + f["voices1"]
        seen.append("%d ms: %d" % (ms, on))
        if on < voices:
            problems.append("midipanel: at %d ms %d voices sound, expected at least %d" % (ms, on, voices))
    lines.append("  voices sounding at " + ", ".join(seen))
    return problems, lines


def check_midilat(case_dir):
    """Latency (R-MIDI-7): from each note on's last byte (the script's time
    and the wire's pace, docs/HARNESS.md) to the first sample of its sound
    (ipb.csv's block ends, exact), within MIDI_LATENCY_MS."""
    problems, lines, a, _, wav = check_audio_common("midilat", case_dir)
    more, l2, r, _ = midi_common("midilat", case_dir)
    problems, lines = problems + more, lines + l2
    if wav is None:
        return problems + ["midilat: no audio.wav"], lines
    x, ends = wav
    starts = [aa.sample_ms(first, ends) for first, _ in sounds(x)]
    ons = [t for t, d in midi_times("midilat", 0x90) if d[1]]
    lat = []
    for t in ons:
        s = [u for u in starts if u >= t]
        lat.append(s[0] - t if s else None)
    if len(starts) != len(ons) or None in lat:
        return problems + ["midilat: %d sounds for %d note ons" % (len(starts), len(ons))], lines
    lines.append("  latency, last byte to first sample: %.3f to %.3f ms, mean %.3f (bound %.1f), %d notes"
                 % (min(lat), max(lat), sum(lat) / len(lat), MIDI_LATENCY_MS, len(lat)))
    if max(lat) > MIDI_LATENCY_MS or min(lat) < 0:
        problems.append("midilat: latency %.3f to %.3f ms, bound %.1f" % (min(lat), max(lat), MIDI_LATENCY_MS))
    return problems, lines


# --- MIDI out (M6b; R-MIDIOUT-*) -----------------------------------------

MIDI_OUT_ADDR, MIDI_OUT_LEN = 0x01c00734, 0x4c
MIDI_OUT_FIELDS = ("marker", "queued", "merged", "dropped", "offs_dropped", "offs_lost", "waiting_max",
                   "messages", "bytes", "running", "transfers", "polls_busy", "thru", "thru_sysex",
                   "panel_notes", "panel_ccs", "panel_programs", "last_note_tick", "last_start_tick")
MIDI_OUT_MARKER = 0x424F444D  # "MDOB", firmware/src/midi_out.h
MIDI_OUT_CHUNK = 12           # the most bytes a transfer takes (midi_out.h)
BYTE_MS = midi_scripts.BYTE_MS
BLOCK_MS = 1000.0 * 64 * 544 / 24000000
MIDI_OUT_LATENCY_MS = 6.5     # a panel key down to its note on's first start bit (R-MIDIOUT-8)
ROUND_SEMI = 0.05             # a note's pitch, round trip against the panel's


def midi_out_record(path):
    with open(path, "rb") as f:
        b = f.read()
    return dict(zip(MIDI_OUT_FIELDS, struct.unpack("<%dI" % len(MIDI_OUT_FIELDS), b[:MIDI_OUT_LEN])))


def midi_out_name(when="end"):
    return "ram-%08x-%x-%s.bin" % (MIDI_OUT_ADDR, MIDI_OUT_LEN, when)


def wire_bytes(path):
    """midi-out.csv: [(ms, byte)], each byte's stop bit's end."""
    with open(path) as f:
        rows = [l.strip().split(",") for l in f][1:]
    return [(float(ms), int(b, 16)) for ms, b in rows if ms]


def wire_messages(wire):
    """The messages on the wire, by the parser model's rules (running
    status, realtime anywhere): [(ms of the last byte, (status, d1, d2,
    length))], and the model."""
    model = midi_model.Parser()
    out = []
    for t, b in wire:
        n = len(model.log)
        model.byte(b)
        out += [(t, m) for m in model.log[n:]]
    return out, model


def wire_runs(wire):
    """Bytes 320 us apart, one transfer each: [(first index, end index)]."""
    runs, i = [], 0
    while i < len(wire):
        j = i + 1
        while j < len(wire) and abs(wire[j][0] - wire[j - 1][0] - BYTE_MS) < 1e-6:
            j += 1
        runs.append((i, j))
        i = j
    return runs


def midi_out_common(name, case_dir):
    """Every MIDI out case (R-MIDIOUT-1, R-MIDIOUT-7): the wire's timing,
    the transfers, running status and the record. Bytes never closer than
    one byte time; each run of bytes back to back is one transfer of at
    most MIDI_OUT_CHUNK bytes, as many runs as the firmware started
    transfers (so it never started one while another ran: fwtest would
    have sent it straight after, in the same run); the bytes it handed on
    are those on the wire, none dropped; every byte makes whole messages
    (no orphan, nothing cut short, no SysEx); and a message after a gap of
    more than two blocks (the wire ran dry at a poll) carries its status.
    Returns (problems, lines, record, [(ms, message)], wire)."""
    problems, lines = [], []
    with open(os.path.join(case_dir, "result.json")) as f:
        run = json.load(f).get("run", {})
    if run.get("midi_out_bytes_dropped"):
        problems.append("%s: fwtest dropped %s MIDI out bytes (the UART was off)" % (name, run["midi_out_bytes_dropped"]))
    r = midi_out_record(os.path.join(case_dir, midi_out_name()))
    if r["marker"] != MIDI_OUT_MARKER:
        return problems + ["%s: the MIDI out record's marker is 0x%08x" % (name, r["marker"])], lines, r, [], []
    wire = wire_bytes(os.path.join(case_dir, "midi-out.csv"))
    gaps = [b[0] - a[0] for a, b in zip(wire, wire[1:])]
    if gaps and min(gaps) < BYTE_MS - 1e-6:
        problems.append("%s: two bytes %.3f ms apart, under a byte's time" % (name, min(gaps)))
    runs = wire_runs(wire)
    longest = max([j - i for i, j in runs] or [0])
    if longest > MIDI_OUT_CHUNK:
        problems.append("%s: %d bytes back to back, more than one transfer takes (%d)" % (name, longest, MIDI_OUT_CHUNK))
    if (len(runs), len(wire)) != (r["transfers"], r["bytes"]):
        problems.append("%s: %d runs of %d bytes on the wire; the firmware started %d transfers of %d bytes"
                        % (name, len(runs), len(wire), r["transfers"], r["bytes"]))
    msgs, model = wire_messages(wire)
    bad = {k: model.count[k] for k in ("orphans", "undefined", "cut", "sysex")}
    if any(bad.values()) or model.status and model.data:
        problems.append("%s: the wire holds broken messages: %s" % (name, bad))
    if len(msgs) != r["messages"]:
        problems.append("%s: %d messages on the wire, the firmware sent %d" % (name, len(msgs), r["messages"]))
    quiet = [i for (i, _), (_, k) in zip(runs[1:], runs) if wire[i][0] - BYTE_MS - wire[k - 1][0] > 2 * BLOCK_MS]
    stale = [wire[i][0] for i in quiet if wire[i][1] < 0x80]
    if stale:
        problems.append("%s: after the wire went quiet, a message without its status at %.3f ms" % (name, stale[0]))
    lines.append("  midi out: %d bytes in %d transfers (longest %d), %d messages, %d status bytes left out, "
                 "%d merged, %d dropped (%d note offs with them, %d lost), at most %d waiting"
                 % (len(wire), len(runs), longest, len(msgs), r["running"], r["merged"], r["dropped"],
                    r["offs_dropped"], r["offs_lost"], r["waiting_max"]))
    return problems, lines, r, msgs, wire


def out_notes(msgs):
    """Note ons and offs on the wire as (ms, status's channel, note, velocity)."""
    return [(t, m[0] & 15, m[1], m[2] if m[0] & 0xF0 == 0x90 else 0)
            for t, m in msgs if m[0] & 0xF0 in (0x80, 0x90)]


def notes_paired(name, msgs):
    """Each note on has its note off after it, and no note off comes
    without one: nothing left held at the far end."""
    held, problems = set(), []
    for _, ch, n, v in out_notes(msgs):
        if v:
            held.add((ch, n))
        elif (ch, n) in held:
            held.discard((ch, n))
        else:
            problems.append("%s: a note off for channel %d note %d, never on" % (name, ch + 1, n))
    if held:
        problems.append("%s: notes left on at the far end: %s" % (name, sorted(held)))
    return problems


def expect_messages(name, msgs, expected, lines):
    """The messages on the wire, realtime left out, against expected (a
    list of tuples, or of sets for messages whose order within a group is
    the panel's scan order)."""
    got = [m[:m[3] + 1] if m[3] else (m[0],) for _, m in msgs if m[0] < 0xF8]
    i, problems = 0, []
    for e in expected:
        group = e if isinstance(e, set) else {e}
        if sorted(got[i:i + len(group)]) != sorted(group):
            problems.append("%s: message %d on the wire is %s, expected %s"
                            % (name, i + 1, got[i:i + len(group)], sorted(group)))
            return problems
        i += len(group)
    if i != len(got):
        problems.append("%s: %d messages more than expected: %s" % (name, len(got) - i, got[i:i + 4]))
    else:
        lines.append("  the %d messages expected, in order" % len(got))
    return problems


def on_off(ch, note, vel=100):
    return [(0x90 | ch, note, vel), (0x90 | ch, note, 0)]


def knob_ccs(k, positions):
    """Each knob position's controller value (the map's inverse,
    midi_model.knob_value), only when it changes."""
    out, last = [], None
    for p in positions:
        v = midi_model.knob_value(k, p)
        if v != last:
            out.append((0xB0, 16 + k, v))
            last = v
    return out


def check_midiout(case_dir):
    """What the panel sends (R-MIDIOUT-1 to R-MIDIOUT-3): the notes, the
    knobs' controllers, program and mode changes, against what the script
    does, and the capture against its golden files."""
    problems, lines, a, _, _ = check_audio_common("midiout", case_dir)
    more, l2, r, msgs, _ = midi_out_common("midiout", case_dir)
    problems, lines = problems + more, lines + l2
    expected = on_off(0, 53)
    expected += [{(0x90, 60, 100), (0x90, 64, 100), (0x90, 67, 100)}, {(0x90, 60, 0), (0x90, 64, 0), (0x90, 67, 0)}]
    expected += knob_ccs(0, range(1, 6)) + knob_ccs(1, range(-1, -4, -1)) + knob_ccs(2, range(-1, -11, -1))
    expected += knob_ccs(3, range(1, 8)) + [(0xC0, 1), (0xC0, 2)] + on_off(0, 53 + 4 + 12)
    expected += [(0xB0, 126, 1), (0xB0, 127, 0)] + knob_ccs(0, range(6, 36))[0:] + on_off(0, 53 + 2 + 12)
    problems += expect_messages("midiout", msgs, expected, lines)
    problems += notes_paired("midiout", msgs)
    if r["running"] == 0:
        problems.append("midiout: no status byte left out: the chord should use running status")
    return problems, lines


def check_midiround(case_dir):
    """The round trip (R-MIDIOUT-6): midiout's golden MIDI out played into
    MIDI in. Its script is that capture (tools/midi_scripts.py --check);
    the parser takes every byte as the model does, and at the end the
    engine has midiout's patch, mode and knobs; the notes played alone
    have the pitch they had in midiout."""
    problems, lines, a, _, wav = check_audio_common("midiround", case_dir)
    more, l2, r, model = midi_common("midiround", case_dir)
    problems, lines = problems + more, lines + l2
    other = os.path.join(os.path.dirname(case_dir), "midiout")
    fa, fb = fm_record(os.path.join(other, fm_name())), fm_record(os.path.join(case_dir, fm_name()))
    keys = ("patch", "algorithm", "mono", "pitch_knob", "glide", "depth", "feedback", "notes")
    diff = [k for k in keys if fa[k] != fb[k]]
    if diff:
        problems.append("midiround: the engine's %s differ from midiout's: %s against %s"
                        % (", ".join(diff), [fb[k] for k in diff], [fa[k] for k in diff]))
    else:
        lines.append("  the engine at the end as midiout's: " + ", ".join("%s %d" % (k, fa[k]) for k in keys))
    wa = None
    if os.path.exists(os.path.join(other, "audio.wav")):
        wa = (aa.read_wav(os.path.join(other, "audio.wav"))[1], aa.read_ipb(os.path.join(other, "ipb.csv")))
    if wav is None or wa is None:
        return problems + ["midiround: no audio.wav"], lines
    ons = [t for t, d in midi_times("midiround", 0x90) if d[1]]
    alone = [t for t in ons if all(abs(u - t) > 20 for u in ons if u != t)]
    seen = []
    for t in alone:
        pa, _ = pitch_at(wa[0], wa[1], t + 10, t + 60)
        pb, _ = pitch_at(wav[0], wav[1], t + 10, t + 60)
        seen.append("%.2f/%.2f" % (pa or 0, pb or 0))
        if pa is None or pb is None or abs(pa - pb) > ROUND_SEMI:
            problems.append("midiround: the note at %.1f ms has pitch %s, midiout's %s" % (t, pb, pa))
    lines.append("  notes alone, pitch midiout/midiround: " + ", ".join(seen))
    return problems, lines


def check_midithru(case_dir):
    """MIDI thru (R-MIDIOUT-4): every message MIDI in received, but the
    SysEx, goes out once and in order (the parser model's messages for
    the script's bytes), the panel's on channel 2 once each, and nothing
    else."""
    problems, lines, a, _, _ = check_audio_common("midithru", case_dir)
    more, l2, r, model = midi_common("midithru", case_dir)
    problems, lines = problems + more, lines + l2
    more, l2, o, msgs, _ = midi_out_common("midithru", case_dir)
    problems, lines = problems + more, lines + l2
    passed = [m for m in model.log if m[0] != 0xF0]
    panel = [m for _, m in msgs if m[0] == 0x91]
    thru = [m for _, m in msgs if m[0] != 0x91]
    if thru != passed:
        problems.append("midithru: %d messages passed on, %d received (SysEx left out); first difference at %s"
                        % (len(thru), len(passed), next((i for i, (x, y) in enumerate(zip(thru, passed)) if x != y),
                                                       min(len(thru), len(passed)))))
    want = [(0x91, 53, 100, 2), (0x91, 53, 0, 2), (0x91, 55, 100, 2), (0x91, 55, 0, 2)]
    if panel != want:
        problems.append("midithru: the panel sent %s, expected %s" % (panel, want))
    sysex = len(model.log) - len(passed)
    if (o["thru"], o["thru_sysex"]) != (len(passed), sysex):
        problems.append("midithru: the record says %d passed on and %d SysEx not; expected %d and %d"
                        % (o["thru"], o["thru_sysex"], len(passed), sysex))
    lines.append("  thru: %d messages passed on in order (%d realtime), %d SysEx not; the panel's %d once each"
                 % (len(thru), sum(1 for m in thru if m[0] >= 0xF8), sysex, len(panel)))
    return problems, lines


def check_midilocal(case_dir):
    """Local control (R-MIDIOUT-5): while off, the panel's keys, KNOB1 and
    PRESETS go out but the engine plays no key and keeps its patch and
    knobs (captured at 700 ms), while a MIDI note plays; on again, a key
    plays with KNOB1's position taken up. The screen at 700 ms shows
    "local off" (golden)."""
    problems, lines, a, _, wav = check_audio_common("midilocal", case_dir)
    more, l2, r, _ = midi_common("midilocal", case_dir)
    problems, lines = problems + more, lines + l2
    more, l2, o, msgs, _ = midi_out_common("midilocal", case_dir)
    problems, lines = problems + more, lines + l2
    expected = on_off(0, 53) + knob_ccs(0, range(1, 7)) + [(0xC0, 1), (0xC0, 2), (0xC0, 3)]
    expected += on_off(0, 57) + on_off(0, 60)
    problems += expect_messages("midilocal", msgs, expected, lines)
    f = fm_record(os.path.join(case_dir, fm_name("700ms")))
    if (f["patch"], f["pitch_knob"], f["notes"]) != (0, 0, 0):
        problems.append("midilocal: with local control off the engine took patch %d, KNOB1 %d, %d notes"
                        % (f["patch"], f["pitch_knob"], f["notes"]))
    if wav is None:
        return problems + ["midilocal: no audio.wav"], lines
    x, ends = wav
    starts = [aa.sample_ms(first, ends) for first, _ in sounds(x)]
    if len(starts) != 2 or not 800 < starts[0] < 810 or not 1100 < starts[1] < 1110:
        problems.append("midilocal: sounds start at %s ms; expected only the MIDI note (800) and the key (1100)"
                        % ["%.1f" % u for u in starts])
    p1, _ = pitch_at(x, ends, 820, 880)
    p2, _ = pitch_at(x, ends, 1120, 1180)
    lines.append("  sounds at %s ms; pitch %.2f (MIDI 67, KNOB1 not taken), %.2f (key 60 + KNOB1 6)"
                 % (", ".join("%.1f" % u for u in starts), p1 or 0, p2 or 0))
    if p1 is None or abs(p1 - 67) > ROUND_SEMI or p2 is None or abs(p2 - 66) > ROUND_SEMI:
        problems.append("midilocal: pitches %s and %s, expected 67 and 66" % (p1, p2))
    return problems, lines


def check_midiburst(case_dir):
    """A burst past the queue (R-MIDIOUT-7): the policy holds (the
    controllers and bends merge, note ons past the room for them are
    dropped with their note offs, no note off is lost), every note on the
    wire ends, the wire's timing holds, and the panel's keys afterwards go
    out within the latency bound: nothing wedged."""
    problems, lines = [], []
    more, l2, r, msgs, wire = midi_out_common("midiburst", case_dir)
    problems, lines = problems + more, lines + l2
    problems += notes_paired("midiburst", msgs)
    ons = [n for _, ch, n, v in out_notes(msgs) if v and n >= 60]
    if r["merged"] < 19 + 9 or r["offs_lost"] or not r["dropped"] or r["offs_dropped"] != 32 - len(ons):
        problems.append("midiburst: %d merged, %d dropped, %d note offs dropped, %d lost, %d of 32 burst notes sent"
                        % (r["merged"], r["dropped"], r["offs_dropped"], r["offs_lost"], len(ons)))
    panel = [t for t, ch, n, v in out_notes(msgs) if v and n in (53, 55)]
    keys = [1300, 1500]
    late = [p - BYTE_MS * 3 - k for p, k in zip(panel, keys)]      # the note on's first start bit
    if len(panel) != 2 or max(late) > MIDI_OUT_LATENCY_MS:
        problems.append("midiburst: the panel's notes after the burst at %s ms" % panel)
    lines.append("  burst: %d of its 32 notes sent, each ended; the panel's 2 keys after it sent" % len(ons))
    return problems, lines


def check_midioutlat(case_dir):
    """Latency (R-MIDIOUT-8): from each key going down (the script's time)
    to its note on's first byte starting on the wire (midi-out.csv's stop
    bit time less one byte time), within MIDI_OUT_LATENCY_MS."""
    problems, lines, a, _, _ = check_audio_common("midioutlat", case_dir)
    more, l2, r, msgs, wire = midi_out_common("midioutlat", case_dir)
    problems, lines = problems + more, lines + l2
    keys = [100 + 150 * i for i in range(20)]
    firsts = [t - BYTE_MS for t, b in wire if b == 0x90]
    ons = [t for t, ch, n, v in out_notes(msgs) if v]
    if len(ons) != 20 or len(firsts) < 20:
        return problems + ["midioutlat: %d note ons on the wire for 20 keys" % len(ons)], lines
    starts = [next(f for f in firsts if f >= k) for k in keys]
    lat = [s - k for s, k in zip(starts, keys)]
    lines.append("  latency, key down to the note on's first start bit: %.3f to %.3f ms, mean %.3f (bound %.1f)"
                 % (min(lat), max(lat), sum(lat) / len(lat), MIDI_OUT_LATENCY_MS))
    if max(lat) > MIDI_OUT_LATENCY_MS:
        problems.append("midioutlat: latency up to %.3f ms, bound %.1f" % (max(lat), MIDI_OUT_LATENCY_MS))
    return problems, lines


MIDI_CHECKS = {"midimsg": check_midimsg, "midirun": midi_only("midirun"),
               "midisysex": midi_only("midisysex"), "midijunk": midi_only("midijunk", last_only=True),
               "mididense": check_mididense, "midisustain": check_midisustain,
               "midichan": check_midichan, "midipanel": check_midipanel, "midilat": check_midilat,
               "midiout": check_midiout, "midiround": check_midiround, "midithru": check_midithru,
               "midilocal": check_midilocal, "midiburst": check_midiburst, "midioutlat": check_midioutlat}


AUDIO_CHECKS = {"tone": check_tone, "notes": check_notes, "audioload": check_audioload,
                "audiogold": check_audiogold, "underrun": check_underrun,
                "fmbessel": check_fmbessel, "fmenv": check_fmenv, "fmmono": check_fmmono,
                "fmsteal": check_fmsteal, "fmvel": check_fmvel, "fmgold": check_fmgold, "fmgold2": check_fmgold}
AUDIO_CHECKS.update(MIDI_CHECKS)


# --- The screens (M8a) ---------------------------------------------------

UI_ADDR, UI_LEN = 0x01C00870, 0x50
UI_MARKER = 0x38495553
UI_FIELDS = ("marker screen seq shows frames items rows_sent item_max block_max over leds messages"
             " live live_max item_max_part reserved macro0 macro1 macro2 macro3").split()
UI_PATCH, UI_EDIT, UI_ENV, UI_SETTINGS = range(4)
DRAW_TICKS = 4352          # views.c: drawing a block may take before no more parts start
SCREEN_BUTTON = {UI_PATCH: 8, UI_EDIT: 6, UI_ENV: 4, UI_SETTINGS: 7}   # HOME, EDIT, ENV, GLO
OP1_KEY = 15               # KEY2, the raised key labelled OP1


def ui_record(case_dir, when="end"):
    name = "ram-%08x-%x-%s.bin" % (UI_ADDR, UI_LEN, when if when == "end" else "%dms" % when)
    with open(os.path.join(case_dir, name), "rb") as f:
        u = dict(zip(UI_FIELDS, struct.unpack("<%dI" % len(UI_FIELDS), f.read()[:UI_LEN])))
    u["macros"] = [m - (1 << 32) if m >= 1 << 31 else m for m in (u.pop("macro%d" % k) for k in range(4))]
    return u


def check_drawing(name, u, budget=True):
    """Every part of a screen within the budget, and the block total
    within two budgets (no part starts once a block's budget is spent).
    A part's time is the time base's, so under load it includes the audio
    interrupts that came meanwhile: there (budget False) it is reported,
    not checked."""
    problems = []
    if u["marker"] != UI_MARKER:
        problems.append("%s: no interface record" % name)
    if budget and (u["item_max"] > DRAW_TICKS or u["block_max"] >= 2 * DRAW_TICKS):
        problems.append("%s: the longest part %d time base ticks (part %d), a block's drawing %d; at most %d and"
                        " under %d" % (name, u["item_max"], u["item_max_part"], u["block_max"], DRAW_TICKS,
                                       2 * DRAW_TICKS))
    return problems, ("  drawing: %d screens, %d frames, %d parts, %d rows sent; longest part %d ticks (part %d),"
                      " most in a block %d (budget %d)" % (u["shows"], u["frames"], u["items"], u["rows_sent"],
                                                          u["item_max"], u["item_max_part"], u["block_max"],
                                                          DRAW_TICKS))


def check_views(case_dir):
    """The screens in turn (tests/fw/scripts/views.txt): each one when its
    button is pressed, HOME back to the patch view, the controls that mean
    the same on every screen, the screen's button lit and the selected
    operator's key at half on EDIT and ENV; golden images of each."""
    problems, lines = [], []
    want = {850: UI_PATCH, 1150: UI_EDIT, 1450: UI_ENV, 1750: UI_SETTINGS, 2050: UI_SETTINGS, 2350: UI_PATCH}
    for when, screen in sorted(want.items()):
        u = ui_record(case_dir, when)
        if u["screen"] != screen:
            problems.append("views: at %d ms the screen is %d, expected %d" % (when, u["screen"], screen))
    u = ui_record(case_dir)
    more, line = check_drawing("views", u)
    problems += more
    lines.append(line)
    if u["shows"] != 5:
        problems.append("views: %d whole screens drawn, expected 5 (the first, then four changes)" % u["shows"])
    f = fm_record(os.path.join(case_dir, fm_name()))
    a = audio_record(os.path.join(case_dir, audio_name()))
    if f["patch"] != 2 or a["octave"] != 1 or a["master"] != 700 * 700 * 16:
        problems.append("views: on the settings screen PRESETS, OCT+ and MASTER gave program %d, octave %d,"
                        " gain %d; expected 2, 1, %d" % (f["patch"], a["octave"], a["master"], 700 * 700 * 16))
    # LEDs, sampled every 50 ms: clear of each change by 50 ms.
    for ms, duty in read_leds(case_dir):
        screen = None
        for when, sc in ((650, UI_PATCH), (950, UI_EDIT), (1250, UI_ENV), (1550, UI_SETTINGS), (2150, UI_PATCH)):
            if ms >= when:
                screen = sc
        # A sample's share is the LED's over the 50 ms before it.
        if screen is None or any(t - 5 < ms < t + 60 for t in (600, 900, 1200, 1500, 1850, 2100)):
            continue
        for c in list(SCREEN_BUTTON.values()) + [OP1_KEY]:
            lit = duty[c]
            if c == SCREEN_BUTTON[screen]:
                ok = LED_FULL_DUTY[0] <= lit <= LED_FULL_DUTY[1]
            elif c == OP1_KEY and screen in (UI_EDIT, UI_ENV):
                ok = LED_FULL_DUTY[0] / 2 - 10 <= lit <= LED_FULL_DUTY[1] / 2 + 10
            else:
                ok = lit == 0
            if not ok:
                problems.append("views: LED %d at %.0f ms: %d, wrong for screen %d" % (c, ms, lit, screen))
    lines.append("  screens: patch, EDIT, ENV, settings, then HOME back; on the settings screen PRESETS, OCT+ and"
                 " MASTER as everywhere; each screen's button lit, OP1's key at half on EDIT and ENV")
    return problems[:20], lines


def check_viewsload(case_dir):
    """The screens changing every 100 ms under the heaviest input
    (tests/fw/scripts/viewsload.txt): no underrun, every tick on time,
    every part of every screen within the drawing budget."""
    problems, lines, a, console, _ = check_audio_common("viewsload", case_dir)
    more, tl = check_ticks_under_load("viewsload", case_dir)
    problems += more
    lines += tl
    u = ui_record(case_dir)
    more, line = check_drawing("viewsload", u, budget=False)
    problems += more
    lines.append(line + " (with the audio's interrupts)")
    # 29 changes of screen, every 100 ms; while one is drawn the next may
    # come, and the screen then shows the latest.
    if u["shows"] < 25 or u["screen"] != UI_EDIT:
        problems.append("viewsload: %d whole screens drawn, the last %d; expected at least 25, the last EDIT"
                        % (u["shows"], u["screen"]))
    f = fm_record(os.path.join(case_dir, fm_name()))
    if f["voices_max"] != FM_VOICES:
        problems.append("viewsload: %d voices at most, expected %d" % (f["voices_max"], FM_VOICES))
    lines.append("  %d screens drawn under %d voices, longest fill %.1f us of a %.1f us block"
                 % (u["shows"], f["voices_max"], a["fill_max"] / 24.0, BLOCK_TICKS / 24.0))
    return problems, lines


def check_macros(case_dir):
    """The macros (tests/fw/scripts/macros.txt; R-UI-6, R-UI-7): each one's
    effect on the same note, measured; back at 0 the note exactly as
    before; their controllers out as the panel turned them, and one in."""
    problems, lines, a, console, wav = check_audio_common("macros", case_dir)
    if wav is None:
        return problems + ["macros: no audio"], lines
    x, ends = wav
    f0 = aa.note_hz(70)
    rate = aa.RATE

    def onset(ms):
        i = int(ms * rate / 1000)
        while i < len(x) and not x[i]:
            i += 1
        return i

    def seg(ms, n=8192):
        i = onset(ms)
        return x[i + 2048:i + 2048 + n]

    bright = [aa.share_above(seg(t), 7.5 * f0) for t in (300, 900)]
    color = [aa.inharmonicity(seg(t), f0) for t in (300, 1550)]
    lines.append("  BRIGHT: the share above 7.5 f0 %.3f at 0, %.3f at +20" % tuple(bright))
    lines.append("  COLOR: partials off the harmonics by %.3f f0 at 0, %.3f at +32" % tuple(color))
    if not bright[1] > bright[0] + 0.1:
        problems.append("macros: BRIGHT +20 did not raise the upper partials (%.3f, %.3f)" % tuple(bright))
    if not (color[0] < 0.03 and color[1] > 0.1):
        problems.append("macros: COLOR +32 did not move the partials off the harmonics (%.3f, %.3f)" % tuple(color))
    a0, d0 = onset(300), onset(2200)
    n = int(0.25 * rate)
    if x[a0:a0 + n] != x[d0:d0 + n]:
        problems.append("macros: with every macro back at 0 the note is not the same as before")
    else:
        lines.append("  back at 0: the note is the first one again, sample for sample (%d samples)" % n)
    att = [aa.attack_ms(x[:onset(t) + int(0.9 * rate)], onset(t)) for t in (2650, 3550, 5000)]
    rel = [aa.release_ms(x, int(t * rate / 1000) + int(0.004 * rate)) for t in (2950, 3850, 6400)]
    lines.append("  SHAPE: attack to -3 dB %.1f / %.1f / %.1f ms, release to -60 dB %.0f / %.0f / %.0f ms"
                 " (0, -64, +64)" % tuple(att + rel))
    if not (att[1] <= att[0] and att[2] > 300 and att[0] < 20):
        problems.append("macros: SHAPE's attacks %s, expected -64 no slower than 0, +64 over 300 ms" % att)
    if not (rel[1] < rel[0] < rel[2] and rel[2] > 1000):
        problems.append("macros: SHAPE's releases %s, expected -64 < 0 < +64, over 1 s" % rel)
    swing = [aa.pitch_swing_cents(x, onset(t) + int(0.05 * rate), onset(t) + int(0.28 * rate))
             for t in (2650,)] + [aa.pitch_swing_cents(x, onset(9600) + int(0.05 * rate), onset(9600) + int(0.9 * rate))]
    lines.append("  MOTION: the pitch swings %.1f cents at 0, %.1f at +64" % tuple(swing))
    if not (swing[0] < 2 and swing[1] > 30):
        problems.append("macros: MOTION +64 swings the pitch %.1f cents (at 0 %.1f): expected over 30" % (swing[1], swing[0]))
    u = ui_record(case_dir)
    if u["macros"] != [0, 32, 0, 64]:
        problems.append("macros: at the end the macros are %s, expected [0, 32, 0, 64] (COLOR from MIDI)" % u["macros"])
    # Out: each macro's controller as the panel turned it, over the macros'
    # spans (midi_model.MACRO_SPAN).
    msgs = [m for _, m in wire_messages(wire_bytes(os.path.join(case_dir, "midi-out.csv")))[0] if m[0] == 0xB0]
    want = []
    for k, path in ((0, list(range(1, 21)) + list(range(19, -1, -1))),
                    (1, list(range(1, 33)) + list(range(31, -1, -1))),
                    (2, list(range(-1, -65, -1)) + list(range(-63, 65)) + list(range(63, -1, -1))),
                    (3, list(range(1, 65)))):
        vals, last = [], None
        for p in path:
            v = midi_model.knob_value(k, p, midi_model.MACRO_SPAN)
            if v != last:
                vals.append(v)
                last = v
        got = [m[2] for m in msgs if m[1] == 16 + k]
        want.append(len(vals))
        if got != vals:
            problems.append("macros: controller %d out %s..., expected %s..." % (16 + k, got[:6], vals[:6]))
    lines.append("  out: controllers 16 to 19, %s values, as the macros' spans give them" % want)
    return problems[:20], lines


AUDIO_CHECKS["macros"] = check_macros
AUDIO_CHECKS["viewsload"] = check_viewsload
INPUT_CHECKS = {"views": check_views, "keys": check_keys, "chords": check_chords, "encoders": check_encoders, "pot": check_pot,
                "leds": check_leds, "ledshow": check_ledshow}


# Since M8a KNOB1 to KNOB4 are the macros unless the settings say "Knobs:
# direct". The cases written for M5's and M6's controls (midiout,
# midiround, midilocal) start from a flash chip holding settings that say
# so, as a player who chose it would have: the store's own record,
# written by tools/store.py (version 3, the default map, knobs direct).
KNOBS_DIRECT = os.path.join("out", "fw", "knobs-direct.flash.bin")
DEFAULT_ROUTES = ((1, 1), (7, 2), (11, 3), (64, 4), (16, 5), (17, 6), (18, 7), (19, 8), (5, 6), (74, 7))


def settings_bytes(knobs):
    """struct midi_settings, version 3: midi.c's defaults, with knobs."""
    routes = [b for r in DEFAULT_ROUTES for b in r] + [0] * (2 * (16 - len(DEFAULT_ROUTES)))
    return bytes([3, 0, 2, len(DEFAULT_ROUTES)] + routes + [1, 0, 1, knobs])


def write_knobs_direct():
    s = store_suite.st.Store()
    s.put(store_suite.st.SETTINGS, 0, 3, settings_bytes(1))
    with open(os.path.join(ROOT, KNOBS_DIRECT), "wb") as f:
        f.write(s.chip())


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
    write_knobs_direct()

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
        elif name in AUDIO_CHECKS and run.get("outcome") == EXPECT[name]:
            try:
                more, lines = AUDIO_CHECKS[name](case_dir)
            except (OSError, ValueError) as e:
                more, lines = ["%s: %s" % (name, e)], []
        problems += more
        if lines:
            print("\n".join(lines))

    # Since M7, the store's cases: chained runs (tools/store_suite.py).
    with open(os.path.join(ROOT, IMAGE), "rb") as f:
        image_len = len(f.read())
    more, _ = store_suite.run(sys.modules[__name__], out, image_len)
    problems += more

    for prob in problems:
        print("FAIL: " + prob)
    print("fw suite: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
