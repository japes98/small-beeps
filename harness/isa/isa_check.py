#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""C-HARNESS-ISA: fwtest runs every instruction form the pinned toolchain
knows for the firmware's CPU flags, or the form is a documented gap.

  harness/isa/isa_check.py --out DIR

Spec side (docs/HARNESS.md, "Instructions"). What it does:

1. Copies the vendor objdump out of the pinned toolchain's image
   (tools/build.sh) into DIR, and finds the disassembler's decoder tables
   in it by their content (LLVM's fixed-length decoder table format; the
   one for pi32v2 is the set objdump itself disassembles samples of at the
   expected length). No offset or table is written down here: a later
   toolchain is searched the same way, and a search that finds too little
   is a failure, never a pass.
2. Walks every leaf of those tables (one instruction form each) and makes
   encodings for it: the bits the table fixes, the others zero, all ones
   and at random (a fixed seed).
3. Disassembles them with the firmware's flags (SDK_FLAGS), and assembles
   each text again with the same flags, as the compiler and assembler would
   emit it: the assembler's bytes are the forms checked. Branches get a
   label as their target, blocks (`{`) a body, a dual-issue pair's head a
   second half; texts the assembler refuses (another CPU's forms, and the
   few the disassembler prints in a way it does not parse) are left out.
4. Runs `fwtest decode` (harness/src/decode.rs) on every encoding in the
   fwtest image (harness/ci.sh): each must decode to its length and run.
5. A form that does not is a failure unless its shape (shape(): the
   disassembly with registers and numbers abstracted) is a line of
   harness/isa/known-gaps.txt, which says why. A line no failing form has
   any more is a failure too, so the list stays exact, and so is a line
   that is also the shape of a form that runs.

