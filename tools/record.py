#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Runs every check and writes the test record (R-PROC-4, R-REC-1).

  record.py run --out DIR [--only C-A,C-B] [--skip C-X] [--with-merge]
      Runs the checks in CHECKS, writes DIR/report.json, DIR/report.md,
      DIR/logs/<check>.log, DIR/outputs/ (the build outputs), DIR/fwtest/
      (the firmware suite's outputs, but since M4 its audio captures only
      as names and SHA-256 in DIR/fwtest-audio.sha256: about a megabyte a
      record otherwise), DIR/presets/ (since M8b the preset bank's runs,
      their audio likewise in DIR/presets-audio.sha256), DIR/arp/ (since
      ARP the arpeggiator's runs, their audio likewise in
      DIR/arp-audio.sha256), DIR/spec-experiments.sha256 (the
      names and SHA-256 of the spec experiments' outputs, never the files)
      and DIR/SHA256SUMS (of all of those). Exit status 1 if any check failed.
      Before hashing, C-RECORD-PRIVATE withholds any file holding a private
      term, listing it in DIR/WITHHELD.json with the original's SHA-256.
  record.py compare --record REPORT.json --outputs DIR
      Compares DIR/SHA256SUMS with the outputs listed in a record
      (used by tools/reproduce). Exit status 1 on any difference.

Environment: COMMIT_RANGE (for C-COMMIT-MSG, default: every commit reachable
from HEAD), PERF_BASE_REF (for C-PERF: the history whose latest record is the
baseline, default origin/main), GITHUB_* (recorded, and used by
C-LOW-PROFILE, C-PERF and C-MERGE).
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python3"
SCHEMA = 1


def _low_profile_cmd():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return [PY, "-I", "tools/check-low-profile.py", "--require-api"]
    return [PY, "-I", "tools/check-low-profile.py", "--offline"]


def _private_cmd():
    # CI must have the terms (the PRIVATE_TERMS secret); locally they come
    # from tools/private-terms.local when it exists.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return [PY, "-I", "tools/check-private.py", "--require"]
    return [PY, "-I", "tools/check-private.py"]


def _commit_range():
    return os.environ.get("COMMIT_RANGE") or "..HEAD"


def _perf_cmd():
    # CI must find the records branch for the speed gate's baseline; a
    # clean folder may not have its blobs, and then compares nothing.
    argv = [PY, "-I", "tools/perf.py", "check", "--build", os.path.join(OUT, "build-a"),
            "--out", os.path.join(OUT, "perf"),
            "--base-ref", os.environ.get("PERF_BASE_REF") or "origin/main"]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        argv.append("--require-records")
    return argv


# Each check: id, title, requirement IDs, and either a command (list, or a
# function returning one, run from the repository root) or an internal
# function name. "records_only" checks run only with --with-merge.
CHECKS = [
    {"id": "C-UNIT", "title": "Unit tests of the tools",
     "reqs": ["R-PROC-1", "R-PROC-4", "R-REC-1", "R-CLEAN-3", "R-CLEAN-4", "R-PUB-1",
              "R-SEP-2", "R-SPEC-1", "R-SPEC-3", "R-AUDIT-1", "R-AUDIT-2", "R-AUDIT-3", "R-AUDIT-4",
              "R-AUDIT-5", "R-PERF-4", "R-BUILD-1", "R-FM-1", "R-FM-7", "R-MIDI-1", "R-MIDI-4",
              "R-MIDIOUT-2", "R-MIDIOUT-6", "R-STORE-1", "R-STORE-3", "R-STORE-4", "R-STORE-5",
              "R-STORE-6", "R-STORE-8", "R-UI-6", "R-UI-7", "R-UI-8", "R-PRESET-1", "R-ARP-1", "R-ARP-2",
              "R-ARP-7",
              "R-GOLD-1", "R-GOLD-2", "R-GOLD-3", "R-REL-1", "R-REL-2", "R-REL-3", "R-PKG-1",
              "R-BUILD-3", "R-STORE-10"],
     "cmd": [PY, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]},
    {"id": "C-REUSE", "title": "reuse lint (SPDX licence and copyright on every file)",
     "reqs": ["R-LIC-1", "R-LIC-2"], "cmd": ["reuse", "lint"]},
    {"id": "C-COMMIT-MSG", "title": "Commit messages follow .gitmessage",
     "reqs": ["R-PROC-1"],
     "cmd": lambda: [PY, "-I", "tools/check-commit-msg.py", "--range", _commit_range()]},
    {"id": "C-LOW-PROFILE", "title": "Low profile: name, description, topics, README",
     "reqs": ["R-PUB-1"], "cmd": _low_profile_cmd},
    {"id": "C-SECRETS", "title": "No secrets in tracked files",
     "reqs": ["R-PUB-2"], "cmd": [PY, "-I", "tools/check-tracked.py", "secrets"]},
    {"id": "C-PRIVATE", "title": "No private terms in tracked files or commit messages",
     "reqs": ["R-PUB-3"], "cmd": _private_cmd},
    {"id": "C-NO-TOOLCHAIN", "title": "No toolchain parts or binaries tracked",
     "reqs": ["R-REPRO-1"], "cmd": [PY, "-I", "tools/check-tracked.py", "no-toolchain"]},
    {"id": "C-DENY-LISTS", "title": "Claude Code deny lists never drop an entry",
     "reqs": ["R-CLEAN-4", "R-SEP-2"], "cmd": [PY, "-I", "tools/check-deny-lists.py"]},
    {"id": "C-TRANSCRIPTS", "title": "Archived session transcripts: banners and forbidden material",
     "reqs": ["R-CLEAN-1", "R-CLEAN-3", "R-CLEAN-5", "R-SEP-2"],
     "cmd": [PY, "-I", "tools/check-transcripts.py"]},
    {"id": "C-SEP-TERMS", "title": "No emulator-only identifiers outside the spec side's folders",
     "reqs": ["R-SEP-1", "R-SPEC-2"], "cmd": [PY, "-I", "tools/check-emulator-terms.py"]},
    {"id": "C-SPEC-LINT", "title": "docs/HARDWARE-SPEC.md: every entry has an ID, fact, sources, standing; no code; IDs kept",
     "reqs": ["R-SPEC-1", "R-SPEC-3"], "cmd": [PY, "-I", "tools/check-hardware-spec.py"]},
    {"id": "C-CLEAN-FOLDER", "title": "A fresh clean folder has no spec-side files and denies them",
     "reqs": ["R-CLEAN-1", "R-SEP-2"], "needs": "vendor/emulator", "cmd": ["sh", "tools/check-clean-folder.sh"]},
    {"id": "C-FWTEST-PIN", "title": "tools/fwtest runs an image pinned by digest",
     "reqs": ["R-SEP-3", "R-HARN-10"], "cmd": [PY, "-I", "tools/check-fwtest-pin.py"]},
    {"id": "C-SDK-PIN", "title": "Vendored SDK files match the pinned commit",
     "reqs": ["R-REPRO-5", "R-LIC-2"], "cmd": ["sh", "tools/fetch-sdk.sh", "--verify"]},
    {"id": "C-PLAITS-PIN", "title": "Vendored Plaits files match the pinned upstream commits",
     "reqs": ["R-REPRO-7", "R-LIC-2"], "cmd": ["sh", "tools/fetch-plaits.sh", "--verify"]},
    {"id": "C-EMU-PIN", "title": "Vendored emulator crates match the pinned upstream commit",
     "reqs": ["R-REPRO-6", "R-LIC-2"], "cmd": ["sh", "tools/fetch-emulator.sh", "--verify"]},
    {"id": "C-IMAGE", "title": "Build container (pinned base, toolchain SHA-256 checked)",
     "reqs": ["R-REPRO-1", "R-REPRO-2"], "cmd": ["sh", "tools/build.sh", "image"]},
    {"id": "C-BUILD-A", "title": "Build A in a fresh container (source at /mnt/small-beeps-src)",
     "reqs": ["R-REPRO-3", "R-BUILD-1"],
     "cmd": lambda: ["sh", "tools/build.sh", "build", "--out", os.path.join(OUT, "build-a")]},
    {"id": "C-BUILD-B", "title": "Build B in a fresh container (source at another path)",
     "reqs": ["R-REPRO-3"],
     "cmd": lambda: ["sh", "tools/build.sh", "build", "--out", os.path.join(OUT, "build-b"),
                     "--src-mount", "/tmp/elsewhere/small-beeps-src-b"]},
    {"id": "C-DETERMINISM", "title": "Builds A and B are byte-identical",
     "reqs": ["R-REPRO-3"], "internal": "determinism"},
    # The firmware (M0d): its size from build A, and its fwtest suite.
    {"id": "C-FW-SIZE", "title": "Firmware image size (code, data, bss) from build A",
     "reqs": ["R-BUILD-2"], "internal": "firmware_size"},
    {"id": "C-FW-SUITE", "title": "Firmware in fwtest: boot, clock, tick and heartbeat timing, vector table, idle, fault and stray reports, the screen, the panel's keys, encoders, pot and LEDs, the audio output and the test instrument (tests/fw/boot.suite)",
     "reqs": ["R-BOOT-1", "R-BOOT-2", "R-BOOT-3", "R-BOOT-4", "R-BOOT-5", "R-CLK-1",
              "R-IRQ-1", "R-IRQ-2", "R-IRQ-3", "R-IRQ-4",
              "R-LCD-1", "R-LCD-2", "R-LCD-3", "R-LCD-4", "R-LCD-5", "R-LCD-6",
              "R-KEY-1", "R-KEY-2", "R-KEY-3", "R-ENC-1", "R-ENC-2", "R-POT-1", "R-POT-2",
              "R-LED-1", "R-LED-2", "R-LED-3", "R-INPUT-1", "R-INPUT-2", "R-INPUT-3",
              "R-AUD-1", "R-AUD-2", "R-AUD-3", "R-AUD-4", "R-AUD-5", "R-AUD-6", "R-AUD-7",
              "R-FM-1", "R-FM-3", "R-FM-4", "R-FM-5", "R-FM-6", "R-FM-8", "R-FM-9",
              "R-MIDI-1", "R-MIDI-2", "R-MIDI-3", "R-MIDI-4", "R-MIDI-5", "R-MIDI-6", "R-MIDI-7",
              "R-MIDIOUT-1", "R-MIDIOUT-2", "R-MIDIOUT-3", "R-MIDIOUT-4", "R-MIDIOUT-5", "R-MIDIOUT-6",
              "R-MIDIOUT-7", "R-MIDIOUT-8",
              "R-STORE-1", "R-STORE-2", "R-STORE-3", "R-STORE-4", "R-STORE-5", "R-STORE-6",
              "R-STORE-7", "R-STORE-8", "R-STORE-9",
              "R-UI-1", "R-UI-2", "R-UI-3", "R-UI-4", "R-UI-5", "R-UI-6", "R-UI-7", "R-UI-8",
              "R-UI-9", "R-UI-10", "R-UI-11", "R-UI-12", "R-UI-13", "R-UI-14", "R-ARP-7",
              "R-GOLD-1", "R-GOLD-2"],
     "cmd": lambda: [PY, "-I", "tools/fw-suite.py", "--build", os.path.join(OUT, "build-a"),
                     "--out", os.path.join(OUT, "fwtest")]},
    # The preset bank (M8b): every preset played in fwtest and checked.
    {"id": "C-PRESETS", "title": "The preset bank in fwtest: each preset's reference note (clipping, DC, clicks, loudness, its category's shape), 16 voices, golden SHA-256 (tools/preset_suite.py)",
     "reqs": ["R-PRESET-1", "R-PRESET-2", "R-PRESET-3", "R-PRESET-4"],
     "cmd": lambda: [PY, "-I", "tools/preset_suite.py", "--image", os.path.join(OUT, "build-a", "app.bin"),
                     "--out", os.path.join(OUT, "presets")]},
    # The arpeggiator (ARP): its runs in fwtest against its model.
    {"id": "C-ARP", "title": "The arpeggiator in fwtest: each mode and rate against its model, the frames of its steps, MIDI clock in and out, MIDI out, no stuck notes, its screen, saving, under load (tools/arp_suite.py)",
     "reqs": ["R-ARP-1", "R-ARP-2", "R-ARP-3", "R-ARP-4", "R-ARP-5", "R-ARP-6", "R-ARP-7", "R-ARP-8", "R-GOLD-1"],
     "cmd": lambda: [PY, "-I", "tools/arp_suite.py", "--image", os.path.join(OUT, "build-a", "app.bin"),
                     "--out", os.path.join(OUT, "arp")]},
    # Phase A1: the firmware's .fwsc in fwtest's package path (docs/A1-PLAN.md).
    {"id": "C-PACKAGE", "title": "The firmware as a .fwsc: packed from build A's package link, it boots in fwtest's package path as the raw image does in the suite's main cases, and fwtest refuses each broken package at the reader's check (tools/package_suite.py)",
     "reqs": ["R-PKG-1", "R-PKG-2"],
     "cmd": lambda: [PY, "-I", "tools/package_suite.py", "--build", os.path.join(OUT, "build-a"),
                     "--out", os.path.join(OUT, "package")]},
    # The seams for firmwares built on small-beeps (clean-1027).
    {"id": "C-SEAMS", "title": "Seams for firmwares built on small-beeps: the build's write-back store check, outside sources, the engine seam, the platform alone, core 1's start, the runtime, the SysEx tap, raw MIDI out, the store's firmware kinds (tools/seams_suite.py)",
     "reqs": ["R-BUILD-3", "R-BUILD-4", "R-ENG-1", "R-PLAT-1", "R-CORE-1", "R-RT-1", "R-MIDI-8",
              "R-MIDIOUT-9", "R-STORE-10"],
     "cmd": lambda: [PY, "-I", "tools/seams_suite.py", "--build", os.path.join(OUT, "build-a"),
                     "--out", os.path.join(OUT, "seams")]},
    # M9's app release: made twice from build A, the same bytes, verified.
    {"id": "C-RELEASE", "title": "The app release from build A, made twice: byte for byte the same; release.json format 1.0; the .fm1img passes the app's checks in order (tools/release.py selftest)",
     "reqs": ["R-REL-1", "R-REL-2"],
     "cmd": lambda: [PY, "-I", "tools/release.py", "selftest", "--build", os.path.join(OUT, "build-a"),
                     "--out", os.path.join(OUT, "release")]},
    # Performance (M0e): size, RAM, stack high-water and speed, gated.
    {"id": "C-PERF", "title": "Firmware size, RAM, stack high-water and instructions per period, within budget and the 3% speed gate",
     "reqs": ["R-PERF-1", "R-PERF-2", "R-PERF-3", "R-LCD-6", "R-MIDIOUT-3", "R-UI-4", "R-ARP-8"], "cmd": _perf_cmd},
    {"id": "C-PERF-PROBES", "title": "Deliberately slower and bigger builds fail the performance gates; a known stack use shows",
     "reqs": ["R-PERF-3", "R-PERF-5"],
     "cmd": lambda: [PY, "-I", "tools/perf.py", "probes", "--build", os.path.join(OUT, "build-a"),
                     "--out", os.path.join(OUT, "perf-probes")]},
    {"id": "C-PLAITS-BENCH", "title": "The Plaits load test: demo builds, soft-float exact, every engine measured, clean audio",
     "reqs": ["R-PLAITS-1", "R-PLAITS-2", "R-PLAITS-3", "R-PLAITS-4"],
     "cmd": lambda: [PY, "-I", "tools/plaits-bench.py", "run", "--out", os.path.join(OUT, "plaits"),
                     "--perf", os.path.join(OUT, "perf", "perf.json")]},
    # The harness (spec side): skipped where harness/ isn't on disk.
    {"id": "C-HARNESS-SCOPE", "title": "The harness uses no stock-boot path (packages only through the package reader)",
     "reqs": ["R-HARN-9"], "needs": "harness", "cmd": ["sh", "harness/ci.sh", "scope"]},
    {"id": "C-HARNESS-IMAGES", "title": "Harness test images rebuild identically with the pinned toolchain",
     "reqs": ["R-HARN-8"], "needs": "harness", "cmd": ["sh", "harness/tests/images/build.sh", "--check"]},
    {"id": "C-HARNESS-IMAGE", "title": "fwtest container (pinned bases, offline build)",
     "reqs": ["R-HARN-8"], "needs": "harness", "cmd": ["sh", "harness/ci.sh", "image"]},
    {"id": "C-HARNESS-IMAGE-REPRO", "title": "The fwtest container rebuilds to the same image ID (from scratch, later, from a context with other file times and owners)",
     "reqs": ["R-HARN-8"], "needs": "harness", "cmd": ["sh", "harness/ci.sh", "repro"]},
    {"id": "C-HARNESS-TEST", "title": "The harness's own tests (cargo test in the container)",
     "reqs": ["R-HARN-1", "R-HARN-2", "R-HARN-3", "R-HARN-4", "R-HARN-5", "R-HARN-6", "R-HARN-7"],
     "needs": "harness", "cmd": ["sh", "harness/ci.sh", "test"]},
    {"id": "C-HARNESS-SUITE-A", "title": "Harness suite, run A (fresh container, tests at /mnt/harness-a)",
     "reqs": ["R-HARN-1", "R-HARN-2", "R-HARN-3", "R-HARN-4", "R-HARN-5", "R-HARN-7"], "needs": "harness",
     "cmd": lambda: ["sh", "harness/ci.sh", "suite", os.path.join(OUT, "harness-a"), "/mnt/harness-a"]},
    {"id": "C-HARNESS-SUITE-B", "title": "Harness suite, run B (fresh container, tests at another path)",
     "reqs": ["R-HARN-6"], "needs": "harness",
     "cmd": lambda: ["sh", "harness/ci.sh", "suite", os.path.join(OUT, "harness-b"), "/tmp/elsewhere/harness-b"]},
    {"id": "C-HARNESS-DET", "title": "Harness suite runs A and B are byte-identical",
     "reqs": ["R-HARN-6"], "needs": "harness", "internal": "harness_determinism"},
    {"id": "C-SPEC-EXPERIMENTS", "title": "Spec-side experiments rebuild identically and give the results the spec cites",
     "reqs": ["R-SPEC-4"], "needs": "harness",
     "cmd": lambda: ["sh", "harness/spec-experiments/run.sh", os.path.join(OUT, "spec-experiments")]},
    # Last, over the record's own files before they are hashed and stamped:
    # cmd_run runs it after every other check (record_private).
    {"id": "C-RECORD-PRIVATE", "title": "No private terms in the record's own files (any that hold one are withheld, named with their SHA-256)",
     "reqs": ["R-PUB-3"], "internal": "record_private", "last": True},
    {"id": "C-MERGE", "title": "Signed owner merge of a pull request that passed CI",
     "reqs": ["R-PROC-2"], "records_only": True,
     "cmd": lambda: [PY, "-I", "tools/check-merge.py", git("rev-parse", "HEAD")]},
]

OUT = ""
FIRMWARE_SIZE = {}


def git(*args):
    try:
        return subprocess.run(["git", "-C", ROOT] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums(path):
    sums = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                digest, name = line.split(None, 1)
                sums[name.strip().lstrip("*")] = digest
    return sums


def run_cmd(argv):
    try:
        p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except OSError as e:
        return 127, "could not run %s: %s\n" % (argv[0], e)


def determinism():
    a, b = os.path.join(OUT, "build-a"), os.path.join(OUT, "build-b")
    lines, ok = [], True
    try:
        sa, sb = read_sums(os.path.join(a, "SHA256SUMS")), read_sums(os.path.join(b, "SHA256SUMS"))
    except OSError as e:
        return 1, "missing build output: %s\n" % e
    if sorted(sa) != sorted(sb):
        ok = False
        lines.append("different file lists: %s vs %s" % (sorted(sa), sorted(sb)))
    for name in sorted(set(sa) & set(sb)):
        with open(os.path.join(a, name), "rb") as fa, open(os.path.join(b, name), "rb") as fb:
            same = fa.read() == fb.read()
        lines.append("%s %s %s" % ("IDENTICAL" if same else "DIFFERENT", name, sa[name]))
        ok = ok and same
    if not sa:
        ok = False
        lines.append("no outputs")
    lines.append("determinism: %s" % ("PASS" if ok else "FAIL"))
    return (0 if ok else 1), "\n".join(lines) + "\n"


def firmware_size():
    """Reads build A's app.size (tools/build.sh) into the record."""
    path = os.path.join(OUT, "build-a", "app.size")
    try:
        with open(path) as f:
            pairs = [l.split() for l in f if l.strip()]
        size = {k: int(v) for k, v in pairs}
    except (OSError, ValueError) as e:
        return 1, "cannot read %s: %s\n" % (path, e)
    missing = [k for k in ("code", "data", "bss", "image", "stack") if k not in size]
    if missing:
        return 1, "app.size lacks %s\n" % ", ".join(missing)
    FIRMWARE_SIZE.clear()
    FIRMWARE_SIZE.update(size)
    return 0, "".join("%-5s %8d bytes\n" % (k, size[k]) for k in sorted(size))


def tree_files(top):
    out = {}
    for dirpath, _, names in os.walk(top):
        for n in names:
            p = os.path.join(dirpath, n)
            out[os.path.relpath(p, top)] = sha256_file(p)
    return out


def harness_determinism():
    """Compares suite runs A and B file by file, then keeps A's result.json,
    junit.xml and the hashes of every output in the record (harness/)."""
    a, b = os.path.join(OUT, "harness-a", "suite"), os.path.join(OUT, "harness-b", "suite")
    fa, fb = tree_files(a), tree_files(b)
    lines, ok = [], bool(fa)
    if sorted(fa) != sorted(fb):
        ok = False
        lines.append("different file lists: %d vs %d files" % (len(fa), len(fb)))
    for name in sorted(set(fa) & set(fb)):
        same = fa[name] == fb[name]
        ok = ok and same
        lines.append("%s %s %s" % ("IDENTICAL" if same else "DIFFERENT", name, fa[name]))
    if not fa:
        lines.append("no outputs")
    keep = os.path.join(OUT, "harness")
    if fa:
        os.makedirs(keep, exist_ok=True)
        for n in ("result.json", "junit.xml"):
            if n in fa:
                shutil.copyfile(os.path.join(a, n), os.path.join(keep, n))
        with open(os.path.join(keep, "outputs.sha256"), "w") as f:
            for name in sorted(fa):
                f.write("%s  %s\n" % (fa[name], name))
    lines.append("harness determinism: %s" % ("PASS" if ok else "FAIL"))
    return (0 if ok else 1), "\n".join(lines) + "\n"


def hashes_only(top, manifest):
    """Replaces a folder of spec-experiment outputs (memory dumps, captures,
    audio) with a list of their names and SHA-256: a record never keeps the
    files themselves (CONTRIBUTING.md, "Records in a clean folder")."""
    if not os.path.isdir(top):
        return
    files = tree_files(top)
    with open(manifest, "w") as f:
        for name in sorted(files):
            f.write("%s  %s\n" % (files[name], name))
    shutil.rmtree(top)


def audio_hashes_only(top, manifest, ext=".wav"):
    """Since M4: replaces the firmware suite's audio captures under top
    with a list of their names and SHA-256 in manifest. The suite checked
    them, and they are deterministic, so the hash is enough to match a
    rerun; the rest of the suite's outputs stay."""
    if not os.path.isdir(top):
        return
    files = {n: h for n, h in tree_files(top).items() if n.endswith(ext)}
    if not files:
        return
    with open(manifest, "w") as f:
        for name in sorted(files):
            f.write("%s  %s\n" % (files[name], name))
    for name in files:
        os.remove(os.path.join(top, name))


def dockerfile_pins():
    pins = {}
    with open(os.path.join(ROOT, "tools", "Dockerfile")) as f:
        text = f.read()
    for key in ("BASE", "SNAPSHOT", "TOOLCHAIN_NAME", "TOOLCHAIN_URL", "TOOLCHAIN_SHA256"):
        m = re.search(r"^ARG %s=(\S+)" % key, text, re.M)
        if m:
            pins[key.lower()] = m.group(1)
    m = re.search(r"^# syntax=(\S+)", text, re.M)
    if m:
        pins["dockerfile_frontend"] = m.group(1)
    m = re.search(r"SOURCE_DATE_EPOCH=(\d+)", text)
    if m:
        pins["source_date_epoch"] = m.group(1)
    return pins


def _private_tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_private",
                                                  os.path.join(ROOT, "tools", "check-private.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_private():
    """C-RECORD-PRIVATE (R-PUB-3): every file of the record so far is
    checked for the owner's private terms. A file holding one is deleted
    and listed, with the SHA-256 of the original, in WITHHELD.json; the
    rest of the record is still written. Output names files only."""
    cp = _private_tool()
    terms = cp.load_terms()
    if not terms:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            return 1, "no private terms available (the PRIVATE_TERMS secret)"
        return 0, "no private terms available here: nothing checked"
    gone = cp.withhold(OUT, terms)
    log = ["withheld %s (sha256 %s)" % (g["file"], g["sha256"]) for g in gone]
    log.append("%d term(s); %s" % (len(terms), "%d file(s) withheld" % len(gone) if gone else "no file holds one"))
    return (1 if gone else 0), "\n".join(log)


def tool_version(argv):
    code, out = run_cmd(argv)
    return out.strip().splitlines()[0] if code == 0 and out.strip() else "unavailable"


def environment():
    env = {"dockerfile": dockerfile_pins()}
    with open(os.path.join(ROOT, "tools", "fetch-sdk.sh")) as f:
        m = re.search(r"^SDK_COMMIT=(\S+)", f.read(), re.M)
    env["sdk_commit"] = m.group(1) if m else ""
    env["sdk_sha256sums"] = sha256_file(os.path.join(ROOT, "vendor", "jieli-sdk", "SHA256SUMS"))
    with open(os.path.join(ROOT, "config", "fwtest-image")) as f:
        env["fwtest_image"] = [l.strip() for l in f if l.strip() and not l.startswith("#")][0]
    with open(os.path.join(ROOT, "tools", "fetch-emulator.sh")) as f:
        m = re.search(r"^UPSTREAM_COMMIT=(\S+)", f.read(), re.M)
    env["emulator_commit"] = m.group(1) if m else ""
    if os.path.isdir(os.path.join(ROOT, "harness")):
        env["harness_image_tag"] = run_cmd(["sh", "harness/ci.sh", "tag"])[1].strip()
    tag = run_cmd(["sh", "tools/build.sh", "image-tag"])[1].strip()
    env["build_image_tag"] = tag
    env["build_image_id"] = tool_version(["docker", "image", "inspect", "--format", "{{.Id}}", tag])
    env["docker"] = tool_version(["docker", "version", "--format",
                                  "client {{.Client.Version}} server {{.Server.Version}}"])
    env["python"] = platform.python_version()
    env["reuse"] = tool_version(["reuse", "--version"])
    env["git"] = tool_version(["git", "--version"])
    env["host"] = "%s %s %s" % (platform.system(), platform.release(), platform.machine())
    env["claude_configs"] = {n: sha256_file(os.path.join(ROOT, "config", "claude", n))
                             for n in ("clean.json", "spec.json", "handmade-settings.json",
                                       "handmade-spec-settings.json")}
    env["github"] = {k: os.environ[k] for k in sorted(os.environ)
                     if k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                              "GITHUB_WORKFLOW", "GITHUB_EVENT_NAME", "GITHUB_REF",
                              "GITHUB_SHA", "RUNNER_OS", "RUNNER_ARCH", "ImageOS",
                              "ImageVersion")}
    return env


def requirements_table():
    rows = []
    with open(os.path.join(ROOT, "docs", "REQUIREMENTS.md"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\| (R-[A-Z]+-\d+) \|(.*)\|(.*)\|(.*)\|\s*$", line)
            if m:
                rows.append({"id": m.group(1), "since": m.group(3).strip(),
                             "checked_by": m.group(4).strip()})
    return rows


def traceability(checks, defined=None):
    """requirement -> checks -> result. A requirement passes only if every
    defined check that covers it ran and passed; checks that didn't run in
    this record are named."""
    defined = CHECKS if defined is None else defined
    ran = {c["id"]: c["result"] for c in checks if c["result"] != "SKIP"}
    table = []
    for req in requirements_table():
        mine = [c["id"] for c in defined if req["id"] in c["reqs"]]
        results = [ran[c] for c in mine if c in ran]
        missing = [c for c in mine if c not in ran]
        if not mine:
            result = "not machine-checked (%s)" % req["checked_by"]
        elif "FAIL" in results:
            result = "FAIL"
        elif not results:
            result = "not run in this record (%s)" % ", ".join(missing)
        elif missing:
            result = "PASS (%s not run)" % ", ".join(missing)
        else:
            result = "PASS"
        table.append({"requirement": req["id"], "checks": mine, "result": result})
    return table


def perf_markdown(perf):
    """The record's performance section (tools/perf.py's perf.json)."""
    cur = perf.get("current") or {}
    L = ["Overall: **%s**. Period: %s." % (perf.get("result"), perf.get("period")), ""]
    if not cur.get("error"):
        L += ["| Measure | Value |", "|---------|-------|"]
        # tools/perf.py's MEASURES, and since M2 each perf run's numbers
        for k in ("code", "data", "bss", "image", "static_ram", "stack_reserved", "stack_high_water",
                  "stack_method", "startup_instructions", "instructions", "periods", "instructions_per_period",
                  "frame_update_us", "render_us", "heartbeat_update_us"):
            if k in cur:
                L.append("| %s | %s |" % (k, cur[k]))
        for r in cur.get("runs", []):
            L.append("| run of %s ms | %s instructions, %s periods, ended at %s ms |"
                     % (r.get("ms"), r.get("instructions"), r.get("periods"), r.get("emulated_ms")))
        L.append("")
    loaded = cur.get("loaded") or {}
    if loaded:
        # since M4b: the loaded measure (tools/perf.py)
        L += ["Loaded (`%s`, SHA-256 `%s`): %s" % (
            loaded.get("script"), loaded.get("script_sha256"), loaded.get("error") or
            "%s instructions for %s audio blocks, %s a block." % (
                loaded.get("instructions"), loaded.get("periods"), loaded.get("instructions_per_period"))), ""]
        for r in loaded.get("runs", []):
            L.append("- loaded run of %s ms: %s instructions, %s periods, ended at %s ms"
                     % (r.get("ms"), r.get("instructions"), r.get("periods"), r.get("emulated_ms")))
        L.append("")
    L += ["Baseline: %s." % perf.get("baseline_note"), ""]
    if perf.get("loaded"):
        L += ["Loaded baseline: %s." % perf["loaded"].get("baseline_note"), ""]
    L += ["| Gate | Result | Detail |", "|------|--------|--------|"]
    L += ["| %s | %s | %s |" % (v["gate"], v["result"], v["detail"]) for v in perf.get("gates", [])]
    return L


def write_markdown(report, path):
    L = ["# Test record %s" % report["commit"][:12], "",
         "- Commit: `%s`" % report["commit"],
         "- Subject: %s" % report["subject"],
         "- Tree: `%s`" % report["tree"],
         "- Written: %s" % report["created_utc"],
         "- Overall: **%s**" % report["overall"]]
    gh = report["environment"]["github"]
    if gh.get("GITHUB_RUN_ID"):
        L.append("- CI run: https://github.com/%s/actions/runs/%s"
                 % (gh.get("GITHUB_REPOSITORY"), gh["GITHUB_RUN_ID"]))
    L += ["", "## Checks", "", "| Check | Title | Requirements | Result | Seconds |",
          "|-------|-------|--------------|--------|---------|"]
    for c in report["checks"]:
        L.append("| %s | %s | %s | %s | %.1f |" % (c["id"], c["title"], ", ".join(c["reqs"]),
                                                   c["result"], c["seconds"]))
    if report.get("withheld"):
        L += ["", "## Withheld", "",
              "These files held one of the owner's private terms and are not in this record "
              "(C-RECORD-PRIVATE, R-PUB-3). Only each original's SHA-256 is kept.", "",
              "| File | SHA-256 |", "|------|---------|"]
        L += ["| `%s` | `%s` |" % (w["file"], w["sha256"]) for w in report["withheld"]]
    L += ["", "## Outputs", "", "| File | SHA-256 |", "|------|---------|"]
    for name, digest in sorted(report["outputs"].items()):
        L.append("| `%s` | `%s` |" % (name, digest))
    if report.get("firmware_size"):
        L += ["", "## Firmware size", "", "| Part | Bytes |", "|------|-------|"]
        for part in ("code", "data", "bss", "image", "stack"):
            if part in report["firmware_size"]:
                L.append("| %s | %d |" % (part, report["firmware_size"][part]))
    if report.get("perf"):
        L += ["", "## Performance", ""] + perf_markdown(report["perf"])
    if report.get("plaits_md"):
        # since M4b: tools/plaits-bench.py's own table
        L += [""] + report["plaits_md"].rstrip("\n").splitlines()
    L += ["", "## Traceability", "", "| Requirement | Checks | Result |",
          "|-------------|--------|--------|"]
    for t in report["traceability"]:
        L.append("| %s | %s | %s |" % (t["requirement"], ", ".join(t["checks"]) or "-",
                                       t["result"]))
    L += ["", "## Environment", "", "```json",
          json.dumps(report["environment"], indent=2, sort_keys=True), "```", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def cmd_run(a):
    global OUT
    OUT = os.path.abspath(a.out)
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    skip = set(a.skip.split(",")) if a.skip else set()
    results = []
    for c in CHECKS:
        if only is not None and c["id"] not in only:
            continue
        if c["id"] in skip or (c.get("records_only") and not a.with_merge) or c.get("last"):
            continue
        start = time.time()
        if c.get("needs") and not os.path.isdir(os.path.join(ROOT, c["needs"])):
            with open(os.path.join(OUT, "logs", c["id"] + ".log"), "w", encoding="utf-8") as f:
                f.write("SKIP: %s/ is not on disk (a clean folder leaves it out)\n" % c["needs"])
            print("%-14s %-4s %6.1fs  %s" % (c["id"], "SKIP", 0.0, c["title"]), flush=True)
            results.append({"id": c["id"], "title": c["title"], "reqs": c["reqs"], "command": "",
                            "result": "SKIP", "exit_status": 0, "seconds": 0.0,
                            "log": "logs/%s.log" % c["id"]})
            continue
        if "internal" in c:
            code, log = globals()[c["internal"]]()
            argv = ["(internal) " + c["internal"]]
        else:
            argv = c["cmd"]() if callable(c["cmd"]) else c["cmd"]
            code, log = run_cmd(argv)
        secs = time.time() - start
        result = "PASS" if code == 0 else "FAIL"
        with open(os.path.join(OUT, "logs", c["id"] + ".log"), "w", encoding="utf-8") as f:
            f.write("$ %s\n%s\nexit status %d\n" % (" ".join(argv), log, code))
        print("%-14s %-4s %6.1fs  %s" % (c["id"], result, secs, c["title"]), flush=True)
        results.append({"id": c["id"], "title": c["title"], "reqs": c["reqs"],
                        "command": " ".join(argv), "result": result, "exit_status": code,
                        "seconds": round(secs, 1), "log": "logs/%s.log" % c["id"]})

    outputs = {}
    build_a = os.path.join(OUT, "build-a")
    if os.path.exists(os.path.join(build_a, "SHA256SUMS")):
        outputs = read_sums(os.path.join(build_a, "SHA256SUMS"))
        os.makedirs(os.path.join(OUT, "outputs"), exist_ok=True)
        for name in outputs:
            shutil.copyfile(os.path.join(build_a, name), os.path.join(OUT, "outputs", name))
    for d in ("build-a", "build-b", "harness-a", "harness-b"):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)
    hashes_only(os.path.join(OUT, "spec-experiments"), os.path.join(OUT, "spec-experiments.sha256"))
    audio_hashes_only(os.path.join(OUT, "fwtest"), os.path.join(OUT, "fwtest-audio.sha256"))
    # Since M8b the preset bank's runs: its 128 WAVs (64 MB) as hashes too.
    audio_hashes_only(os.path.join(OUT, "presets"), os.path.join(OUT, "presets-audio.sha256"))
    # Since ARP the arpeggiator's runs: their WAVs as hashes too.
    audio_hashes_only(os.path.join(OUT, "arp"), os.path.join(OUT, "arp-audio.sha256"))
    for c in CHECKS:
        if not c.get("last") or c["id"] in skip or (only is not None and c["id"] not in only):
            continue
        start = time.time()
        code, log = globals()[c["internal"]]()
        result = "PASS" if code == 0 else "FAIL"
        with open(os.path.join(OUT, "logs", c["id"] + ".log"), "w", encoding="utf-8") as f:
            f.write("$ (internal) %s\n%s\nexit status %d\n" % (c["internal"], log, code))
        print("%-14s %-4s %6.1fs  %s" % (c["id"], result, time.time() - start, c["title"]), flush=True)
        results.append({"id": c["id"], "title": c["title"], "reqs": c["reqs"],
                        "command": "(internal) " + c["internal"], "result": result,
                        "exit_status": code, "seconds": round(time.time() - start, 1),
                        "log": "logs/%s.log" % c["id"]})
    withheld = []
    if os.path.exists(os.path.join(OUT, "WITHHELD.json")):
        with open(os.path.join(OUT, "WITHHELD.json")) as f:
            withheld = json.load(f)["withheld"]
    perf = {}
    try:
        with open(os.path.join(OUT, "perf", "perf.json")) as f:
            perf = json.load(f)
    except (OSError, ValueError):
        pass

    plaits, plaits_md = {}, ""
    try:
        with open(os.path.join(OUT, "plaits", "plaits.json")) as f:
            plaits = json.load(f)
        with open(os.path.join(OUT, "plaits", "plaits.md")) as f:
            plaits_md = f.read()
    except (OSError, ValueError):
        pass

    report = {
        "schema": SCHEMA,
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "subject": git("log", "-1", "--format=%s"),
        "worktree_clean": git("status", "--porcelain") == "",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment": environment(),
        "checks": results,
        "outputs": outputs,
        "firmware_size": dict(FIRMWARE_SIZE),
        "perf": perf,
        "plaits": plaits,
        "plaits_md": plaits_md,
        "withheld": withheld,
        "traceability": traceability(results),
        "overall": "PASS" if results and all(r["result"] in ("PASS", "SKIP") for r in results) else "FAIL",
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    write_markdown(report, os.path.join(OUT, "report.md"))
    if any(c["id"] == "C-RECORD-PRIVATE" for c in results):
        cp = _private_tool()
        terms = cp.load_terms()
        if terms and cp.withhold(OUT, terms):
            print("report files held a private term and were withheld (WITHHELD.json)")
            report["overall"] = "FAIL"

    files = []
    for dirpath, _, names in os.walk(OUT):
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), OUT)
            if rel != "SHA256SUMS" and not rel.endswith(".ots"):
                files.append(rel)
    with open(os.path.join(OUT, "SHA256SUMS"), "w") as f:
        for rel in sorted(files):
            f.write("%s  %s\n" % (sha256_file(os.path.join(OUT, rel)), rel))
    print("overall: %s (record in %s)" % (report["overall"], OUT))
    return 0 if report["overall"] == "PASS" else 1


def cmd_compare(a):
    with open(a.record) as f:
        want = json.load(f)["outputs"]
    got = read_sums(os.path.join(a.outputs, "SHA256SUMS"))
    ok = bool(want)
    for name in sorted(set(want) | set(got)):
        w, g = want.get(name), got.get(name)
        status = "MATCH" if w == g else "DIFFERENT"
        ok = ok and w == g
        print("%-9s %s record=%s rebuilt=%s" % (status, name, w, g))
    print("REPRODUCED" if ok else "NOT REPRODUCED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--only")
    r.add_argument("--skip")
    r.add_argument("--with-merge", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("--record", required=True)
    c.add_argument("--outputs", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "compare":
        return cmd_compare(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
