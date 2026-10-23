# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import tempfile
import unittest

from tests.helpers import PLACEHOLDER_FOLDERS, load_tool

ct = load_tool("check-transcripts.py")
# The spec-side folders' rules built from made-up names (tests/helpers.py),
# as check-transcripts.py builds them from config/spec-side-folders.
ct.configure(PLACEHOLDER_FOLDERS)
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
            call("Read", file_path="/w/spa/one/src/lib.rs"),
            call("Read", file_path="./sptwo/src/main.rs"),
            call("Grep", pattern="lcd", path="/w/fm1-sid"),
            call("WebFetch", url="https://github.com/hugelton/Felucca"),
            call("WebFetch", url="https://thefirmwarehub.com/x"),
            call("Bash", command="git clone https://github.com/zvenson/dinghy"),
            call("Bash", command="cat ../fm1-emu/crates/fm1-soc/src/lcd.rs"),
            call("Glob", pattern="**/probes/lcdtest.c"),
            call("Bash", command="ls sptwo"),
            call("Bash", command="cat spa/one/README"),
            call("WebFetch", url="https://github.com/AL-255/FM-1-RE/tree/main/firmware-images"),
            call("Read", file_path="/w/spl/three/2026-10-22-spec-x.jsonl"),
            call("Bash", command="ls spl/three"),
        ]
        for c in cases:
            p = self.write([hook(BANNER_OK), c])
            self.assertTrue(any("forbidden" in x for x in self.problems(p)), json.dumps(c))

    def test_reviewed_hits_pass_only_for_that_exact_call(self):
        c = call("Bash", command="printf 'leaves out spa/one/' > msg.txt")
        c["message"]["content"][0]["id"] = "toolu_1"
        p = self.write([hook(BANNER_OK), c])
        rule = "spa/one/ (spec side)"
        self.assertTrue(self.problems(p))
        ok = ct.check_session(p, {(SID, "toolu_1", rule): "writes a message only"})
        self.assertEqual(ok[0], [])
        i = next(n for n, l in enumerate(ok[1]) if "toolu_1" in l)
        self.assertEqual(ok[1][i + 1].strip(), "REVIEWED F-VENDOR-EMU")
        self.assertTrue(ct.check_session(p, {(SID, "toolu_2", rule): "other call"})[0])
        self.assertTrue(ct.check_session(p, {("other", "toolu_1", rule): "other session"})[0])

    def heredoc_call(self, body, head="python3 - <<'EOF'", tail=""):
        c = call("Bash", command="%s\n%s\nEOF%s" % (head, body, tail))
        c["message"]["content"][0]["id"] = "toolu_h"
        return self.problems(self.write([hook(BANNER_OK), c]))

    def test_heredoc_that_only_edits_the_reviewed_list_passes(self):
        body = ("import json\np='sessions/REVIEWED.json'; d=json.load(open(p))\n"
                "d['reviewed'].append({'reason': 'names sptwo/ and spa/one/ and spl/three/'})\n"
                "open(p,'w').write(json.dumps(d))")
        self.assertEqual(self.heredoc_call(body, tail="\ngit diff --stat sessions/REVIEWED.json"), [])

    def test_heredoc_that_reads_a_clean_transcript_passes(self):
        body = ("import json\nf='sessions/clean/2026-10-22-clean-x.jsonl'\n"
                "for l in open(f):\n    if any(k in l for k in ('sptwo','spa/one','spl/three')):\n"
                "        print(l[:200])")
        self.assertEqual(self.heredoc_call(body, head="cd ~/w/clean && python3 - <<'EOF'"), [])

    def test_heredocs_that_reach_further_still_fail(self):
        names = "x=('sptwo/', 'spa/one/', 'spl/three/')\n"
        bodies = [
            "open('sessions/' + 'spec/x')",                       # a built path
            "p='sessions/clean/a'\np='sptwo/b'\nopen(p)",       # rebound name
            "open('sessions/clean/../spec/x')",                   # escapes the folder
            "open('/w/sptwo/x')",
            "import os\nos.listdir('sptwo')",
            "import glob\nglob.glob('sptwo/*')",
            "import subprocess\nsubprocess.run(['cat', 'sptwo/x'])",
            "from os import listdir\nlistdir('sptwo')",
            "__import__('os').listdir('sptwo')",
            "exec(\"open('sptwo/x')\")",
            "open('sessions/clean/a').__class__",
            "def f():\n    return 1",
            "this is not python sptwo/",
        ]
        for b in bodies:
            self.assertTrue(self.heredoc_call(names + b), b)
        ok = names + "open('sessions/REVIEWED.json')"
        self.assertTrue(self.heredoc_call(ok, head="python3 - <<EOF"))          # unquoted: expands
        self.assertTrue(self.heredoc_call(ok, head="cat > x.py <<'EOF'"))        # not python
        self.assertTrue(self.heredoc_call(ok, head="cd sptwo && python3 - <<'EOF'"))
        self.assertTrue(self.heredoc_call(ok, tail="\ncat sptwo/x"))
        self.assertEqual(self.heredoc_call(ok), [])

    def test_other_rules_are_never_cleared(self):
        body = "x='https://github.com/hugelton/Felucca'\nopen('sessions/REVIEWED.json')"
        self.assertTrue(any("F-FELUCCA" in x for x in self.heredoc_call(body)))

    def test_plain_commands_naming_the_folders_still_fail(self):
        for cmd in ("cat sessions/clean/a sptwo/b", "cd sptwo && ls", "D=spa/one/; ls $D",
                    "git show HEAD:sptwo/x"):
            p = self.write([hook(BANNER_OK), call("Bash", command=cmd)])
            self.assertTrue(any("forbidden" in x for x in self.problems(p)), cmd)

    def test_folder_names_ended_by_a_shell_operator_fail(self):
        for cmd in ("D=spa/one; ls $D", "D=sptwo; ls $D", "ls spl/three;",
                    "ls sptwo&& true", "ls sptwo|head", "cat <sptwo/x", "(cd sptwo)",
                    "x=`ls sptwo`", "{ ls spa/one; }", "ls spl/three>out",
                    "for p in spa/one sptwo spl/three; do ls $p; done"):
            p = self.write([hook(BANNER_OK), call("Bash", command=cmd)])
            self.assertTrue(any("forbidden" in x for x in self.problems(p)), cmd)

    def test_names_that_only_contain_a_folder_name_pass(self):
        p = self.write([hook(BANNER_OK),
                        call("Bash", command="ls tests/sptwo_free; ls spl/threeimen; "
                                             "grep -n sptwoing docs/x.md; ls one/; ls myspa/onex")])
        self.assertEqual(self.problems(p), [])

    def test_a_superseded_entry_clears_nothing_and_must_stay_unneeded(self):
        c = call("Bash", command="printf 'leaves out spa/one/' > msg.txt")
        c["message"]["content"][0]["id"] = "toolu_1"
        p = self.write([hook(BANNER_OK), c])
        key = (SID, "toolu_1", "spa/one/ (spec side)")
        probs = ct.check_session(p, {key: {"superseded": "x"}})[0]
        self.assertTrue(any("marked superseded" in x for x in probs))
        with open(os.path.join(self.dir, "REVIEWED.json"), "w") as f:
            json.dump({"reviewed": [{"session": SID, "tool_use_id": "t", "rule": "r",
                                     "reason": "x", "superseded": "y"}]}, f)
        self.assertEqual(ct.load_reviewed(self.dir)[(SID, "t", "r")], {"superseded": "y"})

    def test_output_never_quotes_the_transcript(self):
        secret = "private-words-here"
        c = call("Bash", command="cat sptwo/x # " + secret)
        c["message"]["content"][0]["id"] = "toolu_q"
        problems, lines = ct.check_session(self.write([hook(BANNER_OK), c]))
        text = "\n".join(problems + lines)
        self.assertNotIn(secret, text)
        self.assertNotIn("cat sptwo", text)
        self.assertIn("entry 2 shell Bash toolu_q touches forbidden material (F-HARNESS)", text)

    def test_reviewed_file_needs_a_reason(self):
        with open(os.path.join(self.dir, "REVIEWED.json"), "w") as f:
            json.dump({"reviewed": [{"session": SID, "tool_use_id": "t", "rule": "r"}]}, f)
        with self.assertRaises(SystemExit):
            ct.load_reviewed(self.dir)

    def test_writing_about_forbidden_material_is_not_a_read(self):
        p = self.write([hook(BANNER_OK),
                        call("Write", file_path="/w/CONTRIBUTING.md",
                             content="never open spa/one/ or Felucca")])
        self.assertEqual(self.problems(p), [])

    def test_words_that_are_not_paths_pass(self):
        p = self.write([hook(BANNER_OK),
                        call("Bash", command="python3 tools/check-transcripts.py"),
                        call("Grep", pattern="sptwoing", path="docs")])
        self.assertEqual(self.problems(p), [])

    def test_spec_side_may_read_emulator_source(self):
        p = self.write([hook(BANNER_OK.replace("clean", "spec")),
                        call("Read", file_path="/w/spa/one/src/lib.rs")], role="spec")
        self.assertEqual(self.problems(p), [])

    def test_subagent_transcripts_are_checked(self):
        p = self.write([hook(BANNER_OK)])
        sub = p[:-len(".jsonl")] + ".subagents"
        os.makedirs(sub)
        with open(os.path.join(sub, "agent-1.jsonl"), "w") as f:
            f.write(json.dumps(call("Read", file_path="/w/sptwo/src/x.rs")) + "\n")
        self.assertTrue(any("forbidden" in x for x in self.problems(p)))

    def test_redaction_note_required(self):
        p = self.write([hook(BANNER_OK)], note=False)
        self.assertTrue(any("redaction note" in x for x in self.problems(p)))

    def test_bad_file_name_fails(self):
        with open(os.path.join(self.dir, "notes.jsonl"), "w") as f:
            f.write("{}\n")
        self.assertTrue(self.problems(os.path.join(self.dir, "notes.jsonl")))


