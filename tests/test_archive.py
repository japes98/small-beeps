# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

ar = load_tool("archive-session.py")
ct = load_tool("check-transcripts.py")

# Built at run time so this file never contains a token-shaped string.
TOKEN = "gh" + "o_" + "A1b2C3d4" * 5
KEY = "sk-" + "ant-" + "x" * 30
PRIVATE = ("-----BEGIN OPENSSH " + "PRIVATE KEY-----\\nabc\\n-----END OPENSSH "
           + "PRIVATE KEY-----")


class ArchiveTest(unittest.TestCase):
    """Requirements: R-CLEAN-3"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_redact_line(self):
        counts = {}
        line = json.dumps({
            "text": "token %s key %s mail jp@example.net keep noreply@anthropic.com "
                    "path /Users/someone/Development/x tmp /private/tmp/claude-501/a"
                    % (TOKEN, KEY),
            "ownerAccountUuid": "abc-123"}) + "\n"
        line = line.replace("PLACEHOLDER", "")
        out = ar.redact_line(line, counts)
        json.loads(out)
        for gone in (TOKEN, KEY, "jp@example.net", "/Users/someone", "claude-501", "abc-123"):
            self.assertNotIn(gone, out)
        self.assertIn("noreply@anthropic.com", out)
        self.assertIn("~/Development/x", out)

    def test_private_key_in_json_string(self):
        line = json.dumps({"t": "x"}).replace('"x"', '"%s"' % PRIVATE) + "\n"
        counts = {}
        out = ar.redact_line(line, counts)
        self.assertNotIn("PRIVATE KEY-----\\nabc", out)
        json.loads(out)

    def test_top_folder_user_and_private_terms_anywhere(self):
        path = os.path.join(self.dir, "t.jsonl")
        line = json.dumps({"cwd": "/Users/someone/Dev/TopFolder/clean",
                           "p": "-Users-someone-Dev-TopFolder-clean",
                           "ls": "drwx someone staff; SOMEONE2; on Secret-Box here"}) + "\n"
        with open(path, "w") as f:
            f.write(line)
        saved = os.environ.get("PRIVATE_TERMS")
        os.environ["PRIVATE_TERMS"] = "# a comment\nsecret-box\n"
        try:
            extra = ar.top_rules("TopFolder") + ar.user_rules(path, me="") + ar.private_rules()
        finally:
            if saved is None:
                del os.environ["PRIVATE_TERMS"]
            else:
                os.environ["PRIVATE_TERMS"] = saved
        counts = {}
        out = ar.redact_line(line, counts, extra)
        json.loads(out)
        for gone in ("someone", "SOMEONE", "TopFolder", "Secret-Box"):
            self.assertNotIn(gone, out)
        self.assertIn("~/Dev/<top>/clean", out)
        self.assertIn("-HOME-Dev-<top>-clean", out)
        self.assertIn("[REDACTED:private]", out)
        self.assertEqual(ar.top_rules(None), [])

    def test_a_term_containing_the_user_name_goes_whole(self):
        path = os.path.join(self.dir, "t.jsonl")
        line = json.dumps({"host": "on someones-laptop now", "u": "/Users/someone/x"}) + "\n"
        with open(path, "w") as f:
            f.write(line)
        saved = os.environ.get("PRIVATE_TERMS")
        os.environ["PRIVATE_TERMS"] = "someones-laptop\n"
        try:
            extra = ar.private_rules() + ar.top_rules(None) + ar.user_rules(path, me="")
        finally:
            if saved is None:
                del os.environ["PRIVATE_TERMS"]
            else:
                os.environ["PRIVATE_TERMS"] = saved
        out = ar.redact_line(line, {}, extra)
        json.loads(out)
        self.assertIn("on [REDACTED:private] now", out)
        self.assertNotIn("laptop", out)

    def test_default_top_skips_a_bare_repository_name(self):
        top = ar.default_top()
        if top is not None:
            self.assertNotEqual(top, os.path.basename(ROOT))

    def test_archive_end_to_end_then_check(self):
        sid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        src_dir = os.path.join(self.dir, "projects")
        os.makedirs(os.path.join(src_dir, sid, "subagents"))
        src = os.path.join(src_dir, sid + ".jsonl")
        banner = ("=== small-beeps session banner v1 ===\nstatus: OK\n")
        with open(src, "w") as f:
            f.write(json.dumps({"type": "attachment", "timestamp": "2026-10-22T01:02:03Z",
                                "attachment": {"hookEvent": "SessionStart", "exitCode": 0,
                                               "stdout": banner}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content": "hi " + TOKEN}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content":
                "cwd /Users/someuser/x; drwxr-xr-x 3 someuser staff; host Some-Mac.local"}}) + "\n")
        with open(os.path.join(src_dir, sid, "subagents", "agent-a.jsonl"), "w") as f:
            f.write(json.dumps({"type": "assistant", "message": {"content": []}}) + "\n")
        out = os.path.join(self.dir, "sessions", "clean")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "archive-session.py"),
                        src, "--role", "clean", "--out", out], check=True,
                       stdout=subprocess.DEVNULL)
        name = "2026-10-22-clean-" + sid
        with open(os.path.join(out, name + ".jsonl")) as f:
            text = f.read()
        for gone in (TOKEN, "someuser", "Some-Mac.local"):
            self.assertNotIn(gone, text)
        self.assertTrue(os.path.exists(os.path.join(out, name + ".REDACTIONS.md")))
        self.assertTrue(os.path.exists(os.path.join(out, name + ".subagents", "agent-a.jsonl")))
        self.assertEqual(ct.check_session(os.path.join(out, name + ".jsonl"))[0], [])
        # Archiving the same session twice is refused.
        again = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "archive-session.py"),
                                src, "--role", "clean", "--out", out],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertNotEqual(again.returncode, 0)

    def test_git_summary_lines_naming_spec_side_files(self):
        names = {"harness/src/a.rs", "harness/tests/golden/x/long-name.bin",
                 "vendor/emulator/LICENSE", "docs/PLAN.md", "tests/golden.py"}
        summary = "\n".join([
            "Fast-forward",
            " docs/PLAN.md                 |  4 +-",
            " harness/src/a.rs             | 12 +",
            " .../golden/x/long-name.bin   | Bin 0 -> 8 bytes",
            " vendor/emulator/LICENSE      | 21 +",
            " tests/golden.py              |  3 +",
            " 5 files changed, 40 insertions(+)",
            " create mode 100644 docs/PLAN.md",
            " create mode 100644 harness/src/a.rs",
            "exit=0"])
        line = json.dumps({"content": summary, "stdout": summary}) + "\n"
        counts = {}
        out = ar.redact_line(line, counts, spec_files=names)
        d = json.loads(out)
        self.assertEqual(d["content"], d["stdout"])
        self.assertEqual(d["content"].splitlines(), [
            "Fast-forward",
            " docs/PLAN.md                 |  4 +-",
            " [redacted: 3 line(s) naming spec-side files]",
            " tests/golden.py              |  3 +",
            " 5 files changed, 40 insertions(+)",
            " create mode 100644 docs/PLAN.md",
            " [redacted: 1 line(s) naming spec-side files]",
            "exit=0"])
        self.assertEqual(counts["spec-side file name in a git summary (lines)"], 8)
        # Spec transcripts and plain mentions of the folders are left alone.
        self.assertEqual(ar.redact_line(line, {}), line)
        prose = json.dumps({"t": "the sparse checkout leaves out harness/\nand more"}) + "\n"
        self.assertEqual(ar.redact_line(prose, {}, spec_files=names), prose)

    def test_settings_local_json_is_not_a_host_name(self):
        out = ar.redact_line(json.dumps({"t": "see .claude/settings.local.json"}) + "\n", {})
        self.assertIn("settings.local.json", out)


if __name__ == "__main__":
    unittest.main()
