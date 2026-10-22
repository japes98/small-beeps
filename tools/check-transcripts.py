#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks archived session transcripts (R-CLEAN-1, R-CLEAN-3, R-CLEAN-5;
check C-TRANSCRIPTS).

  check-transcripts.py [SESSIONS_DIR]        (default: sessions/)

Each archived session is `<role>/<date>-<role>-<id>.jsonl` under
SESSIONS_DIR (role clean or spec, and the folder must match the name), with
its redaction note `<same name>.REDACTIONS.md` beside it, and any subagent
transcripts in `<same name>.subagents/*.jsonl`.

Spec-side transcripts (`spec/`) are left out of clean folders. When `spec/`
isn't on disk, they are skipped, never looked for elsewhere, and the output
says so.

For every transcript:
  - the SessionStart banner (tools/session-banner.sh) must be there, with
    `status: OK` and exit code 0. Any CONFIG MISMATCH or failed SessionStart
    hook fails. (EXEMPT_NO_BANNER lists the only sessions allowed to have
    none, and why.)
For every clean-side transcript, including its subagents:
  - every file read, write, search, web fetch, web search and shell command
    is listed, and any that touches FORBIDDEN fails, unless that exact tool
    call is in sessions/REVIEWED.json (a reviewed false positive, such as a
    shell command that only writes a document naming a forbidden folder).
    Matching is on text, so it errs towards flagging, with one narrow
    exception for the three spec-side folder rules (EXEMPT_PATHS): the body
    of a quoted heredoc fed to `python3 -` is left out of their matching
    when it is code that provably opens nothing but sessions/REVIEWED.json
    and files under sessions/clean/ (exempt_heredoc). Every other rule, and
    the rest of the command, is still matched as text.
  - A REVIEWED.json entry may be marked `superseded` (the exception above
    now clears its call). It no longer clears anything, and the check fails
    if its call is still flagged, so the mark can't be wrong.

