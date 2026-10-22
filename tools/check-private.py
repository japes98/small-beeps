#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""No private terms in the repository (check C-PRIVATE; R-PUB-3).

  check-private.py [--range RANGE] [--require]   tracked files and commit messages
  check-private.py --staged                      staged files (pre-commit hook)
  check-private.py --message-file FILE           a commit message (commit-msg hook)

The owner's private terms (username, hostname, real e-mail, real name,
local folder names) come from the environment variable PRIVATE_TERMS (CI,
from the repository secret of that name) or else from the gitignored file
tools/private-terms.local: one term per line, `#` lines ignored, matched
ignoring case. They are never written anywhere else.

A hit is reported as `path:line` (or `commit <sha>` and the message's line)
and never shows the term or the text around it.

Records written before this check existed are left as they are: a file
under sessions/ or docs/prompts/ whose blob is identical to the same path
at the base commit (BASE in config/private-base, the last main commit
before the check) is exempt. This is decided from git's object hashes
alone, so an exempt file is never opened. Every file added or changed after
the base is checked in full. The output counts the exempt files per folder,
and names no spec-side file: hits there are counted, not listed
(CONTRIBUTING.md, "Privacy").

With no terms available the check passes with a note, unless --require is
given (CI requires them). Files not on disk (parts a clean folder leaves
out) are skipped: the check runs where they are.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERMS_FILE = os.path.join(ROOT, "tools", "private-terms.local")
BASE_FILE = os.path.join(ROOT, "config", "private-base")
EXEMPT_DIRS = ("sessions/", "docs/prompts/")
# The spec side's folders: a hit there is counted, never named, because the
# firmware side reads this check's output.
SPEC_DIRS = ("vendor/emulator/", "harness/", "sessions/spec/")


def load_terms():
    text = os.environ.get("PRIVATE_TERMS")
    if not text and os.path.exists(TERMS_FILE):
        with open(TERMS_FILE, encoding="utf-8") as f:
            text = f.read()
    terms = []
    for line in (text or "").splitlines():
        t = line.strip()
        if t and not t.startswith("#"):
            terms.append(t.lower().encode("utf-8"))
    return sorted(set(terms))


def load_base():
    with open(BASE_FILE, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")][0]


def git(*args, raw=False):
    out = subprocess.run(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE,
                         check=True).stdout
    return out if raw else out.decode("utf-8", "replace")


def hit_lines(data, terms):
    """Line numbers (1-based) of data holding any term, ignoring case."""
    low = data.lower()
    lines = set()
    for t in terms:
        start = low.find(t)
        while start != -1:
            lines.add(low.count(b"\n", 0, start) + 1)
            start = low.find(t, start + 1)
    return sorted(lines)


def check_files(paths, read, terms):
    problems = []
    for p in paths:
        data = read(p)
        if data is None:
            continue
        problems += ["%s:%d" % (p, n) for n in hit_lines(data, terms)]
    return problems


def blobs(*args):
    """path -> blob hash, from `git ls-files -s` or `git ls-tree -r` output."""
    out = {}
    for entry in git(*args).split("\0"):
        if "\t" in entry:
            meta, path = entry.split("\t", 1)
            out[path] = meta.split()[1] if args[0] == "ls-files" else meta.split()[2]
    return out


def exempt_paths(base):
    """Tracked files under EXEMPT_DIRS whose blob in the index is the base
    commit's for that path, and that aren't changed on disk: path -> folder
    label. Only object hashes are compared; no file is read."""
    now = blobs("ls-files", "-s", "-z", "--", *EXEMPT_DIRS)
    then = blobs("ls-tree", "-r", "-z", base, "--", *EXEMPT_DIRS)
    changed = set(git("ls-files", "-m", "-z", "--", *EXEMPT_DIRS).split("\0"))
    out = {}
    for p, h in now.items():
        if then.get(p) == h and p not in changed:
            out[p] = label(p)
    return out


def label(p):
    parts = p.split("/")
    if parts[0] == "sessions" and len(parts) > 2:
        return "spec-side transcripts" if parts[1] == "spec" else "sessions/" + parts[1]
    return "/".join(parts[:2]) if parts[0] == "docs" else parts[0]


def read_worktree(p):
    full = os.path.join(ROOT, p)
    if not os.path.isfile(full) or os.path.islink(full):
        return None
    with open(full, "rb") as f:
        return f.read()


def read_staged(p):
    try:
        return git("show", ":" + p, raw=True)
    except subprocess.CalledProcessError:
        return None


def check_messages(rng, terms):
    problems = []
    shas = git("rev-list", rng).split() if rng else git("rev-list", "HEAD").split()
    for sha in shas:
        for n in hit_lines(git("log", "-1", "--format=%B", sha, raw=True), terms):
            problems.append("commit %s, message line %d" % (sha[:12], n))
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--range", default=None,
                    help="commits whose messages to check (default: all of HEAD's history)")
    ap.add_argument("--staged", action="store_true", help="check the staged files only")
    ap.add_argument("--message-file", help="check one commit message file only")
    ap.add_argument("--require", action="store_true", help="fail when no terms are available")
    a = ap.parse_args()

    terms = load_terms()
    if not terms:
        print("private-terms check: no terms (PRIVATE_TERMS or tools/private-terms.local)")
        return 1 if a.require else 0

    if a.message_file:
        with open(a.message_file, "rb") as f:
            text = b"\n".join(l for l in f.read().split(b"\n") if not l.startswith(b"#"))
        problems = ["commit message line %d" % n for n in hit_lines(text, terms)]
    elif a.staged:
        paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split("\0")
        problems = check_files([p for p in paths if p], read_staged, terms)
    else:
        base = load_base()
        exempt = exempt_paths(base)
        paths = [p for p in git("ls-files", "-z").split("\0") if p and p not in exempt]
        problems = check_files(paths, read_worktree, terms)
        problems += check_messages(a.range, terms)
        counts = {}
        for where in exempt.values():
            counts[where] = counts.get(where, 0) + 1
        print("exempt, unchanged since base %s: %s" % (base[:12], ", ".join(
            "%s %d" % (k, counts[k]) for k in sorted(counts)) or "none"))

    spec_hits = [p for p in problems if p.startswith(SPEC_DIRS)]
    for p in problems:
        if p not in spec_hits:
            print("private term at " + p)
    if spec_hits:
        print("private terms in spec-side files: %d line(s) (not named here)" % len(spec_hits))
    print("private-terms check: %d term(s); %s" % (len(terms), "FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
