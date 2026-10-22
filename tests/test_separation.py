# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest

from tests.helpers import ROOT, load_tool

terms = load_tool("check-emulator-terms.py")
pin = load_tool("check-fwtest-pin.py")


class EmulatorTermsTest(unittest.TestCase):
    """Requirements: R-SEP-1"""

    def test_identifier_shapes(self):
        for w in ("made_up", "SOME_BASE", "someThing", "t9con", "abc_d12"):
            self.assertTrue(terms.shaped(w), w)
        for w in ("the", "firmware", "abc", "deadbeef", "x1f00", "fc1f0000ff4c_u64", "1234"):
            self.assertFalse(terms.shaped(w), w)

    def test_hex_numbers_are_terms_from_four_digits(self):
        self.assertEqual(terms.terms_of("a 0x0ABC_D123 b 0x12 c 0x0fff"), {"0xabcd123"})

    def test_hits_report_place_and_hash_only(self):
        # built at run time, so this file holds no emulator identifier
        word = "made" + "_up_" + "term"
        hits = terms.hits_in("line one\nuses %s here\n" % word, {word}, "docs/X.md")
        self.assertEqual(hits, [("docs/X.md", 2, word)])
        self.assertNotIn(word, terms.h(word))

    def test_skips_without_the_emulator(self):
        saved = terms.EMU
        terms.EMU = os.path.join(ROOT, "no-such-folder")
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.assertEqual(terms.main(), 0)
        finally:
            terms.EMU = saved
        self.assertIn("SKIP", out.getvalue())

    @unittest.skipUnless(os.path.isdir(terms.EMU), "spec side only: needs vendor/emulator/")
    def test_finds_an_emulator_only_identifier(self):
        found = terms.emulator_terms()
        self.assertGreater(len(found), 1000)
        word = sorted(w for w in found if "_" in w)[0]
        self.assertEqual(len(terms.hits_in("see %s" % word, found, "x")), 1)
        self.assertNotIn("sha256", found, "words the clean side already used are not terms")


class DoorsOnMainTest(unittest.TestCase):
    """Terms in the doors as merged on main are accepted; a door's text on a
    branch is not. Requirements: R-SEP-1, R-SPEC-2"""

    def git(self, *args):
        subprocess.run(["git", "-C", self.dir, "-c", "user.name=t", "-c", "user.email=t@example.com"] + list(args),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def write(self, path, text):
        os.makedirs(os.path.dirname(os.path.join(self.dir, path)), exist_ok=True)
        with open(os.path.join(self.dir, path), "w") as f:
            f.write(text)

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        # made-up words, built at run time
        self.merged, self.new = "merged" + "_door_term", "branch" + "_door_term"
        self.git("init", "-q", "-b", "main")
        self.write("vendor/emulator/model.rs", "%s %s 0x1c7f0\n" % (self.merged, self.new))
        self.write("docs/HARDWARE-SPEC.md", "HW-1: %s at 0x01C7F0\n" % self.merged)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "main")
        self.main_sha = subprocess.run(["git", "-C", self.dir, "rev-parse", "HEAD"], check=True,
                                       stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
        # a branch: the new word is added to a door and used elsewhere
        self.write("docs/HARNESS.md", "uses %s\n" % self.new)
        self.write("docs/NOTES.md", "%s and %s, at 0x1c7f0\n" % (self.merged, self.new))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "branch")
        self.saved = (terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts)
        terms.ROOT, terms.EMU = self.dir, os.path.join(self.dir, "vendor", "emulator")
        terms.SDK = terms.REVIEWED = os.path.join(self.dir, "none")
        terms.baseline_texts = lambda: iter(())
        self.env = dict(os.environ)

    def tearDown(self):
        terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts = self.saved
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.dir)

    def run_check(self, ref):
        os.environ["DOORS_REF"] = ref
        os.environ["COMMIT_RANGE"] = "HEAD..HEAD"
        os.environ.pop("GITHUB_EVENT_PATH", None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = terms.main()
        return code, out.getvalue()

    def test_door_terms_come_from_the_commit_not_the_tree(self):
        got = terms.door_terms(self.main_sha)
        self.assertIn(self.merged, got)
        self.assertIn("0x1c7f0", got, "numbers in the doors count too")
        self.assertNotIn(self.new, got, "a door's text on a branch is not accepted")

    def test_merged_door_terms_pass_and_branch_ones_are_hits(self):
        code, out = self.run_check(self.main_sha)
        self.assertEqual(code, 1)
        self.assertIn("DOOR docs/NOTES.md:1 term %s" % terms.h(self.merged), out)
        self.assertIn("DOOR docs/NOTES.md:1 term %s" % terms.h("0x1c7f0"), out)
        self.assertIn("HIT docs/NOTES.md:1 term %s" % terms.h(self.new), out)
        self.assertIn("HIT docs/HARNESS.md:1 term %s" % terms.h(self.new), out)
        self.assertNotIn(self.new, out)

    def test_without_the_ref_nothing_is_accepted(self):
        code, out = self.run_check("no-such-ref")
        self.assertEqual(code, 1)
        self.assertIn("not found", out)
        self.assertIn("HIT docs/NOTES.md:1 term %s" % terms.h(self.merged), out)


class FwtestPinTest(unittest.TestCase):
    """Requirements: R-SEP-3, R-HARN-10"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "config"))
        os.makedirs(os.path.join(self.dir, "tools"))
        shutil.copyfile(os.path.join(ROOT, "tools", "fwtest"), os.path.join(self.dir, "tools", "fwtest"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def problems(self, ref):
        with open(os.path.join(self.dir, "config", "fwtest-image"), "w") as f:
            f.write("# comment\n%s\n" % ref)
        with contextlib.redirect_stdout(io.StringIO()):
            return pin.check(self.dir)

    def test_committed_pin_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(pin.check(), [])

    def test_digest_pins_pass_and_tags_fail(self):
        good = "ghcr.io/someone/some-repo@sha256:" + "a" * 64
        self.assertEqual(self.problems(good), [])
        self.assertEqual(self.problems("unpublished"), [])
        self.assertTrue(self.problems("ghcr.io/someone/some-repo:latest"))
        self.assertTrue(self.problems("ghcr.io/someone/some-repo@sha256:abc"))
        self.assertTrue(self.problems(good + "\nsecond-line"))

    def test_quiet_words_fail(self):
        self.assertTrue(self.problems("ghcr.io/someone/" + "fm" + "1-runner@sha256:" + "a" * 64))

    def test_wrapper_must_pin_and_isolate(self):
        p = os.path.join(self.dir, "tools", "fwtest")
        with open(p) as f:
            text = f.read()
        with open(p, "w") as f:
            f.write(text.replace("--network none", ""))
        self.assertTrue(self.problems("unpublished"))
