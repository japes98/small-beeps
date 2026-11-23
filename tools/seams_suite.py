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
- core1 (BR-17, clean-br17-core1): core 1's release, since
  clean-br17-encoders B's (HW-135's steps 1 and 3: C1_CON bit 3 set and
  bit 1 cleared, SYS_DIV never written; the unit showed it starts core 1),
  is checked in hw3's held run (core 1's own flag seen, its counter
  running); this case builds start3c's A, SB_HW_CORE1_SYSDIV (SYS_DIV bit
  3 set and put back as read), and checks that too.
  fwtest starts core 1 at either step (HW-10), so neither run tells which
  the chip needs.
- finder (BR-17, clean-br17-finder): the knob finder, SB_HW_FINDER, with
  SB_TEST_HW_WINDOW: PLAY's press shows as its matrix cell (column 10,
  PA6), one detent of fwtest's encoder 2 as two cells (columns 8 and 9,
  PA5), each closed and opened once, and the pot as channel 4 from 900 to
  300; nothing is marked noisy or lost.
- audio1 (BR-17, clean-br17-audio1): the audio probe, SB_HW_AUDIO1 with
  SB_TEST_HW_WINDOW and the short hold: ALNK0 plays the 440 Hz tone
  into audio.wav, both channels alike, below -20 dBFS, with no click,
  stopped and started again by PLAY; the halves, timed against TIMER0,
  give fwtest's 44 117.6 frames a second within 0.02 % once fwtest's
  24 MHz TIMER0 is allowed for (HW_RATIO; fwtest's acknowledge restarts
  the count, HW-48, which reads about 80 ppm high); ALNK0's CON0 bit 11
  reads clear at main's start and set with the tone on; HOME shows the
  page again; nothing unmodelled but the window's, corex2's and DAC_CON
  (and, read by HOME's fifth view since audio4, JL_GPCNT's and ALNK1's).
- audio2 (BR-17, clean-br17-audio2): the same build with REC pressed
  twice: CLK_CON2 bit 9 set alone, then CLK_CON2 put back exactly as
  read; CLK_CON2 has no effect in fwtest (HW-53), so the tone plays on in
  both channels at 440 Hz and 44 117.6 frames a second; REC shows the
  page; nothing unmodelled but the window's, corex2's and DAC_CON. Since
  clean-br17-audio3, with bit 9 taken: ARP's step A (CON0 bit 11 cleared
  and set again) and its undo, then SAVE's step B (CLK_CON2 bit 8 alone)
  and its undo, each undo putting back the value read before; the tone
  plays on.
- audio3 (BR-17, clean-br17-audio3): the same build with SEQ pressed
  twice: ALNK0's CON0 bit 11 cleared alone, then CON0 put back exactly as
  read; no half is taken while it is stopped, and the tone plays again at
  440 Hz after; core 1's count, in its own 64-byte block, rises through
  every fixed point (its release, around audio_start, around the key's
  write, on the page), whose beats run in order; the page reaches its
  core 1 view; ARP without bit 9 is refused, nothing written; nothing
  unmodelled but the window's, corex2's and DAC_CON.
- audio4 (BR-17, clean-br17-audio4): report1's build with steps H and I:
  ENV (H: CLK_CON1 bits 4-6 set to 3, then 5, those bits alone, the
  counter set and read), REC, FX (H again), LFO (I: ALNK1 started,
  CLK_CON2 bit 11 alone), SEL (bit 10 alone), REC's undo refused while I
  is taken, then I's, REC's and H's undos, each putting back the values
  read before; the log holds a record for each, in order, the last
  matching RAM; each step key's LED is lit while its step is taken
  (leds1). fwtest models neither JL_GPCNT nor ALNK1 (their registers
  read 0: the counter's gates time out, ALNK1 doesn't play), which the case
  prints; if a later fwtest plays ALNK1, its halves a second must fit
  44 117.6 frames.
- audio5 (BR-17, clean-br17-audio5): report1's build with steps K and J:
  GLO's K measures the clock system's inputs 3, 1, 5, 6 and 7, the
  counter's 480 MHz and input 5 with the DAC's clock choice 1, 2, 3 and
  as read (CLK_CON1 bits 4-6 and 2-3 alone), and its undo puts CLK_CON1
  and the counter back; with ALNK0 stopped (SEQ) OCT+'s J sweeps ALNK0's
  CON1 bits 0-15 and CON3 bits 0-7, each alone, put back and logged; a
  second sweep is aborted by a press; with ALNK0 running again the sweep
  stops at its first try, which moves the link, and a press puts it
  back (in fwtest that bit sets off a burst of source 11, and the guard
  stops the output); the tone plays at 440 Hz and 44 117.6 frames a
  second after the sweeps, before that try. Whether fwtest stores CON1
  and CON3 is printed.
- audio6 (BR-17, clean-br17-audio6): step D. With ALNK0 stopped (SEQ),
  OCT-'s sweep of JL_IOMAP->CON5's 32 bits, with bit 9 set and again
  clear: each try logged before its write and after, CON5 put back as
  read by the firmware, the matrix check passing with the bit set and
  after the undo; with ALNK0 running again (fwtest's link moves), the
  sweep stops at bit 0 with the bit kept and the matrix right, and a press
  puts CON5 back; the tone plays at 440 Hz and 44 117.6 frames a second.
  A test build (SB_TEST_D_CHECK_FAIL) fails the check at bit 2: the
  firmware undoes that try itself and stops the sweep there. (Since
  audio7 the ring holds 96 records: the first sweep's have gone by the
  end, so the second and third are read from the log.)
- audio7 (BR-17, clean-br17-audio7): set-ups L1 (KEY1) and L2 (KEY2),
  HW-157's fields written to ALNK0's CON3, CON1 and CON0: L1, bit 9, L2,
  bit 9's undo, L2, each logged before its writes and after; fwtest's
  link runs through each (fwtest stores CON1 and CON3), so each is kept
  with the matrix right, its halves timed (frames a second by both LEN
  readings, fwtest's at 44 117.6) and the expected rates logged, and
  its key puts CON0, CON1 and CON3 back as read; the guide follows the
  table, a kept set-up's undo first; the tone plays on. A test build
  (SB_TEST_L_CHECK_FAIL) fails L1's check: the firmware puts it back
  and takes no further set-up.
- nowrace (BR-17, after audio5): the hardware build's sb_now() never
  goes back. A test build (SB_TEST_NOW_RACE) makes the slot interrupt's
  time-keeping (its acknowledge and its count) happen at each point
  between sb_now()'s reads just after TIMER0 has wrapped, 50 times at
  each of the four, and every reading is no earlier than the one before
  it. (Until the fix the wrap flag was read after the loop: an interrupt
  there put the time one slot back, which a busy wait read as a timeout.)
- report1 (BR-17, clean-br17-report1): the report log, SB_HW_REPORT with
  audio1's build. From a chip whose log region holds older data (as the
  owner's unit does): the records of boot, each page, REC, ARP and its
  undo and the save key (EDIT), numbered 1 on in consecutive slots, each
  sector erased before its first record and the rest left as they were;
  tools/report_decode.py reads them back, and the last record's fields
  match the probe's state in RAM. A second run from that chip numbers on
  after the newest; a run from a full ring erases the oldest sector and
  keeps the rest. A write that fails its check (SB_TEST_LOG_VERIFY_FAIL)
  is kept in the log's own fields and written again in the next slot
  under the same number, and the decoder lists the failed one.
- hw (BR-17, Phase B): the FM-1 hardware build, SB_HW_FM1 (R-HW-1). In
  fwtest, where its one timer, TIMER0, counts 24 MHz rather than the
  chip's 60 MHz (HW-119), so its beats are 2.5 times slow: the screen goes
  black, then bands 1, 2 and 3 appear in that order on black, then the
  address pattern with band 4 over it; at the end the test screen, no halt, the beats as
  2.5 times slow predicts; PLAY (fwtest's key 12) pressed and released is
  named on the screen, and its LED is lit for its column's slot (one in 14) while
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
    # One slot in 14 since clean-br17-presets (13 columns and slot 0): 71.
    if not press or not after or not 60 <= press[HW_LED] <= 85 or any(v for i, v in enumerate(press) if i != HW_LED) \
            or any(after):
        problems.append("hw: LEDs while PLAY is held %s, after %s (LED %d at about 1000 / 14 alone, then none)"
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


def case_hw3(a, work, log):
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h3, c1 = sy["hw3"], sy["hw_core1_count"]
    script = os.path.join(b, "press.script")
    with open(script, "w") as f:
        f.write("3000 key %d down\n3800 key %d up\n4600 pot 300\n5400 enc 4 +1\n" % (HW_LED, HW_LED))

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

    out, e, core1 = run("first", 6000, "--script", os.path.relpath(script, ROOT), "--lcd", "4400", "--lcd", "5200",
                        "--lcd", "end")
    # MASTER (channel 4, HW-133) moved to 300 at 4.6 s: the event line,
    # which named PLAY's release before it, names it after. Then one detent
    # of fwtest's encoder 4 (KNOB3, row 0: PA0, clean-br17-encoders) at
    # 5.4 s, named after it in yellow. (The unit's PRESETS, PB7 at columns
    # 11 and 12, has no counterpart in fwtest, whose encoder 6 is at 0 and
    # 1: clean-br17-presets.)
    _, _, before = fws.read_png(os.path.join(out, "lcd-4400ms.png"))
    _, _, mid = fws.read_png(os.path.join(out, "lcd-5200ms.png"))
    _, _, last = fws.read_png(os.path.join(out, "lcd-end.png"))
    box = [(x, y) for y in range(104, 120) for x in range(26, 214)]
    if all(before[y][x] == mid[y][x] for x, y in box) or not any(mid[y][x] == (255, 255, 255) for x, y in box):
        problems.append("first: MASTER's move not named on the test screen's event line")
    if not any(last[y][x] == (255, 255, 0) for x, y in box):
        problems.append("first: KNOB3's detent (PA0, row 0) not named on the test screen's event line")
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
    hh = fws.elf_symbols(os.path.join(hb, "app.elf"))["hw3"]
    r = fwtest(os.path.join(hb, "app.bin"), hout, log, "--ms", "9000", "--flash-out", "--leds-every", "100",
               "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN),
               "--ram", "0x%08x:%d@end" % (hh, HW3_FULL_LEN))
    bc = fws.beacon(ram(hout, BEACON_ADDR, fws.BEACON_LEN))
    problems += core1_problems("hold", hw3_record(ram(hout, hh, HW3_FULL_LEN, "end")), False)
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


FIND_LINE = ("kind", "col", "port", "bit", "count", "value", "when", "fresh", "dirty", "l0", "l1", "l2", "nlevels")
FIND_LEN = 4 * 5 + 8 * 4 * len(FIND_LINE)    # hw_start3.c, struct hw_finder


def case_finder(a, work, log):
    """The knob finder (SB_HW_FINDER, clean-br17-finder): PLAY's press as
    its matrix cell, one detent of fwtest's encoder 2 as its two cells, the
    pot as channel 4, and nothing marked noisy."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_FINDER",
          "--define", "SB_TEST_SHORT_HOLD")
    hf = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_find"]
    script = os.path.join(b, "finder.script")
    with open(script, "w") as f:
        # HOME opens the finder (clean-br17-encoders); its release falls in
        # the hands-off time, so its own cell may be marked noisy.
        f.write("1500 key 8 down\n1550 key 8 up\n3500 key %d down\n3800 key %d up\n4200 enc 2 +1\n4800 pot 300\n"
                % (HW_LED, HW_LED))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "6000", "--script", os.path.relpath(script, ROOT),
               "--lcd", "end", "--ram", "0x%08x:%d@end" % (hf, FIND_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("finder: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    data = ram(out, hf, FIND_LEN, "end")
    sweeps, rate, learning, noisy, dropped = struct.unpack_from("<5I", data)
    lines = [dict(zip(FIND_LINE, struct.unpack_from("<13I", data, 20 + 52 * i))) for i in range(8)]
    got = {(l["kind"], l["col"], l["port"], l["bit"]): l for l in lines if l["kind"]}
    want = {(2, 10, 0, 6): 2, (2, 8, 0, 5): 2, (2, 9, 0, 5): 2}
    for k, n in want.items():
        if k not in got or got[k]["count"] != n or got[k]["value"]:
            problems.append("finder: cell %s %s (closed and opened %d times, open now)" % (k[1:], got.get(k), n // 2))
    adc = got.get((3, 0, 0, 4))
    if not adc or adc["value"] != 300 or adc["nlevels"] != 1 or adc["l0"] != 900:
        problems.append("finder: channel 4's line %s (300, from 900)" % adc)
    others = set(got) - set(want) - {(3, 0, 0, 4)}
    if others or noisy > 2 or dropped or learning or not sweeps:
        problems.append("finder: other lines %s, noisy %d, lost %d, learning %d, sweeps %d"
                        % (sorted(others), noisy, dropped, learning, sweeps))
    print("finder: PLAY as cell (10, PA6), encoder 2's detent as cells (8, PA5) and (9, PA5), the pot as channel 4"
          " from 900 to 300; nothing noisy or lost; %d sweeps, %d a second" % (sweeps, rate))
    return problems


def case_core1(a, work, log):
    """Core 1's release with SB_HW_CORE1_SYSDIV, start3c's A: HW-135's full
    order, SYS_DIV bit 3 set and put back as read. The default since
    clean-br17-encoders is B's (steps 1 and 3), checked in hw3's held run;
    fwtest starts core 1 at either (HW-10)."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_CORE1_SYSDIV")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw3"]
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "9000", "--lcd", "end",
               "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN), "--ram", "0x%08x:%d@end" % (h, HW3_FULL_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("core1: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS)
    if odd:
        problems.append("core1: unmodelled accesses besides the window's and corex2's: %s" % odd[:8])
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    if bc["screen"] != 2 or bc["halt_reason"]:
        problems.append("core1: screen %d, halt %d (the test screen, no halt)" % (bc["screen"], bc["halt_reason"]))
    w = hw3_record(ram(out, h, HW3_FULL_LEN, "end"))
    problems += core1_problems("core1", w, True)
    print("core1: A (HW-135's full order, SYS_DIV %08x set with bit 3 and put back): core 1's sign seen after %d ms, C1_CON"
          " %08x > %08x > %08x; the test screen reached" % (w["sd_before"], w["c1_wait_ms"], w["c1_pre"],
                                                            w["c1_post"], w["c1_clr1"]))
    return problems


# audio1 (hw_fm1.h, struct hw_audio): the registers at main's start and
# with the tone on, then the probe's counts and measures.
AUD_REGS = 22
AUD_FIELDS = ("regs_read", "started", "seq", "n0_set", "n0", "t0", "n1", "t1", "halves", "units", "fps10",
              "master", "gain", "tone_on", "storm", "flips", "pend")
AUD_LEN = 4 * (2 * AUD_REGS + len(AUD_FIELDS))
AUD_AL0 = 11          # ALNK0's CON0 in the registers' order (hw_audio.c)
AUD_Y = 160           # hw_fm1.h, HW_AUD_Y
AUD_FPS = 24000000 / 544.0   # fwtest's frames a second (HW-45)


def case_audio1(a, work, log):
    """audio1 (SB_HW_AUDIO1, clean-br17-audio1): ALNK0 plays the 440 Hz
    tone into audio.wav, both channels alike, below -20 dBFS, ramped (no
    click), stopped and started again by PLAY; its halves, timed against
    TIMER0, give fwtest's 44 117.6 frames a second (once TIMER0's 24 MHz in
    fwtest is allowed for); CON0's run bit reads set with the tone on and
    clear before; HOME shows the page again; the only unmodelled accesses
    are the window's, corex2's and JL_AUDIO's DAC_CON."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_aud"]
    script = os.path.join(b, "audio1.script")
    with open(script, "w") as f:
        # The page ends about 6.5 s in (beats 2.5 times slow): PLAY stops
        # the tone at 8 s and starts it at 10 s; HOME shows the page at 11 s.
        f.write("8000 key %d down\n8100 key %d up\n10000 key %d down\n10100 key %d up\n11000 key 8 down\n"
                "11100 key 8 up\n" % (HW_LED, HW_LED, HW_LED, HW_LED))
    out = os.path.join(work, "run")
    # 18 s: HOME's page at 11 s shows every view (eight since audio7, a
    # quarter of the short hold's page each), then the test screen.
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "18000", "--wav", "--script", os.path.relpath(script, ROOT),
               "--lcd", "5000", "--lcd", "12000", "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN),
               "--ram", "0x%08x:%d@end" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio1: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    # Since audio4 HOME's fifth view reads ALNK1 and the counter, which fwtest doesn't model (read only).
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS - {"0x00012f00"}
                 - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio1: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1:"
                        " %s" % odd[:8])
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    if bc["screen"] != 2 or bc["halt_reason"]:
        problems.append("audio1: screen %d, halt %d (the test screen, no halt)" % (bc["screen"], bc["halt_reason"]))
    data = ram(out, h, AUD_LEN)
    regs = [list(struct.unpack_from("<%dI" % AUD_REGS, data, 4 * AUD_REGS * i)) for i in range(2)]
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), data, 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6:
        problems.append("audio1: %.1f frames a second on screen, %.1f in fwtest's time (%.1f, within 0.02 %%)"
                        % (e["fps10"] / 10.0, fps, AUD_FPS))
    if (e["regs_read"], e["storm"], e["tone_on"], e["master"]) != (1, 0, 1, 900) or not e["flips"] or not e["halves"]:
        problems.append("audio1: record %s (registers read, no storm, the tone on, MASTER 900, bit 15 flipping)" % e)
    if regs[0][AUD_AL0] & 0x800 or not regs[1][AUD_AL0] & 0x800:
        problems.append("audio1: ALNK0 CON0 %04x at the start, %04x with the tone on (bit 11 clear, then set)"
                        % (regs[0][AUD_AL0], regs[1][AUD_AL0]))
    rate, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    if left != right:
        problems.append("audio1: the channels differ")
    # Loud or not by 10 ms windows; runs of over 0.1 s, in samples.
    loud = [max(abs(v) for v in left[w:w + 441]) > 64 for w in range(0, len(left), 441)]
    runs, k = [], 0
    while k < len(loud):
        j = k
        while j < len(loud) and loud[j] == loud[k]:
            j += 1
        if j - k > 10:
            runs.append((loud[k], 441 * k, 441 * j))
        k = j
    shape = [on for on, _, _ in runs]
    if shape[-3:] != [True, False, True]:
        problems.append("audio1: tone, silence, tone not found (runs over 0.1 s: %s)" % [(o, i, j) for o, i, j in runs])
    else:
        _, i, j = runs[-3]
        fit = aa.sine_fit(left[i + 4410:j - 4410])
        if abs(fit["frequency"] - 440) > 0.5 or not 2000 < fit["amplitude"] < 3277 or aa.thd_n_db(fit) > -50:
            problems.append("audio1: the tone %.2f Hz, %.0f peak, THD+N %.1f dB (440 Hz, below -20 dBFS, under -50 dB)"
                            % (fit["frequency"], fit["amplitude"], aa.thd_n_db(fit)))
    step = max(abs(p - q) for p, q in zip(left, left[1:]))
    if step > 250:
        problems.append("audio1: a step of %d between samples (a click: the ramps keep it under 250)" % step)
    _, _, page = fws.read_png(os.path.join(out, "lcd-12000ms.png"))
    _, _, end = fws.read_png(os.path.join(out, "lcd-end.png"))
    green = (0, 255, 0)
    if not any(page[y][x] == green for y in range(0, 16) for x in range(6, 200)):
        problems.append("audio1: HOME didn't show the page (its IRQ line in green)")
    if not any(end[y][x] == green for y in range(AUD_Y, AUD_Y + 16) for x in range(6, 230)):
        problems.append("audio1: no green audio line on the test screen")
    print("audio1: ALNK0 played 440 Hz in both channels, stopped and started by PLAY, no click; %d halves timed at"
          " %.1f frames a second on screen, %.1f in fwtest's time; CON0 %04x, then %04x; bit 15 flipped %d times"
          % (e["halves"], e["fps10"] / 10.0, fps, regs[0][AUD_AL0], regs[1][AUD_AL0], e["flips"]))
    return problems


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


def case_audio2(a, work, log):
    """audio2 (clean-br17-audio2): audio1's build with the clock step. REC
    sets CLK_CON2 bit 9 alone and a second REC puts back the value read
    before, exactly; CLK_CON2 has no effect in fwtest (HW-53), so the tone
    plays on through both, at fwtest's 44 117.6 frames a second; the new
    registers are read at the start, with the tone on and after each step;
    nothing unmodelled but the window's, corex2's and DAC_CON. Since
    clean-br17-audio3, with bit 9 taken: ARP's step A (CON0 bit 11 cleared
    and set again) and its undo, then SAVE's step B (CLK_CON2 bit 8) and
    its undo, each undo putting back the value read before; the link
    restarts as HW-45 says and the tone plays on."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_aud"]
    script = os.path.join(b, "audio2.script")
    with open(script, "w") as f:
        # After audio1's page (about 7 s), each key's page lasting about
        # 1.5 s: bit 9 at 7.5 s, A at 9.5 s, its undo at 11.5 s, B at
        # 13.5 s, its undo at 15.5 s, bit 9's undo at 17.5 s.
        for t, k in ((7500, HW_REC), (9500, HW_ARP), (11500, HW_ARP), (13500, HW_SAVE), (15500, HW_SAVE),
                     (17500, HW_REC)):
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "22000", "--wav", "--script", os.path.relpath(script, ROOT),
               "--lcd", "8500", "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN),
               "--ram", "0x%08x:%d@end" % (h, AUD3_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio2: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS - {"0x00012f00"})
    if odd:
        problems.append("audio2: unmodelled accesses besides the window's, corex2's and DAC_CON: %s" % odd[:8])
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    if bc["screen"] != 2 or bc["halt_reason"]:
        problems.append("audio2: screen %d, halt %d (the test screen, no halt)" % (bc["screen"], bc["halt_reason"]))
    data = ram(out, h, AUD3_LEN)
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), data, 8 * AUD_REGS)))
    ab = aud_ab(data)
    run = 0x800
    if (ab["a_state"], ab["a_keys"], ab["b_state"], ab["b_keys"], ab["refused"]) != (2, 2, 2, 2, 0) \
            or not ab["a_before"] & run or ab["a_clr"] & run or not ab["a_set"] & run \
            or (ab["a_back"] ^ ab["a_before"]) & ~0x8000 \
            or ab["b_before"] != st_clk_bit9(data) or ab["b_set"] != ab["b_before"] | 0x100 \
            or ab["b_back"] != ab["b_before"]:
        problems.append("audio2: steps A and B %s (A: bit 11 cleared, set, then CON0 as read, bit 15 aside; B: bit 8"
                        " alone, then CLK_CON2 as read)" % {k: "%x" % v for k, v in ab.items()})
    o = AUD_LEN + 4 * (3 * AUD_MORE)
    regs_step = list(struct.unpack_from("<%dI" % AUD_REGS, data, o))
    st = dict(zip(AUD_STEP_FIELDS, struct.unpack_from("<5I", data, o + 4 * AUD_REGS)))
    if (st["step_state"], st["steps"]) != (2, 2) or st["clk_set"] != st["clk_before"] | 0x200 \
            or st["clk_back"] != st["clk_before"] or regs_step[AUD_CLK2] != st["clk_before"]:
        problems.append("audio2: step %s, CLK_CON2 after %08x (taken then undone: bit 9 alone set, then exactly"
                        " as read)" % (st, regs_step[AUD_CLK2]))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio2: %.1f frames a second in fwtest's time (%.1f), storm %d" % (fps, AUD_FPS, e["storm"]))
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    tail = left[-4 * 44100:]
    if left != right or min(max(abs(v) for v in tail[w:w + 441]) for w in range(0, len(tail) - 441, 441)) < 2000:
        problems.append("audio2: the tone doesn't play on through the steps in both channels")
    else:
        fit = aa.sine_fit(tail[4410:-4410])
        if abs(fit["frequency"] - 440) > 0.5:
            problems.append("audio2: the tone at %.2f Hz (440)" % fit["frequency"])
    _, _, page = fws.read_png(os.path.join(out, "lcd-8500ms.png"))
    if not any(page[y][x] == (0, 255, 0) for y in range(0, 16) for x in range(6, 200)):
        problems.append("audio2: REC didn't show the page")
    print("audio2: CLK_CON2 %08x, %08x with bit 9, %08x put back; A: CON0 %08x, %08x, %08x, back %08x; B: CLK_CON2"
          " %08x, %08x, back %08x; the tone on at 440 Hz, %.1f frames a second in fwtest's time"
          % (st["clk_before"], st["clk_set"], st["clk_back"], ab["a_before"], ab["a_clr"], ab["a_set"], ab["a_back"],
             ab["b_before"], ab["b_set"], ab["b_back"], fps))
    return problems




