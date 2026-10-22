#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""Finds the similarity audit's targets from repository metadata only
(R-AUDIT-2; docs/AUDIT.md).

  audit-discover.py [--write] [--config audit/discover.json] [--targets audit/targets.json]

Reads audit/discover.json and asks GitHub's REST API and `git ls-remote`
for metadata: repository names, owners, descriptions, licences, languages,
fork lists, and commit and tree SHAs. It never opens a target's files,
README or web pages, and never prints a description. A target is:
  - a seed (discover.json "seeds");
  - a repository a search query finds whose name or description mentions
    the FM-1 or a known firmware ("mentions"); one that matches by name
    alone must also be in a language of "name_only_languages";
  - any fork of a target, to any depth (forks inherit "paths" and
    "licence_class").
Each target is pinned at its default branch's head commit, with that
commit's tree. Targets whose tree is already in the list (seeds first, then
by name) are marked `duplicate` and not scored. Licences are classed from
metadata: gpl, permissive, other or none.

Without --write it prints what changed against the committed targets.json
(repository names only) and exits 1 if anything did; with --write it also
writes the new file. The token comes from GITHUB_TOKEN or `gh auth token`.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com"
SCHEMA = 1
GPL = re.compile(r"^(A|L)?GPL-")
PERMISSIVE = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "Zlib", "Unlicense",
              "CC0-1.0", "WTFPL", "0BSD", "BSL-1.0", "MIT-0"}


def licence_class(spdx):
    if not spdx:
        return "none"
    if GPL.match(spdx):
        return "gpl"
    if spdx in PERMISSIVE:
        return "permissive"
    return "other"


def order_key(t):
    # seeds first (in their order), then other originals, then forks; by name within each
    return (0 if t.get("seed") is not None else 1 if not t.get("fork_of") else 2,
            t.get("seed") or 0, t["repo"].lower())


def dedupe(targets):
    """Marks every target whose (tree, paths) was already seen as a duplicate of the first."""
    first = {}
    for t in sorted(targets, key=order_key):
        if t["status"] not in ("scored", "duplicate"):
            continue
        key = (t["tree"], tuple(t.get("paths") or ()))
        if key in first:
            t["status"], t["same_tree_as"] = "duplicate", first[key]
        else:
            t["status"] = "scored"
            t.pop("same_tree_as", None)
            first[key] = t["repo"]
    return targets


def changes(old, new):
    """Names of repositories added, gone or moved (a new pinned commit)."""
    o = {t["repo"]: t.get("commit") for t in old.get("targets", [])}
    n = {t["repo"]: t.get("commit") for t in new.get("targets", [])}
    return (sorted(set(n) - set(o)), sorted(set(o) - set(n)),
            sorted(r for r in set(n) & set(o) if n[r] != o[r]))


class GitHub:
    def __init__(self, token):
        self.token = token
        self.last_search = 0.0

    def get(self, path, params=None):
        url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "audit-discover",
            "Authorization": "Bearer " + self.token, "X-GitHub-Api-Version": "2022-11-28"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in (403, 429, 502, 503) and attempt < 4:
                    time.sleep(30 * (attempt + 1))
                    continue
                raise

    def pages(self, path, params=None, limit=10):
        out = []
        for page in range(1, limit + 1):
            got = self.get(path, dict(params or {}, per_page=100, page=page))
            items = got.get("items", []) if isinstance(got, dict) else (got or [])
            out += items
            if len(items) < 100:
                break
        return out

    def search(self, q):
        out = []
        for page in (1, 2, 3):
            # the search API allows 30 requests a minute
            time.sleep(max(0.0, self.last_search + 2.5 - time.time()))
            self.last_search = time.time()
            got = self.get("/search/repositories", {"q": q, "per_page": 100, "page": page}) or {}
            items = got.get("items", [])
            out += items
            if len(items) < 100:
                break
        return out