DIR gets forms.tsv (each encoding, its shape and fwtest's outcome),
gaps.txt (the failing shapes, known or not) and summary.txt. The toolchain
binaries copied into DIR/work are deleted at the end.
"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
# The SDK's flags for the AC791N (HARDWARE-SPEC HW-62): clang's -mcpu=r3 -mfprev1, the linker
# plugin's mcpu=r3 -mattr=+fprev1. objdump takes the -mattr spelling.
SDK_FLAGS = ["-mcpu=r3", "-mfprev1"]
OBJDUMP_FLAGS = ["-mcpu=r3", "-mattr=+fprev1"]
SAMPLES_PER_LEAF = 16
SEED = 20261028
# A plausible toolchain has far more than this many decoder leaves for the target.
MIN_LEAVES = 300


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


# ---- 1. the decoder tables -------------------------------------------------------------------

class Tables:
    """LLVM's FixedLenDecoderEmitter tables in a binary: MCD_OPC_ExtractField 1, FilterValue 2,
    CheckField 3, CheckPredicate 4, Decode 5, TryDecode 6, SoftFail 7, Fail 8; NumToSkip is
    2 bytes in LLVM 4 (3 in later releases: both are tried)."""

    def __init__(self, data):
        self.b = data

    def uleb(self, i):
        r = s = 0
        while True:
            c = self.b[i]
            i += 1
            r |= (c & 0x7f) << s
            s += 7
            if not c & 0x80:
                return r, i

    def parse(self, i0, skip, limit=400000):
        """(end, decodes, max field end) of a table at i0, or None."""
        b, i, maxt, dec, hi = self.b, i0, i0, 0, 0
        try:
            while i < i0 + limit:
                op = b[i]
                i += 1
                if op in (1, 3):
                    st, ln = b[i], b[i + 1]
                    i += 2
                    if st >= 64 or ln == 0 or ln > 32:
                        return None
                    hi = max(hi, st + ln)
                    if op == 3:
                        _, i = self.uleb(i)
                        n = int.from_bytes(b[i:i + skip], "little")
                        i += skip
                        maxt = max(maxt, i + n)
                elif op in (2, 4):
                    v, i = self.uleb(i)
                    if op == 4 and v > 255:
                        return None
                    n = int.from_bytes(b[i:i + skip], "little")
                    i += skip
                    maxt = max(maxt, i + n)
                elif op in (5, 6):
                    o, i = self.uleb(i)
                    d, i = self.uleb(i)
                    if o > 20000 or d > 20000:
                        return None
                    dec += 1
                    if op == 6:
                        n = int.from_bytes(b[i:i + skip], "little")
                        i += skip
                        maxt = max(maxt, i + n)
                elif op == 7:
                    _, i = self.uleb(i)
                    _, i = self.uleb(i)
                elif op == 8:
                    if i >= maxt:
                        return i, dec, hi
                else:
                    return None
        except IndexError:
            return None
        return None

    def candidates(self):
        """Every table-like run of bytes: (start, NumToSkip size, width, leaves)."""
        out, b, i = [], self.b, 0
        while i < len(b) - 4:
            if b[i] == 1 and b[i + 1] < 64 and 0 < b[i + 2] <= 32 and b[i + 3] in (2, 3, 4, 5, 6):
                for skip in (2, 3):
                    r = self.parse(i, skip)
                    if r and r[1] >= 3:
                        end, dec, hi = r
                        width = next((w for w in (16, 32, 48, 64) if hi <= w), None)
                        if width and width <= 48:
                            out.append((i, skip, width, self.leaves(i, skip)))
                            i = end - 1
                            break
            i += 1
        return out

    def leaves(self, start, skip):
        """Every Decode / TryDecode leaf with the field values fixed on its path."""
        out = []
        b = self.b

        def rec(i, cons, cur, end):
            while i < end:
                op = b[i]
                i += 1
                if op == 1:
                    cur = (b[i], b[i + 1])
                    i += 2
                elif op == 2:
                    v, i = self.uleb(i)
                    n = int.from_bytes(b[i:i + skip], "little")
                    i += skip
                    rec(i, cons + [(cur[0], cur[1], v)], cur, i + n)
                    i += n
                elif op == 3:
                    st, ln = b[i], b[i + 1]
                    i += 2
                    v, i = self.uleb(i)
                    n = int.from_bytes(b[i:i + skip], "little")
                    i += skip
                    rec(i, cons + [(st, ln, v)], cur, i + n)
                    i += n
                elif op == 4:
                    _, i = self.uleb(i)
                    n = int.from_bytes(b[i:i + skip], "little")
                    i += skip
                    rec(i, cons, cur, i + n)
                    i += n
                elif op == 5:
                    _, i = self.uleb(i)
                    _, i = self.uleb(i)
                    out.append(cons)
                    return
                elif op == 6:
                    _, i = self.uleb(i)
                    _, i = self.uleb(i)
                    i += skip
                    out.append(cons)
                elif op == 7:
                    _, i = self.uleb(i)
                    _, i = self.uleb(i)
                elif op == 8:
                    return

        rec(start, [], None, 1 << 60)
        return out


def to_bytes(width, insn):
    """The table's instruction value as memory bytes: halfwords, the first in memory the most
    significant, each little-endian (pi32v2's order, which the sample check confirms)."""
    return b"".join(((insn >> s) & 0xffff).to_bytes(2, "little") for s in range(width - 16, -1, -16))


def leaf_samples(width, cons, k, rng):
    fixed = mask = 0
    for st, ln, v in cons:
        m = ((1 << ln) - 1) << st
        fixed = (fixed & ~m) | (v << st)
        mask |= m
    free = ((1 << width) - 1) & ~mask
    got = [fixed, fixed | free]
    while len(got) < k:
        got.append((rng.getrandbits(width) & free) | fixed)
    return list(dict.fromkeys(to_bytes(width, x) for x in got))


# ---- 2, 3. the toolchain in its container ------------------------------------------------

class Toolchain:
    def __init__(self, work):
        self.work = work
        tag = sh(["sh", os.path.join(ROOT, "tools/build.sh"), "image-tag"]).strip()
        if subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode != 0:
            sh(["sh", os.path.join(ROOT, "tools/build.sh"), "image"])
        self.name = "sb-isa-%d" % os.getpid()
        sh(["docker", "run", "-d", "--rm", "--name", self.name, "--platform", "linux/amd64", "--network", "none",
            "--user", "%d:%d" % (os.getuid(), os.getgid()), "-v", work + ":/w", "-w", "/w", tag, "sleep", "86400"])

    def run(self, script, check=False):
        r = subprocess.run(["docker", "exec", self.name, "sh", "-c", script], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise SystemExit("isa: toolchain command failed: %s\n%s" % (script, r.stderr[-2000:]))
        return r

    def stop(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def disassemble(self, obj, flags=OBJDUMP_FLAGS):
        return self.run("objdump -d %s %s" % (" ".join(flags), obj), check=True).stdout


def bytes_file(samples):
    """An assembly file with each sample as its own function s<i>, so the disassembler keeps
    them apart."""
    lines = [".text"]
    for i, raw in enumerate(samples):
        lines += [".globl s%d" % i, ".type s%d,@function" % i, "s%d:" % i,
                  ".byte " + ",".join("0x%02x" % c for c in raw), ".size s%d,.-s%d" % (i, i)]
    return "\n".join(lines) + "\n"


INSN = re.compile(r"^\s+[0-9a-f]+:\s+((?:[0-9a-f]{2} )+)\s*\t?(.*)$")


def parse_dis(text):
    """{sample index: [(hex, text), ...]} from objdump's output for s<i> functions."""
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"^s(\d+):", ln)
        if m:
            cur = int(m.group(1))
            out[cur] = []
            continue
        m = INSN.match(ln)
        if m and cur is not None:
            out[cur].append((m.group(1).replace(" ", ""), m.group(2).strip()))
    return out


# Branch targets and blocks, which the assembler needs written its own way.
TARGET = re.compile(r"\b(goto|call|gotoss) (-?\d+)")
ANNOT = re.compile(r"\s*<[^<>]*:\s*[0-9a-fA-F]+\s*>")
PARTNERS = ["r3 = [r4+8]", "r15 = [r14+8]", "[r4+8] = r3", "r1 = [sp+8]"]


def snippet(text, i, partner):
    """Assembly for one disassembled text: (lines, its own line's index in them)."""
    t = ANNOT.sub("", text).strip()
    lab = "L%d" % i
    m = re.match(r"^rep (\d+) (r\d+|\d+) \{$", t)
    if m:
        return ["\trep %s {" % m.group(2), "\tr1 = r2 + r3", "\t}"], 0
    if t.endswith("{"):
        return ["\t" + t, "\tr1 = r2 + r3", "\t}"], 0
    if TARGET.search(t) and "ifs2ns" not in t:
        t = TARGET.sub(lambda m: m.group(1) + " " + lab, t)
        body = ["\t" + t] + (["\t" + partner] if t.rstrip().endswith("#") else [])
        return body + ["\tnop", lab + ":", "\tnop"], 0
    if "ifs2ns goto" in t:
        t = re.sub(r"goto -?\d+", "goto " + lab, t)
        return ["\t" + t, "\tnop", lab + ":", "\tnop"], 0
    return ["\t" + t] + (["\t" + partner] if t.rstrip().endswith("#") else []), 0


def reassemble(tc, texts, tag):
    """Assembles every text with the SDK's flags, leaving out the ones the assembler refuses
    (and any whose snippet crashes it). {index: (canonical hex, its disassembly)}."""
    partner = {i: 0 for i in texts}
    alive = dict(texts)

    def build(ids):
        lines, owner = [".text"], {}
        for i in ids:
            body, _ = snippet(alive[i], i, PARTNERS[partner[i]])
            lines += [".globl s%d" % i, ".type s%d,@function" % i, "s%d:" % i]
            for b in body:
                owner[len(lines) + 1] = i
                lines.append(b)
            lines.append(".size s%d,.-s%d" % (i, i))
        return "\n".join(lines) + "\n", owner

    def attempt(ids):
        src, owner = build(ids)
        with open(os.path.join(tc.work, tag + ".s"), "w") as f:
            f.write(src)
        r = tc.run("clang -target pi32v2 %s -c %s.s -o %s.o" % (" ".join(SDK_FLAGS), tag, tag))
        return r, owner

    ids = sorted(alive)
    for _ in range(40):
        r, owner = attempt(ids)
        if r.returncode == 0:
            break
        errs = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"%s\.s:(\d+):\d+: error: (.*)" % tag, r.stderr)]
        moved = False
        for ln, msg in errs:
            i = owner.get(ln)
            if i is None or i not in alive:
                continue
            moved = True
            if "parallel-B" in msg and partner[i] + 1 < len(PARTNERS):
                partner[i] += 1
            else:
                del alive[i]
        if not moved:
            # a crash (seen in the assembler's fixup layout), or an error no snippet owns:
            # bisect for the snippets that do it
            for i in bisect_fail(attempt, ids):
                del alive[i]
        ids = [i for i in ids if i in alive]
    else:
        raise SystemExit("isa: the assembler kept refusing the forms file (%s)" % tag)
    dis = parse_dis(tc.disassemble(tag + ".o"))
    out = {}
    for i in ids:
        ins = dis.get(i, [])
        if ins:
            out[i] = ins[0]
    return out


