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
      Builds the firmware with SB_PROBE_SLOW and with SB_PROBE_BIG
      (firmware/src/probe.c), measures each, and checks that the gates
      fail each one for its own reason, measured against DIR/app.bin: the
      slower build its speed, the bigger build each budget, with the
      unmodified build's sizes as the budgets. Builds it also with
      SB_PROBE_STACK and checks the stack's high-water mark shows at least
      the 1 KiB that build is known to use.
      Exit status 1 if any gate did not fail as it should.
  perf.py history --record REPORT.json --csv FILE
      Appends the record's line to perf-history.csv (records workflow).
      Never rewrites the file; a commit that already has a line is left.
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
- speed: emulated core-0 instructions per period. Until audio (M4) the
  period is the heartbeat (one beat per millisecond): the instructions of
  a one-second run divided by the beats the beacon shows at its end.

The gates: each budget in config/budgets.json for the current milestone
(code, static RAM, stack high-water) must hold, and instructions per
period may rise by at most `speed_rise_percent` against the baseline. A
fall of more than that is reported as an improvement. The count is
deterministic, so there is no noise allowance. The baseline is re-measured
with this checkout's fwtest and options, so a change of fwtest or of the
options never shows up as a change of the firmware.
"""
import argparse
import csv
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

PERIOD = "heartbeat"
RUN_MS = 1000
BEACON = 0x01C00000          # firmware/app.ld, firmware/src/sb.h
BEACON_LEN = 16
MARKER = 0x44304253          # "SB0D"
STACK_FILL = 0x4B415453      # "STAK", firmware/src/crt0.S
STACK_TOP = 0x01C7FC00       # firmware/app.ld asserts it
BUDGETED = ("code", "static_ram", "stack_high_water")
SIZES = ("code", "data", "bss", "image", "stack")

HISTORY_FIELDS = ["commit", "record_utc", "overall", "milestone", "period",
                  "instructions", "periods", "instructions_per_period",
                  "speed_change_percent", "code", "data", "bss", "image",
                  "static_ram", "stack_reserved", "stack_high_water", "fwtest_image"]


def options(stack):
    """The perf run's fwtest options: the instrument. Kept fixed and
    minimal (no watchdog, no captures but these two), because captures
    change when a waiting core 0 is looked at, and with it the count."""
    return ["--ms", str(RUN_MS),
            "--ram", "0x%08x:0x%x@end" % (BEACON, BEACON_LEN),
            "--ram", "0x%08x:0x%x@end" % (STACK_TOP - stack, stack)]


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


def stack_high_water(data):
    """(bytes of stack ever used, the method). With the fill pattern at the
    stack's limit: from the lowest word not holding it to the top. Without
    (an image that doesn't fill): from the lowest non-zero word, which
    misses words written as zero."""
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
    """Runs the perf case on an image and returns its measurement."""
    # tools/fwtest takes inputs from inside the working folder only.
    work = os.path.join(ROOT, "out", "perf-run")
    os.makedirs(work, exist_ok=True)
    img = os.path.join(work, label + ".bin")
    with open(img, "wb") as f:
        f.write(image_bytes)
    opts = options(size["stack"])
    p = subprocess.run(["sh", "tools/fwtest", "run", os.path.relpath(img, ROOT), "--out", out] + opts,
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = p.stdout.decode("utf-8", "replace")
    m = {"label": label, "fwtest_exit": p.returncode, "options": opts}
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
    m.update({"outcome": run.get("outcome"), "emulated_ms": run.get("emulated_ms"),
              "instructions": run.get("instructions", {}).get("core0"),
              "periods": beats, "marker": "0x%08x" % marker,
              "stack_high_water": stack_high_water(stack)[0],
              "stack_method": stack_high_water(stack)[1]})
    try:
        with open(os.path.join(out, "runner.txt")) as f:
            m["fwtest_image"] = f.readline().split(":", 1)[1].strip()
    except (OSError, IndexError):
        m["fwtest_image"] = ""
    if run.get("outcome") != "completed" or marker != MARKER or not beats or m["instructions"] is None:
        m["error"] = "the perf run did not complete with the marker and a heartbeat " \
                     "(outcome %s, marker 0x%08x, beats %d)" % (run.get("outcome"), marker, beats)
    else:
        m["instructions_per_period"] = round(m["instructions"] / beats, 3)
    return m


def measure_build(build, out, label):
    with open(os.path.join(build, "app.bin"), "rb") as f:
        image = f.read()
    with open(os.path.join(build, "app.size")) as f:
        size = read_size(f.read())
    return run_fwtest(image, size, out, label)


def git(*args, binary=False):
    p = subprocess.run(["git", "-C", REPO] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL,
                       # never fetch a missing object (a clean folder is blob-less)
                       env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    if p.returncode != 0:
        return None
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def find_baseline(base_ref, records_ref, head=None):
    """(commit, {app.bin, app.size, report.json}, note) for the newest record
    of a commit on base_ref's first-parent history, other than head itself;
    commit is None (and note says why) when there is none."""
    if git("rev-parse", "--verify", "-q", records_ref + "^{commit}") is None:
        return None, None, "no records here (%s is not available)" % records_ref
    shas = git("rev-list", "--first-parent", "--max-count=200", base_ref)
    if shas is None:
        return None, None, "no history for %s" % base_ref
    listed = set((git("ls-tree", "--name-only", records_ref, "records/") or "").split())
    head = head if head is not None else git("rev-parse", "HEAD")
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
        return sha, files, "the record of %s, the latest of %s on %s" % (sha[:12], base_ref, records_ref)
    return None, None, "no record of a commit on %s" % base_ref


def load_budgets(path=BUDGETS):
    with open(path) as f:
        b = json.load(f)
    milestone = b["milestone"]
    limits = b["budgets"][milestone]
    for k in BUDGETED:
        if not isinstance(limits.get(k), int):
            raise ValueError("%s: budget %s for %s is missing" % (path, k, milestone))
    return {"milestone": milestone, "limits": {k: limits[k] for k in BUDGETED},
            "speed_rise_percent": b["speed_rise_percent"]}


def per_period(m):
    return Fraction(m["instructions"], m["periods"])


def gate(cur, base, budgets):
    """The gates' verdicts: a list of {gate, result, detail}, result one of
    PASS, FAIL, IMPROVED (passes) and NOT COMPARED (passes)."""
    out = []
    if cur.get("error"):
        out.append({"gate": "measurement", "result": "FAIL", "detail": cur["error"]})
    for k in BUDGETED:
        limit, value = budgets["limits"][k], cur.get(k)
        if value is None:
            continue
        if value > limit:
            out.append({"gate": k, "result": "FAIL",
                        "detail": "%d bytes, over the %s budget of %d" % (value, budgets["milestone"], limit)})
        else:
            out.append({"gate": k, "result": "PASS",
                        "detail": "%d of %d bytes (%s budget)" % (value, limit, budgets["milestone"])})
    pct = budgets["speed_rise_percent"]
    if cur.get("error"):
        pass
    elif base is None or base.get("error"):
        why = "no baseline" if base is None else "the baseline: " + base["error"]
        out.append({"gate": "speed", "result": "NOT COMPARED", "detail": why})
    else:
        c, b = per_period(cur), per_period(base)
        change = float((c - b) * 100 / b)
        text = "%.3f instructions per %s period, %.3f before: %+.2f%%" % (float(c), PERIOD, float(b), change)
        if c * 100 > b * (100 + pct):
            out.append({"gate": "speed", "result": "FAIL", "detail": text + ", a rise of more than %s%%" % pct})
        elif c * 100 < b * (100 - pct):
            out.append({"gate": "speed", "result": "IMPROVED", "detail": text + ", a fall of more than %s%%" % pct})
        else:
            out.append({"gate": "speed", "result": "PASS", "detail": text + ", within %s%%" % pct})
    return out


def failed(verdicts):
    return any(v["result"] == "FAIL" for v in verdicts)


def speed_change(cur, base):
    if cur.get("error") or base is None or base.get("error"):
        return None
    c, b = per_period(cur), per_period(base)
    return round(float((c - b) * 100 / b), 3)


def print_verdicts(verdicts):
    for v in verdicts:
        print("  %-16s %-12s %s" % (v["gate"], v["result"], v["detail"]))


def describe(m):
    if m.get("error"):
        return "%s: %s" % (m["label"], m["error"])
    return ("%s: code %d, data %d, bss %d, image %d bytes; static RAM %d; stack %d of %d bytes used; "
            "%d instructions for %d %s periods (%.3f per period) in %s ms"
            % (m["label"], m["code"], m["data"], m["bss"], m["image"], m["static_ram"],
               m["stack_high_water"], m["stack_reserved"], m["instructions"], m["periods"], PERIOD,
               m["instructions_per_period"], m["emulated_ms"]))


def cmd_check(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    budgets = load_budgets()
    cur = measure_build(a.build, os.path.join(out, "current"), "current")
    print(describe(cur))
    sha, files, note = find_baseline(a.base_ref, a.records_ref)
    base, base_recorded = None, None
    if sha is None:
        print("baseline: none (%s)" % note)
        if a.require_records and not git("rev-parse", "--verify", "-q", a.records_ref + "^{commit}"):
            print("FAIL: the records branch is required here")
            cur.setdefault("error", "the records branch (%s) is not available" % a.records_ref)
    else:
        print("baseline: %s" % note)
        try:
            size = read_size(files["outputs/app.size"].decode())
            base = run_fwtest(files["outputs/app.bin"], size, os.path.join(out, "baseline"), "baseline")
        except ValueError as e:
            base = {"label": "baseline", "error": str(e)}
        base["commit"] = sha
        print(describe(base))
        if files.get("report.json"):
            try:
                base_recorded = json.loads(files["report.json"].decode()).get("perf")
            except ValueError:
                pass
    verdicts = gate(cur, base, budgets)
    print_verdicts(verdicts)
    result = "FAIL" if failed(verdicts) else "PASS"
    perf = {"period": PERIOD, "budgets": budgets, "current": cur, "baseline": base,
            "baseline_note": note, "baseline_recorded": (base_recorded or {}).get("current"),
            "speed_change_percent": speed_change(cur, base), "gates": verdicts, "result": result}
    with open(os.path.join(out, "perf.json"), "w") as f:
        json.dump(perf, f, indent=2, sort_keys=True)
        f.write("\n")
    shutil.rmtree(os.path.join(ROOT, "out", "perf-run"), ignore_errors=True)
    print("perf: %s" % result)
    return 1 if result == "FAIL" else 0


# Each probe build, the gates it must fail, and whose sizes are its
# budgets: the unmodified build's for the bigger probe, so it fails each
# budget whatever config/budgets.json allows (budgets only rise); its own
# for the others, so only what they test is under test.
PROBES = [
    ("SB_PROBE_SLOW", {"speed"}, "probe"),
    ("SB_PROBE_BIG", set(BUDGETED), "reference"),
    ("SB_PROBE_STACK", set(), "probe"),
]
# The stack the STACK probe is known to use (a 1 KiB frame written with
# zeros, firmware/src/probe.c): the measured mark must be at least this.
PROBE_STACK_BYTES = 1024


def probe_budgets(sizes, budgets, whose):
    """budgets with each limit set to the sizes measured in `sizes`."""
    return {"milestone": whose, "limits": {k: sizes[k] for k in BUDGETED},
            "speed_rise_percent": budgets["speed_rise_percent"]}


def check_probe(define, verdicts, must_fail):
    """Problems with one probe's verdicts: each gate in must_fail must fail,
    and no other."""
    res = {v["gate"]: v["result"] for v in verdicts}
    probs = ["%s: %s did not fail (%s)" % (define, g, res.get(g, "not run")) for g in sorted(must_fail)
             if res.get(g) != "FAIL"]
    probs += ["%s: %s failed, but this probe should not touch it" % (define, g) for g in sorted(res)
              if g not in must_fail and res[g] == "FAIL"]
    if "measurement" in res:
        probs.append("%s: the measurement failed" % define)
    return probs


def check_stack_probe(m):
    """Problems with the STACK probe's measurement: its known stack use
    must show, by the fill pattern."""
    probs = []
    if m.get("stack_method") != "pattern":
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
    problems = []
    control = gate(ref, ref, budgets)
    print("control (the build against itself):")
    print_verdicts(control)
    if failed(control) or ref.get("error"):
        problems.append("the unmodified build does not pass against itself")
    for define, must_fail, whose in PROBES:
        build = os.path.join(out, define.lower(), "build")
        p = subprocess.run(["sh", "tools/build.sh", "build", "--out", build, "--define", define], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if p.returncode != 0:
            print(p.stdout.decode("utf-8", "replace"))
            problems.append("%s: the build failed" % define)
            continue
        m = measure_build(build, os.path.join(out, define.lower(), "fwtest"), define)
        print(describe(m))
        if m.get("error"):
            problems.append("%s: %s" % (define, m["error"]))
            continue
        limits = probe_budgets(ref if whose == "reference" else m, budgets,
                               "unmodified build's" if whose == "reference" else "probe's own")
        verdicts = gate(m, ref, limits)
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


def cmd_history(a):
    with open(a.record) as f:
        report = json.load(f)
    row = history_row(report)
    if os.path.exists(a.csv) and os.path.getsize(a.csv):
        with open(a.csv, newline="") as f:
            rows = list(csv.reader(f))
        if rows[0] != HISTORY_FIELDS:
            print("%s: unexpected header %s" % (a.csv, rows[0]))
            return 1
        if any(r and r[0] == row["commit"] for r in rows[1:]):
            print("%s already has a line for %s (a re-run): left as it is" % (a.csv, row["commit"]))
            return 0
        new = False
    else:
        new = True
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HISTORY_FIELDS, lineterminator="\n")
    if new:
        w.writeheader()
    w.writerow(row)
    # Append only: earlier lines are never rewritten.
    with open(a.csv, "a", newline="") as f:
        f.write(buf.getvalue())
    print("appended to %s: %s" % (a.csv, buf.getvalue().strip().splitlines()[-1]))
    return 0


def summary(perf):
    if not perf:
        return "### Performance\n\nNo performance data in this record.\n"
    cur = perf["current"]
    L = ["### Performance: %s" % perf["result"], ""]
    if not cur.get("error"):
        L += ["| Measure | Value |", "|---|---|"]
        L += ["| %s | %s |" % (k, cur[k]) for k in
              ("code", "data", "bss", "image", "static_ram", "stack_reserved", "stack_high_water",
               "stack_method", "instructions", "periods", "instructions_per_period") if k in cur]
        L.append("")
    L.append("Baseline: %s." % perf["baseline_note"])
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
