# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

cp = load_tool("check-private.py")


class PrivateTermsTest(unittest.TestCase):
    """Requirements: R-PUB-3"""

    def test_hit_lines_ignore_case_and_count_lines(self):
        data = b"one\nTwo SECRET\nthree\nsecret and secret\n"
        self.assertEqual(cp.hit_lines(data, [b"secret"]), [2, 4])
        self.assertEqual(cp.hit_lines(data, [b"absent"]), [])

    def test_reports_file_and_line_only(self):
        files = {"a.md": b"fine\nhas Secret\n", "b.md": b"fine\n"}
        problems = cp.check_files(sorted(files), files.get, [b"secret"])
        self.assertEqual(problems, ["a.md:2"])
        self.assertFalse(any("ecret" in p for p in problems))

    def test_files_not_on_disk_are_skipped(self):
        self.assertEqual(cp.check_files(["gone"], lambda p: None, [b"x"]), [])

    def test_spec_side_hits_are_counted_not_named(self):
        self.assertTrue("harness/x.rs:3".startswith(cp.SPEC_DIRS))
        self.assertTrue("sessions/spec/a.jsonl:1".startswith(cp.SPEC_DIRS))
        self.assertFalse("docs/PLAN.md:1".startswith(cp.SPEC_DIRS))

    def test_exempt_labels_name_no_spec_file(self):
        self.assertEqual(cp.label("sessions/clean/x.jsonl"), "sessions/clean")
        self.assertEqual(cp.label("sessions/spec/x.jsonl"), "spec-side transcripts")
        self.assertEqual(cp.label("docs/prompts/M0a.md"), "docs/prompts")

    def test_exemption_needs_the_base_blob(self):
        base = cp.load_base()
        self.assertRegex(base, r"^[0-9a-f]{40}$")
        exempt = cp.exempt_paths(base)
        # A file added after the base is never exempt.
        self.assertNotIn("docs/prompts/M0d-addendum.md", exempt)
        for p in exempt:
            self.assertTrue(p.startswith(cp.EXEMPT_DIRS), p)

    def test_terms_from_environment(self):
        saved = os.environ.get("PRIVATE_TERMS")
        os.environ["PRIVATE_TERMS"] = "# comment\n  Alpha \n\nbeta\nalpha\n"
        try:
            self.assertEqual(cp.load_terms(), [b"alpha", b"beta"])
        finally:
            if saved is None:
                del os.environ["PRIVATE_TERMS"]
            else:
                os.environ["PRIVATE_TERMS"] = saved

    def test_withhold_deletes_hit_files_and_lists_their_hashes(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "logs"))
            with open(os.path.join(d, "logs", "a.log"), "w") as f:
                f.write("ok\nseen ZEBRAWORD here\n")
            with open(os.path.join(d, "b.txt"), "w") as f:
                f.write("nothing\n")
            env = dict(os.environ, PRIVATE_TERMS="zebraword")
            p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check-private.py"),
                                "--dir", d, "--withhold"], env=env,
                               stdout=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(p.returncode, 1)
            self.assertNotIn("zebraword", p.stdout.lower())
            self.assertFalse(os.path.exists(os.path.join(d, "logs", "a.log")))
            self.assertTrue(os.path.exists(os.path.join(d, "b.txt")))
            with open(os.path.join(d, "WITHHELD.json")) as f:
                listed = json.load(f)["withheld"]
            self.assertEqual([w["file"] for w in listed], ["logs/a.log"])
            self.assertEqual(len(listed[0]["sha256"]), 64)
            p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check-private.py"),
                                "--dir", d, "--withhold"], env=env, stdout=subprocess.DEVNULL)
            self.assertEqual(p.returncode, 0)  # nothing left to withhold
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