class LayoutTest(unittest.TestCase):
    """Requirements: R-CLEAN-3, R-SEP-2"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def put(self, folder, role, sid=SID):
        d = os.path.join(self.dir, folder)
        os.makedirs(d, exist_ok=True)
        name = "2026-10-21-%s-%s" % (role, sid)
        with open(os.path.join(d, name + ".jsonl"), "w") as f:
            f.write(json.dumps(hook(BANNER_OK)) + "\n")
        open(os.path.join(d, name + ".REDACTIONS.md"), "w").close()
        return os.path.join(d, name + ".jsonl")

    def run_main(self):
        import contextlib
        import io
        import sys
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ["check-transcripts.py", self.dir]
        try:
            with contextlib.redirect_stdout(out):
                code = ct.main()
        finally:
            sys.argv = argv
        return code, out.getvalue()

    def test_role_must_match_folder(self):
        p = self.put("spec", "clean")
        self.assertTrue(any("in spec/" in x for x in ct.check_session(p)[0]))

    def test_clean_folder_without_spec_transcripts_skips_them(self):
        self.put("clean", "clean")
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("spec/: not on disk; spec-side transcripts skipped, not read", out)
        self.assertIn("1 archived transcript(s) checked: PASS", out)

    def test_both_folders_are_checked(self):
        self.put("clean", "clean")
        self.put("spec", "spec", sid="99999999-2222-3333-4444-555555555555")
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("2 archived transcript(s) checked: PASS", out)

    def test_transcript_outside_role_folders_fails(self):
        self.put(".", "clean")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("outside clean/ and spec/", out)

    def test_an_auditor_transcript_fails_anywhere_under_sessions(self):
        os.makedirs(os.path.join(self.dir, "auditor"))
        self.put("auditor", "clean")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("auditor/", out)
        self.assertIn("outside clean/ and spec/", out)

    def test_reviewed_list_is_found_from_a_role_folder(self):
        with open(os.path.join(self.dir, "REVIEWED.json"), "w") as f:
            json.dump({"reviewed": [{"session": SID, "tool_use_id": "t", "rule": "r",
                                     "reason": "x"}]}, f)
        os.makedirs(os.path.join(self.dir, "clean"))
        self.assertIn((SID, "t", "r"), ct.load_reviewed(os.path.join(self.dir, "clean")))


if __name__ == "__main__":
    unittest.main()
