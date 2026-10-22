# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import csv
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

perf = load_tool("perf.py")

BUDGETS = {"milestone": "M0", "speed_rise_percent": 3,
           "limits": {"code": 512, "static_ram": 64, "stack_high_water": 256}}


def measured(instructions=100000, periods=1000, code=252, static_ram=24, stack=0):
    return {"label": "t", "instructions": instructions, "periods": periods, "code": code,
            "static_ram": static_ram, "stack_high_water": stack}


def results(verdicts):
    return {v["gate"]: v["result"] for v in verdicts}


class GateTest(unittest.TestCase):
    """Requirements: R-PERF-1, R-PERF-2, R-PERF-5"""

    def test_speed_boundaries(self):
        base = measured(100000, 1000)            # 100 per period
        for instr, want in ((103000, "PASS"),    # exactly +3%: allowed
                            (103001, "FAIL"),    # just over
                            (100000, "PASS"),
                            (97000, "PASS"),     # exactly -3%: an ordinary pass
                            (96999, "IMPROVED")):
            self.assertEqual(results(perf.gate(measured(instr, 1000), base, BUDGETS))["speed"], want, instr)

    def test_speed_is_per_period(self):
        # twice the instructions over twice the periods is no change
        base = measured(100000, 1000)
        self.assertEqual(results(perf.gate(measured(200000, 2000), base, BUDGETS))["speed"], "PASS")
        self.assertEqual(results(perf.gate(measured(200000, 1000), base, BUDGETS))["speed"], "FAIL")

    def test_improvement_is_reported_and_passes(self):
        v = perf.gate(measured(50000, 1000), measured(100000, 1000), BUDGETS)
        self.assertFalse(perf.failed(v))
        speed = [x for x in v if x["gate"] == "speed"][0]
        self.assertIn("-50.00%", speed["detail"])
        text = perf.summary({"result": "PASS", "current": measured(), "baseline_note": "b",
                             "gates": v, "budgets": BUDGETS})
        self.assertIn("IMPROVED", text)
        self.assertIn("say so in the pull request", text)

    def test_budgets(self):
        for key, arg in (("code", "code"), ("static_ram", "static_ram"), ("stack_high_water", "stack")):
            at = measured(**{arg: BUDGETS["limits"][key]})
            over = measured(**{arg: BUDGETS["limits"][key] + 1})
            self.assertEqual(results(perf.gate(at, None, BUDGETS))[key], "PASS", key)
            r = results(perf.gate(over, None, BUDGETS))
            self.assertEqual(r[key], "FAIL", key)
            self.assertEqual([k for k, x in r.items() if x == "FAIL"], [key])

    def test_no_baseline_is_not_compared(self):
        v = perf.gate(measured(), None, BUDGETS)
        self.assertEqual(results(v)["speed"], "NOT COMPARED")
        self.assertFalse(perf.failed(v))
        v = perf.gate(measured(), {"label": "baseline", "error": "did not run"}, BUDGETS)
        self.assertEqual(results(v)["speed"], "NOT COMPARED")

    def test_a_failed_measurement_fails(self):
        cur = dict(measured(), error="no heartbeat")
        v = perf.gate(cur, measured(), BUDGETS)
        self.assertEqual(results(v)["measurement"], "FAIL")
        self.assertNotIn("speed", results(v))

    def test_probe_expectations(self):
        slow = perf.gate(measured(200000), measured(), BUDGETS)
        self.assertEqual(perf.check_probe("SLOW", slow, {"speed"}, {"code", "static_ram", "stack_high_water"}), [])
        # a probe the gate let through is a problem
        self.assertTrue(perf.check_probe("SLOW", perf.gate(measured(), measured(), BUDGETS), {"speed"}, set()))
        # and so is one that failed a gate it should not touch
        both = perf.gate(measured(200000, code=9999), measured(), BUDGETS)
        self.assertTrue(perf.check_probe("SLOW", both, {"speed"}, {"code"}))
        big = perf.gate(measured(code=9999, static_ram=999, stack=999), measured(), BUDGETS)
        self.assertEqual(perf.check_probe("BIG", big, {"code", "static_ram", "stack_high_water"}, set()), [])

    def test_the_real_budgets_load(self):
        b = perf.load_budgets()
        self.assertIn(b["milestone"], json.load(open(perf.BUDGETS))["budgets"])
        self.assertEqual(sorted(b["limits"]), sorted(perf.BUDGETED))
        self.assertEqual(b["speed_rise_percent"], 3)