def case_audio3(a, work, log):
    """audio3 (clean-br17-audio3): audio1's build with ALNK0 stopped and
    started again by SEQ. The first press clears CON0 bit 11 alone and no
    half is taken while it is stopped; the second writes back the CON0
    read before, exactly, and the tone plays again at 440 Hz. Core 1's
    count, in its own 64-byte block, rises through every fixed point,
    whose beats run in order; the page reaches its core 1 view; nothing
    unmodelled but the window's, corex2's and DAC_CON."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, blk = sy["hw_aud"], sy["hw_core1_blk"]
    if blk % 64:
        problems.append("audio3: core 1's block at %08x (on a 64-byte boundary)" % blk)
    script = os.path.join(b, "audio3.script")
    with open(script, "w") as f:
        # After audio1's page (about 7 s): ALNK0 stopped at 7.5 s, its page
        # until about 9 s, started again at 11.5 s; ARP at 13.5 s, refused
        # (bit 9 not set).
        f.write("7500 key %d down\n7600 key %d up\n11500 key %d down\n11600 key %d up\n13500 key %d down\n"
                "13600 key %d up\n" % (HW_SEQ, HW_SEQ, HW_SEQ, HW_SEQ, HW_ARP, HW_ARP))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "17500", "--wav", "--script", os.path.relpath(script, ROOT),
               "--lcd", "end", "--ram", "0x%08x:%d@end" % (BEACON_ADDR, fws.BEACON_LEN),
               "--ram", "0x%08x:%d@end" % (h, AUD3_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio3: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS - {"0x00012f00"})
    if odd:
        problems.append("audio3: unmodelled accesses besides the window's, corex2's and DAC_CON: %s" % odd[:8])
    bc = fws.beacon(ram(out, BEACON_ADDR, fws.BEACON_LEN))
    if bc["screen"] != 2 or bc["halt_reason"]:
        problems.append("audio3: screen %d, halt %d (the test screen, no halt)" % (bc["screen"], bc["halt_reason"]))
    data = ram(out, h, AUD3_LEN)
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), data, 8 * AUD_REGS)))
    o = AUD2_LEN
    beats = list(struct.unpack_from("<%dI" % AUD3_C1, data, o))
    counts = list(struct.unpack_from("<%dI" % AUD3_C1, data, o + 4 * AUD3_C1))
    st = dict(zip(AUD3_FIELDS, struct.unpack_from("<%dI" % len(AUD3_FIELDS), data, o + 8 * AUD3_C1)))
    if (st["al_state"], st["al_keys"]) != (2, 2) or not st["al_before"] & 0x800 \
            or st["al_stop"] & ~0x8000 != st["al_before"] & ~0x8800 or (st["al_back"] ^ st["al_before"]) & ~0x8000:
        problems.append("audio3: ALNK0 %s (stopped by bit 11 alone, then put back exactly as read, bit 15, the half"
                        " playing, aside)" % st)
    if st["al_blocks_back"] - st["al_blocks_stop"] > 1 or e["n1"] < st["al_blocks_back"] + 100:
        problems.append("audio3: halves %d at the stop, %d at the restart, %d at the end (none while stopped, then"
                        " on again)" % (st["al_blocks_stop"], st["al_blocks_back"], e["n1"]))
    ab = aud_ab(data)
    if (ab["a_keys"], ab["a_state"], ab["refused"]) != (0, 0, 1):
        problems.append("audio3: ARP without bit 9: A %d presses taken, state %d, %d refused (refused, nothing taken)"
                        % (ab["a_keys"], ab["a_state"], ab["refused"]))
    # Two marks in one beat may read one count (core 1's turns in fwtest);
    # across a beat the count must rise.
    if beats != sorted(beats) or not counts[0] or counts != sorted(counts) \
            or any(q <= p for p, q, b0, b1 in zip(counts, counts[1:], beats, beats[1:]) if b1 > b0):
        problems.append("audio3: core 1's marks: beats %s, counts %s (in order, the count rising across each beat)"
                        % (beats, counts))
    if beats[-1] <= beats[-2]:
        problems.append("audio3: the page's core 1 view wasn't redrawn (now %d, page %d)" % (beats[-1], beats[-2]))
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    tail = left[-2 * 44100:]
    if left != right or min(max(abs(v) for v in tail[w:w + 441]) for w in range(0, len(tail) - 441, 441)) < 2000:
        problems.append("audio3: the tone doesn't play again after the restart in both channels")
    else:
        fit = aa.sine_fit(tail[4410:-4410])
        if abs(fit["frequency"] - 440) > 0.5:
            problems.append("audio3: the tone at %.2f Hz (440)" % fit["frequency"])
    print("audio3: ALNK0 CON0 %08x, %08x stopped, %08x put back; halves %d at the stop, %d at the restart, %d at the"
          " end; core 1's count at the marks %s" % (st["al_before"], st["al_stop"], st["al_back"], st["al_blocks_stop"],
                                                   st["al_blocks_back"], e["n1"], counts))
    return problems


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
    """report1 (SB_HW_REPORT, clean-br17-report1): the report log in
    audio1's build. A chip whose log region holds older data gets the
    records of boot, each page, REC, ARP, ARP's undo and EDIT's save,
    numbered 1 on in consecutive slots from the region's start, each
    sector erased before its first record and the rest untouched; the
    decoder reads them back, and the last record matches the probe's state
    in RAM. From that chip a second run numbers on; from a full ring a run
    erases the oldest sector and keeps the rest."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, hr = sy["hw_aud"], sy["hw_rep"]
    with open(os.path.join(b, "app.bin"), "rb") as f:
        if BUILD_ID.encode() not in f.read():
            problems.append("report1: the build's identity isn't in app.bin")

    def run(name, seed, ms, keys):
        flash = os.path.join(work, name + "-seed.bin")
        with open(flash, "wb") as f:
            f.write(seed)
        script = os.path.join(work, name + ".script")
        with open(script, "w") as f:
            for t, k in keys:
                f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
            f.write("%d pot 900\n" % (ms - 10))
        out = os.path.join(work, name)
        r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", str(ms), "--flash", os.path.relpath(flash, ROOT),
                   "--flash-out", "--script", os.path.relpath(script, ROOT),
                   "--ram", "0x%08x:%d@end" % (h, AUD3_LEN), "--ram", "0x%08x:%d@end" % (hr, 4 * len(REP_FIELDS)))
        if r["run"]["outcome"] != "completed":
            problems.append("report1 %s: %s (%s)" % (name, r["run"]["outcome"], r["run"].get("detail")))
        # Each record reads ALNK1's and the counter's registers (layout 2), unmodelled in fwtest.
        odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS - {"0x00012f00"}
                     - GPCNT_REGS - ALNK1_REGS)
        if odd:
            problems.append("report1 %s: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and"
                            " ALNK1: %s" % (name, odd[:8]))
        with open(os.path.join(out, "flash.bin"), "rb") as f:
            chip = f.read()
        rep = dict(zip(REP_FIELDS, struct.unpack("<%dI" % len(REP_FIELDS), ram(out, hr, 4 * len(REP_FIELDS)))))
        return chip, rep, ram(out, h, AUD3_LEN)

    # The unit's case: the log region holds older data, never 0xFF.
    seed = bytearray(b"\xff" * 0x100000)
    for i in range(rd.LOG_BASE, rd.LOG_END):
        seed[i] = (i * 7 + 3) & 0x7F
    keys = ((9000, HW_REC), (11500, HW_ARP), (14000, HW_ARP), (16500, HW_EDIT))
    chip, rep, data = run("first", bytes(seed), 18000, keys)
    rs, bad = rd.records(chip)
    labels = [r["label"] for r in rs]
    want = ["boot", "page", "REC taken", "page", "A taken", "page", "A undone", "page", "save key"]
    if labels != want or [r["seq"] for r in rs] != list(range(1, 10)) or bad \
            or [r["offset"] for r in rs] != [rd.LOG_BASE + rd.REC * i for i in range(9)]:
        problems.append("report1 first: records %s (%s, numbered 1 to 9 in the first slots), %d with a bad CRC"
                        % ([(r["seq"], r["label"], hex(r["offset"])) for r in rs], want, len(bad)))
    if (rep["saved"], rep["fails"], rep["found"]) != (9, 0, 0):
        problems.append("report1 first: saved %d, failed %d, found at the start %d (9, 0, 0)"
                        % (rep["saved"], rep["fails"], rep["found"]))
    if any(not r["known"] or r["build"] != BUILD_ID for r in rs):
        problems.append("report1 first: a record of an unknown layout or another build: %s"
                        % [(r["layout"], r["count"], r["build"]) for r in rs])
    used = (9 * rd.REC + 4095) // 4096 * 4096    # the sectors 9 records take; the rest as they were
    if chip[rd.LOG_BASE + used:rd.LOG_END] != bytes(seed[rd.LOG_BASE + used:rd.LOG_END]) \
            or chip[rd.LOG_BASE + 9 * rd.REC:rd.LOG_BASE + used] != b"\xff" * (used - 9 * rd.REC):
        problems.append("report1 first: the sectors past the records' changed, or the rest of the third isn't"
                        " erased")
    if rs:
        last = rs[-1]["fields"]
        ab = aud_ab(data)
        e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), data, 8 * AUD_REGS)))
        st = dict(zip(AUD_STEP_FIELDS, struct.unpack_from("<5I", data, AUD_LEN + 4 * (3 * AUD_MORE + AUD_REGS))))
        got = (last["rec_state"], last["rec_presses"], last["rec_clk_set"], last["a_state"], last["a_presses"],
               last["a_con0_back"], last["master"], last["CLK_CON2"] & 0x200)
        exp = (st["step_state"], st["steps"], st["clk_set"], ab["a_state"], ab["a_keys"], ab["a_back"], e["master"],
               0x200)
        if got != exp or not 0 < last["core1_count"] or last["log_found_at_start"] != 0:
            problems.append("report1 first: the last record %s, RAM %s (rec, A, MASTER, bit 9), core 1 %d"
                            % (got, exp, last["core1_count"]))
    # A second run from that chip: numbered on after the newest, next slots.
    chip2, rep2, _ = run("second", chip, 8000, ())
    rs2, _ = rd.records(chip2)
    new = [r for r in rs2 if r["seq"] > 9]
    if [(r["seq"], r["label"], r["offset"]) for r in new] != [(10, "boot", rd.LOG_BASE + 9 * rd.REC),
                                                             (11, "page", rd.LOG_BASE + 10 * rd.REC)] \
            or len(rs2) != 11 or rep2["found"] != 9:
        problems.append("report1 second: new records %s, %d in all, %d found at the start (10 boot and 11 page"
                        " after the first run's 9)" % ([(r["seq"], r["label"], hex(r["offset"])) for r in new],
                                                       len(rs2), rep2["found"]))
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
    chip3, rep3, _ = run("wrap", bytes(full), 8000, ())
    rs3, _ = rd.records(chip3)
    seqs = [r["seq"] for r in rs3]
    # The two new records erase as many sectors as they take; those
    # sectors' old records go.
    first = 1000 + (2 * rd.REC + 4095) // 4096 * 4096 // rd.REC
    if seqs != list(range(first, 1000 + slots)) + [1000 + slots, 1001 + slots] \
            or rs3[-2]["offset"] != rd.LOG_BASE or rep3["found"] != slots:
        problems.append("report1 wrap: sequences %s..%s (%d records), the first new at %s (%d to %d, then two"
                        " new from slot 0)" % (seqs[:3], seqs[-3:], len(seqs), hex(rs3[-2]["offset"]) if len(rs3) > 1
                                               else None, first, 999 + slots))
    # A write that fails (SB_TEST_LOG_VERIFY_FAIL: the first record programmed
    # with one bit wrong): it is found, kept in the log's own fields, and the
    # record written again in the next slot under the same number; the
    # decoder lists the failed one with its header.
    vb = os.path.join(work, "build-verify")
    build(vb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT",
          "--define", "SB_TEST_LOG_VERIFY_FAIL")
    vout = os.path.join(work, "verify")
    vflash = os.path.join(work, "verify-seed.bin")
    with open(vflash, "wb") as f:
        f.write(bytes(seed))
    r = fwtest(os.path.join(vb, "app.bin"), vout, log, "--ms", "8000", "--flash", os.path.relpath(vflash, ROOT),
               "--flash-out")
    with open(os.path.join(vout, "flash.bin"), "rb") as f:
        vchip = f.read()
    vrs, vbad = rd.records(vchip)
    vb0 = rd.bad_record(vchip, vbad[0]) if vbad else {}
    vl = vrs[-1]["fields"] if vrs else {}
    got = (len(vbad), vb0.get("slot"), vb0.get("seq"), vb0.get("label"), [(x["seq"], x["label"]) for x in vrs[:2]],
           [x["offset"] for x in vrs[:2]], vl.get("log_fail_count"), vl.get("log_retries"), vl.get("log_fail0_seq"),
           vl.get("log_fail0_slot"), vl.get("log_fail0_err"), vl.get("log_fail0_pages_differ"),
           vl.get("log_fail0_first_byte"), vl.get("log_fail0_bytes_read_ff"), vl.get("log_page_rewaits"))
    exp = (1, 0, 1, "boot", [(1, "boot"), (2, "page")], [rd.LOG_BASE + rd.REC, rd.LOG_BASE + 2 * rd.REC], 1, 1, 1, 0,
           5, 1, 82, 0, 0)
    if r["run"]["outcome"] != "completed" or got != exp:
        problems.append("report1 verify: %s (%s)" % (got, exp))
    print("report1: from older data, %d records (%s) decoded, the sectors past them untouched; a second run"
          " numbered on (%s); from a full ring the oldest sector erased, %d records kept; a failed write found,"
          " logged and written again in the next slot"
          % (len(rs), ", ".join(labels), [r["seq"] for r in new], len(rs3)))
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


