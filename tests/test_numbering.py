# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
import unittest

from tests.helpers import ROOT

# CONTRIBUTING.md, "Numbering": from P-74 on, each side has its own range.
FIRST_SPLIT, SPEC_FROM = 74, 500


def rows(text):
    """(number, session) for each PROVENANCE row."""
    return [(int(m.group(1)), m.group(2))
            for m in re.finditer(r"^\| P-(\d+) \| [^|]* \| ([^|]*) \|", text, re.M)]


def problems(text):
    out, seen = [], set()
    for n, session in rows(text):
        if n in seen:
            out.append("P-%d is used twice" % n)
        seen.add(n)
        if n < FIRST_SPLIT:
            continue
        spec = "(spec side)" in session
        if spec and n < SPEC_FROM:
            out.append("P-%d is the spec side's (%s) but below P-%d" % (n, session.strip(), SPEC_FROM))
        if not spec and n >= SPEC_FROM:
            out.append("P-%d is the firmware side's (%s) but P-%d and up are the spec side's"
                       % (n, session.strip(), SPEC_FROM))
    return out


class NumberingTest(unittest.TestCase):
    """Requirements: R-PROC-1"""

    def test_provenance_rows_keep_to_their_sides_ranges(self):
        with open(os.path.join(ROOT, "PROVENANCE.md"), encoding="utf-8") as f:
            self.assertEqual(problems(f.read()), [])

    def test_the_rule(self):
        head = "| ID | Date | Session | Source | What | Used in |\n"
        ok = head + "| P-73 | d | spec-sr15 (spec side) | s | w | u |\n| P-74 | d | clean-x | s | w | u |\n" \
            "| P-500 | d | spec-y (spec side) | s | w | u |\n"
        self.assertEqual(problems(ok), [])
        self.assertEqual(len(problems(head + "| P-75 | d | spec-y (spec side) | s | w | u |\n")), 1)
        self.assertEqual(len(problems(head + "| P-501 | d | clean-x | s | w | u |\n")), 1)
        self.assertEqual(problems(head + "| P-80 | d | c | s | w | u |\n| P-80 | d | c | s | w | u |\n"),
                         ["P-80 is used twice"])


if __name__ == "__main__":
    unittest.main()
