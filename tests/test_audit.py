# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import tempfile
import unittest
import zipfile

from tests.helpers import ROOT, load_tool

audit = load_tool("audit.py")
disc = load_tool("audit-discover.py")
CFG = {"margin_tokens": 24, "control_ceiling_tokens": 100, "control_related_share": 0.1, "leak_line_chars": 24}


class DiscoverTest(unittest.TestCase):
    """Requirements: R-AUDIT-2"""

    def test_licence_classes(self):
        for spdx, cls in (("GPL-3.0", "gpl"), ("AGPL-3.0", "gpl"), ("LGPL-2.1", "gpl"), ("MIT", "permissive"),
                          ("BSD-3-Clause", "permissive"), ("WTFPL", "permissive"), ("MPL-2.0", "other"),
                          ("NOASSERTION", "other"), (None, "none")):
            self.assertEqual(disc.licence_class(spdx), cls, spdx)

    def test_dedupe_keeps_the_first_by_tree_seeds_first(self):
        ts = [{"repo": "a/fork", "fork_of": "x/up", "tree": "t1", "status": "scored"},
              {"repo": "x/up", "seed": 1, "tree": "t1", "status": "scored"},
              {"repo": "b/other", "tree": "t2", "status": "scored"},
              {"repo": "c/fork", "fork_of": "b/other", "tree": "t2", "status": "scored"},
              {"repo": "d/sub", "tree": "t1", "paths": ["sub/"], "status": "scored"},
              {"repo": "e/empty", "status": "empty"}]
        got = {t["repo"]: (t["status"], t.get("same_tree_as")) for t in disc.dedupe(ts)}
        self.assertEqual(got["x/up"], ("scored", None))
        self.assertEqual(got["a/fork"], ("duplicate", "x/up"))
        self.assertEqual(got["c/fork"], ("duplicate", "b/other"))
        self.assertEqual(got["d/sub"], ("scored", None), "the same tree with other paths is scored")
        self.assertEqual(got["e/empty"], ("empty", None))

    def test_changes_name_new_gone_and_moved(self):
        old = {"targets": [{"repo": "a/a", "commit": "1"}, {"repo": "b/b", "commit": "2"}]}
        new = {"targets": [{"repo": "a/a", "commit": "9"}, {"repo": "c/c", "commit": "3"}]}
        self.assertEqual(disc.changes(old, new), (["c/c"], ["b/b"], ["a/a"]))

    def test_committed_targets_are_pinned(self):
        doc = audit.load_json(os.path.join(ROOT, "audit", "targets.json"))
        self.assertTrue(doc["targets"])
        for t in doc["targets"]:
            self.assertIn(t["licence_class"], ("gpl", "permissive", "other", "none"), t["repo"])
            if t["status"] in ("scored", "duplicate"):
                self.assertRegex(t["commit"], r"^[0-9a-f]{40}$", t["repo"])
                self.assertRegex(t["tree"], r"^[0-9a-f]{40}$", t["repo"])
            if t["status"] == "duplicate":
                self.assertIn(t["same_tree_as"], {x["repo"] for x in doc["targets"]})
        names = {t["repo"] for t in doc["targets"]}
        for seed in audit.load_json(os.path.join(ROOT, "audit", "discover.json"))["seeds"]:
            self.assertIn(seed["repo"], names)
        self.assertEqual(sorted(u["name"] for u in doc["unresolved"]), ["Felucca 8 Patterns", "Felucca Salt"])


