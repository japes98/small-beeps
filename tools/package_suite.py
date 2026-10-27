#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Phase A1's package check (C-PACKAGE; R-PKG-1, R-PKG-2; docs/A1-PLAN.md,
"How it is tested", 1): our firmware boots from its `.fwsc` in fwtest's
package path as it does from its raw image, and fwtest refuses each
broken package at the check tools/fwsc.py names.

  package_suite.py --build DIR --out DIR

Packs DIR/app-pkg.bin (tools/build.sh's package link) with tools/fwsc.py
into OUT/small-beeps-0.0.0.fwsc and reads it back (identity, app area
0x4000, entry 0x02000120, the app byte for byte). Then, through
tools/fwtest (the pinned image), runs the firmware suite's main cases
(CASES: the start, the heartbeat, the screen, the panel, the FM engine
with its golden audio, MIDI in, the interface and the store), each once
from DIR/app.bin and once from the package with --package, their goldens
left to C-FW-SUITE, and checks the two runs agree: the same outcome,
emulated time, instructions on both cores and unmodelled accesses, every
output byte for byte the same, except

- the r0 block (RAM from 0x01c7fc00): the package's is the boot block
  docs/HARNESS.md gives ("Packages": the flash header's copy's address,
  the window's flash offset and address, 12 zero bytes, the flash header
  unmasked), the raw image's the raw path's, and past both the same;
- the flash chip (--flash-out): the package's holds the flash image from
  offset 0, the raw run's the raw image at 0x4000; from the stock user
  patch region on (0xEA000, the store's region included) the same;

and that result.json's run.package names the identity, app area 0x04000
and entry 0x02000120. Last, every broken package (tools/fwsc.py broken):
fwtest refuses it with a usage error (exit 2) whose message is "the
package is refused: " and then the words tools/fwsc.py's reader gives for
that check.
"""

import argparse
import json
import os
import shlex
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fwsc  # noqa: E402  (tools/, our own)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join(ROOT, "tests", "fw", "boot.suite")
CASES = ["boot", "heartbeat", "screen", "keys", "fmgold", "midimsg", "views", "edit"]
PATH_OPTS = ("--script", "--flash")
VERSION = "0.0.0"
R0_BLOCK = 0x01C7FC00
FLASH_REST = fwsc.USER_REGION


def suite_cases():
    """{name: args} of the suite's cases on app.bin, paths from the root,
    goldens dropped."""
    out = {}
    with open(SUITE) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            name, _outcome, image, *args = shlex.split(line)
            if os.path.basename(image) != "app.bin":
                continue
            a, i = [], 0
            while i < len(args):
                if args[i] == "--golden":
                    i += 2
                    continue
                if args[i] in PATH_OPTS:
                    a += [args[i], os.path.relpath(os.path.normpath(os.path.join(ROOT, "tests", "fw", args[i + 1])), ROOT)]
                    i += 2
                    continue
                a.append(args[i])
                i += 1
            out[name] = a
    return out


def fwtest(image, args, out, package=False):
    cmd = ["sh", os.path.join(ROOT, "tools", "fwtest"), "run", os.path.relpath(image, ROOT)] \
        + (["--package"] if package else []) + args + ["--out", os.path.relpath(out, ROOT)]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def boot_block(flash):
    """The r0 block of the package path (docs/HARNESS.md, "Packages")."""
    return struct.pack("<III", R0_BLOCK + 0x18, fwsc.AREA, fwsc.WINDOW) + bytes(12) \
        + fwsc.mask(flash[:32], fwsc.HEADER_KEY)


def compare(name, raw, pkg, flash, image):
    """Problems between a case's raw and package runs."""
    p = []
    rr = json.load(open(os.path.join(raw, "result.json")))["run"]
    pr = json.load(open(os.path.join(pkg, "result.json")))["run"]
    want = {"identity": "small-beeps-" + VERSION, "app_area": "0x04000", "entry": "0x02000120"}
    if pr.get("package") != want:
        p.append("%s: run.package is %r, not %r" % (name, pr.get("package"), want))
    for k in ("outcome", "detail", "emulated_ms", "instructions", "midi_bytes_dropped",
              "midi_out_bytes_dropped", "unmodelled_accesses"):
        if rr.get(k) != pr.get(k):
            p.append("%s: %s %r from the raw image, %r from the package" % (name, k, rr.get(k), pr.get(k)))
    names = sorted(o["name"] for o in rr["outputs"])
    if names != sorted(o["name"] for o in pr["outputs"]):
        p.append("%s: the two runs' outputs differ in name" % name)
        return p
    for n in names:
        a, b = (open(os.path.join(d, n), "rb").read() for d in (raw, pkg))
        if n.startswith("ram-%08x-" % R0_BLOCK):
            bb = boot_block(flash)
            if b[:len(bb)] != bb or a[len(bb):] != b[len(bb):]:
                p.append("%s: %s: the package's r0 block is not HARNESS.md's boot block" % (name, n))
        elif n.startswith("flash"):
            if b[:len(flash)] != flash or a[fwsc.AREA:fwsc.AREA + len(image)] != image:
                p.append("%s: %s: the package's or the raw image's own bytes are not on the chip" % (name, n))
            if a[FLASH_REST:] != b[FLASH_REST:]:
                p.append("%s: %s: the chip differs from 0x%X on" % (name, n, FLASH_REST))
        elif a != b:
            p.append("%s: %s differs between the raw image and the package" % (name, n))
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    problems = []
    raw = os.path.join(out, "app.bin")
    shutil.copyfile(os.path.join(a.build, "app.bin"), raw)
    with open(os.path.join(a.build, "app-pkg.bin"), "rb") as f:
        app = f.read()
    pkg = os.path.join(out, "small-beeps-%s.fwsc" % VERSION)
    blob = fwsc.pack(app, "small-beeps-" + VERSION)
    with open(pkg, "wb") as f:
        f.write(blob)
    r = fwsc.check(blob)
    print("package: %s, %d bytes; identity %s, app area 0x%05X, entry 0x%08X, chip key 0x%04X"
          % (os.path.basename(pkg), len(blob), r["identity"], r["area"], r["entry"], r["key"]))
    if r["app"] != app or r["entry"] != fwsc.ENTRY or r["area"] != fwsc.AREA:
        problems.append("the reader doesn't read back the package as packed")
    cases = suite_cases()
    for name in CASES:
        runs, ran = {}, True
        for kind, image, package in (("raw", raw, False), ("package", pkg, True)):
            d = os.path.join(out, "%s-%s" % (name, kind))
            res = fwtest(image, cases[name], d, package)
            runs[kind] = d
            if res.returncode != 0:
                ran = False
                problems.append("%s from the %s: fwtest exit %d: %s" % (name, kind, res.returncode, res.stderr.strip()[-300:]))
        if ran:
            got = compare(name, runs["raw"], runs["package"], r["flash"], open(raw, "rb").read())
            problems += got
            print("%-10s %s" % (name, "the same from the raw image and the package" if not got else "DIFFERENT"))
    for n, label, b in fwsc.broken(app):
        f = os.path.join(out, "broken-%d-%s.fwsc" % (n, label))
        with open(f, "wb") as fh:
            fh.write(b)
        try:
            fwsc.check(b)
            words = None
        except ValueError as e:
            words = str(e).split(": ", 1)[1]
        res = fwtest(f, ["--ms", "1"], os.path.join(out, "broken-%d-%s" % (n, label)), True)
        msg = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else ""
        want = "fwtest: the package is refused: %s" % words
        ok = res.returncode == 2 and msg == want
        print("check %d %-20s exit %d: %s%s" % (n, label, res.returncode, msg, "" if ok else "   (wanted: exit 2, %s)" % want))
        if not ok:
            problems.append("broken package %d-%s: fwtest's refusal is not the reader's" % (n, label))
    for p in problems:
        print("FAIL: " + p)
    print("C-PACKAGE: %s" % ("PASS" if not problems else "FAIL"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
