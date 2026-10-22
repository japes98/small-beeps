# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

rm = load_tool("recheck-merge.py")
SHA = "a208634d3f965d3845e71d8705608439a6b7fe1b"


class RecheckTest(unittest.TestCase):
    """Requirements: R-PROC-2, R-REC-1"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_tool(self, exit_code, out=None, sha=SHA, reason="GitHub's endpoint answered 500"):
        fake = os.path.join(self.dir, "fake_check.py")
        with open(fake, "w") as f:
            f.write("import sys\nprint('merge check: %s', sys.argv[1])\nsys.exit(%d)\n"
                    % ("PASS" if exit_code == 0 else "FAIL", exit_code))
        out = out or os.path.join(self.dir, "verified")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "recheck-merge.py"), sha,
                            "--out", out, "--reason", reason, "--checker-commit", "c" * 40,
                            "--check-cmd", "%s %s" % (sys.executable, fake)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        return p, out

    def test_a_pass_is_written_with_its_checker(self):
        p, out = self.run_tool(0)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(sorted(os.listdir(out)),
                         ["C-MERGE.log", "SHA256SUMS", "verification.json", "verification.md"])
        v = json.load(open(os.path.join(out, "verification.json")))
        self.assertEqual((v["commit"], v["result"], v["check"]), (SHA, "PASS", "C-MERGE"))
        self.assertEqual(v["checker_commit"], "c" * 40)
        self.assertRegex(v["checker_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("500", v["reason"])
        self.assertIn("Only C-MERGE", v["scope"])
        self.assertIn("merge check: PASS " + SHA, open(os.path.join(out, "C-MERGE.log")).read())
        sums = open(os.path.join(out, "SHA256SUMS")).read()
        for n in ("C-MERGE.log", "verification.json", "verification.md"):
            self.assertIn("  " + n, sums)

    def test_a_fail_is_written_and_returned(self):
        p, out = self.run_tool(1)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.load(open(os.path.join(out, "verification.json")))["result"], "FAIL")

    def test_never_overwrites(self):
        out = os.path.join(self.dir, "verified")
        os.makedirs(out)
        p, _ = self.run_tool(0, out=out)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(os.listdir(out), [])

    def test_refuses_a_short_sha_or_no_reason(self):
        self.assertEqual(self.run_tool(0, sha="a208634")[0].returncode, 2)
        self.assertEqual(self.run_tool(0, reason=" ")[0].returncode, 2)

    def test_the_workflow_only_adds(self):
        with open(os.path.join(ROOT, ".github", "workflows", "recheck-merge.yml")) as f:
            wf = f.read()
        self.assertRegex(wf, r"(?m)^on:\n  workflow_dispatch:")
        self.assertNotRegex(wf, r"(?m)^  (push|pull_request|schedule):")
        self.assertIn("github.ref == 'refs/heads/main'", wf)
        self.assertIn("verified-$(date -u +%Y-%m-%d)", wf)
        self.assertIn('grep -v -E "^A[[:space:]]+$dest/"', wf)
        self.assertNotIn("--force", wf)
        # inputs reach the shell only through env, never interpolated
        for line in wf.splitlines():
            if "${{ inputs." in line:
                self.assertTrue(re.match(r"^\s+(SHA|REASON): \$\{\{ inputs\.\w+ \}\}$", line)
                                or "group: recheck-" in line, line)


if __name__ == "__main__":
    unittest.main()