class ScoreTest(unittest.TestCase):
    """Requirements: R-AUDIT-1, R-AUDIT-4, R-AUDIT-5"""

    def test_names_from_jplag(self):
        self.assertEqual(audit.sub("new_o00001.c"), "o00001.c")
        self.assertEqual(audit.sub("pool/p00042.h"), "p00042.h")
        self.assertEqual(audit.sub("new/c00003.cpp"), "c00003.cpp")
        self.assertIsNone(audit.sub("other_thing.c"))

    def test_gate_is_the_control_max_plus_the_margin(self):
        where = {"p00001.c": [("a/a", "x.c")], "p00002.c": [("b/b", "y.c")], "p00003.c": [("a/a", "z.c")],
                 "p00009.c": [("b/b", "w.c")]}
        pairs = [("o00001.c", "p00001.c", 50, 0.9, 0.2),
                 ("p00002.c", "o00002.c", 57, 0.5, 0.1),
                 ("c00001.c", "p00001.c", 33, 0.8, 0.1),
                 ("p00003.c", "c00002.c", 20, 0.9, 0.3),
                 ("o00001.c", "c00001.c", 12, 0.2, 0.1),
                 ("o00001.c", "o00002.c", 99, 1.0, 1.0)]
        s = audit.score(pairs, CFG, where)
        self.assertEqual(s["control_max"], 33)
        self.assertEqual(s["threshold"], 57)
        self.assertEqual(s["flagged"], [], "57 is not above 57")
        self.assertEqual([x[:3] for x in s["ours"]], [("o00002.c", "p00002.c", 57), ("o00001.c", "p00001.c", 50)])
        self.assertEqual(s["ours_control"][0][:3], ("o00001.c", "c00001.c", 12))
        s = audit.score(pairs + [("o00003.c", "p00009.c", 58, 0.3, 0.1)], CFG, where)
        self.assertEqual([x[:3] for x in s["flagged"]], [("o00003.c", "p00009.c", 58)])

    def test_a_control_related_target_is_judged_on_its_own(self):
        where = {"p00001.c": [("pico/like", "a.c")], "p00002.c": [("other/fw", "b.c")],
                 "p00003.c": [("pico/like", "c.c"), ("other/fw", "c.c")]}
        pairs = [("c00001.c", "p00001.c", 150, 0.9, 0.5),
                 ("c00002.c", "p00002.c", 30, 0.2, 0.1),
                 ("o00001.c", "p00001.c", 160, 0.5, 0.2),
                 ("o00002.c", "p00002.c", 50, 0.5, 0.2),
                 ("o00003.c", "p00003.c", 60, 0.5, 0.2)]
        s = audit.score(pairs, CFG, where)
        self.assertEqual(s["related"], ["pico/like"])
        self.assertEqual(s["control_max"], 30, "the related target doesn't raise the baseline")
        self.assertEqual([x[0] for x in s["flagged"]], ["o00003.c"],
                         "160 is within the related target's 150 + 24; a file both hold gets the stricter 54")
        s = audit.score(pairs + [("o00004.c", "p00001.c", 175, 0.5, 0.2)], CFG, where)
        self.assertIn("o00004.c", [x[0] for x in s["flagged"]])

    def test_reads_names_and_numbers_from_the_archive(self):
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "r.jplag")
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("topComparisons.json", json.dumps([
                    {"firstSubmission": "new_o00001.c", "secondSubmission": "pool_p00001.c",
                     "similarities": {"AVG": 0.5, "MAX": 0.75, "LONGEST_MATCH": 30.0, "MAXIMUM_LENGTH": 90.0}}]))
                z.writestr("runInformation.json", json.dumps({"failedSubmissions": [
                    {"submissionId": "pool/p00002.c", "submissionState": "CANNOT_PARSE"}]}))
                z.writestr("submissionFileIndex.json", json.dumps({"fileIndexes": {
                    "new_o00001.c": {"new_o00001.c/new_o00001.c": {"tokenCount": 54}}}}))
                z.writestr("files/pool_p00001.c/pool_p00001.c", "never read")
            pairs, failed, tokens = audit.read_results(path)
        finally:
            shutil.rmtree(d)
        self.assertEqual(pairs, [("o00001.c", "p00001.c", 30, 0.75, 0.5)])
        self.assertEqual(failed, {"p00002.c": "CANNOT_PARSE"})
        self.assertEqual(tokens, {"o00001.c": 54})