def case_audio4(a, work, log):
    """audio4 (clean-br17-audio4): steps H and I in report1's build. H
    sets CLK_CON1 bits 4-6 alone (3, then 5) and the counter, FX measures
    again, I starts ALNK1 with CLK_CON2 bit 11 alone and SEL adds bit 10;
    REC's undo is refused while I, taken after it, is; every undo puts back
    the values read before. The log holds one record for each press and
    each page, in order, the last matching RAM."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_aud"]
    keys = ((9000, HW_ENV), (11500, HW_REC), (14000, HW_FX), (16500, HW_LFO), (20000, HW_SEL), (23500, HW_REC),
            (26000, HW_LFO), (28500, HW_REC), (31000, HW_ENV))
    script = os.path.join(work, "audio4.script")
    with open(script, "w") as f:
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "34000", "--flash-out", "--leds-every", "500",
               "--script", os.path.relpath(script, ROOT), "--ram", "0x%08x:%d@end" % (h, AUD4_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio4: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    odd = sorted({u["address"] for u in r["run"]["unmodelled_accesses"]} - HW_WINDOW_REGS - {"0x00012f00"}
                 - GPCNT_REGS - ALNK1_REGS)
    gp_unmodelled = bool({u["address"] for u in r["run"]["unmodelled_accesses"]} & GPCNT_REGS)
    al1_unmodelled = bool({u["address"] for u in r["run"]["unmodelled_accesses"]} & ALNK1_REGS)
    if odd:
        problems.append("audio4: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1:"
                        " %s" % odd[:8])
    data = ram(out, h, AUD4_LEN)
    st = dict(zip(AUD_STEP_FIELDS, struct.unpack_from("<5I", data, AUD_LEN + 4 * (3 * AUD_MORE + AUD_REGS))))
    ab = aud_ab(data)
    hh = dict(zip(AUD_H_FIELDS, struct.unpack_from("<%dI" % len(AUD_H_FIELDS), data, AUD_HI_AT)))
    ii = dict(zip(AUD_I_FIELDS, struct.unpack_from("<%dI" % len(AUD_I_FIELDS), data,
                                                    AUD_HI_AT + 4 * len(AUD_H_FIELDS))))
    depth = struct.unpack_from("<I", data, AUD4_LEN - 4)[0]
    c1 = hh["clk1_before"]
    if (hh["h_state"], hh["h_keys"], hh["h_measures"]) != (2, 2, 2) \
            or hh["clk1_check"] != (c1 & ~0x70) | 0x30 or hh["clk1_audio"] != (c1 & ~0x70) | 0x50 \
            or hh["clk1_back"] != c1 or hh["gp_back"] != hh["gp_before"] \
            or (not gp_unmodelled and (hh["gp_check"] & 0x7F0F != 0x1A09 or hh["gp_audio"] & 0x7F0F != 0x1A09)):
        problems.append("audio4: step H %s (CLK_CON1 bits 4-6 alone to 3 and 5, the counter set on, both put back)"
                        % {k: "%x" % v for k, v in hh.items()})
    if (ii["i_state"], ii["i_keys"], ii["i_bit10"]) != (2, 2, 1) or ii["clk_set"] != ii["clk_before"] | 0x800 \
            or ii["clk_set10"] != ii["clk_set"] | 0x400 or ii["clk_back"] != ii["clk_before"] \
            or (not al1_unmodelled and not ii["a0"] & 0x800) or (ii["con_back"] ^ ii["b0"]) & ~0x8000:
        problems.append("audio4: step I %s (ALNK1 on, bit 11 alone, bit 10 alone, then CON0 and CLK_CON2 as read)"
                        % {k: "%x" % v for k, v in ii.items()})
    if (st["step_state"], st["steps"], ab["refused"], depth) != (2, 2, 1, 0) or st["clk_back"] != st["clk_before"] \
            or ii["clk_before"] != st["clk_set"]:
        problems.append("audio4: REC %s, refused %d, CLK_CON2 steps left %d (taken, its undo refused once while I"
                        " was taken, then undone; none left)" % (st, ab["refused"], depth))
    frames = 64
    with open(os.path.join(ROOT, "firmware", "src", "audio.h")) as f:
        m = re.search(r"#define AUDIO_FRAMES\s+(\d+)", f.read())
        if m:
            frames = int(m.group(1))
    plays = ii["flips"] > 0
    if plays:
        fps = ii["hps10"] / 10.0 / HW_RATIO * frames
        if abs(fps / AUD_FPS - 1) > 0.02:
            problems.append("audio4: ALNK1's halves %.1f a second, %.0f frames in fwtest's time (44 117.6, 2 %%)"
                            % (ii["hps10"] / 10.0, fps))
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        chip = f.read()
    rs, bad = rd.records(chip)
    labels = [x["label"] for x in rs]
    want = ["boot", "page"]
    for lab in ("H taken", "REC taken", "H measured", "I taken", "I bit 10", "REC refused", "I undone", "REC undone",
                "H undone"):
        want += [lab, "page"]
    if labels != want or bad or any(x["layout"] != HW_LAYOUT_OLD or not x["known"] for x in rs):
        problems.append("audio4: log records %s (%s), layouts %s, %d bad" % (labels, want,
                        sorted({(x["layout"], x["count"]) for x in rs}), len(bad)))
    elif rs:
        last = rs[-1]["fields"]
        got = (last["h_state"], last["h_clk1_back"], last["i_state"], last["i_clk2_back"], last["i_b15_flips"],
               last["refused"], last["clk2_steps_taken"])
        exp = (hh["h_state"], hh["clk1_back"], ii["i_state"], ii["clk_back"], ii["flips"], ab["refused"], depth)
        if got != exp:
            problems.append("audio4: the last record %s, RAM %s" % (got, exp))
    # leds1: a step key's LED lit (one slot in 14, about 71) while its step
    # is taken, every other LED dark, at moments when no key is held.
    with open(os.path.join(out, "leds.csv")) as f:
        leds = {int(float(row[0])): [int(v) for v in row[1:]] for row in list(csv.reader(f))[1:]}
    # A key's release is read once its page is over, so each moment is
    # after a page and before the next press.
    lit_at = {13000: {HW_ENV, HW_FX, HW_REC}, 21500: {HW_ENV, HW_FX, HW_REC, HW_LFO, HW_SEL},
              28500: {HW_ENV, HW_FX, HW_REC}, 31000: {HW_ENV, HW_FX}, 33500: set()}
    for t, want_lit in sorted(lit_at.items()):
        row = leds.get(t)
        if not row or any((60 <= v <= 85) != (i in want_lit) or (i not in want_lit and v) for i, v in enumerate(row)):
            problems.append("audio4: LEDs at %d ms %s (lit: %s)" % (t, row and {i: v for i, v in enumerate(row) if v},
                                                                     sorted(want_lit)))
    print("audio4: H: CLK_CON1 %08x > %08x > %08x > back %08x, counts bus %d/%d audio %d/%d (%d and %d gates timed"
          " out; fwtest's counter %s); I: CLK_CON2 %08x > %08x > %08x > back %08x, ALNK1 %s (%d half changes, %d.%d"
          " a second; fwtest's ALNK1 %s); REC's undo refused once; %d log records in order"
          % (c1, hh["clk1_check"], hh["clk1_audio"], hh["clk1_back"], hh["check0"], hh["check1"], hh["audio0"],
             hh["audio1"], hh["check_to"], hh["audio_to"], "unmodelled" if gp_unmodelled else "modelled",
             ii["clk_before"], ii["clk_set"], ii["clk_set10"], ii["clk_back"], "plays" if plays else "doesn't play",
             ii["flips"], ii["hps10"] // 10, ii["hps10"] % 10, "unmodelled" if al1_unmodelled else "modelled", len(rs)))
    return problems


AUD_K_AT = AUD4_LEN
AUD_K_FIELDS = ("k_state", "k_keys", "k_clk1_before", "k_gp_before", "k_clk1_back", "k_gp_back")
AUD5_LEN = AUD_K_AT + 4 * (len(AUD_K_FIELDS) + 10 * 6)
HW_GLO, HW_OCTUP = 7, 1      # fwtest's keys of GLO (step K) and OCT+ (step J) (input.h)


def case_audio5(a, work, log):
    """audio5 (clean-br17-audio5): steps K and J in report1's build. K's
    one press measures input 5 every way the prompt gives, writing
    CLK_CON1 bits 4-6 and 2-3 alone, and its undo puts CLK_CON1 and the
    counter back. J's sweep, with ALNK0 stopped, tries each of CON1's 16
    bits and CON3's 8 alone and puts each back; a press aborts a second
    sweep; with ALNK0 running the sweep stops at its first try and a press
    puts it back. Every step is in the log; the tone plays on."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT")
    h = fws.elf_symbols(os.path.join(b, "app.elf"))["hw_aud"]
    keys = ((9000, HW_GLO), (11500, HW_GLO), (14000, HW_SEQ), (16500, HW_OCTUP), (25000, HW_OCTUP),
            (25600, HW_OCTUP), (30000, HW_SEQ), (32500, HW_OCTUP), (36000, HW_OCTUP))
    script = os.path.join(work, "audio5.script")
    with open(script, "w") as f:
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "40000", "--flash-out", "--wav",
               "--script", os.path.relpath(script, ROOT), "--ram", "0x%08x:%d@end" % (h, AUD5_LEN),
               "--ram", "0x%08x:%d@32000" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio5: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio5: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    data = ram(out, h, AUD5_LEN)
    k = dict(zip(AUD_K_FIELDS, struct.unpack_from("<%dI" % len(AUD_K_FIELDS), data, AUD_K_AT)))
    m = [struct.unpack_from("<6I", data, AUD_K_AT + 4 * (len(AUD_K_FIELDS) + 6 * i)) for i in range(10)]
    c1 = k["k_clk1_before"]
    want = [(c1 & ~0x70) | s << 4 for s in (3, 1, 5, 6, 7)] + [(c1 & ~0x70) | 0x70]
    want += [(c1 & ~0x7C) | 0x50 | d << 2 for d in (1, 2, 3)] + [(c1 & ~0x70) | 0x50]
    if (k["k_state"], k["k_keys"]) != (2, 2) or [x[0] for x in m] != want or k["k_clk1_back"] != c1 \
            or k["k_gp_back"] != k["k_gp_before"]:
        problems.append("audio5: step K %s, CLK_CON1 at each %s (%s)" % (k, ["%x" % x[0] for x in m],
                                                                       ["%x" % x for x in want]))
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    labels = [x["label"] for x in rs]
    tries = ["CON1 b%d" % i for i in range(16)] + ["CON3 b%d" % i for i in range(8)]
    starts = [i for i, l in enumerate(labels) if l == "J starting"]
    sweeps = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(labels)
        sweeps.append([l for l in labels[i + 1:end] if l.startswith("CON") or l.startswith("J ")])
    if bad or any(x["layout"] != HW_LAYOUT_OLD or not x["known"] for x in rs) or len(sweeps) != 3:
        problems.append("audio5: log: %d sweeps, %d bad, layouts %s" % (len(sweeps), len(bad),
                                                                        sorted({x["layout"] for x in rs})))
    else:
        if sweeps[0] != tries + ["J done"]:
            problems.append("audio5: the first sweep %s (every try, then J done)" % sweeps[0])
        if sweeps[1][-1:] != ["J aborted"] or not 1 <= len(sweeps[1]) - 1 < len(tries):
            problems.append("audio5: the second sweep %s (some tries, then aborted)" % sweeps[1])
        if sweeps[2][:3] != ["CON1 b0 moved", "J moved", "J undone"]:
            problems.append("audio5: the third sweep %s (its first try moves; then undone)" % sweeps[2])
    last = rs[-1]["fields"] if rs else {}
    if last.get("AL0_CON1_now") or last.get("AL0_CON3_now") or last.get("j_state") != 4 \
            or last.get("j_back") != last.get("j_before"):
        problems.append("audio5: at the end CON1 %s, CON3 %s, J state %s, put back %s of %s (0, 0, undone, as read)"
                        % tuple(last.get(x) for x in ("AL0_CON1_now", "AL0_CON3_now", "j_state", "j_back",
                                                       "j_before")))
    first = [x for x in rs if x["label"] in tries]
    stored = [x["fields"]["j_read"] == x["fields"]["j_written"] for x in first[:24]]
    # The tone and its rate after K, the sweeps and SEQ's restart, before
    # the third sweep: in fwtest CON1 bit 0 sets off a burst
    # of source 11 with ALNK0 running, the guard stops the output (storm),
    # and that try counts as moving the link.
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    seg = left[-int(1.5 * 44100):]     # the WAV holds only what played: its end is after the restart
    if left != right or min(max(abs(v) for v in seg[w:w + 441]) for w in range(0, len(seg) - 441, 441)) < 2000:
        problems.append("audio5: the tone doesn't play after the sweeps in both channels")
    else:
        fit = aa.sine_fit(seg[4410:-4410])
        if abs(fit["frequency"] - 440) > 0.5:
            problems.append("audio5: the tone at %.2f Hz (440)" % fit["frequency"])
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(out, h, AUD_LEN, "32000ms"),
                                                 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio5: %.1f frames a second in fwtest's time (%.1f), storm %d, at 32 s"
                        % (fps, AUD_FPS, e["storm"]))
    end = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), data, 8 * AUD_REGS)))
    print("audio5: K: CLK_CON1 %08x through inputs 3, 1, 5, 6, 7, the 480 MHz and the DAC choices, back %08x (fwtest's"
          " counter %s); J: sweeps of %s tries, fwtest %s CON1 and CON3 (%d of %d read back as written); the tone at 440"
          " Hz, %.1f frames a second after the sweeps; with ALNK0 running, CON1 bit 0 %s in fwtest; %d log records"
          % (c1, k["k_clk1_back"], "unmodelled" if acc & GPCNT_REGS else "modelled",
             "/".join(str(len(x) - 1) for x in sweeps), "stores" if all(stored) and stored else "doesn't store",
             sum(stored), len(stored), fps, "set off the storm guard" if end["storm"] else "moved the link", len(rs)))
    return problems


