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
CFG = {"margin_tokens": 24, "control_ceiling_tokens": 100, "control_related_share": 0.1, "leak_line_chars": 24,
       "min_tokens": 12, "text_check": {"k": 24, "threshold": 0.5}}


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
        self.assertEqual(cfg["base_code"], [{"path": "vendor/jieli-sdk/include_lib"},
                                            {"path": "vendor/plaits", "sha256sums": True,
                                             "only_for": "firmware/demos/plaits"}])
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

    def test_rediscovery_only_writes_issues(self):
        with open(os.path.join(ROOT, ".github", "workflows", "audit-discover.yml")) as f:
            text = f.read()
        self.assertIn("      contents: read\n      issues: write\n", text)
        for word in ("contents: write", "pull-requests", "gh pr ", "git push", "secrets."):
            self.assertNotIn(word, text)
        self.assertIn("tools/audit-discover.py --write", text)
        self.assertIn("gh issue create", text)


class SelftestVerdictTest(unittest.TestCase):
    """A file JPlag leaves out of its index (no match) fails the self-test
    rather than being skipped; a file JPlag cannot score must be found by the
    text check, both as an exact and as a reformatted copy.
    Requirements: R-AUDIT-5"""

    def report(self, states, text=()):
        files = [{"file": f, "tokens": 20 if st == "scored" else None, "state": st} for f, st in states]
        for f in files:
            if f["state"] == "TOO_SMALL":
                f["not_scorable"] = audit.not_scorable("TOO_SMALL", CFG)
        best = [[f, "copy/" + f, 20, 1.0, 1.0] for f, st in states if st == "scored"]
        return {"ours_files": files, "selftest": {"ours_best": best, "text": [list(t) for t in text]},
                "checks": [{"id": "C-AUDIT-LEAK", "result": "PASS"}]}

    def test_all_found(self):
        ok, detail = audit.selftest_verdict(self.report([("src/a.c", "scored"), ("src/b.h", "scored")]), CFG)
        self.assertTrue(ok, detail)
        self.assertIn("2 of our 2 files", detail)

    def test_a_file_without_a_match_fails(self):
        ok, detail = audit.selftest_verdict(self.report([("src/a.c", "scored"), ("src/b.h", "no match")]), CFG)
        self.assertFalse(ok)
        self.assertIn("1 of our 2 files", detail)

    def test_a_file_too_small_for_jplag_is_found_by_the_text_check(self):
        text = [("src/font.c", "copied/src/font.c", 1.0, True), ("src/font.c", "reformatted/src/font.c", 1.0, False)]
        ok, detail = audit.selftest_verdict(self.report([("src/a.c", "scored"), ("src/font.c", "TOO_SMALL")], text), CFG)
        self.assertTrue(ok, detail)
        self.assertIn("2 of our 2 files found in a target holding copies of them (1 by JPlag, 1 by the text check)", detail)

    def test_a_file_too_small_for_jplag_the_text_check_misses_fails(self):
        for text in ((), [("src/font.c", "copied/src/font.c", 1.0, True)],
                     [("src/font.c", "copied/src/font.c", 1.0, True), ("src/font.c", "reformatted/src/font.c", 0.4, False)]):
            ok, detail = audit.selftest_verdict(self.report([("src/a.c", "scored"), ("src/font.c", "TOO_SMALL")], text),
                                                CFG)
            self.assertFalse(ok, text)
            self.assertIn("1 of our 2 files", detail)


    def test_a_copy_split_by_base_code_is_found_by_its_similarity(self):
        # JPlag leaves base code out, so a verbatim copy's match can come in
        # pieces: the longest under 90% of the tokens, the similarity 1.0
        r = self.report([("src/a.c", "scored"), ("demos/p/b.c", "scored")])
        r["ours_files"][1]["tokens"] = 471
        r["selftest"]["ours_best"][1] = ["demos/p/b.c", "p00011.c", 198, 1.0, 1.0, "copied/demos/p/b.c"]
        ok, detail = audit.selftest_verdict(r, CFG)
        self.assertTrue(ok, detail)
        self.assertIn("2 of our 2 files", detail)
        # the similarity counts only with a copy of the file itself
        r["selftest"]["ours_best"][1] = ["demos/p/b.c", "p00012.c", 198, 1.0, 1.0, "copied/demos/p/c.c"]
        ok, detail = audit.selftest_verdict(r, CFG)
        self.assertFalse(ok, detail)
        r["selftest"]["ours_best"][1] = ["demos/p/b.c", "p00011.c", 198, 0.8, 0.8, "reformatted/demos/p/b.c"]
        self.assertFalse(audit.selftest_verdict(r, CFG)[0])

    def test_a_file_without_a_match_is_found_by_the_text_check(self):
        text = [("src/b.h", "copied/src/b.h", 1.0, True), ("src/b.h", "reformatted/src/b.h", 0.9, False)]
        ok, detail = audit.selftest_verdict(self.report([("src/a.c", "scored"), ("src/b.h", "no match")], text), CFG)
        self.assertTrue(ok, detail)
        self.assertIn("(1 by JPlag, 1 by the text check)", detail)

    def test_the_text_check_takes_what_jplag_does_not_cover(self):
        mine = {"o1", "o2", "o3"}
        self.assertEqual(audit.text_check_files(mine, {"o2": "TOO_SMALL"}, {"o1": 40}), {"o2", "o3"})
        self.assertEqual(audit.text_check_files(mine, {}, {"o1": 40, "o2": 9, "o3": 30}), set())