class LeakTest(unittest.TestCase):
    """Requirements: R-AUDIT-1, R-AUDIT-3"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "p00001.c"), "w") as f:
            f.write("short\n    static int a_long_enough_line_of_code(void);\n")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_a_target_line_in_the_report_is_caught(self):
        self.assertEqual(audit.leak(["x static int a_long_enough_line_of_code(void); y"], self.dir, 24), "p00001.c")
        self.assertIsNone(audit.leak(["src/main.c 53 1.000 short"], self.dir, 24))

    def test_a_leaking_report_is_withheld(self):
        out = os.path.join(self.dir, "out")
        report = {"schema": 1, "set": "full", "commit": "c", "run": None,
                  "top_pairs": [{"ours": "static int a_long_enough_line_of_code(void);", "longest_tokens": 1,
                                 "max": 0.1, "avg": 0.1, "target_files": [], "target_places": 0}]}
        audit.write_report(report, {"C-AUDIT-SCORE": ("PASS", "ok")}, out, self.dir, CFG)
        r = audit.load_json(os.path.join(out, "report.json"))
        self.assertNotIn("top_pairs", r)
        self.assertEqual([c["result"] for c in r["checks"] if c["id"] == "C-AUDIT-LEAK"], ["FAIL"])
        with open(os.path.join(out, "report.md")) as f:
            self.assertNotIn("a_long_enough", f.read())
        self.assertEqual(audit.check_artifact(out), [])

    def test_artifact_must_hold_only_the_report(self):
        out = os.path.join(self.dir, "out")
        audit.write_report({"schema": 1}, {"C-AUDIT-SCORE": ("PASS", "ok")}, out, None, CFG)
        self.assertEqual(audit.check_artifact(out), [])
        with open(os.path.join(out, "extra.c"), "w") as f:
            f.write("x")
        self.assertTrue(audit.check_artifact(out))


class SettingsTest(unittest.TestCase):
    """Requirements: R-AUDIT-3, R-AUDIT-4"""

    def test_pins(self):
        cfg = audit.load_json(os.path.join(ROOT, "audit", "audit.json"))
        self.assertRegex(cfg["jplag"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(cfg["java_image"], r"@sha256:[0-9a-f]{64}$")
        self.assertRegex(cfg["control"]["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(cfg["control"]["tree"], r"^[0-9a-f]{40}$")
        self.assertEqual(cfg["base_code"], "vendor/jieli-sdk/include_lib")
        self.assertFalse(cfg["ours"].startswith("vendor"))

    def test_the_workflow_keeps_targets_away_from_secrets(self):
        with open(os.path.join(ROOT, ".github", "workflows", "audit.yml")) as f:
            text = f.read()
        self.assertNotIn("pull_request", text)
        jobs = text[text.index("\njobs:"):].split("\n  record:")
        self.assertEqual(len(jobs), 2, "two jobs: audit, then record")
        audit_job, record_job = jobs
        self.assertNotIn("secrets.", audit_job)
        self.assertNotIn("environment:", audit_job)
        self.assertNotIn("cache", audit_job)
        self.assertIn("tools/audit.py run", audit_job)
        self.assertNotIn("tools/audit.py run", record_job)
        self.assertIn("check-artifact", record_job)
        self.assertIn("path: out/audit/", audit_job)


class AcceptedTest(unittest.TestCase):
    """Requirements: R-AUDIT-5, R-AUDIT-6"""

    def row(self, longest, places):
        return {"ours": "src/x.c", "longest_tokens": longest, "max": 0.5, "avg": 0.1,
                "target_files": [{"repo": "a/a", "path": p, "licence_class": "gpl"} for p in places],
                "target_places": len(places)}

    def test_only_a_covered_score_is_accepted(self):
        rules = [{"ours": "src/x.c", "repo": "a/a", "path": "f.c", "longest_tokens": 70, "finding": "audit/findings/1.md"}]
        flagged, accepted = audit.split_accepted([self.row(70, ["f.c"])], rules)
        self.assertEqual((len(flagged), len(accepted)), (0, 1))
        flagged, accepted = audit.split_accepted([self.row(71, ["f.c"])], rules)
        self.assertEqual((len(flagged), len(accepted)), (1, 0), "a higher score fails again")
        flagged, accepted = audit.split_accepted([self.row(60, ["f.c", "g.c"])], rules)
        self.assertEqual((len(flagged), len(accepted)), (1, 0), "every place must be covered")

    def test_committed_list_is_well_formed(self):
        for r in audit.load_json(os.path.join(ROOT, "audit", "accepted.json"))["accepted"]:
            self.assertEqual(set(r), {"ours", "repo", "path", "longest_tokens", "finding"})
            self.assertTrue(os.path.exists(os.path.join(ROOT, r["finding"])), r["finding"])


class CarryOverTest(unittest.TestCase):
    """A target the searches miss this time stays, unless its repository is
    gone; an unmoved head reuses its tree. Requirements: R-AUDIT-2"""

    class FakeGitHub:
        def __init__(self):
            self.requests = 0

        def get(self, path, params=None):
            self.requests += 1
            if path == "/repos/s/seed":
                return {"full_name": "s/seed", "html_url": "https://x/s/seed", "forks_count": 0, "license": None}
            if "/git/commits/" in path:
                return {"tree": {"sha": "t" * 40}}
            return None

        def pages(self, path, params=None, limit=10):
            return []

        def search(self, q):
            return []

    def test_carry_over(self):
        heads = {"https://x/s/seed.git": "a" * 40, "https://x/kept/repo.git": "b" * 40, "https://x/gone/repo.git": None}
        saved = disc.head
        disc.head = lambda url: heads[url]
        try:
            gh = self.FakeGitHub()
            prev = [{"repo": "kept/repo", "url": "https://x/kept/repo", "found_by": "search: x", "licence_class": "gpl",
                     "commit": "b" * 40, "tree": "c" * 40},
                    {"repo": "gone/repo", "url": "https://x/gone/repo", "found_by": "fork", "licence_class": "none"}]
            got = disc.discover({"seeds": [{"repo": "s/seed"}], "queries": [], "mentions": "x"}, gh,
                                pinned={"kept/repo": ("b" * 40, "c" * 40)}, previous=prev)
        finally:
            disc.head = saved
        by = {t["repo"]: t for t in got}
        self.assertEqual(sorted(by), ["kept/repo", "s/seed"])
        self.assertEqual(by["kept/repo"]["tree"], "c" * 40, "an unmoved head keeps its tree")
        self.assertEqual(gh.requests, 2, "one seed lookup and one tree, none for the kept target")
