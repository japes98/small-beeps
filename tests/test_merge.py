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


class MergeCiWaitTest(unittest.TestCase):
    """Requirements: R-PROC-2"""

    def test_verdicts(self):
        done_ok = {"status": "completed", "conclusion": "success"}
        done_bad = {"status": "completed", "conclusion": "failure"}
        running = {"status": "in_progress", "conclusion": None}
        self.assertEqual(cm.ci_verdict([done_bad, done_ok]), "success")
        self.assertEqual(cm.ci_verdict([done_bad, running]), "pending")
        self.assertEqual(cm.ci_verdict([done_bad]), "failed")
        self.assertEqual(cm.ci_verdict([]), "failed")

    def test_waits_until_the_run_finishes(self):
        answers = [[{"status": "in_progress", "conclusion": None}]] * 3 + \
                  [[{"status": "completed", "conclusion": "success"}]]
        calls, t = [], [0.0]

        def fetch():
            calls.append(1)
            return answers[len(calls) - 1]

        def sleep(s):
            t[0] += s
        verdict, _ = cm.wait_for_ci(fetch, 600, sleep=sleep, clock=lambda: t[0])
        self.assertEqual(verdict, "success")
        self.assertEqual(len(calls), 4)

    def test_gives_up_after_the_limit(self):
        t = [0.0]

        def sleep(s):
            t[0] += s
        verdict, _ = cm.wait_for_ci(lambda: [{"status": "queued", "conclusion": None}], 90,
                                    sleep=sleep, clock=lambda: t[0])
        self.assertEqual(verdict, "pending")
        self.assertGreaterEqual(t[0], 90)


if __name__ == "__main__":
    unittest.main()
