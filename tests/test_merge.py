# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import io
import unittest
import urllib.error

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
        self.assertEqual(cm.ci_verdict([]), "missing")

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

    def wait(self, answers, limit):
        """Runs wait_for_ci over answers (the last repeats) on a fake clock;
        returns (verdict, fetches, sleeps)."""
        calls, sleeps, t = [], [], [0.0]

        def fetch():
            calls.append(1)
            return answers[min(len(calls), len(answers)) - 1]

        def sleep(s):
            sleeps.append(s)
            t[0] += s
        verdict, _ = cm.wait_for_ci(fetch, limit, sleep=sleep, clock=lambda: t[0])
        return verdict, len(calls), sleeps

    def test_an_empty_answer_is_asked_again(self):
        # PR #13's record: the search found no run although CI had passed
        ok = [{"status": "completed", "conclusion": "success"}]
        verdict, fetches, sleeps = self.wait([[], [], ok], 1800)
        self.assertEqual(verdict, "success")
        self.assertEqual(fetches, 3)
        self.assertEqual(sleeps, [10, 20])

    def test_a_late_run_is_waited_for(self):
        # none found, then queued, then running, then done
        answers = [[], [{"status": "queued", "conclusion": None}],
                   [{"status": "in_progress", "conclusion": None}],
                   [{"status": "completed", "conclusion": "success"}]]
        verdict, fetches, _ = self.wait(answers, 1800)
        self.assertEqual((verdict, fetches), ("success", 4))
        # and a late run that fails is a failure, not a wait
        answers[-1] = [{"status": "completed", "conclusion": "failure"}]
        self.assertEqual(self.wait(answers, 1800)[0], "failed")

    def test_no_run_at_all_gives_up_at_the_limit(self):
        verdict, fetches, sleeps = self.wait([[]], 1800)
        self.assertEqual(verdict, "missing")
        self.assertEqual(sum(sleeps), 1800)          # never sleeps past the limit
        self.assertEqual(max(sleeps), cm.POLL_MAX)
        self.assertEqual(sleeps[:6], [10, 20, 40, 80, 160, 300])
        self.assertLess(fetches, 15)                 # backoff: few questions

    def test_backoff(self):
        self.assertEqual([cm.backoff(n) for n in range(7)], [10, 20, 40, 80, 160, 300, 300])


class MergeApiRetryTest(unittest.TestCase):
    """Requirements: R-PROC-2"""

    def err(self, code):
        return urllib.error.HTTPError("https://api.github.com/x", code, "e", {}, io.BytesIO(b""))

    def test_a_server_error_is_asked_again(self):
        answers = [self.err(500), self.err(502), {"ok": True}]
        sleeps = []

        def call():
            a = answers.pop(0)
            if isinstance(a, Exception):
                raise a
            return a
        self.assertEqual(cm.with_retries(call, sleep=sleeps.append), {"ok": True})
        self.assertEqual(sleeps, [10, 20])

    def test_gives_up_after_the_tries(self):
        sleeps = []

        def call():
            raise self.err(500)
        with self.assertRaises(urllib.error.HTTPError):
            cm.with_retries(call, tries=3, sleep=sleeps.append)
        self.assertEqual(len(sleeps), 2)

    def test_other_errors_are_not_retried(self):
        sleeps = []

        def call():
            raise self.err(404)
        with self.assertRaises(urllib.error.HTTPError):
            cm.with_retries(call, sleep=sleeps.append)
        self.assertEqual(sleeps, [])
        self.assertTrue(cm.transient(urllib.error.URLError("down")))
        self.assertTrue(cm.transient(self.err(429)))
        self.assertFalse(cm.transient(ValueError("bad json")))


if __name__ == "__main__":
    unittest.main()
