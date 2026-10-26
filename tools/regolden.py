#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Writes timing goldens again, only after proving the change a pure time
shift (docs/DESIGN-NOTES.md, "Timing goldens"; tools/goldtime.py, rule 3).

  regolden.py --out DIR [--only NAME ...] [--write]
      DIR: tools/fw-suite.py's --out. Every golden file of
      tests/fw/boot.suite's cases (their --golden folders,
      tests/fw/golden-midi/ and tests/fw/golden-live/) against that run's
      output of the same name.
  regolden.py --arp-out NEW --arp-old OLD [--only NAME ...] [--write]
      tests/fw/golden/arp.json's sound hashes: NEW and OLD are
      tools/arp_suite.py's --out on the new image and on the base image
      (whose WAVs must give the golden hashes); a hash moves only if the
      two runs' WAVs are the same sounds, moved.

For each golden file it prints "same", "shift" (proven: the same bytes,
notes and sound, only their times moved, with how far; for a screen in
golden-live/, the same outside the live spectrum, which shows the sound)
or "REFUSED" (and why). --write copies the proven ones over their goldens, and only if
nothing was refused: a change that is not a time shift is a change of
behaviour, made by hand in the commit that changes the behaviour, which
says so. When midiout's capture moves, tools/midi_scripts.py writes
midiround's script from it again.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goldtime as gt  # noqa: E402  (tools/, our own)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join(ROOT, "tests", "fw", "boot.suite")
MIDI_GOLDEN = os.path.join(ROOT, "tests", "fw", "golden-midi")
LIVE_GOLDEN = os.path.join(ROOT, "tests", "fw", "golden-live")
ARP_SUMS = os.path.join(ROOT, "tests", "fw", "golden", "arp.json")


def suite_goldens(suite=SUITE):
    """{case: its --golden folder} from a suite file, plus golden-midi's."""
    out = {}
    with open(suite) as f:
        for line in f:
            w = line.split()
            if not w or w[0].startswith("#") or "--golden" not in w:
                continue
            out.setdefault(w[0], []).append(os.path.normpath(os.path.join(os.path.dirname(suite),
                                                                          w[w.index("--golden") + 1])))
    for top in (MIDI_GOLDEN, LIVE_GOLDEN):
        for case in sorted(os.listdir(top)) if os.path.isdir(top) else []:
            out.setdefault(case, []).append(os.path.join(top, case))
    return out


def plan_suite(out_dir, only=None):
    """[(golden path, new path, state, detail)] for the suite's goldens."""
    rows = []
    for case, dirs in sorted(suite_goldens().items()):
        if only and case not in only:
            continue
        for d in dirs:
            for name in sorted(os.listdir(d)):
                if name.endswith(".tolerance"):
                    continue
                g, n = os.path.join(d, name), os.path.join(out_dir, case, name)
                ok, detail = gt.shift_file(g, n)
                rows.append((g, n, "same" if detail == "identical" else ("shift" if ok else "REFUSED"), detail))
    return rows


def plan_arp(new_dir, old_dir, only=None):
    """[(case, new hash, state, detail)] for arp.json's sound hashes."""
    import arp_suite  # noqa: E402  (only here: it imports the store's tools)
    with open(ARP_SUMS) as f:
        golden = json.load(f)
    rows = []
    for case in sorted(k for k in golden if k != "comment"):
        if only and case not in only:
            continue
        nd, od = os.path.join(new_dir, case), os.path.join(old_dir, case)
        try:
            new = arp_suite.wav_sha256(nd)
            old = arp_suite.wav_sha256(od)
        except OSError as e:
            rows.append((case, None, "REFUSED", "no WAV: %s" % e))
            continue
        if new == golden[case]:
            rows.append((case, new, "same", "identical"))
        elif old != golden[case]:
            rows.append((case, new, "REFUSED", "the base run's WAV does not give the golden hash"))
        else:
            ok, detail = gt.shift_wav(os.path.join(od, "audio.wav"), os.path.join(nd, "audio.wav"))
            rows.append((case, new, "shift" if ok else "REFUSED", detail))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="tools/fw-suite.py's output folder")
    ap.add_argument("--arp-out", help="tools/arp_suite.py's output folder on the new image")
    ap.add_argument("--arp-old", help="... and on the base image")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if not a.out and not (a.arp_out and a.arp_old):
        ap.error("--out, or --arp-out with --arp-old")
    refused, moved = 0, []
    if a.out:
        for g, n, state, detail in plan_suite(os.path.abspath(a.out), a.only):
            print("%-8s %s: %s" % (state, os.path.relpath(g, ROOT), detail))
            refused += state == "REFUSED"
            if state == "shift":
                moved.append(("file", g, n))
    if a.arp_out:
        for case, h, state, detail in plan_arp(os.path.abspath(a.arp_out), os.path.abspath(a.arp_old), a.only):
            print("%-8s arp.json %s: %s" % (state, case, detail))
            refused += state == "REFUSED"
            if state == "shift":
                moved.append(("arp", case, h))
    if refused:
        print("regolden: %d REFUSED; nothing written" % refused)
        return 1
    if not a.write:
        print("regolden: %d golden(s) a pure time shift; --write to write them" % len(moved))
        return 0
    sums = None
    for kind, x, y in moved:
        if kind == "file":
            shutil.copyfile(y, x)
        else:
            if sums is None:
                with open(ARP_SUMS) as f:
                    sums = json.load(f)
            sums[x] = y
    if sums is not None:
        with open(ARP_SUMS, "w") as f:
            json.dump(sums, f, indent=2, sort_keys=True)
            f.write("\n")
    if any(kind == "file" and os.path.basename(os.path.dirname(x)) == "midiout" for kind, x, _ in moved):
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "midi_scripts.py")], check=True)
        print("midiround's script written again from midiout's capture")
    print("regolden: %d golden(s) written" % len(moved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
