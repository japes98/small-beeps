#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The preset bank's tests (M8b; docs/M8-PROPOSAL.md, "Presets"):
every preset in tools/fm_patch.py's PRESETS played in fwtest by the
shipping image, through MIDI in: a program change, a reference note (C4
at velocity 100, held 2 s, then 1 s to fade), then a short phrase (C4 E4
G4 C5, then the C major chord held 1 s). Four runs at a time.

  preset_suite.py --image APP.bin --out DIR [--drop DIR] [--write-golden [--replace]]

Each reference note is checked:
- no clipping (no sample at 16-bit full scale) and no DC (the held note's
  mean under 0.5% of full scale);
- no click: the note's first sample under 5% of its peak (no jump from
  silence), and no step in the 5 ms after the note off more than twice
  the largest in the 5 ms before it;
- its loudness (the RMS of its loudest 20 ms) within 3 dB of the bank's
  target (TARGET_DB), so the bank plays at one level;
- its category's shape: a bass has most of its power below 300 Hz, a pad
  takes 50 ms or more to reach 3 dB under its peak, a pluck falls 30 dB
  within 2 s while held;
- on all 16 voices (a 16-note chord, 500 ms): no underrun, every block
  filled within its 1 451 us;
- the WAV against its SHA-256 in tests/fw/golden/presets.json (fwtest is
  exact), unless --write-golden writes them: the SHA-256 of its first
  HASH_FRAMES frames, whole blocks that end at least 2 ms before RUN_MS.
  The WAV ends when the run does, and a run that ends while core 0 waits
  ends late (docs/HARNESS.md, "Time"), by an amount that moves with core
  0's instruction count (fwtest 0.6.0's flash busy time moved P44's and
  P47's by a block), so the frames after that are left out.