The output never quotes a transcript: calls are listed by file, entry
(the transcript's line number), tool and tool-call ID, and hits by rule ID
(FORBIDDEN), so nothing a session typed reaches a log or a record.

The format is Claude Code's JSONL transcript: tool calls are `tool_use`
blocks inside `type: "assistant"` entries; hook output is an `attachment`
entry with `hookEvent: "SessionStart"`, `stdout` and `exitCode` (PROVENANCE
P-6). Other entries are not inspected for tool use.
"""
import ast
import glob
import json
import os
import posixpath
import re
import sys

NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(clean|spec)-([0-9a-f-]{36})\.jsonl$")
BANNER_START = "=== small-beeps session banner v1 ==="

EXEMPT_NO_BANNER = {
    "36860ab8-77fd-4fd6-aa1d-2063c15a5548":
        "M0a, the first session: it began before tools/session-banner.sh and "
        "its hook existed (docs/EXPOSURE.md, Addendum 2 step 5)",
    "ddebd686-9190-4fa3-b217-30d0a98fda69":
        "a one-prompt `claude -p` run started by M0a in its scratch folder to "
        "learn how hook output is stored; its only hook printed a test marker, "
        "and it made no tool calls (docs/EXPOSURE.md, session M0a)",
    "e74c69f7-ff95-4dcc-bf7a-9a980e62a6f9":
        "M0b, the first spec-side session: it began under the owner's hand-made "
        "settings, before tools/spec-setup.sh installed the banner hook in its "
        "folder (docs/EXPOSURE.md, session M0b)",
}
ROLES = ("clean", "spec")

# Mirrors CONTRIBUTING.md, "Firmware side never opens, fetches, searches or
# quotes". Each pattern is matched, case-insensitively, against the targets
# of reads, searches, fetches and shell commands (not against the contents
# a session writes).
FORBIDDEN = [
    ("F-FELUCCA", "Felucca and firmwares built on it", r"felucca|hortator|ghoulbox|melodee|\bskiff\b"),
    ("F-HUGELTON", "hugelton (Felucca's author)", r"hugelton"),
    ("F-DINGHY", "dinghy", r"dinghy|zvenson"),
    ("F-FM1-SID", "FM-1 SID firmware", r"fm1-sid"),
    ("F-PROBE", "emulator probe source", r"probes/lcdtest\.c"),
    ("F-EMU-REPO", "F-Emulator / fm1-emu repository", r"fm1-emu|f-emulator"),
    ("F-EMU-CRATES", "emulator crates", r"\bcrates/fm1-"),
    # A path into the folder, or the folder itself as a whole word, ended by
    # whitespace, a quote or a shell operator or bracket (since M2, so that
    # `D=harness; ls $D` is caught too).
    ("F-VENDOR-EMU", "vendor/emulator/ (spec side)",
     r"(^|[\s\"'=:/;&|<>(){}`])vendor/emulator(/|[\s\"';&|<>(){}`]|$)"),
    ("F-HARNESS", "harness/ source (spec side)",
     r"(^|[\s\"'=:/;&|<>(){}`])harness(/|[\s\"';&|<>(){}`]|$)"),
    ("F-FWHUB", "thefirmwarehub.com", r"thefirmwarehub\.com"),
    ("F-SPEC-SESSIONS", "spec-side session transcripts", r"sessions/spec(/|[\s\"';&|<>(){}`]|$)"),
    ("F-RE-FIRMWARE", "FM-1-RE firmware images or disassembly",
     r"fm-1-re.*(firmware-images|disasm|disassembl|ghidra|\.idb\b|\.i64\b|functions)"
     r"|firmware-images/"),
    ("F-STOCK", "M-VAVE stock firmware", r"m-?vave.*\.(fwsc|bin|ufw|hex)\b"),
]
FORBIDDEN_RE = [(rid, why, re.compile(p, re.IGNORECASE)) for rid, why, p in FORBIDDEN]
RULE_ID = {why: rid for rid, why, _ in FORBIDDEN}
# The rules a heredoc's body can be cleared of (exempt_heredoc).
FOLDER_RULES = ("F-VENDOR-EMU", "F-HARNESS", "F-SPEC-SESSIONS")


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


# What an exempt heredoc may open: the reviewed list and archived clean
# transcripts, nothing else.
EXEMPT_PATHS = ("sessions/REVIEWED.json", "sessions/clean/")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"])([A-Za-z_][A-Za-z0-9_]*)\1")
PYTHON_STDIN = re.compile(r"^\s*python3?(\.\d+)?(\s+-[IEsSBu]+)*\s+-\s*$")
# Names a cleared heredoc may call; anything else (exec, eval, getattr,
# __import__, compile, ...) means no exemption. Only json and re may be
# imported, so no module that reaches files or processes is in reach.
SAFE_CALLS = {"print", "len", "any", "all", "sorted", "set", "list", "dict", "tuple",
              "str", "int", "bool", "repr", "enumerate", "range", "isinstance",
              "min", "max", "sum", "zip", "open"}
SAFE_IMPORTS = {"json", "re"}


def allowed_path(path):
    if not isinstance(path, str) or path.startswith("/") or "\\" in path:
        return False
    norm = posixpath.normpath(path)
    if norm != path.rstrip("/") or ".." in norm.split("/"):
        return False
    return norm == EXEMPT_PATHS[0] or (norm.startswith(EXEMPT_PATHS[1]) and norm != EXEMPT_PATHS[1])


def exempt_heredoc(code):
    """True when Python code provably opens only EXEMPT_PATHS: it imports
    only SAFE_IMPORTS, calls only SAFE_CALLS and methods (no dunder names),
    and every open() names a path that is a literal, or a variable bound
    exactly once to a literal, under EXEMPT_PATHS. Strings it uses
    otherwise are data (e.g. the text it writes)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    bound = {}
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.For, ast.comprehension)):
            targets = [node.target]
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            targets = [node.optional_vars]
        elif isinstance(node, (ast.FunctionDef, ast.Lambda, ast.Global, ast.Nonlocal)):
            return False
        for t in targets:
            for n in ast.walk(t):
                if isinstance(n, ast.Name):
                    single = (isinstance(node, ast.Assign) and len(node.targets) == 1
                              and t is n and isinstance(node.value, ast.Constant))
                    bound.setdefault(n.id, []).append(node.value.value if single else None)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name not in SAFE_IMPORTS or a.asname for a in node.names):
                return False
        elif isinstance(node, ast.ImportFrom):
            return False
        elif isinstance(node, ast.Name) and node.id.startswith("_"):
            return False
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return False
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                if f.id not in SAFE_CALLS or f.id in bound:
                    return False
                if f.id == "open":
                    if not node.args or any(k.arg in ("file",) for k in node.keywords):
                        return False
                    a = node.args[0]
                    if isinstance(a, ast.Constant):
                        path = a.value
                    elif isinstance(a, ast.Name) and len(bound.get(a.id, [])) == 1:
                        path = bound[a.id][0]
                    else:
                        return False
                    if not allowed_path(path):
                        return False
            elif not isinstance(f, ast.Attribute):
                return False
    return True


def shell_parts(command):
    """Splits a shell command into (rest, cleared): rest is the command
    with the bodies of exempt heredocs taken out, matched against the
    folder rules; cleared says whether any body was taken out. A heredoc is
    exempt only when its delimiter is quoted (so the shell expands nothing
    in it), it is the only one on its line, the command it feeds is
    `python3 -` alone, and its body passes exempt_heredoc."""
    lines = command.split("\n")
    keep, i, cleared = [], 0, False
    while i < len(lines):
        line = lines[i]
        keep.append(line)
        i += 1
        ops = list(HEREDOC_RE.finditer(line))
        if len(ops) != 1:
            continue
        delim, strip = ops[0].group(2), line[ops[0].start():].startswith("<<-")
        body = []
        while i < len(lines) and (lines[i].lstrip("\t") if strip else lines[i]) != delim:
            body.append(lines[i])
            i += 1
        segment = re.split(r"&&|\|\||[;|(]", line[:ops[0].start()])[-1]
        if PYTHON_STDIN.match(segment) and exempt_heredoc("\n".join(body)):
            cleared = True
        else:
            keep.extend(body)
        if i < len(lines):
            keep.append(lines[i])
            i += 1
    return "\n".join(keep), cleared