class MeasureTest(unittest.TestCase):
    """Requirements: R-PERF-1, R-PERF-3"""

    def test_stack_high_water(self):
        n = 1024
        self.assertEqual(perf.stack_high_water(bytes(n)), 0)
        self.assertEqual(perf.stack_high_water(bytes(n - 4) + b"\x01\0\0\0"), 4)
        self.assertEqual(perf.stack_high_water(b"\0\0\0\x80" + bytes(n - 4)), n)
        # zeros above the deepest written word still count as used
        data = bytes(n - 64) + b"\x07\0\0\0" + bytes(60)
        self.assertEqual(perf.stack_high_water(data), 64)

    def test_options_capture_the_stack_below_its_top(self):
        opts = perf.options(0x1000)
        self.assertIn("0x01c7ec00:0x1000@end", opts)
        self.assertIn("0x01c00000:0x10@end", opts)
        self.assertEqual(perf.capture_name(0x01c7ec00, 0x1000), "ram-01c7ec00-1000-end.bin")

    def test_layout_constants_match_the_linker_script(self):
        with open(os.path.join(ROOT, "firmware", "app.ld")) as f:
            ld = f.read()
        self.assertIn("__stack_top == 0x%08X" % perf.STACK_TOP, ld)
        self.assertIn("ADDR(.beacon) == 0x%08X" % perf.BEACON, ld)
        with open(os.path.join(ROOT, "firmware", "src", "sb.h")) as f:
            self.assertIn("SB_MARKER     0x%08xu" % perf.MARKER, f.read())

    def test_read_size(self):
        size = perf.read_size("code 252\ndata 4\nbss 20\nimage 256\nstack 4096\n")
        self.assertEqual(size["code"], 252)
        with self.assertRaises(ValueError):
            perf.read_size("code 252\n")