tools/record.py's check C-PRESETS runs it (R-PRESET-1 to R-PRESET-4).
With --drop, each run's WAV is copied there as NN-name.wav, with
INDEX.md (number, name, category, what it is for, its loudness).
"""

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_analysis as aa  # noqa: E402  (tools/, our own)
import fm_patch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "fw", "golden", "presets.json")
FIRST_PROGRAM = 25          # fm.h: FM_PRESET0
TARGET_DB = -25.0           # dBFS RMS of each reference note's loudest 20 ms
TOLERANCE_DB = 3.0
NOTE_ON_MS, NOTE_OFF_MS, RUN_MS = 300, 2300, 6200
FULL = 32767
HASH_FRAMES = int((RUN_MS - 2) * aa.RATE / 1000) // 64 * 64   # 273 408


def script(program):
    lines = ["100 midi c0 %02x" % program, "%d midi 90 3c 64" % NOTE_ON_MS, "%d midi 80 3c 00" % NOTE_OFF_MS]
    t = 3300
    for note in (0x3C, 0x40, 0x43, 0x48):
        lines += ["%d midi 90 %02x 64" % (t, note), "%d midi 80 %02x 00" % (t + 230, note)]
        t += 250
    lines += ["4400 midi 90 3c 64 90 40 64 90 43 64", "5400 midi 80 3c 00 80 40 00 80 43 00"]
    return lines


def chord_script(program):
    """All 16 voices: 16 notes at once, C3 up a whole tone at a time."""
    notes = " ".join("90 %02x 64" % (48 + 2 * k) for k in range(16))
    return ["100 midi c0 %02x" % program, "300 midi " + notes]


def rel(path):
    return os.path.relpath(path, ROOT)


AUDIO_RAM = "0x01c00550:0x40@end"   # the audio record (audio.h): blocks, underruns, fill_max at words 2, 3, 5
BLOCK_TICKS = 34816                   # a block, 64 frames of 544 time base ticks


def load(image, out, i):
    """Preset i on all 16 voices for 500 ms: (underruns, the longest fill
    in time base ticks)."""
    d = os.path.join(out, "c%02d" % (i + 1))
    shutil.rmtree(d, ignore_errors=True)
    s = os.path.join(out, "c%02d.txt" % (i + 1))
    with open(s, "w") as f:
        f.write("\n".join(chord_script(FIRST_PROGRAM + i)) + "\n")
    subprocess.run(["sh", "tools/fwtest", "run", rel(image), "--ms", "800", "--script", rel(s), "--ram", AUDIO_RAM,
                    "--out", rel(d)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(d, "ram-01c00550-40-end.bin"), "rb") as f:
        w = struct.unpack("<16I", f.read()[:64])
    return w[3], w[5]


def render(image, out, i):
    """Runs preset i; returns the WAV's path, or raises."""
    d = os.path.join(out, "p%02d" % (i + 1))
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    s = os.path.join(out, "p%02d.txt" % (i + 1))
    with open(s, "w") as f:
        f.write("\n".join(script(FIRST_PROGRAM + i)) + "\n")
    p = subprocess.run(["sh", "tools/fwtest", "run", rel(image), "--ms", str(RUN_MS), "--script", rel(s), "--wav",
                        "--out", rel(d)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    wav = os.path.join(d, "audio.wav")
    if p.returncode or not os.path.exists(wav):
        raise RuntimeError("preset %d: fwtest: %s" % (i + 1, p.stdout.decode("utf-8", "replace")[-300:]))
    return wav


def sound_sha256(wav):
    """The SHA-256 of the WAV's first HASH_FRAMES frames (16-bit stereo)."""
    with open(wav, "rb") as f:
        b = f.read()
    i = 12
    while b[i:i + 4] != b"data":
        i += 8 + struct.unpack("<I", b[i + 4:i + 8])[0]
    data = b[i + 8:i + 8 + struct.unpack("<I", b[i + 4:i + 8])[0]]
    if len(data) < HASH_FRAMES * 4:
        raise ValueError("%s: %d frames, fewer than %d" % (rel(wav), len(data) // 4, HASH_FRAMES))
    return hashlib.sha256(data[:HASH_FRAMES * 4]).hexdigest()


def db(x):
    return 20 * math.log10(x / FULL) if x > 0 else -200.0


def measure(wav):
    """The reference note's figures."""
    rate, x, _ = aa.read_wav(wav)
    r = aa.RATE
    on, off = int(NOTE_ON_MS * r / 1000), int(NOTE_OFF_MS * r / 1000)
    start = on
    while start < off and not x[start]:
        start += 1
    note = x[start:off + int(1.0 * r)]
    held = x[start:off]
    win = int(0.02 * r)
    step = int(0.005 * r)
    loud = max(math.sqrt(sum(v * v for v in held[k:k + win]) / win) for k in range(0, max(1, len(held) - win), step))
    peak = max(abs(v) for v in note) if note else 0
    mean = sum(held) / len(held) if held else 0
    # A click: the note starting with a jump from silence (its first
    # sample over 5% of its peak), or a step in the 5 ms after the note off
    # more than twice the largest in the 5 ms before it.
    def steps(a, b):
        return max([abs(x[n] - x[n - 1]) for n in range(max(a, 1), b)] or [0])
    ms5 = int(0.005 * r)
    peak_note = max(abs(v) for v in note) if note else 1
    jump = max(20 * abs(x[start]) / max(1, peak_note), steps(off, off + ms5) / max(1, steps(off - ms5, off)))
    env = aa.envelope(held, 64)
    top = max(env) if env else 0
    attack = aa.attack_ms(held, 0) if top else 0
    after2s = max(env[-int(0.1 * r / 64):]) if env else 0
    low = 1 - aa.share_above(held[:8192], 300.0) if len(held) >= 8192 else 0
    return {"loud_db": db(loud), "peak": peak, "dc": abs(mean) / FULL, "jump": jump, "attack_ms": attack,
            "fall_db": db(after2s) - db(top), "low_share": low}


def check(i, m):
    category, purpose, p = fm_patch.PRESETS[i]
    problems = []
    if m["peak"] >= FULL:
        problems.append("clips")
    if m["dc"] > 0.005:
        problems.append("DC %.3f" % m["dc"])
    if m["jump"] > 2:
        problems.append("a click at the note's edge (%.1f, where 2 is the limit)" % m["jump"])
    if abs(m["loud_db"] - TARGET_DB) > TOLERANCE_DB:
        problems.append("loudness %.1f dBFS, the target %.1f +- %.0f" % (m["loud_db"], TARGET_DB, TOLERANCE_DB))
    if category == 1 and m["low_share"] < 0.5:
        problems.append("a bass with %.0f%% of its power below 300 Hz" % (100 * m["low_share"]))
    if category == 4 and m["attack_ms"] < 50:
        problems.append("a pad whose attack takes %.0f ms" % m["attack_ms"])
    if category == 6 and m["fall_db"] > -30:
        problems.append("a pluck that falls only %.0f dB in 2 s" % -m["fall_db"])
    return problems


def run(image, out, which=None, write_golden=False):
    """Plays and checks presets `which` (indexes; all by default):
    (problems, rows, wavs, sums), printing a line for each."""
    which = range(len(fm_patch.PRESETS)) if which is None else which
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        wavs = dict(zip(which, ex.map(lambda i: render(image, out, i), which)))
        loads = dict(zip(which, ex.map(lambda i: load(image, out, i), which)))
    golden = {}
    if os.path.exists(GOLDEN):
        with open(GOLDEN) as f:
            golden = json.load(f)
    problems, rows, sums = [], [], {}
    for i in which:
        category, purpose, p = fm_patch.PRESETS[i]
        m = measure(wavs[i])
        sums["P%02d" % (i + 1)] = sound_sha256(wavs[i])
        more = check(i, m)
        under, fill = loads[i]
        m["fill_us"] = fill / 24.0
        if under or fill >= BLOCK_TICKS:
            more.append("on 16 voices: %d underruns, the longest fill %.0f us" % (under, fill / 24.0))
        if not write_golden and golden.get("P%02d" % (i + 1)) != sums["P%02d" % (i + 1)]:
            more.append("the WAV differs from its golden SHA-256" if "P%02d" % (i + 1) in golden
                        else "no golden SHA-256")
        problems += ["P%02d %s: %s" % (i + 1, p["name"], q) for q in more]
        rows.append((i + 1, p["name"], fm_patch.CATEGORIES[category], purpose, m))
        print("P%02d %-12s %-22s %6.1f dBFS  attack %6.1f ms  2 s %6.1f dB  below 300 Hz %3.0f%%  16 voices %4.0f us"
              "  %s" % (i + 1, p["name"], fm_patch.CATEGORIES[category], m["loud_db"], m["attack_ms"], m["fall_db"],
                        100 * m["low_share"], m["fill_us"], "PASS" if not more else "FAIL"))
    return problems, rows, wavs, sums


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drop")
    ap.add_argument("--write-golden", action="store_true",
                    help="write the hashes of presets that have none (new presets)")
    ap.add_argument("--replace", action="store_true",
                    help="with --write-golden, also those that differ: a change of sound, said so in its commit"
                         " (one that moved with the timing only: tools/regolden.py)")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--calibrate", action="store_true",
                    help="rewrite tools/fm_patch.py's TRIM toward TARGET_DB from this render")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    which = [k - 1 for k in a.only] if a.only else None
    problems, rows, wavs, sums = run(a.image, out, which, a.write_golden)
    if a.calibrate:
        trims = dict(fm_patch.TRIM)
        for n, name, cat, purpose, m in rows:
            steps = round((TARGET_DB - m["loud_db"]) / (48.16 / 64))
            trims[name] = trims.get(name, 0) + steps
        trims = {k: v for k, v in sorted(trims.items()) if v}
        path = os.path.join(ROOT, "tools", "fm_patch.py")
        with open(path) as f:
            src = f.read()
        i = src.index("TRIM = {")
        j = src.index("}", i) + 1
        body = ",\n        ".join("%r: %d" % kv for kv in trims.items())
        src = src[:i] + "TRIM = {\n        " + body + ",\n}" + src[j:] if trims else src[:i] + "TRIM = {}" + src[j:]
        with open(path, "w") as f:
            f.write(src)
        print("calibrate: TRIM rewritten for %d presets" % len(trims))
    if a.write_golden:
        # The presets written now replace theirs; the others' (--only) stay.
        old = {}
        if os.path.exists(GOLDEN):
            with open(GOLDEN) as f:
                old = json.load(f)
        for k in sorted(sums):
            if k in old and old[k] != sums[k] and not a.replace:
                print("FAIL: %s: the WAV differs from its golden SHA-256; not written (tools/regolden.py, or"
                      " --replace)" % k)
                problems.append(k)
                sums[k] = old[k]
        old.update(sums)
        old["comment"] = "SHA-256 of each preset's run in tools/preset_suite.py (its WAV's first HASH_FRAMES frames)"
        with open(GOLDEN, "w") as f:
            json.dump(old, f, indent=2, sort_keys=True)
            f.write("\n")
    if a.drop:
        os.makedirs(a.drop, exist_ok=True)
        idx = ["# The preset bank (M8b, a draft): what to listen to", "",
               "Each WAV: a program change, then C4 held 2 s (the reference note) and 1 s to fade, then C4 E4 G4"
               " C5 and the C major chord held 1 s. Rendered by fwtest from the image the draft pull request"
               " builds; loudness is the reference note's loudest 20 ms.", "",
               "| # | Name | Category | What it is for | Loudness |", "|---|---|---|---|---|"]
        # With --only, the other presets' rows (and WAVs) stay as they were.
        kept = {}
        old_index = os.path.join(a.drop, "INDEX.md")
        if which is not None and os.path.exists(old_index):
            with open(old_index) as f:
                for line in f:
                    cells = line.split("|")
                    if len(cells) > 2 and cells[1].strip().isdigit():
                        kept[int(cells[1])] = line.rstrip("\n")
        for n, name, cat, purpose, m in rows:
            fn = "%02d-%s.wav" % (n, "".join(c if c.isalnum() else "-" for c in name).strip("-").lower())
            shutil.copyfile(wavs[n - 1], os.path.join(a.drop, fn))
            kept[n] = "| %d | [%s](%s) | %s | %s | %.1f dBFS |" % (n, name, fn, cat, purpose, m["loud_db"])
        idx += [kept[n] for n in sorted(kept)]
        with open(os.path.join(a.drop, "INDEX.md"), "w") as f:
            f.write("\n".join(idx) + "\n")
    for q in problems:
        print("FAIL: " + q)
    print("presets: %d of %d pass" % (len(rows) - len({q.split(":")[0] for q in problems}), len(rows)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
