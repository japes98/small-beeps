# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

lp = load_tool("check-low-profile.py")


class LowProfileTest(unittest.TestCase):
    """Requirements: R-PUB-1"""

    def test_quiet_words_are_found_in_any_spelling(self):
        for text in ("FM-1", "fm1", "FM 1", "M-VAVE", "mvave", "JieLi", "Jie-Li",
                     "synth", "Synthesizer", "firmware", "Firm-Ware"):
            self.assertTrue(lp.quiet_words(text), text)

    def test_plain_words_pass(self):
        for text in ("Embedded audio experiments.", "small-beeps", "How to verify our work"):
            self.assertEqual(lp.quiet_words(text), [], text)

    def test_the_real_readme_passes(self):
        self.assertEqual(lp.check_readme(os.path.join(ROOT, "README.md")), [])

    def test_readme_first_line_and_words(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "README.md")
            with open(p, "w") as f:
                f.write("Hello.\nA synth project.\n")
            problems = lp.check_readme(p)
        self.assertTrue(any("line 1" in x for x in problems))
        self.assertTrue(any("quiet word" in x for x in problems))

    def test_metadata(self):
        good = {"name": "small-beeps", "description": lp.DESCRIPTION, "topics": []}
        self.assertEqual(lp.check_metadata(good), [])
        self.assertTrue(lp.check_metadata(dict(good, topics=["audio"])))
        self.assertTrue(lp.check_metadata(dict(good, description="FM-1 firmware")))
        self.assertTrue(lp.check_metadata(dict(good, description="Other.")))


if __name__ == "__main__":
    unittest.main()