class TextCheckTest(unittest.TestCase):
    """Our files JPlag cannot score are compared as text: exact copies, and
    the share of their normalised text in each target file.
    Requirements: R-AUDIT-1, R-AUDIT-5"""

    OURS = (b"/* our glyphs, a made-up font */\n#include \"sb.h\"\n"
            b"#define G(a, b) { ROW(a), ROW(b) }\n"
            b"const u8 glyphs[4][2] = {\n"
            b"    /* 'a' */ G(\".#.#.\", \"#...#\"),\n"
            b"    /* 'b' */ G(\"##...\", \"..#..\"),\n"
            b"    /* 'c' */ G(\"...##\", \".###.\"),\n"
            b"    /* 'd' */ G(\"#####\", \".....\"),\n};\n")

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def put(self, name, data):
        with open(os.path.join(self.dir, name), "wb") as f:
            f.write(data)

    def scores(self):
        return {p: (round(c, 3), exact) for o, p, c, exact in audit.text_scores({"o00001.c": self.OURS}, self.dir, 24)}

    def test_normalise_drops_comments_and_whitespace_but_not_literals(self):
        self.assertEqual(audit.normalise('int a = 1; /* c */ // x\nchar *s = "a /* b */ c";\n'),
                         'inta=1;char*s="a/*b*/c";')

    def test_copies_are_found_and_unrelated_code_is_not(self):
        text = self.OURS.decode()
        self.put("p00001.c", self.OURS)
        self.put("p00002.c", audit.reformat(text).encode())
        self.put("p00003.c", b"static int before(int x) { return x + 1; }\n" + self.OURS +
                 b"int after(void) { return before(2); }\n")
        self.put("p00004.c", b"int unrelated(int a) { return a * 3 + 1; }\n")
        half = "\n".join(l for l in text.splitlines() if "'c'" not in l and "'d'" not in l)
        self.put("p00005.c", half.encode())
        got = self.scores()
        self.assertEqual(got["p00001.c"], (1.0, True), "a verbatim copy is exact")
        self.assertEqual(got["p00002.c"], (1.0, False), "a reformatted copy is found, but not as exact")
        self.assertEqual(got["p00003.c"], (1.0, False), "a copy inside a larger file is found")
        self.assertNotIn("p00004.c", got, "unrelated code shares nothing")
        self.assertTrue(0 < got["p00005.c"][0] < 1, got["p00005.c"])

    def test_the_reformatted_copy_differs_in_bytes_only(self):
        text = self.OURS.decode()
        self.assertNotEqual(audit.reformat(text), text)
        self.assertEqual(audit.normalise(audit.reformat(text)), audit.normalise(text))

    def test_the_report_says_why_a_file_is_not_scorable(self):
        self.assertEqual(audit.not_scorable("TOO_SMALL", CFG),
                         "not scorable by JPlag: fewer tokens than JPlag's minimum match of 12 (TOO_SMALL); "
                         "compared by the text check instead")
        self.assertIn("could not parse", audit.not_scorable("CANNOT_PARSE", CFG))

    def test_committed_settings(self):
        cfg = audit.load_json(os.path.join(ROOT, "audit", "audit.json"))
        self.assertEqual(cfg["text_check"], {"k": 24, "threshold": 0.5})


