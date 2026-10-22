#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Archives a finished session's transcript into sessions/ (R-CLEAN-3).

  archive-session.py TRANSCRIPT.jsonl --role clean|spec [--out sessions/<role>]

Run it at the start of the next session (never on the live session). A
clean session archives only clean sessions; a spec session may archive
either (sessions/README.md). It copies the transcript to
`sessions/<role>/<date>-<role>-<id>.jsonl` (the date is
the UTC date of its first entry), along with any subagent transcripts
(`<id>/subagents/*.jsonl` next to it) into `<same name>.subagents/`. It
redacts:
  - tokens and keys (GitHub, Anthropic, AWS, bearer tokens, private keys);
  - e-mail addresses, except no-reply addresses;
  - account and organisation IDs;
  - private paths: home folders become `~`, and per-user temp folders are
    shortened;
  - the local user names seen in those paths, wherever they appear, and
    `*.local` host names;
  - in clean transcripts only: the lines of a git summary (a merge's
    diffstat, `create mode` and `delete mode` lines) that name files under
    vendor/emulator/, harness/ or sessions/spec/. Each run of such lines
    becomes one note saying how many were removed. A name shortened to
    `.../tail` counts when its tail matches only such files.
It writes `<same name>.REDACTIONS.md` beside the copy, saying what was
redacted and how many times, with the SHA-256 of the original and of the
copy. Every redacted line must still parse as JSON. It refuses to overwrite
an existing archive.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

RULES = [
    ("private key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----.*?-----END[A-Z ]*PRIVATE KEY-----"),
     "[REDACTED:private-key]"),
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
     "[REDACTED:github-token]"),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}"), "[REDACTED:anthropic-key]"),
    ("AWS key ID", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED:aws-key]"),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*"), "Bearer [REDACTED]"),
    ("account or organisation ID",
     re.compile(r'("(?:owner)?(?:[Aa]ccount|[Oo]rganization)(?:Uuid|Id|UUID|_uuid|_id)"\s*:\s*")[^"]+(")'),
     r"\1[REDACTED:account-id]\2"),
    ("e-mail address",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
     "[REDACTED:email]"),
    ("home folder path", re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+(?=/|\b)"), "~"),
    ("per-user temp path", re.compile(r"/private/tmp/claude-\d+/|/tmp/claude-\d+/"), "/tmp/claude-UID/"),
    ("project folder name", re.compile(r"-Users-[A-Za-z0-9._]+-"), "-HOME-"),
]
# no-reply addresses are kept: they identify authors without being private
KEEP_EMAIL = re.compile(r"noreply@|@users\.noreply\.github\.com")


HOST_RULE = ("host name", re.compile(r"\b[A-Za-z0-9-]+\.local\b(?!\.)"), "[REDACTED:host]")
HOME_USER = re.compile(r"/(?:Users|home)/([A-Za-z0-9._-]+)/")


def user_rules(path):
    """Rules for the local user names seen in home-folder paths, so they are
    also redacted where they appear alone (e.g. in `ls -l` output)."""
    names = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            names.update(HOME_USER.findall(line))
    names -= {"Shared", "runner"}
    return [("local user name", re.compile(r"\b%s\b" % re.escape(n)), "[REDACTED:user]")
            for n in sorted(names)]


SPEC_DIRS = ("vendor/emulator/", "harness/", "sessions/spec/")
# One line of a git summary inside a JSON string: " path | 12 +-" or
# " create mode 100644 path". Lines are split on the JSON escape \n.
STAT_LINE = re.compile(r'^ (?:(?:create|delete) mode \d{6} (?P<m>[^\s"\\]+)'
                       r'|(?P<s>[^\s"\\]+) +\| +(?:\d+|Bin)\b[^"\\]*)$')
SPEC_NOTE = " [redacted: %d line(s) naming spec-side files]"


