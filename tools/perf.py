#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Measures the firmware's size, RAM and speed, and gates them (checks
C-PERF and C-PERF-PROBES; R-PERF-1 to R-PERF-5).

  perf.py check --build DIR --out DIR [--base-ref REF] [--records-ref REF]
                [--require-records]
      Measures DIR/app.bin (a tools/build.sh output), finds the latest
      record of a main commit (the first-parent history of --base-ref,
      default origin/main, on --records-ref, default origin/records),
      measures that record's own app.bin the same way, and applies the
      gates. Writes OUT/perf.json. Exit status 1 if a gate failed.
  perf.py probes --build DIR --out DIR
      Builds the firmware with SB_PROBE_SLOW, SB_PROBE_BIG and (since
      M4b) SB_PROBE_LOADED (firmware/src/probe.c), measures each, and
      checks that the gates fail each one for its own reason, measured
      against DIR/app.bin: the slower build its speed and its steady-state
      budget, the bigger build each size budget and its startup budget,
      the loaded build its loaded speed and loaded budget, with the
      unmodified build's measurements as those budgets. Builds it also with SB_PROBE_STACK
      and checks the stack's high-water mark shows at least the 1 KiB that
      build is known to use.
      Exit status 1 if any gate did not fail as it should.
  perf.py history --record REPORT.json --csv FILE [--measures FILE]
      Appends the record's line to perf-history.csv (records workflow),
      and since M4b its rows to perf-measures.csv, one per measure. Never
      rewrites either file; a commit (and measure) that already has a
      line is left.
  perf.py summary --record REPORT.json
      Prints the record's performance as Markdown (for the CI summary).

What is measured (docs/DESIGN-NOTES.md, M0e):
- size: code, data, bss, the raw image and the stack reserved, from
  app.size; static RAM is data + bss;
