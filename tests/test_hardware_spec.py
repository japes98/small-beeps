# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import unittest

from tests.helpers import ROOT, load_tool

hs = load_tool("check-hardware-spec.py")

GOOD = """# Hardware spec

## 1. Boot

### HW-1: Load address
- Fact: The image starts at the window's first byte.
- Sources: HARNESS ("The raw image"); E-1.
- Standing: confirmed (E-1)
- Needed by: M0d

### HW-2: Something the model says
- Fact: A property, continued
  on a second line.
- Sources: the emulator model.
- Standing: emulator-only
- Needed by: M1

## Open questions

- **Q-1. Clocks.** Not known.
"""


class HardwareSpecLintTest(unittest.TestCase):
    """Requirements: R-SPEC-1, R-SPEC-3"""

    def problems(self, text, base=None, exps=frozenset({"1"})):
        return hs.lint(text, base, set(exps) if exps is not None else None)[1]

    def test_good(self):
        entries, problems = hs.lint(GOOD, None, {"1"})
        self.assertEqual(problems, [])
        self.assertEqual(entries["HW-2"]["Fact"], "A property, continued on a second line.")

    def test_missing_field_and_unknown_field(self):
        bad = GOOD.replace("- Needed by: M1\n", "- Notes: x\n")
        p = self.problems(bad)
        self.assertTrue(any("HW-2" in x and "no Needed by" in x for x in p), p)
        self.assertTrue(any("unknown field 'Notes'" in x for x in p), p)

    def test_empty_source(self):
        p = self.problems(GOOD.replace("- Sources: the emulator model.", "- Sources:"))
        self.assertTrue(any("HW-2" in x and "no Sources" in x for x in p), p)

    def test_duplicate_id_and_question(self):
        p = self.problems(GOOD.replace("### HW-2:", "### HW-1:") + "- **Q-1. Again.** x\n")
        self.assertTrue(any("HW-1 is used twice" in x for x in p), p)
        self.assertTrue(any("Q-1 is used twice" in x for x in p), p)

    def test_standing(self):
        p = self.problems(GOOD.replace("- Standing: emulator-only", "- Standing: probably"))
        self.assertTrue(any("standing 'probably'" in x for x in p), p)
        p = self.problems(GOOD.replace("- Standing: emulator-only", "- Standing: superseded by HW-9"))
        self.assertTrue(any("superseded by HW-9" in x for x in p), p)
        self.assertEqual(self.problems(GOOD.replace("- Standing: emulator-only",
                                                    "- Standing: superseded by HW-1")), [])

    def test_confirmed_needs_an_independent_source(self):
        for weak in ("the emulator model.", 'HARNESS ("The raw image").'):
            bad = GOOD.replace('- Sources: HARNESS ("The raw image"); E-1.', "- Sources: " + weak)
            p = self.problems(bad, exps=None)
            self.assertTrue(any("HW-1: confirmed, but" in x for x in p), (weak, p))

    def test_unknown_experiment(self):
        p = self.problems(GOOD, exps={"2"})
        self.assertTrue(any("cites E-1" in x for x in p), p)
        self.assertEqual(self.problems(GOOD, exps=None), [], "skipped where harness/ is absent")

    def test_no_code(self):
        p = self.problems(GOOD + "\n```c\nint x;\n```\n")
        self.assertTrue(any("fenced code block" in x for x in p), p)

    def test_history(self):
        changed = GOOD.replace("starts at the window's first byte", "starts elsewhere")
        p = self.problems(changed, base=GOOD)
        self.assertTrue(any("HW-1's fact changed" in x for x in p), p)
        gone = GOOD.split("### HW-2")[0]
        p = self.problems(gone, base=GOOD)
        self.assertTrue(any("HW-2 was removed" in x for x in p), p)
        superseded = GOOD.replace("- Standing: confirmed (E-1)", "- Standing: superseded by HW-2")
        self.assertEqual(self.problems(superseded, base=GOOD), [])

    def test_the_real_spec(self):
        with open(os.path.join(ROOT, "docs", "HARDWARE-SPEC.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(hs.lint(text, None, None)[1], [])


if __name__ == "__main__":
    unittest.main()
