# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import contextlib
import io
import os
import shutil
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
