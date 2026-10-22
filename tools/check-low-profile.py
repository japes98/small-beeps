#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Low-profile check (R-PUB-1, check C-LOW-PROFILE).

The repository's name, description and topics, and README.md, must contain
none of the quiet words. The description must be exactly
"Embedded audio experiments.", there must be no topics, and README.md must
open with "Embedded audio experiments. Work in progress."

  check-low-profile.py [--repo OWNER/NAME] [--offline | --require-api]

The repository's metadata comes from the GitHub API (token from GITHUB_TOKEN
or GH_TOKEN, if set). --offline checks only the README and the name;
--require-api fails if the API can't be reached.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

QUIET = re.compile(r"fm[\s_-]?1|m[\s_.-]?vave|jie[\s_-]?li|synth|firm[\s_-]?ware",
                   re.IGNORECASE)
DESCRIPTION = "Embedded audio experiments."
README_FIRST = "Embedded audio experiments. Work in progress."


def quiet_words(text):
    return sorted({m.group(0) for m in QUIET.finditer(text or "")})


def check_readme(path):
    problems = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    first = text.splitlines()[0] if text else ""
    if first != README_FIRST:
        problems.append("README.md line 1 is %r, want %r" % (first, README_FIRST))
    for i, line in enumerate(text.splitlines(), 1):
        found = quiet_words(line)
        if found:
            problems.append("README.md line %d has quiet word(s) %s"
                            % (i, ", ".join(found)))
    return problems


def check_metadata(meta):
    problems = []
    for field in ("name", "description", "homepage"):
        found = quiet_words(meta.get(field) or "")
        if found:
            problems.append("repository %s has quiet word(s) %s" % (field, ", ".join(found)))
    if meta.get("description") != DESCRIPTION:
        problems.append("description is %r, want %r" % (meta.get("description"), DESCRIPTION))
    if meta.get("topics"):
        problems.append("topics must be empty, found %s" % ", ".join(meta["topics"]))
    return problems


def fetch_metadata(repo):
    req = urllib.request.Request("https://api.github.com/repos/" + repo,
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "small-beeps-checks"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--readme", default="README.md")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--offline", action="store_true")
    g.add_argument("--require-api", action="store_true")
    a = ap.parse_args()

    problems = check_readme(a.readme)
    print("README.md: checked")
    if a.repo:
        name = a.repo.split("/")[-1]
        found = quiet_words(name)
        if found:
            problems.append("repository name %r has quiet word(s) %s" % (name, ", ".join(found)))
        print("name: %s" % name)
        if not a.offline:
            try:
                meta = fetch_metadata(a.repo)
                print("description: %r" % meta.get("description"))
                print("topics: %s" % (meta.get("topics") or []))
                problems += check_metadata(meta)
            except Exception as e:  # network or API failure
                if a.require_api:
                    problems.append("could not read repository metadata: %s" % e)
                else:
                    print("SKIPPED metadata (API unreachable: %s)" % e)
        else:
            print("SKIPPED metadata (--offline)")
    elif a.require_api:
        problems.append("--require-api needs --repo or GITHUB_REPOSITORY")
    else:
        print("SKIPPED name and metadata (no repository given)")

    for p in problems:
        print("FAIL " + p)
    print("low-profile check: %s" % ("FAIL" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
