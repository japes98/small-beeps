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
  instruction, and so is the same with PLAITS_HWFLOAT defined (the
  check's one exception is the Plaits demo's hardware-float measurement
  builds, tools/build.sh); build A, which passed the same check, holds
  none.

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
- powercut (R-STORE-11): BR-12's saves that survive a power cut. Three
  saves, each from the base's full store (16 user slots, the selection,
  the settings) beside the firmware kinds' payloads, started by a key
  tap (tests/seams/engine's steps 0x80 and up): a 4 096-byte payload
  rewritten on the wide region test build (SB_TEST_STORE_WIDE, 5
  sectors), and on today's region a one-part payload rewritten (300
  bytes) and a user slot's patch, each with the head full, so that it
  takes a new sector and compacts. A run with --flash-log gives the
  save's flash commands; then for each command a power cut (fwtest's
  --power-cut) just after it starts, halfway and just before it ends,
  and one between commands and after the last; and from each cut's
  flash the firmware starts again (no tap, so it only reads): it finds
  the old payload or the new one, whole (length and sum), never another;
  the old until a moment, then the new; the other payloads unchanged;
  tools/store.py reads the same. Flash images are kept as their SHA-256.

Prints what each case saw, and exits 1 if any failed.
"""

import argparse
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
    print("ownbase: the test build %s; build A passed the check" % ("refused" if rc else "NOT refused"))
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


# --- engine ---------------------------------------------------------------

ENGINE_FIELDS = ("marker", "inits", "init_ticks", "init_blocks", "blocks", "frames", "serves",
                 "serve_seconds", "presses", "serve_presses", "core1", "core1_jobs", "core1_wrong",
                 "runtime", "sysex_begun", "sysex_ended", "sysex_cut", "sysex_cut_by", "sysex_served",
                 "sysex_len", "sysex_sum", "sysex_first", "sysex_last", "realtime", "notes",
                 "raw_started", "raw_done", "out_notes", "out_clocks", "out_refused",
                 "step", "boot_large", "boot_large_sum", "boot_small", "boot_small_sum", "put_result",
                 "put2_result", "put_len", "put_sum", "boot_patch", "boot_patch_sum", "stepped")
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
    # is written, and the old one stays (case powercut rewrites it, on
    # the wide region test build).
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


# --- powercut -------------------------------------------------------------

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
    builds = {"today": os.path.join(work, "build"), "wide": os.path.join(work, "build-wide")}
    opts = ["--platform", "--src", "tests/seams/engine", "--ld", "tests/seams/engine/engine.ld"]
    build(builds["today"], log, *opts)
    build(builds["wide"], log, *opts + ["--define", "SB_TEST_STORE_WIDE"])
    rec = fw_suite().elf_symbols(os.path.join(builds["today"], "app.elf"))["sb_test_engine"]
    n_rec = 4 * len(ENGINE_FIELDS)

    def full_store(sectors):
        s = st.Store(sectors=sectors)
        for i in range(st.SLOTS):
            s.put(st.PATCH, i, 2, pattern(20 + i, 112))
        s.put(st.SELECTION, 0, 1, bytes([5, 0, 0, 0]))
        s.put(st.SETTINGS, 0, 4, bytes(42))
        return s

    # The three saves, each from the base's full store beside the firmware
    # kinds' payloads: (name, build, sectors, step, the image before).
    wide = full_store(st.WIDE_SECTORS)
    wide.put_fw(LARGE[0], LARGE[1], 1, pattern(2, 4096))
    wide.put_fw(SMALL[0], SMALL[1], 1, pattern(9, 10))
    wide.put_fw(CONTROL_KIND, 0, 1, bytes([0x83]))
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
        saves.append((name, "today", st.SECTORS, step, s))
    saves.insert(0, ("large", "wide", st.WIDE_SECTORS, 0x83, wide))
    # What each payload is before the save and after it: (kind, id) to the
    # record's (length, sum) fields; the base's patch as STORE_PATCH.
    olds = {"large": pattern(2, 4096), "small": pattern(9, 10), "patch": pattern(20 + 3, 112)}
    news = {"large": pattern(3, 4096), "small": pattern(10, 300), "patch": pattern(12, 112)}
    fields = {"large": ("boot_large", "boot_large_sum"), "small": ("boot_small", "boot_small_sum"),
              "patch": ("boot_patch", "boot_patch_sum")}
    # And the others, which each save leaves as they were.
    p23, l1500 = pattern(20 + 3, 112), pattern(1, 1500)
    unchanged = {"large": {"small": olds["small"], "patch": p23}, "small": {"large": l1500, "patch": p23},
                 "patch": {"large": l1500, "small": olds["small"]}}

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
    for name, which, sectors, step, s in saves:
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
        lo, hi = st.region_base(sectors), st.REGION_END
        with open(os.path.join(out, "flash-ops.csv")) as f:
            rows = [l.split(",") for l in f.read().splitlines()[1:]]
        ops = [(float(r[0]), float(r[1])) for r in rows if lo <= int(r[3], 16) < hi]
        erases = sum(1 for r in rows if lo <= int(r[3], 16) < hi and r[2] != "02")
        if not erases:
            problems.append("%s: the save took no new sector" % name)
        points = powercut_points(ops)

        def one(i_t):
            i, t = i_t
            _, cut, _ = fw_run("%s-cut-%03d" % (name, i), image, pre, "--script", os.path.relpath(script, ROOT),
                               "--power-cut", "%.3f" % t)
            cut_in = os.path.join(work, "%s-cut-%03d-in.bin" % (name, i))
            with open(cut_in, "wb") as f:
                f.write(cut)
            b, _, _ = fw_run("%s-next-%03d" % (name, i), image, cut_in, "--ms", str(POWERCUT_BOOT_MS))
            os.remove(cut_in)
            img = st.Image(cut, sectors)
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
                if (b[fields[k][0]], b[fields[k][1]]) != (len(o), place_sum(o)):
                    problems.append("%s: cut at %.3f ms, %s changed" % (name, t, k))
            # tools/store.py's reader finds the same.
            if name == "patch":
                m = img.get(st.PATCH, 3)
            else:
                m = img.get_fw(*(LARGE if name == "large" else SMALL))
            if (m[1] if m else None) != (new if want[got] == "new" else old):
                problems.append("%s: cut at %.3f ms, tools/store.py reads otherwise" % (name, t))
        if seen != sorted(seen, key=lambda k: k == "new") or (seen and seen[-1] != "new"):
            problems.append("%s: not the old payload until a moment and then the new" % name)
        first_new = next((i for i, k in enumerate(seen) if k == "new"), len(seen))
        summary.append("%s: %d commands (%d erases), %d cuts, old %d, new %d"
                       % (name, len(ops), erases, len(points), first_new, len(seen) - first_new))
    print("powercut: %s; never neither, never a mix; tools/store.py agrees" % "; ".join(summary))
    return problems


CASES = [
    ("ownbase", case_ownbase),
    ("outside", case_outside),
    ("engine", case_engine),
    ("platform", case_platform),
    ("sysex", case_sysex),
    ("rawout", case_rawout),
    ("store", case_store),
    ("powercut", case_powercut),
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
