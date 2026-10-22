# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import shutil
import subprocess
import tempfile
import unittest

from tests.helpers import ROOT


class BannerTest(unittest.TestCase):
    """Requirements: R-CLEAN-5"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, ".claude"))
        shutil.copytree(os.path.join(ROOT, "config"), os.path.join(self.dir, "config"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def run_banner(self, role, settings_from):
        with open(os.path.join(self.dir, ".claude", "small-beeps-role"), "w") as f:
            f.write(role + "\n")
        if settings_from:
            shutil.copyfile(os.path.join(self.dir, "config", "claude", settings_from),
                            os.path.join(self.dir, ".claude", "settings.json"))
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir)
        return subprocess.run(["sh", os.path.join(ROOT, "tools", "session-banner.sh")],
                              input=b'{"source":"clear"}', env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_matching_settings(self):
        for role in ("clean", "spec"):
            p = self.run_banner(role, role + ".json")
            out = p.stdout.decode()
            self.assertEqual(p.returncode, 0, out)
            self.assertIn("=== small-beeps session banner v1 ===", out)
            self.assertIn("status: OK", out)
            self.assertIn("source: clear", out)
            self.assertIn("role: " + role, out)

    def test_wrong_config_is_a_mismatch(self):
        p = self.run_banner("clean", "spec.json")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("CONFIG MISMATCH", p.stdout.decode())

    def test_missing_settings_is_a_mismatch(self):
        p = self.run_banner("clean", None)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("CONFIG MISMATCH", p.stdout.decode())

    def test_unknown_role_is_a_mismatch(self):
        p = self.run_banner("other", "clean.json")
        self.assertNotEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
