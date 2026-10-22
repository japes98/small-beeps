#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Runs the firmware's fwtest suite and checks its heartbeat (check
C-FW-SUITE; R-BOOT-1 to R-BOOT-5).

  fw-suite.py --build DIR --out DIR

Copies DIR/app.bin (a tools/build.sh output) to out/fw/app.bin, where
tests/fw/boot.suite expects it, runs the suite through tools/fwtest (the
pinned image), and then checks every case's result.json and the heartbeat
case's beacon captures:

- each case completed: no fault, halt or hang; no unmodelled accesses; core
  1 never ran;
- every beacon holds the marker and the period of 24 000 ticks (1 ms of the
  24 MHz time base, HW-13);
- beats == ticks // period: one beat per whole period of the time base;
- each capture's ticks are no earlier than its time asked, less START_SLACK
  (main starts the time base a few instructions after the image starts),
  and no later than LATE_MS after it (captures can come late while the
  image waits, docs/HARNESS.md "Time");
- at the end of the run the time base agrees with fwtest's emulated time
  (result.json's emulated_ms, given to the microsecond) within
  START_SLACK: the stated tolerance of the heartbeat's timing, 10
  microseconds over the run.

Prints what it saw (the marker, and each capture's beats and time) for the
record, and exits 1 if anything failed.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = "tests/fw/boot.suite"
IMAGE = os.path.join("out", "fw", "app.bin")

MARKER = 0x44304253        # "SB0D", firmware/src/sb.h
TICKS_PER_MS = 24000       # HW-13
START_SLACK = 240          # ticks: 10 microseconds
LATE_MS = 5
CAPTURE = re.compile(r"^ram-01c00000-10-(?P<when>[0-9.]+ms|end)\.bin$")


def check_case(name, result):
    """Problems with one case's result.json."""
    run = result.get("run", {})
    problems = []
    if run.get("outcome") != "completed":
        problems.append("%s: outcome %s (%s)" % (name, run.get("outcome"), run.get("detail")))
    if run.get("unmodelled_accesses"):
        problems.append("%s: unmodelled accesses %s" % (name, run["unmodelled_accesses"]))
    if run.get("instructions", {}).get("core1", 0) != 0:
        problems.append("%s: core 1 ran" % name)
    return problems


def check_beacon(when_ms, data, end_ms=None):
    """Problems with one 16-byte beacon captured at when_ms (the time asked;
    end_ms is result.json's emulated_ms for the capture at the end)."""
    marker, beats, ticks, period = struct.unpack("<4I", data)
    problems = []
    if marker != MARKER:
        problems.append("marker 0x%08x, not 0x%08x" % (marker, MARKER))
    if period != TICKS_PER_MS:
        problems.append("period %d, not %d" % (period, TICKS_PER_MS))
        return problems
    if beats != ticks // period:
        problems.append("%d beats after %d ticks, not %d" % (beats, ticks, ticks // period))
    if end_ms is not None:
        expect = round(end_ms * TICKS_PER_MS)
        if abs(ticks - expect) > START_SLACK:
            problems.append("%d ticks at the end (%.3f ms), not within %d of %d"
                            % (ticks, end_ms, START_SLACK, expect))
    else:
        low = round(when_ms * TICKS_PER_MS) - START_SLACK
        high = round((when_ms + LATE_MS) * TICKS_PER_MS)
        if not low <= ticks <= high:
            problems.append("%d ticks at %s ms, not within %d to %d" % (ticks, when_ms, low, high))
    return problems


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
    problems, lines, last = [], [], -1
    if len(caps) < 2:
        problems.append("heartbeat: %d beacon captures, expected several" % len(caps))
    for when_ms, when, n in caps:
        with open(os.path.join(case_dir, n), "rb") as f:
            data = f.read()
        if len(data) != 16:
            problems.append("%s: %d bytes" % (n, len(data)))
            continue
        marker, beats, ticks, _ = struct.unpack("<4I", data)
        lines.append("  %-6s marker 0x%08x  beats %5d  ticks %9d (%.3f ms)"
                     % (when, marker, beats, ticks, ticks / TICKS_PER_MS))
        problems += ["heartbeat %s: %s" % (when, p) for p in
                     check_beacon(when_ms, data, end_ms if when == "end" else None)]
        if beats < last:
            problems.append("heartbeat %s: beats went back from %d to %d" % (when, last, beats))
        last = beats
    return problems, lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", required=True, help="a tools/build.sh output folder")
    ap.add_argument("--out", required=True, help="where the suite's outputs go (empty or new)")
    a = ap.parse_args()

    os.makedirs(os.path.join(ROOT, os.path.dirname(IMAGE)), exist_ok=True)
    shutil.copyfile(os.path.join(a.build, "app.bin"), os.path.join(ROOT, IMAGE))
    size = os.path.join(a.build, "app.size")
    if os.path.exists(size):
        with open(size) as f:
            print("image size: " + ", ".join(l.strip() for l in f if l.strip()))

    out = os.path.abspath(a.out)
    p = subprocess.run(["sh", "tools/fwtest", "suite", SUITE, "--out", out], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace").rstrip())
    problems = [] if p.returncode == 0 else ["fwtest suite exited %d" % p.returncode]

    for name in ("boot", "heartbeat"):
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
        if name == "boot":
            golden = result.get("golden") or []
            if not golden:
                problems.append("boot: no golden files compared")
            for g in golden:
                print("  golden %s: %s" % (g.get("name"), g.get("result")))
                if g.get("result") != "match":
                    problems.append("boot: golden %s: %s" % (g.get("name"), g.get("detail")))
        if name == "heartbeat" and "emulated_ms" in run:
            more, lines = check_heartbeat(os.path.join(out, name), result)
            problems += more
            print("\n".join(lines))

    for prob in problems:
        print("FAIL: " + prob)
    print("fw suite: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