def forbidden_hits(kind, target):
    """Rule IDs a call's target matches, and whether a heredoc exemption
    cleared any folder rule."""
    if kind in ("write", "agent"):
        return [], False  # what a session writes isn't a read; agents have own transcripts
    hits = [rid for rid, _, rx in FORBIDDEN_RE if rx.search(target)]
    if kind != "shell" or not any(r in FOLDER_RULES for r in hits):
        return hits, False
    rest, cleared = shell_parts(target)
    if not cleared:
        return hits, False
    kept = [r for r in hits if r not in FOLDER_RULES
            or any(rid == r and rx.search(rest) for rid, _, rx in FORBIDDEN_RE)]
    return kept, kept != hits


def load(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    e = json.loads(line)
                    if isinstance(e, dict):
                        e["_line"] = n  # the entry's line, for listing it
                    entries.append(e)
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
                yield (e.get("_line", 0), block.get("id", ""), block.get("name", ""),
                       block.get("input") or {})
    # Files attached to a user message (e.g. @-mentions) are reads too.
    for e in entries:
        a = e.get("attachment") if e.get("type") == "attachment" else None
        if isinstance(a, dict) and a.get("type") in ("file", "directory", "opened_file_in_ide",
                                                       "selected_lines_in_ide", "compact_file_reference"):
            yield (e.get("_line", 0), e.get("uuid", ""), "Read",
                   {"file_path": a.get("filename") or a.get("path") or ""})


def load_reviewed(sessions_dir):
    """sessions/REVIEWED.json: hits that people reviewed and found not to be
    a touch of forbidden material (e.g. a shell command that only *writes*
    a document naming a forbidden folder). Each entry names the session, the
    tool call's ID, the matched rule and the reason. It is added by pull
    request, so the owner's signed merge approves it. An entry with a
    `superseded` note is kept for history but clears nothing: its value is
    a dict {"superseded": note} instead of the reason."""
    path = os.path.join(sessions_dir, "REVIEWED.json")
    if not os.path.exists(path) and os.path.basename(sessions_dir.rstrip("/")) in ROLES:
        path = os.path.join(os.path.dirname(sessions_dir.rstrip("/")), "REVIEWED.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    reviewed = {}
    for r in data.get("reviewed", []):
        if not (r.get("session") and r.get("tool_use_id") and r.get("rule") and r.get("reason")):
            raise SystemExit("%s: every entry needs session, tool_use_id, rule and reason" % path)
        key = (r["session"], r["tool_use_id"], r["rule"])
        reviewed[key] = {"superseded": r["superseded"]} if r.get("superseded") else r["reason"]
    return reviewed


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


def check_session(path, reviewed=None):
    reviewed = reviewed if reviewed is not None else load_reviewed(os.path.dirname(path))
    base = os.path.basename(path)
    m = NAME_RE.match(base)
    if not m:
        return ["file name doesn't match <date>-<role>-<id>.jsonl"], []
    date, role, sid = m.groups()
    problems = []
    lines = []
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if folder in ROLES and folder != role:
        problems.append("a %s-side transcript in %s/" % (role, folder))
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
            for line_no, tid, name, inp in tool_calls(load(f) if f != path else entries):
                for kind, target in targets(name, inp):
                    count += 1
                    hits, cleared = forbidden_hits(kind, target)
                    where = "entry %d %s %s %s%s" % (line_no, kind, name, tid, sub)
                    lines.append("  " + where)
                    if cleared:
                        lines.append("    CLEARED folder rules: its heredoc opens only %s"
                                     % " and ".join(EXEMPT_PATHS))
                    for rid in hits:
                        why = next(w for r, w, _ in FORBIDDEN_RE if r == rid)
                        entry = reviewed.get((sid, tid, why))
                        if isinstance(entry, str):
                            lines.append("    REVIEWED %s" % rid)
                        elif entry is not None:
                            problems.append("%s: %s, but its REVIEWED.json entry is marked "
                                            "superseded" % (where, rid))
                        else:
                            problems.append("%s touches forbidden material (%s)" % (where, rid))
        lines.append("  %d reads, writes, searches, fetches and commands listed" % count)
    return problems, lines


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sessions = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "sessions")
    reviewed = load_reviewed(sessions)
    failed = False
    # anywhere else under sessions/ (an auditor's transcript, say: those are never archived here)
    for stray in sorted(glob.glob(os.path.join(sessions, "**", "*.jsonl"), recursive=True)):
        rel = os.path.relpath(stray, sessions).replace(os.sep, "/")
        if rel.split("/")[0] not in ROLES:
            print("FAIL %s: a transcript outside clean/ and spec/" % rel)
            failed = True
    paths = []
    for role in ROLES:
        d = os.path.join(sessions, role)
        if not os.path.isdir(d):
            print("%s/: not on disk; %s-side transcripts skipped, not read%s"
                  % (role, role, " (a clean folder leaves them out)" if role == "spec" else ""))
            continue
        paths += sorted(glob.glob(os.path.join(d, "*.jsonl")))
    for p in paths:
        problems, lines = check_session(p, reviewed)
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
