#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Lints docs/HARDWARE-SPEC.md (R-SPEC-1, R-SPEC-3; check C-SPEC-LINT).

  check-hardware-spec.py [FILE] [--base REV]

Every entry is a `### HW-n: title` heading followed by the fields
`- Fact:`, `- Sources:`, `- Standing:` and `- Needed by:`, each non-empty.
It fails on:
  - a missing or empty field, or a field it doesn't know;
  - an ID used twice, or an open question (`**Q-n.`) numbered twice;
  - a standing that isn't `confirmed ...`, `emulator-only ...`,
    `other chip (SDK63)` or `superseded by HW-n` (an entry that exists);
  - an `other chip` entry whose sources don't cite SDK63 (another JieLi
    chip's SDK; such an entry is never confirmed for the FM-1's chip);
  - a confirmed entry whose sources name nothing independent: it must cite
    SDK, RE, DS, PANEL, MAN or an experiment E-n (HARNESS, the spec side's own
    description of fwtest, and the emulator model don't count);
  - an experiment E-n cited but not listed in
    harness/spec-experiments/README.md (checked only where harness/ is on
    disk; a clean folder skips that part and says so);
  - code: a fenced code block anywhere in the file;
  - history: against REV (default: the merge base with origin/main, when
    there is one and the file existed there), an entry that has gone, or
    one whose fact text changed. A corrected fact gets a new ID and the old
    entry is marked superseded; IDs are never reused or renumbered.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "docs", "HARDWARE-SPEC.md")
EXPERIMENTS = os.path.join(ROOT, "harness", "spec-experiments", "README.md")
FIELDS = ("Fact", "Sources", "Standing", "Needed by")
HEAD = re.compile(r"^### (HW-(\d+)): (\S.*)$")
FIELD = re.compile(r"^- ([A-Z][a-z]+(?: by)?):\s*(.*)$")
SOURCE_KEYS = re.compile(r"\b(SDK|RE|DS|PANEL|MAN|E-\d+)\b")
# Another chip's SDK: a source, but never an independent one for this chip.
OTHER_CHIP = re.compile(r"\bSDK63\b")
EXP = re.compile(r"\bE-(\d+)\b")


def parse(text):
    """Entries {id: {"title", "line", field: text}} and a list of problems."""
    entries, problems = {}, []
    cur = field = None
    for n, line in enumerate(text.splitlines(), 1):
        m = HEAD.match(line)
        if m:
            if m.group(1) in entries:
                problems.append("line %d: %s is used twice" % (n, m.group(1)))
            cur = entries.setdefault(m.group(1), {"title": m.group(3), "line": n})
            field = None
            continue
        if line.startswith("#"):
            cur = field = None
            continue
        if cur is None:
            continue
        m = FIELD.match(line)
        if m:
            field = m.group(1)
            if field not in FIELDS:
                problems.append("line %d: %s has an unknown field '%s'" % (n, cur_id(entries, cur), field))
            cur[field] = m.group(2).strip()
        elif field and line.strip():
            cur[field] = (cur.get(field, "") + " " + line.strip()).strip()
        elif not line.strip():
            continue
    return entries, problems


def cur_id(entries, cur):
    for k, v in entries.items():
        if v is cur:
            return k
    return "?"


def norm(s):
    return " ".join((s or "").split())


def experiments_known():
    if not os.path.exists(EXPERIMENTS):
        return None
    with open(EXPERIMENTS, encoding="utf-8") as f:
        return set(re.findall(r"^\| E-(\d+) \|", f.read(), re.M))


def lint(text, base_text=None, known_exps=None):
    entries, problems = parse(text)
    if not entries:
        problems.append("no entries (### HW-n: title)")
    if "```" in text:
        problems.append("a fenced code block: the spec holds facts, never code")
    qs = re.findall(r"^- \*\*(Q-\d+)\.", text, re.M)
    for q in sorted(set(qs)):
        if qs.count(q) > 1:
            problems.append("%s is used twice" % q)
    for eid, e in sorted(entries.items(), key=lambda kv: kv[1]["line"]):
        for f in FIELDS:
            if not e.get(f):
                problems.append("%s (line %d): no %s" % (eid, e["line"], f))
        st = e.get("Standing", "")
        m = re.match(r"superseded by (HW-\d+)\b", st)
        if m:
            if m.group(1) not in entries or m.group(1) == eid:
                problems.append("%s: superseded by %s, which isn't another entry" % (eid, m.group(1)))
        elif st.startswith("confirmed"):
            if not SOURCE_KEYS.search(e.get("Sources", "")):
                problems.append("%s: confirmed, but its sources name no independent source (SDK, RE, DS, PANEL, MAN, E-n)" % eid)
        elif st.startswith("other chip"):
            if st != "other chip (SDK63)" or not OTHER_CHIP.search(e.get("Sources", "")):
                problems.append("%s: other chip, but its standing isn't 'other chip (SDK63)' or its sources don't cite SDK63" % eid)
        elif not st.startswith("emulator-only"):
            problems.append("%s: standing '%s' is not confirmed, emulator-only, other chip or superseded by HW-n" % (eid, st))
        if known_exps is not None:
            for x in EXP.findall(e.get("Sources", "") + " " + st):
                if x not in known_exps:
                    problems.append("%s: cites E-%s, which harness/spec-experiments/README.md doesn't list" % (eid, x))
    if base_text is not None:
        old, _ = parse(base_text)
        for eid, e in old.items():
            if eid not in entries:
                problems.append("%s was removed: entries stay, marked superseded" % eid)
            elif norm(entries[eid].get("Fact")) != norm(e.get("Fact")):
                problems.append("%s's fact changed: a corrected fact gets a new ID and this one is marked superseded" % eid)
    return entries, problems


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, universal_newlines=True,
                       env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    return p.stdout if p.returncode == 0 else None


def main(argv):
    path, base = SPEC, None
    args = list(argv)
    if "--base" in args:
        i = args.index("--base")
        base = args[i + 1]
        del args[i:i + 2]
    if args:
        path = args[0]
    if not os.path.exists(path):
        print("FAIL: %s does not exist" % os.path.relpath(path, ROOT))
        return 1
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if base is None:
        base = (git("merge-base", "HEAD", "origin/main") or "").strip() or None
    base_text = None
    if base:
        base_text = git("show", "%s:%s" % (base, os.path.relpath(path, ROOT)))
    known = experiments_known()
    entries, problems = lint(text, base_text, known)
    for p in problems:
        print("FAIL " + p)
    n_conf = sum(1 for e in entries.values() if e.get("Standing", "").startswith("confirmed"))
    n_emu = sum(1 for e in entries.values() if e.get("Standing", "").startswith("emulator-only"))
    n_chip = sum(1 for e in entries.values() if e.get("Standing", "").startswith("other chip"))
    print("%d entries (%d confirmed, %d emulator-only, %d other chip, %d other)"
          % (len(entries), n_conf, n_emu, n_chip, len(entries) - n_conf - n_emu - n_chip))
    print("history: %s" % ("checked against %s" % base[:12] if base_text is not None
                           else "no earlier version to compare with"))
    if known is None:
        print("experiments: SKIP (harness/ is not on disk: a clean folder leaves it out)")
    print("hardware spec: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
