#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The tests of the seams for firmwares built on small-beeps (clean-1027;
docs/DESIGN-NOTES.md, "Seams for firmwares built on small-beeps";
docs/BUILDING-ON-SMALL-BEEPS.md), check C-SEAMS.

  seams_suite.py --build DIR --out DIR [--only NAME ...]

DIR is build A's outputs (tools/build.sh build). Each case builds what it
needs with tools/build.sh into OUT/<case>/ and runs it in fwtest
(tools/fwtest, the pinned image) where it runs anything. The cases:

- ownbase (R-BUILD-3): a test build holding a store that writes back
  into the register it stores (SB_TEST_OWNBASE, firmware/src/probe.c)
  is refused, its message naming the object, the function and the
  instruction, and so is the same with PLAITS_HWFLOAT defined; build A,
  which passed the same check, holds none. Since BR-13 the check reads
  each object as it was compiled: a float-heavy object
  (tests/seams/float, as an outside source: the compiler's float code
  and a float conditional block, which read as a store without the CPU's
  features) passes, disassembled with the firmware's CPU and features
  as the base's own C is, the runtime's C with none; and with
  SB_TEST_FLOAT_OWNBASE, a real store after its float code, it is
  refused for that store alone, at its place, nothing unreadable.

- outside (R-BUILD-4): the firmware built with an outside source folder
  (tools/build.sh --src tests/seams/outside: C including a base header
  and one of its own, assembly in a folder below, C++, and a file named
  as a base file is): each one's symbols in the ELF, the base's
  same-named file built too; the folder copied to two other places on
  the host and built from each, with the source mounted at another path
  for one (as C-BUILD-B does), gives the same outputs byte for byte;
  --leave-out firmware/src/probe.c builds without it (its object never
  built) and, as it holds nothing without a test define, gives build A's
  image; a folder holding the base, a folder inside firmware/ and a base
  file that isn't one are refused.

