# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import hashlib
import json
import os
import unittest

from tests.helpers import PLACEHOLDER_FOLDERS, ROOT, load_tool

ct = load_tool("check-transcripts.py")
ar = load_tool("archive-session.py")
cp = load_tool("check-private.py")

# The barrier tools and their tests, which build the spec-side folders'
# names from config/spec-side-folders (since M3) and so never spell them
# out: changing one of them needs no command that names the folders.
BARRIER_FILES = [
    "tools/clean-setup.sh", "tools/clean-update.sh", "tools/setup-folder.sh",
    "tools/check-clean-folder.sh", "tools/reproduce", "tools/check-transcripts.py",
    "tools/archive-session.py", "tools/check-private.py",
    "tests/test_transcripts.py", "tests/test_archive.py", "tests/test_private.py",
    "tests/test_folder_list.py", "tests/helpers.py",
]
SHELL_TOOLS = ["tools/clean-update.sh", "tools/setup-folder.sh", "tools/check-clean-folder.sh",
               "tools/reproduce"]
# SHA-256 of the transcript check's three folder rules ("id<TAB>label<TAB>
# pattern" lines) and of the archiver's and private-terms check's folder
# list, exactly as they were spelled out in these tools before M3. The list
# and its generation must give the same rules; a test that held the old
# text would name the folders, so it holds their hashes.
RULES_BEFORE_M3 = "862c0ac8e554aa801165651a5dde82766631fe69f3193bb00e8e8a7586cee937"
DIRS_BEFORE_M3 = "e5758d4f9f3f5c74339a18b829ba838ba0b4e730c5a8a2310ebcb820102c640a"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class FolderListTest(unittest.TestCase):
    """Requirements: R-CLEAN-1, R-SEP-2"""

    def test_the_list(self):
        rows = ct.read_folders()
        self.assertEqual(len(rows), 3)
        self.assertEqual([r[2] for r in rows], ["F-VENDOR-EMU", "F-HARNESS", "F-SPEC-SESSIONS"])
        self.assertEqual([r[1] for r in rows], ["source", "source", "transcripts"])
        self.assertEqual([r[2] for r in rows], [r[2] for r in PLACEHOLDER_FOLDERS])

    def test_the_rules_are_the_ones_before_m3(self):
        rules = [r for r in ct.FORBIDDEN if r[0] in ct.FOLDER_RULES]
        self.assertEqual(sha("\n".join("%s\t%s\t%s" % r for r in rules)), RULES_BEFORE_M3)
        self.assertEqual(sha("\n".join(ar.SPEC_DIRS)), DIRS_BEFORE_M3)
        self.assertEqual(sha("\n".join(cp.SPEC_DIRS)), DIRS_BEFORE_M3)
        # in the same places in the table as before
        self.assertEqual([r[0] for r in ct.FORBIDDEN][7:11],
                         ["F-VENDOR-EMU", "F-HARNESS", "F-FWHUB", "F-SPEC-SESSIONS"])

    def test_configure_needs_every_folder_rule(self):
        mod = load_tool("check-transcripts.py")
        with self.assertRaises(ValueError):
            mod.configure(PLACEHOLDER_FOLDERS[:2])
        with self.assertRaises(ValueError):
            mod.configure(PLACEHOLDER_FOLDERS + [("x", "source", "F-NEW", "x/")])
        mod.configure(PLACEHOLDER_FOLDERS)
        self.assertTrue(any(rx.search("cat spa/one/x") for _, _, rx in mod.FORBIDDEN_RE))

    def test_the_clean_settings_deny_every_folder(self):
        with open(os.path.join(ROOT, "config", "claude", "clean.json")) as f:
            deny = json.load(f)["permissions"]["deny"]
        for folder, _, _, _ in ct.read_folders():
            self.assertIn("Read(./%s/**)" % folder, deny, folder)

    def test_barrier_files_never_spell_a_folder_out(self):
        rules = [(rid, rx) for rid, _, rx in ct.FORBIDDEN_RE if rid in ct.FOLDER_RULES]
        for path in BARRIER_FILES:
            with open(os.path.join(ROOT, path), encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    hits = [rid for rid, rx in rules if rx.search(line)]
                    self.assertEqual(hits, [], "%s:%d names a spec-side folder" % (path, n))

    def test_shell_tools_read_the_list(self):
        for path in SHELL_TOOLS:
            with open(os.path.join(ROOT, path), encoding="utf-8") as f:
                self.assertIn("config/spec-side-folders", f.read(), path)
