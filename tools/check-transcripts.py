#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks archived session transcripts (R-CLEAN-1, R-CLEAN-3, R-CLEAN-5;
check C-TRANSCRIPTS).

  check-transcripts.py [SESSIONS_DIR]        (default: sessions/)

Each archived session is `<date>-<role>-<id>.jsonl` (role clean or spec),
with its redaction note `<same name>.REDACTIONS.md` beside it, and any
subagent transcripts in `<same name>.subagents/*.jsonl`.

For every transcript:
  - the SessionStart banner (tools/session-banner.sh) must be there, with
    `status: OK` and exit code 0. Any CONFIG MISMATCH or failed SessionStart
    hook fails. (EXEMPT_NO_BANNER lists the only sessions allowed to have
    none, and why.)
For every clean-side transcript, including its subagents:
  - every file read, write, search, web fetch, web search and shell command
    is listed, and any that touches FORBIDDEN fails.

The format is Claude Code's JSONL transcript: tool calls are `tool_use`
blocks inside `type: "assistant"` entries; hook output is an `attachment`
entry with `hookEvent: "SessionStart"`, `stdout` and `exitCode` (PROVENANCE
P-6). Other entries are not inspected for tool use.
"""
import glob
import json
import os
import re
import sys

NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(clean|spec)-([0-9a-f-]{36})\.jsonl$")
BANNER_START = "=== small-beeps session banner v1 ==="

EXEMPT_NO_BANNER = {
    "36860ab8-77fd-4fd6-aa1d-2063c15a5548":
        "M0a, the first session: it began before tools/session-banner.sh and "
        "its hook existed (docs/EXPOSURE.md, Addendum 2 step 5)",
}

# Mirrors CONTRIBUTING.md, "Firmware side never opens, fetches, searches or
# quotes". Each pattern is matched, case-insensitively, against the targets
# of reads, searches, fetches and shell commands (not against the contents
# a session writes).
FORBIDDEN = [
    ("Felucca and firmwares built on it", r"felucca|hortator|ghoulbox|melodee|\bskiff\b"),
    ("hugelton (Felucca's author)", r"hugelton"),
    ("dinghy", r"dinghy|zvenson"),
    ("FM-1 SID firmware", r"fm1-sid"),
    ("emulator probe source", r"probes/lcdtest\.c"),
    ("F-Emulator / fm1-emu repository", r"fm1-emu|f-emulator"),
    ("emulator crates", r"\bcrates/fm1-"),
    # A path into the folder, or the folder itself as a whole word.
    ("vendor/emulator/ (spec side)", r"(^|[\s\"'=:/])vendor/emulator(/|[\s\"']|$)"),
    ("harness/ source (spec side)", r"(^|[\s\"'=:/])harness(/|[\s\"']|$)"),
    ("thefirmwarehub.com", r"thefirmwarehub\.com"),
    ("FM-1-RE firmware images or disassembly",
     r"fm-1-re.*(firmware-images|disasm|disassembl|ghidra|\.idb\b|\.i64\b|functions)"
     r"|firmware-images/"),
    ("M-VAVE stock firmware", r"m-?vave.*\.(fwsc|bin|ufw|hex)\b"),
]
FORBIDDEN_RE = [(why, re.compile(p, re.IGNORECASE)) for why, p in FORBIDDEN]


def targets(name, inp):
    """Returns (kind, target) pairs for one tool call."""
    s = lambda k: str(inp.get(k, "")) if inp.get(k) is not None else ""
    if name == "Read":
        return [("read", s("file_path"))]
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return [("write", s("file_path") or s("notebook_path"))]
    if name == "Grep":
        return [("search", " ".join(x for x in (s("path"), s("glob"), s("pattern")) if x))]
    if name == "Glob":
        return [("search", " ".join(x for x in (s("path"), s("pattern")) if x))]
    if name == "WebFetch":
        return [("fetch", s("url"))]
    if name == "WebSearch":
        return [("web-search", s("query"))]
    if name == "Bash":
        return [("shell", s("command"))]
    if name in ("Agent", "Task"):
        return [("agent", s("description"))]
    if name.startswith("mcp__"):
        out = []
        for k, v in sorted(inp.items()):
            if isinstance(v, str) and (k in ("url", "path", "file_path", "query")
                                       or v.startswith("http")):
                out.append(("mcp", "%s=%s" % (k, v)))
        return out
    return []


def forbidden_hits(kind, target):
    if kind in ("write", "agent"):
        return []  # what a session writes isn't a read; agents have own transcripts
    return [why for why, rx in FORBIDDEN_RE if rx.search(target)]


def load(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except ValueError as e:
                    raise SystemExit("%s:%d: not JSON (%s)" % (path, n, e))
    return entries


def banners(entries):
    """Yields (exit_code, stdout) for every SessionStart hook run."""
    for e in entries:
        a = e.get("attachment") if e.get("type") == "attachment" else None
        if isinstance(a, dict) and a.get("hookEvent") == "SessionStart":
            yield a.get("exitCode"), a.get("stdout") or a.get("content") or "", a.get("stderr") or ""


def tool_calls(entries):
    for e in entries:
        if e.get("type") != "assistant":
            continue
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name", ""), block.get("input") or {}
    # Files attached to a user message (e.g. @-mentions) are reads too.
    for e in entries:
        a = e.get("attachment") if e.get("type") == "attachment" else None
        if isinstance(a, dict) and a.get("type") in ("file", "directory", "opened_file_in_ide",
                                                       "selected_lines_in_ide", "compact_file_reference"):
            yield "Read", {"file_path": a.get("filename") or a.get("path") or ""}


def check_banner(sid, entries, problems):
    runs = list(banners(entries))
    ok = 0
    for code, out, err in runs:
        if "CONFIG MISMATCH" in out or "CONFIG MISMATCH" in err:
            problems.append("CONFIG MISMATCH in SessionStart banner")
        elif BANNER_START in out:
            if code not in (0, None) or "status: OK" not in out:
                problems.append("SessionStart banner without status OK (exit %s)" % code)
            else:
                ok += 1
        elif code not in (0, None):
            problems.append("a SessionStart hook failed (exit %s)" % code)
    if ok:
        return "banner OK (%d)" % ok
    if sid in EXEMPT_NO_BANNER:
        return "no banner, exempt: " + EXEMPT_NO_BANNER[sid]
    problems.append("no SessionStart banner")
    return "no banner"


def check_session(path):
    base = os.path.basename(path)
    m = NAME_RE.match(base)
    if not m:
        return ["file name doesn't match <date>-<role>-<id>.jsonl"], []
    date, role, sid = m.groups()
    problems = []
    lines = []
    if not os.path.exists(path[:-len(".jsonl")] + ".REDACTIONS.md"):
        problems.append("redaction note %s.REDACTIONS.md is missing" % base[:-6])
    entries = load(path)
    lines.append("%s (%s side, session %s, %s): %s"
                 % (base, role, sid, date, check_banner(sid, entries, problems)))
    if role == "clean":
        files = [path] + sorted(glob.glob(path[:-len(".jsonl")] + ".subagents/*.jsonl"))
        count = 0
        for f in files:
            sub = "" if f == path else " [subagent %s]" % os.path.basename(f)
            for name, inp in tool_calls(load(f) if f != path else entries):
                for kind, target in targets(name, inp):
                    count += 1
                    hits = forbidden_hits(kind, target)
                    shown = target.replace("\n", "\\n")
                    if len(shown) > 240:
                        shown = shown[:240] + "..."
                    lines.append("  %-10s %-9s %s%s" % (kind, name[:9], shown, sub))
                    for why in hits:
                        problems.append("%s %s touches forbidden material (%s): %s"
                                        % (kind, name, why, shown[:120]))
        lines.append("  %d reads, writes, searches, fetches and commands listed" % count)
    return problems, lines


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sessions = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "sessions")
    paths = sorted(glob.glob(os.path.join(sessions, "*.jsonl")))
    failed = False
    for p in paths:
        problems, lines = check_session(p)
        for l in lines:
            print(l)
        for pr in problems:
            print("FAIL %s: %s" % (os.path.basename(p), pr))
        failed = failed or bool(problems)
    print("%d archived transcript(s) checked: %s"
          % (len(paths), "FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
