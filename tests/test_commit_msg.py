# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import unittest

from tests.helpers import load_tool

cm = load_tool("check-commit-msg.py")

GOOD = """tools: add the commit-message check

What:    adds tools/check-commit-msg.py
Why:     M0a, R-PROC-1
How:     a small parser of .gitmessage's fields;
         continuation lines are indented
Result:  unit tests pass
Sources: none
Exposure: firmware side, none
"""

AGENT_TRAILERS = """
Model: claude-opus-5-5
Claude-Session: https://claude.ai/code/session_x
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
"""


class CommitMessageTest(unittest.TestCase):
    """Requirements: R-PROC-1"""

    def test_good_message_passes(self):
        self.assertEqual(cm.validate(GOOD, "Someone <s@example.org>"), [])

    def test_agent_message_needs_trailers(self):
        problems = cm.validate(GOOD, "Claude (claude-opus-5-5) <noreply@anthropic.com>")
        self.assertTrue(any("Model" in p for p in problems))
        self.assertTrue(any("Claude-Session" in p for p in problems))
        self.assertEqual(cm.validate(GOOD + AGENT_TRAILERS, "Claude <noreply@anthropic.com>"), [])

    def test_each_field_is_required(self):
        for field in cm.FIELDS:
            lines = [l for l in GOOD.splitlines() if not l.startswith(field + ":")]
            problems = cm.validate("\n".join(lines))
            self.assertTrue(any(field in p for p in problems), field)

    def test_empty_field_fails(self):
        msg = GOOD.replace("Result:  unit tests pass", "Result:")
        self.assertTrue(any("Result: empty" in p for p in cm.validate(msg)))

    def test_bad_subject_fails(self):
        for subject in ("Add a thing", "Tools: add", "tools:add", "tools: "):
            msg = GOOD.replace("tools: add the commit-message check", subject)
            self.assertTrue(cm.validate(msg), subject)

    def test_line_two_must_be_blank(self):
        msg = GOOD.replace("check\n\nWhat", "check\nWhat")
        self.assertTrue(any("line 2" in p for p in cm.validate(msg)))

    def test_order_matters(self):
        msg = GOOD.replace("Why:     M0a, R-PROC-1\n", "").replace(
            "Sources: none\n", "Sources: none\nWhy:     M0a\n")
        self.assertTrue(any("order" in p for p in cm.validate(msg)))

    def test_template_comments_are_stripped(self):
        with open(cm.__file__.replace("tools/check-commit-msg.py", ".gitmessage")) as f:
            template = f.read()
        # The bare template must fail: its fields are empty.
        self.assertTrue(cm.validate(cm.strip_comments(template)))


if __name__ == "__main__":
    unittest.main()
