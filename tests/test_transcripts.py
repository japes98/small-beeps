# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import tempfile
import unittest

from tests.helpers import load_tool

ct = load_tool("check-transcripts.py")
SID = "11111111-2222-3333-4444-555555555555"
BANNER_OK = ("=== small-beeps session banner v1 ===\nrole: clean\nstatus: OK\n"
             "=== end of banner ===\n")


def hook(stdout, code=0):
    return {"type": "attachment", "attachment": {
        "type": "hook_success" if code == 0 else "hook_non_blocking_error",
        "hookEvent": "SessionStart", "hookName": "SessionStart:startup",
        "stdout": stdout, "stderr": "", "exitCode": code}}


def call(name, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": inp}]}}


class TranscriptTest(unittest.TestCase):
    """Requirements: R-CLEAN-1, R-CLEAN-3, R-CLEAN-5"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, entries, role="clean", sid=SID, note=True):
        name = "2026-10-21-%s-%s" % (role, sid)
        with open(os.path.join(self.dir, name + ".jsonl"), "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        if note:
            open(os.path.join(self.dir, name + ".REDACTIONS.md"), "w").close()
        return os.path.join(self.dir, name + ".jsonl")

    def problems(self, path):
        return ct.check_session(path)[0]

    def test_clean_session_with_banner_passes(self):
        p = self.write([hook(BANNER_OK), call("Read", file_path="/x/docs/PLAN.md"),
                        call("Bash", command="git status")])
        self.assertEqual(self.problems(p), [])

    def test_missing_banner_fails(self):
        p = self.write([call("Read", file_path="README.md")])
        self.assertTrue(any("no SessionStart banner" in x for x in self.problems(p)))

    def test_mismatch_fails(self):
        bad = BANNER_OK.replace("status: OK", "status: CONFIG MISMATCH")
        p = self.write([hook(bad, 1)])
        self.assertTrue(any("CONFIG MISMATCH" in x for x in self.problems(p)))

    def test_first_session_is_exempt_only_by_id(self):
        sid = next(iter(ct.EXEMPT_NO_BANNER))
        p = self.write([call("Read", file_path="README.md")], sid=sid)
        self.assertEqual(self.problems(p), [])

    def test_forbidden_reads_fetches_and_commands_fail(self):
        cases = [
            call("Read", file_path="/w/vendor/emulator/src/lib.rs"),
            call("Read", file_path="./harness/src/main.rs"),
            call("Grep", pattern="lcd", path="/w/fm1-sid"),
            call("WebFetch", url="https://github.com/hugelton/Felucca"),
            call("WebFetch", url="https://thefirmwarehub.com/x"),
            call("Bash", command="git clone https://github.com/zvenson/dinghy"),
            call("Bash", command="cat ../fm1-emu/crates/fm1-soc/src/lcd.rs"),
            call("Glob", pattern="**/probes/lcdtest.c"),
            call("Bash", command="ls harness"),
            call("Bash", command="cat vendor/emulator/README"),
            call("WebFetch", url="https://github.com/AL-255/FM-1-RE/tree/main/firmware-images"),
        ]
        for c in cases:
            p = self.write([hook(BANNER_OK), c])
            self.assertTrue(any("forbidden" in x for x in self.problems(p)), json.dumps(c))

    def test_reviewed_hits_pass_only_for_that_exact_call(self):
        c = call("Bash", command="printf 'leaves out vendor/emulator/' > msg.txt")
        c["message"]["content"][0]["id"] = "toolu_1"
        p = self.write([hook(BANNER_OK), c])
        rule = "vendor/emulator/ (spec side)"
        self.assertTrue(self.problems(p))
        ok = ct.check_session(p, {(SID, "toolu_1", rule): "writes a message only"})
        self.assertEqual(ok[0], [])
        self.assertTrue(any("REVIEWED toolu_1" in l for l in ok[1]))
        self.assertTrue(ct.check_session(p, {(SID, "toolu_2", rule): "other call"})[0])
        self.assertTrue(ct.check_session(p, {("other", "toolu_1", rule): "other session"})[0])

    def test_reviewed_file_needs_a_reason(self):
        with open(os.path.join(self.dir, "REVIEWED.json"), "w") as f:
            json.dump({"reviewed": [{"session": SID, "tool_use_id": "t", "rule": "r"}]}, f)
        with self.assertRaises(SystemExit):
            ct.load_reviewed(self.dir)

    def test_writing_about_forbidden_material_is_not_a_read(self):
        p = self.write([hook(BANNER_OK),
                        call("Write", file_path="/w/CONTRIBUTING.md",
                             content="never open vendor/emulator/ or Felucca")])
        self.assertEqual(self.problems(p), [])

    def test_words_that_are_not_paths_pass(self):
        p = self.write([hook(BANNER_OK),
                        call("Bash", command="python3 tools/check-transcripts.py"),
                        call("Grep", pattern="harnessing", path="docs")])
        self.assertEqual(self.problems(p), [])

    def test_spec_side_may_read_emulator_source(self):
        p = self.write([hook(BANNER_OK.replace("clean", "spec")),
                        call("Read", file_path="/w/vendor/emulator/src/lib.rs")], role="spec")
        self.assertEqual(self.problems(p), [])

    def test_subagent_transcripts_are_checked(self):
        p = self.write([hook(BANNER_OK)])
        sub = p[:-len(".jsonl")] + ".subagents"
        os.makedirs(sub)
        with open(os.path.join(sub, "agent-1.jsonl"), "w") as f:
            f.write(json.dumps(call("Read", file_path="/w/harness/src/x.rs")) + "\n")
        self.assertTrue(any("forbidden" in x for x in self.problems(p)))

    def test_redaction_note_required(self):
        p = self.write([hook(BANNER_OK)], note=False)
        self.assertTrue(any("redaction note" in x for x in self.problems(p)))

    def test_bad_file_name_fails(self):
        with open(os.path.join(self.dir, "notes.jsonl"), "w") as f:
            f.write("{}\n")
        self.assertTrue(self.problems(os.path.join(self.dir, "notes.jsonl")))


if __name__ == "__main__":
    unittest.main()
