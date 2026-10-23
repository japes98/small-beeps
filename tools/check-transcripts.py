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
    is listed, and any that accesses FORBIDDEN material fails, unless that
    exact tool call is in sessions/REVIEWED.json (a reviewed false
    positive). Two rules run over each call (since M4, the owner's
    request):
    - the access rule, which decides: the call's text with only the spans
      it can prove are mentions taken out (access_hits), matched against
      FORBIDDEN. The spans: the body of a quoted heredoc that only goes
      into one of our own files (`cat > P`, `tee P`) or feeds `python3 -`
      code that provably opens only our own files (exempt_heredoc with
      own_path); the message of `git commit`, `tag` or `merge`; the title
      and body of a `gh` pull request or issue; a grep's pattern, and a
      sed script that only substitutes or prints, when every file they
      read is ours; the Grep tool's pattern over our own files. A
      command with a substitution (`$(`, a backtick) outside single
      quotes, or that doesn't parse, keeps everything. A hit must also
      be the text rule's, so this rule never flags more, with one
      exception: a later command that runs a file written by such a
      heredoc gets the hits of what was written into it. Reads, Grep and
      Glob paths, web fetches and searches are matched whole, as before;
    - the text rule, report only: the call's whole text, as before M4,
      with its one narrow exception for the three spec-side folder rules
      (EXEMPT_PATHS): the body of a quoted heredoc fed to `python3 -` is
      left out of their matching when it is code that provably opens
      nothing but sessions/REVIEWED.json and files under sessions/clean/.
      Its hits that the access rule doesn't make are logged as MENTION,
      by rule ID, and never fail, so nothing goes unseen.
  - A REVIEWED.json entry may be marked `superseded` (a rule now clears
    its call). It no longer clears anything, and the check fails if the
    access rule still flags its call, so the mark can't be wrong. The
    output ends with how many entries the access rule still needs.

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
import shlex
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
# a session writes). The rule IDs are neutral numbers (since M4b, the
# owner's request), so a command that only names a rule matches none;
# OLD_IDS maps the IDs used before, which older logs and records show.
FORBIDDEN = [
    ("F-1", "Felucca and firmwares built on it", r"felucca|hortator|ghoulbox|melodee|\bskiff\b"),
    ("F-2", "hugelton (Felucca's author)", r"hugelton"),
    ("F-3", "dinghy", r"dinghy|zvenson"),
    ("F-4", "FM-1 SID firmware", r"fm1-sid"),
    ("F-5", "emulator probe source", r"probes/lcdtest\.c"),
    ("F-6", "F-Emulator / fm1-emu repository", r"fm1-emu|f-emulator"),
    ("F-7", "emulator crates", r"\bcrates/fm1-"),
    # The spec-side folders' rules (F-8, F-9, F-11) are built here, in these
    # places, from config/spec-side-folders (configure, below).
    ("F-8", None, None),
    ("F-9", None, None),
    ("F-10", "thefirmwarehub.com", r"thefirmwarehub\.com"),
    ("F-11", None, None),
    ("F-12", "FM-1-RE firmware images or disassembly",
     r"fm-1-re.*(firmware-images|disasm|disassembl|ghidra|\.idb\b|\.i64\b|functions)"
     r"|firmware-images/"),
    ("F-13", "M-VAVE stock firmware", r"m-?vave.*\.(fwsc|bin|ufw|hex)\b"),
]
TEMPLATE = FORBIDDEN
OLD_IDS = {
    "F-FELUCCA": "F-1", "F-HUGELTON": "F-2", "F-DINGHY": "F-3", "F-FM1-SID": "F-4",
    "F-PROBE": "F-5", "F-EMU-REPO": "F-6", "F-EMU-CRATES": "F-7", "F-VENDOR-EMU": "F-8",
    "F-HARNESS": "F-9", "F-FWHUB": "F-10", "F-SPEC-SESSIONS": "F-11",
    "F-RE-FIRMWARE": "F-12", "F-STOCK": "F-13",
}

FOLDERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "config", "spec-side-folders")
# A folder's name in a target is bounded by whitespace, a quote, or a shell
# operator or bracket (since M2, so that `D=<folder>; ls $D` is caught
# too), or followed by a slash. A source folder is also matched as a whole
# word; a transcripts folder only as a path ending in its name.
BEFORE = r"(^|[\s\"'=:/;&|<>(){}`])"
AFTER = r"(/|[\s\"';&|<>(){}`]|$)"


