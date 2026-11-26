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
- nowrace (BR-17, after audio5): the hardware build's sb_now() never
  goes back. A test build (SB_TEST_NOW_RACE) makes the slot interrupt's
  time-keeping (its acknowledge and its count) happen at each point
  between sb_now()'s reads just after TIMER0 has wrapped, 50 times at
  each of the four, and every reading is no earlier than the one before
  it. (Until the fix the wrap flag was read after the loop: an interrupt
  there put the time one slot back, which a busy wait read as a timeout.)
- report1 (BR-17, clean-br17-report1; since round 2 the release's): the
  report log. From a chip whose log region holds older data (as the
  owner's unit does): the power-on's one record, "Summary", numbered 1 in
  the region's first slot, its sector erased and the rest left as it was;
  tools/report_decode.py reads it back (layout 18). A second power-on from
  that chip numbers on in the next slot; one from a full ring erases the
  oldest sector and keeps the rest. A write that fails its check
  (SB_TEST_LOG_VERIFY_FAIL) is kept in the log's own fields and written
  again in the next slot under the same number, and the decoder lists the
  failed one.
- hw (BR-17, Phase B; since round 2 the release's start): the FM-1
  release, SB_HW_FM1 (R-HW-1), starts to its panel with no halt. Built
  with SB_TEST_FAULT as well (main's stack overrun) it halts on the
  stack's guard with the screen solid red. Built with SB_TEST_SPI_NO_IRQ
  (SPI1's interrupt left off) the first frame's chain stalls and
  lcd_wait's timeout draws band 5 under bands 1 to 3. Its hardware package
  passes fwsc.py's unit checks; with SB_ENGINE_EXTERNAL or a probe it is
  refused, and so is the test build without SB_USB_MIDI.
- release (round 2, clean-r2-cleanup): the published release (USB off)
  and the owner-only one (USB on), each with KEY1 tapped from power-on:
  sound in the first 0.5 s, the panel, one record ("Summary", layout 18,
  the build's identity) and no problem, the start's stages in order and
  ready well under a second on fwtest's clock (only the unit's time
  counts, HW-175). The owner-only one enumerates with --usb, no problem
  listed. From the unit builds: every symbol only the owner-only image
  has is usb_midi.c's, none is only in the published one, and the
  published image has neither 1209:0001's bytes nor "small-beeps" in
  UTF-16 (R-USB-1).
- test (round 2, clean-r2-cleanup): the owner-only test build, which keeps
  the bring-up: from power-on the instrument's start with every stage's
  record (layout 17), KEY1 sounding; with HOME held the test screen; its
  unit file runs past the start's bands through fwtest's package path.
- usbmidi (U3-F, clean-br17-audio14; U3-U; round 2): the USB MIDI device,
  a test build with SB_USB_MIDI, with fwtest's --usb host: enumerated as
  1209:0001, "small-beeps" for the manufacturer and the product, no serial
  number, no problem listed; the host's notes sound in audio.wav; the
  panel's notes reach usb-midi-out.csv; the set-up is HW-178's, started
  once the cable reading (CON0 bits 16 and 17) reads steadily 0 three
  checks in a row; every stage reached, nothing given up. Without --usb
  (fwtest 0.15.0) the lines change from read to read as with no cable, so
  USB doesn't start, and the outputs are build A's. The test build's log,
  end to end, with the USB records; the owner-only release's unit file
  enumerates through fwtest's package path with --usb; the published
  release has none of the device's symbols.
- screens (round 3, clean-r3-store): the published release's screens in
  large text against golden images (tests/seams/screens), the title and
  the event line at scale 3, every other word and number at 2.
- storerel (round 3): the release starts the store: an erased region, a
  save read back at the next start, a full region (every slot, start3b's
  counter writes, the ring gone round) read within the start's time; no
  write without the code window's registers.
- soak (round 3): the test file's save soak, its power cut at points
  across its erases and programs, slot 16 then A or B, never broken.
- fault (round 3): the red screen's cause and address in large text, from
  the test file's trap and from a fault while a save has the flash.
- stack (round 3): the owner-only release's stacks with notes, USB traffic
  and saves: 512 bytes or more unused on each, no underrun.

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
import time
import zlib
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


def hexv(v):
    """A hex string (or None) from result.json as a number."""
    return int(str(v), 16) if v is not None else None


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
            chip = st.chip_of(f.read())
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
            after = st.chip_of(f.read())
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
            chip = st.chip_of(f.read())
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


# Since start3c the build reads the corex2 words 0x80 to 0x8F around core
# 1's release (Q-17), which fwtest doesn't model either.
HW_COREX2 = {"0x%08x" % (0x01EEE000 + 4 * (0x80 + i)) for i in range(16)}
HW_WINDOW_READS = {"0x00040200", "0x0004020c", "0x00040304"} | HW_COREX2   # HW-128: CON, the base, the key
# The round trip's registers (HW-128): those, the window's cipher and the
# peripheral cipher. fwtest models none of them; 0x01F0xxxx is RAM there.
HW_WINDOW_REGS = HW_WINDOW_READS | {"0x00040300", "0x00013000", "0x00040204"}   # and BAUD (HW-134)
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
    """hw (R-HW-1; since round 2 the release's start, clean-r2-cleanup): the release on the unit's start-up, its
    panel at the end with no halt; with SB_TEST_FAULT a halt on red; with SB_TEST_SPI_NO_IRQ bands 1 to 3, then
    band 5; its hardware package passes the unit's checks; SB_HW_FM1 refused with an external engine or a probe,
    and the test build refused without the USB device."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, *R_PUB)
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "3000", "--lcd", "end",
               "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("hw: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    # The release reads the window's registers for the log (HW-128), which fwtest doesn't model: those alone.
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_READS)
    if odd:
        problems.append("hw: unmodelled accesses: %s" % odd[:8])
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    _, _, end = fws.read_png(os.path.join(out, "lcd-end.png"))
    lit = sum(1 for row in end for p in row if p[:3] != (0, 0, 0))
    if bc["halt_reason"] or lit < 200:
        problems.append("hw: at the end halt %d, %d pixels lit (the panel up, no halt)" % (bc["halt_reason"], lit))
    fb = os.path.join(work, "fault")
    build(fb, log, *R_PUB, "--define", "SB_TEST_FAULT")
    fout = os.path.join(work, "run-fault")
    r = fwtest(os.path.join(fb, "app.bin"), fout, log, "--ms", "3000", "--halt-ok", "--lcd", "end",
               "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN))
    _, _, rows = fws.read_png(os.path.join(fout, "lcd-end.png"))
    bc = fws.beacon(ram(fout, BEACON_ADDR, fws.BEACON_LEN))
    # SB_TEST_FAULT overruns main's stack: the tick's guard check halts (SB_HALT_STACK). Since round 3 the red
    # screen carries its cause and address in white (case fault checks the text): red and white only.
    if r["run"]["outcome"] != "halt" or bc["halt_reason"] != 3 \
            or any(p[:3] not in ((255, 0, 0), (255, 255, 255)) for row in rows for p in row) \
            or sum(1 for row in rows for p in row if p[:3] == (255, 0, 0)) < 40000:
        problems.append("hw with SB_TEST_FAULT: %s, halt reason %d, the screen not red with white text" % (
            r["run"]["outcome"], bc["halt_reason"]))
    nb = os.path.join(work, "no-irq")
    build(nb, log, *R_PUB, "--define", "SB_TEST_SPI_NO_IRQ")
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
    for name, opts, words in (("engine", ("--define", "SB_ENGINE_EXTERNAL"), "is the base's own start-up on a unit"),
                              ("probe", ("--define", "SB_PROBE_PANEL"), "is not a probe"),
                              ("test-no-usb", ("--define", "SB_HW_TEST"), "is the owner-only test build")):
        code, text = build(os.path.join(work, "with-" + name), log, *R_PUB, *opts, check=False)
        if not code or words not in text:
            problems.append("SB_HW_FM1 with %s not refused (exit %d)" % (" ".join(opts[1::2]), code))
    print("hw: the release's start to its panel, no halt; a fault halts on red; band 5 for a frame whose interrupt"
          " never came; its hardware package passes the unit's checks; an external engine, a probe, and the test build"
          " without USB refused")
    return problems


HW3_FIELDS = ("win_con", "win_base", "win_key", "tried", "back", "idle_timeouts", "id", "status1", "status2",
              "stored", "count", "get_result", "put_result")    # hw_fm1.h, struct hw_start3
HW3_LEN = 4 * len(HW3_FIELDS) + 16 + 4 * 12
HW3_STEP_Y = 216    # hw_fm1.h


# Then (since start3c) core 1's release in HW-135's order.
HW3_C1 = ("c1_pre", "c1_post", "c1_word", "c1_fn", "sd_before", "sd_set", "sd_after", "c1_clr1", "c1_seen",
          "c1_wait_ms", "c1_at")
HW3_FULL_LEN = HW3_LEN + 4 * len(HW3_C1) + 4 * 33


def hw3_record(data):
    w = dict(zip(HW3_FIELDS, struct.unpack_from("<13i", data)))
    w["grid"] = list(data[52:68])
    w["adc"] = list(struct.unpack_from("<12I", data, 68))
    if len(data) >= HW3_FULL_LEN:
        w.update(zip(HW3_C1, struct.unpack_from("<11I", data, HW3_LEN)))
        o = HW3_LEN + 4 * len(HW3_C1)
        w["x2_before"] = list(struct.unpack_from("<16I", data, o))
        w["x2_after"] = list(struct.unpack_from("<16I", data, o + 64))
        (w["count1"],) = struct.unpack_from("<I", data, o + 128)
    return w


def core1_problems(name, w, sysdiv):
    """The release's record (start3c): core 1's flag seen in fwtest, which
    starts core 1 at the first of SYS_DIV bit 3 and C1_CON bit 3 (HW-10);
    SYS_DIV set with bit 3 and put back exactly (sysdiv), or never written;
    C1_CON's bit 1 cleared; the start word read back; core 1 counting."""
    p = []
    if not w["c1_seen"] or w["c1_wait_ms"] >= 100 or not w["count1"]:
        p.append("%s: core 1's sign %d after %d ms, its counter %d a second later" % (name, w["c1_seen"],
                                                                                    w["c1_wait_ms"], w["count1"]))
    want_set = w["sd_before"] | 8 if sysdiv else 0
    if w["sd_set"] != want_set or w["sd_after"] != w["sd_before"]:
        p.append("%s: SYS_DIV %08x, %08x with bit 3, %08x after (expected %08x, then as before)"
                 % (name, w["sd_before"], w["sd_set"], w["sd_after"], want_set))
    if w["c1_clr1"] & 2 or w["c1_word"] != w["c1_fn"]:
        p.append("%s: C1_CON %08x after bit 1 cleared; start word %08x, the loop at %08x"
                 % (name, w["c1_clr1"], w["c1_word"], w["c1_fn"]))
    return p


FIND_LINE = ("kind", "col", "port", "bit", "count", "value", "when", "fresh", "dirty", "l0", "l1", "l2", "nlevels")
FIND_LEN = 4 * 5 + 8 * 4 * len(FIND_LINE)    # hw_start3.c, struct hw_finder


# audio1 (hw_fm1.h, struct hw_audio): the registers at main's start and
# with the tone on, then the probe's counts and measures.
AUD_REGS = 22
AUD_FIELDS = ("regs_read", "started", "seq", "n0_set", "n0", "t0", "n1", "t1", "halves", "units", "fps10",
              "master", "gain", "tone_on", "storm", "flips", "pend")
AUD_LEN = 4 * (2 * AUD_REGS + len(AUD_FIELDS))
AUD_AL0 = 11          # ALNK0's CON0 in the registers' order (hw_audio.c)
AUD_Y = 160           # hw_fm1.h, HW_AUD_Y
AUD_FPS = 24000000 / 544.0   # fwtest's frames a second (HW-45)


AUD_MORE = 13
AUD_STEP_FIELDS = ("step_state", "steps", "clk_before", "clk_set", "clk_back")
AUD2_LEN = AUD_LEN + 4 * (3 * AUD_MORE + AUD_REGS + len(AUD_STEP_FIELDS))
AUD_CLK2 = 1          # CLK_CON2 in audio1's registers (hw_audio.c)
HW_REC = 13           # fwtest's key of REC (HW-35)
AUD3_C1 = 13          # hw_fm1.h, HW_C1_MARKS
AUD3_FIELDS = ("c1_seen", "c1_moved", "al_state", "al_keys", "al_before", "al_stop", "al_back",
               "al_blocks_stop", "al_blocks_back")
AUD_AB_FIELDS = ("a_state", "a_keys", "a_before", "a_clr", "a_set", "a_back", "b_state", "b_keys", "b_before",
                 "b_set", "b_back", "refused")
AUD3_LEN = AUD2_LEN + 4 * (2 * AUD3_C1 + len(AUD3_FIELDS) + 32 + len(AUD_AB_FIELDS) + 32)
AUD_AB_AT = AUD2_LEN + 4 * (2 * AUD3_C1 + len(AUD3_FIELDS) + 32)
HW_SEQ = 11           # fwtest's key of SEQ (HW-35)
HW_ARP = 10           # fwtest's key of ARP: step A
HW_SAVE = 9           # fwtest's key of SAVE: step B


def aud_ab(data):
    return dict(zip(AUD_AB_FIELDS, struct.unpack_from("<%dI" % len(AUD_AB_FIELDS), data, AUD_AB_AT)))


def st_clk_bit9(data):
    """CLK_CON2 as REC's step left it: the value read before, with bit 9."""
    o = AUD_LEN + 4 * (3 * AUD_MORE + AUD_REGS)
    return struct.unpack_from("<5I", data, o)[3]


def _build_id():
    """The hardware build's identity, as hw_fm1.h's HW_BUILD_ID gives it to
    a build without the newest round's define (case report1's): the last
    of its definitions, the #else of the newest round's (since audio13,
    whose own identity comes first)."""
    with open(os.path.join(ROOT, "firmware", "src", "hw_fm1.h")) as f:
        return re.findall(r'#define HW_BUILD_ID\s+"([^"]+)"', f.read())[-1]


BUILD_ID = _build_id()


# The report log's layout every hardware build writes but audio11's (layout 10, case audio11).
HW_LAYOUT_OLD = 9


def report_decoder():
    spec = importlib.util.spec_from_file_location("report_decode", os.path.join(ROOT, "tools", "report_decode.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HW_EDIT = 6           # fwtest's key of EDIT: save a report
REP_FIELDS = ("scanned", "found", "slot", "seq", "saved", "fails", "last_err")


def case_report1(a, work, log):
    """report1 (since round 2 in the release, clean-r2-cleanup): the report log. A chip whose log region holds
    older data gets the power-on's one record, "Summary", numbered 1 in the region's first slot, its sector erased
    and the rest untouched; the decoder reads it back (layout 18). From that chip a second power-on numbers on in
    the next slot; from a full ring a power-on erases the oldest sector and keeps the rest; a write that fails its
    verify (SB_TEST_LOG_VERIFY_FAIL) is found, counted and written again in the next slot."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *R_PUB, *FW_WINDOW)
    hr = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_rep"]
    if BUILD_ID.encode() not in read_bytes(os.path.join(b, "app.bin")):
        problems.append("report1: the build's identity isn't in app.bin")

    def run(name, image, seed, ms=6000):
        flash = os.path.join(work, name + "-seed.bin")
        with open(flash, "wb") as f:
            f.write(seed)
        out = os.path.join(work, name)
        r = fwtest(image, out, log, "--ms", str(ms), "--flash", os.path.relpath(flash, ROOT), "--flash-out",
                   "--ram", "0x%08x:%d@end" % (hr, 4 * len(REP_FIELDS)))
        if r["run"]["outcome"] != "completed":
            problems.append("report1 %s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS)
        if odd:
            problems.append("report1 %s: unmodelled accesses besides the window's: %s" % (name, odd[:8]))
        rep = dict(zip(REP_FIELDS, struct.unpack("<%dI" % len(REP_FIELDS), ram(out, hr, 4 * len(REP_FIELDS)))))
        return read_bytes(os.path.join(out, "flash.bin")), rep

    image = os.path.join(b, "app.bin")
    # The unit's case: the log region holds older data, never 0xFF.
    seed = bytearray(b"\xff" * 0x100000)
    for i in range(rd.LOG_BASE, rd.LOG_END):
        seed[i] = (i * 7 + 3) & 0x7F
    chip, rep = run("first", image, bytes(seed))
    rs, bad = rd.records(chip)
    got = [(r["seq"], r["label"], r["offset"]) for r in rs]
    if got != [(1, "Summary", rd.LOG_BASE)] or bad or (rep["saved"], rep["fails"], rep["found"]) != (1, 0, 0):
        problems.append("report1 first: records %s, %d with a bad CRC, saved/failed/found %s (one Summary, #1 in the"
                        " first slot; 1, 0, 0)" % (got, len(bad), (rep["saved"], rep["fails"], rep["found"])))
    if any(not r["known"] or r["build"] != BUILD_ID or r["layout"] != R_LAYOUT for r in rs):
        problems.append("report1 first: a record of an unknown layout or another build: %s"
                        % [(r["layout"], r["count"], r["build"]) for r in rs])
    used = (rd.REC + 4095) // 4096 * 4096
    if chip[rd.LOG_BASE + used:rd.LOG_END] != bytes(seed[rd.LOG_BASE + used:rd.LOG_END]):
        problems.append("report1 first: the sectors past the record's changed")
    chip2, rep2 = run("second", image, chip)
    rs2, _ = rd.records(chip2)
    if [(r["seq"], r["label"], r["offset"]) for r in rs2] != [(1, "Summary", rd.LOG_BASE),
                                                             (2, "Summary", rd.LOG_BASE + rd.REC)] or rep2["found"] != 1:
        problems.append("report1 second: records %s, %d found at the start (#2 after the first run's #1)" % (
            [(r["seq"], r["label"], hex(r["offset"])) for r in rs2], rep2["found"]))
    # A full ring: the next record goes in slot 0, its sector erased.
    full = bytearray(b"\xff" * 0x100000)
    slots = (rd.LOG_END - rd.LOG_BASE) // rd.REC
    for i in range(slots):
        w = [0] * (rd.REC // 4)
        w[0], w[1], w[2], w[3] = rd.MAGIC, HW_LAYOUT_OLD, 1000 + i, i
        rec = bytearray(struct.pack("<%dI" % (rd.REC // 4), *w))
        rec[32:35] = b"old"
        struct.pack_into("<I", rec, rd.REC - 4, zlib.crc32(bytes(rec[:rd.REC - 4])) & 0xFFFFFFFF)
        full[rd.LOG_BASE + rd.REC * i:rd.LOG_BASE + rd.REC * (i + 1)] = rec
    chip3, rep3 = run("wrap", image, bytes(full), 9000)
    rs3, _ = rd.records(chip3)
    seqs = [r["seq"] for r in rs3]
    first = 1000 + (rd.REC + 4095) // 4096 * 4096 // rd.REC
    if seqs != list(range(first, 1000 + slots)) + [1000 + slots] or rs3[-1]["offset"] != rd.LOG_BASE \
            or rep3["found"] != slots:
        problems.append("report1 wrap: sequences %s..%s (%d records), the new one at %s (%d to %d, then one new in"
                        " slot 0)" % (seqs[:3], seqs[-3:], len(seqs), hex(rs3[-1]["offset"]) if rs3 else None, first,
                                      999 + slots))
    # A write that fails (SB_TEST_LOG_VERIFY_FAIL: the first record programmed with one bit wrong): found, kept in
    # the log's own fields, and the record written again in the next slot under the same number; the decoder
    # lists the failed one with its header.
    vb = os.path.join(work, "build-verify")
    build(vb, log, *R_PUB, *FW_WINDOW, "--define", "SB_TEST_LOG_VERIFY_FAIL")
    vchip, _ = run("verify", os.path.join(vb, "app.bin"), bytes(seed))
    vrs, vbad = rd.records(vchip)
    vb0 = rd.bad_record(vchip, vbad[0]) if vbad else {}
    vl = vrs[-1]["fields"] if vrs else {}
    got = (len(vbad), vb0.get("slot"), vb0.get("seq"), vb0.get("label"), [(x["seq"], x["label"]) for x in vrs],
           [x["offset"] for x in vrs], vl.get("log_fail_count"), vl.get("log_retries"), vl.get("log_fail0_seq"),
           vl.get("log_fail0_slot"), vl.get("log_fail0_err"), vl.get("log_fail0_pages_differ"),
           vl.get("log_fail0_first_byte"), vl.get("log_fail0_bytes_read_ff"), vl.get("log_page_rewaits"))
    exp = (1, 0, 1, "Summary", [(1, "Summary")], [rd.LOG_BASE + rd.REC], 1, 1, 1, 0, 5, 1, 82, 0, 0)
    if got != exp:
        problems.append("report1 verify: %s (%s)" % (got, exp))
    print("report1: from older data the power-on's Summary in the first slot, the sectors past it untouched; a second"
          " power-on numbered on; from a full ring the oldest sector erased, %d records kept; a failed write found,"
          " logged and written again in the next slot" % len(rs3))
    return problems


AUD_STEPS = 8         # hw_fm1.h, HW_K_N: the steps' snapshots (6 before audio5)
AUD_HI_AT = AUD_AB_AT + 4 * (len(AUD_AB_FIELDS) + AUD_STEPS * 2 * 4)
AUD_H_FIELDS = ("h_state", "h_keys", "h_measures", "clk1_before", "clk1_check", "clk1_audio", "clk1_back",
                "gp_before", "gp_check", "gp_audio", "gp_back", "check0", "check1", "audio0", "audio1", "check_to",
                "audio_to", "check_clk2", "audio_clk2")
AUD_I_FIELDS = ("i_state", "i_keys", "i_bit10", "b0", "b1", "b2", "b3", "a0", "a1", "a2", "a3", "con_back",
                "clk_before", "clk_set", "clk_set10", "clk_back", "flips", "pend", "span", "hps10")
AUD4_LEN = AUD_HI_AT + 4 * (len(AUD_H_FIELDS) + len(AUD_I_FIELDS) + 4)
HW_ENV, HW_FX, HW_LFO, HW_SEL = 4, 2, 5, 3      # fwtest's keys of ENV, FX, LFO and SEL (input.h)
GPCNT_REGS = {"0x00011100", "0x00011104"}
ALNK1_REGS = {"0x%08x" % (0x00015100 + 4 * i) for i in range(9)}


AUD_K_AT = AUD4_LEN
AUD_K_FIELDS = ("k_state", "k_keys", "k_clk1_before", "k_gp_before", "k_clk1_back", "k_gp_back")
AUD5_LEN = AUD_K_AT + 4 * (len(AUD_K_FIELDS) + 10 * 6)
HW_GLO, HW_OCTUP = 7, 1      # fwtest's keys of GLO (step K) and OCT+ (step J) (input.h)


HW_OCTDOWN = 0        # fwtest's key of OCT- (step D)


HW_KEY1, HW_KEY2 = 14, 15   # fwtest's keys of KEY1 (L1) and KEY2 (L2) (input.h, INPUT_KEY(1) and (2))


HW_KEY3, HW_KEY4, HW_KEY5, HW_KEY6 = 16, 17, 18, 19   # fwtest's keys of KEY3 to KEY6 (audio8: R2, step 1, sweep, sense)


def a8_script(work, name, keys):
    path = os.path.join(work, name + ".script")
    with open(path, "w") as f:
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    return os.path.relpath(path, ROOT)


def a8_run(work, log, b, name, keys, ms, *extra):
    out = os.path.join(work, name)
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", str(ms), "--flash-out",
               "--script", a8_script(work, name, keys), *extra)
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = report_decoder().records(f.read())
    return r, out, rs, bad


# Labels the old probe steps write: none may appear once their keys are the engine's (audio9).
A9_STEP_LABELS = ("REC", "SEQ", "A ", "B ", "H ", "I ", "K ", "J ", "D ", "L1", "L2 undone", "L refused", "S1", "SW", "SE",
                  "R2 refused")


def a9_run(work, log, b, name, keys, ms, *extra):
    """keys: (time, key, held for) each."""
    path = os.path.join(work, name + ".script")
    with open(path, "w") as f:
        for t, k, d in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + d, k))
    out = os.path.join(work, name)
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", str(ms), "--flash-out",
               "--script", os.path.relpath(path, ROOT), *extra)
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = report_decoder().records(f.read())
    return r, out, rs, bad


HW_PLAY, HW_HOME = 12, 8   # fwtest's keys of PLAY and HOME (input.h)
HW_CHORD = (14, 16, 18, 19, 21, 23, 25, 26)   # KEY1, 3, 5, 6, 8, 10, 12, 13: eight keys (fwtest's key numbers)




def font_glyphs():
    """firmware/src/font.c's glyphs: {character: 8 rows of 5 bits}."""
    with open(os.path.join(ROOT, "firmware", "src", "font.c")) as f:
        text = f.read()
    out = {}
    for m in re.finditer(r'/\* (\'.\'|\'\\\\\'|\'\'\') \*/ G\(((?:"[.#]{5}",? ?){8})\)', text):
        ch = m.group(1)[1:-1].replace("\\\\", "\\")
        rows = re.findall(r'"([.#]{5})"', m.group(2))
        out[ch] = tuple(int(r.replace("#", "1").replace(".", "0"), 2) for r in rows)
    return out


def read_big(fws, png, glyphs):
    """audio11's large area on a screenshot: three lines of 12 cells, each
    cell 18 x 24 pixels from (6, 40 + 24 line), the glyph at three times
    the font; a cell is read as the glyph whose pixels match, '?' if none."""
    _, _, rows = fws.read_png(png)
    lit = lambda x, y: sum(rows[y][x]) > 60
    by_bits = {v: k for k, v in glyphs.items()}
    lines = []
    for ln in range(3):
        t = ""
        for c in range(12):
            x0, y0 = 6 + 18 * c, 40 + 24 * ln
            bits = tuple(sum(1 << (4 - i) for i in range(5) if lit(x0 + 3 * i + 1, y0 + 3 * r + 1)) for r in range(8))
            t += by_bits.get(bits, "?")
        lines.append(t.rstrip())
    return lines


HW_ARP_KEY = 10      # fwtest's key of ARP (input.h)
HW_ALG_ENC = 1       # fwtest's encoder of ALGORITHM (input.h)


def runs_between(x, rate, ms, t0, t1):
    """nonzero_runs of x (a run's audio.wav, which ends at ms) that begin
    between t0 and t1 ms of the run."""
    return [(s0, e) for s0, e in nonzero_runs(x) if t0 <= ms - (len(x) - s0) * 1000.0 / rate <= t1]


def nonzero_runs(x, gap=32, least=4410):
    """The runs of x between stretches of at least `gap` exact zeros, as
    (start, end), those at least `least` samples long."""
    runs, start, zeros = [], None, 0
    for i, v in enumerate(x):
        if v:
            if start is None:
                start = i
            zeros = 0
        elif start is not None:
            zeros += 1
            if zeros >= gap:
                if i - zeros + 1 - start >= least:
                    runs.append((start, i - zeros + 1))
                start, zeros = None, 0
    if start is not None and len(x) - start >= least:
        runs.append((start, len(x)))
    return runs


def a12_arp(work, log, b, name):
    """The instrument's start (SEL) in build b, ARP on and two keys held 4 s:
    the steps' times in frames (sb_arp's log), and the record's fields."""
    fws = fw_suite()
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    path = os.path.join(work, name + ".script")
    with open(path, "w") as f:
        f.write("9000 key %d tap 100\n11000 key %d tap 100\n" % (HW_SEL, HW_ARP_KEY))
        for k in (HW_KEY1, HW_KEY5):
            f.write("11500 key %d down\n15500 key %d up\n" % (k, k))
    out = os.path.join(work, name)
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "16000", "--flash-out", "--script",
               os.path.relpath(path, ROOT), "--ram", "0x%08x:%d@end" % (sy["sb_arp"], 4 * 48))
    w = struct.unpack("<48I", ram(out, sy["sb_arp"], 4 * 48))
    n = w[14]
    t = [w[16 + i % 32] for i in range(max(0, n - 32), n)]
    return r, [y - x for x, y in zip(t, t[1:])], w[2]


A13_INST = ["boot", "Inst engine", "Inst store", "Slot16 empty", "Inst synth", "Synth on", "Inst ALNK0", "Inst L2", "L2 before", "L2 kept",
            "Inst R2", "R2 before", "R2 set", "Inst route", "Route before", "Route kept", "Inst panel"]
A13_FWTEST_WORDS = (0, 0x8000, 0, 0, 0)   # the five words as fwtest reads them with no --usb: CON1's bit 15 set


def a13_labels(rs):
    return [x["label"] for x in rs if x["label"] != "MASTER still" and not x["label"].startswith("PB5")]


def a13_cold(work, log, b, name, sy):
    """Power-on with nothing held in build b: KEY1, then ARP on and two keys
    held 10 s, REC (the panel's save), OCT- (the test screen's U2-A key:
    nothing in the panel). Returns the result, the records and audio.wav's
    left channel and rate."""
    rd = report_decoder()
    path = os.path.join(work, name + ".script")
    with open(path, "w") as f:
        for t, k, d in ((12000, HW_KEY1, 300), (13000, HW_ARP_KEY, 100), (24000, HW_REC, 100),
                        (24500, HW_OCTDOWN, 100)):
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + d, k))
        for k in (HW_KEY1, HW_KEY5):
            f.write("13500 key %d down\n23500 key %d up\n" % (k, k))
    out = os.path.join(work, name)
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "25500", "--flash-out", "--wav", "--script",
               os.path.relpath(path, ROOT), "--ram", "0x%08x:8@end" % sy["sb_ui"])
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    rate, left, _ = aa.read_wav(os.path.join(out, "audio.wav"))
    return r, rs, bad, left, rate, struct.unpack("<2I", ram(out, sy["sb_ui"], 8))[0]


def a13_arp_check(f, name, slow):
    """ARP's steps in a record: the gaps in frames (5514 +-2), each step's
    two times, the gap by sb_now (125 ms of the unit's, 50 of fwtest's
    slower TIMER0's), at least 64 steps in one chain."""
    n = f.get("arp_n", 0)
    steps = [(f["arp_log_%d_frames" % (k % 48)], f["arp_log_%d_units" % (k % 48)]) for k in range(max(0, n - 48), n)]
    df = [y[0] - x[0] for x, y in zip(steps, steps[1:])]
    du = [(y[1] - x[1]) / 24000.0 for x, y in zip(steps, steps[1:])]
    want = 125.0 / slow
    ok = (n >= 64 and f["arp_best_n"] >= 64 and abs(f["arp_gmin_f"] - 5514) <= 2 and abs(f["arp_gmax_f"] - 5514) <= 2
          and all(abs(d - 5514) <= 2 for d in df) and all(abs(d - want) < 3.5 for d in du)
          and abs(f["arp_gmin_units"] / 24000.0 - want) < 3.5 and abs(f["arp_gmax_units"] / 24000.0 - want) < 3.5)
    text = "%s: %d steps (chain %d), gaps %d to %d frames, %.2f to %.2f ms by sb_now (%.0f expected here)" % (
        name, n, f.get("arp_best_n", 0), f.get("arp_gmin_f", 0), f.get("arp_gmax_f", 0),
        f.get("arp_gmin_units", 0) / 24000.0, f.get("arp_gmax_units", 0) / 24000.0, want)
    return ok, text


# Round 2's builds (hw_fm1.h): the release, published (USB off) and owner-only (USB on), and the test build.
R_PUB = ("--define", "SB_HW_FM1")
R_OWN = R_PUB + ("--define", "SB_USB_MIDI")
T_UNIT = R_OWN + ("--define", "SB_HW_TEST")
# The three identities as hw_fm1.h gives them (test, owner-only, published, in that order), so a try's new
# identity needs no change here.
T_ID, R_OWN_ID, R_PUB_ID = re.findall(r'#define HW_BUILD_ID\s+"([^"]+)"', read(os.path.join(ROOT, "firmware", "src",
                                                                                          "hw_fm1.h")))[-3:]
# The release's log layout (hw_fm1.h's HW_LOG_LAYOUT without SB_HW_TEST): 19 since round 3.
R_LAYOUT = 19
# fwtest's window CON reads 0, so a build that logs there takes SB_TEST_HW_WINDOW; the test build's holds short.
FW_WINDOW = ("--define", "SB_TEST_HW_WINDOW")
T_DEFINES = T_UNIT + FW_WINDOW + ("--define", "SB_TEST_SHORT_HOLD")
A14_P = tuple("%05X" % (0x16A00 + 4 * i) for i in range(4))


# The owner-only release's USB device identity in its image: 1209:0001's bytes, as the device descriptor holds them
# (R-USB-1), and the product string in the descriptor's UTF-16.
USB_ID_BYTES = bytes([0x09, 0x12, 0x01, 0x00])
USB_NAME_UTF16 = "small-beeps".encode("utf-16-le")
# The release's ready, in fwtest: a bound on the summary's ready stage (us on fwtest's clock, whose beats are
# HW_RATIO times slow), far under the unit's 1 000 ms (HW-175: fwtest's times don't predict the unit's).
R_READY_US_MAX = 50000


def usb_only_text(text):
    """The lines a C source compiles only with SB_USB_MIDI: those inside an #if whose condition is
    defined(SB_USB_MIDI), alone or with &&, up to its #else, #elif or #endif."""
    out, stack = [], []
    for line in text.split("\n"):
        t = line.strip()
        if re.match(r"#\s*(if|ifdef|ifndef)\b", t):
            stack.append(bool(re.match(r"#\s*if\s+(defined\(\w+\)\s*&&\s*)*defined\(SB_USB_MIDI\)", t)))
        elif re.match(r"#\s*(else|elif)\b", t) and stack:
            stack[-1] = False
        elif re.match(r"#\s*endif\b", t) and stack:
            stack.pop()
        elif any(stack):
            out.append(line)
    return "\n".join(out)


def case_release(a, work, log):
    """release (round 2, clean-r2-cleanup): the published release (USB off) and the owner-only one (USB on). Each
    starts the instrument at once with a key tapped through the start: sound from the first tap, the panel, one
    record ("Summary", layout 18, its identity) and no problem; its stages in order and ready in fwtest well under a
    second. The owner-only one enumerates with --usb, with no problem listed and still one record. From the unit
    builds: the published and owner-only images differ by USB alone (every symbol only the owner-only one has is
    usb_midi.c's, none only in the published), and the published has neither 1209:0001's bytes nor the product
    string in UTF-16."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    rate = None
    script = os.path.join(work, "taps.script")
    with open(script, "w") as f:
        for t in range(0, 2000, 200):
            f.write("%d key %d tap 80\n" % (t, HW_KEY1))
    seen = {}
    for name, opts, extra, want_id in (("published", R_PUB + FW_WINDOW, (), R_PUB_ID),
                                       ("owner-only", R_OWN + FW_WINDOW, ("--usb",), R_OWN_ID)):
        b = os.path.join(work, "build-" + name)
        build(b, log, *opts)
        out = os.path.join(work, name)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "6000", "--wav", "--audio-chip", "--flash-out",
                   "--lcd", "end", "--script", os.path.relpath(script, ROOT), *extra)
        rs, bad = rd.records(read_bytes(os.path.join(out, "flash.bin")))
        rate, left, _ = aa.read_wav(os.path.join(out, "audio.wav"))
        peak = max([abs(v) for v in left[int(0.0 * rate):int(0.5 * rate)]] or [0])
        f0 = rs[0]["fields"] if rs else {}
        at = [f0.get("inst_at_%s_us" % n, 0) for n in rd.INST_STAGES]
        seen[name] = (at[-1], peak, [x["label"] for x in rs])
        if r["run"]["outcome"] != "completed" or bad or [x["label"] for x in rs] != ["Summary"] \
                or not rs[0]["known"] or rs[0]["build"] != want_id or rs[0]["layout"] != R_LAYOUT:
            problems.append("release %s: %s, %d bad, records %s (want one Summary of %s, layout %d)" % (
                name, r["run"]["outcome"], len(bad), [(x["label"], x["build"], x["layout"], x["count"]) for x in rs],
                want_id, R_LAYOUT))
        if at != sorted(at) or not 0 < at[-1] < R_READY_US_MAX or f0.get("inst_problems") or f0.get("route") != 1:
            problems.append("release %s: stages %s us (in order, ready under %d), problems %s, route %s" % (
                name, at, R_READY_US_MAX, f0.get("inst_problems"), f0.get("route")))
        if peak < 100:
            problems.append("release %s: KEY1 tapped from power-on, audio.wav's first 0.5 s peak %d" % (name, peak))
        _, _, end = fws.read_png(os.path.join(out, "lcd-end.png"))
        if sum(1 for row in end for p in row if p[:3] != (0, 0, 0)) < 200:
            problems.append("release %s: the panel isn't up at the end" % name)
        if extra:
            u = r["run"].get("usb") or {}
            if u.get("configuration") != 1 or u.get("problems") or hexv(u.get("vendor")) != 0x1209:
                problems.append("release owner-only: usb %s (configured, no problem)" % u)
    # From the unit builds (no fwtest hooks): USB alone between the two.
    imgs, syms = {}, {}
    for name, opts in (("published", R_PUB), ("owner-only", R_OWN)):
        b = os.path.join(work, "unit-" + name)
        build(b, log, *opts)
        imgs[name] = read_bytes(os.path.join(b, "app-pkg.bin"))
        syms[name] = set(fws.elf_symbols(os.path.join(b, "app-pkg.elf")))
    # The names only SB_USB_MIDI compiles: usb_midi.c's and usb_midi.h's, and those in every other source's
    # blocks under "#if defined(SB_USB_MIDI)" (usb_only_text).
    ident = lambda t: set(re.findall(r"\b[A-Za-z_]\w*\b", t))
    usb_names = set()
    for f in sorted(os.listdir(os.path.join(ROOT, "firmware", "src"))):
        if f.endswith((".c", ".h")):
            text = read(os.path.join(ROOT, "firmware", "src", f))
            usb_names |= ident(text if f.startswith("usb_midi.") else usb_only_text(text))
    only_own = sorted(syms["owner-only"] - syms["published"])
    only_pub = sorted(syms["published"] - syms["owner-only"])
    # The compiler's own local labels (".L...", ".G...") and a function's static locals ("setup.two") count by the
    # name before the dot.
    not_usb = [n for n in only_own if not n.startswith(".") and n.split(".")[0] not in usb_names]
    if not only_own or not_usb or only_pub:
        problems.append("release: symbols only in the owner-only build not from usb_midi.c %s; only in the published"
                        " %s" % (not_usb[:8], only_pub[:8]))
    if USB_ID_BYTES in imgs["published"] or USB_NAME_UTF16 in imgs["published"] \
            or USB_ID_BYTES not in imgs["owner-only"] or USB_NAME_UTF16 not in imgs["owner-only"]:
        problems.append("release: 1209:0001's bytes in the published image %s, its name %s; in the owner-only %s, %s" % (
            USB_ID_BYTES in imgs["published"], USB_NAME_UTF16 in imgs["published"], USB_ID_BYTES in imgs["owner-only"],
            USB_NAME_UTF16 in imgs["owner-only"]))
    print("release: ready in fwtest (us on its clock, %.1f times slow) published %d, owner-only %d; the first 0.5 s"
          " peaks %d and %d; records %s and %s; the owner-only build adds %d symbols, all usb_midi.c's; the published"
          " image has no USB identity; images %d and %d bytes" % (
              HW_RATIO, seen["published"][0], seen["owner-only"][0], seen["published"][1], seen["owner-only"][1],
              seen["published"][2], seen["owner-only"][2], len(only_own), len(imgs["published"]),
              len(imgs["owner-only"])))
    return problems


def case_test(a, work, log):
    """test (round 2, clean-r2-cleanup): the owner-only test build keeps the bring-up. From power-on with nothing
    held, the instrument's start with every stage's record (layout 17, its identity) and KEY1 sounding; with HOME
    held, the test screen; its unit file through fwtest's package path past the start's bands."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *T_DEFINES)
    path = os.path.join(work, "cold.script")
    with open(path, "w") as f:
        f.write("12000 key %d tap 300\n" % HW_KEY1)
    out = os.path.join(work, "cold")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "14000", "--wav", "--audio-chip", "--flash-out",
               "--script", os.path.relpath(path, ROOT))
    rs, bad = rd.records(read_bytes(os.path.join(out, "flash.bin")))
    labels = a13_labels(rs)
    rate, left, _ = aa.read_wav(os.path.join(out, "audio.wav"))
    # The whole capture: the build is silent until KEY1 (with --audio-chip the capture is the chip's frames, so
    # its seconds aren't the run's).
    peak = max([abs(v) for v in left] or [0])
    if r["run"]["outcome"] != "completed" or bad or labels[:len(A13_INST)] != A13_INST \
            or any(x != "USB cable" for x in labels[len(A13_INST):]) \
            or any(x["layout"] != 17 or not x["known"] or x["build"] != T_ID for x in rs) or peak < 100:
        problems.append("test cold: %s, %d bad, records %s, layouts %s, KEY1's peak %d" % (
            r["run"]["outcome"], len(bad), labels, sorted({(x["layout"], x["count"], x["build"]) for x in rs}), peak))
    hpath = os.path.join(work, "home.script")
    with open(hpath, "w") as f:
        f.write("0 key %d down\n5000 key %d up\n" % (HW_HOME, HW_HOME))
    hout = os.path.join(work, "home")
    hr = fwtest(os.path.join(b, "app.bin"), hout, log, "--ms", "9000", "--flash-out", "--script",
                os.path.relpath(hpath, ROOT), "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN))
    hrs, hbad = rd.records(read_bytes(os.path.join(hout, "flash.bin")))
    hboot = next((x["fields"] for x in hrs if x["label"] == "boot"), {})
    hbc = fws.beacon(ram(hout, BEACON_ADDR, fws.BEACON_LEN))
    if hr["run"]["outcome"] != "completed" or hbad or hboot.get("a13_start") != 2 or hbc["screen"] != 2:
        problems.append("test HOME: %s, %d bad, start %s, the beacon's screen %d (2: the test screen)" % (
            hr["run"]["outcome"], len(hbad), hboot.get("a13_start"), hbc["screen"]))
    cb = os.path.join(work, "build-unit")
    build(cb, log, *T_UNIT)
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    upath = os.path.join(work, "unit.fwsc")
    with open(upath, "wb") as f:
        f.write(fwsc.pack(read_bytes(os.path.join(cb, "app-pkg.bin")), "FM-1_" + T_ID))
    pout = os.path.join(work, "unit")
    pr = fwtest(upath, pout, log, "--package", "--ms", "20000", "--lcd", "19900")
    png = os.path.join(pout, "lcd-19900ms.png")
    bands = None
    if os.path.exists(png):
        _, _, rows = fws.read_png(png)
        bands = all(rows[72][x][:3] == (0, 0, 255) and rows[96][x][:3] == (0, 255, 0) for x in range(0, 240, 16))
    if pr["run"]["outcome"] != "completed" or bands is not False:
        problems.append("test unit file: %s, still at the two bands %s" % (pr["run"]["outcome"], bands))
    print("test: from cold %d records (the instrument's %d, then %s), KEY1's peak %d; HOME: the test screen; the"
          " unit file past the start's bands" % (len(rs), len(A13_INST), labels[len(A13_INST):], peak))
    return problems


USB_DEVICE_SYMBOLS = ("sb_usb", "usb_midi_poll", "usb_midi_take", "usb_midi_send")
# The stages a device that enumerated and passed notes both ways reached (all but the give-up).
USB_ALL_STAGES = 20


def case_usbmidi(a, work, log):
    """U3-F (clean-br17-audio14), U3-U (clean-br17-u3u): the USB MIDI
    device in a test build (SB_USB_MIDI) with fwtest's --usb host; the same
    build without it; the owner-only unit file; the published unit build
    without any of it."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    nrec = len(rd.USB_REC)
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_USB_MIDI")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    path = os.path.join(work, "usb.script")
    with open(path, "w") as f:
        # The host's note (channel 1) once the device is up (the third cable check, about 2 s), then the panel's
        # KEY1; and a note at MIDI in for the run without --usb.
        # Try 3: two events in one packet, then four packets in a row of one each; then three keys, each pressed
        # and released, while the host sends notes too (both ways at once). Try 4: one packet whose code index (8)
        # doesn't match its status (90), dropped.
        f.write("3000 usbmidi 09 90 3c 64\n3000 usbmidi 09 90 40 64\n3050 usbmidi 08 80 3c 00\n"
                "3100 usbmidi 08 80 40 00\n3150 usbmidi 09 90 43 64\n3200 usbmidi 08 80 43 00\n"
                "3250 usbmidi 08 90 45 64\n"
                "5000 key %d tap 200\n5100 usbmidi 09 90 48 40\n5300 key %d tap 200\n5400 usbmidi 08 80 48 00\n"
                "5600 key %d tap 200\n6000 midi 90 40 64\n6500 midi 80 40 00\n" % (HW_KEY1, HW_KEY1 + 1, HW_KEY1 + 2))
    out = os.path.join(work, "usb")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--usb", "--wav", "--midi-out", "--ms", "7000", "--script",
               os.path.relpath(path, ROOT), "--ram", "0x%08x:%d@end" % (sy["sb_usb"], 4 * nrec))
    u = r["run"].get("usb") or {}
    rec = words(ram(out, sy["sb_usb"], 4 * nrec), rd.USB_REC)
    reached = [n for n in rd.USB_STAGES if rec["usb_at_" + n]]
    hexv = lambda v: int(str(v), 16) if v is not None else None
    if r["run"]["outcome"] != "completed" or hexv(u.get("vendor")) != 0x1209 or hexv(u.get("product")) != 0x0001 \
            or u.get("manufacturer") != "small-beeps" or u.get("product_name") != "small-beeps" or u.get("serial") \
            or u.get("problems") or u.get("configuration") != 1 or u.get("midi_out_endpoint") is None \
            or u.get("midi_in_endpoint") is None or rec["usb_magic"] != 0x4D425355 or rec["usb_state"] != 2 \
            or rec["usb_giveup_why"] or len(reached) != USB_ALL_STAGES:
        problems.append("usbmidi: %s, usb %s, magic %08X, state %d, gave up %d, stages %s" % (
            r["run"]["outcome"], u, rec["usb_magic"], rec["usb_state"], rec["usb_giveup_why"], reached))
    order = [rec["usb_at_" + n] for n in rd.USB_STAGES[:15]]
    if order != sorted(order) or rec["usb_gap_units"] != 240 or rec["usb_poll_limit"] != 20000:
        problems.append("usbmidi: the set-up's stages out of order %s, spacing %d, polls %d" % (
            order, rec["usb_gap_units"], rec["usb_poll_limit"]))
    rate, left, _ = aa.read_wav(os.path.join(out, "audio.wav"))
    peak = lambda t0, t1: max([abs(v) for v in left[int(t0 * rate):int(t1 * rate)]] or [0])
    host, quiet = peak(3.0, 3.4), peak(0.0, 0.25)
    if host < 100 or quiet > 10:
        problems.append("usbmidi: the host's notes in audio.wav peak %d (3.0 to 3.4 s), before them %d" % (host, quiet))
    sent = []
    p = os.path.join(out, "usb-midi-out.csv")
    if os.path.exists(p):
        with open(p) as f:
            for row in csv.DictReader(f):
                sent.append((float(row["ms"]), int(row["cin"], 0) if str(row["cin"]).startswith("0x")
                             else int(row["cin"]), row["bytes"].split()))
    ons = [x for x in sent if x[1] == 9 and len(x[2]) == 3 and int(x[2][2], 16)]
    offs = [x for x in sent if x[1] == 9 and len(x[2]) == 3 and not int(x[2][2], 16)]
    # Each key's press a note on and its release a note off of the same note, nothing else (try 3: on the unit the
    # releases went out as copies of the first packet).
    pairs = [(x[2][1], x[2][2]) for x in sent]
    want_pairs = [(n, v) for n in [ons[k][2][1] for k in range(min(3, len(ons)))] for v in ("64", "00")]
    if len(ons) != 3 or len(offs) != 3 or not 5000 <= ons[0][0] < 5300 or pairs != want_pairs \
            or len(set(n for n, _ in want_pairs)) != 3 or any(3000 <= x[0] < 4900 for x in sent):
        problems.append("usbmidi: usb-midi-out.csv %s (want three keys' note on and off each, nothing echoed)" % sent[:8])
    # Each packet in gives exactly its own events: the two-event packet two, each other one (try 3: on the unit
    # stale bytes past a packet were taken as events).
    rxl = [rec["usb_rx_log_%d" % (k % 8)] for k in range(max(0, rec["usb_rx_log_n"] - 8), rec["usb_rx_log_n"])]
    rx_pk = [(w & 0xFF, w >> 16 & 0xFF) for w in rxl]
    # fwtest's counts are the host's: events_sent went to the device, events_received came from it.
    # Try 4: the events are read to the first zero one (RXCOUNT1 only logged; fwtest's is right), the mismatched
    # one dropped and counted; each packet's non-zero 4-byte slots logged beside it.
    want_pk = [(8, 2)] + [(4, 1)] * 4 + [(4, 0)] + [(4, 1)] * 2
    masks = [rec["usb_rx_mask_%d" % (k % 8)] for k in range(max(0, rec["usb_rx_log_n"] - 8), rec["usb_rx_log_n"])]
    if rx_pk != want_pk or rec["usb_rx_events"] != 8 or rec["usb_rx_bad"] != 1 or masks != [3] + [1] * 7 \
            or u.get("events_sent") != 9 or u.get("events_received") != 6:
        problems.append("usbmidi: packets in (bytes, events) %s, %d events, %d dropped, slots %s, fwtest's sent %s"
                        " received %s (want %s; 8, 1, [3, 1 x7], 9, 6)" % (
                            rx_pk, rec["usb_rx_events"], rec["usb_rx_bad"], masks, u.get("events_sent"),
                            u.get("events_received"), want_pk))
    if rec["usb_cable_checks"] < 3 or rec["usb_lines_set"] or rec["usb_lines_or"] or rec["usb_cable"] != 1:
        problems.append("usbmidi: the cable reading: %d checks, the last %d of %d reads with a bit set, bits %08X" % (
            rec["usb_cable_checks"], rec["usb_lines_set"], rec["usb_lines_reads"], rec["usb_lines_or"]))
    # Without --usb (fwtest 0.15.0): the lines change from read to read as with no cable, so USB doesn't start:
    # still waiting, no stage past the cable reading; the outputs are build A's: the same samples and MIDI bytes.
    outs = {}
    for name, image in (("usb-off", os.path.join(b, "app.bin")), ("build-a", os.path.join(a.build, "app.bin"))):
        o = os.path.join(work, name)
        extra = ("--ram", "0x%08x:%d@end" % (sy["sb_usb"], 4 * nrec)) if name == "usb-off" else ()
        rr = fwtest(image, o, log, "--wav", "--midi-out", "--ms", "7000", "--script", os.path.relpath(path, ROOT),
                    *extra)
        _, wl, wr = aa.read_wav(os.path.join(o, "audio.wav"))
        with open(os.path.join(o, "midi-out.csv")) as f:
            mo = [(float(x[0]), x[1]) for x in list(csv.reader(f))[1:]]
        outs[name] = (rr["run"]["outcome"], wl, wr, mo, rr["run"].get("usb"))
    off = words(ram(os.path.join(work, "usb-off"), sy["sb_usb"], 4 * nrec), rd.USB_REC)
    (o1, l1, r1, m1, u1), (o2, l2, r2, m2, _) = outs["usb-off"], outs["build-a"]
    n = min(len(l1), len(l2))
    same_wav = l1[:n] == l2[:n] and r1[:n] == r2[:n] and abs(len(l1) - len(l2)) <= 128 and max(map(abs, l2)) > 100
    same_midi = [x[1] for x in m1] == [x[1] for x in m2] and len(m2) >= 6 \
        and all(abs(x[0] - y[0]) < 2 for x, y in zip(m1, m2))
    if o1 != "completed" or o2 != "completed" or u1 or not same_wav or not same_midi or off["usb_resets"] \
            or off["usb_state"] != 0 or off["usb_cable"] != 2 or any(off["usb_at_" + n] for n in rd.USB_STAGES[1:]):
        problems.append("usbmidi without --usb: %s/%s, usb %s, resets %d, state %d, cable %d, stages %s; the samples"
                        " the same: %s (%d and %d frames); MIDI out the same: %s (%s, build A %s)" % (
                            o1, o2, u1, off["usb_resets"], off["usb_state"], off["usb_cable"],
                            [n for n in rd.USB_STAGES if off["usb_at_" + n]], same_wav, len(l1), len(l2), same_midi,
                            m1[:6], m2[:6]))
    # A give-up (the test build SB_TEST_USB_STOP: the first port access's bit 15 never comes, before POWER): logged
    # with its stage and index, no stage after it, no USB write after it (so no connection), the instrument on.
    gb = os.path.join(work, "build-stop")
    build(gb, log, "--define", "SB_USB_MIDI", "--define", "SB_TEST_USB_STOP")
    gsy = fws.elf_symbols(os.path.join(gb, "app.elf"))
    gout = os.path.join(work, "stop")
    gr = fwtest(os.path.join(gb, "app.bin"), gout, log, "--usb", "--wav", "--ms", "7000", "--script",
                os.path.relpath(path, ROOT), "--ram", "0x%08x:%d@end" % (gsy["sb_usb"], 4 * nrec))
    stop = words(ram(gout, gsy["sb_usb"], 4 * nrec), rd.USB_REC)
    gu = gr["run"].get("usb") or {}
    g_reached = [n for n in rd.USB_STAGES if stop["usb_at_" + n]]
    _, gleft, _ = aa.read_wav(os.path.join(gout, "audio.wav"))
    g_panel = max([abs(v) for v in gleft[int(5.0 * rate):int(5.4 * rate)]] or [0])
    if gr["run"]["outcome"] != "completed" or stop["usb_state"] != 3 or stop["usb_giveup_why"] != 2 \
            or rd.USB_STAGES[stop["usb_giveup_stage"]] != "irqs_off" or stop["usb_giveup_index"] != 11 \
            or g_reached != list(rd.USB_STAGES[:8]) + ["stopped"] or gu.get("vendor") or g_panel < 100:
        problems.append("usbmidi stop: %s, state %d, why %d at %s index %d, stages %s, usb %s, the panel's note %d" % (
            gr["run"]["outcome"], stop["usb_state"], stop["usb_giveup_why"], stop["usb_giveup_stage"],
            stop["usb_giveup_index"], g_reached, gu, g_panel))
    # The log, end to end: round 2's test build (which keeps every record), with --usb: the instrument's
    # start, then the USB records in order, layout 17 whole, one way out (0, the SDK's steps) and the spacing 10 us;
    # and HOME held, the tries' test keys (KEY7, KEY8) changing nothing of USB.
    lb = os.path.join(work, "build-log")
    build(lb, log, *T_DEFINES)
    lout = os.path.join(work, "log")
    lr = fwtest(os.path.join(lb, "app.bin"), lout, log, "--usb", "--ms", "30000", "--flash-out", "--script",
                os.path.relpath(path, ROOT))
    with open(os.path.join(lout, "flash.bin"), "rb") as f:
        lrecs, lbad = rd.records(f.read())
    usb_labels = [x["label"] for x in lrecs if x["label"].startswith("USB")]
    want = ["USB cable"] + ["USB step %d" % k for k in range(1, 7)] + ["USB set up", "USB reset", "USB address",
                                                                        "USB configured"]
    last = lrecs[-1]["fields"] if lrecs else {}
    lines = rd.u3u_lines(last) if "usb_magic" in last else []
    lu = lr["run"].get("usb") or {}
    if lr["run"]["outcome"] != "completed" or lbad or usb_labels[:len(want)] != want \
            or any(len(x["fields"]) != len(rd.FIELDS[17]) for x in lrecs if x["label"].startswith("USB")) \
            or last.get("usb_giveup_why") or not lines or lu.get("problems") \
            or [x for x in usb_labels if x.startswith(("USB way", "USB spacing", "USB out way"))] \
            or (last.get("usb_tx_variant"), last.get("usb_way_prev"), last.get("usb_try_n"), last.get("usb_gap_units")) \
            != (0, 0xFFFFFFFF, 5, 240):
        problems.append("usbmidi log: %s, %d bad, USB records %s, usb %s, lines %s" % (
            lr["run"]["outcome"], len(lbad), usb_labels, lu, lines[:2]))
    step6_to_sieie = last.get("usb_at_sieie", 0) - last.get("usb_at_step6_pulls", 0)
    kpath = os.path.join(work, "key7.script")
    with open(kpath, "w") as f:
        # HOME let go, then the tries' KEY7 and KEY8 tapped on the test screen: neither is USB's now.
        f.write("0 key %d down\n8000 key %d up\n12000 key %d tap 100\n13000 key %d tap 100\n"
                % (HW_HOME, HW_HOME, HW_KEY1 + 6, HW_KEY1 + 7))
    kout = os.path.join(work, "key7")
    kr = fwtest(os.path.join(lb, "app.bin"), kout, log, "--usb", "--ms", "20000", "--flash-out", "--script",
                os.path.relpath(kpath, ROOT))
    with open(os.path.join(kout, "flash.bin"), "rb") as f:
        krecs, kbad = rd.records(f.read())
    kl = krecs[-1]["fields"] if krecs else {}
    if kr["run"]["outcome"] != "completed" or kbad \
            or [x["label"] for x in krecs if x["label"].startswith(("USB way", "USB spacing", "USB out way"))] \
            or kl.get("usb_gap_presses") != 0 or kl.get("usb_gap_units") != 240 or kl.get("usb_tx_variant") != 0 \
            or (kr["run"].get("usb") or {}).get("configuration") != 1:
        problems.append("usbmidi KEY7 and KEY8: %s, %d bad, labels %s, presses %s, spacing %s, usb %s" % (
            kr["run"]["outcome"], len(kbad), [x["label"] for x in krecs][-8:], kl.get("usb_gap_presses"),
            kl.get("usb_gap_units"), kr["run"].get("usb")))
    # The owner-only release (USB on): its unit file through fwtest's package path with --usb.
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    ub = os.path.join(work, "build-u3u")
    build(ub, log, *R_OWN)
    usy3 = fws.elf_symbols(os.path.join(ub, "app-pkg.elf"))
    upath = os.path.join(work, "u3u.fwsc")
    with open(upath, "wb") as f:
        f.write(fwsc.pack(read_bytes(os.path.join(ub, "app-pkg.bin")), "FM-1_" + R_OWN_ID))
    uout = os.path.join(work, "u3u")
    ur = fwtest(upath, uout, log, "--package", "--usb", "--ms", "40000", "--lcd", "39900")
    uu = ur["run"].get("usb") or {}
    # The owner's file writes FADDR after SET_ADDRESS's status stage (usb_midi.c); fwtest 0.15.0's host checks it
    # after that stage, so no problem is expected.
    if ur["run"]["outcome"] != "completed" or hexv(uu.get("vendor")) != 0x1209 or uu.get("configuration") != 1 \
            or uu.get("problems") or not all(n in usy3 for n in USB_DEVICE_SYMBOLS):
        problems.append("usbmidi: the owner-only release's unit file %s, usb %s, its device symbols %s" % (
            ur["run"]["outcome"], uu, [n for n in USB_DEVICE_SYMBOLS if n in usy3]))
    # The published release has none of it (case release checks the rest: USB alone between the two).
    cb = os.path.join(work, "build-unit")
    build(cb, log, *R_PUB)
    usy = fws.elf_symbols(os.path.join(cb, "app-pkg.elf"))
    found = [n for n in USB_DEVICE_SYMBOLS if n in usy]
    if found:
        problems.append("usbmidi: the published release's device symbols %s (want none)" % found)
    beats = lambda f: ", ".join("%s %d" % (n, f["usb_at_" + n]) for n in rd.USB_STAGES if f["usb_at_" + n])
    print("usbmidi: packets in (bytes, events) %s; out %s" % (rx_pk, pairs))
    print("usbmidi: the give-up test: %s at %s index %d, stages %s, no connection: %s, the panel's note %d; the log:"
          " USB records %s, step 6 to SIEIE %d beats; %s; KEY7 and KEY8: spacing %s units, %s" % (
              rd.USB_WHYS.get(stop["usb_giveup_why"]), rd.USB_STAGES[stop["usb_giveup_stage"]],
              stop["usb_giveup_index"], g_reached, not gu.get("vendor"), g_panel, usb_labels, step6_to_sieie,
              " / ".join(lines[1:2] + lines[-1:]), kl.get("usb_gap_units"),
              rd.u3u_lines(kl)[-1] if "usb_magic" in kl else "no record"))
    print("usbmidi: enumerated %s:%s, %r / %r, serial %r, address %s (written late %d), endpoints out %s in %s, %d"
          " events received, %d sent; stages (beat) %s; the host's note peaks %d; the panel's note %s; the cable"
          " reading %d checks, bits 16-17 set in %d of %d reads (with --usb's host: 0); read back CON0"
          " %08X CON1 %08X IO CON0 %08X; port accesses %d, most polls %d; without --usb: USB not started (state %d,"
          " %d resets), outputs as build A: %s; the owner-only release's unit file: %s, enumerated %s:%s configuration %s,"
          " problems %s; the published release: none of %s" % (
              u.get("vendor"), u.get("product"), u.get("manufacturer"), u.get("product_name"), u.get("serial"),
              u.get("address"), rec["usb_addr_late"], u.get("midi_out_endpoint"), u.get("midi_in_endpoint"),
              u.get("events_received", 0), u.get("events_sent", 0), beats(rec), host, ons[:1] + offs[:1],
              rec["usb_cable_checks"], rec["usb_lines_set"], rec["usb_lines_reads"], rec["usb_rb_con0"],
              rec["usb_rb_con1"], rec["usb_rb_io_con0"], rec["usb_accesses"], rec["usb_polls_max"],
              off["usb_state"], off["usb_resets"], same_wav and same_midi, ur["run"]["outcome"], uu.get("vendor"),
              uu.get("product"), uu.get("configuration"), uu.get("problems"), ", ".join(USB_DEVICE_SYMBOLS)))
    return problems


def case_nowrace(a, work, log):
    """sb_now() never goes back: the slot interrupt's time-keeping forced
    at each point between its reads, just after TIMER0 wraps (main.c,
    SB_TEST_NOW_RACE); 200 runs, no reading earlier than the one before."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, *R_PUB, *FW_WINDOW, "--define", "SB_TEST_NOW_RACE")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_now_test"]
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "3000", "--ram", "0x%08x:28@end" % h)
    done, runs, *backs = struct.unpack("<7I", ram(out, h, 28))
    if r["run"]["outcome"] != "completed" or (done, runs) != (1, 200) or any(backs):
        problems.append("nowrace: %s, done %d, runs %d, readings that went back by point %s (done, 200, none)"
                        % (r["run"]["outcome"], done, runs, backs[1:]))
    print("nowrace: the slot's time-keeping forced at each of sb_now()'s four points, %d runs: %s readings went back"
          % (runs, sum(backs)))
    return problems


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


# --- Round 3 (clean-r3-store) -------------------------------------------------------------------------------------

R3_ENC_SELECT, R3_ENC_KNOB2 = 0, 3          # fwtest's encoders of SELECT and KNOB2 (input.c's table)
R3_KEY = {"oct-": 0, "oct+": 1, "sel": 3, "env": 4, "edit": 6, "glo": 7, "home": 8, "save": 9, "arp": 10,
          "key1": 14, "key16": 29, "pit": 29, "glide": 31}   # fwtest's key numbers (input.h); KEY16 is also PIT
R3_GOLDEN = os.path.join(ROOT, "tests", "seams", "screens")
R3_HOLD_FW = 300                    # hw_test_store.c's HOLD_MS with SB_TEST_SHORT_HOLD (beats)
R3_STACK_FLOOR = 512                # section 5's floor, bytes unused on each stack


def store_tools():
    spec = importlib.util.spec_from_file_location("store_py", os.path.join(ROOT, "tools", "store.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    spec = importlib.util.spec_from_file_location("fm_patch", os.path.join(ROOT, "tools", "fm_patch.py"))
    f = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f)
    return m, f


def r3_full_region():
    """A store region as full as the base's records make it, and as the owner's unit may hold it: every user slot
    (the test patches, renamed), 40 writes of start3b's power-on counter (kind 0xF0, HW-133), then the selection
    written until the ring has gone round more than once."""
    st, fp = store_tools()
    pats = [fp.encode(p) for p in fp.TEST_PATCHES]
    s = st.Store()
    for n in range(16):
        b = bytearray(pats[n % len(pats)])
        b[4:16] = (b"USER %02d" % (n + 1)).ljust(12, b"\0")
        b[110:112] = struct.pack("<H", fp.fletcher16(bytes(b[:110])))
        s.put(st.PATCH, n, 2, bytes(b))
    for n in range(40):
        s.put_fw(0xF0, 0, 1, struct.pack("<I", n + 1))
    for n in range(400):
        s.put(st.SELECTION, 0, 1, bytes([n % 9, 0, 0, 0]))
    img = st.Image(s.chip())
    return s.chip(), sum(1 for k in img.keys if k), st


def strokes(rows, box, scale):
    """Pixels in box (x0, y0, x1, y1) that aren't black and whose run of the same colour, across or down, is
    shorter than scale: text drawn smaller than scale shows as such runs."""
    x0, y0, x1, y1 = box
    bad = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = rows[y][x][:3]
            if c == (0, 0, 0):
                continue
            a = b = x
            while a > x0 and rows[y][a - 1][:3] == c:
                a -= 1
            while b + 1 < x1 and rows[y][b + 1][:3] == c:
                b += 1
            u = v = y
            while u > y0 and rows[u - 1][x][:3] == c:
                u -= 1
            while v + 1 < y1 and rows[v + 1][x][:3] == c:
                v += 1
            if b - a + 1 < scale or v - u + 1 < scale:
                bad += 1
    return bad


# The release's screens (views.c's large layout): where text is, and its least scale.
R3_TITLE, R3_KEYS, R3_MSG, R3_STRIP = (0, 0, 240, 25), (0, 142, 240, 176), (0, 176, 240, 202), (0, 204, 240, 240)
R3_SCREENS = [   # (name, ms, the body's text boxes at scale 2)
    ("patch", 1500, [(124, 26, 240, 99)]),
    ("edit", 2600, []),
    ("edit-level", 3300, []),
    ("edit-page2", 4000, []),
    ("env", 4700, [(0, 26, 240, 43)]),
    ("pitch", 5600, [(0, 26, 240, 43)]),
    ("glide", 6500, [(0, 26, 240, 43)]),
    ("settings", 7200, [(0, 26, 240, 142)]),
    ("arp", 9300, [(0, 26, 240, 142)]),
    ("save-held", 10200, []),
    ("saved", 11000, []),
]


def r3_tour_script(path):
    k = R3_KEY
    with open(path, "w") as f:
        f.write("200 key %d tap 80\n" % k["key1"])
        f.write("2000 key %d tap 80\n2700 enc %d -3\n3400 enc %d +1\n" % (k["edit"], R3_ENC_KNOB2, R3_ENC_SELECT))
        f.write("4100 key %d tap 80\n" % k["env"])
        f.write("4800 key %d down\n4850 key %d tap 80\n5000 key %d up\n" % (k["sel"], k["pit"], k["sel"]))
        f.write("5700 key %d down\n5750 key %d tap 80\n5900 key %d up\n" % (k["sel"], k["glide"], k["sel"]))
        f.write("6600 key %d tap 80\n7300 key %d tap 1600\n" % (k["glo"], k["arp"]))
        f.write("9400 key %d tap 80\n9800 key %d down\n10300 key %d tap 80\n10500 key %d up\n" % (
            k["home"], k["save"], k["key1"], k["save"]))


def case_screens(a, work, log):
    """screens (round 3, clean-r3-store, section 2): the published release's screens in large text, each against
    its golden image (tests/seams/screens; SEAMS_REGOLD=1 writes them): the patch view, the operator view's pages
    and a level turned (the value large in the event line), the envelope, pitch and glide views, the settings, the
    ARP screen, SAVE held (how to save) and "SAVED 1". On each: the title at scale 3 or more, the keys' lines and
    the strip at 2 or more, the event line at 3, and the body's text at 2 (no run of a colour shorter than the
    scale)."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, *(R_PUB + FW_WINDOW))
    script = os.path.join(work, "tour.script")
    r3_tour_script(script)
    out = os.path.join(work, "tour")
    lcd = []
    for _, ms, _ in R3_SCREENS:
        lcd += ["--lcd", str(ms)]
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "11500", "--script", os.path.relpath(script, ROOT),
               *lcd)
    if r["run"]["outcome"] != "completed":
        return ["screens: %s" % r["run"]["outcome"]]
    regold = os.environ.get("SEAMS_REGOLD") == "1"
    os.makedirs(R3_GOLDEN, exist_ok=True)
    for name, ms, body in R3_SCREENS:
        png = os.path.join(out, "lcd-%dms.png" % ms)
        gold = os.path.join(R3_GOLDEN, name + ".png")
        _, _, rows = fws.read_png(png)
        if regold or not os.path.exists(gold):
            shutil.copy(png, gold)
            if not regold:
                problems.append("screens %s: no golden image; written to %s, check it" % (name, gold))
        else:
            _, _, want = fws.read_png(gold)
            diff = sum(1 for y in range(240) for x in range(240) if rows[y][x][:3] != want[y][x][:3])
            if diff:
                shutil.copy(png, os.path.join(work, name + "-got.png"))
                problems.append("screens %s: %d pixels differ from its golden image" % (name, diff))
        for box, scale in [(R3_TITLE, 3), (R3_KEYS, 2), (R3_MSG, 3), (R3_STRIP, 2)] + [(x, 2) for x in body]:
            n = strokes(rows, box, scale)
            if n:
                problems.append("screens %s: %d pixels in %s drawn smaller than scale %d" % (name, n, box, scale))
        if not any(rows[y][x][:3] != (0, 0, 0) for y in range(142, 176) for x in range(240)):
            problems.append("screens %s: no keys named" % name)
    print("screens: %d screens of the published release against their goldens; title and event line at scale 3,"
          " every other word and number at 2" % len(R3_SCREENS))
    return problems


def r3_summary(rd, flash):
    rs, bad = rd.records(flash)
    s = [x for x in rs if x["label"] == "Summary"]
    return rs, bad, (s[-1]["fields"] if s else {})


def case_store_release(a, work, log):
    """storerel (round 3, clean-r3-store, section 1): the release starts the store. From an erased region: read,
    nothing loaded, no problem. SAVE with KEY1: "SAVED 1"; at the next start slot 1 is loaded. From a full region
    (every slot, start3b's counter writes, the selection round the ring): all 16 slots loaded, the store's stage
    in the summary, ready well under a second (R_READY_US_MAX on fwtest's clock). With the code window's
    registers not kept (no SB_TEST_HW_WINDOW: the take refused), the store isn't read: "Store not read" in the
    log and "NO FLASH" for a save."""
    problems = []
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *(R_OWN + FW_WINDOW))
    k = R3_KEY
    path = os.path.join(work, "save.script")
    with open(path, "w") as f:
        f.write("200 key %d tap 80\n1000 key %d down\n1300 key %d tap 80\n1600 key %d up\n" % (
            k["key1"], k["save"], k["key1"], k["save"]))
    o1 = os.path.join(work, "save")
    r1 = fwtest(os.path.join(b, "app.bin"), o1, log, "--ms", "3500", "--flash-out", "--script",
                os.path.relpath(path, ROOT))
    _, bad1, f1 = r3_summary(rd, read_bytes(os.path.join(o1, "flash.bin")))
    o2 = os.path.join(work, "again")
    r2 = fwtest(os.path.join(b, "app.bin"), o2, log, "--ms", "2500", "--flash-out", "--flash",
                os.path.relpath(os.path.join(o1, "flash.bin"), ROOT))
    rs2, bad2, f2 = r3_summary(rd, read_bytes(os.path.join(o2, "flash.bin")))
    if r1["run"]["outcome"] != "completed" or bad1 or f1.get("store_up") != 1 or f1.get("inst_problems") \
            or f1.get("store_loaded", 0) >> 8:
        problems.append("storerel erased: %s, %d bad, store_up %s, problems %s, loaded %s" % (
            r1["run"]["outcome"], len(bad1), f1.get("store_up"), f1.get("inst_problems"), f1.get("store_loaded")))
    if r2["run"]["outcome"] != "completed" or bad2 or not f2.get("store_loaded", 0) >> 8 & 1 \
            or f2.get("store_saves"):
        problems.append("storerel read-back: %s, %d bad, loaded %s (want slot 1)" % (
            r2["run"]["outcome"], len(bad2), f2.get("store_loaded")))
    chip, live, st = r3_full_region()
    full = os.path.join(work, "full.bin")
    with open(full, "wb") as f:
        f.write(chip)
    o3 = os.path.join(work, "full")
    r3 = fwtest(os.path.join(b, "app.bin"), o3, log, "--ms", "2500", "--flash-out", "--flash",
                os.path.relpath(full, ROOT))
    _, bad3, f3 = r3_summary(rd, read_bytes(os.path.join(o3, "flash.bin")))
    ready = f3.get("inst_at_ready_us", 0)
    stage = f3.get("inst_at_audio_us", 0) - f3.get("inst_at_store_us", 0)
    if r3["run"]["outcome"] != "completed" or bad3 or f3.get("store_loaded", 0) >> 8 != 0xFFFF \
            or f3.get("store_valid_sectors") != st.SECTORS or not 0 < ready < R_READY_US_MAX or f3.get("inst_problems"):
        problems.append("storerel full: %s, %d bad, loaded %s, sectors %s, ready %d us, store stage %d us, problems %s"
                        % (r3["run"]["outcome"], len(bad3), f3.get("store_loaded"), f3.get("store_valid_sectors"),
                           ready, stage, f3.get("inst_problems")))
    nb = os.path.join(work, "build-nowin")
    build(nb, log, *R_PUB)
    o4 = os.path.join(work, "nowin")
    r4 = fwtest(os.path.join(nb, "app.bin"), o4, log, "--ms", "3500", "--flash-out", "--script",
                os.path.relpath(path, ROOT), "--lcd", "3400")
    rs4, _, f4 = r3_summary(rd, read_bytes(os.path.join(o4, "flash.bin")))
    # Without the window's registers the log can't write either (its take is the same): read the store's state from
    # the beacon-free side, the screen's event line.
    labels4 = [x["label"] for x in rs4]
    if r4["run"]["outcome"] != "completed" or labels4:
        problems.append("storerel no window: %s, records %s (none: neither the store nor the log takes the flash)"
                        % (r4["run"]["outcome"], labels4))
    print("storerel: erased region read, nothing loaded; slot 1 saved and loaded at the next start; a full region"
          " (%d live records, %d sectors) read in %d us of fwtest's clock, ready at %d us; without the window's"
          " registers nothing is written" % (live, f3.get("store_valid_sectors", 0), stage, ready))
    return problems


def r3_verdict(rd, flash):
    rs, _ = rd.records(flash)
    v = [x["label"] for x in rs if x["label"].startswith("Slot16")]
    return v[-1] if v else None


R3_SOAK_CUTS = 6


def case_soak(a, work, log):
    """soak (round 3, clean-r3-store, section 3): the test file's save soak. SAVE and KEY16 held (the hold a tenth
    as long in fwtest's build) save slot 16 again and again, A and B in turn; the power is cut in the soak at
    points spread over its erases and programs (just after one starts, halfway, just before it ends, between two),
    and each next start shows slot 16 as A or B, never broken; the first start shows it empty."""
    problems = []
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *T_DEFINES)
    k = R3_KEY
    path = os.path.join(work, "soak.script")
    hold_at = 13000
    with open(path, "w") as f:
        f.write("%d key %d down\n%d key %d down\n" % (hold_at, k["save"], hold_at + 100, k["key16"]))
    o = os.path.join(work, "log")
    r = fwtest(os.path.join(b, "app.bin"), o, log, "--power-cut", "16000", "--flash-out", "--flash-log", "--script",
               os.path.relpath(path, ROOT))
    first = r3_verdict(rd, read_bytes(os.path.join(o, "flash.bin")))
    ops = []
    with open(os.path.join(o, "flash-ops.csv")) as f:
        for row in csv.DictReader(f):
            if int(row["offset"], 16) >= 0xFC000 and float(row["start_ms"]) > hold_at + 1000:
                ops.append((float(row["start_ms"]), float(row["end_ms"]), row["command"]))
    if not ops or first != "Slot16 empty":
        return ["soak: %d store commands in the soak, first verdict %s" % (len(ops), first)]
    erases = [x for x in ops if x[2] == "20"]
    picks = []
    if erases:
        e = erases[0]
        picks += [e[0] + 0.001, (e[0] + e[1]) / 2]
    p = ops[len(ops) // 2]
    picks += [p[0] + 0.001, (p[0] + p[1]) / 2, p[1] - 0.001]
    nxt = ops[ops.index(p) + 1] if ops.index(p) + 1 < len(ops) else None
    if nxt:
        picks.append((p[1] + nxt[0]) / 2)
    seen = []
    for i, t in enumerate(sorted(picks)[:R3_SOAK_CUTS]):
        oc = os.path.join(work, "cut%d" % i)
        rc = fwtest(os.path.join(b, "app.bin"), oc, log, "--power-cut", "%.3f" % t, "--flash-out", "--script",
                    os.path.relpath(path, ROOT))
        on = os.path.join(work, "next%d" % i)
        rn = fwtest(os.path.join(b, "app.bin"), on, log, "--ms", "8000", "--flash-out", "--flash",
                    os.path.relpath(os.path.join(oc, "flash.bin"), ROOT))
        v = r3_verdict(rd, read_bytes(os.path.join(on, "flash.bin")))
        seen.append((round(t, 3), rc["run"].get("detail", ""), v))
        if rc["run"]["outcome"] != "power-cut" or rn["run"]["outcome"] != "completed" or v not in ("Slot16 A",
                                                                                                    "Slot16 B"):
            problems.append("soak cut at %.3f ms (%s): next start %s, verdict %s" % (
                t, rc["run"].get("detail"), rn["run"]["outcome"], v))
    print("soak: %d store commands in 3 s of soak (%d erases); cuts and verdicts: %s" % (
        len(ops), len(erases), "; ".join("%s ms %s" % (t, v) for t, _, v in seen)))
    return problems


def case_fault(a, work, log):
    """fault (round 3, clean-r3-store, section 4): the red screen with its cause and address in large text. The
    test file's trap (OCT- and OCT+ held, the hold a tenth as long in fwtest's build): a halt, the screen red, its
    text at scale 3 ("STRAY IRQ", the source, the address) and 2. A release built to fault while a save has the
    flash taken (SB_TEST_FAULT_TAKEN, the code window off): the same red screen, drawn from RAM."""
    problems = []
    fws = fw_suite()
    k = R3_KEY
    path = os.path.join(work, "trap.script")
    with open(path, "w") as f:
        f.write("13000 key %d down\n13050 key %d down\n" % (k["oct-"], k["oct+"]))
    b = os.path.join(work, "build-test")
    build(b, log, *T_DEFINES)
    spath = os.path.join(work, "save.script")
    with open(spath, "w") as f:
        f.write("200 key %d tap 80\n1000 key %d down\n1300 key %d tap 80\n1600 key %d up\n" % (
            k["key1"], k["save"], k["key1"], k["save"]))
    rb = os.path.join(work, "build-taken")
    build(rb, log, *(R_PUB + FW_WINDOW + ("--define", "SB_TEST_FAULT_TAKEN")))
    for name, img, script, ms in (("trap", b, path, 15000), ("taken", rb, spath, 4000)):
        out = os.path.join(work, name)
        r = fwtest(os.path.join(img, "app.bin"), out, log, "--ms", str(ms), "--script", os.path.relpath(script, ROOT),
                   "--lcd", "end")
        _, _, rows = fws.read_png(os.path.join(out, "lcd-end.png"))
        red = sum(1 for y in range(240) for x in range(240) if rows[y][x][:3] == (255, 0, 0))
        white = sum(1 for y in range(0, 150) for x in range(240) if rows[y][x][:3] == (255, 255, 255))
        small = sum(strokes([[(0, 0, 0) if p[:3] == (255, 0, 0) else p for p in row] for row in rows], box, s)
                    for box, s in (((0, 0, 240, 150), 3), ((0, 150, 240, 240), 2)))
        if r["run"]["outcome"] != "halt" or red < 40000 or white < 1500 or small:
            problems.append("fault %s: %s, %d red pixels, %d white in the large text, %d drawn small" % (
                name, r["run"]["outcome"], red, white, small))
        shutil.copy(os.path.join(out, "lcd-end.png"), os.path.join(work, name + ".png"))
    print("fault: the trap and a fault with the flash taken each end on the red screen, its cause and address at"
          " scale 3")
    return problems


def case_stack(a, work, log):
    """stack (round 3, clean-r3-store, section 5): the owner-only release's stacks at their worst in fwtest: notes
    from the panel and from the host over USB while a save is written, then another. Each stack keeps at least
    512 bytes unused (R3_STACK_FLOOR), and the log holds the summary alone (no underrun from the saves' give-backs,
    whose cache clear runs with interrupts off); the same run without the saves says what the store takes from
    each."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *(R_OWN + FW_WINDOW))
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    lo, mid, hi = sy["__stack_limit"], sy["__irq_stack_top"], sy["__stack_top"]
    k = R3_KEY
    got = {}
    for name, saves in (("plain", False), ("saves", True)):
        path = os.path.join(work, name + ".script")
        with open(path, "w") as f:
            f.write("3000 usbmidi 09 90 3c 64\n3000 usbmidi 09 90 40 64\n3000 usbmidi 09 90 43 64\n")
            f.write("3100 key %d down\n3120 key %d down\n3140 key %d down\n" % (k["key1"] + 2, k["key1"] + 4,
                                                                               k["key1"] + 7))
            for i in range(20):
                f.write("%d usbmidi 09 90 %02x 50\n%d usbmidi 08 80 %02x 00\n" % (3200 + 50 * i, 0x30 + i,
                                                                                  3225 + 50 * i, 0x30 + i))
            if saves:
                f.write("3300 key %d down\n3400 key %d tap 80\n3700 key %d up\n" % (k["save"], k["key1"], k["save"]))
                f.write("3800 key %d down\n3900 key %d tap 80\n4200 key %d up\n" % (k["save"], k["key1"] + 1,
                                                                                   k["save"]))
            f.write("4600 key %d up\n4620 key %d up\n4640 key %d up\n" % (k["key1"] + 2, k["key1"] + 4,
                                                                         k["key1"] + 7))
        out = os.path.join(work, name)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--usb", "--ms", "5500", "--flash-out", "--script",
                   os.path.relpath(path, ROOT), "--ram", "0x%08x:%d@end" % (lo, hi - lo))
        # The saves' give-backs (interrupts off while the cache is cleared) make no underrun, and nothing else is
        # wrong: the summary alone in the log.
        labels = [x["label"] for x in rd.records(read_bytes(os.path.join(out, "flash.bin")))[0]]
        if labels != ["Summary"]:
            problems.append("stack %s: records %s (want the summary alone)" % (name, labels))
        data = ram(out, lo, hi - lo)
        w = struct.unpack("<%dI" % ((hi - lo) // 4), data)
        irq = next((i for i, v in enumerate(w[:(mid - lo) // 4]) if v != 0x4B415453), (mid - lo) // 4) * 4
        main = next((i for i, v in enumerate(w[(mid - lo) // 4:]) if v != 0x4B415453), (hi - mid) // 4) * 4
        got[name] = (main, irq)
        if r["run"]["outcome"] != "completed" or main < R3_STACK_FLOOR or irq < R3_STACK_FLOOR:
            problems.append("stack %s: %s, unused main %d, irq %d (floor %d)" % (
                name, r["run"]["outcome"], main, irq, R3_STACK_FLOOR))
    took = (got["plain"][0] - got["saves"][0], got["plain"][1] - got["saves"][1])
    print("stack: unused bytes, main %d and interrupts %d with the saves (%d and %d without): the store took %d"
          " from main's stack and %d from the interrupts'" % (got["saves"] + got["plain"] + took))
    return problems


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
    ("report1", case_report1),
    ("nowrace", case_nowrace),
    ("release", case_release),
    ("test", case_test),
    ("usbmidi", case_usbmidi),
    ("screens", case_screens),
    ("storerel", case_store_release),
    ("soak", case_soak),
    ("fault", case_fault),
    ("stack", case_stack),
]


# Each case's measured time in seconds, for --shard (CI's seams parts): the cases are taken longest first and dealt
# out in turn (shard_cases), so the parts take about as long. A case not listed counts as CASE_SECONDS_DEFAULT. Measured from the
# "seams case" lines a run prints; update them when a case's time changes much.
# Measured on CI (#254, run 45751696587, fwtest 0.14.0); round 2's release, test and report1 estimated from local
# runs (about three times CI's) until their CI times are in; round 3's soak, fault, storerel, screens and stack
# likewise.
CASE_SECONDS = {
    "soak": 300, "fault": 50, "storerel": 30, "screens": 15, "stack": 15,
    "powercut": 194, "usbmidi": 119, "test": 90, "release": 50, "report1": 30, "hw": 20, "panel": 19, "light":
    18, "flags": 14, "ownbase": 9, "outside": 8, "region": 8, "nostart": 6, "nowrace": 5, "engine": 5, "store":
    5, "parts": 4, "platform": 3, "sysex": 3, "rawout": 3, "probe": 2,
}
CASE_SECONDS_DEFAULT = 60


def shard_cases(k, n):
    """The case names part k of n runs: the cases longest first by CASE_SECONDS, each given to the part with the
    least time so far (the first such part on a tie), so the parts take about as long."""
    names = [name for name, _ in CASES]
    ranked = sorted(names, key=lambda x: (-CASE_SECONDS.get(x, CASE_SECONDS_DEFAULT), names.index(x)))
    load, part = [0] * n, {}
    for x in ranked:
        p = load.index(min(load))
        part[x] = p
        load[p] += CASE_SECONDS.get(x, CASE_SECONDS_DEFAULT)
    return {x for x, p in part.items() if p == k - 1}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--shard", help="k/n: run part k of n (CI's seams parts), the cases spread by their measured times")
    a = ap.parse_args()
    shard = None
    if a.shard:
        k, n = (int(x) for x in a.shard.split("/"))
        if not 1 <= k <= n:
            ap.error("--shard k/n wants 1 <= k <= n")
        shard = shard_cases(k, n)
    a.build = os.path.abspath(a.build)
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    failed = []
    for name, fn in CASES:
        if a.only and name not in a.only:
            continue
        if shard is not None and name not in shard:
            continue
        work = os.path.join(out, name)
        os.makedirs(work)
        log = os.path.join(work, "log.txt")
        t0 = time.time()
        try:
            problems = fn(a, work, log)
        except RuntimeError as e:
            problems = [str(e)]
        print("seams case %s: %.0fs" % (name, time.time() - t0), flush=True)
        for p in problems:
            print("  FAIL %s: %s" % (name, p))
        if problems:
            failed.append(name)
    print("seams suite%s: %s" % (" part " + a.shard if a.shard else "",
                                  "FAIL (%s)" % ", ".join(failed) if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
