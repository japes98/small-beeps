#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The store's tests (M7; R-STORE-1 to R-STORE-9), run by tools/fw-suite.py
after its suite: runs that need the flash another run left (fwtest's
--flash and --flash-out), so they are run here, one by one or four at a
time, rather than from tests/fw/boot.suite. Every input file (scripts,
flash images) is made under out/fw/store/, inside the repository, as
tools/fwtest needs; the outputs go to the suite's output folder, one
folder a run, named store-<case>-<run>, each with its flash image only as
its SHA-256 (flash.bin.sha256): the checks read the image in memory.

Each flash image is read by tools/store.py, which follows store.c's rules
(docs/STORE-FORMAT.md). Where a case starts from an image tools/store.py
made, its Store model also predicts the image the firmware should leave,
command for command, and the two are compared byte for byte.

- persist (R-STORE-2): from an erased chip, ALGORITHM turned, the patch
  saved to slot 1 (SAVE held, KEY1), PRESETS turned, local control off
  (CC 122); the next run starts with the slot, the selection and the
  settings, and plays the slot's patch. Every run of every case: nothing
  written outside the store's region but fwtest's own image (R-STORE-1).
- sweep (R-STORE-3): a ring that has wrapped, its head one save from
  full, so a save takes a new sector, its erase and the compaction of the
  sector after it. The power cut test build stops after every one of the
  save's flash commands in turn, and part way through every page program;
  tools/store.py makes the program's bits half cleared and the erase half
  done. Every image: the store model's prediction exactly, slot 3 either
  the old patch or the new, every other key as before; then the shipping
  image starts from it, finds what tools/store.py finds, saves slot 5, and
  leaves what the model predicts.
- reset (R-STORE-9): SAVE and HOME held 2.4 s empty the store (a reset
  record) and the next start finds nothing; held 1 s, nothing happens.
  The screen says "factory defaults" (golden image).
- corrupt (R-STORE-5): a record's payload and another's CRC damaged, a
  garbage block, a record of a kind this firmware doesn't know: the older
  copy is read, the damaged one ignored, the counts as tools/store.py's;
  a save after it, "saved to slot 4" on the screen (golden image).
- full (R-STORE-4): every sector in use and the sector after the head
  holding a live record that the head has no room for: the save is
  refused, "SAVE FAILED, slot 2" on the screen (golden image), and nothing
  is written.
- wear (R-STORE-4, R-STORE-8): 36 saves on the wrapped ring, two or more
  new heads: the model's image exactly, the sectors erased in ring order; the
  selection, turned every 250 ms for 6 s, written at most once in 2 s.
- migrate (R-STORE-6): settings saved as version 1 (M6a's) are taken as
  version 2, with its defaults; a change then writes version 2.
- busy, wipe (R-STORE-7): saves under audioload's input (the heaviest the
  panel gives: test patch 6 on all 16 voices), SAVE held three times so
  the keys it strikes meanwhile save to their slots, on a test build whose chip takes the part's longest times, 12 ms
  an erase and 3 ms a page program (HW-77; busy), and on one that has erased its own image (wipe): no
  underrun, every tick on time, every save written.
"""

import concurrent.futures
import hashlib
import json
import os
import random
import struct
import subprocess

import fm_patch
import store as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "out", "fw", "store")
IMAGES = {"app": "out/fw/app.bin", "cut": "out/fw/test-storecut.bin",
          "busy": "out/fw/test-storebusy.bin", "wipe": "out/fw/test-storewipe.bin"}
RECORDS = {"store": (0x01C00780, 0xF0), "fm": (0x01C00590, 0x40), "midi": (0x01C005D0, 0x164),
           "audio": (0x01C00550, 0x40), "beacon": (0x01C00000, 0x60)}
STORE_FIELDS = ("marker part valid_sectors head head_seq append next_seq live init_ticks crc_bad skipped unknown"
                " voided records copies erases programs verify_fail refused last_result put_max commands"
                " saves save_fail resets auto_writes loaded trace_count").split()
FM_FIELDS = ("marker core1 core1_blocks patch algorithm mono voices0 voices1 voices_max stolen notes"
             " wait_max pitch_knob glide depth feedback").split()
MIDI_FIELDS = ("marker bytes ring_dropped parsed messages realtime sysex sysex_bytes sysex_long sysex_cut"
               " orphans undefined cut filtered notes_on notes_off").split()
STORE_MARKER = 0x374F5453
IMAGE_AT = 0x4000              # fwtest writes the image here (docs/HARNESS.md)
KEY_HOME, KEY_SAVE = 8, 9
ENC_ALGORITHM, ENC_PRESETS = 1, 6
WORKERS = 4
PATCHES = [fm_patch.encode(p) for p in fm_patch.TEST_PATCHES]
ERR_FULL = -2


def key(n):
    """fwtest's key number for KEYn (HW-37: control n is fwtest key n)."""
    return 13 + n


