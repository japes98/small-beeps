# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import unittest

from tests.helpers import load_tool

cm = load_tool("check-merge.py")


def ev(**kw):
    args = dict(n_parents=2, verified=True, reason="valid", committer="web-flow",
                merged_by="owner", owner="owner", pr_found=True, ci_success=True)
    args.update(kw)
    return cm.evaluate(**args)


class MergeCheckTest(unittest.TestCase):
    """Requirements: R-PROC-2"""

    def test_button_merge_by_the_owner_passes(self):
        self.assertEqual(ev(), [])

    def test_local_signed_merge_by_the_owner_passes(self):
        self.assertEqual(ev(committer="owner", merged_by="owner"), [])

    def test_button_merge_by_someone_else_fails(self):
        self.assertTrue(ev(merged_by="someone"))

    def test_other_committer_fails(self):
        self.assertTrue(ev(committer="someone"))

    def test_unverified_fails(self):
        self.assertTrue(ev(verified=False, reason="unsigned"))

    def test_not_a_merge_fails(self):
        self.assertTrue(ev(n_parents=1))

    def test_needs_a_pull_request_with_passing_ci(self):
        self.assertTrue(ev(pr_found=False))
        self.assertTrue(ev(ci_success=False))


if __name__ == "__main__":
    unittest.main()