- the stack's high-water mark: the firmware fills its unused stack with
  STACK_FILL once at startup (crt0.S, sb_stack_fill), so the deepest the
  stack went is the lowest word no longer holding it, in the stack
  captured at the end of the run. An image without the fill (an older
  record's) is read by the lowest non-zero word, as fwtest starts RAM at
  zero; that method can't see words written as zero;
- speed (since M2, the owner's decision): emulated core-0 instructions,
  in two parts, from two runs that differ only in length (RUN_MS):
  - steady state, per period: the longer run's instructions less the
    shorter's, divided by the periods gained between their ends. Since M4
    the period is the audio block (64 stereo frames, 1.451 ms), counted by
    fwtest itself as the rows of `ipb.csv` (`--ipb`, which changes no
    count); an image without audio output (one from before M4) has none,
    so its measurement says so and the speed gate doesn't compare with
    it. Until M4 the period was the heartbeat (one beat per millisecond,
    the beats the beacon gained). Both runs end a quarter of a second
    past a whole second, so the window between them holds whole seconds and none of
    the firmware's work timed on whole seconds or tenths of a second
    falls near its ends (an end can come up to about 30 ms late while the
    image idles, docs/HARNESS.md "Time");
  - startup: the instructions of the shorter run beyond its periods at the
    steady-state rate, the one-off work before the firmware settles.
  The stack's high-water mark is read at the end of the longer run.
  Until M2 speed was the instructions of one one-second run divided by
  its beats, startup included;
- loaded (since M4b, R-PERF-2): the same two runs again, with the fixed
  input script LOAD_SCRIPT, which drives the firmware to its heaviest
  steady load (every voice sounding, every control moving), and its
  steady state per period worked out the same way. Its budget
  (`loaded_per_period`) is optional: a milestone without one has the
  measure recorded and reported, not gated.

The gates: each budget in config/budgets.json for the current milestone
must hold: code, static RAM, stack high-water, startup instructions and
steady-state instructions per period. Steady-state instructions per period
may also rise by at most `speed_rise_percent` against the baseline, when
the baseline's record was made under the same steady-state budget;
otherwise that comparison is not made, and the record says why. Since M3
a record under the current budget that still holds the image of the last
record before that budget was raised (the raise's own merge, or any merge
after it that changed no firmware) is never the baseline: it is skipped,
and the baseline note names it (choose_baseline). A fall of
more than that is reported as an improvement. Startup has its budget but
no such comparison. The count is deterministic, so there is no noise
allowance. The baseline is re-measured with this checkout's fwtest, runs
and options, so a change of fwtest or of the method never shows up as a
change of the firmware.

The loaded measure is gated the same way, on its own (since M4b): within
its budget, and by at most `speed_rise_percent` against a baseline found
by the same rule keyed on the loaded budget, so it may be another
record than the steady state's. Its baseline is re-measured with this
checkout's LOAD_SCRIPT too.

perf-history.csv keeps its columns: since M2 its `instructions`,
`periods` and `instructions_per_period` are the steady state's window,
and its `period` says `heartbeat-steady` (since M4 `audio-block-steady`).
Startup is in each record. Since M4b, perf-measures.csv beside it holds
one row per commit per measure (MEASURE_FIELDS), so a new measure needs
no new column; it starts with the loaded measure.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGETS = os.path.join(ROOT, "config", "budgets.json")
REPO = ROOT                  # where find_baseline looks (tests change it)

# Since M4 the period is the audio block (R-PERF-2): the blocks are
# counted by fwtest itself, as the rows of ipb.csv.
PERIOD = "audio-block-steady"
RUN_MS = (1250, 2250)        # the two runs, shorter first (see the docstring)
BEACON = 0x01C00000          # firmware/app.ld, firmware/src/sb.h
BEACON_LEN = 0x60            # the whole beacon since M2 (firmware/src/sb.h)
# Beacon words (by index) holding the screen's timings since M2, in time
# base ticks (24 a microsecond); an image that doesn't record one leaves 0.
SCREEN_TIMES = (("frame_update_us", 18), ("render_us", 19), ("heartbeat_update_us", 20))
TICKS_PER_US = 24
MARKER = 0x44304253          # "SB0D"
STACK_FILL = 0x4B415453      # "STAK", firmware/src/crt0.S
STACK_TOP = 0x01C7FC00       # firmware/app.ld asserts it
BUDGETED = ("code", "static_ram", "stack_high_water", "startup_instructions", "steady_per_period")
# Since M4b: the loaded measure (the docstring), its fixed input, and its
# budget, which a milestone may leave out (then it is not gated).
LOAD_SCRIPT = "tests/fw/scripts/perfload.txt"
LOADED = "loaded_per_period"
OPTIONAL = (LOADED,)
# What the record shows, in order (here and tools/record.py).
MEASURES = ("code", "data", "bss", "image", "static_ram", "stack_reserved", "stack_high_water",
            "stack_method", "startup_instructions", "instructions", "periods", "instructions_per_period",
            "frame_update_us", "render_us", "heartbeat_update_us")
UNIT = {"code": "bytes", "static_ram": "bytes", "stack_high_water": "bytes",
        "startup_instructions": "instructions", "steady_per_period": "instructions per period",
        LOADED: "instructions per period"}
SIZES = ("code", "data", "bss", "image", "stack")

HISTORY_FIELDS = ["commit", "record_utc", "overall", "milestone", "period",
                  "instructions", "periods", "instructions_per_period",
                  "speed_change_percent", "code", "data", "bss", "image",
                  "static_ram", "stack_reserved", "stack_high_water", "fwtest_image"]
# perf-measures.csv (since M4b): one row per commit per measure. `gated`
# says whether the change against the baseline was gated (yes) or only
# reported (no).
MEASURE_FIELDS = ["commit", "record_utc", "milestone", "measure", "value", "unit", "budget",
                  "change_percent", "gated"]


def options(stack, ms=RUN_MS[-1], script=None):
    """A perf run's fwtest options: the instrument. Kept fixed and minimal
    (no watchdog, no captures but these two), because captures change when
    a waiting core 0 is looked at, and with it the count. The loaded runs
    add their input script."""
    return ["--ms", str(ms), "--ipb",
            "--ram", "0x%08x:0x%x@end" % (BEACON, BEACON_LEN),
            "--ram", "0x%08x:0x%x@end" % (STACK_TOP - stack, stack)] + \
        (["--script", script] if script else [])


def capture_name(addr, length):
    return "ram-%08x-%x-end.bin" % (addr, length)


def read_size(text):
    size = {}
    for line in text.splitlines():
        if line.strip():
            k, v = line.split()
            size[k] = int(v)
    missing = [k for k in SIZES if k not in size]
    if missing:
        raise ValueError("app.size lacks %s" % ", ".join(missing))
    return size


def stack_high_water(data, irq_stack=0):
    """(bytes of stack ever used, the method). With the fill pattern at the
    stack's limit: from the lowest word not holding it to the top. Without
    (an image that doesn't fill): from the lowest non-zero word, which
    misses words written as zero. With irq_stack (app.size's, from M1 on),
    the area's lowest irq_stack bytes are the interrupt stack and the rest
    main's: each is measured from its own limit to its own top, and the
    two are added, since both can be at their deepest at once."""
    if irq_stack and len(data) > irq_stack:
        irq, irq_how = stack_high_water(data[:irq_stack])
        main, main_how = stack_high_water(data[irq_stack:])
        return irq + main, "%s, two stacks" % (main_how if main_how == irq_how else
                                                "%s and %s" % (main_how, irq_how))
    words = struct.unpack("<%dI" % (len(data) // 4), data[:len(data) // 4 * 4])
    if words and words[0] == STACK_FILL:
        for i, w in enumerate(words):
            if w != STACK_FILL:
                return (len(words) - i) * 4, "pattern"
        return 0, "pattern"
    for i, w in enumerate(words):
        if w:
            return (len(words) - i) * 4, "non-zero"
    return 0, "non-zero"


def run_fwtest(image_bytes, size, out, label):
    """Runs the perf runs on an image and returns its measurement: sizes,
    the stack and the last run's outcome from the longer run, speed from
    the two together (steady), the shorter run's instructions beyond its
    beats at that rate (startup), and each run's own numbers in `runs`."""
    runs = [run_once(image_bytes, size, os.path.join(out, "%dms" % ms), label, ms) for ms in RUN_MS]
    m = dict(runs[-1])
    m["runs"] = [{k: r.get(k) for k in ("ms", "outcome", "emulated_ms", "instructions", "periods", "error")
                  if r.get(k) is not None} for r in runs]
    m["options"] = [r["options"] for r in runs]
    bad = [r for r in runs if r.get("error")]
    if bad:
        m["error"] = "the %d ms run: %s" % (bad[0]["ms"], bad[0]["error"])
        m.pop("instructions_per_period", None)
        return m
    short, long_ = runs[0], runs[-1]
    di, dp = long_["instructions"] - short["instructions"], long_["periods"] - short["periods"]
    if dp <= 0 or di < 0:
        m["error"] = "the longer run gained %d audio blocks and %d instructions over the shorter" % (dp, di)
        m.pop("instructions_per_period", None)
        return m
    steady = Fraction(di, dp)
    m.update({"instructions": di, "periods": dp, "instructions_per_period": round(float(steady), 3),
              "startup_instructions": int(round(short["instructions"] - steady * short["periods"]))})
    return m


def run_loaded(image_bytes, size, out, label):
    """The loaded measure (since M4b): the two perf runs with LOAD_SCRIPT,
    and the steady state per period between them, as run_fwtest works it
    out. Returns {instructions, periods, instructions_per_period, runs,
    options, script, script_sha256}, or with `error`."""
    with open(os.path.join(ROOT, LOAD_SCRIPT), "rb") as f:
        script_sha = hashlib.sha256(f.read()).hexdigest()
    runs = [run_once(image_bytes, size, os.path.join(out, "loaded-%dms" % ms), label + "-loaded", ms,
                     LOAD_SCRIPT) for ms in RUN_MS]
    m = {"label": label + " loaded", "script": LOAD_SCRIPT, "script_sha256": script_sha,
         "runs": [{k: r.get(k) for k in ("ms", "outcome", "emulated_ms", "instructions", "periods", "error")
                   if r.get(k) is not None} for r in runs],
         "options": [r["options"] for r in runs]}
    bad = [r for r in runs if r.get("error")]
    if bad:
        m["error"] = "the loaded %d ms run: %s" % (bad[0]["ms"], bad[0]["error"])
        return m
    short, long_ = runs[0], runs[-1]
    di, dp = long_["instructions"] - short["instructions"], long_["periods"] - short["periods"]
    if dp <= 0 or di < 0:
        m["error"] = "the longer loaded run gained %d audio blocks and %d instructions over the shorter" % (dp, di)
        return m
    m.update({"instructions": di, "periods": dp, "instructions_per_period": round(di / dp, 3)})
    return m


def run_once(image_bytes, size, out, label, ms, script=None):
    """One perf run of ms emulated milliseconds (with an input script, for
    the loaded measure)."""
    # tools/fwtest takes inputs from inside the working folder only.
    work = os.path.join(ROOT, "out", "perf-run")
    os.makedirs(work, exist_ok=True)
    img = os.path.join(work, label + ".bin")
    with open(img, "wb") as f:
        f.write(image_bytes)
    opts = options(size["stack"], ms, script)
    p = subprocess.run(["sh", "tools/fwtest", "run", os.path.relpath(img, ROOT), "--out", out] + opts,
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = p.stdout.decode("utf-8", "replace")
    m = {"label": label, "ms": ms, "fwtest_exit": p.returncode, "options": opts}
    return read_run(out, size, m, log)


def read_run(out, size, m, log=""):
    """A perf run's measurement from its outputs in out (run_once): sizes,
    the beacon's marker and beats, the stack, and since M4 the audio
    blocks fwtest finished (the rows of ipb.csv) as its periods."""
    for k in SIZES:
        m[k] = size[k]
    m["stack_reserved"] = size["stack"]
    m["static_ram"] = size["data"] + size["bss"]
    try:
        with open(os.path.join(out, "result.json")) as f:
            result = json.load(f)
        with open(os.path.join(out, capture_name(BEACON, BEACON_LEN)), "rb") as f:
            beacon = f.read()
        with open(os.path.join(out, capture_name(STACK_TOP - size["stack"], size["stack"])), "rb") as f:
            stack = f.read()
    except (OSError, ValueError) as e:
        m["error"] = "fwtest gave no result (%s): %s" % (e, log.strip()[-400:])
        return m
    run = result.get("run", {})
    marker, beats = struct.unpack("<2I", beacon[:8])
    try:
        with open(os.path.join(out, "ipb.csv")) as f:
            blocks = max(0, sum(1 for line in f if line.strip()) - 1)
    except OSError:
        blocks = 0
    words = struct.unpack("<%dI" % (len(beacon) // 4), beacon[:len(beacon) // 4 * 4])
    for k, i in SCREEN_TIMES:
        if i < len(words) and words[i]:
            m[k] = round(words[i] / TICKS_PER_US, 3)
    m.update({"outcome": run.get("outcome"), "emulated_ms": run.get("emulated_ms"),
              "instructions": run.get("instructions", {}).get("core0"),
              "periods": blocks, "beats": beats, "marker": "0x%08x" % marker,
              "stack_high_water": stack_high_water(stack, size.get("irq_stack", 0))[0],
              "stack_method": stack_high_water(stack, size.get("irq_stack", 0))[1]})
    try:
        with open(os.path.join(out, "runner.txt")) as f:
            m["fwtest_image"] = f.readline().split(":", 1)[1].strip()
    except (OSError, IndexError):
        m["fwtest_image"] = ""
    if run.get("outcome") != "completed" or marker != MARKER or not beats or m["instructions"] is None:
        m["error"] = "the perf run did not complete with the marker and a heartbeat " \
                     "(outcome %s, marker 0x%08x, beats %d)" % (run.get("outcome"), marker, beats)
    elif not blocks:
        # An image from before M4 (an older record's) plays no audio, so
        # it has no period to compare with: the gate says so.
        m["error"] = "no audio blocks: this image does not run the audio output (before M4)"
    else:
        m["instructions_per_period"] = round(m["instructions"] / blocks, 3)
    return m


def measure_build(build, out, label):
    """A build's measurement, with its loaded measure in `loaded`."""
    with open(os.path.join(build, "app.bin"), "rb") as f:
        image = f.read()
    with open(os.path.join(build, "app.size")) as f:
        size = read_size(f.read())
    m = run_fwtest(image, size, out, label)
    m["loaded"] = run_loaded(image, size, out, label)
    return m


def git(*args, binary=False):
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL,
                       # never fetch a missing object (a clean folder is blob-less)
                       env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    if p.returncode != 0:
        return None
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def recorded_budget(files, key="steady_per_period"):
    """The budget `key` a record was made under (its report.json's
    perf.budgets; steady state, or since M4b the loaded measure's), or
    None."""
    try:
        budgets = (json.loads(files["report.json"].decode()).get("perf") or {}).get("budgets")
        return ((budgets or {}).get("limits") or {}).get(key)
    except (AttributeError, KeyError, ValueError):
        return None


def choose_baseline(records, steady):
    """Since M3 (the owner's rule): records, newest first, as (commit,
    steady-state budget it was made under, SHA-256 of its image). The
    pre-raise record is the newest made under another budget (or none):
    the last before the current budget was raised. A record under the
    current budget whose image is the pre-raise record's still runs the
    firmware from before the raise (the raise's own merge, or any merge
    after it that changed no firmware), so it is skipped and reported.
    Returns (index of the baseline or None, skipped commits, the pre-raise
    commit or None). Only each record's own budget and image count, so the
    order the records were written in doesn't matter."""
    pre = next((i for i, r in enumerate(records) if r[1] != steady), None)
    image = records[pre][2] if pre is not None else None
    skipped = []
    for i, (sha, budget, img) in enumerate(records):
        if steady is not None and budget == steady and image is not None and img == image:
            skipped.append(sha)
            continue
        return i, skipped, records[pre][0] if pre is not None else None
    return None, skipped, records[pre][0] if pre is not None else None


def find_baseline(base_ref, records_ref, head=None, steady=None, key="steady_per_period"):
    """(commit, {app.bin, app.size, report.json}, note) for the newest record
    of a commit on base_ref's first-parent history, other than head itself,
    that may be a speed baseline (choose_baseline, when steady, the current
    budget `key`, is given: the steady state's, or since M4b the loaded
    measure's); commit is None (and note says why) when there is none. The
    note names any record skipped."""
    if git("rev-parse", "--verify", "-q", records_ref + "^{commit}") is None:
        return None, None, "no records here (%s is not available)" % records_ref
    shas = git("rev-list", "--first-parent", "--max-count=200", base_ref)
    if shas is None:
        return None, None, "no history for %s" % base_ref
    listed = set((git("ls-tree", "--name-only", records_ref, "records/") or "").split())
    head = head if head is not None else git("rev-parse", "HEAD")
    found = []      # (commit, files), newest first, down to the pre-raise record
    for sha in shas.split():
        if sha == head or "records/" + sha not in listed:
            continue
        files = {}
        for name in ("outputs/app.bin", "outputs/app.size", "report.json"):
            files[name] = git("cat-file", "blob", "%s:records/%s/%s" % (records_ref, sha, name), binary=True)
        if files["outputs/app.bin"] is None and (git("ls-tree", "--name-only", "%s:records/%s" % (records_ref, sha))
                                                 or "").split() == ["audit"]:
            # only the similarity audit's report so far (records/<sha>/audit/): not recorded yet
            continue
        if files["outputs/app.bin"] is None or files["outputs/app.size"] is None:
            return None, None, "the record of %s has no image here (not in the record, or not " \
                               "fetched)" % sha[:12]
        found.append((sha, files))
        if steady is None or recorded_budget(files, key) != steady:
            break
    records = [(sha, recorded_budget(f, key), hashlib.sha256(f["outputs/app.bin"]).hexdigest())
               for sha, f in found]
    i, skipped, pre = choose_baseline(records, steady)
    why = ""
    if skipped:
        why = "; skipped %s, made under this budget but still holding the image of %s, the last record " \
              "before it was raised" % (", ".join(c[:12] for c in skipped), pre[:12] if pre else "?")
    if i is None:
        return None, None, "no record of a commit on %s%s" % (base_ref, why)
    sha, files = found[i]
    return sha, files, "the record of %s, the latest of %s on %s%s" % (sha[:12], base_ref, records_ref, why)


def load_budgets(path=BUDGETS):
    with open(path) as f:
        b = json.load(f)
    milestone = b["milestone"]
    limits = b["budgets"][milestone]
    for k in BUDGETED:
        if not isinstance(limits.get(k), int):
            raise ValueError("%s: budget %s for %s is missing" % (path, k, milestone))
    for k in OPTIONAL:
        if k in limits and not isinstance(limits[k], int):
            raise ValueError("%s: budget %s for %s is not a whole number" % (path, k, milestone))
    return {"milestone": milestone, "limits": {k: limits.get(k) for k in BUDGETED + OPTIONAL},
            "speed_rise_percent": b["speed_rise_percent"]}


def per_period(m):
    return Fraction(m["instructions"], m["periods"])


def budget_value(m, k):
    """The measured value a budget limits (steady state and loaded exactly,
    as a fraction), or None."""
    if k == LOADED:
        m = m.get("loaded") or {}
    if k in ("steady_per_period", LOADED):
        return per_period(m) if m.get("instructions") is not None and m.get("periods") else None
    return m.get(k)


def steady_budget(budgets, key="steady_per_period"):
    return ((budgets or {}).get("limits") or {}).get(key)


def comparable(budgets, base_budgets, key="steady_per_period"):
    """Whether the baseline's record was made under the same budget `key`
    (steady state since M2, loaded since M4b): the only case the 3%
    comparison is made. Records that still hold the image from before a
    raise are never baselines (choose_baseline, since M3). A measure with
    no budget now is never compared."""
    if not base_budgets or steady_budget(budgets, key) is None:
        return False
    return steady_budget(base_budgets, key) == steady_budget(budgets, key)


# The two speed comparisons: (gate, budget, what the detail calls it).
SPEEDS = (("speed", "steady_per_period", "steady-state"), ("loaded_speed", LOADED, "loaded"))


def compare(name, key, what, cur, base, budgets, base_budgets):
    """One speed comparison's verdict (gate below)."""
    pct = budgets["speed_rise_percent"]
    if base is None or base.get("error"):
        why = "no baseline" if base is None else "the baseline: " + base["error"]
        return {"gate": name, "result": "NOT COMPARED", "detail": why}
    c, b = per_period(cur), per_period(base)
    if not comparable(budgets, base_budgets, key):
        was, now = steady_budget(base_budgets, key), steady_budget(budgets, key)
        if now is None:
            under = "there is no %s budget for %s" % (what, budgets["milestone"])
        else:
            under = "the baseline's record was made under %s, not this %s budget of %d" % (
                "no %s budget" % what if was is None else "a %s budget of %s" % (what, was),
                budgets["milestone"], now)
        return {"gate": name, "result": "NOT COMPARED", "detail":
                "%.3f %s instructions per period, %.3f before (%+.2f%%), but %s"
                % (float(c), what, float(b), float((c - b) * 100 / b), under)}
    change = float((c - b) * 100 / b)
    text = "%.3f %s instructions per period, %.3f before: %+.2f%%" % (float(c), what, float(b), change)
    if c * 100 > b * (100 + pct):
        return {"gate": name, "result": "FAIL", "detail": text + ", a rise of more than %s%%" % pct}
    if c * 100 < b * (100 - pct):
        return {"gate": name, "result": "IMPROVED", "detail": text + ", a fall of more than %s%%" % pct}
    return {"gate": name, "result": "PASS", "detail": text + ", within %s%%" % pct}


def gate(cur, base, budgets, base_budgets=None, loaded_base=None, loaded_base_budgets=None):
    """The gates' verdicts: a list of {gate, result, detail}, result one of
    PASS, FAIL, IMPROVED (passes), NOT COMPARED (passes) and NOT GATED (a
    measure with no budget: passes). base_budgets are the budgets the
    baseline's record was made under. Since M4b the loaded measure
    (cur["loaded"]) is gated too, when it was measured: against
    loaded_base (by default the baseline's own) and the budgets its record
    was made under (by default base_budgets; give {} for none, and then
    no loaded_base means no baseline)."""
    out = []
    if cur.get("error"):
        out.append({"gate": "measurement", "result": "FAIL", "detail": cur["error"]})
    loaded = cur.get("loaded")
    if loaded is not None and loaded.get("error"):
        out.append({"gate": "loaded measurement", "result": "FAIL", "detail": loaded["error"]})
    for k in BUDGETED + OPTIONAL:
        limit, value = budgets["limits"].get(k), budget_value(cur, k)
        if value is None:
            continue
        shown = "%.3f" % float(value) if isinstance(value, Fraction) else "%d" % value
        if limit is None:
            out.append({"gate": k, "result": "NOT GATED", "detail": "%s %s; there is no %s budget for %s"
                        % (shown, UNIT[k], k, budgets["milestone"])})
        elif value > limit:
            out.append({"gate": k, "result": "FAIL", "detail": "%s %s, over the %s budget of %d"
                        % (shown, UNIT[k], budgets["milestone"], limit)})
        else:
            out.append({"gate": k, "result": "PASS", "detail": "%s of %d %s (%s budget)"
                        % (shown, limit, UNIT[k], budgets["milestone"])})
    if not cur.get("error"):
        out.append(compare("speed", "steady_per_period", "steady-state", cur, base, budgets, base_budgets))
    if loaded is not None and not loaded.get("error"):
        if loaded_base is None and loaded_base_budgets is None and base is not None:
            loaded_base = base.get("loaded") or {"error": base.get("error") or "it has no loaded measure"}
        out.append(compare("loaded_speed", LOADED, "loaded", loaded, loaded_base, budgets,
                           base_budgets if loaded_base_budgets is None else loaded_base_budgets))
    return out


def failed(verdicts):
    return any(v["result"] == "FAIL" for v in verdicts)


def speed_change(cur, base):
    if cur is None or cur.get("error") or base is None or base.get("error"):
        return None
    c, b = per_period(cur), per_period(base)
    return round(float((c - b) * 100 / b), 3)


def print_verdicts(verdicts):
    for v in verdicts:
        print("  %-20s %-12s %s" % (v["gate"], v["result"], v["detail"]))


def describe(m):
    if m.get("error"):
        return "%s: %s" % (m.get("label"), m["error"])
    if "script" in m:
        return ("%s: %d instructions for %d audio blocks (%.3f per block) between the %s ms runs with %s"
                % (m["label"], m["instructions"], m["periods"], m["instructions_per_period"],
                   " and ".join("%s" % r.get("emulated_ms") for r in m.get("runs", [])), m["script"]))
    return ("%s: code %d, data %d, bss %d, image %d bytes; static RAM %d; stack %d of %d bytes used; "
            "startup %d instructions; steady state %d instructions for %d audio blocks (%.3f per "
            "block) between the %s ms runs"
            % (m["label"], m["code"], m["data"], m["bss"], m["image"], m["static_ram"],
               m["stack_high_water"], m["stack_reserved"], m["startup_instructions"], m["instructions"],
               m["periods"], m["instructions_per_period"],
               " and ".join("%s" % r.get("emulated_ms") for r in m.get("runs", []))))


def recorded_perf(files):
    """A record's own perf section (report.json), or {}."""
    if files.get("report.json"):
        try:
            return json.loads(files["report.json"].decode()).get("perf") or {}
        except ValueError:
            pass
    return {}


def measure_record(sha, files, out, label, loaded_only=False):
    """Re-measures a record's own image with this checkout's runs: the
    whole measurement, or (loaded_only) the loaded measure alone."""
    try:
        size = read_size(files["outputs/app.size"].decode())
    except ValueError as e:
        return {"label": label, "error": str(e), "commit": sha}
    image = files["outputs/app.bin"]
    if loaded_only:
        m = run_loaded(image, size, out, label)
    else:
        m = run_fwtest(image, size, out, label)
        m["loaded"] = run_loaded(image, size, out, label)
    m["commit"] = sha
    return m


def cmd_check(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    budgets = load_budgets()
    cur = measure_build(a.build, os.path.join(out, "current"), "current")
    print(describe(cur))
    print(describe(cur["loaded"]))
    sha, files, note = find_baseline(a.base_ref, a.records_ref, steady=budgets["limits"]["steady_per_period"])
    base, base_recorded = None, {}
    if sha is None:
        print("baseline: none (%s)" % note)
        if a.require_records and not git("rev-parse", "--verify", "-q", a.records_ref + "^{commit}"):
            print("FAIL: the records branch is required here")
            cur.setdefault("error", "the records branch (%s) is not available" % a.records_ref)
    else:
        print("baseline: %s" % note)
        base = measure_record(sha, files, os.path.join(out, "baseline"), "baseline")
        print(describe(base))
        base_recorded = recorded_perf(files)
    # Since M4b the loaded measure's baseline, by the same rule keyed on
    # its own budget: re-measured only when it is another record.
    lsha, lfiles, lnote = find_baseline(a.base_ref, a.records_ref, steady=budgets["limits"][LOADED], key=LOADED)
    lbase, lrecorded = None, {}
    if lsha is not None and lsha == sha:
        lbase, lrecorded = (base or {}).get("loaded"), base_recorded
    elif lsha is not None:
        lbase = measure_record(lsha, lfiles, os.path.join(out, "loaded-baseline"), "loaded-baseline", True)
        lrecorded = recorded_perf(lfiles)
    if lbase is not None:
        lbase = dict(lbase, commit=lsha)
        print(describe(lbase))
    print("loaded baseline: %s" % (lnote if lsha else "none (%s)" % lnote))
    verdicts = gate(cur, base, budgets, base_recorded.get("budgets"), lbase, lrecorded.get("budgets") or {})
    print_verdicts(verdicts)
    result = "FAIL" if failed(verdicts) else "PASS"
    perf = {"period": PERIOD, "runs_ms": list(RUN_MS), "budgets": budgets, "current": cur, "baseline": base,
            "baseline_note": note, "baseline_recorded": base_recorded.get("current"),
            "baseline_budgets": base_recorded.get("budgets"),
            "speed_change_percent": speed_change(cur, base),
            "loaded": {"script": LOAD_SCRIPT, "script_sha256": cur["loaded"].get("script_sha256"),
                       "baseline": lbase, "baseline_note": lnote,
                       "baseline_budgets": lrecorded.get("budgets"),
                       "change_percent": speed_change(cur["loaded"], lbase),
                       "gated": comparable(budgets, lrecorded.get("budgets"), LOADED) and lbase is not None
                       and not lbase.get("error") and not cur["loaded"].get("error")},
            "gates": verdicts, "result": result}
    with open(os.path.join(out, "perf.json"), "w") as f:
        json.dump(perf, f, indent=2, sort_keys=True)
        f.write("\n")
    shutil.rmtree(os.path.join(ROOT, "out", "perf-run"), ignore_errors=True)
    print("perf: %s" % result)
    return 1 if result == "FAIL" else 0


# Each probe build, the gates it must fail, and the budgets whose limits
# are the unmodified build's measurements, so that it fails them whatever
# config/budgets.json allows (budgets only rise). Every other budget is
# the probe's own measurement, so only what it tests is under test.
SIZE_BUDGETS = {"code", "static_ram", "stack_high_water"}
PROBES = [
    ("SB_PROBE_SLOW", {"speed", "steady_per_period"}, {"steady_per_period"}),
    ("SB_PROBE_BIG", SIZE_BUDGETS | {"startup_instructions"}, SIZE_BUDGETS | {"startup_instructions"}),
    ("SB_PROBE_STACK", set(), set()),
    # Since M4b: work for each voice sounding, so it shows under load and
    # not at rest (firmware/src/synth.c).
    ("SB_PROBE_LOADED", {"loaded_speed", LOADED}, {LOADED}),
]
# The stack the STACK probe is known to use (a 1 KiB frame written with
# zeros, firmware/src/probe.c): the measured mark must be at least this.
PROBE_STACK_BYTES = 1024


def probe_budgets(ref, probe, budgets, from_ref):
    """budgets with each limit set to a measurement: the unmodified
    build's (ref) for the budgets in from_ref, the probe's own otherwise.
    Budgets are whole numbers, so a steady-state limit is the unmodified
    build's rounded down (a slower probe goes over it) or the probe's own
    rounded up (it stays within)."""
    def limit(k):
        v = budget_value(ref if k in from_ref else probe, k)
        if v is not None and k in ("steady_per_period", LOADED):
            return v.numerator // v.denominator if k in from_ref else -(-v.numerator // v.denominator)
        return v
    return {"milestone": "probe", "limits": {k: limit(k) for k in BUDGETED + OPTIONAL},
            "speed_rise_percent": budgets["speed_rise_percent"]}


def check_probe(define, verdicts, must_fail):
    """Problems with one probe's verdicts: each gate in must_fail must fail,
    and no other."""
    res = {v["gate"]: v["result"] for v in verdicts}
    probs = ["%s: %s did not fail (%s)" % (define, g, res.get(g, "not run")) for g in sorted(must_fail)
             if res.get(g) != "FAIL"]
    probs += ["%s: %s failed, but this probe should not touch it" % (define, g) for g in sorted(res)
              if g not in must_fail and res[g] == "FAIL"]
    for g in ("measurement", "loaded measurement"):
        if g in res:
            probs.append("%s: the %s failed" % (define, g))
    return probs


def check_stack_probe(m):
    """Problems with the STACK probe's measurement: its known stack use
    must show, by the fill pattern."""
    probs = []
    if not str(m.get("stack_method", "")).startswith("pattern"):
        probs.append("SB_PROBE_STACK: the stack does not hold the fill pattern")
    if m.get("stack_high_water", 0) < PROBE_STACK_BYTES:
        probs.append("SB_PROBE_STACK: stack high-water %s bytes, less than the %d it uses"
                     % (m.get("stack_high_water"), PROBE_STACK_BYTES))
    return probs


def cmd_probes(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    budgets = load_budgets()
    ref = measure_build(a.build, os.path.join(out, "reference"), "reference")
    print(describe(ref))
    print(describe(ref["loaded"]))
    problems = []
    control = gate(ref, ref, budgets, budgets)
    print("control (the build against itself):")
    print_verdicts(control)
    if failed(control) or ref.get("error"):
        problems.append("the unmodified build does not pass against itself")
    for define, must_fail, from_ref in PROBES:
        build = os.path.join(out, define.lower(), "build")
        p = subprocess.run(["sh", "tools/build.sh", "build", "--out", build, "--define", define], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            print(p.stdout.decode("utf-8", "replace"))
            problems.append("%s: the build failed" % define)
            continue
        m = measure_build(build, os.path.join(out, define.lower(), "fwtest"), define)
        print(describe(m))
        print(describe(m["loaded"]))
        if m.get("error"):
            problems.append("%s: %s" % (define, m["error"]))
            continue
        limits = probe_budgets(ref, m, budgets, from_ref)
        verdicts = gate(m, ref, limits, limits)
        print_verdicts(verdicts)
        problems += check_probe(define, verdicts, must_fail)
        if define == "SB_PROBE_STACK":
            problems += check_stack_probe(m)
        shutil.rmtree(build, ignore_errors=True)
    shutil.rmtree(os.path.join(ROOT, "out", "perf-run"), ignore_errors=True)
    for prob in problems:
        print("FAIL: " + prob)
    print("perf probes: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


def history_row(report):
    perf = report.get("perf") or {}
    cur = perf.get("current") or {}
    row = {k: "" for k in HISTORY_FIELDS}
    row.update({"commit": report["commit"], "record_utc": report.get("created_utc", ""),
                "overall": report.get("overall", "")})
    if perf:
        row.update({"milestone": perf["budgets"]["milestone"], "period": perf["period"],
                    "speed_change_percent": "" if perf.get("speed_change_percent") is None
                    else "%.3f" % perf["speed_change_percent"]})
        for k in ("instructions", "periods", "instructions_per_period", "code", "data", "bss", "image",
                  "static_ram", "stack_reserved", "stack_high_water", "fwtest_image"):
            if cur.get(k) is not None:
                row[k] = cur[k]
    return row


def measure_rows(report):
    """A record's rows for perf-measures.csv (since M4b): one per measure
    it has beyond perf-history.csv's, so far the loaded measure."""
    perf = report.get("perf") or {}
    loaded = (perf.get("current") or {}).get("loaded") or {}
    if loaded.get("instructions_per_period") is None:
        return []
    info = perf.get("loaded") or {}
    budget = ((perf.get("budgets") or {}).get("limits") or {}).get(LOADED)
    return [{"commit": report["commit"], "record_utc": report.get("created_utc", ""),
             "milestone": perf["budgets"]["milestone"], "measure": LOADED,
             "value": loaded["instructions_per_period"], "unit": "instructions per audio block",
             "budget": "" if budget is None else budget,
             "change_percent": "" if info.get("change_percent") is None else "%.3f" % info["change_percent"],
             "gated": "yes" if info.get("gated") else "no"}]


def append_rows(path, fields, rows, key):
    """Appends rows to an append-only CSV with header fields, skipping a
    row whose key (a tuple of fields) is already there (a re-run). Returns
    1 if the file's header isn't fields, else 0."""
    if os.path.exists(path) and os.path.getsize(path):
        with open(path, newline="") as f:
            old = list(csv.reader(f))
        if old[0] != fields:
            print("%s: unexpected header %s" % (path, old[0]))
            return 1
        have = {tuple(r[fields.index(k)] for k in key) for r in old[1:] if len(r) == len(fields)}
        new = False
    else:
        have, new = set(), True
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    if new:
        w.writeheader()
    added = []
    for row in rows:
        k = tuple(str(row[x]) for x in key)
        if k in have:
            print("%s already has a line for %s (a re-run): left as it is" % (path, " ".join(k)))
            continue
        w.writerow(row)
        have.add(k)
        added.append(k)
    if added:
        # Append only: earlier lines are never rewritten.
        with open(path, "a", newline="") as f:
            f.write(buf.getvalue())
        for line in buf.getvalue().strip().splitlines()[-len(added):]:
            print("appended to %s: %s" % (path, line))
    return 0


def cmd_history(a):
    with open(a.record) as f:
        report = json.load(f)
    status = append_rows(a.csv, HISTORY_FIELDS, [history_row(report)], ("commit",))
    if getattr(a, "measures", None):
        status |= append_rows(a.measures, MEASURE_FIELDS, measure_rows(report), ("commit", "measure"))
    return status


def summary(perf):
    if not perf:
        return "### Performance\n\nNo performance data in this record.\n"
    cur = perf["current"]
    L = ["### Performance: %s" % perf["result"], ""]
    if not cur.get("error"):
        L += ["| Measure | Value |", "|---|---|"]
        L += ["| %s | %s |" % (k, cur[k]) for k in
              MEASURES if k in cur]
        L += ["| run of %s ms | %s instructions, %s periods, ended at %s ms |"
              % (r.get("ms"), r.get("instructions"), r.get("periods"), r.get("emulated_ms"))
              for r in cur.get("runs", [])]
        L.append("")
    loaded = cur.get("loaded") or {}
    if loaded and not loaded.get("error"):
        L += ["Loaded (%s): %s instructions for %s audio blocks, %s a block." % (
            loaded.get("script"), loaded.get("instructions"), loaded.get("periods"),
            loaded.get("instructions_per_period")), ""]
    L.append("Baseline: %s." % perf["baseline_note"])
    if perf.get("loaded"):
        L.append("Loaded baseline: %s." % perf["loaded"].get("baseline_note"))
    L += ["", "| Gate | Result | Detail |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % (v["gate"], v["result"], v["detail"]) for v in perf["gates"]]
    if any(v["result"] == "IMPROVED" for v in perf["gates"]):
        L += ["", "**An improvement of more than %s%%: say so in the pull request.**"
              % perf["budgets"]["speed_rise_percent"]]
    return "\n".join(L) + "\n"


def cmd_summary(a):
    with open(a.record) as f:
        print(summary(json.load(f).get("perf")), end="")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check")
    c.add_argument("--build", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--base-ref", default="origin/main")
    c.add_argument("--records-ref", default="origin/records")
    c.add_argument("--require-records", action="store_true")
    p = sub.add_parser("probes")
    p.add_argument("--build", required=True)
    p.add_argument("--out", required=True)
    h = sub.add_parser("history")
    h.add_argument("--record", required=True)
    h.add_argument("--csv", required=True)
    h.add_argument("--measures", help="perf-measures.csv (since M4b)")
    s = sub.add_parser("summary")
    s.add_argument("--record", required=True)
    a = ap.parse_args()
    cmds = {"check": cmd_check, "probes": cmd_probes, "history": cmd_history, "summary": cmd_summary}
    if a.cmd not in cmds:
        ap.print_help()
        return 2
    return cmds[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
