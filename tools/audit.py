#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
"""The similarity audit (R-AUDIT-1 to R-AUDIT-5; docs/AUDIT.md).

  audit.py run [--set full|fast] [--out DIR] [--jar FILE]
      Fetches each target in audit/targets.json at its pinned commit (C and
      C++ files only) into a temporary folder, with the control, and runs
      JPlag (pinned by hash, in a Java image pinned by digest, with no
      network) on our firmware and the control against them, the JieLi SDK
      and (since SR-4) the vendored Plaits, checksum-verified, as base
      code. Writes DIR/report.json and DIR/report.md: scores and
      file names only. Deletes everything it fetched, whatever happens.
      Exit status 1 if a check failed (the report says which).
  audit.py selftest [--out DIR] [--jar FILE]
      The same run against one made-up local target that holds verbatim
      copies of our files, and reformatted copies: each must be found, by
      JPlag or, for a file JPlag cannot score, by the text check
      (C-AUDIT-SELFTEST).
  audit.py check-artifact DIR
      Checks that DIR holds only a report this tool wrote (for the job that
      writes it into the record, which never sees the targets).

Nothing it prints or writes holds a line of a target's files: JPlag's own
output goes to a log in the temporary folder that is never shown, its
report archive (which embeds the sources) is read for names and numbers
only and then deleted, and before writing, every line of every target file
of at least `leak_line_chars` characters is looked for in the report
(C-AUDIT-LEAK).

A file of ours that JPlag cannot score (too few tokens, or not parsed) is
reported as such and compared as text instead: exact copies, and the share
of its normalised text found in each target file (C-AUDIT-TEXT). Like
JPlag, the text check leaves out what is in the base code (since SR-4):
pieces of our text found in a base file, and exact copies of one.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sha256sums  # noqa: E402  (tools/, our own)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = 1
REQS = {
    "C-AUDIT-JPLAG": ["R-AUDIT-4"],
    "C-AUDIT-PIN": ["R-AUDIT-2"],
    "C-AUDIT-CONTROL": ["R-AUDIT-4"],
    "C-AUDIT-SCORE": ["R-AUDIT-1", "R-AUDIT-5"],
    "C-AUDIT-LEAK": ["R-AUDIT-1", "R-AUDIT-3"],
    "C-AUDIT-TEXT": ["R-AUDIT-1", "R-AUDIT-5"],
    "C-AUDIT-SELFTEST": ["R-AUDIT-5"],
    "C-AUDIT-BASE": ["R-AUDIT-4"],
}
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ADVICE="0")
SUB = re.compile(r"^(?:new_|pool_)?([ocp]\d{5}\.[A-Za-z]+)$")
# a string or character literal (kept), or a comment (dropped), for normalise()
LITERAL_OR_COMMENT = re.compile(r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|/\*.*?\*/|//[^\n]*', re.S)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def wanted(path, suffixes, paths=None):
    if not path.lower().endswith(tuple(suffixes)):
        return False
    return not paths or any(path.startswith(p) for p in paths)


def git(args, cwd):
    """Runs git quietly: its output is never shown (it could name a target's contents)."""
    return subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=GIT_ENV)


class Unavailable(Exception):
    pass


class Mismatch(Exception):
    pass


def fetch(url, commit, tree, dest, suffixes, paths=None):
    """The commit's C/C++ files (blob-less, depth 1, sparse) in dest.
    Returns [(blob, path)] of the files on disk."""
    os.makedirs(dest)
    git(["init", "-q"], dest)
    if git(["fetch", "-q", "--depth", "1", "--filter=blob:none", url, commit], dest).returncode:
        raise Unavailable("could not fetch the pinned commit")
    got = git(["rev-parse", "FETCH_HEAD^{tree}"], dest).stdout.decode().strip()
    if tree and got != tree:
        raise Mismatch("tree %s, pinned %s" % (got[:12], tree[:12]))
    ls = git(["ls-tree", "-r", "-z", "FETCH_HEAD"], dest).stdout.decode("utf-8", "replace")
    files = []
    for rec in ls.split("\0"):
        meta, _, path = rec.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob" and parts[0] != "120000" and wanted(path, suffixes, paths):
            files.append((parts[2], path))
    if not files:
        return []
    pats = []
    for p in (paths or [""]):
        for s in suffixes:
            for v in {s, s.upper()}:
                pats.append(("/" + p + "**/*" + v) if p else ("*" + v))
    p = subprocess.run(["git", "sparse-checkout", "set", "--no-cone", "--stdin"], cwd=dest,
                       input="\n".join(pats).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=GIT_ENV)
    if p.returncode or git(["checkout", "-q", "FETCH_HEAD"], dest).returncode:
        raise Unavailable("could not check out the pinned commit's files")
    return [(b, path) for b, path in files if os.path.isfile(os.path.join(dest, path))]


class Pool:
    """Target files, one copy per blob: pool/p00001.c ..., and where each came from."""

    def __init__(self, folder):
        self.dir = folder
        os.makedirs(folder)
        self.by_blob = {}
        self.where = {}

    def add(self, blob, src, repo, path):
        new = blob not in self.by_blob
        if new:
            name = "p%05d%s" % (len(self.by_blob) + 1, os.path.splitext(path)[1].lower())
            shutil.copyfile(src, os.path.join(self.dir, name))
            self.by_blob[blob] = name
            self.where[name] = []
        name = self.by_blob[blob]
        self.where[name].append((repo, path))
        return name, new


def copy_tree_files(top, suffixes, dest, prefix):
    """Our files (or the control's): dest/<prefix>00001.c ..., and a map to their paths."""
    names = {}
    for dirpath, dirs, files in os.walk(top):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for f in sorted(files):
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, top).replace(os.sep, "/")
            if wanted(rel, suffixes) and os.path.isfile(full):
                name = "%s%05d%s" % (prefix, len(names) + 1, os.path.splitext(f)[1].lower())
                shutil.copyfile(full, os.path.join(dest, name))
                names[name] = rel
    return names


