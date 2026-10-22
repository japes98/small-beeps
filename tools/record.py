#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Runs every check and writes the test record (R-PROC-4, R-REC-1).

  record.py run --out DIR [--only C-A,C-B] [--skip C-X] [--with-merge]
      Runs the checks in CHECKS, writes DIR/report.json, DIR/report.md,
      DIR/logs/<check>.log, DIR/outputs/ (the build outputs) and
      DIR/SHA256SUMS (of all of those). Exit status 1 if any check failed.
  record.py compare --record REPORT.json --outputs DIR
      Compares DIR/SHA256SUMS with the outputs listed in a record
      (used by tools/reproduce). Exit status 1 on any difference.

Environment: COMMIT_RANGE (for C-COMMIT-MSG, default: every commit reachable
from HEAD), GITHUB_* (recorded, and used by C-LOW-PROFILE and C-MERGE).
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python3"
SCHEMA = 1


def _low_profile_cmd():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return [PY, "-I", "tools/check-low-profile.py", "--require-api"]
    return [PY, "-I", "tools/check-low-profile.py", "--offline"]


def _commit_range():
    return os.environ.get("COMMIT_RANGE") or "..HEAD"


# Each check: id, title, requirement IDs, and either a command (list, or a
# function returning one, run from the repository root) or an internal
# function name. "records_only" checks run only with --with-merge.
CHECKS = [
    {"id": "C-UNIT", "title": "Unit tests of the tools",
     "reqs": ["R-PROC-1", "R-PROC-4", "R-REC-1", "R-CLEAN-3", "R-CLEAN-4", "R-PUB-1",
              "R-SEP-2"],
     "cmd": [PY, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]},
    {"id": "C-REUSE", "title": "reuse lint (SPDX licence and copyright on every file)",
     "reqs": ["R-LIC-1", "R-LIC-2"], "cmd": ["reuse", "lint"]},
    {"id": "C-COMMIT-MSG", "title": "Commit messages follow .gitmessage",
     "reqs": ["R-PROC-1"],
     "cmd": lambda: [PY, "-I", "tools/check-commit-msg.py", "--range", _commit_range()]},
    {"id": "C-LOW-PROFILE", "title": "Low profile: name, description, topics, README",
     "reqs": ["R-PUB-1"], "cmd": _low_profile_cmd},
    {"id": "C-SECRETS", "title": "No secrets in tracked files",
     "reqs": ["R-PUB-2"], "cmd": [PY, "-I", "tools/check-tracked.py", "secrets"]},
    {"id": "C-NO-TOOLCHAIN", "title": "No toolchain parts or binaries tracked",
     "reqs": ["R-REPRO-1"], "cmd": [PY, "-I", "tools/check-tracked.py", "no-toolchain"]},
    {"id": "C-DENY-LISTS", "title": "Claude Code deny lists never drop an entry",
     "reqs": ["R-CLEAN-4", "R-SEP-2"], "cmd": [PY, "-I", "tools/check-deny-lists.py"]},
    {"id": "C-TRANSCRIPTS", "title": "Archived session transcripts: banners and forbidden material",
     "reqs": ["R-CLEAN-1", "R-CLEAN-3", "R-CLEAN-5", "R-SEP-2"],
     "cmd": [PY, "-I", "tools/check-transcripts.py"]},
    {"id": "C-SDK-PIN", "title": "Vendored SDK files match the pinned commit",
     "reqs": ["R-REPRO-5", "R-LIC-2"], "cmd": ["sh", "tools/fetch-sdk.sh", "--verify"]},
    {"id": "C-IMAGE", "title": "Build container (pinned base, toolchain SHA-256 checked)",
     "reqs": ["R-REPRO-1", "R-REPRO-2"], "cmd": ["sh", "tools/build.sh", "image"]},
    {"id": "C-BUILD-A", "title": "Build A in a fresh container (source at /mnt/small-beeps-src)",
     "reqs": ["R-REPRO-3", "R-BUILD-1"],
     "cmd": lambda: ["sh", "tools/build.sh", "build", "--out", os.path.join(OUT, "build-a")]},
    {"id": "C-BUILD-B", "title": "Build B in a fresh container (source at another path)",
     "reqs": ["R-REPRO-3"],
     "cmd": lambda: ["sh", "tools/build.sh", "build", "--out", os.path.join(OUT, "build-b"),
                     "--src-mount", "/tmp/elsewhere/small-beeps-src-b"]},
    {"id": "C-DETERMINISM", "title": "Builds A and B are byte-identical",
     "reqs": ["R-REPRO-3"], "internal": "determinism"},
    {"id": "C-MERGE", "title": "Signed owner merge of a pull request that passed CI",
     "reqs": ["R-PROC-2"], "records_only": True,
     "cmd": lambda: [PY, "-I", "tools/check-merge.py", git("rev-parse", "HEAD")]},
]

OUT = ""


