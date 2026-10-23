#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The Plaits load test's measurements (M4b; docs/DESIGN-NOTES.md, check
C-PLAITS-BENCH; R-PLAITS-1 to R-PLAITS-4).

  plaits-bench.py run --out DIR [--perf PERF.json]
      Builds the Plaits demo's images (tools/build.sh build --demo plaits):
      the demo itself, twice (the two builds must be identical), and with
      the hardware float instructions (PLAITS_HWFLOAT), the bench
      (PLAITS_BENCH: the soft-float test, then the engines) and the bench
      with the hardware float instructions (PLAITS_BENCH and
      PLAITS_HWFLOAT); runs each in fwtest; and writes DIR/plaits.json,
      DIR/plaits.md, the bench consoles and a log. Exit status 1 if a
      check failed.
  plaits-bench.py softfloat CONSOLE.txt
      Checks a soft-float test run's console against the exact reference.

What is checked:
- the soft-float routines, bit for bit, against results worked out
  exactly (fractions, then rounded to nearest even as binary32), on the
  same operands as the test image (firmware/demos/plaits/sftest.c);
- the bench (firmware/demos/plaits/bench.c): every engine measured, no
  NaN, infinity or bad conversion in soft-float, the same sound with
  hardware float as with soft-float (checksums), core 1 started;
- the demo playing a note with no underrun and sound that is not
  silence: the soft-float build on the chiptune engine (the only one that
  fits in a block with soft-float), the hardware-float build on engine 0.
The numbers are fwtest's, where an instruction is a cycle: on the chip,
code from flash through the cache will take more.
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys
import wave
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCK_CYCLES = 348160        # core 0's cycles a block: 64 frames at 24 MHz / 544, at 240 MHz
ENGINES = [
    "virtual analog VCF", "phase distortion", "six-op FM (bank 1)", "six-op FM (bank 2)",
    "six-op FM (bank 3)", "wave terrain", "string machine", "chiptune",
    "virtual analog", "waveshaping", "FM", "grain", "additive", "wavetable", "chords",
    "speech", "swarm", "noise", "particle", "string", "modal", "bass drum", "snare drum",
    "hi-hat",
]

# --- soft-float reference --------------------------------------------

SPECIAL = [0x00000000, 0x80000000, 0x7F800000, 0xFF800000, 0x7FC00000, 0x00000001,
           0x80000001, 0x007FFFFF, 0x00800000, 0x7F7FFFFF, 0xFF7FFFFF, 0x3F800000,
           0xBF800000, 0x3F800001, 0x4B000000, 0x4EFFFFFF, 0x4F000000, 0xCF000000,
           0x4F800000, 0x00400000, 0x33800000, 0x34000000]
CASES = 20000
QNAN = 0x7FC00000
M32 = 0xFFFFFFFF


