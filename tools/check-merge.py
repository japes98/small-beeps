#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks how a commit reached main (R-PROC-2, check C-MERGE; records only).

  check-merge.py SHA [--owner LOGIN]

The owner merges pull requests with GitHub's merge button (decided
2026-10-22, CONTRIBUTING.md). GitHub then commits and signs the merge as
`web-flow`, and records who pressed the button as the pull request's
`merged_by`. This check passes when:
  - SHA is a merge commit (two parents);
  - GitHub reports its signature as verified;
  - its committer is `web-flow` and the pull request's merged_by is the
    owner, or (merges made before that decision could also be local) its
    committer is the owner;
  - its second parent is the head commit of a pull request into main whose
    CI workflow ("ci") concluded successfully on that commit.
A ci run on that head that hasn't finished yet is waited for (polling every
POLL seconds, up to --wait-minutes, default 30): GitHub can report a run as
in progress for minutes after its last job has finished, and the record of
PR #10's merge failed this check that way while CI had passed.
The first commit (the bootstrap, no parents) is reported as such and passes:
it was pushed before the rulesets existed (docs/prompts/M0a.md, section 4).
Needs GITHUB_REPOSITORY and GITHUB_TOKEN (or GH_TOKEN).
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "https://api.github.com"
WEB_FLOW = "web-flow"
POLL = 30


def api(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "small-beeps-checks"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def evaluate(n_parents, verified, reason, committer, merged_by, owner, pr_found, ci_success):
    """Returns the list of problems for one merge commit (pure, for tests)."""
    problems = []
    if n_parents != 2:
        problems.append("not a merge commit (%d parent)" % n_parents)
    if not verified:
        problems.append("merge commit signature not verified (%s)" % reason)
    if committer == WEB_FLOW:
        if merged_by != owner:
            problems.append("merged by %s, not the owner %s" % (merged_by, owner))
    elif committer != owner:
        problems.append("committer is %s, neither %s nor the owner %s"
                        % (committer, WEB_FLOW, owner))
    if not pr_found:
        problems.append("second parent is not the head of a pull request into main")
    if not ci_success:
        problems.append("no successful ci run on the pull request head")
    return problems


def ci_verdict(runs):
    """"success" if any ci run concluded successfully, "pending" if none did
    and one hasn't finished, else "failed" (pure, for tests)."""
    if any(r.get("conclusion") == "success" for r in runs):
        return "success"
    if any(r.get("status") != "completed" for r in runs):
        return "pending"
    return "failed"


def wait_for_ci(fetch, wait_s, sleep=time.sleep, clock=time.monotonic):
    """Fetches the ci runs until one succeeded, none is pending, or wait_s
    seconds have passed. Returns (verdict, runs)."""
    deadline = clock() + wait_s
    while True:
        runs = fetch()
        verdict = ci_verdict(runs)
        if verdict != "pending" or clock() >= deadline:
            return verdict, runs
        print("ci run still in progress; checking again in %d s" % POLL, flush=True)
        sleep(POLL)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sha")
    ap.add_argument("--owner", default="")
    ap.add_argument("--wait-minutes", type=float, default=30,
                    help="how long to wait for an unfinished ci run on the head")
    a = ap.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    owner = a.owner or repo.split("/")[0]

    parents = subprocess.run(["git", "rev-list", "--parents", "-n", "1", a.sha], check=True,
                             stdout=subprocess.PIPE, universal_newlines=True).stdout.split()[1:]
    if not parents:
        print("%s is the root (bootstrap) commit, pushed before the rulesets existed" % a.sha)
        print("merge check: PASS")
        return 0

    c = api("/repos/%s/commits/%s" % (repo, a.sha))
    v = c["commit"].get("verification") or {}
    committer = (c.get("committer") or {}).get("login")
    print("signature: verified=%s reason=%s committer=%s"
          % (v.get("verified"), v.get("reason"), committer))

    merged_by, pr_found, ci_success = None, False, False
    if len(parents) == 2:
        head = parents[1]
        prs = [p for p in api("/repos/%s/commits/%s/pulls" % (repo, head))
               if (p.get("base") or {}).get("ref") == "main" and p["head"]["sha"] == head]
        pr_found = bool(prs)
        for p in prs:
            full = api("/repos/%s/pulls/%d" % (repo, p["number"]))
            merged_by = (full.get("merged_by") or {}).get("login")
            print("pull request #%d: %s merged_by=%s merge_commit=%s"
                  % (p["number"], p["html_url"], merged_by, full.get("merge_commit_sha")))
        def fetch():
            runs = api("/repos/%s/actions/runs?head_sha=%s&event=pull_request" % (repo, head))
            return [r for r in runs.get("workflow_runs", []) if r.get("name") == "ci"]
        verdict, ci = wait_for_ci(fetch, a.wait_minutes * 60)
        for r in ci:
            print("ci run %s: %s/%s %s" % (r["id"], r["status"], r["conclusion"], r["html_url"]))
        if verdict == "pending":
            print("ci run still unfinished after %g minutes" % a.wait_minutes)
        ci_success = verdict == "success"

    problems = evaluate(len(parents), v.get("verified"), v.get("reason"), committer,
                        merged_by, owner, pr_found, ci_success)
    for p in problems:
        print("FAIL " + p)
    print("merge check: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