def spec_names():
    """Every path in this checkout's history (names only: a clean folder has
    them without the spec-side files' contents)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        out = subprocess.run(["git", "-C", root, "log", "--all", "--name-only", "--format="],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, env=dict(os.environ, GIT_NO_LAZY_FETCH="1")).stdout
    except OSError:
        out = ""
    return set(n for n in out.splitlines() if n)


def names_spec_file(path, names):
    if path.startswith(SPEC_DIRS):
        return True
    if path.startswith(".../"):
        tail = path[3:]
        hits = [n for n in names if ("/" + n).endswith(tail)]
        return bool(hits) and all(n.startswith(SPEC_DIRS) for n in hits)
    return False


def redact_spec_paths(line, counts, names):
    parts = re.split(r"(?<!\\)\\n", line)
    if len(parts) < 2:
        return line
    out, run = [], 0
    for part in parts + [None]:
        m = STAT_LINE.match(part) if part is not None else None
        if m and names_spec_file(m.group("m") or m.group("s"), names):
            run += 1
            continue
        if run:
            out.append(SPEC_NOTE % run)
            counts["spec-side file name in a git summary (lines)"] = \
                counts.get("spec-side file name in a git summary (lines)", 0) + run
            run = 0
        if part is not None:
            out.append(part)
    return "\\n".join(out)


def redact_line(line, counts, extra=(), spec_files=None):
    for name, rx, repl in list(RULES) + [HOST_RULE] + list(extra):
        if name == "e-mail address":
            def sub(m):
                if KEEP_EMAIL.search(m.group(0)):
                    return m.group(0)
                counts[name] = counts.get(name, 0) + 1
                return repl
            line = rx.sub(sub, line)
            continue
        line, n = rx.subn(repl, line)
        if n:
            counts[name] = counts.get(name, 0) + n
    if spec_files is not None:
        line = redact_spec_paths(line, counts, spec_files)
    return line


def redact_file(src, dst, counts, extra=(), spec_files=None):
    h_src, h_dst = hashlib.sha256(), hashlib.sha256()
    with open(src, "rb") as f, open(dst, "wb") as out:
        for n, raw in enumerate(f, 1):
            h_src.update(raw)
            line = redact_line(raw.decode("utf-8"), counts, extra, spec_files)
            if line.strip():
                try:
                    json.loads(line)
                except ValueError as e:
                    raise SystemExit("%s:%d: redaction broke the JSON (%s)" % (src, n, e))
            data = line.encode("utf-8")
            h_dst.update(data)
            out.write(data)
    return h_src.hexdigest(), h_dst.hexdigest()


def first_date(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                ts = json.loads(line).get("timestamp")
            except ValueError:
                continue
            if ts:
                return ts[:10]
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript")
    ap.add_argument("--role", required=True, choices=("clean", "spec"))
    ap.add_argument("--out", default=None,
                    help="where to put it (default: sessions/<role>/)")
    ap.add_argument("--archived-by", default="",
                    help="the session doing the archiving, for the note")
    a = ap.parse_args()
    if a.out is None:
        a.out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "sessions", a.role)

    src = a.transcript
    sid = os.path.basename(src)[:-len(".jsonl")]
    name = "%s-%s-%s" % (first_date(src), a.role, sid)
    dst = os.path.join(a.out, name + ".jsonl")
    if os.path.exists(dst):
        raise SystemExit("refusing to overwrite %s" % dst)
    os.makedirs(a.out, exist_ok=True)

    counts = {}
    files = [(src, dst)]
    subs = sorted(glob.glob(os.path.join(os.path.dirname(src), sid, "subagents", "*.jsonl")))
    if subs:
        os.makedirs(os.path.join(a.out, name + ".subagents"))
        files += [(s, os.path.join(a.out, name + ".subagents", os.path.basename(s))) for s in subs]
    extra = []
    for s, _ in files:
        extra += [r for r in user_rules(s) if r[1].pattern not in [e[1].pattern for e in extra]]
    spec_files = spec_names() if a.role == "clean" else None
    hashes = []
    for s, d in files:
        hs, hd = redact_file(s, d, counts, extra, spec_files)
        hashes.append((os.path.relpath(d, a.out), hs, hd))

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # REUSE-IgnoreStart
    note = ["<!--", "SPDX-License-Identifier: MIT",
            "SPDX-FileCopyrightText: 2026 japes98", "-->", "",
            # REUSE-IgnoreEnd
            "# Redactions: %s" % name, "",
            "- Session: `%s` (%s side)" % (sid, a.role),
            "- Archived: %s%s" % (now, (" by " + a.archived_by) if a.archived_by else ""),
            "- Tool: tools/archive-session.py (its RULES list is the full redaction policy)",
            "", "## What was redacted", ""]
    if counts:
        note += ["| Kind | Count |", "|------|-------|"]
        note += ["| %s | %d |" % (k, counts[k]) for k in sorted(counts)]
    else:
        note.append("Nothing.")
    note += ["", "Nothing else was changed. Redactions replace text in place, so every line",
             "is still the same JSON entry.", "",
             "## Files", "",
             "| File | SHA-256 of the original | SHA-256 of this copy |",
             "|------|-------------------------|----------------------|"]
    note += ["| `%s` | `%s` | `%s` |" % h for h in hashes]
    note.append("")
    with open(os.path.join(a.out, name + ".REDACTIONS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(note))
    print("archived %s -> %s" % (src, dst))
    for k in sorted(counts):
        print("  redacted %-28s %d" % (k, counts[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
