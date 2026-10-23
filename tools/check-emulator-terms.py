#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Spec-side text discipline (R-SEP-1, check C-SEP-TERMS).

  check-emulator-terms.py [--show]

Looks for identifiers that occur in vendor/emulator/ and nowhere in
vendor/jieli-sdk/ or (since M4b) vendor/plaits/, in the places the firmware
side reads:
  - every tracked text file outside vendor/emulator/, harness/, sessions/
    (transcripts), docs/prompts/ (prompts are kept verbatim) and
    vendor/plaits/ (third-party code we didn't write, since M4b; its
    SOURCE.md, which we write, is scanned since SR-4);
  - the two doors, docs/HARNESS.md and docs/HARDWARE-SPEC.md, and their
    reviews in docs/reviews/, for identifier-shaped words only: they carry
    addresses and other numbers on purpose, each one sourced, and people
    review them too (R-SPEC-2);
  - the commit messages in COMMIT_RANGE (default ..HEAD);
  - the pull request's title and body, when GITHUB_EVENT_PATH names one.

The list is built at run time from vendor/emulator/ and never written down:
identifier-shaped words (with an underscore, inner capitals, or letters and
digits mixed; four characters or more, not just hex digits) and hex numbers
of four digits or more, except universal constants (powers of two, 2^n-1,
2^n+1, sign-bit masks and IEEE 754's standard patterns: universal(), by
rule, since SR-4's note). Terms that already occur in CLEAN_BASELINE's tree
(the repository as the clean side left it at the end of M0a, before any
emulator source entered it) or in vendor/jieli-sdk/ (whole identifiers, or the parts of one between
underscores) are not on the list. Since M4b (the owner's decision) neither
are the terms of vendor/plaits/, Mutable Instruments' Plaits, MIT, built
the same way as the SDK's, but only from the files vendor/plaits/SHA256SUMS
lists, each matching its hash (the pinned upstream tree, R-REPRO-7); if any
doesn't, the check fails. The output says how many emulator-only terms the
Plaits list takes off (a count, never the terms). A hit is reported as its place and a SHA-256 prefix of the word, never
the word or the text around it, because the log is visible to the firmware
side; `--show` prints the word too, for a spec-side author fixing it.

A hit is accepted without an entry of its own when the term occurs in one of
the two doors as they are on main (DOOR_FILES at origin/main, or at the
commit DOORS_REF names): what is there passed people's review. The doors are
read from that commit's blobs, never from the working tree, so a branch
cannot get a term accepted by adding it to a door; a term new to a door is
still a hit until the change that adds it has merged. When that commit
can't be found, nothing is accepted this way (and the output says so).
Any other reviewed false positive is listed by its hash in
config/emulator-terms-reviewed.json, with a reason that doesn't name it.

Where vendor/emulator/ isn't on disk (a clean folder), it says SKIP.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sha256sums  # noqa: E402  (tools/, our own)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMU = os.path.join(ROOT, "vendor", "emulator")
SDK = os.path.join(ROOT, "vendor", "jieli-sdk")
PLAITS = os.path.join(ROOT, "vendor", "plaits")
REVIEWED = os.path.join(ROOT, "config", "emulator-terms-reviewed.json")
# main at the end of M0a (pull request #2): written by the clean side only
CLEAN_BASELINE = "265f15b5b646cf7d5110d4606365d82fae93f5bc"
EXCLUDE = ("vendor/emulator/", "harness/", "sessions/", "docs/prompts/", "vendor/plaits/")
# what we write ourselves inside an excluded vendored tree is scanned (since SR-4)
OWN_NOTES = ("vendor/plaits/SOURCE.md",)
DOORS = ("docs/HARNESS.md", "HARDWARE-SPEC.md", "docs/HARDWARE-SPEC.md")
# The doors whose merged text is accepted everywhere, and the commit read for them.
DOOR_FILES = ("docs/HARDWARE-SPEC.md", "docs/HARNESS.md")
DOORS_REF = "origin/main"
# Reviews of the doors discuss their facts, numbers included: scanned the same way.
DOOR_PREFIXES = ("docs/reviews/",)

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


def power_of_two(v):
    return v > 0 and v & (v - 1) == 0


def ieee754(v):
    """Whether v is a standard IEEE 754 single or double bit pattern: an
    infinity or the quiet NaN (either sign; the exponent field all ones,
    the fraction zero or only its top bit), or a signed power of two whose
    unbiased exponent is 0, +-23 (single) or +-52 (double), i.e. one,
    2^+-23 and 2^+-52 (the fraction zero)."""
    for width, frac in ((32, 23), (64, 52)):
        if v >> width:
            continue
        ebits = width - 1 - frac
        emax, bias = (1 << ebits) - 1, (1 << (ebits - 1)) - 1
        e, m = (v >> frac) & emax, v & ((1 << frac) - 1)
        if e == emax and m in (0, 1 << (frac - 1)):
            return True
        if m == 0 and e - bias in (0, frac, -frac):
            return True
    return False


def universal(v):
    """Numbers that are universal constants, never emulator terms (since
    SR-4's note; R-SEP-1), by rule rather than by list: powers of two (the
    sign-bit masks among them), 2^n-1 (all-ones masks, the masks below a
    sign bit, IEEE 754's exponent biases and fraction masks), 2^n+1, and
    IEEE 754's standard single and double patterns (ieee754)."""
    return power_of_two(v) or power_of_two(v + 1) or power_of_two(v - 1) or ieee754(v)


def norm_hex(h):
    v = int(h[2:].replace("_", ""), 16)
    return "0x%x" % v if v >= 0x1000 and not universal(v) else None


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


def public_terms(texts):
    """The terms of a public source's texts, with the parts of each
    identifier between underscores (JL_TIMER4 names TIMER4, IRQ_SPI1_IDX
    names SPI1)."""
    known = set()
    for text in texts:
        t = terms_of(text)
        known |= t
        known |= set(w for x in t if not x.startswith("0x") for w in x.split("_") if shaped(w))
    return known


def verified_texts(top):
    """The texts of the files top/SHA256SUMS lists, each checked against its
    hash (tools/sha256sums.py); ValueError names the first that is missing
    or doesn't match, or a file there that isn't listed."""
    texts = []
    for data in sha256sums.verified(top).values():
        try:
            texts.append(data.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    return texts


def emulator_terms_counted():
    """(the emulator-only terms, how many of the emulator's terms only the
    Plaits list took off). ValueError if vendor/plaits/ isn't the
    checksum-verified tree."""
    emu = set()
    for text in walk_text(EMU):
        emu |= terms_of(text)
    known = public_terms(walk_text(SDK))
    known |= set().union(*(terms_of(text) for text in baseline_texts()))
    plaits = public_terms(verified_texts(PLAITS)) if os.path.isdir(PLAITS) else set()
    left = emu - known
    return left - plaits, len(left & plaits)


def emulator_terms():
    return emulator_terms_counted()[0]


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


def doors_ref():
    """The commit whose doors are accepted: DOORS_REF from the environment,
    or origin/main. None if it isn't there (fail closed)."""
    ref = os.environ.get("DOORS_REF") or DOORS_REF
    p = subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "-q", ref + "^{commit}"],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    return p.stdout.strip() if p.returncode == 0 else None


def door_terms(commit):
    """Every term in DOOR_FILES at that commit (from its blobs), numbers too."""
    out = set()
    for path in DOOR_FILES:
        p = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (commit, path)],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if p.returncode == 0:
            out |= terms_of(p.stdout.decode("utf-8", "replace"))
    return out


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
    try:
        terms, by_plaits = emulator_terms_counted()
    except (OSError, ValueError) as e:
        print("vendor/plaits/: %s, so its terms can't be taken off the list" % e)
        print("emulator terms: FAIL")
        return 1
    ok_hashes = reviewed()
    hits = []
    scanned = 0
    for p in tracked():
        if p.startswith(EXCLUDE) and p not in OWN_NOTES:
            continue
        try:
            with open(os.path.join(ROOT, p), encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        hits += hits_in(text, terms, p, words_only=p in DOORS or p.startswith(DOOR_PREFIXES))
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
    commit = doors_ref()
    in_doors = door_terms(commit) if commit else set()
    if commit:
        print("doors accepted as on %s (%s): %d terms" % (os.environ.get("DOORS_REF") or DOORS_REF,
                                                      commit[:12], len(in_doors & terms)))
    else:
        print("doors: %s not found, so no term is accepted for being in them"
              % (os.environ.get("DOORS_REF") or DOORS_REF))
    bad = 0
    for where, n, t in sorted(hits):
        key = h(t)
        if t in in_doors:
            print("DOOR %s:%d term %s: in the reviewed doors on main" % (where, n, key))
            continue
        if key in ok_hashes:
            print("REVIEWED %s:%d term %s: %s" % (where, n, key, ok_hashes[key]))
            continue
        bad += 1
        print("HIT %s:%d term %s%s" % (where, n, key, (" (%s)" % t) if show else ""))
    print("%d emulator-only terms; %d files, %d commit messages, %d pull request texts scanned"
          % (len(terms), scanned, len(commits), pr))
    print("the Plaits list (vendor/plaits/, checksums verified) took %d of the emulator's terms off "
          "the list" % by_plaits if os.path.isdir(PLAITS) else "no vendor/plaits/: no Plaits list")
    print("emulator terms: %s" % ("FAIL" if bad else "PASS"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