def git(*args):
    try:
        return subprocess.run(["git", "-C", ROOT] + list(args), check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums(path):
    sums = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                digest, name = line.split(None, 1)
                sums[name.strip().lstrip("*")] = digest
    return sums


def run_cmd(argv):
    try:
        p = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except OSError as e:
        return 127, "could not run %s: %s\n" % (argv[0], e)


def determinism():
    a, b = os.path.join(OUT, "build-a"), os.path.join(OUT, "build-b")
    lines, ok = [], True
    try:
        sa, sb = read_sums(os.path.join(a, "SHA256SUMS")), read_sums(os.path.join(b, "SHA256SUMS"))
    except OSError as e:
        return 1, "missing build output: %s\n" % e
    if sorted(sa) != sorted(sb):
        ok = False
        lines.append("different file lists: %s vs %s" % (sorted(sa), sorted(sb)))
    for name in sorted(set(sa) & set(sb)):
        with open(os.path.join(a, name), "rb") as fa, open(os.path.join(b, name), "rb") as fb:
            same = fa.read() == fb.read()
        lines.append("%s %s %s" % ("IDENTICAL" if same else "DIFFERENT", name, sa[name]))
        ok = ok and same
    if not sa:
        ok = False
        lines.append("no outputs")
    lines.append("determinism: %s" % ("PASS" if ok else "FAIL"))
    return (0 if ok else 1), "\n".join(lines) + "\n"


def dockerfile_pins():
    pins = {}
    with open(os.path.join(ROOT, "tools", "Dockerfile")) as f:
        text = f.read()
    for key in ("BASE", "SNAPSHOT", "TOOLCHAIN_NAME", "TOOLCHAIN_URL", "TOOLCHAIN_SHA256"):
        m = re.search(r"^ARG %s=(\S+)" % key, text, re.M)
        if m:
            pins[key.lower()] = m.group(1)
    m = re.search(r"^# syntax=(\S+)", text, re.M)
    if m:
        pins["dockerfile_frontend"] = m.group(1)
    m = re.search(r"SOURCE_DATE_EPOCH=(\d+)", text)
    if m:
        pins["source_date_epoch"] = m.group(1)
    return pins


def tool_version(argv):
    code, out = run_cmd(argv)
    return out.strip().splitlines()[0] if code == 0 and out.strip() else "unavailable"


def environment():
    env = {"dockerfile": dockerfile_pins()}
    with open(os.path.join(ROOT, "tools", "fetch-sdk.sh")) as f:
        m = re.search(r"^SDK_COMMIT=(\S+)", f.read(), re.M)
    env["sdk_commit"] = m.group(1) if m else ""
    env["sdk_sha256sums"] = sha256_file(os.path.join(ROOT, "vendor", "jieli-sdk", "SHA256SUMS"))
    tag = run_cmd(["sh", "tools/build.sh", "image-tag"])[1].strip()
    env["build_image_tag"] = tag
    env["build_image_id"] = tool_version(["docker", "image", "inspect", "--format", "{{.Id}}", tag])
    env["docker"] = tool_version(["docker", "version", "--format",
                                  "client {{.Client.Version}} server {{.Server.Version}}"])
    env["python"] = platform.python_version()
    env["reuse"] = tool_version(["reuse", "--version"])
    env["git"] = tool_version(["git", "--version"])
    env["host"] = "%s %s %s" % (platform.system(), platform.release(), platform.machine())
    env["claude_configs"] = {n: sha256_file(os.path.join(ROOT, "config", "claude", n))
                             for n in ("clean.json", "spec.json", "handmade-settings.json")}
    env["github"] = {k: os.environ[k] for k in sorted(os.environ)
                     if k in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                              "GITHUB_WORKFLOW", "GITHUB_EVENT_NAME", "GITHUB_REF",
                              "GITHUB_SHA", "RUNNER_OS", "RUNNER_ARCH", "ImageOS",
                              "ImageVersion")}
    return env