def bisect_fail(attempt, ids):
    """The snippets among ids the assembler fails on (each alone, or a group that fails)."""
    if len(ids) <= 1:
        return set(ids)
    bad = set()
    for half in (ids[:len(ids) // 2], ids[len(ids) // 2:]):
        r, _ = attempt(half)
        if r.returncode != 0:
            bad |= bisect_fail(attempt, half)
    return bad


# ---- 5. shapes and the known gaps --------------------------------------------------------

def shape(text):
    """The disassembly with registers and numbers abstracted (R, RR a pair, #), a register's
    halves and bytes (.l .h .b0..b3) as .H, and a register list as what it holds: general
    registers ({R..}, after rets or pc), special registers fwtest models ({SREGS}) or not
    ({SREGS-NOT-MODELLED})."""
    t = ANNOT.sub("", text).strip()
    t = re.sub(r"\s+#$", " #", t)
    t = re.sub(r"\br\d+_r\d+\b", "RR", t)
    t = re.sub(r"\br\d+\b", "R", t)
    t = re.sub(r"(?<![\w.])-?(0x[0-9A-Fa-f]+|\d+)\b", "#", t)
    t = re.sub(r"R-R", "R", t)
    t = re.sub(r"\.[lhb][0-3]?\b", ".H", t)
    t = re.sub(r"\{([^}]*)\}", _list, t)
    return re.sub(r"\s+", " ", t)


def _list(m):
    x = m.group(1)
    if re.search(r"\bR\b", x):
        return "{%sR..}" % ("rets, " if "rets" in x else "pc, " if "pc" in x else "")
    return "{SREGS-NOT-MODELLED}" if re.search(r"\b(pc|cnum|uspn|icfgn|icfgs)\b", x) else "{SREGS}"


def load_known(path):
    """{shape: reason} from known-gaps.txt: a shape, a tab, the reason's name (defined in the
    file's `# reason NAME: ...` lines)."""
    reasons, known = set(), {}
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            m = re.match(r"^# reason (\S+):", line)
            if m:
                reasons.add(m.group(1))
                continue
            if not line.strip() or line.startswith("#"):
                continue
            s, _, why = line.partition("\t")
            if why not in reasons:
                raise SystemExit("isa: %s line %d: no such reason %r" % (path, n, why))
            known[s] = why
    return known


# ---- the check -------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    work = os.path.join(out, "work")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(work)
    tc = Toolchain(work)
    try:
        return check(tc, out, work)
    finally:
        tc.stop()
        shutil.rmtree(work, ignore_errors=True)


def check(tc, out, work):
    rng = random.Random(SEED)
    tc.run("cp /opt/jieli/common/bin/objdump /w/objdump.bin", check=True)
    with open(os.path.join(work, "objdump.bin"), "rb") as f:
        tables = Tables(f.read())
    os.remove(os.path.join(work, "objdump.bin"))

    # 1. which candidate tables are pi32v2's: objdump disassembles their samples at their width
    cands = tables.candidates()
    chosen = []
    for start, skip, width, leaves in cands:
        probe, owner = [], []
        for li, cons in enumerate(leaves[:60]):
            for raw in leaf_samples(width, cons, 3, rng)[:3]:
                probe.append(raw)
                owner.append(li)
        with open(os.path.join(work, "probe.s"), "w") as f:
            f.write(bytes_file(probe))
        tc.run("clang -target pi32v2 -c probe.s -o probe.o", check=True)
        dis = parse_dis(tc.disassemble("probe.o", ["-mcpu=r5", "-mattr=+fprev2,+simd,+cordic,+instrev2,+secext,+full-rep,+round-64"]))
        good = set(owner[i] for i, raw in enumerate(probe)
                   if len(dis.get(i, [])) == 1 and dis[i][0][0] == raw.hex() and "unknown" not in dis[i][0][1])
        # (a table of another of the toolchain's targets may pass too: its forms are then checked
        # as pi32v2's, each still only if objdump and the assembler take it)
        if owner and len(good) >= 0.6 * len(set(owner)):
            chosen.append((start, width, leaves))
    widths = sorted(set(w for _, w, _ in chosen))
    nleaves = sum(len(lv) for _, _, lv in chosen)
    if 16 not in widths or 32 not in widths or nleaves < MIN_LEAVES:
        print("isa: FAIL, the toolchain's decoder tables were not found (widths %s, %d leaves)" % (widths, nleaves))
        return 1

    # 2. samples per leaf
    samples, leaf_of = [], []
    for t, (start, width, leaves) in enumerate(chosen):
        for li, cons in enumerate(leaves):
            for raw in leaf_samples(width, cons, SAMPLES_PER_LEAF, rng):
                samples.append(raw)
                leaf_of.append((t, li))
    with open(os.path.join(work, "samples.s"), "w") as f:
        f.write(bytes_file(samples))
    tc.run("clang -target pi32v2 -c samples.s -o samples.o", check=True)
    dis = parse_dis(tc.disassemble("samples.o"))
    texts = {i: dis[i][0][1] for i, raw in enumerate(samples)
             if len(dis.get(i, [])) == 1 and dis[i][0][0] == raw.hex() and "unknown" not in dis[i][0][1]
             and "??" not in dis[i][0][1] and dis[i][0][1].count("(") == dis[i][0][1].count(")")}
    leaves_at_flags = set(leaf_of[i] for i in texts)

    # 3. the assembler's own encodings of them, with the SDK's flags
    canon = reassemble(tc, texts, "forms")
    leaves_assembled = set(leaf_of[i] for i in canon)
    encodings = {}
    for i, (hx, text) in canon.items():
        encodings.setdefault(hx, text)
    hexes = sorted(encodings)

    # 4. fwtest
    with open(os.path.join(work, "encodings.txt"), "w") as f:
        f.write("\n".join(hexes) + "\n")
    ftag = sh(["sh", os.path.join(ROOT, "harness/ci.sh"), "tag"]).strip()
    if subprocess.run(["docker", "image", "inspect", ftag], capture_output=True).returncode != 0:
        sh(["sh", os.path.join(ROOT, "harness/ci.sh"), "image"])
    rep = sh(["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none", "-v", work + ":/w:ro",
              ftag, "decode", "/w/encodings.txt"])
    result = {}
    for ln in rep.splitlines():
        hx, ln_, what = ln.split("\t")
        result[hx] = (ln_, what)
    if set(result) != set(hexes):
        print("isa: FAIL, fwtest decode did not report every encoding")
        return 1

    # 5. the verdict
    known_gaps = load_known(os.path.join(HERE, "known-gaps.txt"))
    rows, failing, running = [], {}, set()
    for hx in hexes:
        ln_, what = result[hx]
        ok = what == "runs" and ln_ == str(len(hx) // 2)
        s = shape(encodings[hx])
        rows.append("%s\t%s\t%s" % (hx, s, "runs" if ok else what if ln_ in ("-", str(len(hx) // 2)) else "wrong-length"))
        if ok:
            running.add(s)
        else:
            failing.setdefault(s, []).append(hx)
    known = {s: (known_gaps[s], len(h)) for s, h in failing.items() if s in known_gaps}
    unknown = {s: h for s, h in failing.items() if s not in known_gaps}
    stale = sorted(s for s in known_gaps if s not in failing)
    # a known gap's shape must not be a form that runs too, or the line would excuse it failing
    blurred = sorted(s for s in known_gaps if s in running)
    with open(os.path.join(out, "forms.tsv"), "w") as f:
        f.write("hex\tshape\tfwtest\n" + "\n".join(rows) + "\n")
    with open(os.path.join(out, "gaps.txt"), "w") as f:
        for s in sorted(unknown):
            f.write("UNKNOWN\t%s\t%d encodings, e.g. %s\n" % (s, len(unknown[s]), unknown[s][0]))
        for s in sorted(known):
            f.write("known\t%s\t%d encodings\t%s\n" % (s, known[s][1], known[s][0]))
    summary = {
        "decoder_tables": len(chosen), "decoder_leaves": nleaves,
        "leaves_disassembled_at_sdk_flags": len(leaves_at_flags),
        "leaves_assembled_at_sdk_flags": len(leaves_assembled),
        "encodings": len(hexes), "shapes": len(set(shape(t) for t in encodings.values())),
        "encodings_running": sum(1 for r in rows if r.endswith("\truns")),
        "failing_shapes_known": len(known), "failing_shapes_unknown": len(unknown),
        "known_gap_lines_unused": stale, "known_gap_lines_also_running": blurred,
        "sdk_flags": " ".join(SDK_FLAGS),
    }
    with open(os.path.join(out, "summary.txt"), "w") as f:
        f.write(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    for s in sorted(unknown):
        print("isa: not run and not a known gap: %s (%d encodings, e.g. %s)" % (s, len(unknown[s]), unknown[s][0]))
    for p in stale:
        print("isa: known-gaps.txt line matches no failing form any more: %s" % p)
    for p in blurred:
        print("isa: known-gaps.txt line is also the shape of forms that run (make it narrower): %s" % p)
    if unknown or stale or blurred:
        print("isa: FAIL")
        return 1
    print("isa: PASS (every form the toolchain knows at %s runs in fwtest, or is a known gap)" % " ".join(SDK_FLAGS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