def read_folders(path=FOLDERS_FILE):
    """[(folder, kind, rule, label)] from config/spec-side-folders."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                folder, kind, rule, label = line.rstrip("\n").split("\t")
                if kind not in ("source", "transcripts"):
                    raise ValueError("%s: unknown kind %r" % (path, kind))
                rows.append((folder, kind, rule, label))
    return rows


def folder_rule(folder, kind, rule, label):
    p = re.escape(folder) + AFTER
    return (rule, label, BEFORE + p if kind == "source" else p)


def configure(folders):
    """Builds the rules from the spec-side folders: the real list at import,
    placeholder names in the tests (since M3, so the tests never spell the
    folders out). Every folder rule of TEMPLATE must be given."""
    global FORBIDDEN, FORBIDDEN_RE, RULE_ID, RULE_WHY, FOLDER_RULES
    rules = {r[2]: folder_rule(*r) for r in folders}
    missing = [rid for rid, why, _ in TEMPLATE if why is None and rid not in rules]
    if missing or set(rules) - {rid for rid, _, _ in TEMPLATE}:
        raise ValueError("the spec-side folders' rules must be exactly %s"
                         % [rid for rid, why, _ in TEMPLATE if why is None])
    FORBIDDEN = [rules.get(rid, (rid, why, p)) if why is None else (rid, why, p) for rid, why, p in TEMPLATE]
    FORBIDDEN_RE = [(rid, why, re.compile(p, re.IGNORECASE)) for rid, why, p in FORBIDDEN]
    RULE_ID = {why: rid for rid, why, _ in FORBIDDEN}
    RULE_WHY = {rid: why for rid, why, _ in FORBIDDEN}
    # The rules a heredoc's body can be cleared of (exempt_heredoc).
    FOLDER_RULES = tuple(r[2] for r in folders)


configure(read_folders())


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


# What the imported modules may be used for (since M4): without this,
# `json.codecs.open(...)` would reach a file through a module the code
# imported.
MODULE_ATTRS = {
    "json": {"load", "loads", "dump", "dumps", "JSONDecodeError"},
    "re": {"compile", "search", "match", "fullmatch", "sub", "subn", "findall", "finditer",
           "split", "escape", "error", "I", "IGNORECASE", "M", "MULTILINE", "S", "DOTALL",
           "X", "VERBOSE"},
}


def allowed_path(path):
    if not isinstance(path, str) or path.startswith("/") or "\\" in path:
        return False
    norm = posixpath.normpath(path)
    if norm != path.rstrip("/") or ".." in norm.split("/"):
        return False
    return norm == EXEMPT_PATHS[0] or (norm.startswith(EXEMPT_PATHS[1]) and norm != EXEMPT_PATHS[1])


def own_path(path):
    """A path that is provably one of our own: relative to the repository,
    normalised, without `..`, `~` or a variable, and matching no rule (so
    outside the spec-side folders). The access rule (since M4)."""
    if not isinstance(path, str) or not path or path[0] in "/~-" or "\\" in path or "$" in path:
        return False
    norm = posixpath.normpath(path)
    if norm != path.rstrip("/") or ".." in norm.split("/"):
        return False
    return not any(rx.search(path) for _, _, rx in FORBIDDEN_RE)


def exempt_heredoc(code, allowed=allowed_path):
    """True when Python code provably opens only paths `allowed` accepts
    (EXEMPT_PATHS for the text rule, own_path for the access rule): it
    imports only SAFE_IMPORTS and uses them only for MODULE_ATTRS, calls
    only SAFE_CALLS and methods (no dunder names), and every open() names
    a path that is a literal, or a variable bound exactly once to a
    literal, that `allowed` accepts. Strings it uses otherwise are data
    (e.g. the text it writes)."""
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
        elif (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
              and node.value.id in SAFE_IMPORTS):
            if node.value.id in bound or node.attr not in MODULE_ATTRS[node.value.id]:
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
                    if not allowed(path):
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


# The access rule (since M4, the owner's request). The text rule above flags
# a forbidden name anywhere in a call; most such hits were mentions (a pull
# request's body, a commit message, a document written to our own file, a
# grep pattern over our own files) that needed a REVIEWED.json entry each.
# The access rule takes out only the spans of a call it can prove are
# mentions, matches the same rules against what is left, and keeps a hit
# only if the text rule made it too, so it never flags more than the text
# rule. Anything it can't parse, or doesn't know, stays flagged. The text
# rule still runs, report only, so every mention is still listed.

# A heredoc whose body only goes into one of our own files: `cat > P`,
# `cat >> P`, `cat <<'X' > P`, `tee [-a] P`, with nothing piped after it.
CAT_BEFORE = re.compile(r"^\s*cat(\s+>>?\s*(?P<p>\S+))?\s*$")
TEE_BEFORE = re.compile(r"^\s*tee(\s+-a)?\s+(?P<p>\S+)\s*$")
CAT_AFTER = re.compile(r"^\s*(>>?\s*(?P<p>\S+))?\s*$")
# What such a file's name may be: a plain path, perhaps through a variable
# (`$T/pr.md`), never a process substitution or a command.
DEST_RE = re.compile(r"^[A-Za-z0-9_./${}~-]+$")
# Commands that run a file: a later one given a file written that way
# brings back the hits of the body written into it.
EXECUTORS = {"python", "python3", "sh", "bash", "zsh", "dash", "ksh", "perl", "node", "ruby",
             "source", ".", "make", "env", "exec", "xargs"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", "\n", ";;", "|&"}
KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "time"}
# Text-valued options: git commit, tag and merge's message; gh's pull
# request and issue title and body.
GIT_TEXT = {"commit", "tag", "merge"}
GIT_TEXT_OPTS = ("-m", "--message")
GH_TEXT_OPTS = ("-t", "--title", "-b", "--body")
GREP_VALUE_OPTS = {"-e", "--regexp", "-f", "--file", "-m", "--max-count", "-A", "-B", "-C",
                   "--after-context", "--before-context", "--context", "--include", "--exclude",
                   "--exclude-dir", "-g", "--glob", "-t", "--type", "-T", "--type-not"}


def shell_tokens(text):
    """The words and operators of shell text, quotes removed, or None if
    it can't be parsed. `#` is kept as text: a comment could only hide
    words."""
    lex = shlex.shlex(text.replace("\\\n", " "), posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        return list(lex)
    except ValueError:
        return None


def substitutes(text):
    """True when shell text may run a command inside a word: `$(`, a
    backtick, or a process substitution, outside single quotes."""
    i, single = 0, False
    while i < len(text):
        c = text[i]
        if single:
            single = c != "'"
        elif c == "'":
            single = True
        elif c == "\\":
            i += 1
        elif c == "`" or text[i:i + 2] in ("$(", "<(", ">("):
            return True
        i += 1
    return False


def commands(tokens):
    """Splits tokens into simple commands (lists of words)."""
    out, cur = [], []
    for t in tokens:
        if t in SEPARATORS:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def option_values(argv, start, names):
    """Indices in argv of the values of the options `names` (`-m X`,
    `--message=X`, `-mX` for a one-letter option), from argv[start] on."""
    idx, i = [], start
    while i < len(argv):
        t = argv[i]
        if t in names and i + 1 < len(argv):
            idx.append(i + 1)
            i += 2
            continue
        if any(t.startswith(n + "=") for n in names if n.startswith("--")) or \
                any(t.startswith(n) and len(t) > 2 for n in names if len(n) == 2):
            idx.append(i)
        i += 1
    return idx


def grep_pattern(argv, start, git=False):
    """Indices of a grep's patterns, if every path it searches is one of
    our own (own_path); else []. A grep of standard input, or (git grep)
    of the repository, searches our own files."""
    pats, operands, paths, i, dashdash = [], [], [], start, False
    while i < len(argv):
        t = argv[i]
        if dashdash:
            paths.append(t)
        elif t == "--":
            dashdash = True
        elif t in ("-e", "--regexp") and i + 1 < len(argv):
            pats.append(i + 1)
            i += 1
        elif t in ("-f", "--file") and i + 1 < len(argv):
            paths.append(argv[i + 1])
            i += 1
        elif t in GREP_VALUE_OPTS:
            i += 1
        elif t.startswith("-") and t != "-":
            pass
        elif t and t[0] in "<>":
            break
        else:
            operands.append(i)
        i += 1
    if not pats and operands:
        pats, operands = [operands[0]], operands[1:]
    if git and operands:
        return []  # a revision or a path: only pathspecs after `--` are clear
    paths += [argv[j] for j in operands if not (argv[j].isdigit() and j + 1 < len(argv)
                                                and argv[j + 1][:1] in "<>")]
    if not all(own_path(p.lstrip(":!")) if git else own_path(p) for p in paths):
        return []
    return pats


def command_index(argv):
    """The index of a simple command's command word, past shell keywords
    and variable assignments (which stay matched), or None."""
    i = 0
    while i < len(argv) and (argv[i] in KEYWORDS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i])):
        i += 1
    return i if i < len(argv) else None


def mention_spans(argv):
    """Indices of argv's words that are only text: messages, titles,
    bodies, grep patterns over our own files."""
    i = command_index(argv)
    if i is None:
        return []
    cmd = argv[i]
    if cmd == "git":
        j = i + 1
        while j < len(argv) and argv[j] in ("-C", "-c") and j + 1 < len(argv):
            j += 2
        if j < len(argv) and argv[j] in GIT_TEXT:
            return option_values(argv, j + 1, GIT_TEXT_OPTS)
        if j < len(argv) and argv[j] == "grep":
            return grep_pattern(argv, j + 1, git=True)
        return []
    if cmd == "gh" and len(argv) > i + 2 and argv[i + 1] in ("pr", "issue") \
            and argv[i + 2] in ("create", "edit", "comment", "review"):
        return option_values(argv, i + 3, GH_TEXT_OPTS)
    if cmd in ("grep", "egrep", "fgrep", "rg"):
        return grep_pattern(argv, i + 1)
    if cmd == "sed":
        return sed_script(argv, i + 1)
    return []


# A sed script that only substitutes, prints, deletes or quits (no command
# that reads, writes or runs anything: r, R, w, W, e, or s///w, s///e).
SED_SUBST = re.compile(r"s(?P<d>[^\\\n\sa-zA-Z0-9])(?:\\.|(?!(?P=d)).)*(?P=d)"
                       r"(?:\\.|(?!(?P=d)).)*(?P=d)[gpiI0-9]*", re.S)
SED_REST = re.compile(r"^[\d,;$!pdnq{}\s]*$")


def sed_script(argv, start):
    """Indices of a sed's script, if it is SED_SUBST commands and lines
    only and every file it edits is one of our own; else []."""
    scripts, files, i = [], [], start
    while i < len(argv):
        t = argv[i]
        if t in ("-e", "--expression") and i + 1 < len(argv):
            scripts.append(i + 1)
            i += 1
        elif t == "-i" and i + 1 < len(argv) and (argv[i + 1] == "" or argv[i + 1].startswith(".")):
            i += 1  # BSD sed's -i takes a suffix
        elif t in ("-f", "--file"):
            return []
        elif t.startswith("-") and t != "-":
            pass
        elif t and t[0] in "<>":
            break
        else:
            files.append(i)
        i += 1
    if not scripts and files:
        scripts, files = [files[0]], files[1:]
    files = [j for j in files if not (argv[j].isdigit() and j + 1 < len(argv) and argv[j + 1][:1] in "<>")]
    if not scripts or not all(own_path(argv[j]) for j in files):
        return []
    if not all(SED_REST.match(SED_SUBST.sub(";", argv[j])) for j in scripts):
        return []
    return scripts


def data_heredoc(line, op):
    """The file a heredoc's body only goes into (CAT_BEFORE, TEE_BEFORE),
    or None. It must be a plain name (DEST_RE) matching no rule."""
    before = re.split(r"&&|\|\||;", line[:op.start()])[-1]
    after = re.split(r"&&|\|\||;", line[op.end():])[0]
    if "|" in after:
        return None
    dest = None
    m, a = CAT_BEFORE.match(before), CAT_AFTER.match(after)
    if m and a and bool(m.group("p")) != bool(a.group("p")):
        dest = m.group("p") or a.group("p")
    t = TEE_BEFORE.match(before)
    if t and a and not a.group("p"):
        dest = t.group("p")
    if not dest or not DEST_RE.match(dest) or "$(" in dest:
        return None
    if any(rx.search(dest) for _, _, rx in FORBIDDEN_RE):
        return None
    return dest


def runs(argv, path):
    """True when a simple command runs, or hands to something that runs,
    a file whose name holds path: an EXECUTORS command given it, or the
    file itself as the command."""
    i = command_index(argv)
    if i is None or not any(path in w for w in argv[i:]):
        return False
    return path in argv[i] or posixpath.basename(argv[i]) in EXECUTORS or argv[i].startswith("python")


def access_hits(name, kind, target, inp, text_hits, written, cwd=""):
    """The access rule's hits for one call. `written` maps a file that an
    earlier call of the session wrote with a stripped heredoc to the rules
    its body matched; a later command that runs that file brings them back
    (the only hits this rule can add). Otherwise the hits are a subset of
    text_hits, the text rule's."""
    if name == "Grep" and text_hits:
        # Its pattern is text when it searches our own files.
        path = str(inp.get("path") or "")
        if cwd and (path == cwd or path.startswith(cwd + "/")):
            path = path[len(cwd) + 1:] or "."
        glob_ = str(inp.get("glob") or "")
        if (not path or own_path(path)) and not any(rx.search(glob_) for _, _, rx in FORBIDDEN_RE):
            rest = " ".join(x for x in (path, glob_) if x)
            return [r for r in text_hits if any(rid == r and rx.search(rest) for rid, _, rx in FORBIDDEN_RE)]
        return text_hits
    if kind != "shell" or not (text_hits or any(p in target for p in written)):
        return text_hits
    lines = target.split("\n")
    keep, bodies, i, wrote = [], [], 0, {}
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
        text = "\n".join(body)
        segment = re.split(r"&&|\|\||[;|(]", line[:ops[0].start()])[-1]
        dest = data_heredoc(line, ops[0])
        if PYTHON_STDIN.match(segment) and exempt_heredoc(text, own_path):
            pass  # code that provably opens only our own files: its strings are data
        elif dest:
            wrote[dest] = {rid for rid, _, rx in FORBIDDEN_RE if rx.search(text)}
        else:
            bodies.append(text)  # matched whole, never parsed as shell
        if i < len(lines):
            keep.append(lines[i])
            i += 1
    rest = "\n".join(keep)
    tokens = None if substitutes(rest) else shell_tokens(rest)
    extra = set()
    if tokens is None:
        remaining = rest
        for path, hits in written.items():
            if path in rest:
                extra |= hits
    else:
        words = []
        for argv in commands(tokens):
            drop = set(mention_spans(argv))
            words.append(" ".join(w for k, w in enumerate(argv) if k not in drop))
            for path, hits in list(written.items()) + list(wrote.items()):
                if runs(argv, path):
                    extra |= hits
        remaining = "\n".join(words)
    written.update(wrote)
    remaining += "\n" + "\n".join(bodies)
    found = {rid for rid, _, rx in FORBIDDEN_RE if rx.search(remaining)}
    return [r for r in text_hits if r in found or r in extra] + sorted(extra - set(text_hits))


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
    tool call's ID, the matched rule (its label, or its ID) and the reason. It is added by pull
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
        # A rule is named by its label, or (since M4b) by its rule ID, which
        # new entries use since some labels match their own patterns.
        key = (r["session"], r["tool_use_id"], RULE_WHY.get(r["rule"], r["rule"]))
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