def requirements_table():
    rows = []
    with open(os.path.join(ROOT, "docs", "REQUIREMENTS.md"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\| (R-[A-Z]+-\d+) \|(.*)\|(.*)\|(.*)\|\s*$", line)
            if m:
                rows.append({"id": m.group(1), "since": m.group(3).strip(),
                             "checked_by": m.group(4).strip()})
    return rows


def traceability(checks, defined=None):
    """requirement -> checks -> result. A requirement passes only if every
    defined check that covers it ran and passed; checks that didn't run in
    this record are named."""
    defined = CHECKS if defined is None else defined
    ran = {c["id"]: c["result"] for c in checks}
    table = []
    for req in requirements_table():
        mine = [c["id"] for c in defined if req["id"] in c["reqs"]]
        results = [ran[c] for c in mine if c in ran]
        missing = [c for c in mine if c not in ran]
        if not mine:
            result = "not machine-checked (%s)" % req["checked_by"]
        elif "FAIL" in results:
            result = "FAIL"
        elif not results:
            result = "not run in this record (%s)" % ", ".join(missing)
        elif missing:
            result = "PASS (%s not run)" % ", ".join(missing)
        else:
            result = "PASS"
        table.append({"requirement": req["id"], "checks": mine, "result": result})
    return table


def write_markdown(report, path):
    L = ["# Test record %s" % report["commit"][:12], "",
         "- Commit: `%s`" % report["commit"],
         "- Subject: %s" % report["subject"],
         "- Tree: `%s`" % report["tree"],
         "- Written: %s" % report["created_utc"],
         "- Overall: **%s**" % report["overall"]]
    gh = report["environment"]["github"]
    if gh.get("GITHUB_RUN_ID"):
        L.append("- CI run: https://github.com/%s/actions/runs/%s"
                 % (gh.get("GITHUB_REPOSITORY"), gh["GITHUB_RUN_ID"]))
    L += ["", "## Checks", "", "| Check | Title | Requirements | Result | Seconds |",
          "|-------|-------|--------------|--------|---------|"]
    for c in report["checks"]:
        L.append("| %s | %s | %s | %s | %.1f |" % (c["id"], c["title"], ", ".join(c["reqs"]),
                                                   c["result"], c["seconds"]))
    L += ["", "## Outputs", "", "| File | SHA-256 |", "|------|---------|"]
    for name, digest in sorted(report["outputs"].items()):
        L.append("| `%s` | `%s` |" % (name, digest))
    L += ["", "## Traceability", "", "| Requirement | Checks | Result |",
          "|-------------|--------|--------|"]
    for t in report["traceability"]:
        L.append("| %s | %s | %s |" % (t["requirement"], ", ".join(t["checks"]) or "-",
                                       t["result"]))
    L += ["", "## Environment", "", "```json",
          json.dumps(report["environment"], indent=2, sort_keys=True), "```", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def cmd_run(a):
    global OUT
    OUT = os.path.abspath(a.out)
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    skip = set(a.skip.split(",")) if a.skip else set()
    results = []
    for c in CHECKS:
        if only is not None and c["id"] not in only:
            continue
        if c["id"] in skip or (c.get("records_only") and not a.with_merge):
            continue
        start = time.time()
        if "internal" in c:
            code, log = globals()[c["internal"]]()
            argv = ["(internal) " + c["internal"]]
        else:
            argv = c["cmd"]() if callable(c["cmd"]) else c["cmd"]
            code, log = run_cmd(argv)
        secs = time.time() - start
        result = "PASS" if code == 0 else "FAIL"
        with open(os.path.join(OUT, "logs", c["id"] + ".log"), "w", encoding="utf-8") as f:
            f.write("$ %s\n%s\nexit status %d\n" % (" ".join(argv), log, code))
        print("%-14s %-4s %6.1fs  %s" % (c["id"], result, secs, c["title"]), flush=True)
        results.append({"id": c["id"], "title": c["title"], "reqs": c["reqs"],
                        "command": " ".join(argv), "result": result, "exit_status": code,
                        "seconds": round(secs, 1), "log": "logs/%s.log" % c["id"]})

    outputs = {}
    build_a = os.path.join(OUT, "build-a")
    if os.path.exists(os.path.join(build_a, "SHA256SUMS")):
        outputs = read_sums(os.path.join(build_a, "SHA256SUMS"))
        os.makedirs(os.path.join(OUT, "outputs"), exist_ok=True)
        for name in outputs:
            shutil.copyfile(os.path.join(build_a, name), os.path.join(OUT, "outputs", name))
    for d in ("build-a", "build-b"):
        shutil.rmtree(os.path.join(OUT, d), ignore_errors=True)

    report = {
        "schema": SCHEMA,
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "subject": git("log", "-1", "--format=%s"),
        "worktree_clean": git("status", "--porcelain") == "",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment": environment(),
        "checks": results,
        "outputs": outputs,
        "traceability": traceability(results),
        "overall": "PASS" if results and all(r["result"] == "PASS" for r in results) else "FAIL",
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    write_markdown(report, os.path.join(OUT, "report.md"))

    files = []
    for dirpath, _, names in os.walk(OUT):
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), OUT)
            if rel != "SHA256SUMS" and not rel.endswith(".ots"):
                files.append(rel)
    with open(os.path.join(OUT, "SHA256SUMS"), "w") as f:
        for rel in sorted(files):
            f.write("%s  %s\n" % (sha256_file(os.path.join(OUT, rel)), rel))
    print("overall: %s (record in %s)" % (report["overall"], OUT))
    return 0 if report["overall"] == "PASS" else 1


def cmd_compare(a):
    with open(a.record) as f:
        want = json.load(f)["outputs"]
    got = read_sums(os.path.join(a.outputs, "SHA256SUMS"))
    ok = bool(want)
    for name in sorted(set(want) | set(got)):
        w, g = want.get(name), got.get(name)
        status = "MATCH" if w == g else "DIFFERENT"
        ok = ok and w == g
        print("%-9s %s record=%s rebuilt=%s" % (status, name, w, g))
    print("REPRODUCED" if ok else "NOT REPRODUCED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--only")
    r.add_argument("--skip")
    r.add_argument("--with-merge", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("--record", required=True)
    c.add_argument("--outputs", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "compare":
        return cmd_compare(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