def get_jar(cfg, work, jar=None):
    dest = os.path.join(work, "jplag.jar")
    if jar:
        shutil.copyfile(jar, dest)
    else:
        with urllib.request.urlopen(cfg["jplag"]["url"], timeout=300) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    return dest, sha256_file(dest)


def run_jplag(cfg, work, sub="."):
    """JPlag in the pinned Java image, no network, on work/sub's new/ and
    base/ against work/pool/; its output goes only to a log in work/sub,
    its report to work/sub/result.jplag."""
    cmd = ["docker", "run", "--rm", "--network", "none", "--user", "%d:%d" % (os.getuid(), os.getgid()),
           "-e", "HOME=/w", "-v", "%s:/w" % work, "-w", "/w", cfg["java_image"],
           "java", "-jar", "/w/jplag.jar", "-l", "c", "-new", "/w/%s/new" % sub, "-old", "/w/pool", "-bc", "/w/%s/base" % sub,
           "-p", ",".join(cfg["suffixes"]), "-t", str(cfg["min_tokens"]), "-M", "RUN", "-r", "/w/%s/result" % sub,
           "-n", "-1", "-m", "0.000001", "--cluster-skip", "--overwrite"]
    with open(os.path.join(work, sub, "jplag.log"), "wb") as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode


def read_results(path):
    """Names and numbers from JPlag's report archive: comparisons, failed submissions, token counts."""
    with zipfile.ZipFile(path) as z:
        top = json.loads(z.read("topComparisons.json"))
        info = json.loads(z.read("runInformation.json"))
        index = json.loads(z.read("submissionFileIndex.json"))
    pairs = []
    for c in top:
        a, b = sub(c["firstSubmission"]), sub(c["secondSubmission"])
        s = c["similarities"]
        if a and b:
            pairs.append((a, b, int(s.get("LONGEST_MATCH", 0)), float(s.get("MAX", 0)), float(s.get("AVG", 0))))
    failed = {}
    for f in info.get("failedSubmissions", []):
        n = sub(f.get("submissionId", ""))
        if n:
            failed[n] = f.get("submissionState", "FAILED")
    tokens = {}
    for k, v in index.get("fileIndexes", {}).items():
        n = sub(k)
        if n:
            tokens[n] = sum(int(x.get("tokenCount", 0)) for x in v.values())
    return pairs, failed, tokens


def sub(name):
    m = SUB.match(name.split("/")[-1])
    return m.group(1) if m else None


def score(pairs, cfg, where):
    """Splits JPlag's pairs by kind and applies the gate. Pairs are
    (a, b, longest, max, avg) with a and b named o.. (ours), c.. (control)
    or p.. (a target file); where maps a target file to its (repo, path)s.

    The baseline is the control's longest match with any target it is not
    related to; a target the control itself matches above the ceiling is
    control-related, and is judged against the control's own score there.
    A pair of ours fails above its target's score plus the margin (for a
    file several targets hold, the strictest of theirs)."""
    ours, ctl, ours_ctl = [], [], []
    for a, b, l, m, v in pairs:
        k = {a[0], b[0]}
        if k == {"o", "p"}:
            o, p = (a, b) if a[0] == "o" else (b, a)
            ours.append((o, p, l, m, v))
        elif k == {"c", "p"}:
            c, p = (a, b) if a[0] == "c" else (b, a)
            ctl.append((c, p, l, m, v))
        elif k == {"o", "c"}:
            o, c = (a, b) if a[0] == "o" else (b, a)
            ours_ctl.append((o, c, l, m, v))
    best = lambda xs: sorted(xs, key=lambda x: (-x[2], -x[3], x[0], x[1]))
    per_target = {}
    for c, p, l, m, v in ctl:
        for repo, _ in where.get(p, []):
            per_target[repo] = max(per_target.get(repo, 0), l)
    related = sorted(r for r, l in per_target.items() if l > cfg["control_ceiling_tokens"])
    baseline = max([l for r, l in per_target.items() if r not in related], default=0)

    def threshold(p):
        return min([(per_target[r] if r in related else baseline) + cfg["margin_tokens"]
                    for r, _ in where.get(p, [])] or [baseline + cfg["margin_tokens"]])

    flagged = [x for x in best(ours) if x[2] > threshold(x[1])]
    return {"ours": best(ours), "control": best(ctl), "ours_control": best(ours_ctl),
            "control_max": baseline, "threshold": baseline + cfg["margin_tokens"], "flagged": flagged,
            "related": related, "control_per_target": per_target}


def split_accepted(rows, rules):
    """Flagged pairs an auditor's finding accepted (audit/accepted.json: our
    file, the target's repo and path, the longest match accepted, the
    finding) are moved out of the gate while their score stays at or below
    the accepted one; a place not covered keeps the pair flagged."""
    flagged, accepted = [], []
    for row in rows:
        def ok(t):
            return any(r["ours"] == row["ours"] and r["repo"] == t["repo"] and r["path"] == t["path"]
                       and row["longest_tokens"] <= r["longest_tokens"] for r in rules)
        if row["target_places"] == len(row["target_files"]) and row["target_files"] and all(ok(t) for t in row["target_files"]):
            accepted.append(dict(row, findings=sorted(set(r["finding"] for r in rules if r["ours"] == row["ours"]))))
        else:
            flagged.append(row)
    return flagged, accepted


def report_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from report_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from report_strings(v)


def leak(texts, folder, min_chars):
    """The name of a file in folder one of whose lines (stripped, at least
    min_chars long) occurs in texts, or None."""
    joined = "\n".join(texts)
    windows = set(joined[i:i + min_chars] for i in range(max(0, len(joined) - min_chars + 1)))
    for name in sorted(os.listdir(folder)):
        with open(os.path.join(folder, name), "rb") as f:
            text = f.read().decode("utf-8", "replace")
        for line in text.splitlines():
            s = line.strip()
            if len(s) >= min_chars and s[:min_chars] in windows and s in joined:
                return name
    return None


