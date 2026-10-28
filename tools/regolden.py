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
  regolden.py --presets-out NEW --presets-old OLD [--only P01 ...] [--write]
      The same for tests/fw/golden/presets.json (M8b; tools/preset_suite.py's
      --out on the new image and on the base image).

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
PRESET_SUMS = os.path.join(ROOT, "tests", "fw", "golden", "presets.json")


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


def plan_hashes(sums_path, new_dir, old_dir, wav_of, hash_of, only=None):
    """[(key, new hash, state, detail)] for a golden file of sound
    hashes: wav_of(dir, key) the run's WAV, hash_of(wav) its hash."""
    with open(sums_path) as f:
        golden = json.load(f)
    rows = []
    for key in sorted(k for k in golden if k != "comment"):
        if only and key not in only:
            continue
        nw, ow = wav_of(new_dir, key), wav_of(old_dir, key)
        try:
            new, old = hash_of(nw), hash_of(ow)
        except (OSError, ValueError) as e:
            rows.append((key, None, "REFUSED", "no WAV: %s" % e))
            continue
        if new == golden[key]:
            rows.append((key, new, "same", "identical"))
        elif old != golden[key]:
            rows.append((key, new, "REFUSED", "the base run's WAV does not give the golden hash"))
        else:
            ok, detail = gt.shift_wav(ow, nw)
            rows.append((key, new, "shift" if ok else "REFUSED", detail))
    return rows


def plan_arp(new_dir, old_dir, only=None):
    """arp.json's sound hashes (plan_hashes)."""
    import arp_suite  # noqa: E402  (only here: it imports the store's tools)
    return plan_hashes(ARP_SUMS, new_dir, old_dir, lambda d, k: os.path.join(d, k, "audio.wav"),
                       lambda w: arp_suite.wav_sha256(os.path.dirname(w)), only)


def plan_presets(new_dir, old_dir, only=None):
    """presets.json's sound hashes (plan_hashes): key P01 is run p01."""
    import preset_suite  # noqa: E402
    return plan_hashes(PRESET_SUMS, new_dir, old_dir, lambda d, k: os.path.join(d, k.lower(), "audio.wav"),
                       preset_suite.sound_sha256, only)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", help="tools/fw-suite.py's output folder")
    ap.add_argument("--arp-out", help="tools/arp_suite.py's output folder on the new image")
    ap.add_argument("--arp-old", help="... and on the base image")
    ap.add_argument("--presets-out", help="tools/preset_suite.py's output folder on the new image")
    ap.add_argument("--presets-old", help="... and on the base image")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if not a.out and not (a.arp_out and a.arp_old) and not (a.presets_out and a.presets_old):
        ap.error("--out, or --arp-out with --arp-old, or --presets-out with --presets-old")
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
    if a.presets_out:
        for key, h, state, detail in plan_presets(os.path.abspath(a.presets_out), os.path.abspath(a.presets_old),
                                                  a.only):
            print("%-8s presets.json %s: %s" % (state, key, detail))
            refused += state == "REFUSED"
            if state == "shift":
                moved.append(("presets", key, h))
    if refused:
        print("regolden: %d REFUSED; nothing written" % refused)
        return 1
    if not a.write:
        print("regolden: %d golden(s) a pure time shift; --write to write them" % len(moved))
        return 0
    sums = {}
    for kind, x, y in moved:
        if kind == "file":
            shutil.copyfile(y, x)
        else:
            path = ARP_SUMS if kind == "arp" else PRESET_SUMS
            if path not in sums:
                with open(path) as f:
                    sums[path] = json.load(f)
            sums[path][x] = y
    for path, d in sums.items():
        with open(path, "w") as f:
            json.dump(d, f, indent=2, sort_keys=True)
            f.write("\n")
    if any(kind == "file" and os.path.basename(os.path.dirname(x)) == "midiout" for kind, x, _ in moved):
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "midi_scripts.py")], check=True)
        print("midiround's script written again from midiout's capture")
    print("regolden: %d golden(s) written" % len(moved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