HW_OCTDOWN = 0        # fwtest's key of OCT- (step D)


def case_audio6(a, work, log):
    """audio6 (clean-br17-audio6): step D, JL_IOMAP->CON5 a bit at a time,
    each try checked and undone by the firmware; a forced check failure
    stops the sweep with the try undone; a moving link keeps its bit."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, ga = sy["hw_aud"], sy["hw_guide_at"]
    keys = ((9000, HW_SEQ), (11500, HW_REC), (14000, HW_OCTDOWN), (30000, HW_REC), (32500, HW_OCTDOWN),
            (49000, HW_SEQ), (51500, HW_OCTDOWN), (55000, HW_OCTDOWN))
    script = os.path.join(work, "audio6.script")
    with open(script, "w") as f:
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "58000", "--flash-out", "--wav", "--leds-every", "2500",
               "--script", os.path.relpath(script, ROOT), "--ram", "0x%08x:4@end" % ga,
               "--ram", "0x%08x:%d@51000" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio6: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio6: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    labels = [x["label"] for x in rs]
    starts = [i for i, l in enumerate(labels) if l == "D starting"]
    sweeps = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(labels)
        sweeps.append([x for x in rs[i + 1:end] if x["label"].startswith("D ")])
    full = []
    for bit in range(32):
        full += ["D b%d before" % bit, "D b%d" % bit]
    # Since audio7 the ring holds 96 records of 4096 bytes, and a sweep
    # writes about 67: the newest stay, so the first sweep has gone by the
    # third's end. The second (bit 9 clear) and the third are checked; the
    # first in RAM below.
    if bad or any(x["layout"] != HW_LAYOUT_OLD or not x["known"] for x in rs) or len(sweeps) < 2:
        problems.append("audio6: log: %d sweeps, %d bad, layouts %s" % (len(sweeps), len(bad),
                                                                        sorted({x["layout"] for x in rs})))
    else:
        sweeps = [None] * (3 - len(sweeps)) + sweeps
        for n in (1,):
            names = [x["label"] for x in sweeps[n]]
            tries = [x["fields"] for x in sweeps[n] if x["label"].startswith("D b") and not x["label"].endswith("before")]
            if names != full + ["D done"] or any(f["d_con5_back"] != f["d_con5_before"] or f["d_check_set"]
                                                 or f["d_check_after"] for f in tries):
                problems.append("audio6: sweep %d: %s (every bit tried and put back, the checks passing)"
                                % (n + 1, [(x["label"], x["fields"]["d_check_set"], x["fields"]["d_check_after"])
                                           for x in sweeps[n] if x["label"] not in full[::2]][:6]))
        clk = sweeps[1][0]["fields"]["d_clk2"] & 0x200
        if clk:
            problems.append("audio6: CLK_CON2 bit 9 set at the second sweep (clear)")
        done2 = [x for x in rs if x["label"] == "D done" and x["fields"]["d_sweeps"] == 2]
        if not done2 or done2[0]["fields"]["d_tries"] != 32:
            problems.append("audio6: the second sweep's end %s (32 tries)" % (done2 and done2[0]["fields"]["d_tries"]))
        names = [x["label"] for x in sweeps[2]]
        if names[:4] != ["D b0 before", "D b0 kept", "D kept", "D undone"]:
            problems.append("audio6: the third sweep %s (bit 0 kept, then undone)" % names[:6])
    last = rs[-1]["fields"] if rs else {}
    if last.get("d_state") != 4 or last.get("d_con5_now") != last.get("d_con5_before"):
        problems.append("audio6: at the end D %s, CON5 %s (undone, as read)" % (last.get("d_state"),
                                                                             last.get("d_con5_now")))
    stored = [x["fields"]["d_con5_read"] == x["fields"]["d_con5_written"] for x in (sweeps[1] if len(sweeps) > 1 and
                                                                                     sweeps[1] else [])
              if x["label"].startswith("D b") and not x["label"].endswith("before")]
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(out, h, AUD_LEN, "51000ms"),
                                                 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio6: %.1f frames a second in fwtest's time (%.1f), storm %d" % (fps, AUD_FPS, e["storm"]))
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    tail = left[-int(1.5 * 44100):]
    if left != right or min(max(abs(v) for v in tail[w:w + 441]) for w in range(0, len(tail) - 441, 441)) < 2000:
        problems.append("audio6: the tone doesn't play at the end in both channels")
    # The forced check failure: the sweep stops at bit 2, the try undone.
    fb = os.path.join(work, "build-fail")
    build(fb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT",
          "--define", "SB_TEST_D_CHECK_FAIL")
    fscript = os.path.join(work, "fail.script")
    with open(fscript, "w") as f:
        for t, k in ((9000, HW_SEQ), (11500, HW_OCTDOWN)):
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    fout = os.path.join(work, "run-fail")
    r = fwtest(os.path.join(fb, "app.bin"), fout, log, "--ms", "16000", "--flash-out",
               "--script", os.path.relpath(fscript, ROOT))
    with open(os.path.join(fout, "flash.bin"), "rb") as f:
        frs, _ = rd.records(f.read())
    flab = [x["label"] for x in frs if x["label"].startswith("D ")]
    fl = frs[-1]["fields"] if frs else {}
    if r["run"]["outcome"] != "completed" or flab[-3:] != ["D b2 before", "D b2 check BAD", "D stopped"] \
            or (fl.get("d_stop"), fl.get("d_tries"), fl.get("d_check_set"), fl.get("d_check_after")) != (1, 3, 1, 0) \
            or fl.get("d_con5_now") != fl.get("d_con5_before"):
        problems.append("audio6 fail: %s, records %s, stop %s, tries %s, checks %s/%s, CON5 %s of %s"
                        % (r["run"]["outcome"], flab[-3:], fl.get("d_stop"), fl.get("d_tries"), fl.get("d_check_set"),
                           fl.get("d_check_after"), fl.get("d_con5_now"), fl.get("d_con5_before")))
    print("audio6: D: two full sweeps (CLK_CON2 bit 9 set, then clear), every try put back by the firmware with the"
          " matrix right; fwtest %s CON5 (%d of %d read back as written); with ALNK0 running bit 0 kept, then put back;"
          " a forced check failure stopped the sweep at bit 2, undone; the tone at %.1f frames a second; %d records"
          % ("stores" if stored and all(stored) else "doesn't store", sum(stored), len(stored), fps, len(rs)))
    return problems


HW_KEY1, HW_KEY2 = 14, 15   # fwtest's keys of KEY1 (L1) and KEY2 (L2) (input.h, INPUT_KEY(1) and (2))


def case_audio7(a, work, log):
    """audio7 (clean-br17-audio7): set-ups L1 and L2 in the next-key order,
    each with D's safety machinery; kept and put back by key in fwtest,
    where the link runs; a forced check failure put back by the firmware."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, ga = sy["hw_aud"], sy["hw_guide_at"]
    keys = ((9000, HW_KEY1), (13000, HW_KEY1), (15500, HW_REC), (18000, HW_KEY2), (22000, HW_KEY2), (24500, HW_REC),
            (27000, HW_KEY2), (31000, HW_KEY2), (33500, HW_EDIT))
    script = os.path.join(work, "audio7.script")
    with open(script, "w") as f:
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "38000", "--flash-out", "--wav",
               "--script", os.path.relpath(script, ROOT), "--ram", "0x%08x:4@end" % ga,
               "--ram", "0x%08x:%d@end" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio7: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio7: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    ls = [x for x in rs if x["label"].startswith("L")]
    want = ["L1 before", "L1 kept", "L1 undone"] + ["L2 before", "L2 kept", "L2 undone"] * 2
    if bad or [x["label"] for x in ls] != want or any(x["layout"] != HW_LAYOUT_OLD or not x["known"] for x in ls):
        problems.append("audio7: L records %s (%s), %d bad" % ([x["label"] for x in ls], want, len(bad)))
    else:
        for i in range(0, 9, 3):
            bf, kp, ud = (x["fields"] for x in ls[i:i + 3])
            which = kp["l_which"]
            con3 = (0xC2, 0x83)[which - 1]
            fps = kp["l_fps_x10_b"] / 10.0 / HW_RATIO
            if kp["l_check_set"] or kp["l_readback_CON3"] != con3 or kp["l_readback_CON1"] != 0x1000 \
                    or not kp["l_expect_hps_x10_a"] or not kp["l_expect_hps_x10_b"] or abs(fps / AUD_FPS - 1) > 0.01:
                problems.append("audio7: L%d kept: check %d, CON3 %02x, CON1 %04x, expected halves %s/%s, %.1f frames a"
                                " second by fwtest's LEN reading (44 117.6)" % (which, kp["l_check_set"],
                                                                               kp["l_readback_CON3"],
                                                                               kp["l_readback_CON1"],
                                                                               kp["l_expect_hps_x10_a"],
                                                                               kp["l_expect_hps_x10_b"], fps))
            if (ud["l_back_CON0"] ^ bf["l_before_AL0_CON0"]) & ~0x8000 or ud["l_back_CON1"] != bf["l_before_AL0_CON1"] \
                    or ud["l_back_CON3"] != bf["l_before_AL0_CON3"]:
                problems.append("audio7: L%d undone: CON0 %04x CON1 %04x CON3 %02x, before %04x %04x %02x"
                                % (which, ud["l_back_CON0"], ud["l_back_CON1"], ud["l_back_CON3"],
                                   bf["l_before_AL0_CON0"], bf["l_before_AL0_CON1"], bf["l_before_AL0_CON3"]))
        bits = [ls[i]["fields"]["l_clk2"] & 0x200 for i in (3, 6)]
        if bits != [0x200, 0]:
            problems.append("audio7: CLK_CON2 bit 9 at the L2s %s (set, then clear)" % bits)
    at = struct.unpack("<I", ram(out, ga, 4))[0]
    if at != 6:
        problems.append("audio7: the guide at %d (6: L1, bit 9, L2, bit 9, L2, save)" % at)
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(out, h, AUD_LEN), 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio7: %.1f frames a second in fwtest's time (%.1f), storm %d" % (fps, AUD_FPS, e["storm"]))
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    tail = left[-2 * 44100:]
    if left != right or min(max(abs(v) for v in tail[w:w + 441]) for w in range(0, len(tail) - 441, 441)) < 2000:
        problems.append("audio7: the tone doesn't play at the end in both channels")
    # The forced check failure: L1 put back by the firmware, no further set-up.
    fb = os.path.join(work, "build-fail")
    build(fb, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT",
          "--define", "SB_TEST_L_CHECK_FAIL")
    fscript = os.path.join(work, "fail.script")
    with open(fscript, "w") as f:
        for t, k in ((9000, HW_KEY1), (13000, HW_KEY2)):
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    fout = os.path.join(work, "run-fail")
    r = fwtest(os.path.join(fb, "app.bin"), fout, log, "--ms", "16000", "--flash-out",
               "--script", os.path.relpath(fscript, ROOT))
    with open(os.path.join(fout, "flash.bin"), "rb") as f:
        frs, _ = rd.records(f.read())
    fl = [x for x in frs if x["label"].startswith("L")]
    f1 = fl[1]["fields"] if len(fl) > 1 else {}
    if r["run"]["outcome"] != "completed" or [x["label"] for x in fl] != ["L1 before", "L1 check BAD", "L refused"] \
            or f1.get("l_check_set") != 1 or f1.get("l_stopped") != 1 \
            or (f1.get("l_back_CON0", 0) ^ f1.get("l_before_AL0_CON0", 0)) & ~0x8000 \
            or f1.get("l_back_CON3") != f1.get("l_before_AL0_CON3") or f1.get("l_back_CON1") != f1.get("l_before_AL0_CON1"):
        problems.append("audio7 fail: %s, records %s, %s" % (r["run"]["outcome"], [x["label"] for x in fl],
                                                             {k: f1.get(k) for k in ("l_check_set", "l_stopped",
                                                                                     "l_back_CON0", "l_back_CON1",
                                                                                     "l_back_CON3")}))
    print("audio7: L1, bit 9, L2, bit 9's undo, L2: each kept in fwtest (its link runs) with the matrix right and put"
          " back by its key; fwtest stores CON1 and CON3; the guide through its table; the tone at %.1f frames a"
          " second; a forced check failure put back by the firmware and the next set-up refused; %d records"
          % (fps, len(rs)))
    return problems


HW_KEY3, HW_KEY4, HW_KEY5, HW_KEY6 = 16, 17, 18, 19   # fwtest's keys of KEY3 to KEY6 (audio8: R2, step 1, sweep, sense)
A8_DEFINES = ("--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD", "--define",
              "SB_TEST_SHORT_HOLD", "--define", "SB_HW_AUDIO1", "--define", "SB_HW_REPORT", "--define", "SB_HW_AUDIO8")


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