class BaseCodeTest(unittest.TestCase):
    """The base code is a list of trees (since SR-4): the JieLi SDK for all
    our files, and the vendored Plaits, only as its SHA256SUMS pins it, for
    our files under firmware/demos/plaits/ only, in a JPlag pass of their
    own; the text check uses the same base code. A file outside that folder
    that includes Plaits fails the audit, so the owner decides.
    Requirements: R-AUDIT-4, R-AUDIT-5"""

    SHARED = b"float shared_dsp_step(float x, float y) { return x * 0.5f + y * 0.25f - x * y; }\n"
    OWN = b"int our_own_glue(int voice) { return voice * 17 + 3; }\nint more_of_ours(void) { return 42; }\n"

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.saved = audit.ROOT
        audit.ROOT = self.dir
        self.put("sdk/a/x.h", b"#define SDK_THING 1\n")
        self.put("sdk/notes.txt", b"not code\n")
        self.put("pl/up/plaits/dsp/x.h", self.SHARED)
        self.put("pl/SOURCE.md", b"ours\n")
        self.sums()
        self.cfg = {"suffixes": [".c", ".h", ".cc"], "ours": "fw",
                    "base_code": [{"path": "sdk"}, {"path": "pl", "sha256sums": True, "only_for": "fw/demo"}]}

    def tearDown(self):
        audit.ROOT = self.saved
        shutil.rmtree(self.dir)

    def put(self, rel, data):
        os.makedirs(os.path.dirname(os.path.join(self.dir, rel)), exist_ok=True)
        with open(os.path.join(self.dir, rel), "wb") as f:
            f.write(data)

    def sums(self):
        import hashlib
        with open(os.path.join(self.dir, "pl/up/plaits/dsp/x.h"), "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        self.put("pl/SHA256SUMS", ("%s up/plaits/dsp/x.h\n" % h).encode())

    def groups(self, files):
        ours = {"o%05d.c" % i: p for i, p in enumerate(sorted(files), 1)}
        return audit.groups(self.cfg, ours, lambda n: files[ours[n]], audit.base_trees(self.cfg))

    def test_each_tree_with_our_suffixes(self):
        got = [(b["path"], sorted(f)) for b, f in audit.base_trees(self.cfg)]
        self.assertEqual(got, [("sdk", ["a/x.h"]), ("pl", ["up/plaits/dsp/x.h"])])

    def test_a_tree_that_does_not_match_its_checksums_fails(self):
        self.put("pl/up/plaits/dsp/x.h", self.SHARED + b"// changed\n")
        with self.assertRaisesRegex(ValueError, "pl: up/plaits/dsp/x.h does not match its SHA-256"):
            audit.base_trees(self.cfg)
        self.sums()
        self.put("pl/up/extra.cc", b"int extra;\n")
        with self.assertRaisesRegex(ValueError, "up/extra.cc is not in SHA256SUMS"):
            audit.base_trees(self.cfg)

    def test_a_missing_tree_fails(self):
        shutil.rmtree(os.path.join(self.dir, "pl"))
        with self.assertRaisesRegex(ValueError, "base code pl is not on disk"):
            audit.base_trees(self.cfg)

    def test_plaits_is_base_code_only_for_the_demo(self):
        got = self.groups({"src/main.c": b"int main(void) { return 0; }\n",
                           "demo/glue.cc": b'#include "plaits/dsp/x.h"\n'})
        self.assertEqual([(label, sorted(mine.values()), [b["path"] for b, _ in tr]) for label, mine, tr in got],
                         [("our files outside fw/demo/", ["src/main.c"], ["sdk"]),
                          ("our files under fw/demo/", ["demo/glue.cc"], ["sdk", "pl"])])

    def test_no_demo_files_one_pass(self):
        got = self.groups({"src/main.c": b"int main(void) { return 0; }\n"})
        self.assertEqual(len(got), 1)

    def test_a_core_file_that_includes_plaits_fails(self):
        for inc in (b'#include "plaits/dsp/x.h"\n', b'  #  include <dsp/x.h>\n',
                    b'#include "../../pl/up/plaits/dsp/x.h"\n'):
            with self.assertRaisesRegex(ValueError, r"fw/src/synth.c includes .* from pl, which is base code only "
                                                    r"under fw/demo/; .* the owner decides"):
                self.groups({"src/synth.c": inc})
        # a flat include, or one naming no Plaits file, is not taken for Plaits
        self.assertEqual(len(self.groups({"src/a.c": b'#include "x.h"\n#include "dsp/y.h"\n'})), 1)

    def test_the_text_check_leaves_out_base_pieces(self):
        pool = os.path.join(self.dir, "pool")
        os.makedirs(pool)
        with open(os.path.join(pool, "p00001.cc"), "wb") as f:
            f.write(self.SHARED)  # a target that took the same base code
        with open(os.path.join(pool, "p00002.c"), "wb") as f:
            f.write(self.OWN)  # a target that copied our own code
        ours = {"o00001.c": self.SHARED + self.OWN, "o00002.c": self.SHARED}
        base = [d for _, f in audit.base_trees(self.cfg) for d in f.values()]
        without = {(o, p): c for o, p, c, _ in audit.text_scores(ours, pool, 24)}
        self.assertGreater(without[("o00001.c", "p00001.cc")], 0, "without base code, the shared code counts")
        got = {(o, p): (round(c, 3), e) for o, p, c, e in audit.text_scores(ours, pool, 24, base)}
        self.assertNotIn(("o00001.c", "p00001.cc"), got, "with it, the base code alone matches nothing")
        c, exact = got[("o00001.c", "p00002.c")]
        self.assertGreater(c, without[("o00001.c", "p00002.c")], "our own code weighs more without the base")
        self.assertGreaterEqual(c, 0.5, "and is still found, above the threshold")
        self.assertFalse([k for k in got if k[0] == "o00002.c"], "a copy of a base file is not flagged")


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