class BaselineTest(unittest.TestCase):
    """Requirements: R-PERF-2"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.saved = perf.REPO
        perf.REPO = self.dir
        self.g("init", "-q", "-b", "main")
        self.shas = []
        for i in range(3):
            with open(os.path.join(self.dir, "f"), "w") as f:
                f.write(str(i))
            self.g("add", "f")
            self.g("commit", "-q", "-m", "c%d" % i)
            self.shas.append(self.g("rev-parse", "HEAD"))
        # a records branch with records of the first two commits
        self.g("checkout", "-q", "--orphan", "records")
        self.g("rm", "-q", "-rf", ".")
        for n, sha in enumerate(self.shas[:2]):
            d = os.path.join(self.dir, "records", sha, "outputs")
            os.makedirs(d)
            with open(os.path.join(d, "app.bin"), "wb") as f:
                f.write(bytes([n]))
            with open(os.path.join(d, "app.size"), "w") as f:
                f.write("code %d\n" % n)
        self.g("add", "records")
        self.g("commit", "-q", "-m", "records")
        self.g("checkout", "-q", "main")

    def tearDown(self):
        perf.REPO = self.saved
        shutil.rmtree(self.dir)

    def g(self, *args):
        return subprocess.run(["git", "-C", self.dir, "-c", "user.name=t", "-c", "user.email=t@example.org"]
                              + list(args), check=True, stdout=subprocess.PIPE,
                              universal_newlines=True).stdout.strip()

    def test_latest_record_on_the_history(self):
        sha, files, note = perf.find_baseline("main", "records", head="none")
        self.assertEqual(sha, self.shas[1])       # the newest commit with a record
        self.assertEqual(files["outputs/app.bin"], b"\x01")
        self.assertIsNone(files["report.json"])

    def test_never_the_commit_under_test(self):
        # the records workflow: the new commit's own record is not its baseline
        sha, _, _ = perf.find_baseline("main", "records", head=self.shas[1])
        self.assertEqual(sha, self.shas[0])
        sha, _, _ = perf.find_baseline(self.shas[1] + "^1", "records", head=self.shas[1])
        self.assertEqual(sha, self.shas[0])

    def test_no_records(self):
        sha, files, note = perf.find_baseline("main", "no-such-ref", head="none")
        self.assertIsNone(sha)
        self.assertIn("not available", note)
        sha, _, note = perf.find_baseline(self.shas[0] + "^0", "records", head=self.shas[0])
        self.assertIsNone(sha)


class HistoryTest(unittest.TestCase):
    """Requirements: R-PERF-4"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.csv = os.path.join(self.dir, "perf-history.csv")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def record(self, commit, ipp=356.887):
        path = os.path.join(self.dir, commit + ".json")
        cur = dict(measured(356887, 1000), data=4, bss=20, image=256, stack_reserved=4096,
                   instructions_per_period=ipp, fwtest_image="img@sha256:ab")
        with open(path, "w") as f:
            json.dump({"commit": commit, "created_utc": "2026-10-22T00:00:00Z", "overall": "PASS",
                       "perf": {"period": "heartbeat", "budgets": BUDGETS, "current": cur,
                                "speed_change_percent": 0.0}}, f)
        return path

    def history(self, record):
        class A:
            pass
        a = A()
        a.record, a.csv = record, self.csv
        return perf.cmd_history(a)

    def test_one_line_per_commit_appended_never_rewritten(self):
        self.assertEqual(self.history(self.record("a" * 40)), 0)
        with open(self.csv, "rb") as f:
            first = f.read()
        self.assertEqual(self.history(self.record("b" * 40)), 0)
        # a re-run of the records workflow for the same commit adds nothing
        self.assertEqual(self.history(self.record("b" * 40, ipp=1.0)), 0)
        with open(self.csv, "rb") as f:
            now = f.read()
        self.assertTrue(now.startswith(first))
        rows = list(csv.DictReader(open(self.csv)))
        self.assertEqual([r["commit"] for r in rows], ["a" * 40, "b" * 40])
        self.assertEqual(rows[1]["instructions_per_period"], "356.887")
        self.assertEqual(rows[1]["stack_high_water"], "0")
        self.assertEqual(rows[1]["milestone"], "M0")

    def test_a_record_without_perf_still_gets_its_line(self):
        path = os.path.join(self.dir, "old.json")
        with open(path, "w") as f:
            json.dump({"commit": "c" * 40, "overall": "FAIL"}, f)
        self.assertEqual(self.history(path), 0)
        rows = list(csv.DictReader(open(self.csv)))
        self.assertEqual(rows[0]["commit"], "c" * 40)
        self.assertEqual(rows[0]["code"], "")

    def test_an_unexpected_header_is_refused(self):
        with open(self.csv, "w") as f:
            f.write("something,else\n")
        self.assertEqual(self.history(self.record("a" * 40)), 1)

    def test_header_names_every_measure(self):
        for k in ("code", "static_ram", "stack_high_water", "instructions_per_period", "image"):
            self.assertIn(k, perf.HISTORY_FIELDS)
        self.assertTrue(re.match(r"^commit,", ",".join(perf.HISTORY_FIELDS)))


class ProbeSourceTest(unittest.TestCase):
    """Requirements: R-PERF-5"""

    def test_probes_are_compiled_only_on_request(self):
        # every probe's code is under its define, so the firmware itself
        # carries none of it
        for name in ("main.c", "probe.c", "sb.h"):
            with open(os.path.join(ROOT, "firmware", "src", name)) as f:
                text = f.read()
            guard = []
            for line in text.splitlines():
                m = re.match(r"#if defined\((SB_PROBE_\w+)\)", line)
                if m:
                    guard.append(m.group(1))
                elif line.startswith("#endif") and guard:
                    guard.pop()
                elif re.search(r"\bsb_probe_\w+|probe_(table|ram|stack)\b", line):
                    self.assertTrue(guard, "%s: %r outside a probe's #if" % (name, line))
        self.assertEqual({d for d, _, _ in perf.PROBES}, {"SB_PROBE_SLOW", "SB_PROBE_BIG"})


if __name__ == "__main__":
    unittest.main()