- flags (R-BUILD-5): per-folder compiler flags (BR-11). The firmware
  built with tests/seams/flags as --src, its C given -DSB_FLAGS_OUTER=7
  -O2 (--cflags), its folder inner/ -DSB_FLAGS_INNER=5 -Iinclude as
  well, its C++ -DSB_FLAGS_CXX=2 (--cxxflags) and its assembly
  -DSB_FLAGS_ASM (--asflags): each file builds only with its folders'
  flags (each #errors otherwise; the -O2 after the base's -Os, the outer
  folder's before the inner's, -Iinclude from inner/), its symbol in the
  ELF; the base's own files' compile lines carry none of them and are
  the lines of the same build without the flags (of firmware/src/,
  which come before the folder's files stop it); the folder copied to two other places and built from
  each, one with the source mounted elsewhere, gives the same bytes; and
  refused: a folder not inside a --src folder, a base folder, an
  absolute path, "..", -fdebug-prefix-map, -o, -Xclang, -mllvm (since
  clean-mllvm), -Wp, an @file, a
  bare -isystem, and a folder without its flags. Since clean-pin-flags
  its objects must be built for the SDK's CPU and float: the folder
  given -mcpu=r3 -mfprev1 again, inner/ -mno-fprev1, its C++ -mfprev1
  and its assembly -mcpu=r3 builds (inner/'s object read as without
  float instructions); inner/ given -mcpu=r4, the C++ -mfprev2 and the
  assembly -msimd are each refused before any of the folder's files is
  compiled, the message naming the option and folder as given, the file,
  what the flag does and the fix.
- engine (R-ENG-1): the engine seam. A test engine from outside
  firmware/ (tests/seams/engine/, built with SB_ENGINE_EXTERNAL) runs in
  fwtest for 2.3 s with two key taps (tests/seams/scripts/engine.txt):
  its record (read by its ELF symbol) shows its init called once, before
  the tick's interrupts and the audio started; every audio block given
  to its block callback (as many as the audio record counts, 64 frames
  each); its serve called before the loop and on the wakes (the two
  whole seconds, the taps), seeing both taps its block callback took;
  its square wave in the audio, with no underrun; and the base's
  instrument never started (the FM engine's record still zero). The
  Plaits demo is an engine on the same seam (C-PLAITS-BENCH).
- platform (R-PLAT-1): the same test engine linked with the platform
  alone (tools/build.sh --platform, with its own script,
  tests/seams/engine/engine.ld, that includes firmware/platform.ld and
  asserts its record first among the engine's records, 0x01C00870):
  none of the instrument's functions or records in the ELF, the
  platform's records where the base has them, the package link built
  too, and the engine case's run and checks pass on it (the engine's
  slot, where the base keeps its FM engine's record, still zero).
- core 1 (R-CORE-1), within engine and platform: since BR-3 the test
  engine starts core 1 with sb_core1_start (core1.h) and hands it a job
  every block with sb_publish and sb_shared: core 1 starts (1), does one
  job a block, every answer right and in time, and source 126's vector
  word, borrowed for core 1's start, holds its stub again; with the
  platform alone too.
- runtime (R-RT-1), within engine and platform: since BR-4 the test
  engine's init runs C++ needing the platform's runtime
  (tests/seams/engine/sb_test_runtime.cc: a virtual class, std::sort,
  memcpy, memmove and memset with lengths known at run time, a static
  object whose constructor main() runs, and one with a destructor) and
  records its result, 1301; the runtime's members are in the ELF; and build A,
  which calls none of them, has none (the archive gives an image only
  what it calls).
- sysex (R-MIDI-8): MIDI in's SysEx tap, on the test engine linked with
  the platform alone. Its script, written here: a System Exclusive
  message of SYSEX_DATA (4 104) data bytes, sent in lines of 60 every
  20 ms (fwtest drops bytes when more than about a second's worth wait),
  with a clock byte (F8) in its middle; then one cut short by a note on.
  The tap sees both begin, every data byte in order and no other
  (length, sum by place, first and last, against the script's), the
  first end with F7 and the second cut by 0x90; the work runs in the
  serve; midi_read hands on the clock and the note; MIDI's record counts
  the first message long (past MIDI_SYSEX_LIMIT) and no byte is dropped.
- rawout (R-MIDIOUT-9): MIDI out's raw bytes, on the same build. At the
  first whole second the test engine's serve hands MIDI out a System
  Exclusive message of RAW_LEN (600) bytes; for 300 blocks from then its
  block callback queues a clock every block and a note on or off every
  16th (no more than the queue holds while the stream runs). On the wire
  (fwtest's --midi-out): the 600 bytes in order, nothing inside them but
  clocks (at least one, so a clock waits for no stream), every note
  after the F7, the first carrying its status, all of them and every
  clock sent, none dropped; the stream counted whole and the serve
  finding it gone.
- store (R-STORE-10): the store's kinds for firmwares built on the base,
  on the same build, in runs chained through the flash file
  (tools/store.py writes a control record before each, which the test
  engine reads at start-up and acts on in its first serve): a 4 096-byte
  payload and a small one written and read back, then read at the next
  start-up; since BR-12 a rewrite, which needs room for both copies, is
  refused as full in today's region, nothing written and the old payload
  kept; a factory reset voids both; then, alone in the store, 5 000
  bytes written and read back and the store's largest payload
  (STORE_FW_MAX) refused as full. After every run tools/store.py's
  reader finds what the firmware does.
- powercut (R-STORE-11, R-STORE-12): BR-12's saves that survive a power
  cut. Five saves, four of them from the base's full store (16 user
  slots, the selection, the settings) beside the firmware kinds'
  payloads, started by a key tap (tests/seams/engine's steps 0x80 and
  up): since clean-store-region in regions of the test engine's own,
  after its small image (tests/seams/engine/store5.ld and store16.ld,
  from 0x20000), a 4 096-byte payload rewritten in 5 sectors, and in 16
  one of eleven 4 096-byte payloads rewritten, after 27 rewrites that
  leave the ring so full the save must move the head on twice for one
  part's room (the case checks the model's save did, and that the
  firmware's flash commands are the model's, one for one); on today's
  region a 3 400-byte payload rewritten where the ring must copy the old
  write's parts forward during the rewrite (the case checks it did), a
  one-part payload rewritten (300 bytes) and a user slot's patch, these
  two with the head full, so that each takes a new sector and compacts.
  A run with --flash-log gives the save's flash commands, every one in
  the build's region (by its ELF's sb_store_base and sb_store_size);
  then for each command a power cut (fwtest's --power-cut) just after it
  starts, halfway and just before it ends, and one between commands and
  after the last; and from each cut's flash the firmware starts again
  (no tap, so it only reads): it finds the old payload or the new one,
  whole (length and sum), never another; the old until a moment, then
  the new; the other payloads unchanged; tools/store.py reads the same.
  Flash images are kept as their SHA-256.
- region (R-STORE-12): each firmware chooses its own store region
  (clean-store-region). The test engine on the platform with its own
  regions (store5.ld, store16.ld: 5 and 16 sectors from 0x20000, after
  its small image) builds, both links' check lines naming the region and
  the image's end, the ELFs' sb_store_base and sb_store_size the
  script's; the default build's region is today's. Then a script of
  each of these, in a folder of its own given with --src, is refused,
  with what is wrong and where it would fit: a region over the image
  (from 0x6000), one across the app area's end (0x90000, 16 sectors),
  one in the stock user patch region (0xFA000, 5 sectors: the wide
  region test build's until now), one off a sector boundary (0x20800)
  and one of 2 sectors. tools/store-region.pl's every refusal is
  unit-tested (tests/test_store_region.py).
- nostart (R-ENG-2): starting without the base's bring-up screens
  (BR-16). The test engine built with SB_ENGINE_EXTERNAL alone and with
  SB_NO_START_SCREENS as well, each run for 800 ms. Its first serve
  records what main left: by default the test screen (the second whole
  frame) at 500 ms; with the option black (SB_SCREEN_BLANK) after one
  whole frame, at least NOSTART_SOONER ms sooner (lcd_init's own waits
  stay), and there it draws its own frame, a square. At the end the
  panel is that square on black, nothing else (so the one frame before
  it was black: neither the pattern nor the test screen reached the
  panel), and the beacon shows the engine's screen, no test screen
  drawn (render time 0) and no heartbeat shown. The option without
  SB_ENGINE_EXTERNAL (the base's instrument) is refused.
- parts (SR-15, R-STORE-13): the test engine with its store region at
  0x80000, 16 sectors, as RevoiceDX keeps its saves, built with
  SB_TEST_STORE_PART, whose start-up takes the flash part's ID from the
  flash file (store.c): with each part's ID, 0x856014 and 0xB36014, its
  4 096-byte payload is written and read at the next start-up, as
  tools/store.py reads it at 0x80000; with an unknown ID (the P25Q80H's
  with its manufacturer byte zero) it is refused,
  nothing written.
- probe (BR-17, Phase B): the entry-return probe, build A with
  SB_PROBE_RETURN (firmware/src/crt0.S): the image's first instruction
  returns to whoever called the entry, before any register or RAM is
  written. Its raw image and package link start with the same 2 bytes,
  and those bytes and the rest are build A's shifted by 2; in fwtest,
  where core 0 starts with every register but r0 at zero (HW-1), it
  faults at once with the pc outside every memory that holds code, from
  the raw image and from its emulator package, where build A runs on;
  and its hardware package passes fwsc.py's unit checks.
- light (BR-17, Phase B): the light probe, build A with SB_PROBE_LIGHT
  (firmware/src/crt0.S): the backlight and PLAY's LED on, a hold, both
  off, then a return. Its raw image and package link start with the
  same probe, then build A's code; in fwtest, from the raw image and
  from its emulator package, the LED at row 2, column 10 (LED 12) is lit
  the whole of every sample until the return and no other LED ever is,
  the run faults with the pc outside the code (the return) after the
  hold, and no port access is unmodelled; its hardware package passes
  fwsc.py's unit checks; and a build with SB_PROBE_RETURN as well is
  refused.
- panel (BR-17, Phase B): the panel probe, build A with SB_PROBE_PANEL
  (firmware/src/crt0.S, probe.c): the panel brought up as HW-115 gives
  it, four bars and a square drawn, the backlight on, a hold, then a
  return. In fwtest, from the raw image and from its emulator package,
  the screen at 3 s and at the end is that picture, every pixel; the run
  faults with the pc outside the code (the return) after the waits;
  no port or SPI1 access is unmodelled; its hardware package passes
  fwsc.py's unit checks; and a build with SB_PROBE_LIGHT as well is
  refused.
- hw3 (BR-17, start3): the hardware build with SB_TEST_HW_WINDOW, which
  takes HW-128's quad mode word where fwtest's window CON reads 0, so the
  round trip and the store run: the round trip reads 856014 and comes
  back; the store's start-up counter is 1, then 2 at the next start from
  the first's flash; the matrix grid shows column 10, PA6, while PLAY is
  held; ADC channel 4 follows the pot; core 1's counter rises; only the
  window's registers are unmodelled. The shipping build tries neither.
- hw (BR-17, Phase B): the FM-1 hardware build, SB_HW_FM1 (R-HW-1). In
  fwtest, where its one timer, TIMER0, counts 24 MHz rather than the
  chip's 60 MHz (HW-119), so its beats are 2.5 times slow: the screen goes
  black, then bands 1, 2 and 3 appear in that order on black, then the
  address pattern with band 4 over it; at the end the test screen, no halt, the beats as
  2.5 times slow predicts; PLAY (fwtest's key 12) pressed and released is
  named on the screen, and its LED is lit for its column's twelfth while
  it is held and dark after; nothing unmodelled. Built with
  SB_TEST_FAULT as well (main's stack overrun) it halts on the stack's
  guard with the screen solid red. Built with SB_TEST_SPI_NO_IRQ (SPI1's
  interrupt left off) the first frame's chain stalls and lcd_wait's
  timeout draws band 5 under bands 1 to 3. Its hardware
  package passes fwsc.py's unit checks; with SB_ENGINE_EXTERNAL or a
  probe it is refused.

Prints what each case saw, and exits 1 if any failed.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_analysis as aa  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(argv, log, check=True):
    """Runs argv from the repository root, its output into log; returns
    (exit code, output)."""
    p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    with open(log, "a", encoding="utf-8") as f:
        f.write("$ %s\n%s\n" % (" ".join(argv), out))
    if check and p.returncode:
        raise RuntimeError("%s failed (%d); see %s" % (argv[0], p.returncode, log))
    return p.returncode, out


def build(out, log, *opts, check=True):
    return sh(["sh", "tools/build.sh", "build", "--out", out] + list(opts), log, check)


def fw_suite():
    spec = importlib.util.spec_from_file_location("fw_suite", os.path.join(ROOT, "tools", "fw-suite.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fwtest(image, out, log, *opts):
    """Runs fwtest on image (a path inside the repository); returns
    result.json."""
    shutil.rmtree(out, ignore_errors=True)
    sh(["sh", "tools/fwtest", "run", os.path.relpath(image, ROOT), "--out", os.path.relpath(out, ROOT)]
       + list(opts), log, check=False)
    with open(os.path.join(out, "result.json")) as f:
        return json.load(f)


def ram(out, addr, length, when="end"):
    with open(os.path.join(out, "ram-%08x-%x-%s.bin" % (addr, length, when)), "rb") as f:
        return f.read()


def words(data, fields):
    return dict(zip(fields, struct.unpack("<%dI" % len(fields), data[:4 * len(fields)])))


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- ownbase --------------------------------------------------------------

FLOAT = "tests/seams/float"


def case_ownbase(a, work, log):
    problems = []
    rc, out = build(os.path.join(work, "build"), log, "--define", "SB_TEST_OWNBASE", check=False)
    if rc == 0:
        problems.append("the SB_TEST_OWNBASE build was not refused")
    if not re.search(r"^probe\.o: sb_test_ownbase\+0x[0-9a-f]+ \(\.text[^)]*\): \[\+\+r1=4\] = r1$", out, re.M):
        problems.append("the refusal does not name probe.o, sb_test_ownbase and its store")
    if "FAIL: a store writes back into the register it stores" not in out:
        problems.append("no FAIL line")
    # The demo's hardware-float exception holds for the demo only.
    rc2, _ = build(os.path.join(work, "build2"), log, "--define", "SB_TEST_OWNBASE",
                   "--define", "PLAITS_HWFLOAT", check=False)
    if rc2 == 0:
        problems.append("the firmware built with SB_TEST_OWNBASE and PLAITS_HWFLOAT was not refused")
    if not os.path.exists(os.path.join(a.build, "app.elf")):
        problems.append("build A has no app.elf")
    # BR-13: a float-heavy object, read as compiled.
    cpu = "-mcpu=r3 -mattr=+fprev1"
    rc3, out3 = build(os.path.join(work, "float"), log, "--src", FLOAT, check=False)
    if rc3:
        problems.append("the float-heavy object was refused")
    counts = dict((m.group(2), int(m.group(1)))
                  for m in re.finditer(r"^ownbase check: (\d+) objects disassembled with (.+)$", out3, re.M))
    _, out_a = build(os.path.join(work, "plain"), log)
    counts_a = dict((m.group(2), int(m.group(1)))
                    for m in re.finditer(r"^ownbase check: (\d+) objects disassembled with (.+)$", out_a, re.M))
    if counts.get(cpu) != counts_a.get(cpu, 0) + 1 or counts.get("no CPU options") != counts_a.get("no CPU options"):
        problems.append("the float-heavy object was not disassembled with %s (%s; without it %s)"
                        % (cpu, counts, counts_a))
    if "unreadable" in out3:
        problems.append("code the disassembler can't read in the float-heavy build")
    rc4, out4 = build(os.path.join(work, "float-ownbase"), log, "--src", FLOAT, "--define", "SB_TEST_FLOAT_OWNBASE",
                      check=False)
    found = re.findall(r"^(\S+\.o: \S+ \(\.text[^)]*\): .*)$", out4, re.M)
    if rc4 == 0:
        problems.append("the float-heavy object with SB_TEST_FLOAT_OWNBASE was not refused")
    if len(found) != 1 or not re.match(r"src1_float_heavy\.o: sb_test_float_ownbase\+0x[0-9a-f]+ \(\.text\): "
                                       r"\[\+\+r1=4\] = r1$", found[0]):
        problems.append("the float-heavy refusal does not name its one store: %s" % found)
    print("ownbase: the test build %s; build A passed the check; the float-heavy object read as compiled (%s), "
          "its real store %s" % ("refused" if rc else "NOT refused", "passed" if not rc3 else "REFUSED",
                                 found[0] if found else "NOT found"))
    return problems


# --- outside --------------------------------------------------------------

OUTSIDE = "tests/seams/outside"
OUTSIDE_SYMBOLS = ("sb_outside_sum", "sb_outside_text", "sb_outside_asm", "sb_outside_cxx",
                   "sb_outside_probe")


def case_outside(a, work, log):
    problems = []
    b1 = os.path.join(work, "in-tree")
    _, out = build(b1, log, "--src", OUTSIDE)
    syms = fw_suite().elf_symbols(os.path.join(b1, "app.elf"))
    for s in OUTSIDE_SYMBOLS:
        if s not in syms:
            problems.append("%s is not in the ELF" % s)
    if "-c firmware/src/probe.c" not in out or "-c ../sb-src-1/probe.c" not in out:
        problems.append("the base's probe.c and the outside one were not both built")
    # The same folder from two other places on the host, one with the
    # source mounted elsewhere: the same bytes.
    sums = [read(os.path.join(b1, "SHA256SUMS"))]
    for i, (place, extra) in enumerate((("a/x", []), ("b/y/z", ["--src-mount", "/tmp/elsewhere/small-beeps-src-b"]))):
        copy = os.path.join(work, "copies", place)
        shutil.copytree(os.path.join(ROOT, OUTSIDE), copy)
        bi = os.path.join(work, "copy-%d" % i)
        build(bi, log, "--src", copy, *extra)
        sums.append(read(os.path.join(bi, "SHA256SUMS")))
    if len(set(sums)) != 1:
        problems.append("the outside folder's builds from three places differ")
    # Leaving a base file out.
    b2 = os.path.join(work, "left-out")
    _, out = build(b2, log, "--leave-out", "firmware/src/probe.c")
    if "left out: firmware/src/probe.c" not in out or "-c firmware/src/probe.c" in out:
        problems.append("--leave-out firmware/src/probe.c still built it")
    if sha256(os.path.join(b2, "app.bin")) != sha256(os.path.join(a.build, "app.bin")):
        problems.append("without probe.c the image is not build A's")
    # What is refused.
    for opts in (["--src", "."], ["--src", "firmware/src"], ["--leave-out", "firmware/src/no-such.c"],
                 ["--leave-out", "tools/build.sh"]):
        rc, _ = build(os.path.join(work, "refused"), log, *opts, check=False)
        if rc != 2:
            problems.append("%s was not refused (exit %d)" % (" ".join(opts), rc))
    print("outside: %d symbols from the folder; three places, %s; probe.c left out, %s"
          % (sum(s in syms for s in OUTSIDE_SYMBOLS), "the same bytes" if len(set(sums)) == 1 else "DIFFERENT",
             "build A's image" if sha256(os.path.join(b2, "app.bin")) == sha256(os.path.join(a.build, "app.bin"))
             else "ANOTHER image"))
    return problems


# --- flags --------------------------------------------------------------

FLAGS = "tests/seams/flags"
FLAGS_SYMBOLS = ("sb_flags_outer", "sb_flags_inner", "sb_flags_cxx", "sb_flags_asm")


def flags_opts(folder):
    return ["--src", folder,
            "--cflags", folder, "-DSB_FLAGS_OUTER=7 -O2",
            "--cflags", folder + "/inner", "-DSB_FLAGS_INNER=5 -Iinclude",
            "--cxxflags", folder, "-DSB_FLAGS_CXX=2",
            "--asflags", folder, "-DSB_FLAGS_ASM"]


def base_lines(out, under="firmware/"):
    """The compile lines of the base's own files (those under `under`), as
    set -x printed them."""
    return [l for l in out.splitlines() if l.startswith("+ clang") and " -c %s" % under in l]


def case_flags(a, work, log):
    """BR-11 (R-BUILD-5): per-folder compiler flags."""
    problems = []
    b1 = os.path.join(work, "with-flags")
    _, out = build(b1, log, *flags_opts(FLAGS))
    syms = fw_suite().elf_symbols(os.path.join(b1, "app.elf"))
    for sym in FLAGS_SYMBOLS:
        if sym not in syms:
            problems.append("%s is not in the ELF" % sym)
    lines = [l for l in out.splitlines() if l.startswith("+ clang")]
    want = {"sb_flags.c": "-DSB_FLAGS_OUTER=7 -O2 -c", "sb_flags_cxx.cc": "-DSB_FLAGS_CXX=2 -c",
            "sb_flags_asm.S": "-DSB_FLAGS_ASM -c",
            "sb_flags_inner.c": "-DSB_FLAGS_OUTER=7 -O2 -DSB_FLAGS_INNER=5 -I../sb-src-1/inner/include -c"}
    for f, w in want.items():
        got = [l for l in lines if "/%s -o" % f in l]
        if len(got) != 1 or w not in got[0]:
            problems.append("%s was not built with its folders' flags, after the base's (%s)" % (f, w))
    # The base's own files with the base's flags only: the same lines as a
    # build without the flags, which the folder's files then stop.
    base = base_lines(out)
    if not base or any("SB_FLAGS" in l or "-O2" in l for l in base):
        problems.append("a base file was built with a folder's flags")
    # (Its first file, inner/'s, stops on its include; the runtime, built
    # after the outside folders, never comes.)
    rc, out0 = build(os.path.join(work, "without"), log, "--src", FLAGS, check=False)
    if rc == 0 or not re.search(r"^\.\./sb-src-1/\S+: (fatal )?error: ", out0, re.M):
        problems.append("without the flags the folder's file built")
    if not base_lines(out0, "firmware/src/") or base_lines(out0, "firmware/src/") != base_lines(out, "firmware/src/"):
        problems.append("the base's compile lines differ with the folders' flags")
    # The same bytes from two other places on the host, one with the
    # source mounted elsewhere (deterministic).
    sums = [read(os.path.join(b1, "SHA256SUMS"))]
    for i, (place, extra) in enumerate((("a/x", []), ("b/y/z", ["--src-mount", "/tmp/elsewhere/small-beeps-src-b"]))):
        copy = os.path.join(work, "copies", place)
        shutil.copytree(os.path.join(ROOT, FLAGS), copy)
        bi = os.path.join(work, "copy-%d" % i)
        build(bi, log, *(flags_opts(copy) + extra))
        sums.append(read(os.path.join(bi, "SHA256SUMS")))
    if len(set(sums)) != 1:
        problems.append("the flags folder's builds from three places differ")
    # What is refused.
    refused = (["--src", FLAGS, "--cflags", "tests/seams/outside", "-DX"],    # not a --src folder
               ["--cflags", "firmware/src", "-DX"],
               ["--src", FLAGS, "--cflags", FLAGS, "-I/usr/include"],
               ["--src", FLAGS, "--cflags", FLAGS, "-Iinner/../.."],
               ["--src", FLAGS, "--cflags", FLAGS, "-fdebug-prefix-map=a=b"],
               ["--src", FLAGS, "--cflags", FLAGS, "-o x"],
               ["--src", FLAGS, "--cflags", FLAGS, "-Xclang -v"],
               ["--src", FLAGS, "--cflags", FLAGS, "-mllvm -fast-isel"],
               ["--src", FLAGS, "--cflags", FLAGS, "-Wp,-MD,x"],
               ["--src", FLAGS, "--cflags", FLAGS, "@file"],
               ["--src", FLAGS, "--cflags", FLAGS, "-isystem inner"],
               ["--src", FLAGS, "--cflags", FLAGS])
    for opts in refused:
        rc, _ = build(os.path.join(work, "refused"), log, *opts, check=False)
        if rc != 2:
            problems.append("%s was not refused (exit %d)" % (" ".join(opts), rc))
    # The folder's objects for the SDK's CPU and float (clean-pin-flags):
    # the SDK's own set again, and no float instructions, are taken...
    allowed = flags_opts(FLAGS) + ["--cflags", FLAGS, "-mcpu=r3 -mfprev1", "--cflags", FLAGS + "/inner", "-mno-fprev1",
                                   "--cxxflags", FLAGS, "-mfprev1", "--asflags", FLAGS, "-mcpu=r3"]
    rc, out = build(os.path.join(work, "cpu-allowed"), log, *allowed, check=False)
    if rc != 0:
        problems.append("the SDK's CPU and float set, or none, given as a folder's flags, was refused (exit %d)" % rc)
    elif "ownbase check: 1 objects disassembled with -mcpu=r3 -mattr=-fprev1" not in out:
        problems.append("inner/'s file was not built without float instructions (-mno-fprev1)")
    # ...another CPU, double precision and SIMD are refused before any of
    # the folder's files is compiled, each naming the folder as given, the
    # file, the effect and the fix.
    cpu_refused = (("--cflags", FLAGS + "/inner", "-mcpu=r4", "inner/sb_flags_inner.c",
                    "another CPU, r4 (the SDK's is r3)"),
                   ("--cxxflags", FLAGS, "-O2 -mfprev2", "sb_flags_cxx.cc", "double-precision float (fprev2)"),
                   ("--asflags", FLAGS, "-msimd", "sb_flags_asm.S", "SIMD instructions (simd)"))
    for opt, folder, fl, f, effect in cpu_refused:
        rc, out = build(os.path.join(work, "refused"), log, *(flags_opts(FLAGS) + [opt, folder, fl]), check=False)
        flag = fl.split()[-1]
        want = ("build: %s %s: %s/%s would be built for %s, which the SDK's flags exclude and fwtest doesn't run "
                "(from %s)." % (opt, folder, FLAGS, f, effect, flag),
                "Fix: take that out of %s %s." % (opt, folder))
        if rc == 0 or any(w not in out for w in want) or re.search(r"^\+ clang .*\.\./sb-src-", out, re.M):
            problems.append("%s %s %s was not refused before compiling, with what it does and the fix (exit %d)"
                            % (opt, folder, fl, rc))
    print("flags: %d symbols from the folder; each file with its folders' flags after the base's, the base's"
          " files with the base's only; without them it stops on the folder's files; three places, %s; %d refused;"
          " the SDK's CPU and float, or none, taken; another CPU, double precision and SIMD refused"
          % (sum(sym in syms for sym in FLAGS_SYMBOLS), "the same bytes" if len(set(sums)) == 1 else "DIFFERENT",
             len(refused)))
    return problems


# --- engine ---------------------------------------------------------------

ENGINE_FIELDS = ("marker", "inits", "init_ticks", "init_blocks", "blocks", "frames", "serves",
                 "serve_seconds", "presses", "serve_presses", "core1", "core1_jobs", "core1_wrong",
                 "runtime", "sysex_begun", "sysex_ended", "sysex_cut", "sysex_cut_by", "sysex_served",
                 "sysex_len", "sysex_sum", "sysex_first", "sysex_last", "realtime", "notes",
                 "raw_started", "raw_done", "out_notes", "out_clocks", "out_refused",
                 "step", "boot_large", "boot_large_sum", "boot_small", "boot_small_sum", "put_result",
                 "put2_result", "put_len", "put_sum", "boot_patch", "boot_patch_sum", "stepped",
                 "first_beats", "first_screen", "first_frames", "drawn_beats")
RUNTIME_RESULT = 1301           # tests/seams/engine/sb_test_runtime.cc
RUNTIME_SYMBOLS = ("memcpy", "memmove", "memset", "__cxa_pure_virtual", "_ZdlPv")
CORE1_START_WORD = 0x01c7fff8   # source 126's vector word, core 1's start address (HW-9)
ENGINE_MARKER = 0x31474E45   # "ENG1"
AUDIO_ADDR, AUDIO_FIELDS = 0x01c00550, ("marker", "start", "blocks", "underruns")
ENGINE_MS = 2300


ENGINE_SLOT = 0x01c00590    # firmware/platform.ld: the FM engine's record's place in the base
PLATFORM_RECORDS = {"sb_beacon": 0x01c00000, "sb_input": 0x01c00060, "sb_audio": 0x01c00550,
                    "sb_midi": 0x01c005d0, "sb_midi_out": 0x01c00734, "sb_store": 0x01c00780}
INSTRUMENT_SYMBOLS = ("fm_init", "fm_block", "fm_render", "fm_patches", "fm_core1_entry", "sb_fm",
                      "view_serve", "sb_ui", "store_boot", "store_serve", "arp_block", "sb_arp",
                      "spectrum_feed")


def case_engine(a, work, log):
    syms = fw_suite().elf_symbols(os.path.join(a.build, "app.elf"))
    pulled = [s for s in RUNTIME_SYMBOLS if s in syms]
    if pulled:
        return ["build A has the runtime's %s, which it never calls" % ", ".join(pulled)]
    b = os.path.join(work, "build")
    build(b, log, "--src", "tests/seams/engine", "--define", "SB_ENGINE_EXTERNAL")
    return run_engine(b, work, log, "engine")


def run_engine(b, work, log, name):
    """The test engine's run and checks, on the image in b."""
    problems = []
    syms = fw_suite().elf_symbols(os.path.join(b, "app.elf"))
    rec, fm = syms["sb_test_engine"], ENGINE_SLOT
    run = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), run, log, "--ms", str(ENGINE_MS),
               "--script", "tests/seams/scripts/engine.txt", "--wav",
               "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)),
               "--ram", "0x%08x:64@end" % fm, "--ram", "0x%08x:16@end" % AUDIO_ADDR,
               "--ram", "0x%08x:4@end" % CORE1_START_WORD)
    if r["run"]["outcome"] != "completed" or r["run"].get("unmodelled_accesses"):
        return ["the run: %s (%s), unmodelled %s" % (r["run"]["outcome"], r["run"].get("detail"),
                                                     r["run"].get("unmodelled_accesses"))]
    e = words(ram(run, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS)
    au = words(ram(run, AUDIO_ADDR, 16), AUDIO_FIELDS)
    want = {"marker": ENGINE_MARKER, "inits": 1, "init_ticks": 0, "init_blocks": 0,
            "serve_seconds": 2, "presses": 2, "serve_presses": 2, "core1": 1, "core1_wrong": 0,
            "runtime": RUNTIME_RESULT}
    for k, v in want.items():
        if e[k] != v:
            problems.append("%s is %d, not %d" % (k, e[k], v))
    if e["blocks"] != au["blocks"] or e["frames"] != 64 * e["blocks"]:
        problems.append("blocks %d (frames %d), the audio record's %d" % (e["blocks"], e["frames"], au["blocks"]))
    missing = [s for s in RUNTIME_SYMBOLS if s not in syms]
    if missing:
        problems.append("the runtime's %s not linked" % ", ".join(missing))
    if e["core1_jobs"] != e["blocks"]:
        problems.append("core 1 did %d jobs in %d blocks" % (e["core1_jobs"], e["blocks"]))
    word, = struct.unpack("<I", ram(run, CORE1_START_WORD, 4))
    if word != syms["sb_irq_stubs"] + 2 * 126:
        problems.append("source 126's vector word is 0x%08x, not its stub's" % word)
    if au["underruns"]:
        problems.append("%d underruns" % au["underruns"])
    # Before the loop, the two seconds, the two taps' presses and releases.
    if e["serves"] < 5:
        problems.append("serve called %d times, fewer than 5" % e["serves"])
    if any(ram(run, fm, 64)):
        problems.append("the engine's slot (the FM engine's record) is not zero: the instrument ran")
    _, left, _ = aa.read_wav(os.path.join(run, "audio.wav"))
    tail = left[-20000:]
    peak = max(abs(s) for s in tail)
    if not 1900 <= peak <= 2200:
        problems.append("the square wave's level in the audio is %d, not about 2048" % peak)
    print("%s: init once before the ticks and the audio; %d blocks of 64 frames; %d serves (seconds %d);"
          " %d presses; core 1 did %d jobs, none wrong, its vector word restored; the square wave at %d;"
          " the instrument never ran" % (
              name, e["blocks"], e["serves"], e["serve_seconds"], e["presses"], e["core1_jobs"], peak))
    return problems


# --- platform -------------------------------------------------------------

def case_platform(a, work, log):
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/engine.ld")
    syms = fw_suite().elf_symbols(os.path.join(b, "app.elf"))
    found = [s for s in INSTRUMENT_SYMBOLS if s in syms]
    if found:
        problems.append("the instrument is in the platform link: %s" % ", ".join(found))
    for s, addr in sorted(PLATFORM_RECORDS.items()):
        if syms.get(s) != addr:
            problems.append("%s at %s, not 0x%08x" % (s, hex(syms.get(s, 0)), addr))
    if syms.get("sb_test_engine") != 0x01c00870:
        problems.append("the test engine's record is not first among the engine's records")
    if not os.path.exists(os.path.join(b, "app-pkg.bin")):
        problems.append("no package link")
    with open(os.path.join(b, "app.size")) as f:
        code = int(re.search(r"^code (\d+)$", f.read(), re.M).group(1))
    print("platform: linked without the instrument (%d bytes of code), its records in place" % code)
    return problems + run_engine(b, work, log, "platform")


# --- sysex ----------------------------------------------------------------

SYSEX_DATA = 4104
SYSEX_CLOCK_AT = 1000            # the clock byte comes after this many data bytes
MIDI_ADDR = 0x01c005d0           # MIDI in's record (midi.h)
MIDI_FIELDS = ("marker", "bytes", "ring_dropped", "parsed", "messages", "realtime", "sysex",
               "sysex_bytes", "sysex_long", "sysex_cut")


def sysex_script(path):
    data = [(i * 7 + 3) & 0x7F for i in range(SYSEX_DATA)]
    wire = ["f0"]
    for i, b in enumerate(data):
        if i == SYSEX_CLOCK_AT:
            wire.append("f8")
        wire.append("%02x" % b)
    wire.append("f7")
    lines = ["# tools/seams_suite.py, case sysex (written by it)"]
    t = 600
    for k in range(0, len(wire), 60):
        lines.append("%d midi %s" % (t, " ".join(wire[k:k + 60])))
        t += 20
    lines.append("%d midi f0 01 02 03 90 3c 40" % (t + 100))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return data, t + 100


def case_sysex(a, work, log):
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/engine.ld")
    rec = fw_suite().elf_symbols(os.path.join(b, "app.elf"))["sb_test_engine"]
    script = os.path.join(work, "sysex.txt")
    data, last = sysex_script(script)
    run = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), run, log, "--ms", str(last + 400), "--script",
               os.path.relpath(script, ROOT), "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)),
               "--ram", "0x%08x:%d@end" % (MIDI_ADDR, 4 * len(MIDI_FIELDS)))
    if r["run"]["outcome"] != "completed" or r["run"].get("midi_bytes_dropped"):
        return ["the run: %s (%s), MIDI bytes dropped %s" % (r["run"]["outcome"], r["run"].get("detail"),
                                                           r["run"].get("midi_bytes_dropped"))]
    e = words(ram(run, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS)
    mi = words(ram(run, MIDI_ADDR, 4 * len(MIDI_FIELDS)), MIDI_FIELDS)
    want = {"sysex_begun": 2, "sysex_ended": 1, "sysex_cut": 1, "sysex_cut_by": 0x90, "sysex_served": 1,
            "sysex_len": SYSEX_DATA, "sysex_sum": sum(v * (i + 1) for i, v in enumerate(data)) & 0xFFFFFFFF,
            "sysex_first": data[0], "sysex_last": data[-1], "realtime": 1, "notes": 1}
    for k, v in want.items():
        if e[k] != v:
            problems.append("%s is %d, not %d" % (k, e[k], v))
    if mi["sysex_long"] != 1 or mi["ring_dropped"] or mi["sysex_bytes"] != SYSEX_DATA + 3:
        problems.append("MIDI's record: %d long, %d dropped, %d SysEx data bytes" % (
            mi["sysex_long"], mi["ring_dropped"], mi["sysex_bytes"]))
    print("sysex: %d data bytes in order through the tap (a clock byte inside handed on as a message);"
          " the work in the serve; a second message cut by 0x%02x" % (e["sysex_len"], e["sysex_cut_by"]))
    return problems


# --- rawout ---------------------------------------------------------------

RAW_LEN = 600
RAW_FIELDS = ("streams", "done", "bytes", "realtime")


def midi_bytes(run):
    with open(os.path.join(run, "midi-out.csv")) as f:
        rows = [l.strip().split(",") for l in f if l.strip()][1:]
    return [int(r[1], 16) for r in rows]


def case_rawout(a, work, log):
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/engine.ld")
    syms = fw_suite().elf_symbols(os.path.join(b, "app.elf"))
    rec, raw = syms["sb_test_engine"], syms["sb_midi_out_raw"]
    run = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), run, log, "--ms", "2300", "--midi-out",
               "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)),
               "--ram", "0x%08x:%d@end" % (raw, 4 * len(RAW_FIELDS)))
    if r["run"]["outcome"] != "completed" or r["run"].get("midi_out_bytes_dropped"):
        return ["the run: %s (%s), MIDI out bytes dropped %s" % (
            r["run"]["outcome"], r["run"].get("detail"), r["run"].get("midi_out_bytes_dropped"))]
    e = words(ram(run, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS)
    rw = words(ram(run, raw, 4 * len(RAW_FIELDS)), RAW_FIELDS)
    if not e["raw_started"] or not e["raw_done"] or e["out_refused"]:
        problems.append("the stream: started at block %d, found gone at %d, %d queued messages dropped"
                        % (e["raw_started"], e["raw_done"], e["out_refused"]))
    if (rw["streams"], rw["done"], rw["bytes"] - rw["realtime"]) != (1, 1, RAW_LEN) or not rw["realtime"]:
        problems.append("MIDI out's raw record: %s" % rw)
    wire = midi_bytes(run)
    want = [0xF0] + [(i * 5 + 1) & 0x7F for i in range(1, RAW_LEN - 1)] + [0xF7]
    if 0xF0 not in wire or 0xF7 not in wire:
        return problems + ["no F0 ... F7 on the wire"]
    s, f = wire.index(0xF0), wire.index(0xF7)
    inside = wire[s:f + 1]
    others = [x for x in inside if x != 0xF8]
    if others != want:
        problems.append("the raw bytes on the wire are not the 600 sent, in order, with only clocks inside")
    clocks_inside = len(inside) - len(others)
    if not clocks_inside:
        problems.append("no clock inside the stream")
    notes = [i for i, x in enumerate(wire) if 0x80 <= x <= 0x9F]
    if notes and notes[0] < f:
        problems.append("a note's status before the stream's end")
    after = [x for x in wire[f + 1:] if x != 0xF8]
    if not after or after[0] < 0x80:
        problems.append("the first message after the stream has no status byte")
    with open(os.path.join(run, "midi-out.txt")) as fh:
        text = fh.read()
    n_notes = len(re.findall(r"note-o(n|ff) ", text))
    n_clocks = wire.count(0xF8)
    if n_notes != e["out_notes"] or n_clocks != e["out_clocks"]:
        problems.append("on the wire %d notes and %d clocks, queued %d and %d" % (
            n_notes, n_clocks, e["out_notes"], e["out_clocks"]))
    print("rawout: %d bytes in order with %d clocks inside; then %d notes, the first with its status;"
          " %d clocks in all, none dropped" % (len(others), clocks_inside, n_notes, n_clocks))
    return problems


# --- store ----------------------------------------------------------------

CONTROL_KIND, LARGE, SMALL, HUGE = 0x8F, (0x80, 7), (0x81, 0), (0x82, 0)
NONE32 = 0xFFFFFFFF
STORE_ERR_FULL = -2 & 0xFFFFFFFF  # as the record's u32 holds it


def pattern(p, n):
    return bytes((i * (2 * p + 1) + p) & 0xFF for i in range(n))


def place_sum(b):
    return sum(x * (i + 1) for i, x in enumerate(b)) & 0xFFFFFFFF


def case_store(a, work, log):
    import store as st
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/engine.ld")
    rec = fw_suite().elf_symbols(os.path.join(b, "app.elf"))["sb_test_engine"]
    state = {"chip": None}

    def run(name, step, *opts):
        s = st.Store(state["chip"])
        s.put_fw(CONTROL_KIND, 0, 1, bytes([step]))
        flash = os.path.join(work, name + "-in.bin")
        with open(flash, "wb") as f:
            f.write(s.chip())
        out = os.path.join(work, name)
        timing = list(opts) if any(o == "--power-cut" for o in opts) else ["--ms", "1200"] + list(opts)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--flash", os.path.relpath(flash, ROOT), "--flash-out",
                   "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)), *timing)
        if r["run"]["outcome"] not in ("completed", "power-cut"):
            raise RuntimeError("%s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        with open(os.path.join(out, "flash.bin"), "rb") as f:
            chip = f.read()
        return words(ram(out, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS), chip, out

    def expect(name, e, img, large, small, **fields):
        for k, v in fields.items():
            if e[k] != v:
                problems.append("%s: %s is %d, not %d" % (name, k, e[k], v))
        for (kind, ident), want in ((LARGE, large), (SMALL, small)):
            got = img.get_fw(kind, ident)
            if (got[1] if got else None) != want:
                problems.append("%s: tools/store.py reads 0x%02x/%d as %s" % (
                    name, kind, ident, "none" if got is None else "%d bytes" % len(got[1])))

    p1, p9, p5 = pattern(1, 4096), pattern(9, 10), pattern(5, 5000)
    e, state["chip"], _ = run("1-write", 1)
    expect("1-write", e, st.Image(state["chip"]), p1, p9, step=1, boot_large=NONE32, put_result=0,
           put_len=4096, put_sum=place_sum(p1))
    e, state["chip"], _ = run("2-read", 0)
    expect("2-read", e, st.Image(state["chip"]), p1, p9, boot_large=4096, boot_large_sum=place_sum(p1),
           boot_small=10, boot_small_sum=place_sum(p9))
    # Since BR-12 a rewrite needs room for the old payload and the new
    # one: in today's region a 4 096-byte one is refused before anything
    # is written, and the old one stays (case powercut rewrites it, in
    # the test engine's own 5- and 16-sector regions).
    before = state["chip"]
    e, state["chip"], _ = run("3-rewrite-refused", 2)
    expect("3-rewrite-refused", e, st.Image(state["chip"]), p1, p9, put_result=STORE_ERR_FULL, put_len=4096,
           put_sum=place_sum(p1))
    with_control = st.Store(before)
    with_control.put_fw(CONTROL_KIND, 0, 1, bytes([2]))
    if state["chip"] != with_control.chip():
        problems.append("3-rewrite-refused: the refused rewrite wrote something")
    e, state["chip"], _ = run("4-reset", 4)
    e, state["chip"], _ = run("5-after-reset", 0)
    expect("5-after-reset", e, st.Image(state["chip"]), None, None, boot_large=NONE32, boot_small=NONE32)
    e, state["chip"], _ = run("6-largest", 5)
    expect("6-largest", e, st.Image(state["chip"]), None, None, put_result=0, put2_result=STORE_ERR_FULL,
           put_len=5000, put_sum=place_sum(p5))
    got = st.Image(state["chip"]).get_fw(*HUGE)
    if not got or got[1] != p5:
        problems.append("6-largest: tools/store.py doesn't read the 5 000 bytes back")
    print("store: 4 096 bytes written, read at start-up; a rewrite refused as full, nothing written, the old"
          " one kept; a reset voids both; 5 000 bytes alone, %d refused as full; tools/store.py agrees" % 5904)
    return problems


# --- parts ----------------------------------------------------------------

PART_PARAM = 0xE8000 + 0x10          # store.c, SB_TEST_STORE_PART
PARTS_BASE, PARTS_SECTORS = 0x80000, 16
STORE_ERR_PART = -4 & 0xFFFFFFFF


def case_parts(a, work, log):
    import store as st
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/store80000.ld",
          "--define", "SB_TEST_STORE_PART")
    rec = fw_suite().elf_symbols(os.path.join(b, "app.elf"))["sb_test_engine"]
    p1 = pattern(1, 4096)

    def run(name, chip, step, ident):
        s = st.Store(chip, sectors=PARTS_SECTORS, base=PARTS_BASE)
        s.put_fw(CONTROL_KIND, 0, 1, bytes([step]))
        c = bytearray(s.chip())
        c[PART_PARAM:PART_PARAM + 8] = struct.pack("<IBBBB", ident, 0, 0, 0xFF, 0xFF)
        flash = os.path.join(work, name + "-in.bin")
        with open(flash, "wb") as f:
            f.write(c)
        out = os.path.join(work, name)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--flash", os.path.relpath(flash, ROOT), "--flash-out",
                   "--ms", "1200", "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)))
        if r["run"]["outcome"] != "completed":
            raise RuntimeError("%s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        with open(os.path.join(out, "flash.bin"), "rb") as f:
            after = f.read()
        return words(ram(out, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS), bytes(c), after

    for ident in (0x856014, 0xB36014):
        e, _, chip = run("%06x-write" % ident, None, 1, ident)
        if e["put_result"] != 0 or e["put_len"] != 4096 or e["put_sum"] != place_sum(p1):
            problems.append("0x%06x: the write gave %d (%d bytes)" % (ident, e["put_result"], e["put_len"]))
        got = st.Image(chip, sectors=PARTS_SECTORS, base=PARTS_BASE).get_fw(*LARGE)
        if not got or got[1] != p1:
            problems.append("0x%06x: tools/store.py doesn't read the payload at 0x%X" % (ident, PARTS_BASE))
        e, _, _ = run("%06x-read" % ident, chip, 0, ident)
        if e["boot_large"] != 4096 or e["boot_large_sum"] != place_sum(p1):
            problems.append("0x%06x: the next start-up read %d bytes" % (ident, e["boot_large"]))
    unknown = 0x856014 & 0xFFFF         # the P25Q80H's ID, its manufacturer byte zero
    e, before, after = run("unknown-write", None, 1, unknown)
    if e["put_result"] != STORE_ERR_PART or before[PARTS_BASE:PARTS_BASE + PARTS_SECTORS * st.SECTOR] != \
            after[PARTS_BASE:PARTS_BASE + PARTS_SECTORS * st.SECTOR]:
        problems.append("unknown part: the write gave %d, or the region changed" % e["put_result"])
    print("parts: 4 096 bytes written at 0x%X and read at the next start-up with 0x856014 and with 0xB36014;"
          " refused with an unknown part, 0x%06x (result %d), nothing written"
          % (PARTS_BASE, unknown, STORE_ERR_PART - (1 << 32)))
    return problems


# --- powercut -------------------------------------------------------------

# Case powercut's save "several": eleven 4 096-byte payloads of the large
# kind (the large one, id 7, last), each a pattern of its own.
SEVERAL_IDS = (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 7)
SEVERAL_REWRITES = 27


def several_old(i):
    return pattern(2 if i == LARGE[1] else 30 + SEVERAL_IDS.index(i), 4096)


POWERCUT_TAP_MS = 300          # the key tap that starts the save (tests/seams/scripts/powercut.txt)
POWERCUT_AFTER_MS = 2000       # long enough for the slowest save to end
POWERCUT_BOOT_MS = 60          # the next start: the test engine reads the store in its init
POWERCUT_WORKERS = 4


def powercut_points(ops):
    """The cut times for a save's flash commands (rows of flash-ops.csv:
    start, end): in every command, just after it starts, halfway and just
    before it ends; between two commands; and once the save is done."""
    points = []
    for k, (t0, t1) in enumerate(ops):
        points += [t0 + 0.001, (t0 + t1) / 2, t1 - 0.001]
        nxt = ops[k + 1][0] if k + 1 < len(ops) else t1 + 2.0
        if nxt - t1 > 0.002:
            points.append((t1 + nxt) / 2)
    return sorted(set(round(t, 3) for t in points if t > 0))


def case_powercut(a, work, log):
    """BR-12 (R-STORE-11): every save is atomic, cut at every point."""
    import concurrent.futures
    import store as st
    problems = []
    script = os.path.join(work, "powercut.txt")
    with open(script, "w") as f:
        f.write("# tools/seams_suite.py, case powercut: the tap that starts the test engine's save.\n"
                "%d     key 12 tap 60\n" % POWERCUT_TAP_MS)
    builds = {"today": os.path.join(work, "build"), "r5": os.path.join(work, "build-r5"),
              "r16": os.path.join(work, "build-r16")}
    for which, script_ld in (("today", "engine.ld"), ("r5", "store5.ld"), ("r16", "store16.ld")):
        build(builds[which], log, "--platform", "--src", "tests/seams/engine", "--ld",
              "tests/seams/engine/" + script_ld)
    syms = dict((w, fw_suite().elf_symbols(os.path.join(b, "app.elf"))) for w, b in builds.items())
    rec = syms["today"]["sb_test_engine"]
    if any(syms[w]["sb_test_engine"] != rec for w in builds):
        problems.append("the test engine's record is not in one place in the three builds")
    regions = {"today": (None, st.SECTORS), "r5": st.TEST_REGIONS[5], "r16": st.TEST_REGIONS[16]}
    for w, (base, sectors) in regions.items():
        want = (st.BASE if base is None else base, sectors * st.SECTOR)
        if (syms[w]["sb_store_base"], syms[w]["sb_store_size"]) != want:
            problems.append("%s: the ELF's region is 0x%X+0x%X, not 0x%X+0x%X"
                            % (w, syms[w]["sb_store_base"], syms[w]["sb_store_size"], want[0], want[1]))
    n_rec = 4 * len(ENGINE_FIELDS)

    def full_store(sectors, base=None):
        s = st.Store(sectors=sectors, base=base)
        for i in range(st.SLOTS):
            s.put(st.PATCH, i, 2, pattern(20 + i, 112))
        s.put(st.SELECTION, 0, 1, bytes([5, 0, 0, 0]))
        s.put(st.SETTINGS, 0, 4, bytes(42))
        return s

    # The saves, each but "mid" from the base's full store beside the firmware
    # kinds' payloads: (name, build, the image before).
    wide = full_store(*st.TEST_REGIONS[5][::-1])
    wide.put_fw(LARGE[0], LARGE[1], 1, pattern(2, 4096))
    wide.put_fw(SMALL[0], SMALL[1], 1, pattern(9, 10))
    wide.put_fw(CONTROL_KIND, 0, 1, bytes([0x83]))
    # Eleven 4 096-byte payloads in 16 sectors (the worked example), the
    # large one among them, rewritten in turn 27 times: the ring so full
    # that the save moves the head on twice for one part's room.
    several = full_store(*st.TEST_REGIONS[16][::-1])
    several.put_fw(SMALL[0], SMALL[1], 1, pattern(9, 10))
    for r in range(len(SEVERAL_IDS) + SEVERAL_REWRITES):
        i = SEVERAL_IDS[r % len(SEVERAL_IDS)]
        several.put_fw(LARGE[0], i, 1, several_old(i))
    several.put_fw(CONTROL_KIND, 0, 1, bytes([0x83]))
    saves = []
    for name, step in (("small", 0x86), ("patch", 0x87)):
        s = full_store(st.SECTORS)
        s.put_fw(SMALL[0], SMALL[1], 1, pattern(9, 10))
        s.put_fw(LARGE[0], LARGE[1], 1, pattern(1, 1500))
        s.put_fw(CONTROL_KIND, 0, 1, bytes([step]))
        fill = 0
        # The head filled, so the save takes a new sector and compacts.
        size = st.record_size(112) if step == 0x87 else st.record_size(st.TAG + 300)
        while s.head_seq < st.SECTORS + 1 or st.SECTOR - s.append >= size:
            room = st.SECTOR - s.append
            if s.head_seq < st.SECTORS + 1 or room >= st.record_size(42) + size:
                s.put(st.SETTINGS, 0, 4, bytes([fill & 0xFF]) * 42)
                fill += 1
            else:
                s.put_fw(0x84, 0, 1, bytes(room - 24))
        saves.append((name, "today", s))
    saves.insert(0, ("large", "r5", wide))
    saves.insert(1, ("several", "r16", several))
    # A large payload in today's region whose rewrite makes the ring copy
    # the old write's parts forward while the new write is under way.
    mid = st.Store()
    mid.put_fw(SMALL[0], SMALL[1], 1, pattern(9, 10))
    for _ in range(4):
        mid.put_fw(LARGE[0], LARGE[1], 1, pattern(1, 3400))
    mid.put_fw(CONTROL_KIND, 0, 1, bytes([0x84]))
    saves.insert(2, ("mid", "today", mid))
    # What each payload is before the save and after it: (kind, id) to the
    # record's (length, sum) fields; the base's patch as STORE_PATCH.
    olds = {"large": pattern(2, 4096), "several": several_old(LARGE[1]), "mid": pattern(1, 3400),
            "small": pattern(9, 10), "patch": pattern(20 + 3, 112)}
    news = {"large": pattern(3, 4096), "several": pattern(3, 4096), "mid": pattern(4, 3400),
            "small": pattern(10, 300), "patch": pattern(12, 112)}
    fields = {"large": ("boot_large", "boot_large_sum"), "several": ("boot_large", "boot_large_sum"),
              "mid": ("boot_large", "boot_large_sum"), "small": ("boot_small", "boot_small_sum"),
              "patch": ("boot_patch", "boot_patch_sum")}
    # And the others, which each save leaves as they were (the other ten
    # large payloads of "several" read by tools/store.py).
    p23, l1500 = pattern(20 + 3, 112), pattern(1, 1500)
    unchanged = {"large": {"small": olds["small"], "patch": p23}, "several": {"small": olds["small"], "patch": p23},
                 "mid": {"small": olds["small"], "patch": None},
                 "small": {"large": l1500, "patch": p23}, "patch": {"large": l1500, "small": olds["small"]}}

    def fw_run(name, image, flash, *opts):
        out = os.path.join(work, name)
        r = fwtest(image, out, log, "--flash", os.path.relpath(flash, ROOT), "--flash-out",
                   "--ram", "0x%08x:%d@end" % (rec, n_rec), *opts)
        if r["run"]["outcome"] not in ("completed", "power-cut") or r["run"].get("unmodelled_accesses"):
            raise RuntimeError("%s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        e = words(ram(out, rec, n_rec), ENGINE_FIELDS)
        with open(os.path.join(out, "flash.bin"), "rb") as f:
            chip = f.read()
        # The image only as its SHA-256 (as the store suite keeps them).
        os.remove(os.path.join(out, "flash.bin"))
        with open(os.path.join(out, "flash.bin.sha256"), "w") as f:
            f.write(hashlib.sha256(chip).hexdigest() + "\n")
        return e, chip, out

    summary = []
    for name, which, s in saves:
        base, sectors = regions[which]
        image = os.path.join(builds[which], "app.bin")
        pre = os.path.join(work, "%s-in.bin" % name)
        with open(pre, "wb") as f:
            f.write(s.chip())
        # The save whole, its flash commands logged to aim the cuts.
        e, chip, out = fw_run("%s-aim" % name, image, pre, "--script", os.path.relpath(script, ROOT),
                              "--flash-log", "--ms", str(POWERCUT_AFTER_MS))
        if e["put_result"] != 0 or not e["stepped"]:
            problems.append("%s: the save itself failed (%d)" % (name, e["put_result"]))
            continue
        lo = st.region_base(sectors) if base is None else base
        hi = lo + sectors * st.SECTOR
        with open(os.path.join(out, "flash-ops.csv")) as f:
            rows = [l.split(",") for l in f.read().splitlines()[1:]]
        outside = [r for r in rows if not lo <= int(r[3], 16) < hi]
        if outside:
            problems.append("%s: %d flash commands outside the region, the first at %s" % (name, len(outside),
                                                                                      outside[0][3]))
        ops = [(float(r[0]), float(r[1])) for r in rows if lo <= int(r[3], 16) < hi]
        erases = sum(1 for r in rows if lo <= int(r[3], 16) < hi and r[2] != "02")
        if not erases:
            problems.append("%s: the save took no new sector" % name)
        if name == "several":
            # The model's save: the head moved on twice for one part's
            # room, and its commands the firmware's.
            m = st.Store(s.chip(), sectors, base)
            m.commands, moves, room = [], [], m._room

            def counted(size, room=room, m=m):
                n = sum(1 for c in m.commands if c[0] == "erase")
                room(size)
                moves.append(sum(1 for c in m.commands if c[0] == "erase") - n)
            m._room = counted
            m.put_fw(LARGE[0], LARGE[1], 1, pattern(3, 4096))
            if max(moves) < 2:
                problems.append("several: the model's save never moved the head on twice (%s)" % moves)
            # fwtest logs a page program at its page's start.
            fw_cmds = [("program" if r[2] == "02" else "erase", int(r[3], 16)) for r in rows]
            if fw_cmds != [(c[0], c[1] & ~(st.PAGE - 1)) for c in m.commands]:
                problems.append("several: the firmware's %d flash commands are not the model's %d"
                                % (len(fw_cmds), len(m.commands)))
        points = powercut_points(ops)
        if name == "mid":
            # The old write's parts copied forward during the rewrite (its
            # tag, sequence numbers from the save's): what this save is for.
            tag = struct.pack("<I", st.Image(s.chip()).commit_of(*LARGE)[3])
            copies = sum(1 for r in st.Image(chip).records if (r[3], r[4]) == LARGE and r[6][:st.TAG] == tag
                         and r[2] >= s.next_seq)
            if not copies:
                problems.append("mid: the rewrite copied none of the old write's parts")

        def one(i_t):
            i, t = i_t
            _, cut, _ = fw_run("%s-cut-%03d" % (name, i), image, pre, "--script", os.path.relpath(script, ROOT),
                               "--power-cut", "%.3f" % t)
            cut_in = os.path.join(work, "%s-cut-%03d-in.bin" % (name, i))
            with open(cut_in, "wb") as f:
                f.write(cut)
            b, _, _ = fw_run("%s-next-%03d" % (name, i), image, cut_in, "--ms", str(POWERCUT_BOOT_MS))
            os.remove(cut_in)
            img = st.Image(cut, sectors, base)
            return t, b, img

        seen = []
        with concurrent.futures.ThreadPoolExecutor(POWERCUT_WORKERS) as pool:
            results = list(pool.map(one, enumerate(points)))
        for t, b, img in results:
            ln, sm = fields[name]
            got = (b[ln], b[sm])
            old, new = olds[name], news[name]
            want = {(len(old), place_sum(old)): "old", (len(new), place_sum(new)): "new"}
            if got not in want:
                problems.append("%s: cut at %.3f ms, the next start finds %s" % (
                    name, t, "none" if got[0] == NONE32 else "%d bytes, another sum" % got[0]))
                continue
            seen.append(want[got])
            for k, o in unchanged[name].items():
                if (b[fields[k][0]], b[fields[k][1]]) != ((len(o), place_sum(o)) if o is not None else (NONE32, 0)):
                    problems.append("%s: cut at %.3f ms, %s changed" % (name, t, k))
            # tools/store.py's reader finds the same.
            if name == "patch":
                m = img.get(st.PATCH, 3)
            else:
                m = img.get_fw(*(SMALL if name == "small" else LARGE))
            if (m[1] if m else None) != (new if want[got] == "new" else old):
                problems.append("%s: cut at %.3f ms, tools/store.py reads otherwise" % (name, t))
            if name == "several":
                for i in SEVERAL_IDS:
                    if i != LARGE[1] and img.get_fw(LARGE[0], i) != (1, several_old(i)):
                        problems.append("several: cut at %.3f ms, payload 0x%02x/%d changed" % (t, LARGE[0], i))
        if seen != sorted(seen, key=lambda k: k == "new") or (seen and seen[-1] != "new"):
            problems.append("%s: not the old payload until a moment and then the new" % name)
        first_new = next((i for i, k in enumerate(seen) if k == "new"), len(seen))
        summary.append("%s: %d commands (%d erases%s), %d cuts, old %d, new %d"
                       % (name, len(ops), erases, ", %d old parts copied" % copies if name == "mid" else "",
                          len(points), first_new, len(seen) - first_new))
    print("powercut: %s; never neither, never a mix; tools/store.py agrees" % "; ".join(summary))
    return problems


# --- region ---------------------------------------------------------------

REGION_REFUSALS = (
    ("over-image", 0x6000, 0x5000, "overlaps the image, which ends at chip offset"),
    ("across-end", 0x90000, 0x10000, "crosses the end of the app area at 0x94000"),
    ("user-patch", 0xFA000, 0x5000, "overlaps the stock firmware's user patch region"),
    ("unaligned", 0x20800, 0x5000, "STORE_BASE 0x20800 is not on a 4 KiB sector boundary"),
    ("too-small", 0x20000, 0x2000, "STORE_SIZE 0x2000 is 2 sectors; the store needs 3 at least"),
)


def case_region(a, work, log):
    import store as st
    problems = []
    opts = ["--platform", "--src", "tests/seams/engine"]
    for name, script_ld, (base, sectors) in (("default", "engine.ld", (st.BASE, st.SECTORS)),
                                              ("r5", "store5.ld", st.TEST_REGIONS[5]),
                                              ("r16", "store16.ld", st.TEST_REGIONS[16])):
        b = os.path.join(work, name)
        _, out = build(b, log, *opts + ["--ld", "tests/seams/engine/" + script_ld])
        for elf in ("app.elf", "app-pkg.elf"):
            m = re.search(r"^%s: store region 0x([0-9A-F]+) to 0x([0-9A-F]+), (\d+) sectors \(the image ends at "
                          r"0x([0-9A-F]+)\)$" % re.escape(elf), out, re.M)
            if not m or (int(m.group(1), 16), int(m.group(3))) != (base, sectors):
                problems.append("%s: %s's check line is not the region's" % (name, elf))
            elif int(m.group(4), 16) >= base:
                problems.append("%s: the image ends after the region begins" % name)
            sy = fw_suite().elf_symbols(os.path.join(b, elf))
            if (sy["sb_store_base"], sy["sb_store_size"]) != (base, sectors * st.SECTOR):
                problems.append("%s: %s's sb_store_base and sb_store_size are not the script's" % (name, elf))
    refused = []
    for name, base, size, want in REGION_REFUSALS:
        d = os.path.join(work, "ld-" + name)
        os.makedirs(d)
        with open(os.path.join(d, "region.ld"), "w") as f:
            f.write("/* tools/seams_suite.py, case region: a region the build must refuse. */\n"
                    "STORE_BASE = 0x%X;\nSTORE_SIZE = 0x%X;\n\nINCLUDE platform.ld\n" % (base, size))
        rc, out = build(os.path.join(work, name), log, *opts + ["--src", d, "--ld", os.path.join(d, "region.ld")],
                        check=False)
        if rc == 0:
            problems.append("%s: a region at 0x%X, 0x%X bytes, was not refused" % (name, base, size))
            continue
        if "FAIL: the store's region doesn't fit" not in out or not re.search(
                r"^app\.elf: store region: .*%s" % re.escape(want), out, re.M):
            problems.append("%s: refused without saying \"%s\"" % (name, want))
        if not re.search(r"^app\.elf: store region: where it would fit: .*from 0x[0-9A-F]+ to 0x[0-9A-F]+ at the latest",
                         out, re.M):
            problems.append("%s: no place where it would fit" % name)
        refused.append(name)
    print("region: the test engine built in today's region and in 5 and 16 sectors from 0x20000; refused, each saying"
          " why and where it would fit: %s" % ", ".join(refused))
    return problems


# --- nostart --------------------------------------------------------------

NOSTART_MS = 800
NOSTART_SOONER = 300            # ms; measured 373 (DESIGN-NOTES, clean-br16)
SCREEN_TEST, SCREEN_PANEL, SCREEN_BLANK = 2, 3, 4   # firmware/src/sb.h, SB_SCREEN_*
BEACON_ADDR = 0x01c00000
DRAWN = (100, 100, 40)          # tests/seams/engine/sb_test_engine.c: DRAWN_X, DRAWN_Y, DRAWN_SIZE


def case_nostart(a, work, log):
    problems, first = [], {}
    fws = fw_suite()
    for name, opts in (("default", ()), ("nostart", ("--define", "SB_NO_START_SCREENS"))):
        b = os.path.join(work, name)
        build(b, log, "--src", "tests/seams/engine", "--define", "SB_ENGINE_EXTERNAL", *opts)
        rec = fws.elf_symbols(os.path.join(b, "app.elf"))["sb_test_engine"]
        run = os.path.join(work, name + "-run")
        r = fwtest(os.path.join(b, "app.bin"), run, log, "--ms", str(NOSTART_MS),
                   "--ram", "0x%08x:%d@end" % (rec, 4 * len(ENGINE_FIELDS)),
                   "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN), "--lcd", "end")
        if r["run"]["outcome"] != "completed":
            return ["%s: the run %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail"))]
        e = words(ram(run, rec, 4 * len(ENGINE_FIELDS)), ENGINE_FIELDS)
        bc = fws.beacon(ram(run, BEACON_ADDR, fws.BEACON_LEN))
        _, _, rows = fws.read_png(os.path.join(run, "lcd-end.png"))
        first[name] = e
        if name == "default":
            want = {"first_screen": SCREEN_TEST, "first_frames": 2, "drawn_beats": 0}
            if e["first_beats"] < 499:
                problems.append("default: the first serve at %d ms, before the test screen's 500" % e["first_beats"])
        else:
            want = {"first_screen": SCREEN_BLANK, "first_frames": 1}
            if not e["first_beats"] <= e["drawn_beats"] <= e["first_beats"] + 2:
                problems.append("nostart: its frame sent at %d ms, the first serve at %d" % (
                    e["drawn_beats"], e["first_beats"]))
            for k, v in (("screen", SCREEN_PANEL), ("render_ticks", 0), ("shown", 0)):
                if bc[k] != v:
                    problems.append("nostart: the beacon's %s is %d, not %d" % (k, bc[k], v))
            x0, y0, n = DRAWN
            square = fws.rgb8(0, 63, 31)
            wrong = [(x, y) for y, row in enumerate(rows) for x, p in enumerate(row)
                     if p != (square if x0 <= x < x0 + n and y0 <= y < y0 + n else (0, 0, 0))]
            if wrong:
                problems.append("nostart: %d pixels at the end are not the square on black, the first at %s"
                                % (len(wrong), wrong[0]))
        for k, v in want.items():
            if e[k] != v:
                problems.append("%s: %s is %d, not %d" % (name, k, e[k], v))
    sooner = first["default"]["first_beats"] - first["nostart"]["first_beats"]
    if sooner < NOSTART_SOONER:
        problems.append("the first serve only %d ms sooner with SB_NO_START_SCREENS" % sooner)
    code, out = build(os.path.join(work, "alone"), log, "--define", "SB_NO_START_SCREENS", check=False)
    if not code or "SB_NO_START_SCREENS is for an engine built on the base" not in out:
        problems.append("SB_NO_START_SCREENS without SB_ENGINE_EXTERNAL not refused (exit %d)" % code)
    d, n = first["default"], first["nostart"]
    print("nostart: the first serve at %d ms by default (screen %d, %d frames), at %d ms with"
          " SB_NO_START_SCREENS (screen %d, %d frame), %d ms sooner; the option without an external"
          " engine refused" % (d["first_beats"], d["first_screen"], d["first_frames"], n["first_beats"],
                               n["first_screen"], n["first_frames"], sooner))
    return problems


# --- probe ----------------------------------------------------------------

def case_probe(a, work, log):
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_PROBE_RETURN")
    raw, pkg = read_bytes(os.path.join(b, "app.bin")), read_bytes(os.path.join(b, "app-pkg.bin"))
    base = read_bytes(os.path.join(a.build, "app.bin"))
    if raw[:2] != pkg[:2] or raw[2:2 + 64] != base[:64]:
        problems.append("the probe's first instruction is not 2 bytes before build A's code")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    emu = os.path.join(work, "probe.fwsc")
    with open(emu, "wb") as f:
        f.write(fwsc.pack(pkg, "small-beeps-0.0.0"))
    for name, image, opts in (("raw", os.path.join(b, "app.bin"), ()), ("package", emu, ("--package",)),
                              ("build A", os.path.join(a.build, "app.bin"), ())):
        r = fwtest(image, os.path.join(work, "run-" + name.replace(" ", "")), log, "--ms", "5", "--halt-ok", *opts)
        outcome, detail = r["run"]["outcome"], r["run"].get("detail") or ""
        if name == "build A":
            if outcome != "completed":
                problems.append("build A: %s (%s)" % (outcome, detail))
        elif outcome != "fault" or "left every memory that can hold code" not in detail \
                or float(r["run"]["emulated_ms"]) > 0.1:
            problems.append("%s: %s at %s ms (%s), not a fault at once outside the code" % (
                name, outcome, r["run"]["emulated_ms"], detail))
    try:
        fwsc.unit_check(fwsc.pack_hardware(pkg, "0.0.0", 0x980F, 0xFC000), 0x980F)
    except ValueError as e:
        problems.append("its hardware package: %s" % e)
    print("probe: the first instruction returns: from the raw image and the package fwtest faults at once outside "
          "the code (build A runs on); its hardware package passes the unit's checks")
    return problems


LIGHT_LED = 12                  # fwtest's LED at row 2 (PA10), column 10 (0xFBFF; HW-35, HW-42)
LIGHT_HOLD_MS = 900000000 * 2 / 240000.0   # SB_PROBE_HOLD's two-instruction passes at fwtest's clock


def case_light(a, work, log):
    problems = []
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_PROBE_LIGHT")
    raw, pkg = read_bytes(os.path.join(b, "app.bin")), read_bytes(os.path.join(b, "app-pkg.bin"))
    base = read_bytes(os.path.join(a.build, "app.bin"))
    n = raw.find(base[:64])
    if not 0 < n < 0x200 or pkg[:n] != raw[:n]:
        problems.append("the probe is not before build A's code in both links (build A's start at %d)" % n)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    emu = os.path.join(work, "light.fwsc")
    with open(emu, "wb") as f:
        f.write(fwsc.pack(pkg, "small-beeps-0.0.0"))
    for name, image, opts in (("raw", os.path.join(b, "app.bin"), ()), ("package", emu, ("--package",))):
        out = os.path.join(work, "run-" + name)
        r = fwtest(image, out, log, "--ms", "8000", "--halt-ok", "--leds-every", "500", *opts)
        outcome, detail, ms = r["run"]["outcome"], r["run"].get("detail") or "", float(r["run"]["emulated_ms"])
        if outcome != "fault" or "left every memory that can hold code" not in detail \
                or abs(ms - LIGHT_HOLD_MS) > 1:
            problems.append("%s: %s at %s ms (%s), not the return after the %.0f ms hold" % (
                name, outcome, ms, detail, LIGHT_HOLD_MS))
        ports = [u["address"] for u in r["run"]["unmodelled_accesses"] if 0x50000 <= int(u["address"], 16) < 0x50200]
        if ports:
            problems.append("%s: port accesses unmodelled: %s" % (name, ", ".join(ports)))
        with open(os.path.join(out, "leds.csv")) as f:
            rows = list(csv.reader(f))[1:]
        held = [row for row in rows if float(row[0]) <= LIGHT_HOLD_MS - 1]
        if len(held) < 14:
            problems.append("%s: %d LED samples in the hold" % (name, len(held)))
        for row in rows:
            lit = {i: int(v) for i, v in enumerate(row[1:]) if int(v)}
            want = {LIGHT_LED: 1000} if row in held else {}
            if (lit if row in held else {k: v for k, v in lit.items() if k != LIGHT_LED}) != want:
                problems.append("%s: at %s ms the LEDs lit are %s, not %s" % (name, row[0], lit, want or "LED %d alone" % LIGHT_LED))
                break
    try:
        fwsc.unit_check(fwsc.pack_hardware(pkg, "0.0.0", 0x980F, 0xFC000), 0x980F)
    except ValueError as e:
        problems.append("its hardware package: %s" % e)
    code, out = build(os.path.join(work, "both"), log, "--define", "SB_PROBE_LIGHT", "--define", "SB_PROBE_RETURN",
                      check=False)
    if not code or "are three probes: define one" not in out:
        problems.append("SB_PROBE_LIGHT with SB_PROBE_RETURN not refused (exit %d)" % code)
    print("light: LED %d lit for the %.0f ms hold and no other, then the return, from the raw image and the package; "
          "no port access unmodelled; its hardware package passes the unit's checks; both probes at once refused"
          % (LIGHT_LED, LIGHT_HOLD_MS))
    return problems


PANEL_WAIT_MS = (150 + 120 + 5000) * 360 / 240.0   # pp_wait_ms's waits, counted for 360 MHz, at fwtest's 240
PANEL_SEND_MS = 100                                 # at most, for the bytes sent besides


def panel_picture(fws):
    """The panel probe's picture: bars red, green, blue and white from the
    left, 60 pixels each, and a yellow 40 x 40 square at (0, 0)."""
    bars = [fws.rgb8(31, 0, 0), fws.rgb8(0, 63, 0), fws.rgb8(0, 0, 31), fws.rgb8(31, 63, 31)]
    yellow = fws.rgb8(31, 63, 0)
    return [[yellow if x < 40 and y < 40 else bars[x // 60] for x in range(240)] for y in range(240)]


def case_panel(a, work, log):
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_PROBE_PANEL")
    pkg = read_bytes(os.path.join(b, "app-pkg.bin"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    emu = os.path.join(work, "panel.fwsc")
    with open(emu, "wb") as f:
        f.write(fwsc.pack(pkg, "small-beeps-0.0.0"))
    want = panel_picture(fws)
    for name, image, opts in (("raw", os.path.join(b, "app.bin"), ()), ("package", emu, ("--package",))):
        out = os.path.join(work, "run-" + name)
        r = fwtest(image, out, log, "--ms", "9000", "--halt-ok", "--lcd", "3000", "--lcd", "end", *opts)
        outcome, detail, ms = r["run"]["outcome"], r["run"].get("detail") or "", float(r["run"]["emulated_ms"])
        if outcome != "fault" or "left every memory that can hold code" not in detail \
                or not PANEL_WAIT_MS <= ms <= PANEL_WAIT_MS + PANEL_SEND_MS:
            problems.append("%s: %s at %s ms (%s), not the return after the %.0f ms of waits" % (
                name, outcome, ms, detail, PANEL_WAIT_MS))
        # Ports A to H up to JL_IOMAP->CON1 (HW-56), and SPI1's block (HW-28).
        regs = [u["address"] for u in r["run"]["unmodelled_accesses"]
                if 0x50000 <= int(u["address"], 16) <= 0x51020 or 0x11D00 <= int(u["address"], 16) < 0x11D00 + 0x100]
        if regs:
            problems.append("%s: port or SPI1 accesses unmodelled: %s" % (name, ", ".join(regs)))
        for when in ("3000ms", "end"):
            png = os.path.join(out, "lcd-%s.png" % when)
            if not os.path.exists(png):
                problems.append("%s: no screen at %s" % (name, when))
                continue
            _, _, rows = fws.read_png(png)
            wrong = [(x, y) for y in range(240) for x in range(240) if rows[y][x] != want[y][x]]
            if wrong:
                problems.append("%s: at %s %d pixels are not the probe's picture, the first at %s"
                                % (name, when, len(wrong), wrong[0]))
    try:
        fwsc.unit_check(fwsc.pack_hardware(pkg, "0.0.0", 0x980F, 0xFC000), 0x980F)
    except ValueError as e:
        problems.append("its hardware package: %s" % e)
    code, out = build(os.path.join(work, "both"), log, "--define", "SB_PROBE_PANEL", "--define", "SB_PROBE_LIGHT",
                      check=False)
    if not code or "are three probes: define one" not in out:
        problems.append("SB_PROBE_PANEL with SB_PROBE_LIGHT not refused (exit %d)" % code)
    print("panel: the bars and the square on the screen at 3 s and at the end, then the return after the %.0f ms of"
          " waits, from the raw image and the package; no port or SPI1 access unmodelled; its hardware package passes"
          " the unit's checks; two probes at once refused" % PANEL_WAIT_MS)
    return problems


HW_WINDOW_READS = {"0x00040200", "0x0004020c", "0x00040304"}   # HW-128: CON, the base, the key
# The round trip's registers (HW-128): those, the window's cipher and the
# peripheral cipher. fwtest models none of them; 0x01F0xxxx is RAM there.
HW_WINDOW_REGS = HW_WINDOW_READS | {"0x00040300", "0x00013000"}
HW_RATIO = 60 / 24.0                # the chip's TIMER0 clock over fwtest's (HW-119, HW-48)
HW_LED = 12                         # fwtest's LED of PLAY (HW-35, HW-42)
HW_BANDS = ((0, 0, 255), (0, 255, 0), (255, 255, 255))


def hw_state(rows):
    """How many of the start-up's bands are on an otherwise black screen,
    or None if the screen is something else."""
    n = 0
    for k, colour in enumerate(HW_BANDS, 1):
        p = rows[40 + 24 * k + 8][120]
        if p == colour and n == k - 1:
            n = k
        elif p != (0, 0, 0):
            return None
    if any(rows[y][x] != (0, 0, 0) for x, y in ((0, 0), (120, 20), (239, 239), (5, 200))):
        return None
    return n


def case_hw(a, work, log):
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1")
    script = os.path.join(b, "press.script")
    with open(script, "w") as f:
        f.write("3000 key %d down\n3800 key %d up\n" % (HW_LED, HW_LED))
    out = os.path.join(work, "run")
    early = []
    for t in range(400, 431):
        early += ["--lcd", str(t)]
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "5000", "--script", script, "--leds-every", "500",
               "--lcd", "1000", "--lcd", "3500", "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN), *early)
    if r["run"]["outcome"] != "completed":
        problems.append("hw: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    # Since start3 the build reads the window's registers before its round
    # trip (HW-128), which fwtest doesn't model: those, and nothing else.
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_READS)
    if odd:
        problems.append("hw: unmodelled accesses: %s" % odd[:8])
    seen = []
    for t in range(400, 431):
        _, _, rows = fws.read_png(os.path.join(out, "lcd-%dms.png" % t))
        st = hw_state(rows)
        if not seen or seen[-1] != st:
            seen.append(st)
    want = [0, 1, 2, 3, None]
    if seen != want:
        problems.append("hw: the start-up's screens in order were %s, not black, bands 1, 2, 3, then the pattern" % seen)
    _, _, pat = fws.read_png(os.path.join(out, "lcd-1000ms.png"))
    # Band 4 is rows 136 to 151; since start3b the store's row (142 to 149)
    # is drawn again over the pattern, so its last rows are looked at.
    if pat[40 + 24 * 4 + 14][120] != (255, 255, 0) or pat[8][8] != fws.rgb8(1, 2, 0):
        problems.append("hw: at 1 s not the address pattern with band 4 (yellow) over it")
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    lo, hi = (5000 - 430) / HW_RATIO - 2, (5000 - 400) / HW_RATIO + 2
    if bc["screen"] != 2 or bc["halt_reason"] or not lo <= bc["beats"] <= hi:
        problems.append("hw: at the end screen %d, halt %d, beats %d (not the test screen, no halt, %.0f to %.0f beats)"
                        % (bc["screen"], bc["halt_reason"], bc["beats"], lo, hi))
    _, _, held = fws.read_png(os.path.join(out, "lcd-3500ms.png"))
    _, _, end = fws.read_png(os.path.join(out, "lcd-end.png"))
    if held[8][8] != (255, 0, 0) or end[8][8] != (255, 0, 0):
        problems.append("hw: no test screen (its red corner) at 3.5 s and at the end")
    box = [(x, y) for y in range(104, 120) for x in range(26, 214)]
    if not any(held[y][x] == (255, 255, 255) for x, y in box) or all(held[y][x] == end[y][x] for x, y in box):
        problems.append("hw: PLAY's press and release are not both named on the screen")
    with open(os.path.join(out, "leds.csv")) as f:
        leds = {int(float(row[0])): [int(v) for v in row[1:]] for row in list(csv.reader(f))[1:]}
    press, after = leds.get(3500), leds.get(4500)
    if not press or not after or not 70 <= press[HW_LED] <= 95 or any(v for i, v in enumerate(press) if i != HW_LED) \
            or any(after):
        problems.append("hw: LEDs while PLAY is held %s, after %s (LED %d at about 1000 / 12 alone, then none)"
                        % (press, after, HW_LED))
    fb = os.path.join(work, "fault")
    build(fb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_FAULT")
    fout = os.path.join(work, "run-fault")
    r = fwtest(os.path.join(fb, "app.bin"), fout, log, "--ms", "3000", "--halt-ok", "--lcd", "end",
               "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN))
    _, _, rows = fws.read_png(os.path.join(fout, "lcd-end.png"))
    bc = fws.beacon(ram(fout, BEACON_ADDR, fws.BEACON_LEN))
    # SB_TEST_FAULT overruns main's stack: the tick's guard check halts (SB_HALT_STACK).
    if r["run"]["outcome"] != "halt" or bc["halt_reason"] != 3 or any(p != (255, 0, 0) for row in rows for p in row):
        problems.append("hw with SB_TEST_FAULT: %s, halt reason %d, the screen not all red" % (r["run"]["outcome"], bc["halt_reason"]))
    nb = os.path.join(work, "no-irq")
    build(nb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_SPI_NO_IRQ")
    nout = os.path.join(work, "run-no-irq")
    r = fwtest(os.path.join(nb, "app.bin"), nout, log, "--ms", "3000", "--lcd", "end")
    _, _, rows = fws.read_png(os.path.join(nout, "lcd-end.png"))
    got = [rows[40 + 24 * k + 8][120] for k in (1, 2, 3, 4, 5)]
    if r["run"]["outcome"] != "completed" or got != list(HW_BANDS) + [(0, 0, 0), (255, 0, 255)]:
        problems.append("hw with SB_TEST_SPI_NO_IRQ: %s, bands %s (not 1 to 3, then 5 for a chain whose interrupt"
                        " never came)" % (r["run"]["outcome"], got))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    try:
        fwsc.unit_check(fwsc.pack_hardware(read_bytes(os.path.join(b, "app-pkg.bin")), "0.0.0", 0x980F, 0xFC000), 0x980F)
    except ValueError as e:
        problems.append("its hardware package: %s" % e)
    for other, words in (("SB_ENGINE_EXTERNAL", "is the base's own start-up on a unit"),
                         ("SB_PROBE_PANEL", "is not a probe")):
        code, text = build(os.path.join(work, "with-" + other.lower()), log, "--define", "SB_HW_FM1", "--define", other,
                           check=False)
        if not code or words not in text:
            problems.append("SB_HW_FM1 with %s not refused (exit %d)" % (other, code))
    print("hw: bands 1 to 3 in order, the pattern, then the test screen with beats %.1f times slow; PLAY named and its"
          " LED lit while held; a fault halts on red; its hardware package passes the unit's checks; with an external"
          " engine or a probe refused" % HW_RATIO)
    return problems


HW3_FIELDS = ("win_con", "win_base", "win_key", "tried", "back", "idle_timeouts", "id", "status1", "status2",
              "stored", "count", "get_result", "put_result")    # hw_fm1.h, struct hw_start3
HW3_LEN = 4 * len(HW3_FIELDS) + 16 + 4 * 12
HW3_STEP_Y = 216    # hw_fm1.h


def hw3_record(data):
    w = dict(zip(HW3_FIELDS, struct.unpack_from("<13i", data)))
    w["grid"] = list(data[52:68])
    w["adc"] = list(struct.unpack_from("<12I", data, 68))
    return w


def case_hw3(a, work, log):
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h3, c1 = sy["hw3"], sy["hw_core1_count"]
    script = os.path.join(b, "press.script")
    with open(script, "w") as f:
        f.write("3000 key %d down\n3800 key %d up\n4600 pot 300\n" % (HW_LED, HW_LED))

    def run(name, ms, *opts):
        out = os.path.join(work, name)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", str(ms), "--flash-out",
                   "--ram", "0x%08x:%d@3500" % (h3, HW3_LEN), "--ram", "0x%08x:%d@end" % (h3, HW3_LEN),
                   "--ram", "0x%08x:4@2000" % c1, "--ram", "0x%08x:4@end" % c1, *opts)
        if r["run"]["outcome"] != "completed":
            problems.append("%s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS)
        if odd:
            problems.append("%s: unmodelled accesses besides the window's: %s" % (name, odd[:8]))
        core1 = [struct.unpack("<I", ram(out, c1, 4, w))[0] for w in ("2000ms", "end")]
        return out, hw3_record(ram(out, h3, HW3_LEN, "end")), core1

    out, e, core1 = run("first", 6000, "--script", os.path.relpath(script, ROOT))
    held = hw3_record(ram(out, h3, HW3_LEN, "3500ms"))
    for k, v in (("id", 0x856014), ("tried", 1), ("back", 1), ("idle_timeouts", 0), ("stored", 1), ("count", 1),
                 ("put_result", 0), ("get_result", -1)):
        if e[k] != v:
            problems.append("first: %s is %d, not %d" % (k, e[k], v))
    if held["grid"] != [2 if c == 10 else 0 for c in range(16)] or any(e["grid"]):
        problems.append("first: the grid while PLAY was held %s, at the end %s (column 10, PA6, alone)"
                        % (held["grid"], e["grid"]))
    if held["adc"][4] != 900 or e["adc"][4] != 300 or e["adc"][3] != 640:
        problems.append("first: ADC channel 4 %d then %d (900 then the pot's 300), channel 3 %d (640)"
                        % (held["adc"][4], e["adc"][4], e["adc"][3]))
    if not 0 < core1[0] < core1[1]:
        problems.append("first: core 1's counter %d at 2 s, %d at the end: not rising" % tuple(core1))
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        chip = f.read()
    flash = os.path.join(work, "first-out.bin")
    with open(flash, "wb") as f:
        f.write(chip)
    _, e, _ = run("second", 3000, "--flash", os.path.relpath(flash, ROOT))
    if (e["count"], e["get_result"], e["put_result"]) != (2, 4, 0):
        problems.append("second: count %d, get %d, put %d (2, 4, 0)" % (e["count"], e["get_result"], e["put_result"]))
    # The shipping build: the window's CON reads 0 in fwtest, so no round trip.
    sb = os.path.join(work, "shipping")
    build(sb, log, "--define", "SB_HW_FM1")
    sh3 = fws.elf_symbols(os.path.join(sb, "app.elf"))["hw3"]
    r = fwtest(os.path.join(sb, "app.bin"), os.path.join(work, "run-shipping"), log, "--ms", "2000",
               "--ram", "0x%08x:%d@end" % (sh3, HW3_LEN))
    e = hw3_record(ram(os.path.join(work, "run-shipping"), sh3, HW3_LEN, "end"))
    if e["tried"] or e["stored"] or r["run"]["outcome"] != "completed":
        problems.append("shipping: tried %d, stored %d, %s (the window's CON reads 0: neither)"
                        % (e["tried"], e["stored"], r["run"]["outcome"]))
    # start3b's unit build (SB_HW_HOLD), its hold cut short: the round
    # trip's last LED mark (OCT- and OCT+ alone) held until the scan, the
    # tick watched after the store and core 1, the test screen reached and
    # the step row drawn there.
    hb = os.path.join(work, "hold")
    build(hb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD")
    hout = os.path.join(work, "run-hold")
    r = fwtest(os.path.join(hb, "app.bin"), hout, log, "--ms", "6000", "--flash-out", "--leds-every", "100",
               "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN))
    bc = fws.beacon(ram(hout, BEACON_ADDR, fws.BEACON_LEN))
    if r["run"]["outcome"] != "completed" or bc["screen"] != 2 or bc["halt_reason"]:
        problems.append("hold: %s, screen %d, halt %d (the test screen, no halt)"
                        % (r["run"]["outcome"], bc["screen"], bc["halt_reason"]))
    with open(os.path.join(hout, "leds.csv")) as f:
        leds = [[int(v) for v in row[1:]] for row in list(csv.reader(f))[1:]]
    if not any(v[0] and v[1] and not any(v[2:]) for v in leds):
        problems.append("hold: no sample with OCT- and OCT+ alone lit (the round trip's last mark)")
    _, _, end = fws.read_png(os.path.join(hout, "lcd-end.png"))
    if not any(end[y][x] != (0, 0, 0) for y in range(HW3_STEP_Y, HW3_STEP_Y + 8) for x in range(6, 120)):
        problems.append("hold: no step row on the test screen")
    print("hw3: the round trip read 856014 and came back; the store's counter 1, then 2 at the next start; the grid"
          " column 10, PA6, while PLAY was held; ADC channel 4 900, then 300; core 1 counting; the shipping build,"
          " whose window CON reads 0 in fwtest, tries neither; the held build reaches the test screen, its round"
          " trip's last LED mark (OCT- and OCT+) held, its step row drawn")
    return problems


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


CASES = [
    ("ownbase", case_ownbase),
    ("outside", case_outside),
    ("flags", case_flags),
    ("engine", case_engine),
    ("platform", case_platform),
    ("sysex", case_sysex),
    ("rawout", case_rawout),
    ("store", case_store),
    ("powercut", case_powercut),
    ("region", case_region),
    ("nostart", case_nostart),
    ("parts", case_parts),
    ("probe", case_probe),
    ("light", case_light),
    ("panel", case_panel),
    ("hw", case_hw),
    ("hw3", case_hw3),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    a.build = os.path.abspath(a.build)
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    failed = []
    for name, fn in CASES:
        if a.only and name not in a.only:
            continue
        work = os.path.join(out, name)
        os.makedirs(work)
        log = os.path.join(work, "log.txt")
        try:
            problems = fn(a, work, log)
        except RuntimeError as e:
            problems = [str(e)]
        for p in problems:
            print("  FAIL %s: %s" % (name, p))
        if problems:
            failed.append(name)
    print("seams suite: %s" % ("FAIL (%s)" % ", ".join(failed) if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
