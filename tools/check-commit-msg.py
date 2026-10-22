#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks commit messages against .gitmessage (R-PROC-1, check C-COMMIT-MSG).

  check-commit-msg.py --file MSGFILE     one message (the commit-msg hook;
                                         lines starting with # are removed)
  check-commit-msg.py --range A..B       every commit in A..B
  check-commit-msg.py --range ..B        every commit reachable from B
  check-commit-msg.py --commit SHA       one commit

Merge commits are exempt (their pull request carries the sections) and are
listed as such. Exit status 1 if any message fails.
"""
import argparse
import re
import subprocess
import sys

FIELDS = ["What", "Why", "How", "Result", "Sources", "Exposure"]
SUBJECT_RE = re.compile(r"^[a-z0-9][a-z0-9/_.-]*: \S.*$")
FIELD_RE = re.compile(r"^(%s):(.*)$" % "|".join(FIELDS))
TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z-]*): (.+)$")
KNOWN_TRAILERS = ("Model", "Claude-Session", "Co-Authored-By", "Signed-off-by")
MAX_SUBJECT = 100


def strip_comments(text):
    return "\n".join(l for l in text.splitlines() if not l.startswith("#"))


def validate(message, author=""):
    """Returns a list of problems; empty means the message is fine."""
    problems = []
    lines = message.strip("\n").splitlines()
    if not lines:
        return ["empty message"]
    subject = lines[0]
    if not SUBJECT_RE.match(subject):
        problems.append("subject must look like '<area>: <what changed>' "
                        "with a lower-case area: %r" % subject)
    if len(subject) > MAX_SUBJECT:
        problems.append("subject longer than %d characters" % MAX_SUBJECT)
    if len(lines) < 2 or lines[1].strip():
        problems.append("line 2 must be empty")

    values = {}
    order = []
    current = None
    trailers = {}
    for line in lines[2:]:
        m = FIELD_RE.match(line)
        if m:
            current = m.group(1)
            if current in values:
                problems.append("field %s: appears twice" % current)
            order.append(current)
            values[current] = m.group(2).strip()
            continue
        if current and (line.startswith(" ") or line.startswith("\t")):
            values[current] = (values[current] + " " + line.strip()).strip()
            continue
        t = TRAILER_RE.match(line)
        if t and (current == FIELDS[-1] or t.group(1) in KNOWN_TRAILERS):
            trailers.setdefault(t.group(1), []).append(t.group(2).strip())
            current = None
            continue
        if line.strip():
            current = None
    for f in FIELDS:
        if f not in values:
            problems.append("field %s: missing" % f)
        elif not values[f]:
            problems.append("field %s: empty" % f)
    present = [f for f in order if f in FIELDS]
    if present != [f for f in FIELDS if f in present]:
        problems.append("fields out of order: %s (want %s)"
                        % (", ".join(present), ", ".join(FIELDS)))

    agent = ("claude" in author.lower()
             or "Claude-Session" in trailers
             or any("claude" in v.lower()
                    for v in trailers.get("Co-Authored-By", [])))
    if agent:
        for t in ("Model", "Claude-Session"):
            if t not in trailers:
                problems.append("agent-written commit needs a %s: trailer" % t)
    return problems


def git(*args):
    return subprocess.run(["git"] + list(args), check=True,
                          stdout=subprocess.PIPE, universal_newlines=True).stdout


def commits_in(rng):
    if rng.startswith("..") or re.match(r"^0{40}\.\.", rng):
        return git("rev-list", "--reverse", rng.split("..", 1)[1]).split()
    return git("rev-list", "--reverse", rng).split()


def check_commit(sha):
    parents = git("rev-list", "--parents", "-n", "1", sha).split()[1:]
    subject = git("log", "-1", "--format=%s", sha).strip()
    if len(parents) > 1:
        print("EXEMPT %s (merge) %s" % (sha[:12], subject))
        return True
    message = git("log", "-1", "--format=%B", sha)
    author = git("log", "-1", "--format=%an <%ae>", sha).strip()
    problems = validate(message, author)
    if problems:
        print("FAIL   %s %s" % (sha[:12], subject))
        for p in problems:
            print("         - " + p)
        return False
    print("OK     %s %s" % (sha[:12], subject))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--range")
    g.add_argument("--commit")
    a = ap.parse_args()

    if a.file:
        with open(a.file) as f:
            text = strip_comments(f.read())
        problems = validate(text, git("var", "GIT_AUTHOR_IDENT").strip())
        if problems:
            print("Commit message doesn't follow .gitmessage:", file=sys.stderr)
            for p in problems:
                print("  - " + p, file=sys.stderr)
            return 1
        return 0

    shas = [a.commit] if a.commit else commits_in(a.range)
    if not shas:
        print("no commits in range %s" % a.range)
        return 0
    ok = all([check_commit(s) for s in shas])
    print("%d commit(s) checked: %s" % (len(shas), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
