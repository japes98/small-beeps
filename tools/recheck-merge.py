#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Re-checks how a past commit reached main with today's merge check, and
writes the result for its record's folder (R-PROC-2, R-REC-1).

  recheck-merge.py SHA --out DIR --reason TEXT --checker-commit SHA2

Runs this checkout's tools/check-merge.py (C-MERGE) on SHA and writes DIR
(the workflow puts it at records/<SHA>/verified-<date>/ on the records
branch, beside the original record, which it never touches):
  - C-MERGE.log: the check's output;
  - verification.json and verification.md: the commit, the result, the
    commit whose check-merge.py was used (SHA2, main when the re-check
    ran) and its SHA-256, the reason, when, and the run;
  - SHA256SUMS of those files.
Only C-MERGE is re-checked: the original record holds every other check.
Exit status: the check's (0 when it passes).
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join("tools", "check-merge.py")


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verification(sha, code, checker_commit, checker_sha256, reason, now, run_url):
    """The verification record (pure, for tests)."""
    return {
        "commit": sha,
        "check": "C-MERGE",
        "result": "PASS" if code == 0 else "FAIL",
        "exit_status": code,
        "checker": CHECKER,
        "checker_commit": checker_commit,
        "checker_sha256": checker_sha256,
        "reason": reason,
        "created_utc": now,
        "run": run_url,
        "scope": "Only C-MERGE is re-checked. The original record in the folder above, "
                 "never changed, holds every other check of this commit.",
    }


def markdown(v):
    return "\n".join([
        "# C-MERGE re-checked: %s" % v["commit"][:12], "",
        "- Commit: `%s`" % v["commit"],
        "- Result: **%s** (exit status %d)" % (v["result"], v["exit_status"]),
        "- Checker: `%s` from commit `%s` (SHA-256 `%s`)"
        % (v["checker"], v["checker_commit"], v["checker_sha256"]),
        "- Why: %s" % v["reason"],
        "- Written: %s" % v["created_utc"],
        "- Run: %s" % (v["run"] or "(not in CI)"),
        "", v["scope"], "", "The check's output: `C-MERGE.log`.", ""])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sha")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reason", required=True)
    ap.add_argument("--checker-commit", required=True)
    ap.add_argument("--check-cmd", default=None, help=argparse.SUPPRESS)  # tests only
    a = ap.parse_args()
    if len(a.sha) != 40 or any(ch not in "0123456789abcdef" for ch in a.sha):
        print("recheck-merge: %r is not a full commit SHA" % a.sha)
        return 2
    if not a.reason.strip():
        print("recheck-merge: --reason must say why")
        return 2
    if os.path.exists(a.out):
        print("recheck-merge: %s exists; a verification is never overwritten" % a.out)
        return 2
    os.makedirs(a.out)
    cmd = a.check_cmd.split() if a.check_cmd else [sys.executable or "python3", "-I", CHECKER]
    p = subprocess.run(cmd + [a.sha], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(os.path.join(a.out, "C-MERGE.log"), "wb") as f:
        f.write(("$ %s %s\n" % (" ".join(cmd), a.sha)).encode() + p.stdout
                + ("\nexit status %d\n" % p.returncode).encode())
    run_url = ""
    if os.environ.get("GITHUB_RUN_ID"):
        run_url = "https://github.com/%s/actions/runs/%s (attempt %s)" % (
            os.environ.get("GITHUB_REPOSITORY"), os.environ["GITHUB_RUN_ID"],
            os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    v = verification(a.sha, p.returncode, a.checker_commit, sha256_file(os.path.join(ROOT, CHECKER)),
                     a.reason.strip(), now, run_url)
    with open(os.path.join(a.out, "verification.json"), "w") as f:
        json.dump(v, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(os.path.join(a.out, "verification.md"), "w") as f:
        f.write(markdown(v))
    names = sorted(n for n in os.listdir(a.out) if n != "SHA256SUMS")
    with open(os.path.join(a.out, "SHA256SUMS"), "w") as f:
        for n in names:
            f.write("%s  %s\n" % (sha256_file(os.path.join(a.out, n)), n))
    sys.stdout.write(p.stdout.decode("utf-8", "replace"))
    print("re-check of %s: %s (written to %s)" % (a.sha, v["result"], a.out))
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