def operands():
    """The test image's operand pairs, in order (sftest.c, operands)."""
    seed = 0x5EEDF10A

    def nxt():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & M32
        return seed
    n = len(SPECIAL)
    for i in range(CASES):
        if i < n * n:
            yield SPECIAL[i // n], SPECIAL[i % n]
            continue
        a = nxt()
        k = i & 3
        if k == 0:
            b = nxt()
        elif k == 1:
            b = (a & 0xFF800000) | (nxt() & 0x007FFFFF)
            b ^= nxt() & 0x80000000
        elif k == 2:
            a &= 0x80FFFFFF
            b = nxt() & 0x80FFFFFF
        else:
            b = (a + (nxt() & 3) - 1) & M32
        yield a, b


def kind(u):
    """('nan'|'inf'|'num', sign, Fraction value or None)."""
    s, e, m = u >> 31, (u >> 23) & 0xFF, u & 0x7FFFFF
    if e == 255:
        return ("nan" if m else "inf"), s, None
    v = Fraction(m if e == 0 else m | 0x800000) * Fraction(2) ** ((1 if e == 0 else e) - 150)
    return "num", s, -v if s else v


def round32(v, sign_if_zero=0):
    """The binary32 nearest v (a Fraction), ties to even, with subnormals
    and overflow to infinity. A zero takes sign_if_zero."""
    if v == 0:
        return sign_if_zero << 31
    s = 1 if v < 0 else 0
    a = -v if s else v
    e = math.floor(math.log2(a.numerator) - math.log2(a.denominator))
    while Fraction(2) ** e > a:
        e -= 1
    while Fraction(2) ** (e + 1) <= a:
        e += 1
    e = max(e, -126)                       # subnormals share exponent -126
    q = a / Fraction(2) ** (e - 23)        # significand in units of the last place
    n, r = divmod(q.numerator, q.denominator)
    if 2 * r > q.denominator or (2 * r == q.denominator and n & 1):
        n += 1
    if n == 1 << 24:
        n >>= 1
        e += 1
    if e > 127:
        return (s << 31) | 0x7F800000
    if n < 1 << 23:                        # subnormal (or rounded to zero)
        return (s << 31) | n
    return (s << 31) | ((e + 127) << 23) | (n & 0x7FFFFF)


def ref_add(a, b, sub=False):
    if sub:
        b ^= 0x80000000
    ka, sa, va = kind(a)
    kb, sb, vb = kind(b)
    if "nan" in (ka, kb):
        return QNAN
    if ka == "inf" and kb == "inf":
        return QNAN if sa != sb else a
    if ka == "inf":
        return a
    if kb == "inf":
        return b
    v = va + vb
    if v == 0:
        return (sa & sb) << 31 if va == 0 and vb == 0 else 0
    return round32(v)


def ref_mul(a, b):
    ka, sa, va = kind(a)
    kb, sb, vb = kind(b)
    s = sa ^ sb
    if "nan" in (ka, kb):
        return QNAN
    if ka == "inf" or kb == "inf":
        if (ka == "num" and va == 0) or (kb == "num" and vb == 0):
            return QNAN
        return (s << 31) | 0x7F800000
    return round32(va * vb, s)


def ref_div(a, b):
    ka, sa, va = kind(a)
    kb, sb, vb = kind(b)
    s = sa ^ sb
    if "nan" in (ka, kb):
        return QNAN
    if ka == "inf":
        return QNAN if kb == "inf" else (s << 31) | 0x7F800000
    if kb == "inf":
        return s << 31
    if vb == 0:
        return QNAN if va == 0 else (s << 31) | 0x7F800000
    return round32(va / vb, s)


def ref_sqrt(a):
    k, s, v = kind(a)
    if k == "nan":
        return QNAN
    if k == "inf":
        return QNAN if s else a
    if v == 0:
        return a
    if s:
        return QNAN
    # sqrt to 60 bits beyond the binary point of the result, by integers,
    # with a sticky bit: enough to round correctly.
    num, den = v.numerator, v.denominator
    shift = 2 * 200
    r = math.isqrt(num * (1 << shift) // den)
    exact = r * r * den == num * (1 << shift)
    root = Fraction(r, 1 << 200)
    if not exact:
        root += Fraction(1, 1 << 202)       # strictly between: a sticky bit
    return round32(root)


def ref_i2f(x, signed):
    if signed and x & 0x80000000:
        x -= 1 << 32
    return round32(Fraction(x))


def ref_f2i(a, signed):
    k, s, v = kind(a)
    if k == "nan":
        return 0
    if signed:
        if k == "inf":
            return 0x80000000 if s else 0x7FFFFFFF
        t = int(v)                           # toward zero
        if t > 0x7FFFFFFF:
            return 0x7FFFFFFF
        if t < -0x80000000:
            return 0x80000000
        return t & M32
    if k == "inf":
        return 0 if s else M32
    t = int(v)
    if t < 0:
        return 0
    return min(t, M32)


def ref_cmp(a, b):
    ka, _, va = kind(a)
    kb, _, vb = kind(b)
    if "nan" in (ka, kb):
        return None
    def val(k, u, v):
        if k == "inf":
            return Fraction(-1 if u >> 31 else 1) * Fraction(10) ** 50
        return v
    return val(ka, a, va), val(kb, b, vb)


def softfloat_hashes():
    h = [2166136261] * 15

    def mix(op, v):
        h[op] = ((h[op] ^ (v & M32)) * 16777619) & M32
    for a, b in operands():
        mix(0, ref_add(a, b))
        mix(1, ref_add(a, b, sub=True))
        mix(2, ref_mul(a, b))
        mix(3, ref_div(a, b))
        mix(4, ref_sqrt(a))
        mix(5, ref_i2f(a, True))
        mix(6, ref_i2f(a, False))
        mix(7, ref_f2i(a, True))
        mix(8, ref_f2i(a, False))
        c = ref_cmp(a, b)
        for op, f in ((9, lambda x, y: x < y), (10, lambda x, y: x <= y), (11, lambda x, y: x > y),
                      (12, lambda x, y: x >= y), (13, lambda x, y: x == y)):
            mix(op, 0 if c is None else int(f(*c)))
        mix(14, 1 if c is None else int(c[0] != c[1]))
    return h


SFT_OPS = ["add", "subtract", "multiply", "divide", "square root", "int to float",
           "unsigned to float", "float to int", "float to unsigned", "<", "<=", ">", ">=", "==", "!="]


def check_softfloat(console):
    """[(operation, ok)] from a soft-float test run's console text."""
    got = {}
    for line in console.splitlines():
        p = line.split()
        if len(p) == 3 and p[0] == "SFT":
            got[ord(p[1]) - ord("a")] = int(p[2], 16)
    want = softfloat_hashes()
    return [(SFT_OPS[i], got.get(i) == want[i]) for i in range(len(SFT_OPS))]


def cmd_softfloat(a):
    with open(a.console) as f:
        res = check_softfloat(f.read())
    for name, ok in res:
        print("  %-18s %s" % (name, "PASS" if ok else "FAIL"))
    bad = [n for n, ok in res if not ok]
    print("soft-float: %s" % ("FAIL (%s)" % ", ".join(bad) if bad else "PASS, %d cases each" % CASES))
    return 1 if bad else 0


# --- the run ---------------------------------------------------------

# The live checks: a key held, with no underrun counted between the
# capture at 300 ms and the end. The demo starts on the chiptune engine,
# the one engine soft-float can play in a block; the hardware-float build
# is turned (ALGORITHM is fwtest's encoder 1, HW-39) to engine 0, one of
# the heavier ones.
LIVE = (("soft", (), 7, ""), ("hw", ("PLAITS_HWFLOAT",), 0, "50       enc 1 -7\n"))
LIVE_SCRIPT = """# plaits-bench.py's live check (written by it)
%s300      key 22 down
800      key 22 up
"""
AUDIO_RECORD = 0x01C00550    # firmware/app.ld, audio.h
AUDIO_LEN = 0x40


def sh(argv, log):
    p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write("$ %s\n%s\nexit status %d\n" % (" ".join(argv), p.stdout.decode("utf-8", "replace")[-4000:],
                                                p.returncode))
    return p.returncode


def build(out, log, *defines):
    argv = ["sh", "tools/build.sh", "build", "--out", out, "--demo", "plaits"]
    for d in defines:
        argv += ["--define", d]
    return sh(argv, log) == 0


def fwtest(image, out, log, *opts):
    rel = os.path.relpath(image, ROOT)
    sh(["sh", "tools/fwtest", "run", rel, "--out", out] + list(opts), log)
    try:
        with open(os.path.join(out, "result.json")) as f:
            return json.load(f)["run"]
    except (OSError, ValueError, KeyError):
        return {}


def parse_bench(console):
    """The bench's console lines (bench.c) as a dict."""
    b = {"engines": {}, "dual": [], "end": False}
    for line in console.splitlines():
        p = line.split()
        if not p:
            continue
        w = [int(x, 16) for x in p[1:]] if p[0] in ("PLAITS-BENCH", "E", "FLAGS", "CORE1", "D") else []
        if p[0] == "PLAITS-BENCH":
            b["format"], b["count"], b["points"], b["blocks"], b["frames"], b["render"], b["hwfloat"] = w[:7]
        elif p[0] == "E":
            b["engines"][w[0]] = {"set_up": w[1], "max": w[2], "mean": w[3], "checksum": "%08x" % w[4],
                                  "clipped": w[5], "peak": w[6]}
        elif p[0] == "FLAGS":
            b["flags"] = {"invalid": w[0], "overflow": w[1], "convert": w[2]}
        elif p[0] == "CORE1":
            b["core1"] = bool(w[0])
        elif p[0] == "D":
            b["dual"].append({"engine": w[0], "apart": w[1], "both": w[2]})
        elif p[0] == "END":
            b["end"] = True
    return b


def platform_costs(perf_path):
    """Core 0's instructions a block the firmware itself takes, at rest
    and under its heaviest input (tools/perf.py's perf.json), or the M4
    figures (docs/DESIGN-NOTES.md) when there is no perf.json."""
    rest, loaded, where = 1812.939, None, "docs/DESIGN-NOTES.md, M4"
    try:
        with open(perf_path) as f:
            cur = json.load(f)["current"]
        rest = cur["instructions_per_period"]
        loaded = (cur.get("loaded") or {}).get("instructions_per_period")
        where = "this record's perf.json"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return rest, loaded, where


def cmd_run(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    work = os.path.join(ROOT, "out", "plaits-work")
    subprocess.run(["rm", "-rf", work])
    os.makedirs(work)
    checks, problems = [], []
    log = open(os.path.join(out, "plaits.log"), "w", encoding="utf-8")

    def check(name, ok, detail=""):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            problems.append(name)
        print("  %-34s %s  %s" % (name, "PASS" if ok else "FAIL", detail), flush=True)

    # 1. The demo, twice: the builds must be identical.
    ok_a = build(os.path.join(work, "demo-a"), log)
    ok_b = build(os.path.join(work, "demo-b"), log)
    sums = []
    for d in ("demo-a", "demo-b"):
        try:
            with open(os.path.join(work, d, "SHA256SUMS")) as f:
                sums.append(f.read())
        except OSError:
            sums.append(None)
    check("demo builds", ok_a and ok_b)
    check("demo build is deterministic", ok_a and ok_b and sums[0] == sums[1] and sums[0] is not None)
    size = {}
    if ok_a:
        with open(os.path.join(work, "demo-a", "app.size")) as f:
            size = {k: int(v) for k, v in (l.split() for l in f if l.strip())}
        with open(os.path.join(work, "demo-a", "SHA256SUMS")) as f:
            image_sha = next((l.split()[0] for l in f if l.split()[1:] == ["app.bin"]), "")
    else:
        image_sha = ""

    # 2. The live demo: no underrun while it plays, and not silence.
    live = {}
    for name, defines, engine, turn in LIVE:
        d = os.path.join(work, "demo-a") if not defines else os.path.join(work, "demo-" + name)
        if defines and not build(d, log, *defines):
            check("live demo builds (%s)" % name, False)
            continue
        if not os.path.exists(os.path.join(d, "app.bin")):
            continue
        script = os.path.join(work, "live-%s.txt" % name)
        with open(script, "w") as f:
            f.write(LIVE_SCRIPT % turn)
        o = os.path.join(work, "live-" + name)
        run = fwtest(os.path.join(d, "app.bin"), o, log,
                     "--ms", "1000", "--wav", "--script", os.path.relpath(script, ROOT),
                     "--ram", "0x%08x:0x%x@300" % (AUDIO_RECORD, AUDIO_LEN),
                     "--ram", "0x%08x:0x%x@end" % (AUDIO_RECORD, AUDIO_LEN))
        try:
            rec = []
            for when in ("300ms", "end"):
                with open(os.path.join(o, "ram-%08x-%x-%s.bin" % (AUDIO_RECORD, AUDIO_LEN, when)), "rb") as f:
                    rec.append(struct.unpack("<16I", f.read()))
            with wave.open(os.path.join(o, "audio.wav")) as w:
                frames = w.readframes(w.getnframes())
            samples = struct.unpack("<%dh" % (len(frames) // 2), frames)
            start = 2 * int(0.31 * 24e6 / 544)
            peak = max(abs(x) for x in samples[start:]) if samples[start:] else 0
            live[name] = {"engine": engine, "outcome": run.get("outcome"),
                          "underruns_while_playing": rec[1][3] - rec[0][3], "engine_set": rec[1][7],
                          "peak": peak, "blocks": rec[1][2], "fill_max_ticks": rec[1][5]}
        except (OSError, struct.error, wave.Error, IndexError) as e:
            live[name] = {"error": str(e)}
        lv = live[name]
        check("live demo plays without underrun (%s)" % name,
              lv.get("outcome") == "completed" and lv.get("engine_set") == engine
              and lv.get("underruns_while_playing") == 0 and lv.get("peak", 0) > 1000,
              "engine %s, %s underruns while playing, peak %s" % (lv.get("engine_set"),
                                                                  lv.get("underruns_while_playing"),
                                                                  lv.get("peak")))

    # 3. The bench, with soft-float and with the hardware float instructions.
    benches = {}
    for name, defines in (("soft", ("PLAITS_BENCH",)), ("hw", ("PLAITS_BENCH", "PLAITS_HWFLOAT"))):
        d = os.path.join(work, "bench-" + name)
        if not build(d, log, *defines):
            check("bench builds (%s)" % name, False)
            continue
        run = fwtest(os.path.join(d, "app.bin"), os.path.join(work, "run-" + name), log,
                     "--ms", "60000", "--console", "--halt-ok")
        try:
            with open(os.path.join(work, "run-" + name, "console.txt")) as f:
                console = f.read()
        except OSError:
            console = ""
        with open(os.path.join(out, "bench-%s-console.txt" % name), "w") as f:
            f.write(console)
        b = parse_bench(console)
        b["outcome"] = run.get("outcome")
        b["instructions"] = (run.get("instructions") or {})
        benches[name] = b
        sft = check_softfloat(console)
        check("soft-float bit for bit (%s image)" % name, all(ok for _, ok in sft),
              "%d operations, %d cases each" % (len(sft), CASES))
        check("bench completes (%s)" % name, b["outcome"] == "halt" and b["end"]
              and sorted(b["engines"]) == list(range(len(ENGINES))))
        check("core 1 starts and renders (%s)" % name, b.get("core1") is True and len(b["dual"]) == 3)
    soft, hw = benches.get("soft", {}), benches.get("hw", {})
    if soft:
        f = soft.get("flags", {})
        check("no NaN, infinity or bad conversion", f == {"invalid": 0, "overflow": 0, "convert": 0},
              "soft-float flags %s" % f)
    if soft and hw:
        same = [e for e in range(len(ENGINES))
                if soft["engines"].get(e, {}).get("checksum") == hw["engines"].get(e, {}).get("checksum")]
        check("hardware float sounds the same", len(same) == len(ENGINES),
              "%d of %d engines' checksums equal" % (len(same), len(ENGINES)))

    # 4. The table and the headroom.
    rest, loaded, where = platform_costs(a.perf) if a.perf else platform_costs("")
    rows = []
    for e, name in enumerate(ENGINES):
        r = {"engine": e, "name": name}
        for key, b in (("soft", soft), ("hw", hw)):
            m = b.get("engines", {}).get(e)
            if m:
                r[key] = dict(m, voices_rest=int((BLOCK_CYCLES - rest) // m["max"]),
                              voices_loaded=None if loaded is None else int((BLOCK_CYCLES - loaded) // m["max"]),
                              share=round(100.0 * m["max"] / BLOCK_CYCLES, 2))
        rows.append(r)
    dual = {}
    for key, b in (("soft", soft), ("hw", hw)):
        dual[key] = [dict(d, name=ENGINES[d["engine"]], speedup=round(d["apart"] / d["both"], 3))
                     for d in b.get("dual", []) if d["both"]]
    result = {"format": 1, "result": "FAIL" if problems else "PASS", "checks": checks,
              "image": {"size": size, "app_bin_sha256": image_sha},
              "vendor": {"eurorack": "f4cfa7697095a28d292bff758beb51deb49b5a86",
                         "stmlib": "e3bd7c9cc00e4364166f9905c0509b6ffd0535ec"},
              "block": {"frames": 64, "cycles": BLOCK_CYCLES, "render_frames": 16},
              "platform": {"rest": rest, "loaded": loaded, "from": where},
              "engines": rows, "dual": dual, "live": live,
              "bench_instructions": {k: b.get("instructions") for k, b in benches.items()}}
    with open(os.path.join(out, "plaits.json"), "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(out, "plaits.md"), "w") as f:
        f.write(markdown(result))
    log.close()
    subprocess.run(["rm", "-rf", work])
    print("plaits bench: %s" % result["result"])
    return 1 if problems else 0


def markdown(r):
    L = ["## Plaits load test (M4b): %s" % r["result"], "",
         "fwtest's instructions per audio block (64 frames, %d of core 0's cycles), each engine at its "
         "heaviest over nine settings; voices that fit on core 0 beside the firmware at rest (%s "
         "instructions a block%s). Soft-float is our runtime's; hardware float is the toolchain's "
         "instructions, which fwtest runs; whether the chip has them is open (SR-5)." % (
             r["block"]["cycles"], r["platform"]["rest"],
             "" if r["platform"]["loaded"] is None else
             "; under the heaviest input %s" % r["platform"]["loaded"]), "",
         "| # | Engine | Soft-float max | mean | voices | Hardware float max | mean | voices | Full-scale samples |",
         "|---|---|---|---|---|---|---|---|---|"]
    for row in r["engines"]:
        s, h = row.get("soft", {}), row.get("hw", {})
        L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row["engine"], row["name"], s.get("max", ""), s.get("mean", ""), s.get("voices_rest", ""),
            h.get("max", ""), h.get("mean", ""), h.get("voices_rest", ""), s.get("clipped", "")))
    L += ["", "Two voices at once, core 0 and core 1, against one after the other on core 0:", "",
          "| Engine | Float | apart | at once | speed-up |", "|---|---|---|---|---|"]
    for key, label in (("soft", "soft"), ("hw", "hardware")):
        for d in r["dual"].get(key, []):
            L.append("| %s | %s | %d | %d | %.3f |" % (d["name"], label, d["apart"], d["both"], d["speedup"]))
    L += ["", "| Check | Result | Detail |", "|---|---|---|"]
    L += ["| %s | %s | %s |" % (c["check"], c["result"], c["detail"]) for c in r["checks"]]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--perf", help="tools/perf.py's perf.json, for the firmware's own cost")
    s = sub.add_parser("softfloat")
    s.add_argument("console")
    a = ap.parse_args()
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "softfloat":
        return cmd_softfloat(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
