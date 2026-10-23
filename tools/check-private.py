#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""No private terms in the repository (check C-PRIVATE; R-PUB-3).

  check-private.py [--range RANGE] [--require]   tracked files and commit messages
  check-private.py --staged                      staged files (pre-commit hook)
  check-private.py --message-file FILE           a commit message (commit-msg hook)
  check-private.py --dir DIR [--withhold]        every file under DIR (a record)

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

`--dir` checks every file under a folder about to be published (a test
record, an audit report, a re-check). With `--withhold`, each file holding
a term is deleted and listed, with the SHA-256 of the withheld original, in
DIR/WITHHELD.json; the rest stays, and the exit status is 1 if anything was
withheld. The original is not kept anywhere: the checks are deterministic,
so it can be regenerated and matched against its hash if that is ever
needed. tools/record.py does the same as its check C-RECORD-PRIVATE.

With no terms available the check passes with a note, unless --require is
given (CI requires them). Files not on disk (parts a clean folder leaves
out) are skipped: the check runs where they are.
"""
import argparse
import hashlib
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
def spec_dirs(path=os.path.join(ROOT, "config", "spec-side-folders")):
    """The spec-side folders, each ending in a slash, from
    config/spec-side-folders (since M3: one list for every barrier tool)."""
    with open(path, encoding="utf-8") as f:
        return tuple(l.split("\t")[0] + "/" for l in f if l.strip() and not l.startswith("#"))


SPEC_DIRS = spec_dirs()


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


WITHHELD = "WITHHELD.json"


def withhold(top, terms):
    """Deletes every file under top that holds a term, and writes (or adds
    to) top/WITHHELD.json: one entry per withheld file, its path relative
    to top and the SHA-256 of the original. Returns the new entries."""
    listed = os.path.join(top, WITHHELD)
    old = []
    if os.path.exists(listed):
        with open(listed, encoding="utf-8") as f:
            old = json.load(f).get("withheld", [])
    new = []
    for dirpath, _, names in sorted(os.walk(top)):
        for n in sorted(names):
            full = os.path.join(dirpath, n)
            rel = os.path.relpath(full, top).replace(os.sep, "/")
            if rel == WITHHELD or os.path.islink(full):
                continue
            with open(full, "rb") as f:
                data = f.read()
            if hit_lines(data, terms):
                new.append({"file": rel, "sha256": hashlib.sha256(data).hexdigest()})
                os.remove(full)
    if new:
        with open(listed, "w", encoding="utf-8") as f:
            json.dump({"comment": "Files withheld from this folder because they held one of the "
                                  "owner's private terms (tools/check-private.py, R-PUB-3). Only "
                                  "the name and the SHA-256 of each original are kept.",
                       "withheld": old + new}, f, indent=2)
            f.write("\n")
    return new


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
    """A staged file's contents, or None. Never fetches: in a blob-less
    clean folder a merge stages spec-side files whose contents are not
    there, and with lazy fetching on, reading them would download them
    (found in M2). CI's full scan reads every tracked file."""
    out = subprocess.run(["git", "show", ":" + p], cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, env=dict(os.environ, GIT_NO_LAZY_FETCH="1"))
    return out.stdout if out.returncode == 0 else None


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
    ap.add_argument("--dir", help="check every file under this folder (a record about to be published)")
    ap.add_argument("--withhold", action="store_true",
                    help="with --dir: delete each file holding a term, listing it in WITHHELD.json")
    ap.add_argument("--require", action="store_true", help="fail when no terms are available")
    a = ap.parse_args()

    terms = load_terms()
    if not terms:
        print("private-terms check: no terms (PRIVATE_TERMS or tools/private-terms.local)")
        return 1 if a.require else 0

    if a.dir and a.withhold:
        gone = withhold(a.dir, terms)
        for g in gone:
            print("withheld %s (sha256 %s)" % (g["file"], g["sha256"]))
        print("private-terms check of %s: %d term(s); %s" % (
            a.dir, len(terms), "%d file(s) WITHHELD" % len(gone) if gone else "PASS"))
        return 1 if gone else 0
    if a.dir:
        paths = []
        for dirpath, _, names in os.walk(a.dir):
            paths += [os.path.join(dirpath, n) for n in names]
        problems = check_files(sorted(os.path.relpath(p, a.dir) for p in paths),
                               lambda p: open(os.path.join(a.dir, p), "rb").read(), terms)
    elif a.message_file:
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
