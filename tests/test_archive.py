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
        out = os.path.join(self.dir, "sessions")
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

    def test_settings_local_json_is_not_a_host_name(self):
        out = ar.redact_line(json.dumps({"t": "see .claude/settings.local.json"}) + "\n", {})
        self.assertIn("settings.local.json", out)


if __name__ == "__main__":
    unittest.main()