def case_audio8(a, work, log):
    """audio8 (clean-br17-audio8): L2 set up at start-up and kept; REC's
    watch; R2's set and undo of PC0, PC1, PC2 and PC6 alone; step 1 and
    the CON5 sweep (in fwtest no pin's IN follows the link, so step 1 finds
    port C still and the sweep runs all 32 bits); the sense scan; then the
    test seams: a forced failed check and a forced port A movement in the
    sweep, a forced port C movement in step 1 (kept, the sweep refused,
    put back by R2's undo); and the 16-bit tone's build."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *A8_DEFINES)
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, ga = sy["hw_aud"], sy["hw_guide_at"]
    # The sense scan's 2000 beats are 5 s in fwtest (its TIMER0 counts 24 MHz, HW_RATIO).
    keys = ((9000, HW_REC), (11000, HW_REC), (13000, HW_KEY3), (16000, HW_KEY4), (20000, HW_KEY5), (34000, HW_KEY6),
            (42000, HW_KEY3), (45000, HW_EDIT))
    r, out, rs, bad = a8_run(work, log, b, "run", keys, 48000, "--wav", "--ram", "0x%08x:4@end" % ga,
                             "--ram", "0x%08x:%d@end" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio8: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio8: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    labels = [x["label"] for x in rs]
    by = {}
    for x in rs:
        by.setdefault(x["label"], x["fields"])
    top = HW_LAYOUT_OLD
    if bad or any(x["layout"] != top or not x["known"] or x["count"] != len(rd.FIELDS[top]) for x in rs):
        problems.append("audio8: %d bad records, or one not layout %d with %d fields" % (len(bad), top,
                                                                                       len(rd.FIELDS[top])))
    want = ["L2 before", "L2 kept", "REC taken", "REC undone", "R2 before", "R2 set", "S1a", "S1b before", "S1b"] \
        + sum((["SW b%d before" % i, "SW b%d" % i] for i in range(32)), []) + ["SW done", "SE before", "SE done",
                                                                               "R2 undone", "save key"]
    got = [x for x in labels if x != "page" and x != "boot"]
    if got[-len(want):] != want:
        problems.append("audio8: records %s, want %s" % (got[:12], want[:12]))
    kp = by.get("L2 kept", {})
    if kp.get("l_which") != 2 or kp.get("l_readback_CON3") != 0x83 or kp.get("l_readback_CON1") != 0x1000 \
            or kp.get("l_check_set") or kp.get("l_clk2", 0) & 0x200:
        problems.append("audio8: start-up's L2: %s" % {k: kp.get(k) for k in ("l_which", "l_readback_CON3",
                                                                              "l_readback_CON1", "l_check_set", "l_clk2")})
    last = rs[-1]["fields"] if rs else {}
    if last.get("a8_boot") != 1 or last.get("a8_off") != 0 or last.get("a8_pcm16") != 0:
        problems.append("audio8: boot %s, off %s, pcm16 %s (1, 0, 0)" % (last.get("a8_boot"), last.get("a8_off"),
                                                                      last.get("a8_pcm16")))
    rt = by.get("REC taken", {})
    if rt.get("rec_watch_clk2", 0) & 0x200 != 0x200:
        problems.append("audio8: REC's watch: CLK_CON2 %08x (bit 9 set)" % rt.get("rec_watch_clk2", 0))
    st, bf, ud = by.get("R2 set", {}), by.get("R2 before", {}), by.get("R2 undone", {})
    pins, lcd = 0x47, 0x180
    if st.get("r2_check") or st.get("r2_pc_set_OUT", 0) & pins != pins or st.get("r2_pc_set_DIR", pins) & pins \
            or st.get("r2_pc_set_DIE", 0) & pins != pins \
            or any(st.get("r2_pc_set_%s" % k) != st.get("r2_pc_before_%s" % k) for k in ("PU", "PD", "HD0", "HD")) \
            or (st.get("r2_pc_set_DIR", 0) ^ st.get("r2_pc_before_DIR", 0)) & ~pins:
        problems.append("audio8: R2 set: %s" % {k: st.get(k) for k in st if k.startswith("r2_")})
    if ud.get("r2_check") or ud.get("r2_state") != 2 \
            or any((ud.get("r2_pc_after_%s" % k, 0) ^ ud.get("r2_pc_before_%s" % k, 0)) & ~(lcd if k == "OUT" else 0)
                   for k in ("OUT", "DIR", "DIE", "PU", "PD", "HD0", "HD")):
        problems.append("audio8: R2 undone: %s" % {k: ud.get(k) for k in ud if k.startswith("r2_")})
    s1 = by.get("S1b", {})
    pc = ("PC0", "PC1", "PC2", "PC6")
    # S1b is written inside the try, before step 1's state is set: the state from the next record.
    if by.get("SW b0 before", {}).get("s1_state") != 2 or s1.get("rt_kind") != 1 or s1.get("rt_check_set") or s1.get("rt_check_after") \
            or s1.get("rt_con0_written", 0) & 0x180 != 0x180 or s1.get("rt_con0_back", 0x180) & 0x180 \
            or not s1.get("rt_s1_passes") or not s1.get("rt_s2_passes"):
        problems.append("audio8: step 1: %s" % {k: s1.get(k) for k in ("rt_kind", "rt_check_set",
                                                                       "rt_check_after", "rt_con0_written",
                                                                       "rt_con0_back", "rt_s1_passes", "rt_s2_passes")})
    sw = by.get("SW done", {})
    if sw.get("sw_state") != 1 or sw.get("sw_tries") != 32 or sw.get("rt_bit") != 31 or sw.get("rt_check_after") \
            or sw.get("rt_con5_back") != sw.get("rt_con5_before") or sw.get("rt_con0_back", 0x180) & 0x180:
        problems.append("audio8: sweep: %s" % {k: sw.get(k) for k in ("sw_state", "sw_tries", "rt_bit", "rt_check_after",
                                                                      "rt_con5_before", "rt_con5_back", "rt_con0_back")})
    moved = sum(x["fields"].get("rt_s1_%s" % n, 0) + x["fields"].get("rt_s2_%s" % n, 0)
                for x in rs if x["label"].startswith(("S1b", "SW b")) for n in pc)
    se = by.get("SE done", {})
    if se.get("se_state") != 1 or not 1500 <= se.get("se_readings", 0) <= 2100:
        problems.append("audio8: sense: state %s, %s readings (about 2000)" % (se.get("se_state"), se.get("se_readings")))
    at = struct.unpack("<I", ram(out, ga, 4))[0]
    if at != 5:
        problems.append("audio8: the guide at %d (5: R2, step 1, sweep, sense, save)" % at)
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(out, h, AUD_LEN), 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio8: %.1f frames a second in fwtest's time (%.1f), storm %d" % (fps, AUD_FPS, e["storm"]))
    _, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    tail = left[-2 * 44100:]
    if left != right or min(max(abs(v) for v in tail[w:w + 441]) for w in range(0, len(tail) - 441, 441)) < 2000:
        problems.append("audio8: the tone doesn't play at the end in both channels")
    summary = ("audio8: L2 kept at start-up; REC's watch (CLK_CON2 %08x: b15 %d, irq %d); R2 set and undone, port C's"
               " other bits as read; step 1 (b) and %d sweep tries: port C's and port A's IN changed %d times in"
               " fwtest; CON5 read back %08x for bit 31; sense %d readings, changed %s; guide %d; %d records"
               % (rt.get("rec_watch_clk2", 0), rt.get("rec_watch_b15_flips", 0), rt.get("rec_watch_irq", 0),
                  sw.get("sw_tries", 0), moved, sw.get("rt_con5_read", 0), se.get("se_readings", 0),
                  {c: "%04x" % se.get("se_changed_P%s" % c, 0) for c in "ABCDEFGH" if se.get("se_changed_P%s" % c)},
                  at, len(rs)))
    # The test seams. A failed check at the sweep's bit 1; port A moving at its bit 3.
    seam_keys = ((9000, HW_KEY3), (12000, HW_KEY4), (16000, HW_KEY5))
    for define, bit, stop, label in (("SB_TEST_A8_CHECK_FAIL", 1, 3, "SW b1 check BAD"),
                                     ("SB_TEST_A8_PA_MOVE", 3, 2, "SW b3 PA moved")):
        fb = os.path.join(work, "build-" + define.lower())
        build(fb, log, *A8_DEFINES, "--define", define)
        r, _, frs, _ = a8_run(work, log, fb, "run-" + define.lower(), seam_keys, 24000)
        fl = [x["label"] for x in frs if x["label"].startswith("SW")]
        f = frs[-1]["fields"] if frs else {}
        if r["run"]["outcome"] != "completed" or fl[-2:] != [label, "SW stopped"] or f.get("sw_state") != 3 \
                or f.get("rt_stop") != stop or f.get("rt_bit") != bit or f.get("rt_check_after") \
                or f.get("rt_con5_back") != f.get("rt_con5_before") or f.get("rt_con0_back", 0x180) & 0x180 \
                or (stop == 2 and (f.get("sw_pa_bits") != 1 << bit or f.get("rt_check_set") != 32)):
            problems.append("audio8 %s: %s, records %s, %s" % (define, r["run"]["outcome"], fl[-3:],
                                                               {k: f.get(k) for k in ("sw_state", "rt_stop", "rt_bit",
                                                                                      "rt_check_set", "rt_check_after",
                                                                                      "sw_pa_bits")}))
    # Port C moving in step 1: kept, the sweep refused, put back by R2's undo.
    fb = os.path.join(work, "build-pc")
    build(fb, log, *A8_DEFINES, "--define", "SB_TEST_A8_PC_MOVE")
    r, _, frs, _ = a8_run(work, log, fb, "run-pc", seam_keys + ((20000, HW_KEY3),), 26000)
    fl = [x["label"] for x in frs if x["label"].split(" ")[0] in ("S1a", "S1b", "S1", "SW", "R2")]
    f = frs[-1]["fields"] if frs else {}
    if r["run"]["outcome"] != "completed" \
            or fl != ["R2 before", "R2 set", "S1a", "S1b before", "S1b kept", "SW refused", "S1 undone", "R2 undone"] \
            or f.get("s1_state") != 4 or f.get("rt_con0_back", 0x180) & 0x180 or f.get("r2_check"):
        problems.append("audio8 port C seam: %s, records %s, %s" % (r["run"]["outcome"], fl,
                                                                    {k: f.get(k) for k in ("s1_state", "rt_con0_back",
                                                                                           "r2_check")}))
    # The unit's 16-bit tone: the image builds and runs; fwtest plays the words in its own layout, so its
    # frames a second, counted as the unit counts them (a word a frame), read twice fwtest's rate.
    pb = os.path.join(work, "build-pcm16")
    build(pb, log, *A8_DEFINES, "--define", "SB_HW_PCM16")
    py = fws.elf_symbols(os.path.join(pb, "app.elf"))["hw_aud"]
    r, pout, prs, _ = a8_run(work, log, pb, "run-pcm16", (), 12000, "--ram", "0x%08x:%d@end" % (py, AUD_LEN))
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(pout, py, AUD_LEN), 8 * AUD_REGS)))
    f = prs[-1]["fields"] if prs else {}
    pfps = e["fps10"] / 10.0 / HW_RATIO
    if r["run"]["outcome"] != "completed" or f.get("a8_pcm16") != 1 or f.get("a8_off") != 0 or e["storm"] \
            or abs(pfps / (2 * AUD_FPS) - 1) > 200e-6:
        problems.append("audio8 16-bit: %s, pcm16 %s, off %s, storm %d, %.1f frames a second (%.1f)"
                        % (r["run"]["outcome"], f.get("a8_pcm16"), f.get("a8_off"), e["storm"], pfps, 2 * AUD_FPS))
    print(summary + "; the forced failed check and port A movement stopped the sweep, undone; the forced port C"
          " movement kept step 1, refused the sweep, and R2's undo put both back; the 16-bit build runs (%.1f frames"
          " a second counted a word a frame)" % pfps)
    return problems


A9_DEFINES = A8_DEFINES + ("--define", "SB_HW_AUDIO9")
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


def case_audio9(a, work, log):
    """audio9 (clean-br17-audio9): at start-up L2, R2 and the route (CON0
    bits 7 and 8, kept on port A's stillness and the matrix check); S2's
    three states; the synth (fm_play, core 0 alone, MIDI off) playing the
    keys into audio.wav with no late half; the old steps' buttons left to
    the engine (no step record, the clock words and JL_IOMAP as read); the
    route down and up by SEQ, port C back as read; PB5 counted, with the
    test seam changing it; the route's self-undo forced by a port A
    movement and by a failed check; and in the 16-bit build each S2
    state's words."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *A9_DEFINES, "--define", "SB_TEST_A9_PB5")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, ga = sy["hw_aud"], sy["hw_guide_at"]
    keys = [(9000, HW_LFO, 100), (10500, HW_LFO, 100), (12000, HW_LFO, 100), (13500, HW_FX, 100),
            (15000, HW_KEY1, 1500), (17000, HW_KEY5, 1500), (17500, HW_KEY3, 1000)]
    # The old steps' buttons and keys: the engine's now (KEY2, KEY4 and KEY6 play notes too).
    keys += [(19000 + 400 * i, k, 100) for i, k in enumerate((HW_OCTUP, HW_OCTDOWN, HW_GLO, HW_ENV, HW_SEL,
                                                              HW_KEY2, HW_KEY4, HW_KEY6))]
    keys += [(24000, HW_SEQ, 100), (29000, HW_SEQ, 100), (34000, HW_FX, 100), (35000, HW_EDIT, 100)]
    r, out, rs, bad = a9_run(work, log, b, "run", keys, 38000, "--wav", "--ram", "0x%08x:4@end" % ga,
                             "--ram", "0x%08x:%d@end" % (h, AUD_LEN))
    if r["run"]["outcome"] != "completed":
        problems.append("audio9: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio9: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    top = HW_LAYOUT_OLD
    if bad or any(x["layout"] != top or not x["known"] or x["count"] != len(rd.FIELDS[top]) for x in rs):
        problems.append("audio9: %d bad records, or one not layout %d with %d fields" % (len(bad), top,
                                                                                       len(rd.FIELDS[top])))
    labels = [x["label"] for x in rs if x["label"] not in ("page", "boot") and not x["label"].startswith("PB5")]
    want = ["L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "S2 upper", "S2 lower",
            "S2 both", "Synth on", "Route down", "R2 undone", "R2 before", "R2 set", "Route before", "Route kept",
            "Synth off", "save key"]
    if labels != want:
        problems.append("audio9: records %s, want %s" % (labels, want))
    steps = [x["label"] for x in rs if x["label"].startswith(A9_STEP_LABELS)]
    if steps:
        problems.append("audio9: old steps' records %s" % steps)
    first, last = (rs[0]["fields"], rs[-1]["fields"]) if rs else ({}, {})
    by = {}
    for x in rs:
        by.setdefault(x["label"], x["fields"])
    if last.get("a9_route") != 1 or last.get("a9_route_ups") != 2 or last.get("a9_route_downs") != 1 \
            or last.get("a9_late_halves") or last.get("a9_fallback_beat") or not last.get("a9_engine_blocks") \
            or last.get("midi_out_bytes") or last.get("a9_synth") or last.get("a9_synth_ons") != 1:
        problems.append("audio9: %s" % {k: last.get(k) for k in ("a9_route", "a9_route_ups", "a9_route_downs",
                                                                 "a9_late_halves", "a9_fallback_beat",
                                                                 "a9_engine_blocks", "midi_out_bytes", "a9_synth",
                                                                 "a9_synth_ons")})
    for k in ("CLK_CON1_now", "d_con5_now"):
        if first.get(k) != last.get(k):
            problems.append("audio9: %s %08x at the start, %08x at the end" % (k, first.get(k, 0), last.get(k, 0)))
    rt = by.get("Route kept", {})
    if rt.get("rt_kind") != 3 or rt.get("rt_check_set") or rt.get("rt_con0_read", 0) & 0x180 != 0x180 \
            or rt.get("rt_con5_before") or rt.get("rt_s1_span_units", 0) < 0.099 * 24000000 \
            or any(rt.get("rt_iomap_before_CON%d" % i) != first.get("MAP%d" % i, rt.get("rt_iomap_before_CON%d" % i))
                   for i in range(2, 9)):
        problems.append("audio9: the route: %s" % {k: rt.get(k) for k in ("rt_kind", "rt_check_set", "rt_con0_read",
                                                                          "rt_con5_before", "rt_s1_span_units")})
    ud = by.get("R2 undone", {})
    if ud.get("r2_check") or any((ud.get("r2_pc_after_%s" % k, 0) ^ ud.get("r2_pc_before_%s" % k, 0))
                                 & ~(0x180 if k == "OUT" else 0) for k in ("OUT", "DIR", "DIE", "PU", "PD", "HD0", "HD")) \
            or ud.get("rt_con0_back", 0x180) & 0x180:
        problems.append("audio9: the route down: %s" % {k: ud.get(k) for k in ud if k.startswith(("r2_pc", "r2_check"))})
    # Main writes a settled level only while it isn't on a page, so fewer are written than seen.
    if last.get("pb5_raw_changes", 0) < 8 or last.get("pb5_logged", 0) < 5:
        problems.append("audio9: PB5 changes %s, written %s (the seam changes it every 1500 beats)"
                        % (last.get("pb5_raw_changes"), last.get("pb5_logged")))
    if last.get("daa7_reads", 0) < 1:
        problems.append("audio9: DAA_CON7 never read")
    gat = struct.unpack("<I", ram(out, ga, 4))[0]
    if gat != 5:
        problems.append("audio9: the guide at %d (5: S2 three times, the synth, a save)" % gat)
    e = dict(zip(AUD_FIELDS, struct.unpack_from("<%dI" % len(AUD_FIELDS), ram(out, h, AUD_LEN), 8 * AUD_REGS)))
    fps = e["fps10"] / 10.0 / HW_RATIO
    if not e["fps10"] or abs(fps / AUD_FPS - 1) > 200e-6 or e["storm"]:
        problems.append("audio9: %.1f frames a second in fwtest's time (%.1f), storm %d" % (fps, AUD_FPS, e["storm"]))
    rate, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    # The WAV starts with the output, not at the script's 0: it ends at the run's end (38 s). KEY1 is held
    # from 15 s to 16.5 s with the synth on; from 22.5 s to 24 s no note is held; the tone is back after 34 s.
    at = lambda t0, t1: max([abs(v) for v in left[len(left) - int((38 - t0) * rate):len(left) - int((38 - t1) * rate)]]
                            or [0])
    during, rest, tone = at(15.3, 16.3), at(22.5, 23.9), at(35, 37.5)
    if left != right or during < 500 or rest or tone < 2000:
        problems.append("audio9: audio.wav: peak %d while KEY1 is held (more than 500), %d with no note held (0), %d"
                        " with the tone back (more than 2000), channels %s"
                        % (during, rest, tone, "alike" if left == right else "differ"))
    summary = ("audio9: L2, R2 and the route at start-up; S2's three states; the synth played KEY1, KEY3 and KEY5"
               " (peak %d in audio.wav), %d engine blocks, %d late halves, MIDI out bytes %d; the old steps' buttons"
               " wrote no step; the route down and up by SEQ; PB5 %d changes, %d written; %d records"
               % (during, last.get("a9_engine_blocks", 0), last.get("a9_late_halves", 0), last.get("midi_out_bytes", 0),
                  last.get("pb5_raw_changes", 0), last.get("pb5_logged", 0), len(rs)))
    # The route's self-undo.
    for define, label, stop in (("SB_TEST_A9_PA_MOVE", "Route PA moved", 2), ("SB_TEST_A9_CHECK_FAIL", "Route check BAD", 3)):
        fb = os.path.join(work, "build-" + define.lower())
        build(fb, log, *A9_DEFINES, "--define", define)
        r, _, frs, _ = a9_run(work, log, fb, "run-" + define.lower(), [], 12000)
        fl = [x["label"] for x in frs if x["label"].startswith(("Route", "R2"))]
        f = frs[-1]["fields"] if frs else {}
        if r["run"]["outcome"] != "completed" or fl != ["R2 before", "R2 set", "Route before", label, "R2 undone"] \
                or f.get("a9_route") != 3 or f.get("rt_stop") != stop or f.get("rt_check_after") \
                or f.get("rt_con0_back", 0x180) & 0x180 or f.get("r2_check"):
            problems.append("audio9 %s: %s, records %s, %s" % (define, r["run"]["outcome"], fl,
                                                               {k: f.get(k) for k in ("a9_route", "rt_stop",
                                                                                      "rt_check_after", "r2_check")}))
    # The 16-bit build: each S2 state's words.
    pb = os.path.join(work, "build-pcm16")
    build(pb, log, *A9_DEFINES, "--define", "SB_HW_PCM16")
    r, _, prs, _ = a9_run(work, log, pb, "run-pcm16", [(9000, HW_LFO, 100), (10500, HW_LFO, 100),
                                                       (12000, HW_LFO, 100)], 14000)
    f = prs[-1]["fields"] if prs else {}
    # Since layout 9 the words are kept by format: P (both), U (upper), L (lower).
    words = {st: [f.get("a9_words_%s_%d" % (n, i), 0) for i in range(4)]
             for st, n in (("both", "P"), ("upper", "U"), ("lower", "L"))}
    ok = (all(w >> 16 == w & 0xFFFF for w in words["both"]) and any(words["both"])
          and all(not w & 0xFFFF for w in words["upper"]) and any(words["upper"])
          and all(not w >> 16 for w in words["lower"]) and any(words["lower"]))
    if r["run"]["outcome"] != "completed" or not ok or f.get("a8_pcm16") != 1:
        problems.append("audio9 16-bit: %s, pcm16 %s, words %s" % (r["run"]["outcome"], f.get("a8_pcm16"),
                                                                   {k: ["%08x" % w for w in v] for k, v in words.items()}))
    print(summary + "; the forced port A movement and failed check undid the route and R2; the 16-bit words: both"
          " %08x, upper %08x, lower %08x" % (words["both"][0], words["upper"][0], words["lower"][0]))
    return problems


A10_DEFINES = A9_DEFINES + ("--define", "SB_HW_AUDIO10")
HW_PLAY, HW_HOME = 12, 8   # fwtest's keys of PLAY and HOME (input.h)
HW_CHORD = (14, 16, 18, 19, 21, 23, 25, 26)   # KEY1, 3, 5, 6, 8, 10, 12, 13: eight keys (fwtest's key numbers)


def case_audio10(a, work, log):
    """audio10 (clean-br17-audio10): F's five formats cycled by LFO, each
    logged; the synth with an 8-key chord (M2's soft clip and M3's
    saturation: the sum never wraps), its fill timed with 8 voices; MASTER
    moved by the script's pot, its value, raw reading and applied levels
    logged; C's holds (zeros, the LED blink, the screen, the log) each on
    and back by its key, and the scan hold ending by itself; the zero key's
    zeros in audio.wav; the tone looked at for a step at any period. Then
    the test builds: 18 dB more into the soft clip; and in the 16-bit build
    each format's words, the clamp of the most negative sample included."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    b = os.path.join(work, "build")
    build(b, log, *A10_DEFINES)
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    h, ga = sy["hw_aud"], sy["hw_guide_at"]
    keys = [(9000 + 1000 * i, HW_LFO, 100) for i in range(5)] + [(14000, HW_FX, 100)]
    keys += [(15000 + 20 * i, k, 3000) for i, k in enumerate(HW_CHORD)] + [(19000, HW_FX, 100)]
    # MASTER's record comes after 1000 still beats, 2.5 s of fwtest's time (HW_RATIO): the pot's moves 3 s apart.
    keys += [(35000, HW_PLAY, 100), (37000, HW_PLAY, 100), (38000, HW_HOME, 100), (39000, HW_HOME, 100),
             (40000, HW_ENV, 100), (41000, HW_ENV, 100), (42000, HW_GLO, 100), (43000, HW_GLO, 100),
             (44000, HW_REC, 100), (58000, HW_EDIT, 100)]
    path = os.path.join(work, "run.script")
    with open(path, "w") as f:
        for t, k, d in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + d, k))
        for t, v in ((20000, 900), (23000, 600), (26000, 300), (29000, 100), (32000, 1000)):
            f.write("%d pot %d\n" % (t, v))
    out = os.path.join(work, "run")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "61000", "--flash-out", "--wav",
               "--script", os.path.relpath(path, ROOT), "--ram", "0x%08x:4@end" % ga,
               "--ram", "0x%08x:%d@end" % (h, AUD_LEN))
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    if r["run"]["outcome"] != "completed":
        problems.append("audio10: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio10: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    top = HW_LAYOUT_OLD
    if bad or any(x["layout"] != top or not x["known"] or x["count"] != len(rd.FIELDS[top]) for x in rs):
        problems.append("audio10: %d bad records, or one not layout %d with %d fields" % (len(bad), top,
                                                                                         len(rd.FIELDS[top])))
    labels = [x["label"] for x in rs if x["label"] not in ("page", "boot", "MASTER still")
              and not x["label"].startswith("PB5")]
    want = ["L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "F L", "F N", "F N'", "F P",
            "F U", "Synth on", "Synth off", "ZERO on", "zero off", "LED HELD", "LED blink on", "SCREEN HELD",
            "screen on", "LOG HELD", "log on", "SCAN HELD", "scan hold end", "save key"]
    if labels != want:
        problems.append("audio10: records %s, want %s" % (labels, want))
    last = rs[-1]["fields"] if rs else {}
    stills = [x["fields"]["m_value"] for x in rs if x["label"] == "MASTER still"]
    ring = [last.get("m_ring_%d" % (k % 40), 0) & 0x3FF for k in range(max(0, last.get("m_ring_n", 0) - 40),
                                                                      last.get("m_ring_n", 0))]
    if last.get("a10_fmt_changes") != 5 or last.get("a9_s2") != 1 or last.get("holds") or last.get("hold_n") != 10 \
            or last.get("a10_voices_max") != 8 or not last.get("a10_fill_max8_units") or last.get("a9_late_halves") \
            or last.get("a10_saturated") or last.get("log_dropped"):
        problems.append("audio10: %s" % {k: last.get(k) for k in ("a10_fmt_changes", "a9_s2", "holds", "hold_n",
                                                                  "a10_voices_max", "a10_fill_max8_units",
                                                                  "a9_late_halves", "a10_saturated", "log_dropped")})
    # fwtest moves the pot in steps the scan sees on the way; each pause leaves a record at its value.
    if any(not any(abs(v - p) <= 8 for v in stills) for p in (600, 300, 100, 1000)) or len(ring) < 8:
        problems.append("audio10: MASTER's still records %s (600, 300, 100, 1000), changes %s" % (stills, ring))
    gat = struct.unpack("<I", ram(out, ga, 4))[0]
    if gat != 16:
        problems.append("audio10: the guide at %d (16)" % gat)
    rate, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    at = lambda t0, t1: left[len(left) - int((61 - t0) * rate):len(left) - int((61 - t1) * rate)]
    chord, zero, tone = at(15.5, 17.9), at(35.4, 36.8), at(5, 8.5)
    jump = max(abs(chord[i + 1] - chord[i]) for i in range(len(chord) - 1)) if chord else 0
    d2 = max(abs(tone[i + 1] - 2 * tone[i] + tone[i - 1]) for i in range(1, len(tone) - 1)) if tone else 0
    if left != right or not chord or max(abs(v) for v in chord) < 500 or jump > 16000 or any(zero) or d2 > 100:
        problems.append("audio10: audio.wav: chord peak %d, largest step %d (a wrap is near 65535); %d non-zero"
                        " samples while zeros held; the tone's largest second difference %d (a 440 Hz sine at its"
                        " level about 13)" % (max([abs(v) for v in chord] or [0]), jump, sum(1 for v in zero if v),
                                              d2))
    summary = ("audio10: F's five formats cycled and logged; the 8-key chord with %d voices, peak %d, largest step %d,"
               " longest fill with 8 voices %.1f us; MASTER %s logged, %d raw jumps; the holds on and back, the scan"
               " hold ended by itself; zeros while held; the tone's largest second difference %d (no step at any"
               " period)" % (last.get("a10_voices_max", 0), max([abs(v) for v in chord] or [0]), jump,
                             last.get("a10_fill_max8_units", 0) / 24.0, stills, last.get("m_raw_jumps", 0), d2))
    # 18 dB more into M2: the soft clip bends the chord, nothing saturates or wraps.
    gb = os.path.join(work, "build-gain")
    build(gb, log, *A10_DEFINES, "--define", "SB_TEST_A10_GAIN")
    gkeys = [(9000, HW_FX, 100)] + [(10000 + 20 * i, k, 3000) for i, k in enumerate(HW_CHORD)] + [(14000, HW_EDIT, 100)]
    r, gout, grs, _ = a9_run(work, log, gb, "run-gain", gkeys, 16000, "--wav")
    gl = aa.read_wav(os.path.join(gout, "audio.wav"))[1]
    gc = gl[len(gl) - int(5.5 * rate):len(gl) - int(3.2 * rate)]
    gjump = max(abs(gc[i + 1] - gc[i]) for i in range(len(gc) - 1)) if gc else 0
    gf = grs[-1]["fields"] if grs else {}
    if r["run"]["outcome"] != "completed" or not gf.get("a10_soft_clipped") or gf.get("a10_saturated") \
            or max([abs(v) for v in gc] or [0]) >= 32767 or gjump > 16000:
        problems.append("audio10 gain: %s, soft %s, saturated %s, peak %d, largest step %d" % (
            r["run"]["outcome"], gf.get("a10_soft_clipped"), gf.get("a10_saturated"),
            max([abs(v) for v in gc] or [0]), gjump))
    # The 16-bit build: each format's words, each half's first sample forced to the most negative.
    pb = os.path.join(work, "build-pcm16")
    build(pb, log, *A10_DEFINES, "--define", "SB_HW_PCM16", "--define", "SB_TEST_A10_CLAMP")
    # The words of each format are those of its halves after the switch: a save at the end carries P's.
    r, _, prs, _ = a9_run(work, log, pb, "run-pcm16", [(9000 + 1500 * i, HW_LFO, 100) for i in range(4)]
                          + [(15500, HW_EDIT, 100)], 17000)
    f = prs[-1]["fields"] if prs else {}
    words = {fm: [f.get("a9_words_%s_%d" % (fm, i), 0) for i in range(4)] for fm in ("P", "U", "L", "N", "N'")}
    first = {"P": 0x80008000, "U": 0x80000000, "L": 0x00008000, "N": 0x80007FFF, "N'": 0x7FFF8000}
    neg = lambda x: (-((x ^ 0x8000) - 0x8000)) & 0xFFFF
    rule = {"P": lambda w: w >> 16 == w & 0xFFFF, "U": lambda w: not w & 0xFFFF, "L": lambda w: not w >> 16,
            "N": lambda w: w & 0xFFFF == neg(w >> 16), "N'": lambda w: w >> 16 == neg(w & 0xFFFF)}
    bad_fmt = [fm for fm, ws in words.items() if ws[0] != first[fm] or not all(rule[fm](w) for w in ws[1:])
               or not any(ws[1:])]
    if r["run"]["outcome"] != "completed" or bad_fmt or f.get("a8_pcm16") != 1:
        problems.append("audio10 16-bit: %s, formats wrong %s: %s" % (r["run"]["outcome"], bad_fmt,
                                                                      {k: ["%08x" % w for w in v]
                                                                       for k, v in words.items()}))
    print(summary + "; with 18 dB more the soft clip bent %d samples, none saturated, peak %d; the 16-bit words: %s"
          % (gf.get("a10_soft_clipped", 0), max([abs(v) for v in gc] or [0]),
             ", ".join("%s %08x %08x" % (k, v[0], v[1]) for k, v in words.items())))
    return problems


A11_DEFINES = A10_DEFINES + ("--define", "SB_HW_AUDIO11")


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


def case_audio11(a, work, log):
    """audio11 (clean-br17-audio11): N from start-up, the only format (LFO
    the engine's); the SARADC through the service: the SDK's three CON
    writes, the old one by SEL and back, each conversion waited for with
    bit 7 held back 300 us by the test seam (no time-out, the times
    logged), the sweep leaving out channels 6 and 7 while the route is up
    (and 2, 8, 9 always), each channel's values counted; MASTER turned in
    each set-up, its curve (the square) and the tone's level ramped over a
    half (no step in audio.wav as it moves); audio10's holds on and back,
    the scan hold ending by itself, the zeros in audio.wav; an 8-key chord,
    the fill per algorithm; the large area read off the screen in each
    state. Then the 16-bit build: N's words from start-up, the clamp
    included, and fwtest's own conversion time."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    glyphs = font_glyphs()
    b = os.path.join(work, "build")
    build(b, log, *A11_DEFINES, "--define", "SB_TEST_A11_SLOW")
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    ga = sy["hw_guide_at"]
    keys = [(19000, HW_HOME, 100), (20000, HW_HOME, 100), (21000, HW_ENV, 100), (22000, HW_ENV, 100),
            (23000, HW_GLO, 100), (24000, HW_GLO, 100), (25000, HW_REC, 100), (39000, HW_PLAY, 100),
            (41000, HW_PLAY, 100), (42000, HW_SEL, 100), (49000, HW_SEL, 100), (50000, HW_FX, 100)]
    keys += [(51000 + 20 * i, k, 3000) for i, k in enumerate(HW_CHORD)] + [(55000, HW_FX, 100), (56000, HW_EDIT, 100)]
    pots = ((10000, 900), (13000, 600), (16000, 300), (43000, 800), (46000, 200))
    path = os.path.join(work, "run.script")
    with open(path, "w") as f:
        for t, k, d in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + d, k))
        for t, v in pots:
            f.write("%d pot %d\n" % (t, v))
    # The large area's level: MASTER's square in whole per cent (300: 8 %, 200: 3 %); the scan hold's line
    # ends with its countdown, so lines are compared by their start.
    shots = {18500: ("N TONE SDK", "M300 r300", "L8% -"), 19500: ("N TONE SDK", None, "L8% LED"),
             30000: ("N TONE SDK", None, "L8% SCAN"), 40000: ("N TONE SDK", None, "L8% ZERO"),
             48000: ("N TONE OLD", "M200 r200", "L3% -"), 53000: ("N SYNTH SDK", None, "L3% -")}
    out = os.path.join(work, "run")
    lcd = [x for t in sorted(shots) for x in ("--lcd", str(t))]
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "58000", "--flash-out", "--wav",
               "--script", os.path.relpath(path, ROOT), "--ram", "0x%08x:4@end" % ga, *lcd)
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    if r["run"]["outcome"] != "completed":
        problems.append("audio11: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    acc = {u["address"] for u in r["run"]["unmodelled_accesses"]}
    odd = sorted(acc - HW_WINDOW_REGS - {"0x00012f00"} - GPCNT_REGS - ALNK1_REGS)
    if odd:
        problems.append("audio11: unmodelled accesses besides the window's, corex2's, DAC_CON, JL_GPCNT and ALNK1: %s"
                        % odd[:8])
    if bad or any(x["layout"] != 10 or not x["known"] or x["count"] != len(rd.FIELDS[10]) for x in rs):
        problems.append("audio11: %d bad records, or one not layout 10 with %d fields" % (len(bad), len(rd.FIELDS[10])))
    labels = [x["label"] for x in rs if x["label"] not in ("page", "boot", "MASTER still")
              and not x["label"].startswith("PB5")]
    want = ["L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "LED HELD", "LED blink on",
            "SCREEN HELD", "screen on", "LOG HELD", "log on", "SCAN HELD", "scan hold end", "ZERO on", "zero off",
            "ADC old", "ADC SDK", "Synth on", "Synth off", "save key"]
    if labels != want:
        problems.append("audio11: records %s, want %s" % (labels, want))
    last = rs[-1]["fields"] if rs else {}
    g = lambda k: last.get(k, 0)
    sdk_con = (0xF44E, 0xF45E, 0xF45E)
    if g("a9_s2") != 3 or g("a10_fmt_changes") or g("adc_setup") or g("adc_set_n") != 2 or g("holds") \
            or g("hold_n") != 10 or g("log_dropped") or g("a10_saturated") or g("a9_late_halves") \
            or g("adc_conv_timeouts_SDK") or g("adc_conv_timeouts_old") \
            or min(g("adc_conv_min_units_SDK"), g("adc_conv_min_units_old")) < 300 * 24 \
            or min(g("adc_conv_tight_units_SDK"), g("adc_conv_tight_units_old")) < 300 * 24 \
            or tuple(g("sar_con_SDK_w%d" % i) for i in (1, 2, 3)) != sdk_con or g("sar_con_old_w1") != 0x450 \
            or g("sar_con_old_w2") or g("m_level") != 200 * 200 * 100 // 10465:
        problems.append("audio11: %s" % {k: last.get(k) for k in (
            "a9_s2", "a10_fmt_changes", "adc_setup", "adc_set_n", "holds", "hold_n", "log_dropped", "a10_saturated",
            "a9_late_halves", "adc_conv_timeouts_SDK", "adc_conv_timeouts_old", "adc_conv_min_units_SDK",
            "adc_conv_min_units_old", "adc_conv_tight_units_SDK", "adc_conv_tight_units_old", "sar_con_SDK_w1",
            "sar_con_SDK_w2", "sar_con_SDK_w3", "sar_con_old_w1", "sar_con_old_w2", "m_level")})
    # The channels: MASTER (4) moved, 3 at fwtest's 640, the others 512; 6 and 7 never (the route up throughout).
    ch = lambda st, c, w: g("adc_%s_ch%d_%s" % (st, c, w))
    chans = []
    for st in ("SDK", "old"):
        if not ch(st, 4, "n") or ch(st, 3, "v0") >> 22 != 640 or ch(st, 0, "v0") >> 22 != 512 \
                or ch(st, 6, "n") or ch(st, 7, "n") or not ch(st, 11, "n"):
            chans.append(st)
    if chans:
        problems.append("audio11: the channels in %s: %s" % (chans, {k: v for k, v in last.items()
                                                                   if k.startswith("adc_") and "_ch" in k and v}))
    stills = {}
    for x in rs:
        if x["label"] == "MASTER still":
            stills.setdefault(x["fields"]["adc_setup"], []).append(x["fields"]["m_value"])
    if any(not any(abs(v - p) <= 8 for v in stills.get(st, [])) for st, p in ((0, 600), (0, 300), (1, 800), (1, 200))):
        problems.append("audio11: MASTER's still records by set-up %s (SDK 600, 300; old 800, 200)" % stills)
    fills = [(k, g("fill_alg_%d" % k)) for k in range(1, 11) if g("fill_alg_%d" % k)]
    if not any(w >> 16 for _, w in fills) or g("a10_voices_max") != 8:
        problems.append("audio11: the fill per algorithm %s, voices %d" % (fills, g("a10_voices_max")))
    gat = struct.unpack("<I", ram(out, ga, 4))[0]
    if gat != 13:
        problems.append("audio11: the guide at %d (13)" % gat)
    big_bad = {}
    big_seen = {}
    for t, want_big in sorted(shots.items()):
        png = os.path.join(out, "lcd-%dms.png" % t)
        got = read_big(fws, png, glyphs) if os.path.exists(png) else ["(no screen)"] * 3
        big_seen[t] = got
        if any(w is not None and not gl.startswith(w) for gl, w in zip(got, want_big)):
            big_bad[t] = (got, want_big)
    if big_bad:
        problems.append("audio11: the large area %s" % big_bad)
    # The save's record (the synth off again, MASTER at 200 in the SDK's set-up) carries the area as drawn then.
    if bad or not rs or [x.rstrip() for x in rd.big_text(last)] != ["N TONE SDK", "M200 r200", "L3% -"]:
        problems.append("audio11: the large area's log at the save %s" % rd.big_text(last))
    rate, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    at = lambda t0, t1: left[len(left) - int((58 - t0) * rate):len(left) - int((58 - t1) * rate)]
    tone, zero, chord = at(9.5, 17.5), at(39.5, 40.8), at(51.5, 53.9)
    d2 = max(abs(tone[i + 1] - 2 * tone[i] + tone[i - 1]) for i in range(1, len(tone) - 1)) if tone else 0
    if left != right or not tone or d2 > 120 or any(zero) or not chord or max(abs(v) for v in chord) < 500:
        problems.append("audio11: audio.wav: the tone's largest second difference %d with MASTER moving (a 440 Hz"
                        " sine at the top about 13); %d non-zero samples while zeros held; chord peak %d"
                        % (d2, sum(1 for v in zero if v), max([abs(v) for v in chord] or [0])))
    summary = ("audio11: N from start-up; SDK CON %04X %04X %04X (read back %04X), old %04X (read back %04X); bit 7"
               " held 300 us by the seam: conversions %d and %d, none timed out, %.1f us at least; channels 6 and 7"
               " never read with the route up; MASTER's stills %s; level %d of 10000; the tone's largest second"
               " difference %d with MASTER moving; zeros while held; the large area %s"
               % (g("sar_con_SDK_w1"), g("sar_con_SDK_w2"), g("sar_con_SDK_w3"), g("sar_con_SDK_read"),
                  g("sar_con_old_w1"), g("sar_con_old_read"), g("adc_conv_n_SDK"), g("adc_conv_n_old"),
                  min(g("adc_conv_min_units_SDK"), g("adc_conv_min_units_old")) / 24.0, stills, g("m_level"), d2,
                  big_seen))
    # The 16-bit build: N's words from start-up (the clamp: each half's first sample the most negative), no seam.
    pb = os.path.join(work, "build-pcm16")
    build(pb, log, *A11_DEFINES, "--define", "SB_HW_PCM16", "--define", "SB_TEST_A10_CLAMP")
    r, _, prs, _ = a9_run(work, log, pb, "run-pcm16", [(11000, HW_LFO, 100), (12000, HW_EDIT, 100)], 14000)
    f = prs[-1]["fields"] if prs else {}
    nw = [f.get("a9_words_N_%d" % i, 0) for i in range(4)]
    others = [f.get("a9_words_%s_%d" % (fm, i), 0) for fm in ("P", "U", "L", "N'") for i in range(4)]
    neg = lambda x: (-((x ^ 0x8000) - 0x8000)) & 0xFFFF
    if r["run"]["outcome"] != "completed" or nw[0] != 0x80007FFF or not all(w & 0xFFFF == neg(w >> 16) for w in nw[1:]) \
            or not any(nw[1:]) or any(others) or f.get("a9_s2") != 3 or f.get("a8_pcm16") != 1 \
            or f.get("adc_conv_timeouts_SDK"):
        problems.append("audio11 16-bit: %s, N %s, others %s, format %s, time-outs %s"
                        % (r["run"]["outcome"], ["%08x" % w for w in nw], any(others), f.get("a9_s2"),
                           f.get("adc_conv_timeouts_SDK")))
    print(summary + "; the 16-bit build: N's words %s (LFO left to the engine), fwtest's own conversion %.1f us by"
          " the tight poll, %.1f to %.1f us by the slot" % (
              " ".join("%08x" % w for w in nw), f.get("adc_conv_tight_units_SDK", 0) / 24.0,
              f.get("adc_conv_min_units_SDK", 0) / 24.0, f.get("adc_conv_max_units_SDK", 0) / 24.0))
    return problems



A12_DEFINES = A11_DEFINES + ("--define", "SB_HW_AUDIO12")
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


def case_audio12(a, work, log):
    """audio12 (clean-br17-audio12). D5: with no key held the instrument's
    own start brings up L2, port C's pins, the route and N with the synth,
    then the panel (no test screen; the test screen's keys do nothing); its
    self-undo forced, the instrument still runs and the panel and the log
    say why; HOME held at power-on gives the test screen. S: LFO plays an
    8-note chord in each algorithm 1 to 10 (a short chord in the test
    build), each one's longest fill with 8 voices, no clip or late half,
    each release ended; the large area shows the sweep; a second sweep
    stopped by LFO after its chord, every voice released. G: every note
    on's ALGORITHM read equals the voice's, an ALGORITHM turn taken; the
    sweep's ten chords differ in audio.wav in Bell (G2's start patch) and
    are identical in Sine (patch 0, the unit's start patch before). D6:
    ARP's steps 1/16 apart in frames on fwtest's layout and on the unit's
    (two engine blocks a half), where the interrupt count gave half."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    glyphs = font_glyphs()
    b = os.path.join(work, "build")
    build(b, log, *A12_DEFINES, "--define", "SB_TEST_A12_SHORT")
    # The test screen (power-on, audio12b); a sweep; ALGORITHM turned and a note; a sweep stopped by LFO.
    keys = [(12000, HW_LFO, 100), (24000, HW_EDIT, 100), (25000, HW_KEY1, 300),
            (26000, HW_LFO, 100), (26300, HW_LFO, 100), (32000, HW_EDIT, 100)]
    path = os.path.join(work, "test.script")
    with open(path, "w") as f:
        for t, k, d in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + d, k))
        f.write("24500 enc %d +1\n" % HW_ALG_ENC)
    shots = (14000, 21000)
    out = os.path.join(work, "test")
    r = fwtest(os.path.join(b, "app.bin"), out, log, "--ms", "33000", "--flash-out", "--wav",
               "--script", os.path.relpath(path, ROOT), *[x for t in shots for x in ("--lcd", str(t))])
    with open(os.path.join(out, "flash.bin"), "rb") as f:
        rs, bad = rd.records(f.read())
    if r["run"]["outcome"] != "completed":
        problems.append("audio12 test screen: %s (%s)" % (r["run"]["outcome"], r["run"].get("detail")))
    if bad or any(x["layout"] != 11 or not x["known"] or x["count"] != len(rd.FIELDS[11]) for x in rs):
        problems.append("audio12: %d bad records, or one not layout 11 with %d fields" % (len(bad), len(rd.FIELDS[11])))
    labels = [x["label"] for x in rs if x["label"] != "MASTER still" and not x["label"].startswith("PB5")]
    want = ["boot", "L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "page", "Synth on",
            "Sweep start", "Sweep done", "save key", "Sweep start", "Sweep stop asked", "Sweep stopped", "save key"]
    if labels != want:
        problems.append("audio12 test screen: records %s, want %s" % (labels, want))
    done = next((x["fields"] for x in rs if x["label"] == "Sweep done"), {})
    last = rs[-1]["fields"] if rs else {}
    g = lambda f, k: f.get(k, 0)
    fills = [g(done, "as_fill_%d" % k) for k in range(1, 11)]
    if g(done, "start_mode") != 2 or g(done, "as_state") != 3 or g(done, "as_chords") != 10 \
            or any(w >> 16 != 8 or not w & 0xFFFF for w in fills) \
            or any(g(done, "as_%s_%d" % (w, k)) for w in ("soft", "hard", "late") for k in range(1, 11)) \
            or any(g(done, "as_rel_frames_%d" % k) >> 31 or not g(done, "as_rel_frames_%d" % k) for k in range(1, 11)):
        problems.append("audio12 sweep: %s" % "; ".join(l for l in rd.derived(done) if l.startswith(("audio12", "  A"))))
    k = g(last, "as_chords") - 10
    if g(last, "as_state") != 4 or k not in (1, 2) or g(last, "as_alg") != k or not g(last, "as_stop") \
            or g(last, "as_rel_frames_%d" % k) >> 31 or not g(last, "as_rel_frames_%d" % k):
        problems.append("audio12 stop: state %d, chords %d, algorithm %d, release %x" % (
            g(last, "as_state"), g(last, "as_chords"), g(last, "as_alg"), g(last, "as_rel_frames_%d" % max(k, 1))))
    # G: each note on's ALGORITHM read and the voice's; the sweep's chords in order; the turn (A10 + 1 = A1) and KEY1.
    n = g(last, "g_note_n")
    notes = [g(last, "g_note_%d" % (i % 16)) for i in range(max(0, n - 16), n)]
    if g(done, "g_note_n") != 80 or n != 80 + 1 + 8 * k or g(last, "g_turns") != 1 or g(last, "g_turns_off") \
            or g(last, "g_turn_alg") != 1 or any(w >> 8 & 0xFF != w >> 1 & 0x7F or not w & 1 for w in notes) \
            or (w := notes[-9 if k == 1 else -17]) >> 24 != 53 or w >> 8 & 0xFF != 1:
        problems.append("audio12 G: %s" % [l for l in rd.derived(last) if l.startswith("  G")])
    big = {}
    for t, want_big in zip(shots, (("SWEEP A", "F"), ("DONE A", "F"))):
        png = os.path.join(out, "lcd-%dms.png" % t)
        got = read_big(fws, png, glyphs) if os.path.exists(png) else ["(no screen)"] * 3
        big[t] = got
        if not got[0].startswith(want_big[0]) or not re.match(r"F\d+US 8V$", got[1]):
            problems.append("audio12: the large area at %d ms %s" % (t, got))
    rate, left, right = aa.read_wav(os.path.join(out, "audio.wav"))
    runs = runs_between(left, rate, 33000, 12000, 24000)
    first = [tuple(left[s0:s0 + 8000]) for s0, _ in runs]
    if len(first) != 10 or len(set(first)) != 10:
        problems.append("audio12 G2: Bell's sweep in audio.wav: %d runs, %d distinct of the first ten" % (
            len(runs), len(set(first))))
    # G's check: the same sweep from Sine (patch 0): ten identical chords.
    zb = os.path.join(work, "build-sine")
    build(zb, log, *A12_DEFINES, "--define", "SB_TEST_A12_SHORT", "--define", "SB_TEST_A12_SINE")
    zpath = os.path.join(work, "sine.script")
    with open(zpath, "w") as f:
        f.write("12000 key %d down\n12100 key %d up\n" % (HW_LFO, HW_LFO))
    zout = os.path.join(work, "sine")
    zr = fwtest(os.path.join(zb, "app.bin"), zout, log, "--ms", "22000", "--wav", "--script", os.path.relpath(zpath, ROOT))
    _, zl, _ = aa.read_wav(os.path.join(zout, "audio.wav"))
    zruns = runs_between(zl, rate, 22000, 12000, 22000)
    zfirst = [tuple(zl[s0:s0 + 8000]) for s0, _ in zruns]
    if zr["run"]["outcome"] != "completed" or len(zfirst) != 10 or len(set(zfirst)) != 1:
        problems.append("audio12 G: Sine's sweep: %d runs, %d distinct of the first ten (want 1)" % (
            len(zruns), len(set(zfirst))))
    # D5 (audio12b): SEL on the test screen runs the instrument's start, a record before each stage; KEY1 plays;
    # FX, SEQ and EDIT (the test screen's) do nothing then.
    sy = fws.elf_symbols(os.path.join(b, "app.elf"))
    ipath = os.path.join(work, "inst.script")
    with open(ipath, "w") as f:
        for t, key in ((9000, HW_SEL), (12000, HW_KEY1), (13000, HW_FX), (13500, HW_SEQ), (14000, HW_EDIT)):
            f.write("%d key %d down\n%d key %d up\n" % (t, key, t + (100 if key == HW_SEL else 300), key))
    iout = os.path.join(work, "inst")
    ir = fwtest(os.path.join(b, "app.bin"), iout, log, "--ms", "15000", "--flash-out", "--wav", "--lcd", "14900",
                "--script", os.path.relpath(ipath, ROOT), "--ram", "0x%08x:8@end" % sy["sb_ui"])
    with open(os.path.join(iout, "flash.bin"), "rb") as f:
        irs, ibad = rd.records(f.read())
    ilabels = [x["label"] for x in irs if x["label"] != "MASTER still" and not x["label"].startswith("PB5")]
    ib = irs[-1]["fields"] if irs else {}
    ui_marker, ui_screen = struct.unpack("<2I", ram(iout, sy["sb_ui"], 8))
    _, il, _ = aa.read_wav(os.path.join(iout, "audio.wav"))
    played = il[len(il) - int(2.9 * rate):len(il) - int(2.5 * rate)]
    if ir["run"]["outcome"] != "completed" or ibad or ilabels != [
            "boot", "L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "page", "Inst synth",
            "Synth on", "Inst ALNK0", "Inst L2", "Inst R2", "Inst route", "Inst panel"] \
            or g(ib, "start_mode") != 1 or g(ib, "a9_route") != 1 or g(ib, "a9_synth") != 1 \
            or rd.big_text(ib)[0] != "audio12: sound o" or ui_marker != 0x38495553 or not played \
            or max(abs(v) for v in played) < 100:
        problems.append("audio12 D5: %s, records %s, mode %d route %d synth %d, line %s, panel marker %x, KEY1 peak %d"
                        % (ir["run"]["outcome"], ilabels, g(ib, "start_mode"), g(ib, "a9_route"), g(ib, "a9_synth"),
                           rd.big_text(ib), ui_marker, max([abs(v) for v in played] or [0])))
    # D5's self-undo, forced: the route's check fails (at power-on and again at SEL's start); the instrument runs,
    # silent, and says why.
    ub = os.path.join(work, "build-undo")
    build(ub, log, *A12_DEFINES, "--define", "SB_TEST_A9_CHECK_FAIL")
    usy = fws.elf_symbols(os.path.join(ub, "app.elf"))
    uout = os.path.join(work, "undo")
    upath = os.path.join(work, "undo.script")
    with open(upath, "w") as f:
        f.write("9000 key %d down\n9100 key %d up\n" % (HW_SEL, HW_SEL))
    ur = fwtest(os.path.join(ub, "app.bin"), uout, log, "--ms", "13000", "--flash-out", "--lcd", "12900",
                "--script", os.path.relpath(upath, ROOT), "--ram", "0x%08x:8@end" % usy["sb_ui"])
    with open(os.path.join(uout, "flash.bin"), "rb") as f:
        urs, _ = rd.records(f.read())
    ubf = urs[-1]["fields"] if urs else {}
    uline = "".join(rd.big_text(ubf))
    umarker = struct.unpack("<2I", ram(uout, usy["sb_ui"], 8))[0]
    if ur["run"]["outcome"] != "completed" or not urs or urs[-1]["label"] != "Inst panel" or g(ubf, "a9_route") != 3 \
            or not uline.startswith("NO SOUND: ") or umarker != 0x38495553:
        problems.append("audio12 D5 undo: %s, last %s, route %d, line %r, panel marker %x" % (
            ur["run"]["outcome"], urs[-1]["label"] if urs else None, g(ubf, "a9_route"), uline, umarker))
    # D6: ARP's steps in frames, fwtest's layout and the unit's.
    arp = {}
    for name, bb in (("arp", b), ("arp-pcm16", None)):
        if bb is None:
            bb = os.path.join(work, "build-pcm16")
            build(bb, log, *A12_DEFINES, "--define", "SB_HW_PCM16")
        ar, diffs, steps = a12_arp(work, log, bb, name)
        arp[name] = (diffs, steps)
        if ar["run"]["outcome"] != "completed" or len(diffs) < 8 or any(abs(d - 5514) > 2 for d in diffs):
            problems.append("audio12 D6 %s: %s, %d steps, frames between %s (5514 +-2)" % (
                name, ar["run"]["outcome"], steps, diffs[:12]))
    # The unit's file (audio12b): the candidate's build (the 16-bit layout, no test seams, the full hold), packed
    # from the package link as the unit runs it (0x02000120, HW-91), through fwtest's package path past the start's
    # bands (to the audio page, at fwtest's slower slots); the raw link (0x02000000) packed the same way stops at
    # the first two bands, blue and green, as audio12's file did on the unit (#240).
    cb = os.path.join(work, "build-unit")
    build(cb, log, "--define", "SB_HW_FM1", "--define", "SB_HW_HOLD", "--define", "SB_HW_AUDIO1", "--define",
          "SB_HW_REPORT", "--define", "SB_HW_AUDIO8", "--define", "SB_HW_PCM16", "--define", "SB_HW_AUDIO9",
          "--define", "SB_HW_AUDIO10", "--define", "SB_HW_AUDIO11", "--define", "SB_HW_AUDIO12")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    pk = {}
    for link in ("app-pkg", "app"):
        path = os.path.join(work, "unit-%s.fwsc" % link)
        with open(path, "wb") as f:
            f.write(fwsc.pack(read_bytes(os.path.join(cb, link + ".bin")), "FM-1_0.12.1-hw3w"))
        pout = os.path.join(work, "unit-" + link)
        pr = fwtest(path, pout, log, "--package", "--ms", "40000", "--lcd", "39900")
        png = os.path.join(pout, "lcd-39900ms.png")
        bands = None
        if os.path.exists(png):
            _, _, rows = fws.read_png(png)
            # The bands as the raw link leaves them: blue across row 72, green across row 96.
            bands = all(rows[72][x][:3] == (0, 0, 255) and rows[96][x][:3] == (0, 255, 0) for x in range(0, 240, 16))
        pk[link] = (pr["run"]["outcome"], bands)
    if pk["app-pkg"][0] != "completed" or pk["app-pkg"][1] is not False or pk["app"][1] is not True:
        problems.append("audio12 unit file: the package link %s, the raw link %s (outcome, still at the two bands)"
                        % (pk["app-pkg"], pk["app"]))
    print("audio12: the unit's build packed: the package link past the bands: %s; the raw link stopped at them: %s"
          % (pk["app-pkg"][1] is False, pk["app"][1]))
    print("audio12: test screen; the sweep in Bell: longest fills (us) %s with 8 voices, releases %s"
          " frames, no clip or late half; stopped after chord %d of the second; G: %d note ons, read = voice's, a turn"
          " taken; Bell's ten chords distinct, Sine's identical (%d distinct); the large area %s; D5: SEL's start"
          " (records before each stage, panel, route up, KEY1 peak %d), its self-undo: %r; D6: ARP steps %s frames apart (fwtest's layout), %s"
          " (the unit's)" % (
              [(w & 0xFFFF) / 10.0 for w in fills], sorted({g(done, "as_rel_frames_%d" % k) for k in range(1, 11)}),
              k, g(last, "g_note_n"), len(set(zfirst)), big, max([abs(v) for v in played] or [0]), uline,
              sorted(set(arp["arp"][0])), sorted(set(arp["arp-pcm16"][0]))))
    return problems


A13_DEFINES = A12_DEFINES + ("--define", "SB_HW_AUDIO13")
A13_INST = ["boot", "Inst engine", "Inst synth", "Synth on", "Inst ALNK0", "Inst L2", "L2 before", "L2 kept",
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


def case_audio13(a, work, log):
    """audio13 (clean-br17-audio13). D5: with nothing held the instrument's
    start runs from cold (the engine, the synth, ALNK0, L2, R2, the route,
    a record before each stage) to the panel with sound, no test screen;
    its self-undo forced, the panel runs silent and says why; HOME held
    gives the test screen. U2-A: the USB block's five words read at the
    app's start and a second later, before the audio path (0 audio blocks),
    in both starts' boot records, and on OCT- in the test screen only.
    U2-B: SAVE steps the cable state a to e, each mark and each change of a
    word logged with its beat (a change made by the test seam), the large
    area "SAME AS A" or "CHANGED C0". U2-C: off at start-up, OCT+ puts
    channels 12 and 13 in the SARADC's sweep and takes them out. ARP: on
    from the panel, its steps 5514 frames apart on both layouts, each
    step's frame count and sb_now logged, REC's save in the panel. The
    unit's build, packed from the package link, runs past the start's
    bands through fwtest's package path; the raw link stops at them."""
    problems = []
    fws = fw_suite()
    rd = report_decoder()
    glyphs = font_glyphs()
    g = lambda f, k: f.get(k, 0)
    words = lambda f, pre: tuple(g(f, "%s_%s" % (pre, w)) for w in rd.A13_WORDS)
    # D5 and ARP: power-on, fwtest's layout and the unit's.
    arp = {}
    for name, extra in (("cold", ()), ("cold-pcm16", ("--define", "SB_HW_PCM16"))):
        b = os.path.join(work, "build-" + name)
        build(b, log, *A13_DEFINES, *extra)
        sy = fws.elf_symbols(os.path.join(b, "app.elf"))
        r, rs, bad, left, rate, marker = a13_cold(work, log, b, name, sy)
        labels = a13_labels(rs)
        boot = rs[0]["fields"] if rs else {}
        last = rs[-1]["fields"] if rs else {}
        panel = next((x["fields"] for x in rs if x["label"] == "Inst panel"), {})
        played = left[len(left) - int(13.5 * rate):len(left) - int(13.2 * rate)]
        if r["run"]["outcome"] != "completed" or bad or any(x["layout"] != 12 or x["count"] != len(rd.FIELDS[12])
                                                             for x in rs):
            problems.append("audio13 %s: %s, %d bad records, layouts %s" % (
                name, r["run"]["outcome"], len(bad), sorted({(x["layout"], x["count"]) for x in rs})))
        if labels != A13_INST + ["Panel save"] or g(panel, "a13_start") != 1 or g(panel, "start_mode") != 1 \
                or g(panel, "a9_route") != 1 or g(panel, "a9_synth") != 1 or rd.big_text(panel)[0] != "audio12: sound o" \
                or marker != 0x38495553 or not played or max(abs(v) for v in played) < 100:
            problems.append("audio13 D5 %s: records %s, start %d mode %d route %d synth %d, line %s, panel marker %x,"
                            " KEY1 peak %d" % (name, labels, g(panel, "a13_start"), g(panel, "start_mode"),
                                               g(panel, "a9_route"), g(panel, "a9_synth"), rd.big_text(panel), marker,
                                               max([abs(v) for v in played] or [0])))
        if words(boot, "u2_boot") != A13_FWTEST_WORDS or words(boot, "u2_late") != A13_FWTEST_WORDS \
                or g(boot, "u2_late_blocks") or g(boot, "u2_late_beat") < 1000 or g(last, "u2_key_n") \
                or g(last, "u2_polls") or g(last, "u2c_toggles"):
            problems.append("audio13 U2-A %s: boot record start %s, later %s at beat %d with %d audio blocks;"
                            " in the panel key reads %d, polls %d, U2-C presses %d (none)" % (
                                name, words(boot, "u2_boot"), words(boot, "u2_late"), g(boot, "u2_late_beat"),
                                g(boot, "u2_late_blocks"), g(last, "u2_key_n"), g(last, "u2_polls"),
                                g(last, "u2c_toggles")))
        # By sb_now, fwtest's TIMER0 is 2.5 times slow; and in the 16-bit layout fwtest takes the unit's half (two
        # engine blocks, 128 frames) in the time of one of its own 64-frame halves, so the audio runs twice as fast.
        ok, text = a13_arp_check(last, name, HW_RATIO * (2 if extra else 1))
        arp[name] = text
        if not ok:
            problems.append("audio13 ARP " + text)
    # D5's self-undo, forced: the panel runs, silent, and says why.
    ub = os.path.join(work, "build-undo")
    build(ub, log, *A13_DEFINES, "--define", "SB_TEST_A9_CHECK_FAIL")
    usy = fws.elf_symbols(os.path.join(ub, "app.elf"))
    uout = os.path.join(work, "undo")
    ur = fwtest(os.path.join(ub, "app.bin"), uout, log, "--ms", "9000", "--flash-out", "--ram",
                "0x%08x:8@end" % usy["sb_ui"])
    with open(os.path.join(uout, "flash.bin"), "rb") as f:
        urs, _ = rd.records(f.read())
    ubf = urs[-1]["fields"] if urs else {}
    uline = "".join(rd.big_text(ubf))
    umarker = struct.unpack("<2I", ram(uout, usy["sb_ui"], 8))[0]
    if ur["run"]["outcome"] != "completed" or not urs or urs[-1]["label"] != "Inst panel" or g(ubf, "a9_route") != 3 \
            or g(ubf, "a13_start") != 1 or not uline.startswith("NO SOUND: ") or umarker != 0x38495553:
        problems.append("audio13 D5 undo: %s, last %s, route %d, line %r, panel marker %x" % (
            ur["run"]["outcome"], urs[-1]["label"] if urs else None, g(ubf, "a9_route"), uline, umarker))
    # HOME held at power-on: the test screen; U2-A's key; U2-B's states (CON0's bit 5 set in b to d by the test
    # seam); U2-C on and off; a save.
    hb = os.path.join(work, "build-home")
    build(hb, log, *A13_DEFINES, "--define", "SB_TEST_A13_U2_CHANGE")
    keys = [(9000, HW_OCTDOWN), (10000, HW_SAVE), (11000, HW_SAVE), (12000, HW_SAVE), (13000, HW_SAVE),
            (14000, HW_OCTUP), (17000, HW_OCTUP), (18000, HW_EDIT)]
    hpath = os.path.join(work, "home.script")
    with open(hpath, "w") as f:
        # Held past core 1's screen, where the start reads it (about 3.3 s at fwtest's slower slots).
        f.write("0 key %d down\n5000 key %d up\n" % (HW_HOME, HW_HOME))
        for t, k in keys:
            f.write("%d key %d down\n%d key %d up\n" % (t, k, t + 100, k))
    shots = (10700, 13700, 16500)   # after the audio page's 10 s
    hout = os.path.join(work, "home")
    hr = fwtest(os.path.join(hb, "app.bin"), hout, log, "--ms", "19000", "--flash-out", "--script",
                os.path.relpath(hpath, ROOT), *[x for t in shots for x in ("--lcd", str(t))])
    with open(os.path.join(hout, "flash.bin"), "rb") as f:
        hrs, hbad = rd.records(f.read())
    hl = a13_labels(hrs)
    rec = lambda lab: next((x["fields"] for x in hrs if x["label"] == lab), {})
    hboot, ue, uon, uoff, hlast = rec("boot"), rec("U2 e"), rec("U2-C on"), rec("U2-C off"), rec("save key")
    want = ["boot", "L2 before", "L2 kept", "R2 before", "R2 set", "Route before", "Route kept", "page", "U2-A key",
            "U2 b", "U2 c", "U2 d", "U2 e", "U2-C on", "U2-C off", "save key"]
    if hr["run"]["outcome"] != "completed" or hbad or hl != want or g(hlast, "a13_start") != 2 \
            or g(hlast, "start_mode") != 2:
        problems.append("audio13 HOME: %s, %d bad, records %s (want %s), start %d mode %d" % (
            hr["run"]["outcome"], len(hbad), hl, want, g(hlast, "a13_start"), g(hlast, "start_mode")))
    if words(hboot, "u2_boot") != A13_FWTEST_WORDS or words(hboot, "u2_late") != A13_FWTEST_WORDS \
            or g(hboot, "u2_late_blocks") or g(hboot, "u2_late_beat") < 1000 or g(hlast, "u2_key_n") != 1 \
            or words(hlast, "u2_key") != A13_FWTEST_WORDS:
        problems.append("audio13 U2-A HOME: boot %s, later %s at beat %d, %d audio blocks; key %d reads %s" % (
            words(hboot, "u2_boot"), words(hboot, "u2_late"), g(hboot, "u2_late_beat"), g(hboot, "u2_late_blocks"),
            g(hlast, "u2_key_n"), words(hlast, "u2_key")))
    n = g(hlast, "u2_mark_n")
    marks = [g(hlast, "u2_mark_%d" % (k % 16)) & 7 for k in range(max(0, n - 16), n)]
    n = g(hlast, "u2_chg_n")
    chg = [(g(hlast, "u2_chg_%d_at" % (k % 24)) & 7, g(hlast, "u2_chg_%d_value" % (k % 24))) for k in range(n)]
    if marks != [1, 2, 3, 4, 0] or chg != [(0, 0x20), (0, 0)] or not g(hlast, "u2_polls") \
            or not g(hlast, "u2_or_r0_b_CON0") & 0x20 or g(hlast, "u2_or_r0_a_CON0") & 0x20 \
            or g(hlast, "u2_and_r0_c_CON0") & 0x20 != 0x20:
        problems.append("audio13 U2-B: marks %s (b c d e a), changes %s (CON0 to 20, back to 0), %d polls, CON0 set in"
                        " a %08X b %08X" % (marks, chg, g(hlast, "u2_polls"), g(hlast, "u2_or_r0_a_CON0"),
                                            g(hlast, "u2_or_r0_b_CON0")))
    c_n = lambda f: [g(f, "u2c_n_%s_ch%d" % (st, c)) + 0 for st in rd.A13_STATES for c in (12, 13)]
    if any(c_n(ue)) or g(ue, "u2c_on") or not g(uoff, "u2c_n_a_ch12") + g(uoff, "u2c_timeouts") \
            or not g(uoff, "u2c_n_a_ch13") + g(uoff, "u2c_timeouts") or c_n(hlast) != c_n(uoff) \
            or g(uon, "u2c_on") != 1 or g(uoff, "u2c_on") or g(hlast, "u2c_toggles") != 2:
        problems.append("audio13 U2-C: readings before %s, at off %s (time-outs %d), after %s; on %d/%d, presses %d" % (
            c_n(ue), c_n(uoff), g(uoff, "u2c_timeouts"), c_n(hlast), g(uon, "u2c_on"), g(uoff, "u2c_on"),
            g(hlast, "u2c_toggles")))
    big = {}
    for t, w0, w2 in zip(shots, ("B CHANGED C0", "E SAME AS A", "A SAME AS A"), ("U2C OFF", "U2C OFF", "U2C ")):
        png = os.path.join(hout, "lcd-%dms.png" % t)
        got = read_big(fws, png, glyphs) if os.path.exists(png) else ["(no screen)"] * 3
        big[t] = got
        if got[0] != w0 or not re.match(r"(C0|C1|P0|P1|P2) [0-9A-F]{8}$", got[1]) or not got[2].startswith(w2) \
                or (w2 == "U2C " and not re.match(r"U2C (\d+|-) (\d+|-)$", got[2])):
            problems.append("audio13: the large area at %d ms %s (want %r, a word, %r)" % (t, got, w0, w2))
    # The unit's file: the candidate's build, packed from the package link, through fwtest's package path past the
    # start's bands; the raw link stops at them (audio12b's check, for this start).
    cb = os.path.join(work, "build-unit")
    build(cb, log, "--define", "SB_HW_FM1", "--define", "SB_HW_HOLD", "--define", "SB_HW_AUDIO1", "--define",
          "SB_HW_REPORT", "--define", "SB_HW_AUDIO8", "--define", "SB_HW_PCM16", "--define", "SB_HW_AUDIO9",
          "--define", "SB_HW_AUDIO10", "--define", "SB_HW_AUDIO11", "--define", "SB_HW_AUDIO12",
          "--define", "SB_HW_AUDIO13")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import fwsc
    pk = {}
    for link in ("app-pkg", "app"):
        path = os.path.join(work, "unit-%s.fwsc" % link)
        with open(path, "wb") as f:
            f.write(fwsc.pack(read_bytes(os.path.join(cb, link + ".bin")), "FM-1_0.13.0-hw3x"))
        pout = os.path.join(work, "unit-" + link)
        pr = fwtest(path, pout, log, "--package", "--ms", "40000", "--lcd", "39900")
        png = os.path.join(pout, "lcd-39900ms.png")
        bands = None
        if os.path.exists(png):
            _, _, rows = fws.read_png(png)
            bands = all(rows[72][x][:3] == (0, 0, 255) and rows[96][x][:3] == (0, 255, 0) for x in range(0, 240, 16))
        pk[link] = (pr["run"]["outcome"], bands)
    if pk["app-pkg"][0] != "completed" or pk["app-pkg"][1] is not False or pk["app"][1] is not True:
        problems.append("audio13 unit file: the package link %s, the raw link %s (outcome, still at the two bands)"
                        % (pk["app-pkg"], pk["app"]))
    print("audio13: D5 from cold to the panel (records %s), KEY1 sounds; the self-undo forced: %r; HOME: the test"
          " screen; U2-A in both boot records before the audio path, %s as fwtest reads them; U2-B marks %s, changes"
          " %s; U2-C readings at off %s; the large area %s; ARP %s; the unit's file: the package link past the bands"
          " %s, the raw link stopped %s" % (
              len(A13_INST), uline, ["%X" % v for v in A13_FWTEST_WORDS], marks, chg, c_n(uoff), big,
              "; ".join(arp.values()), pk["app-pkg"][1] is False, pk["app"][1]))
    return problems


def case_nowrace(a, work, log):
    """sb_now() never goes back: the slot interrupt's time-keeping forced
    at each point between its reads, just after TIMER0 wraps (main.c,
    SB_TEST_NOW_RACE); 200 runs, no reading earlier than the one before."""
    problems = []
    fws = fw_suite()
    b = os.path.join(work, "build")
    build(b, log, "--define", "SB_HW_FM1", "--define", "SB_TEST_HW_WINDOW", "--define", "SB_HW_HOLD",
          "--define", "SB_TEST_SHORT_HOLD", "--define", "SB_TEST_NOW_RACE")
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
    ("finder", case_finder),
    ("core1", case_core1),
    ("audio1", case_audio1),
    ("audio2", case_audio2),
    ("audio3", case_audio3),
    ("report1", case_report1),
    ("audio4", case_audio4),
    ("audio5", case_audio5),
    ("nowrace", case_nowrace),
    ("audio6", case_audio6),
    ("audio7", case_audio7),
    ("audio8", case_audio8),
    ("audio9", case_audio9),
    ("audio10", case_audio10),
    ("audio11", case_audio11),
    ("audio12", case_audio12),
    ("audio13", case_audio13),
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