def base_trees(cfg):
    """The base code: [(entry, {path in the tree: bytes})] for each tree in
    cfg["base_code"], files with our suffixes only. A tree with
    "sha256sums" gives only the files its SHA256SUMS lists, each matching
    its hash (tools/sha256sums.py), or ValueError; a tree without gives its
    files. A tree with "only_for" is base code only for our files under
    that folder (since SR-4)."""
    out = []
    for b in cfg["base_code"]:
        top = os.path.join(ROOT, b["path"])
        if not os.path.isdir(top):
            raise ValueError("base code %s is not on disk" % b["path"])
        if b.get("sha256sums"):
            try:
                files = sha256sums.verified(top)
            except (OSError, ValueError) as e:
                raise ValueError("base code %s: %s" % (b["path"], e))
        else:
            files = {}
            for dirpath, dirs, names in os.walk(top):
                dirs.sort()
                for n in sorted(names):
                    rel = os.path.relpath(os.path.join(dirpath, n), top).replace(os.sep, "/")
                    with open(os.path.join(dirpath, n), "rb") as f:
                        files[rel] = f.read()
        out.append((b, {rel: data for rel, data in files.items() if wanted(rel, cfg["suffixes"])}))
    return out


INCLUDE = re.compile(rb'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)


def includes_from(data, files):
    """The first #include in data (C text) that names one of files (paths in
    a base tree), or None. Only an include with a folder in it counts
    ("plaits/dsp/voice.h", not "voice.h"), matched against the end of a
    listed path, either way round ("../vendor/plaits/eurorack/plaits/x.h")."""
    for m in INCLUDE.finditer(data):
        inc = m.group(1).decode("utf-8", "replace").replace("\\", "/")
        if "/" not in inc:
            continue
        bare = inc.lstrip("./")
        for path in files:
            if path == bare or path.endswith("/" + bare) or bare.endswith("/" + path):
                return inc
    return None


def groups(cfg, ours, read, trees):
    """Splits our files (name -> path under cfg["ours"]) into JPlag passes,
    each with its own base code (since SR-4): first our files outside every
    "only_for" folder, with the base trees that have none; then, for each
    tree with one, our files under it, with the general trees plus that one
    (a pass with no files is left out). A file outside a tree's folder that
    includes one of its files fails (ValueError): it doesn't get that base
    code silently, the owner decides. read(name) gives a file's bytes.
    Returns [(label, {name: path}, [(entry, files)])]."""
    general = [t for t in trees if not t[0].get("only_for")]
    scoped = [t for t in trees if t[0].get("only_for")]

    def under(path, folder):
        return (cfg["ours"] + "/" + path).startswith(folder.rstrip("/") + "/")

    core = {n: p for n, p in ours.items() if not any(under(p, t[0]["only_for"]) for t in scoped)}
    for n, p in sorted(core.items()):
        for entry, files in scoped:
            inc = includes_from(read(n), files)
            if inc:
                raise ValueError("%s/%s includes %s from %s, which is base code only under %s/; it is not given "
                                 "that base code silently: the owner decides (docs/AUDIT.md, \"Base code\")"
                                 % (cfg["ours"], p, inc, entry["path"], entry["only_for"].rstrip("/")))
    out = [("all of our files" if not scoped else "our files outside %s" %
            ", ".join(t[0]["only_for"].rstrip("/") + "/" for t in scoped), core, general)]
    for t in scoped:
        mine = {n: p for n, p in ours.items() if under(p, t[0]["only_for"])}
        if mine:
            out.append(("our files under %s/" % t[0]["only_for"].rstrip("/"), mine, general + [t]))
    return out


def normalise(text):
    """C text without comments or whitespace, for the text check: string and
    character literals are kept, so a comment marker inside one stays."""
    return re.sub(r"\s+", "", LITERAL_OR_COMMENT.sub(lambda m: m.group(0) if m.group(0)[0] in "\"'" else " ", text))


def grams(text, k):
    """The distinct k-character pieces of text (the whole text if shorter)."""
    return {text[i:i + k] for i in range(len(text) - k + 1)} or ({text} if text else set())


def text_scores(ours, folder, k, base=()):
    """The text check: for each of our files (name -> bytes), every file in
    folder (one per target blob) it is near: (ours, target, containment,
    exact), where containment is the share of our normalised text's
    k-character pieces found in the target file's, and exact means the same
    bytes. Pieces found in a base file (base: an iterable of bytes) don't
    count, and a file of ours that is a base file's bytes is never exact,
    as JPlag drops matches with base code. Pairs sharing nothing are left
    out."""
    mine = {}
    for n, data in ours.items():
        text = normalise(data.decode("utf-8", "replace"))
        mine[n] = (data, text, grams(text, k))
    in_base, base_bytes = set(), set()
    wanted_pieces = set().union(*(g for _, _, g in mine.values())) if mine else set()
    for data in base:
        base_bytes.add(data)
        if wanted_pieces:
            in_base |= wanted_pieces & grams(normalise(data.decode("utf-8", "replace")), k)
    if in_base or base_bytes:
        mine = {n: (ob if ob not in base_bytes else None, ot, og - in_base) for n, (ob, ot, og) in mine.items()}
    out = []
    for name in sorted(os.listdir(folder)):
        with open(os.path.join(folder, name), "rb") as f:
            data = f.read()
        text = normalise(data.decode("utf-8", "replace"))
        theirs = None
        for n, (ob, ot, og) in mine.items():
            if not og:
                continue
            if ot in text:
                c = 1.0
            else:
                if theirs is None:
                    theirs = grams(text, k)
                c = len(og & theirs) / len(og)
            if c > 0 or data == ob:
                out.append((n, name, c, data == ob))
    return sorted(out, key=lambda x: (-x[3], -x[2], x[0], x[1]))


def not_scorable(state, cfg):
    """Why JPlag could not score a file of ours, for the report."""
    why = {"TOO_SMALL": "fewer tokens than JPlag's minimum match of %d" % cfg["min_tokens"],
           "CANNOT_PARSE": "JPlag's C front end could not parse it"}.get(state, "JPlag reports it as %s" % state)
    return "not scorable by JPlag: %s (%s); compared by the text check instead" % (why, state)


def text_row(x, ours_names, where, licences, limit=10):
    """A text-check pair for the report: our file, the scores and the target
    files (repository and path) holding that blob."""
    o, p, c, exact = x
    places = [{"repo": r, "path": path, "licence_class": licences.get(r, "none")} for r, path in where.get(p, [])]
    return {"ours": ours_names.get(o, o), "containment": round(c, 4), "exact": exact,
            "target_files": places[:limit] if limit else places, "target_places": len(places)}


def pair_row(x, ours_names, where, licences, limit=10):
    """A pair for the report: our file's path, the scores, and the target files
    (repository and path) holding that blob, the first `limit` of them."""
    o, p, l, m, v = x
    places = [{"repo": r, "path": path, "licence_class": licences.get(r, "none")} for r, path in where.get(p, [])]
    return {"ours": ours_names.get(o, o), "longest_tokens": l, "max": round(m, 4), "avg": round(v, 4),
            "target_files": places[:limit] if limit else places, "target_places": len(places)}


def run(cfg, targets_doc, set_name, out, jar=None, selftest=None):
    """One audit. selftest: a list of target dicts used instead of targets_doc's."""
    t0 = time.time()
    checks = {}
    base_tmp = os.environ.get("RUNNER_TEMP") or None
    work = tempfile.mkdtemp(prefix="audit-", dir=base_tmp)
    report = {"schema": SCHEMA, "set": set_name, "commit": os.environ.get("GITHUB_SHA") or
              git(["rev-parse", "HEAD"], ROOT).stdout.decode().strip(),
              "run": ("%s/%s/actions/runs/%s" % (os.environ["GITHUB_SERVER_URL"], os.environ["GITHUB_REPOSITORY"],
                                                os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else None),
              "jplag": {"version": cfg["jplag"]["version"], "sha256": cfg["jplag"]["sha256"]},
              "java_image": cfg["java_image"], "margin_tokens": cfg["margin_tokens"],
              "control_ceiling_tokens": cfg["control_ceiling_tokens"], "min_tokens": cfg["min_tokens"]}
    try:
        os.makedirs(os.path.join(work, "new"))
        jar_path, got = get_jar(cfg, work, jar)
        jar_ok = got == cfg["jplag"]["sha256"] and "@sha256:" in cfg["java_image"]
        checks["C-AUDIT-JPLAG"] = ("PASS" if jar_ok else "FAIL",
                                   "jar sha256 %s; Java image pinned by digest" % ("matches" if jar_ok else "differs: " + got))
        if not jar_ok:
            raise RuntimeError("JPlag is not the pinned jar")
        ours = copy_tree_files(os.path.join(ROOT, cfg["ours"]), cfg["suffixes"], os.path.join(work, "new"), "o")
        trees = base_trees(cfg)
        report["base_code"] = [dict({"path": b["path"], "checksums": bool(b.get("sha256sums")), "files": len(f)},
                                    **({"only_for": b["only_for"]} if b.get("only_for") else {})) for b, f in trees]

        def read_ours(n):
            with open(os.path.join(work, "new", n), "rb") as fh:
                return fh.read()
        try:
            passes = groups(cfg, ours, read_ours, trees)
        except ValueError as e:
            checks["C-AUDIT-BASE"] = ("FAIL", str(e))
            raise
        checks["C-AUDIT-BASE"] = ("PASS", "; ".join(
            "%s (%d): base code %s" % (label, len(mine), " and ".join(
                "%s (%d files%s)" % (b["path"], len(f), ", checksums verified" if b.get("sha256sums") else "")
                for b, f in tr)) for label, mine, tr in passes))
        c = cfg["control"]
        ctl_dir = os.path.join(work, "control")
        problems = []
        try:
            fetch(c["url"], c["commit"], c["tree"], ctl_dir, cfg["suffixes"])
        except (Unavailable, Mismatch) as e:
            problems.append("control %s: %s" % (c["repo"], e))
        control = copy_tree_files(ctl_dir, cfg["suffixes"], os.path.join(work, "new"), "c")
        shutil.rmtree(ctl_dir, ignore_errors=True)
        report["control"] = {"repo": c["repo"], "commit": c["commit"], "licence": c["licence"], "files": len(control)}

        all_targets = selftest if selftest is not None else targets_doc["targets"]
        chosen = [t for t in all_targets if t.get("status") == "scored" and (set_name != "fast" or t["repo"] in cfg["fast"])]
        pool = Pool(os.path.join(work, "pool"))
        licences = {t["repo"]: t.get("licence_class", "none") for t in all_targets}
        rows = []

        def fetch_one(i, t):
            tdir = os.path.join(work, "t%05d" % i)
            try:
                url = t["url"] if selftest is not None else t["url"] + ".git"
                return tdir, fetch(url, t["commit"], t.get("tree"), tdir, cfg["suffixes"], t.get("paths")), None
            except (Unavailable, Mismatch) as e:
                return tdir, None, e

        # fetched side by side, but added to the pool in the list's order, so its names are stable
        with ThreadPoolExecutor(max_workers=cfg.get("fetch_workers", 8)) as ex:
            futures = [ex.submit(fetch_one, i, t) for i, t in enumerate(chosen)]
            for t, fut in zip(chosen, futures):
                tdir, files, err = fut.result()
                row = {"repo": t["repo"], "commit": t["commit"], "licence": t.get("licence"),
                       "licence_class": t.get("licence_class", "none")}
                if err is None:
                    new = 0
                    for blob, path in files:
                        _, is_new = pool.add(blob, os.path.join(tdir, path), t["repo"], path)
                        new += is_new
                    row.update({"fetched": True, "files": len(files), "new_files": new})
                elif isinstance(err, Mismatch):
                    row.update({"fetched": False, "why": "tree mismatch: " + str(err)})
                    problems.append("%s: tree mismatch" % t["repo"])
                else:
                    row.update({"fetched": False, "why": str(err)})
                shutil.rmtree(tdir, ignore_errors=True)
                rows.append(row)
        unavailable = [r["repo"] for r in rows if not r["fetched"] and not r.get("why", "").startswith("tree")]
        checks["C-AUDIT-PIN"] = ("FAIL" if problems else "PASS",
                                 "%d targets fetched at their pinned commit and tree; %d unavailable%s"
                                 % (sum(r["fetched"] for r in rows), len(unavailable),
                                    ("; " + "; ".join(problems)) if problems else ""))
        report["targets"] = rows
        if targets_doc and selftest is None:
            report["unresolved"] = [u["name"] for u in targets_doc.get("unresolved", [])]
            report["not_scored"] = {s: sum(1 for t in all_targets if t.get("status") == s)
                                    for s in ("duplicate", "empty", "unreachable")}
        report["pool_files"] = len(pool.where)

        if not pool.where:
            raise RuntimeError("no target files were fetched")
        # One JPlag pass per group of our files, each with its own base code
        # and the control scored again under it (since SR-4).
        tc = cfg["text_check"]
        failed, tokens, text, s, report["passes"] = {}, {}, [], None, []
        for i, (label, mine, tr) in enumerate(passes):
            sub = "g%d" % i
            for d in ("new", "base"):
                os.makedirs(os.path.join(work, sub, d))
            for n in list(mine) + list(control):
                shutil.copyfile(os.path.join(work, "new", n), os.path.join(work, sub, "new", n))
            for j, (b, files) in enumerate(tr, 1):
                for rel, data in files.items():
                    os.makedirs(os.path.dirname(os.path.join(work, sub, "base", "b%d" % j, rel)), exist_ok=True)
                    with open(os.path.join(work, sub, "base", "b%d" % j, rel), "wb") as fh:
                        fh.write(data)
            code = run_jplag(cfg, work, sub)
            result = os.path.join(work, sub, "result.jplag")
            if code or not os.path.exists(result):
                raise RuntimeError("JPlag failed (exit %d); its log is not shown, as it can quote the files" % code)
            pairs, f_i, t_i = read_results(result)
            os.remove(result)
            s_i = score(pairs, cfg, pool.where)
            failed.update({n: v for n, v in f_i.items() if n in mine or (i == 0 and n in control)})
            tokens.update({n: v for n, v in t_i.items() if n in mine or (i == 0 and n in control)})
            # A file JPlag could not score at all goes to the text check
            # instead, with the same base code; a file it scored that matched
            # nothing ("no match") does not.
            unscorable_i = {n: read_ours(n) for n in sorted(mine) if n in f_i}
            if unscorable_i:
                text += text_scores(unscorable_i, pool.dir, tc["k"], [d for _, f in tr for d in f.values()])
            report["passes"].append({"files": label, "count": len(mine), "base_code": [b["path"] for b, _ in tr],
                                     "control_max_tokens": s_i["control_max"], "threshold_tokens": s_i["threshold"],
                                     "control_related": s_i["related"]})
            if s is None:
                s = s_i
            else:
                s["ours"] = sorted(s["ours"] + s_i["ours"], key=lambda x: (-x[2], -x[3], x[0], x[1]))
                s["ours_control"] = sorted(s["ours_control"] + s_i["ours_control"],
                                           key=lambda x: (-x[2], -x[3], x[0], x[1]))
                s["flagged"] = sorted(s["flagged"] + s_i["flagged"], key=lambda x: (-x[2], -x[3], x[0], x[1]))
                s["related_extra"] = s.get("related_extra", []) + [s_i["related"]]
            shutil.rmtree(os.path.join(work, sub), ignore_errors=True)
        text.sort(key=lambda x: (-x[3], -x[2], x[0], x[1]))
        names = dict(ours)
        names.update(control)
        # JPlag leaves a file that matched nothing (no run of min_tokens) out
        # of its index, so its token count is unknown; it was still compared.
        report["ours_files"] = [{"file": p, "tokens": tokens.get(n), "state": failed.get(n, "scored" if n in tokens else "no match")}
                                for n, p in sorted(ours.items())]
        unscorable = sorted(n for n in ours if n in failed)
        for f, n in zip(report["ours_files"], sorted(ours)):
            if n in failed:
                f["not_scorable"] = not_scorable(failed[n], cfg)
        text_flagged = [x for x in text if x[3] or x[2] >= tc["threshold"]]
        best_text = {}
        for x in text:
            best_text.setdefault(x[0], x)
        report["text_check"] = {"k": tc["k"], "threshold": tc["threshold"], "files": [ours[n] for n in unscorable],
                                "best": [text_row(best_text[n], ours, pool.where, licences) if n in best_text else
                                         {"ours": ours[n], "containment": 0.0, "exact": False, "target_files": [],
                                          "target_places": 0} for n in unscorable],
                                "top_pairs": [text_row(x, ours, pool.where, licences) for x in text[:cfg["top_pairs"]]],
                                "flagged": [text_row(x, ours, pool.where, licences, limit=None) for x in text_flagged]}
        text_check = ("FAIL" if text_flagged else "PASS",
                                  ("%d of our files not scorable by JPlag (%s), compared as text with %d target files; "
                                   "%d pairs an exact copy or at or above %.2f of %d-character pieces"
                                   % (len(unscorable), ", ".join(ours[n] for n in unscorable), len(pool.where),
                                      len(text_flagged), tc["threshold"], tc["k"])) if unscorable else
                                  "every file of ours was scored by JPlag; none needed the text check")
        report["control_max_tokens"] = s["control_max"]
        report["threshold_tokens"] = s["threshold"]
        report["top_pairs"] = [pair_row(x, ours, pool.where, licences) for x in s["ours"][:cfg["top_pairs"]]]
        report["control_top_pairs"] = [pair_row(x, control, pool.where, licences) for x in s["control"][:5]]
        report["ours_vs_control_best"] = ([{"ours": ours.get(x[0]), "control": control.get(x[1]), "longest_tokens": x[2],
                                            "max": round(x[3], 4)} for x in s["ours_control"][:3]])
        by_repo_ours, by_repo_ctl = {}, s["control_per_target"]
        for x in s["ours"]:
            for r, _ in pool.where.get(x[1], []):
                by_repo_ours[r] = max(by_repo_ours.get(r, 0), x[2])
        unparsed = {}
        for n, state in failed.items():
            for r, _ in pool.where.get(n, []):
                unparsed.setdefault(r, {}).setdefault(state.lower(), 0)
                unparsed[r][state.lower()] += 1
        for row in rows:
            row["ours_longest_tokens"] = by_repo_ours.get(row["repo"], 0)
            row["control_longest_tokens"] = by_repo_ctl.get(row["repo"], 0)
            row["not_parsed"] = unparsed.get(row["repo"], {})
        accepted_rules = load_json(os.path.join(ROOT, "audit", "accepted.json")).get("accepted", []) \
            if os.path.exists(os.path.join(ROOT, "audit", "accepted.json")) else []
        flagged, accepted = split_accepted([pair_row(x, ours, pool.where, licences, limit=None) for x in s["flagged"]],
                                           accepted_rules)
        s["flagged"] = flagged
        report["flagged"] = flagged
        report["accepted"] = accepted
        report["control_related"] = s["related"]
        fetched = sum(r["fetched"] for r in rows)
        ctl_ok = bool(control) and all(len(r) <= cfg["control_related_share"] * max(fetched, 1)
                                       for r in [s["related"]] + s.get("related_extra", []))
        checks["C-AUDIT-CONTROL"] = ("PASS" if ctl_ok else "FAIL",
                                     "%d control files; its longest match with an unrelated target %d tokens; "
                                     "%d of %d targets control-related (above %d tokens; at most %d%% allowed)"
                                     % (len(control), s["control_max"], len(s["related"]), fetched,
                                        cfg["control_ceiling_tokens"], round(100 * cfg["control_related_share"])))
        checks["C-AUDIT-SCORE"] = ("FAIL" if s["flagged"] else "PASS",
                                   "%d of our file pairs above %d tokens (the control's %d plus %d; for a "
                                   "control-related target, its own score plus %d)%s"
                                   % (len(s["flagged"]), s["threshold"], s["control_max"], cfg["margin_tokens"],
                                      cfg["margin_tokens"],
                                      "; %d more accepted by an auditor's finding" % len(accepted) if accepted else "")
                                   + "".join("; %s: above %d tokens (the control's %d under that base code plus %d)"
                                             % (q["files"], q["threshold_tokens"], q["control_max_tokens"],
                                                cfg["margin_tokens"]) for q in report["passes"][1:]))
        checks["C-AUDIT-TEXT"] = text_check
        if selftest is not None:
            report["selftest"] = {"ours_best": [[ours.get(x[0], x[0])] + list(x[1:]) for x in s["ours"]],
                                  "text": [[ours.get(x[0], x[0]), pool.where[x[1]][0][1], x[2], x[3]] for x in text]}
        report["seconds"] = round(time.time() - t0, 1)
        write_report(report, checks, out, pool.dir, cfg)
    except Exception as e:  # the report says what failed; nothing from the targets is printed
        checks.setdefault("C-AUDIT-SCORE", ("FAIL", "not scored: %s" % e))
        report["error"] = str(e)
        report["seconds"] = round(time.time() - t0, 1)
        pool_dir = os.path.join(work, "pool")
        write_report(report, checks, out, pool_dir if os.path.isdir(pool_dir) else None, cfg)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    gone = not os.path.exists(work)
    print("temporary folder removed: %s" % ("yes" if gone else "NO"))
    return report, checks


def traceability(checks):
    table = []
    for req in sorted(set(r for rs in REQS.values() for r in rs)):
        mine = [c for c, rs in REQS.items() if req in rs and c in checks]
        res = [checks[c][0] for c in mine]
        table.append({"requirement": req, "checks": mine,
                      "result": "FAIL" if "FAIL" in res else "PASS" if res else "not run"})
    return table


def write_report(report, checks, out, pool_dir, cfg):
    report["checks"] = [{"id": k, "result": v[0], "detail": v[1], "reqs": REQS[k]} for k, v in checks.items()]
    report["traceability"] = traceability(checks)
    md = markdown(report)
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if pool_dir:
        hit = leak([md] + list(report_strings(report)), pool_dir, cfg["leak_line_chars"])
        report["checks"].append({"id": "C-AUDIT-LEAK", "result": "FAIL" if hit else "PASS", "reqs": REQS["C-AUDIT-LEAK"],
                                 "detail": "a line of a target file is in the report; report withheld" if hit else
                                 "no line of a target file (%d characters or more) in the report" % cfg["leak_line_chars"]})
        if hit:
            report = {k: report[k] for k in ("schema", "set", "commit", "run", "checks")}
        report["traceability"] = traceability({c["id"]: (c["result"], "") for c in report["checks"]})
        md = markdown(report)
        text = json.dumps(report, indent=1, ensure_ascii=False)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(md)


def markdown(r):
    L = ["# Similarity audit %s" % (r.get("commit") or "")[:12], "",
         "- Set: %s; run: %s" % (r.get("set"), r.get("run") or "local"),
         "- JPlag %s (sha256 `%s`), Java image `%s`" % (r.get("jplag", {}).get("version"),
                                                        r.get("jplag", {}).get("sha256", "")[:16], r.get("java_image", "")),
         ""]
    if "threshold_tokens" in r:
        L += ["- Control: %s at `%s`, %s files" % (r["control"]["repo"], r["control"]["commit"][:12], r["control"]["files"]),
              "- The control's longest match with any target it is not related to: **%d tokens**; a pair of ours "
              "fails above **%d tokens** (margin %d)." % (r["control_max_tokens"], r["threshold_tokens"], r["margin_tokens"]),
              "- Control-related targets (the control matches them above %d tokens; each judged against the "
              "control's own score there plus the margin): %s" % (r["control_ceiling_tokens"],
                                                                  ", ".join(r.get("control_related", [])) or "none"),
              "- Target files scored: %d (one copy per blob)" % r.get("pool_files", 0)]
        L += ["- Base code (JPlag and the text check leave out what is in it): %s"
              % "; ".join("`%s`, %d files%s%s" % (b["path"], b["files"], ", checksums verified" if b["checksums"] else "",
                                                 ", only for `%s/`" % b["only_for"] if b.get("only_for") else "")
                          for b in r.get("base_code", []))]
        for q in r.get("passes", [])[1:]:
            L.append("- A pass of its own for %s (%d): the control's longest match there %d tokens, so a pair fails "
                     "above **%d tokens**" % (q["files"], q["count"], q["control_max_tokens"], q["threshold_tokens"]))
        L.append("")
    if r.get("error"):
        L += ["**Not scored:** %s" % r["error"], ""]
    L += ["## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    for c in r.get("checks", []):
        L.append("| %s | %s | %s |" % (c["id"], c["result"], c["detail"]))
    if r.get("flagged"):
        L += ["", "## Flagged pairs (an auditor compares these; nobody else opens them)", "",
              "| Our file | Target | Path | Licence | Longest | Max |", "|---|---|---|---|---|---|"]
        for p in r["flagged"]:
            for t in p["target_files"]:
                L.append("| %s | %s | %s | %s | %d | %.3f |" % (p["ours"], t["repo"], t["path"], t["licence_class"],
                                                               p["longest_tokens"], p["max"]))
    if "top_pairs" in r and not r["top_pairs"]:
        L += ["", "## Our top file pairs", "", "None: no file of ours shares a run of %d tokens or more with any target file."
              % r.get("min_tokens", 12)]
    if r.get("top_pairs"):
        L += ["", "## Our top file pairs", "", "| Our file | Target (places with this file) | Path | Licence | Longest | Max | Avg |",
              "|---|---|---|---|---|---|---|"]
        for p in r["top_pairs"]:
            t = p["target_files"][0] if p["target_files"] else {"repo": "?", "path": "?", "licence_class": "?"}
            L.append("| %s | %s (%d) | %s | %s | %d | %.3f | %.3f |" % (p["ours"], t["repo"], p["target_places"], t["path"],
                                                                     t["licence_class"], p["longest_tokens"], p["max"], p["avg"]))
    if r.get("ours_files"):
        L += ["", "## Our files", "", "| File | Tokens | State |", "|---|---|---|"]
        for f in r["ours_files"]:
            L.append("| %s | %s | %s |" % (f["file"], f["tokens"] if f["tokens"] is not None else "-",
                                           f.get("not_scorable", f["state"])))
    tc = r.get("text_check")
    if tc and tc["files"]:
        L += ["", "## The text check (our files JPlag cannot score)", "",
              "Each is compared with every target file, one per blob: the share of its normalised text's "
              "%d-character pieces found in the target file (containment), and whether the bytes are the same "
              "(exact). A pair fails at %.2f or above, or when exact." % (tc["k"], tc["threshold"]), "",
              "| Our file | Target (places with this file) | Path | Licence | Containment | Exact |", "|---|---|---|---|---|---|"]
        for p in tc["top_pairs"] or tc["best"]:
            t = p["target_files"][0] if p["target_files"] else {"repo": "-", "path": "-", "licence_class": "-"}
            L.append("| %s | %s (%d) | %s | %s | %.3f | %s |" % (p["ours"], t["repo"], p["target_places"], t["path"],
                                                               t["licence_class"], p["containment"],
                                                               "yes" if p["exact"] else "no"))
        if tc["flagged"]:
            L += ["", "Flagged by the text check (an auditor compares these; nobody else opens them):", "",
                  "| Our file | Target | Path | Licence | Containment | Exact |", "|---|---|---|---|---|---|"]
            for p in tc["flagged"]:
                for t in p["target_files"]:
                    L.append("| %s | %s | %s | %s | %.3f | %s |" % (p["ours"], t["repo"], t["path"], t["licence_class"],
                                                                  p["containment"], "yes" if p["exact"] else "no"))
    if r.get("targets"):
        L += ["", "## Targets", "", "| Target | Commit | Licence | Files (new) | Ours longest | Control longest | Not parsed |",
              "|---|---|---|---|---|---|---|"]
        for t in r["targets"]:
            if t.get("fetched"):
                np = ", ".join("%s %d" % kv for kv in sorted(t.get("not_parsed", {}).items())) or "0"
                L.append("| %s | `%s` | %s | %d (%d) | %s | %s | %s |" % (
                    t["repo"], t["commit"][:12], t["licence_class"], t["files"], t["new_files"],
                    t.get("ours_longest_tokens", "-"), t.get("control_longest_tokens", "-"), np))
            else:
                L.append("| %s | `%s` | %s | not fetched: %s | | | |" % (t["repo"], t["commit"][:12], t["licence_class"], t.get("why")))
    if "not_scored" in r:
        L += ["", "Not scored: %s. Unresolved (no repository found): %s." % (
            ", ".join("%d %s" % (v, k) for k, v in r["not_scored"].items()), ", ".join(r.get("unresolved", [])) or "none")]
    L += ["", "## Traceability", "", "| Requirement | Checks | Result |", "|---|---|---|"]
    for t in r.get("traceability", []):
        L.append("| %s | %s | %s |" % (t["requirement"], ", ".join(t["checks"]), t["result"]))
    L.append("")
    return "\n".join(L)


def reformat(text):
    """A near-exact copy for the self-test: no comments, each line
    re-indented, and a comment of its own at the top, so the bytes differ."""
    text = LITERAL_OR_COMMENT.sub(lambda m: m.group(0) if m.group(0)[0] in "\"'" else " ", text)
    lines = ["\t" + line.strip() if not line.lstrip().startswith("#") else line.strip()
             for line in text.splitlines() if line.strip()]
    return "/* reformatted */\n" + "\n".join(lines) + "\n"


def selftest_target(work_parent, cfg):
    """A made-up local target: verbatim and reformatted copies of our files
    and one unrelated file, in a git repository served by path. Returns
    (target dict, its folder)."""
    d = tempfile.mkdtemp(prefix="audit-selftest-", dir=work_parent)
    src = os.path.join(ROOT, cfg["ours"])
    for dirpath, _, files in os.walk(src):
        for f in files:
            if wanted(f, cfg["suffixes"]):
                rel = os.path.relpath(os.path.join(dirpath, f), src)
                os.makedirs(os.path.join(d, "copied", os.path.dirname(rel)), exist_ok=True)
                shutil.copyfile(os.path.join(dirpath, f), os.path.join(d, "copied", rel))
                os.makedirs(os.path.join(d, "reformatted", os.path.dirname(rel)), exist_ok=True)
                with open(os.path.join(dirpath, f), encoding="utf-8") as fin, \
                        open(os.path.join(d, "reformatted", rel), "w", encoding="utf-8") as fout:
                    fout.write(reformat(fin.read()))
    with open(os.path.join(d, "unrelated.c"), "w") as f:
        f.write("int unrelated(int a) { return a * 3 + 1; }\n")
    env = dict(GIT_ENV, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "selftest"],
                 ["config", "uploadpack.allowFilter", "true"], ["config", "uploadpack.allowAnySHA1InWant", "true"]):
        subprocess.run(["git"] + args, cwd=d, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    commit = git(["rev-parse", "HEAD"], d).stdout.decode().strip()
    tree = git(["rev-parse", "HEAD^{tree}"], d).stdout.decode().strip()
    return {"repo": "selftest/copy-of-ours", "url": "file://" + d, "commit": commit, "tree": tree,
            "status": "scored", "licence_class": "none"}, d


def selftest_verdict(report, cfg):
    """Every one of our files must be found in the made-up target, and the
    report written. A file JPlag scored: by a match covering at least 90% of
    its tokens. A file JPlag cannot score: by the text check, as an exact copy
    (the verbatim one) and at or above its threshold without being exact (the
    reformatted one). A file JPlag scored but matched nowhere fails."""
    files = report.get("ours_files", [])
    tokens = {f["file"]: f["tokens"] for f in files if f["state"] == "scored"}
    best = {}
    for o, p, l, m, v in report.get("selftest", {}).get("ours_best", []):
        best[o] = max(best.get(o, 0), l)
    by_jplag = [f for f, t in tokens.items() if best.get(f, 0) >= 0.9 * t]
    exact, near = set(), set()
    for o, path, c, is_exact in report.get("selftest", {}).get("text", []):
        if is_exact:
            exact.add(o)
        elif c >= cfg["text_check"]["threshold"]:
            near.add(o)
    by_text = [f["file"] for f in files if "not_scorable" in f and f["file"] in exact & near]
    leak_ok = any(c["id"] == "C-AUDIT-LEAK" and c["result"] == "PASS" for c in report.get("checks", []))
    found = len(by_jplag) + len(by_text)
    ok = bool(files) and found == len(files) and leak_ok
    return ok, "%d of our %d files found in a target holding copies of them (%d by JPlag, %d by the text check); " \
        "leak check %s" % (found, len(files), len(by_jplag), len(by_text), "PASS" if leak_ok else "not passed")


def check_artifact(folder):
    names = sorted(os.listdir(folder))
    if names != ["report.json", "report.md"]:
        return ["unexpected files: %s" % names]
    problems = []
    for n in names:
        if os.path.getsize(os.path.join(folder, n)) > 2 << 20:
            problems.append("%s is too large" % n)
    r = load_json(os.path.join(folder, "report.json"))
    if r.get("schema") != SCHEMA or not isinstance(r.get("checks"), list):
        problems.append("report.json is not an audit report")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["run", "selftest", "check-artifact"])
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--set", default="full", choices=["full", "fast"])
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "audit"))
    ap.add_argument("--jar")
    ap.add_argument("--config", default=os.path.join(ROOT, "audit", "audit.json"))
    ap.add_argument("--targets", default=os.path.join(ROOT, "audit", "targets.json"))
    a = ap.parse_args(argv)
    if a.command == "check-artifact":
        problems = check_artifact(a.dir)
        for p in problems:
            print("FAIL %s" % p)
        print("artifact: %s" % ("FAIL" if problems else "PASS"))
        return 1 if problems else 0
    cfg = load_json(a.config)
    if a.command == "selftest":
        t, d = selftest_target(os.environ.get("RUNNER_TEMP") or None, cfg)
        try:
            report, checks = run(cfg, None, "selftest", a.out, a.jar, selftest=[t])
        finally:
            shutil.rmtree(d, ignore_errors=True)
        ok, detail = selftest_verdict(report, cfg)
        print("C-AUDIT-SELFTEST: %s (%s)" % ("PASS" if ok else "FAIL", detail))
        for c in report.get("checks", []):
            print("  %s %s: %s" % (c["id"], c["result"], c["detail"]))
        return 0 if ok else 1
    report, checks = run(cfg, load_json(a.targets), a.set, a.out, a.jar)
    for c in report.get("checks", []):
        print("%s %s: %s" % (c["id"], c["result"], c["detail"]))
    failed = [c["id"] for c in report.get("checks", []) if c["result"] != "PASS"]
    print("audit: %s" % ("FAIL (%s)" % ", ".join(failed) if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
