# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import contextlib
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

rec = load_tool("record.py")


class RecordTest(unittest.TestCase):
    """Requirements: R-PROC-4, R-REC-1"""

    def test_every_check_names_known_requirements(self):
        known = {r["id"] for r in rec.requirements_table()}
        self.assertTrue(known)
        ids = [c["id"] for c in rec.CHECKS]
        self.assertEqual(len(ids), len(set(ids)), "duplicate check IDs")
        for c in rec.CHECKS:
            self.assertTrue(c["reqs"], c["id"])
            for r in c["reqs"]:
                self.assertIn(r, known, "%s names unknown %s" % (c["id"], r))

    def test_requirements_table_names_only_real_checks(self):
        # the record's checks, and the similarity audit's (its own workflow, tools/audit.py)
        ids = {c["id"] for c in rec.CHECKS} | set(load_tool("audit.py").REQS)
        for r in rec.requirements_table():
            for named in re.findall(r"C-[A-Z-]+[A-Z]", r["checked_by"]):
                self.assertIn(named, ids, "%s names unknown check %s" % (r["id"], named))

    def test_every_test_class_names_its_requirements(self):
        for path in glob.glob(os.path.join(ROOT, "tests", "test_*.py")):
            with open(path) as f:
                text = f.read()
            classes = re.findall(r'^class \w+\(unittest\.TestCase\):\n    """([^"]*)"""', text, re.M)
            self.assertTrue(classes, "%s: test classes need a docstring" % path)
            for doc in classes:
                self.assertRegex(doc, r"Requirements: R-[A-Z]+-\d+", path)

    def test_traceability(self):
        defined = [{"id": "C-X", "reqs": ["R-PROC-1"]},
                   {"id": "C-Y", "reqs": ["R-PROC-1", "R-PUB-1"]},
                   {"id": "C-Z", "reqs": ["R-PUB-2", "R-LIC-1"]},
                   {"id": "C-W", "reqs": ["R-LIC-1"]}]
        ran = [{"id": "C-X", "result": "PASS"}, {"id": "C-Y", "result": "FAIL"},
               {"id": "C-W", "result": "PASS"}]
        table = {t["requirement"]: t for t in rec.traceability(ran, defined)}
        self.assertEqual(table["R-PROC-1"]["result"], "FAIL")
        self.assertEqual(table["R-PROC-1"]["checks"], ["C-X", "C-Y"])
        self.assertEqual(table["R-PUB-1"]["result"], "FAIL")
        self.assertEqual(table["R-PUB-2"]["result"], "not run in this record (C-Z)")
        self.assertEqual(table["R-LIC-1"]["result"], "PASS (C-Z not run)")
        self.assertTrue(table["R-BOOT-1"]["result"].startswith("not machine-checked"))

    def test_skipped_checks_count_as_not_run(self):
        defined = [{"id": "C-X", "reqs": ["R-PROC-1"]}]
        table = {t["requirement"]: t for t in rec.traceability([{"id": "C-X", "result": "SKIP"}], defined)}
        self.assertEqual(table["R-PROC-1"]["result"], "not run in this record (C-X)")

    def test_spec_side_checks_skip_without_their_folder(self):
        out = tempfile.mkdtemp()
        saved = list(rec.CHECKS)
        try:
            rec.CHECKS[:] = [{"id": "C-T", "title": "t", "reqs": ["R-SEP-2"],
                              "needs": "no-such-folder", "cmd": ["false"]}]
            class A:
                pass
            a = A()
            a.out, a.only, a.skip, a.with_merge = out, None, None, False
            with contextlib.redirect_stdout(io.StringIO()):
                code = rec.cmd_run(a)
            with open(os.path.join(out, "report.json")) as f:
                report = json.load(f)
            self.assertEqual(code, 0)
            self.assertEqual(report["checks"][0]["result"], "SKIP")
            self.assertEqual(report["overall"], "PASS")
        finally:
            rec.CHECKS[:] = saved
            shutil.rmtree(out)

    def test_run_writes_a_complete_record(self):
        out = tempfile.mkdtemp()
        try:
            p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "record.py"), "run",
                                "--out", out, "--only", "C-DENY-LISTS,C-SDK-PIN"],
                               cwd=ROOT, stdout=subprocess.PIPE, universal_newlines=True)
            self.assertEqual(p.returncode, 0, p.stdout)
            with open(os.path.join(out, "report.json")) as f:
                report = json.load(f)
            self.assertEqual([c["id"] for c in report["checks"]], ["C-DENY-LISTS", "C-SDK-PIN"])
            self.assertEqual(report["overall"], "PASS")
            self.assertIn("traceability", report)
            for name in ("report.md", "logs/C-DENY-LISTS.log", "SHA256SUMS"):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)
            sums = rec.read_sums(os.path.join(out, "SHA256SUMS"))
            self.assertIn("report.json", sums)
            self.assertEqual(sums["report.json"], rec.sha256_file(os.path.join(out, "report.json")))
        finally:
            shutil.rmtree(out)

    def test_a_record_file_holding_a_private_term_is_withheld(self):
        out = tempfile.mkdtemp()
        saved, saved_env = list(rec.CHECKS), os.environ.get("PRIVATE_TERMS")
        try:
            os.environ["PRIVATE_TERMS"] = "zebraword"
            rec.CHECKS[:] = [{"id": "C-T", "title": "t", "reqs": ["R-PUB-3"],
                              "cmd": ["sh", "-c", "printf 'a line with Zebra%s in it\\n' Word"]},
                             {"id": "C-U", "title": "u", "reqs": ["R-PUB-3"], "cmd": ["echo", "fine"]}] + \
                            [c for c in saved if c["id"] == "C-RECORD-PRIVATE"]
            class A:
                pass
            a = A()
            a.out, a.only, a.skip, a.with_merge = out, None, None, False
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                code = rec.cmd_run(a)
            self.assertEqual(code, 1)
            self.assertNotIn("zebraword", printed.getvalue().lower())
            with open(os.path.join(out, "report.json")) as f:
                report = json.load(f)
            self.assertEqual([c["id"] for c in report["checks"]], ["C-T", "C-U", "C-RECORD-PRIVATE"])
            self.assertEqual(report["checks"][2]["result"], "FAIL")
            self.assertEqual(report["overall"], "FAIL")
            self.assertEqual([w["file"] for w in report["withheld"]], ["logs/C-T.log"])
            self.assertFalse(os.path.exists(os.path.join(out, "logs", "C-T.log")))
            sums = rec.read_sums(os.path.join(out, "SHA256SUMS"))
            self.assertIn("WITHHELD.json", sums)
            self.assertIn("logs/C-U.log", sums)
            self.assertNotIn("logs/C-T.log", sums)
            for dirpath, _, names in os.walk(out):
                for n in names:
                    with open(os.path.join(dirpath, n), "rb") as f:
                        self.assertNotIn(b"zebraword", f.read().lower(), n)
        finally:
            rec.CHECKS[:] = saved
            if saved_env is None:
                del os.environ["PRIVATE_TERMS"]
            else:
                os.environ["PRIVATE_TERMS"] = saved_env
            shutil.rmtree(out)

    def test_compare(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, "SHA256SUMS"), "w") as f:
                f.write("%s  a.elf\n" % ("0" * 64))
            with open(os.path.join(d, "r.json"), "w") as f:
                json.dump({"outputs": {"a.elf": "0" * 64}}, f)
            run = lambda: subprocess.run([sys.executable, os.path.join(ROOT, "tools", "record.py"),
                                          "compare", "--record", os.path.join(d, "r.json"),
                                          "--outputs", d], stdout=subprocess.DEVNULL).returncode
            self.assertEqual(run(), 0)
            with open(os.path.join(d, "r.json"), "w") as f:
                json.dump({"outputs": {"a.elf": "1" * 64}}, f)
            self.assertEqual(run(), 1)
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
