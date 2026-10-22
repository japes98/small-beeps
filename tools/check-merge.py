#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Checks how a commit reached main (R-PROC-2, check C-MERGE; records only).

  check-merge.py SHA [--owner LOGIN]

The owner merges pull requests locally with a signed merge commit and
pushes as the ruleset's only bypass actor (CONTRIBUTING.md). This check
makes each such push auditable. It passes when:
  - SHA is a merge commit (two parents);
  - GitHub reports its signature as verified, and the committer is the
    owner (the repository owner unless --owner is given);
  - its second parent is the head commit of a pull request into main whose
    CI workflow ("ci") concluded successfully on that commit.
The first commit (the bootstrap, no parents) is reported as such and passes:
it was pushed before the rulesets existed (docs/prompts/M0a.md, section 4).
Needs GITHUB_REPOSITORY and GITHUB_TOKEN (or GH_TOKEN).
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

API = "https://api.github.com"


def api(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "small-beeps-checks"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sha")
    ap.add_argument("--owner", default="")
    a = ap.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    owner = a.owner or repo.split("/")[0]
    problems = []

    parents = subprocess.run(["git", "rev-list", "--parents", "-n", "1", a.sha], check=True,
                             stdout=subprocess.PIPE, universal_newlines=True).stdout.split()[1:]
    if not parents:
        print("%s is the root (bootstrap) commit, pushed before the rulesets existed" % a.sha)
        print("merge check: PASS")
        return 0
    if len(parents) != 2:
        problems.append("%s is not a merge commit (%d parent)" % (a.sha, len(parents)))

    c = api("/repos/%s/commits/%s" % (repo, a.sha))
    v = c["commit"].get("verification") or {}
    committer = (c.get("committer") or {}).get("login")
    print("signature: verified=%s reason=%s committer=%s"
          % (v.get("verified"), v.get("reason"), committer))
    if not v.get("verified"):
        problems.append("merge commit signature not verified (%s)" % v.get("reason"))
    if committer != owner:
        problems.append("committer is %s, not the owner %s" % (committer, owner))

    if len(parents) == 2:
        head = parents[1]
        prs = [p for p in api("/repos/%s/commits/%s/pulls" % (repo, head))
               if (p.get("base") or {}).get("ref") == "main" and p["head"]["sha"] == head]
        if not prs:
            problems.append("second parent %s is not the head of a pull request into main" % head)
        for p in prs:
            print("pull request #%d: %s" % (p["number"], p["html_url"]))
        runs = api("/repos/%s/actions/runs?head_sha=%s&event=pull_request" % (repo, head))
        ci = [r for r in runs.get("workflow_runs", []) if r.get("name") == "ci"]
        for r in ci:
            print("ci run %s: %s/%s %s" % (r["id"], r["status"], r["conclusion"], r["html_url"]))
        if not any(r.get("conclusion") == "success" for r in ci):
            problems.append("no successful ci run on pull request head %s" % head)

    for p in problems:
        print("FAIL " + p)
    print("merge check: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