def check_session(path, reviewed=None, stats=None):
    """Checks one archived session: (problems, log lines). `stats`, if
    given, collects the REVIEWED.json keys the access rule still needs
    ("needed") and those only the text rule would flag ("text_only")."""
    reviewed = reviewed if reviewed is not None else load_reviewed(os.path.dirname(path))
    stats = stats if stats is not None else {"needed": set(), "text_only": set(), "mentions": 0}
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
            those = load(f) if f != path else entries
            cwd = next((e["cwd"] for e in those if isinstance(e.get("cwd"), str)), "")
            written = {}
            for line_no, tid, name, inp in tool_calls(those):
                for kind, target in targets(name, inp):
                    count += 1
                    text, cleared = forbidden_hits(kind, target)
                    hits = access_hits(name, kind, target, inp, text, written, cwd)
                    where = "entry %d %s %s %s%s" % (line_no, kind, name, tid, sub)
                    lines.append("  " + where)
                    if cleared:
                        lines.append("    CLEARED folder rules: its heredoc opens only %s"
                                     % " and ".join(EXEMPT_PATHS))
                    for rid in text:
                        if rid not in hits:
                            stats["mentions"] += 1
                            lines.append("    MENTION %s (report only: not an access)" % rid)
                            stats["text_only"].add((sid, tid, RULE_WHY[rid]))
                    for rid in hits:
                        why = RULE_WHY[rid]
                        entry = reviewed.get((sid, tid, why))
                        if isinstance(entry, str):
                            lines.append("    REVIEWED %s" % rid)
                            stats["needed"].add((sid, tid, why))
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
    stats = {"needed": set(), "text_only": set(), "mentions": 0}
    for p in paths:
        problems, lines = check_session(p, reviewed, stats)
        for l in lines:
            print(l)
        for pr in problems:
            print("FAIL %s: %s" % (os.path.basename(p), pr))
        failed = failed or bool(problems)
    print("%d mention(s) the text rule matched and the access rule did not (report only)"
          % stats["mentions"])
    live = [k for k, v in reviewed.items() if isinstance(v, str)]
    unused = [k for k in live if k not in stats["needed"]]
    print("REVIEWED.json: %d entries clear a hit; the access rule still needs %d, "
          "and %d of the rest only the text rule matches (%d not seen in the transcripts here)"
          % (len(live), len(live) - len(unused), sum(k in stats["text_only"] for k in unused),
             sum(k not in stats["text_only"] for k in unused)))
    print("%d archived transcript(s) checked: %s"
          % (len(paths), "FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