def token():
    t = os.environ.get("GITHUB_TOKEN")
    if t:
        return t
    p = subprocess.run(["gh", "auth", "token"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                       universal_newlines=True)
    if p.returncode != 0 or not p.stdout.strip():
        raise SystemExit("no GITHUB_TOKEN and no `gh auth token`")
    return p.stdout.strip()


def head(url):
    """The default branch's head commit, from `git ls-remote` (None for an empty repository)."""
    p = subprocess.run(["git", "ls-remote", url, "HEAD"], stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, universal_newlines=True,
                       env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    for line in p.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if ref == "HEAD" and re.fullmatch(r"[0-9a-f]{40}", sha):
            return sha
    return None


def entry(meta, found_by, seed=None, fork_of=None, inherit=None):
    t = {"repo": meta["full_name"], "url": meta["html_url"], "found_by": found_by,
         "licence": (meta.get("license") or {}).get("spdx_id") or None}
    t["licence_class"] = licence_class(t["licence"])
    if seed is not None:
        t["seed"] = seed
    if fork_of:
        t["fork_of"] = fork_of
    for k in ("paths", "licence_class"):
        if inherit and k in inherit:
            t[k] = inherit[k]
    return t


def discover(cfg, gh, self_repo=None, log=print):
    mention = re.compile(cfg["mentions"])
    langs = set(cfg.get("name_only_languages", []))
    found = {}
    queue = []

    def add(meta, t):
        name = meta["full_name"]
        if name in found or name == self_repo:
            return
        found[name] = t
        queue.append((meta, t))

    for i, s in enumerate(cfg["seeds"], 1):
        meta = gh.get("/repos/" + s["repo"])
        if not meta:
            log("seed not found: %s" % s["repo"])
            continue
        add(meta, entry(meta, "seed", seed=i, inherit=s))
    for q in cfg["queries"]:
        for meta in gh.search(q):
            if meta.get("fork"):
                continue
            by_desc = bool(mention.search(meta.get("description") or ""))
            by_name = bool(mention.search(meta["name"]))
            if by_desc or (by_name and meta.get("language") in langs):
                add(meta, entry(meta, "search: %s" % q))
    while queue:
        meta, parent = queue.pop(0)
        if meta.get("forks_count", 1):
            for f in gh.pages("/repos/%s/forks" % meta["full_name"]):
                add(f, entry(f, "fork", fork_of=meta["full_name"], inherit=parent))
    targets = []
    for name in sorted(found, key=str.lower):
        t = found[name]
        sha = head(t["url"] + ".git")
        if not sha:
            t["status"] = "empty"
            targets.append(t)
            continue
        c = gh.get("/repos/%s/git/commits/%s" % (name, sha)) or {}
        tree = (c.get("tree") or {}).get("sha")
        t.update({"commit": sha, "tree": tree, "status": "scored" if tree else "unreachable"})
        targets.append(t)
    return dedupe(targets)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "audit", "discover.json"))
    ap.add_argument("--targets", default=os.path.join(ROOT, "audit", "targets.json"))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    old = {}
    if os.path.exists(a.targets):
        with open(a.targets, encoding="utf-8") as f:
            old = json.load(f)
    targets = discover(cfg, GitHub(token()), os.environ.get("GITHUB_REPOSITORY"))
    new = {"schema": SCHEMA,
           "comment": "Written by tools/audit-discover.py from repository metadata only; docs/AUDIT.md. Pinned by commit and tree.",
           "discovered": time.strftime("%Y-%m-%d", time.gmtime()),
           "counts": {s: sum(1 for t in targets if t["status"] == s)
                      for s in ("scored", "duplicate", "empty", "unreachable")},
           "unresolved": cfg.get("unresolved", []),
           "targets": [{k: t[k] for k in ("repo", "url", "found_by", "fork_of", "seed", "paths", "licence",
                                          "licence_class", "commit", "tree", "status", "same_tree_as")
                        if k in t} for t in targets]}
    added, gone, moved = changes(old, new)
    print("targets: %s" % ", ".join("%d %s" % (n, s) for s, n in new["counts"].items()))
    for label, names in (("new", added), ("gone", gone), ("moved", moved)):
        print("%s: %d%s" % (label, len(names), "".join("\n  " + n for n in names)))
    if a.write:
        with open(a.targets, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("wrote %s" % os.path.relpath(a.targets, ROOT))
    return 1 if (added or gone or moved) else 0


if __name__ == "__main__":
    sys.exit(main())