def rel(path):
    return os.path.relpath(path, ROOT)


class Run:
    """One fwtest run; its result, records and flash once done."""

    def __init__(self, out, name, image, ms, script=None, flash=None, at=(), halt_ok=False, extra=()):
        self.name, self.image, self.flash_in = name, image, flash
        self.dir = os.path.join(out, name)
        args = ["sh", "tools/fwtest", "run", IMAGES[image], "--ms", "%.3f" % ms, "--out", self.dir,
                "--flash-out", "--console"]
        os.makedirs(WORK, exist_ok=True)
        if script is not None:
            path = os.path.join(WORK, name + ".txt")
            with open(path, "w") as f:
                f.write("\n".join(script) + "\n")
            args += ["--script", rel(path)]
        if flash is not None:
            path = os.path.join(WORK, name + ".flash.bin")
            with open(path, "wb") as f:
                f.write(flash)
            args += ["--flash", rel(path)]
        for rec in ("store", "fm", "midi", "audio", "beacon"):
            a, n = RECORDS[rec]
            args += ["--ram", "0x%08x:0x%x@end" % (a, n)]
        for rec, when in at:
            a, n = RECORDS[rec]
            args += ["--ram", "0x%08x:0x%x@%s" % (a, n, when)]
        if halt_ok:
            args.append("--halt-ok")
        self.args = args + list(extra)

    def go(self):
        p = subprocess.run(self.args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.exit, self.log = p.returncode, p.stdout.decode("utf-8", "replace")
        try:
            with open(os.path.join(self.dir, "result.json")) as f:
                self.result = json.load(f)
            path = os.path.join(self.dir, "flash.bin")
            with open(path, "rb") as f:
                self.flash = f.read()
            # The 1 MiB image stays in memory for the checks; the run's
            # folder keeps only its SHA-256 (a test record would otherwise
            # carry some 250 MiB of them; tools/record.py does the same
            # for the audio).
            with open(path + ".sha256", "w") as f:
                f.write("%s  flash.bin\n" % hashlib.sha256(self.flash).hexdigest())
            os.remove(path)
        except (OSError, ValueError):
            self.result, self.flash = None, None
        return self

    def outcome(self):
        return (self.result or {}).get("run", {}).get("outcome")

    def rec(self, name, when="end"):
        a, n = RECORDS[name]
        fields = {"store": STORE_FIELDS, "fm": FM_FIELDS, "midi": MIDI_FIELDS}.get(name)
        with open(os.path.join(self.dir, "ram-%08x-%x-%s.bin" % (a, n, when if when == "end" else
                                                                   ("%dms" % when))), "rb") as f:
            b = f.read()
        if fields is None:
            return b
        v = struct.unpack_from("<%di" % len(fields) if name == "store" else "<%dI" % len(fields), b)
        d = dict(zip(fields, v))
        if name == "store":
            d["trace"] = list(struct.unpack_from("<32I", b, 4 * len(fields)))
        return d


def screen(when, name):
    """The screen at `when` against its golden image (the event line says
    what the store did; R-STORE-4, R-STORE-9)."""
    return ("--lcd", str(when), "--golden", "tests/fw/golden/" + name)


def run_all(runs):
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        return list(pool.map(lambda r: r.go(), runs))


# --- What the panel saves, and the images tools/store.py makes -----------

def with_sum(b):
    b = bytearray(b)
    s = fm_patch.fletcher16(b[:110])
    b[110], b[111] = s & 0xFF, s >> 8
    return bytes(b)


def saved(program_patch, algorithm_turns=0):
    """The patch SAVE writes: the one playing, with ALGORITHM turned."""
    b = bytearray(program_patch)
    b[16] = (b[16] - 1 + algorithm_turns) % fm_patch.ALGORITHMS + 1
    return with_sum(b)


def user_patch(n):
    b = bytearray(PATCHES[n % len(PATCHES)])
    b[4:16] = b"\0" * 12
    name = b"USER %02d" % (n + 1)
    b[4:4 + len(name)] = name
    return with_sum(b)


def settings_v2(channel=0, bend=2, out=1, thru=0, local=1):
    return bytes([2, channel, bend, 0] + [0] * 32 + [out, thru, local, 0])


def settings_v1(channel, bend):
    return bytes([1, channel, bend, 0] + [0] * 32)


def save_script(t, slot):
    """SAVE held, KEY<slot> tapped, SAVE let go."""
    return ["%d key %d down" % (t, KEY_SAVE), "%d key %d tap" % (t + 50, key(slot)),
            "%d key %d up" % (t + 150, KEY_SAVE)]


def ring_before_advance():
    """A ring that has wrapped, with the user slots in the sector two past
    the head and the head too full for a patch: the next save takes a new
    head, erases it and compacts the slots into it."""
    s = st.Store()
    for slot in range(st.SLOTS):
        s.put(st.PATCH, slot, 1, user_patch(slot))
    s.put(st.SETTINGS, 0, 2, settings_v2())
    n = 0
    while True:
        s.put(st.SELECTION, 0, 1, bytes([n % 9, 0, 0, 0]))
        n += 1
        if s.head_seq >= st.SECTORS + 2 and s.append + st.record_size(112) > st.SECTOR:
            m = (s.head + 2) % st.SECTORS
            if sum(1 for e in s.key if e and s._sector_of(e[1]) == m) >= 10:
                return s.chip()
        assert n < 50000


def selection_of(chip):
    e = st.Image(chip).get(st.SELECTION)
    return e[1][0] if e else 0


def predict(chip, puts):
    """The Store model's image after these puts, and its commands."""
    s = st.Store(chip)
    for kind, ident, version, payload in puts:
        s.put(kind, ident, version, payload)
    return s.chip(), s.commands


def region(chip):
    return chip[st.BASE:st.BASE + st.SIZE]


def outside_writes(run):
    """Problems if the run changed the chip outside the store's region and
    fwtest's own image (R-STORE-1)."""
    before = run.flash_in if run.flash_in is not None else b"\xff" * st.CHIP
    before = before + b"\xff" * (st.CHIP - len(before))
    after = run.flash
    skip = (IMAGE_AT, IMAGE_AT + os.path.getsize(os.path.join(ROOT, IMAGES[run.image])))
    for lo, hi in ((0, skip[0]), (skip[1], st.BASE), (st.BASE + st.SIZE, st.CHIP)):
        if before[lo:hi] != after[lo:hi]:
            i = next(j for j in range(lo, hi) if before[j] != after[j])
            return ["%s: the chip changed outside the store at 0x%05x" % (run.name, i)]
    return []


def common(run, image_len, outcome="completed"):
    """Every run: its outcome, a store record, no unmodelled accesses,
    nothing written outside the store."""
    if run.result is None:
        return ["%s: fwtest gave no result: %s" % (run.name, run.log.strip()[-300:])]
    p = []
    if run.outcome() != outcome:
        p.append("%s: %s, expected %s (%s)" % (run.name, run.outcome(), outcome,
                                               run.result["run"].get("detail")))
    for g in run.result.get("golden") or []:
        if g.get("result") != "match":
            p.append("%s: golden %s: %s" % (run.name, g.get("name"), g.get("detail")))
    if run.result["run"].get("unmodelled_accesses"):
        p.append("%s: unmodelled accesses %s" % (run.name, run.result["run"]["unmodelled_accesses"][:4]))
    if run.rec("store")["marker"] != STORE_MARKER:
        p.append("%s: no store record" % run.name)
    return p + outside_writes(run)


def agrees(run, chip):
    """Problems if the firmware's start-up didn't find what tools/store.py
    finds in chip."""
    img, r = st.Image(chip), run.rec("store")
    p = []
    want = {"valid_sectors": sum(img.valid), "crc_bad": img.counts["crc_bad"], "skipped": img.counts["skipped"],
            "unknown": img.counts["unknown"], "voided": img.counts["voided"]}
    if not r["erases"]:      # the head start-up found, unless a save moved it since
        want["head"] = 0xFFFFFFFF if img.head is None else img.head
    for k, v in want.items():
        if r[k] & 0xFFFFFFFF != v:
            p.append("%s: start-up found %s %d, tools/store.py %d" % (run.name, k, r[k] & 0xFFFFFFFF, v))
    loaded = sum(1 << (8 + k) for k in range(st.SLOTS) if img.keys[k])
    sel = img.get(st.SELECTION)
    if sel and sel[0] == 1 and len(sel[1]) == 4:
        n = sel[1][0]
        if n < 9 or (n < 9 + st.SLOTS and img.keys[n - 9]):
            loaded |= 1
    if r["loaded"] & ~6 != loaded:
        p.append("%s: loaded 0x%x, tools/store.py has 0x%x" % (run.name, r["loaded"] & ~6, loaded))
    return p


# --- The cases --------------------------------------------------------------

def case_persist(out, image_len):
    p, lines = [], []
    a0 = PATCHES[0][16]
    a = Run(out, "store-persist-a", "app", 3800,
            script=["200 enc %d +2" % ENC_ALGORITHM] + save_script(300, 1)
            + ["600 enc %d +3" % ENC_PRESETS, "700 midi b0 7a 00"]).go()
    p += common(a, image_len)
    if p:
        return p, lines
    r, img = a.rec("store"), st.Image(a.flash)
    want_patch = saved(PATCHES[0], 2)
    if r["saves"] != 1 or r["save_fail"] or r["auto_writes"] != 2:
        p.append("persist-a: saves %d (failed %d), automatic writes %d; expected 1, 0, 2"
                 % (r["saves"], r["save_fail"], r["auto_writes"]))
    if img.get(st.PATCH, 0) != (1, want_patch):
        p.append("persist-a: slot 1 is not the patch saved")
    if img.get(st.SELECTION) != (1, bytes([3, 0, 0, 0])):
        p.append("persist-a: the selection is %s, not program 3" % (img.get(st.SELECTION),))
    sv = img.get(st.SETTINGS)
    if not sv or sv[0] != 2 or sv[1][38] != 0 or sv[1][36] != 1 or sv[1][37] != 0:
        p.append("persist-a: the settings saved are %s, not local off" % (sv,))
    if sorted(img.live()) != ["selection", "settings", "slot 1"]:
        p.append("persist-a: the store holds %s" % sorted(img.live()))
    b = Run(out, "store-persist-b", "app", 1600, flash=a.flash,
            script=["1000 midi b0 7a 7f", "1100 enc %d +6" % ENC_PRESETS], at=(("fm", 500),)).go()
    p += common(b, image_len)
    if b.result is None:
        return p, lines
    p += agrees(b, a.flash)
    rb, f0, f1 = b.rec("store"), b.rec("fm", 500), b.rec("fm")
    if rb["loaded"] != 0x103:
        p.append("persist-b: loaded 0x%x, expected 0x103 (selection, settings, slot 1)" % rb["loaded"])
    if f0["patch"] != 3:
        p.append("persist-b: program %d at the start, not 3" % f0["patch"])
    if f1["patch"] != 9 or f1["algorithm"] != want_patch[16]:
        p.append("persist-b: PRESETS reached program %d, algorithm %d; expected 9, %d"
                 % (f1["patch"], f1["algorithm"], want_patch[16]))
    lines.append("  persist: slot 1 saved with algorithm %d (was %d), program 3, local off; the next start"
                 " loaded all three (store read in %.1f us) and played slot 1 as program 9"
                 % (want_patch[16], a0, rb["init_ticks"] / 24.0, ))
    return p, lines


def cut_script():
    return ["100 enc %d +2" % ENC_ALGORITHM] + save_script(150, 3)


def boot_script():
    return save_script(150, 5)


def check_cut_image(name, chip, s0, new3):
    """The image a cut left: slot 3 old or new, every other key as in s0."""
    img, i0 = st.Image(chip), st.Image(s0)
    p = []
    for k in range(st.KEYS):
        e, e0 = img.keys[k], i0.keys[k]
        got = (e[4], e[5]) if e else None
        was = (e0[4], e0[5]) if e0 else None
        if k == 2:
            if got not in (was, (1, new3)):
                p.append("%s: slot 3 is neither the old patch nor the new" % name)
        elif got != was:
            p.append("%s: %s changed" % (name, st.key_name(k)))
    return p


def boot_check(run, chip, image_len):
    """The shipping image started from a cut's image: it found what
    tools/store.py finds, and its save of slot 5 left the model's image."""
    p = common(run, image_len) + agrees(run, chip)
    if p:
        return p
    sel = selection_of(chip)
    base = PATCHES[sel] if sel < 9 else st.Image(chip).get(st.PATCH, sel - 9)[1]
    want, _ = predict(chip, [(st.PATCH, 4, 1, saved(base))])
    r = run.rec("store")
    if r["save_fail"] or r["saves"] != 1:
        p.append("%s: the save after the cut failed (%d of %d)" % (run.name, r["save_fail"], r["saves"]))
    if region(run.flash) != region(want):
        p.append("%s: the image after the next save is not the model's" % run.name)
    return p


def torn_bits(before, after, rng):
    """A page program cut short at the bit level: about half of the bits it
    clears, cleared."""
    d = bytearray(before)
    for i in range(st.BASE, st.BASE + st.SIZE):
        cleared = before[i] & ~after[i] & 0xFF
        if cleared:
            d[i] &= ~(cleared & rng.randrange(256)) & 0xFF
    return bytes(d)


def torn_erase(before, addr, rng, how):
    d = bytearray(before)
    if how == "half":
        d[addr:addr + st.SECTOR // 2] = b"\xff" * (st.SECTOR // 2)
    else:
        for i in range(addr, addr + st.SECTOR):
            d[i] |= rng.randrange(256)
    return bytes(d)


def case_sweep(out, image_len):
    p, lines = [], []
    s0 = ring_before_advance()
    sel = selection_of(s0)
    new3 = saved(PATCHES[sel], 2)
    s1, commands = predict(s0, [(st.PATCH, 2, 1, new3)])
    erases = sum(1 for c in commands if c[0] == "erase")
    copies = len(commands) - erases
    # The uncut run first: the model's image and its command count.
    ref = Run(out, "store-sweep-full", "cut", 900, flash=st.with_cut(s0, 0xFFFFFFFF), script=cut_script()).go()
    p += common(ref, image_len)
    if p:
        return p, lines
    r = ref.rec("store")
    if region(ref.flash) != region(s1):
        p.append("sweep: the uncut save's image is not the model's")
    if r["commands"] != len(commands):
        p.append("sweep: the save took %d commands, the model %d" % (r["commands"], len(commands)))
    if not r["copies"] or not r["erases"]:
        p.append("sweep: the save copied %d records and erased %d sectors: no compaction" % (r["copies"], r["erases"]))
    # Cut after every command, and part way through every page program.
    cuts = []
    for n in range(len(commands)):
        cuts.append((n, 0))
        if commands[n][0] == "program":
            k = len(commands[n][2])
            cuts += [(n, b) for b in sorted({1, k // 2, k - 1}) if 0 < b < k]
    runs = [Run(out, "store-sweep-cut-%02d-%03d" % (n, b), "cut", 900,
                flash=st.with_cut(s0, n, b), script=cut_script(), halt_ok=True) for n, b in cuts]
    run_all(runs)
    images, seen = {}, set()
    for (n, b), run in zip(cuts, runs):
        more = common(run, image_len, outcome="halt")
        want = st.apply(s0, commands[:n])
        if b:
            kind, addr, data = commands[n]
            want = st.apply(want, [(kind, addr, data[:b])])
        if not more and region(run.flash) != region(want):
            more.append("%s: the image is not the model's after %d commands and %d bytes" % (run.name, n, b))
        if not more:
            more += check_cut_image(run.name, run.flash, s0, new3)
            images[(n, b)] = run.flash
            seen.add(region(run.flash))
        p += more
    if len({region(st.apply(s0, commands[:n])) for n in range(len(commands) + 1)}) != len(commands) + 1:
        p.append("sweep: two cut points left the same image (a command changed nothing)")
    # Torn states the firmware can't make: bits half cleared, erases half done.
    rng = random.Random(7)
    for n, c in enumerate(commands):
        before = st.apply(s0, commands[:n])
        if c[0] == "program":
            images[(n, "bits")] = torn_bits(before, st.apply(before, [c]), rng)
        else:
            images[(n, "half")] = torn_erase(before, c[1], rng, "half")
            images[(n, "noise")] = torn_erase(before, c[1], rng, "noise")
    for at, chip in images.items():
        if isinstance(at[1], str):
            p += check_cut_image("sweep %d %s" % at, chip, s0, new3)
    # The shipping image starts from every one of them, and saves again.
    order = sorted(images, key=str)
    boots = [Run(out, "store-sweep-boot-%02d-%s" % (n, b), "app", 900, flash=images[(n, b)],
                 script=boot_script()) for n, b in order]
    run_all(boots)
    for (n, b), run in zip(order, boots):
        p += boot_check(run, images[(n, b)], image_len)
    lines.append("  sweep: the save took %d commands (%d erase, %d page programs; %d records copied);"
                 " cut at %d points (%d mid-program), %d torn images made, %d distinct images; every start"
                 " after them agreed with tools/store.py and saved again"
                 % (len(commands), erases, copies, r["copies"], len(cuts), sum(1 for c in cuts if c[1]),
                    sum(1 for k in images if isinstance(k[1], str)), len(seen)))
    return p, lines


def case_reset(out, image_len):
    p, lines = [], []
    s = st.Store()
    s.put(st.PATCH, 0, 1, user_patch(0))
    s.put(st.SELECTION, 0, 1, bytes([9, 0, 0, 0]))
    s.put(st.SETTINGS, 0, 2, settings_v2(channel=5))
    chip = s.chip()
    held = Run(out, "store-reset-held", "app", 3000, flash=chip,
               script=["300 key %d down" % KEY_SAVE, "350 key %d down" % KEY_HOME,
                       "2750 key %d up" % KEY_HOME, "2800 key %d up" % KEY_SAVE], at=(("fm", 250),),
               extra=screen(2600, "store-reset")).go()
    short = Run(out, "store-reset-short", "app", 2000, flash=chip,
                script=["300 key %d down" % KEY_SAVE, "350 key %d down" % KEY_HOME,
                        "1350 key %d up" % KEY_HOME, "1400 key %d up" % KEY_SAVE]).go()
    for run in (held, short):
        p += common(run, image_len) + agrees(run, chip)
    if p:
        return p, lines
    rh, rs = held.rec("store"), short.rec("store")
    if held.rec("fm", 250)["patch"] != 9:
        p.append("reset: started on program %d, not slot 1's 9" % held.rec("fm", 250)["patch"])
    if rh["resets"] != 1 or held.rec("fm")["patch"] != 0 or sorted(st.Image(held.flash).live()) != ["reset"]:
        p.append("reset: held 2.4 s: %d resets, program %d, the store holds %s"
                 % (rh["resets"], held.rec("fm")["patch"], sorted(st.Image(held.flash).live())))
    if rs["resets"] or region(short.flash) != region(chip):
        p.append("reset: held 1 s: %d resets, the store changed: %s" % (rs["resets"], region(short.flash) != region(chip)))
    again = Run(out, "store-reset-again", "app", 300, flash=held.flash).go()
    p += common(again, image_len) + agrees(again, held.flash)
    if again.result and again.rec("store")["loaded"]:
        p.append("reset: the next start loaded 0x%x" % again.rec("store")["loaded"])
    lines.append("  reset: held 2.4 s, slot 1, the selection and the settings were voided by one record and"
                 " the next start loaded nothing; held 1 s, nothing changed")
    return p, lines


def case_corrupt(out, image_len):
    p, lines = [], []
    s = st.Store()
    s.put(st.PATCH, 0, 1, user_patch(0))
    s.put(st.PATCH, 0, 1, user_patch(1))      # the newest slot 1: damaged below
    s.put(st.PATCH, 1, 1, user_patch(2))      # slot 2's only copy: CRC damaged below
    s.put(st.SELECTION, 0, 1, bytes([1, 0, 0, 0]))
    chip = bytearray(s.chip())
    img = st.Image(chip)
    a1, a2 = img.keys[0][1], img.keys[1][1]
    chip[a1 + st.HEADER + 40] ^= 0x10
    chip[a2 + st.HEADER + 112] ^= 0x01
    tail = st.BASE + img.head * st.SECTOR + img.append
    chip[tail:tail + 16] = b"\x00\x11\x22\x33" * 4
    chip = bytes(chip)
    s2 = st.Store(chip)
    s2.raw_record(img.head, img.append + 16, 9, 0, 1, b"from later", s2.next_seq)
    chip = s2.chip()
    want = st.Image(chip)
    run = Run(out, "store-corrupt", "app", 900, flash=chip, script=save_script(150, 4),
              extra=screen(880, "store-corrupt")).go()
    p += common(run, image_len) + agrees(run, chip)
    if p:
        return p, lines
    if want.get(st.PATCH, 0) != (1, user_patch(0)) or want.get(st.PATCH, 1) is not None:
        p.append("corrupt: tools/store.py doesn't read the older slot 1 and no slot 2")
    if want.counts["crc_bad"] != 2 or want.counts["unknown"] != 1 or not want.counts["skipped"]:
        p.append("corrupt: tools/store.py counts %s" % want.counts)
    after = st.Image(run.flash)
    if after.get(st.PATCH, 3) != (1, saved(PATCHES[1])) or after.get(st.PATCH, 0) != (1, user_patch(0)):
        p.append("corrupt: the save after it failed, or slot 1 was lost")
    lines.append("  corrupt: %d damaged records and %d garbage blocks ignored, %d unknown record kept out,"
                 " the older slot 1 read; a save after it went in" % (want.counts["crc_bad"],
                                                                    want.counts["skipped"], want.counts["unknown"]))
    return p, lines


def case_full(out, image_len):
    p, lines = [], []
    s = st.Store()
    for sec in range(st.SECTORS):
        s.raw_sector(sec, sec + 1)
    s.raw_record(0, 16, st.PATCH, 0, 1, user_patch(0), 1)        # live, in the sector after the head
    seq = 2
    for sec in range(1, st.SECTORS):
        off = 16
        while off + 32 <= st.SECTOR:
            s.raw_record(sec, off, st.SELECTION, 0, 1, bytes([seq % 9, 0, 0, 0]), seq)
            off += 32
            seq += 1
    chip = s.chip()
    run = Run(out, "store-full", "app", 900, flash=chip, script=save_script(150, 2),
              extra=screen(880, "store-full")).go()
    p += common(run, image_len) + agrees(run, chip)
    if p:
        return p, lines
    r = run.rec("store")
    if r["save_fail"] != 1 or r["last_result"] != ERR_FULL or region(run.flash) != region(chip):
        p.append("full: save failures %d, result %d, the store changed: %s"
                 % (r["save_fail"], r["last_result"], region(run.flash) != region(chip)))
    if st.Image(run.flash).get(st.PATCH, 0) != (1, user_patch(0)):
        p.append("full: slot 1 was lost")
    lines.append("  full: every sector in use and no room to move slot 1 out of the next one: the save was"
                 " refused (result %d), reported, and nothing written" % r["last_result"])
    return p, lines


SAVES = 36


def case_wear(out, image_len):
    p, lines = [], []
    s0 = ring_before_advance()
    sel = selection_of(s0)
    script, puts = [], []
    for i in range(SAVES):
        script += save_script(150 + 150 * i, i % 16 + 1)
        puts.append((st.PATCH, i % 16, 1, saved(PATCHES[sel])))
    want, commands = predict(s0, puts)
    run = Run(out, "store-wear", "app", 150 + 150 * SAVES + 200, flash=s0, script=script).go()
    rate = Run(out, "store-wear-rate", "app", 9500,
               script=["%d enc %d +1" % (300 + 250 * i, ENC_PRESETS) for i in range(24)]).go()
    for x in (run, rate):
        p += common(x, image_len)
    if p:
        return p, lines
    r = run.rec("store")
    if region(run.flash) != region(want):
        p.append("wear: the image after %d saves is not the model's" % SAVES)
    erased = [(c[1] - st.BASE) // st.SECTOR for c in commands if c[0] == "erase"]
    if any((b - a) % st.SECTORS != 1 for a, b in zip(erased, erased[1:])) or len(erased) < 2:
        p.append("wear: sectors erased %s, not two or more in ring order" % erased)
    if r["erases"] != len(erased) or r["saves"] != SAVES or r["save_fail"]:
        p.append("wear: %d erases (model %d), %d saves, %d failed" % (r["erases"], len(erased), r["saves"], r["save_fail"]))
    rr = rate.rec("store")
    # 6 s of turns: at most one write a STORE_SETTLE_S (2 s), and the last.
    if not 2 <= rr["auto_writes"] <= 6 // 2 + 1 or st.Image(rate.flash).get(st.SELECTION) != (1, bytes([24 % 9, 0, 0, 0])):
        p.append("wear: the selection was written %d times over 6 s of turns, and holds %s"
                 % (rr["auto_writes"], st.Image(rate.flash).get(st.SELECTION)))
    lines.append("  wear: %d saves erased sectors %s in ring order, %d records copied; the selection, turned"
                 " 24 times in 6 s, was written %d times" % (SAVES, erased, r["copies"], rr["auto_writes"]))
    return p, lines


def case_migrate(out, image_len):
    p, lines = [], []
    s = st.Store()
    s.put(st.SETTINGS, 0, 1, settings_v1(10, 12))
    chip = s.chip()
    run = Run(out, "store-migrate", "app", 3800, flash=chip,
              script=["300 midi 90 3c 64", "400 midi 80 3c 00", "500 midi 99 40 64", "600 midi 89 40 00",
                      "800 midi b9 7a 00"]).go()
    p += common(run, image_len) + agrees(run, chip)
    if p:
        return p, lines
    r, m = run.rec("store"), run.rec("midi")
    if r["loaded"] & 6 != 6:
        p.append("migrate: loaded 0x%x, not the settings migrated" % r["loaded"])
    if m["filtered"] < 2 or m["notes_on"] != 1:
        p.append("migrate: %d messages filtered, %d notes taken: not channel 10" % (m["filtered"], m["notes_on"]))
    sv = st.Image(run.flash).get(st.SETTINGS)
    if sv != (2, settings_v2(channel=10, bend=12, local=0)):
        p.append("migrate: the settings written after the change are %s" % (sv,))
    lines.append("  migrate: version 1 settings (channel 10, bend 12) taken as version 2; a change wrote"
                 " version 2 with them kept and its defaults added")
    return p, lines


def ring_for_load():
    """A ring that has wrapped, holding only the selection (program 0, as
    audioload expects to start from), its head too full for a patch: the
    first save under load takes a new head and erases it."""
    s = st.Store()
    while not (s.head_seq >= st.SECTORS + 2 and s.append + st.record_size(112) > st.SECTOR):
        s.put(st.SELECTION, 0, 1, bytes([0, 0, 0, 0]))
    return s.chip()


def load_script(ms, saves):
    """audioload's script (the heaviest input, tests/fw/scripts/audioload.txt)
    up to ms, with SAVE held for 150 ms at each time in saves: the keys it
    strikes again meanwhile save to their slots (KEY1 to KEY16)."""
    ev = []
    with open(os.path.join(ROOT, "tests", "fw", "scripts", "audioload.txt")) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line and float(line.split()[0]) < ms - 100:
                ev.append((float(line.split()[0]), line.split(None, 1)[1]))
    for at in saves:
        ev += [(at, "key %d down" % KEY_SAVE), (at + 150, "key %d up" % KEY_SAVE)]
    ev.sort(key=lambda e: e[0])
    return ["%.3f %s" % e for e in ev]


def case_load(fw, out, image_len, image):
    p, lines = [], []
    saves = (1000, 2000, 3000)
    run = Run(out, "store-" + image, image, 5000, flash=ring_for_load(), script=load_script(5000, saves),
              extra=("--ipb",)).go()
    p += common(run, image_len)
    if run.result is None:
        return p, lines
    more, ln, a, _, _ = fw.check_audio_common("store-" + image, run.dir)
    p += more
    lines += ln
    more, ln = fw.check_ticks_under_load("store-" + image, run.dir)
    p += more
    lines += ln
    r, f = run.rec("store"), run.rec("fm")
    if r["saves"] < len(saves) or r["save_fail"] or not r["erases"]:
        p.append("%s: %d saves, %d failed, %d erases" % (image, r["saves"], r["save_fail"], r["erases"]))
    if f["patch"] != 6 or f["voices_max"] != 16:
        p.append("%s: program %d, %d voices at most: not audioload's load" % (image, f["patch"], f["voices_max"]))
    with open(os.path.join(run.dir, "ipb.csv")) as fi:
        rows = [x.split(",") for x in list(fi)[1:] if x.strip()]
    core0 = [int(x[2]) for x in rows if 1000 <= float(x[1]) <= 4900]
    if image == "wipe":
        image_end = IMAGE_AT + os.path.getsize(os.path.join(ROOT, IMAGES[image]))
        if any(x != 0xFF for x in run.flash[IMAGE_AT:image_end]):
            p.append("wipe: the image's own flash was not erased")
    lines.append("  %s: audioload's input with SAVE held 3 times: %d saves (%d erases, %d page programs), the"
                 " longest %.1f ms; %d underruns; core 0 %d instructions a block on average, %d at most"
                 % (image, r["saves"], r["erases"], r["programs"], r["put_max"] / 24000.0, a["underruns"],
                    sum(core0) // len(core0), max(core0)))
    return p, lines


def run(fw, out, image_len):
    """Every case; (problems, lines)."""
    problems, lines = [], []
    cases = [("persist", case_persist), ("sweep", case_sweep), ("reset", case_reset),
             ("corrupt", case_corrupt), ("full", case_full), ("wear", case_wear),
             ("migrate", case_migrate),
             ("busy", lambda o, n: case_load(fw, o, n, "busy")),
             ("wipe", lambda o, n: case_load(fw, o, n, "wipe"))]
    for name, case in cases:
        try:
            p, l = case(out, image_len)
        except (OSError, ValueError, KeyError, AssertionError, TypeError) as e:
            p, l = ["store %s: %s: %s" % (name, type(e).__name__, e)], []
        print("store %s: %s" % (name, "FAIL" if p else "PASS"))
        problems += p
        lines += l
        if l:
            print("\n".join(l))
    return problems, lines
