#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Spec-side text discipline (R-SEP-1, check C-SEP-TERMS).

  check-emulator-terms.py [--show]

Looks for identifiers that occur in vendor/emulator/ and nowhere in
vendor/jieli-sdk/, in the places the firmware side reads:
  - every tracked text file outside vendor/emulator/, harness/, sessions/
    (transcripts) and docs/prompts/ (prompts are kept verbatim);
  - the two doors, docs/HARNESS.md and docs/HARDWARE-SPEC.md, for
    identifier-shaped words only: they carry addresses and other numbers
    on purpose, each one sourced, and people review them too (R-SPEC-2);
  - the commit messages in COMMIT_RANGE (default ..HEAD);
  - the pull request's title and body, when GITHUB_EVENT_PATH names one.

The list is built at run time from vendor/emulator/ and never written down:
identifier-shaped words (with an underscore, inner capitals, or letters and
digits mixed; four characters or more, not just hex digits) and hex numbers
of four digits or more. Terms that already occur in CLEAN_BASELINE's tree
(the repository as the clean side left it at the end of M0a, before any
emulator source entered it) or in vendor/jieli-sdk/ are not on the list. A hit is reported as its place and a SHA-256 prefix of the word, never
the word or the text around it, because the log is visible to the firmware
side; `--show` prints the word too, for a spec-side author fixing it. A
reviewed false positive is listed by that hash in
config/emulator-terms-reviewed.json, with a reason that doesn't name it.

Where vendor/emulator/ isn't on disk (a clean folder), it says SKIP.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMU = os.path.join(ROOT, "vendor", "emulator")
SDK = os.path.join(ROOT, "vendor", "jieli-sdk")
REVIEWED = os.path.join(ROOT, "config", "emulator-terms-reviewed.json")
# main at the end of M0a (pull request #2): written by the clean side only
CLEAN_BASELINE = "265f15b5b646cf7d5110d4606365d82fae93f5bc"
EXCLUDE = ("vendor/emulator/", "harness/", "sessions/", "docs/prompts/")
DOORS = ("docs/HARNESS.md", "HARDWARE-SPEC.md", "docs/HARDWARE-SPEC.md")

WORD = re.compile(r"(?<![0-9A-Za-z_])[A-Za-z_][A-Za-z0-9_]*")
HEX = re.compile(r"\b0[xX][0-9A-Fa-f_]{4,}\b")


def shaped(w):
    if len(w) < 4 or not re.search(r"[A-Za-z]", w):
        return False
    if re.fullmatch(r"x?[0-9A-Fa-f]+(_[ui](8|16|32|64))?", w):
        return False
    if "_" in w.strip("_"):
        return True
    if re.search(r"[a-z][A-Z]", w):
        return True
    return bool(re.search(r"[A-Za-z]", w) and re.search(r"[0-9]", w))


def norm_hex(h):
    v = int(h[2:].replace("_", ""), 16)
    return "0x%x" % v if v >= 0x1000 else None


def terms_of(text):
    out = set(n for n in (norm_hex(h) for h in HEX.findall(text)) if n)
    out.update(w for w in WORD.findall(HEX.sub(" ", text)) if shaped(w))
    return out


def walk_text(top):
    for dirpath, _, names in os.walk(top):
        for n in names:
            try:
                with open(os.path.join(dirpath, n), encoding="utf-8") as f:
                    yield f.read()
            except (UnicodeDecodeError, OSError):
                continue


def emulator_terms():
    emu = set()
    for text in walk_text(EMU):
        emu |= terms_of(text)
    known = set()
    for text in walk_text(SDK):
        known |= terms_of(text)
    for text in baseline_texts():
        known |= terms_of(text)
    return emu - known


def baseline_texts():
    names = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", CLEAN_BASELINE],
                           check=True, stdout=subprocess.PIPE, universal_newlines=True).stdout.split()
    for n in names:
        blob = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (CLEAN_BASELINE, n)],
                              stdout=subprocess.PIPE).stdout
        try:
            yield blob.decode("utf-8")
        except UnicodeDecodeError:
            continue


def h(term):
    return hashlib.sha256(term.encode()).hexdigest()[:16]


def reviewed():
    if not os.path.exists(REVIEWED):
        return {}
    with open(REVIEWED, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for r in data.get("reviewed", []):
        if not (r.get("sha256_16") and r.get("reason")):
            raise SystemExit("%s: each entry needs sha256_16 and reason" % REVIEWED)
        out[r["sha256_16"]] = r["reason"]
    return out


def tracked():
    p = subprocess.run(["git", "-C", ROOT, "ls-files", "-z"], check=True, stdout=subprocess.PIPE)
    return [x.decode() for x in p.stdout.split(b"\0") if x]


def hits_in(text, terms, where, words_only=False):
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        got = terms_of(line)
        if words_only:
            got = set(t for t in got if not t.startswith("0x"))
        for t in got & terms:
            found.append((where, n, t))
    return found


def main():
    show = "--show" in sys.argv[1:]
    if not os.path.isdir(EMU):
        print("SKIP: vendor/emulator/ is not on disk (a clean folder leaves it out)")
        return 0
    terms = emulator_terms()
    ok_hashes = reviewed()
    hits = []
    scanned = 0
    for p in tracked():
        if p.startswith(EXCLUDE):
            continue
        try:
            with open(os.path.join(ROOT, p), encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        hits += hits_in(text, terms, p, words_only=p in DOORS)
    rng = os.environ.get("COMMIT_RANGE") or "..HEAD"
    log = subprocess.run(["git", "-C", ROOT, "log", "--format=%x00%H%n%B", rng],
                         stdout=subprocess.PIPE, universal_newlines=True).stdout
    commits = [c for c in log.split("\0") if c.strip()]
    for c in commits:
        sha, _, body = c.partition("\n")
        hits += hits_in(body, terms, "commit %s" % sha[:12])
    event = os.environ.get("GITHUB_EVENT_PATH")
    pr = 0
    if event and os.path.exists(event):
        with open(event, encoding="utf-8") as f:
            ev = json.load(f)
        pull = ev.get("pull_request") or {}
        if pull:
            pr = 1
            hits += hits_in(pull.get("title") or "", terms, "pull request title")
            hits += hits_in(pull.get("body") or "", terms, "pull request body")
    bad = 0
    for where, n, t in sorted(hits):
        key = h(t)
        if key in ok_hashes:
            print("REVIEWED %s:%d term %s: %s" % (where, n, key, ok_hashes[key]))
            continue
        bad += 1
        print("HIT %s:%d term %s%s" % (where, n, key, (" (%s)" % t) if show else ""))
    print("%d emulator-only terms; %d files, %d commit messages, %d pull request texts scanned"
          % (len(terms), scanned, len(commits), pr))
    print("emulator terms: %s" % ("FAIL" if bad else "PASS"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
