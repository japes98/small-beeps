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

    def test_universal_constants_are_not_terms(self):
        """By rule (R-SEP-1, since SR-4's note): powers of two, 2^n-1, 2^n+1,
        sign-bit masks and IEEE 754's standard patterns."""
        for v in (0x1000, 0x80000000, 0x8000000000000000, 0xffff, 0x7fffffff, 0xffffffff, 0x7fffff,
                  0x10001, 0x100000001,
                  0x3f800000, 0xbf800000, 0x7f800000, 0xff800000, 0x7fc00000, 0xffc00000,
                  0x4b000000, 0x34000000,
                  0x3ff0000000000000, 0x7ff0000000000000, 0xfff0000000000000, 0x7ff8000000000000,
                  0x4330000000000000, 0x3cb0000000000000):
            self.assertTrue(terms.universal(v), hex(v))
            self.assertEqual(terms.terms_of("x 0x%x y" % v), set(), hex(v))
        for v in (0x1c7f0, 0x01eef0d0, 0x3f800001, 0x40490fdb, 0x7fc00001, 0x13572468, 0x3e800000):
            self.assertFalse(terms.universal(v), hex(v))
            self.assertEqual(terms.terms_of("x 0x%x y" % v), {"0x%x" % v}, hex(v))

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


class PlaitsTermsTest(unittest.TestCase):
    """Since M4b (the owner's decision): the terms of vendor/plaits/, read
    only from its checksum-verified files, are public, like the SDK's; the
    check says how many emulator terms that takes off, and doesn't scan
    vendor/plaits/ itself. Requirements: R-SEP-1"""

    def write(self, path, text):
        os.makedirs(os.path.dirname(os.path.join(self.dir, path)), exist_ok=True)
        with open(os.path.join(self.dir, path), "w") as f:
            f.write(text)

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        # made-up words, built at run time
        self.plaits_word, self.other = "plaits" + "_only_term", "nowhere" + "_else_term"
        subprocess.run(["git", "-C", self.dir, "init", "-q", "-b", "main"], check=True)
        self.write("vendor/emulator/model.rs", "%s %s\n" % (self.plaits_word, self.other))
        self.write("vendor/plaits/eurorack/plaits/dsp/x.cc", "float %s;\n" % self.plaits_word)
        self.sums()
        self.write("docs/NOTES.md", "%s\n%s\n" % (self.plaits_word, self.other))
        subprocess.run(["git", "-C", self.dir, "add", "-A"], check=True)
        self.saved = (terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts, terms.PLAITS)
        terms.ROOT, terms.EMU = self.dir, os.path.join(self.dir, "vendor", "emulator")
        terms.SDK = terms.REVIEWED = os.path.join(self.dir, "none")
        terms.PLAITS = os.path.join(self.dir, "vendor", "plaits")
        terms.baseline_texts = lambda: iter(())
        self.env = dict(os.environ)

    def sums(self):
        import hashlib
        top = os.path.join(self.dir, "vendor", "plaits")
        lines = []
        for dirpath, _, names in os.walk(top):
            for n in names:
                rel = os.path.relpath(os.path.join(dirpath, n), top)
                if rel != "SHA256SUMS":
                    with open(os.path.join(dirpath, n), "rb") as f:
                        lines.append("%s %s\n" % (hashlib.sha256(f.read()).hexdigest(), rel))
        with open(os.path.join(top, "SHA256SUMS"), "w") as f:
            f.write("".join(sorted(lines, key=lambda l: l.split()[1])))

    def tearDown(self):
        terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts, terms.PLAITS = self.saved
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.dir)

    def run_check(self):
        os.environ["DOORS_REF"] = "no-such-ref"
        os.environ["COMMIT_RANGE"] = "HEAD..HEAD"
        os.environ.pop("GITHUB_EVENT_PATH", None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = terms.main()
        return code, out.getvalue()

    def test_a_plaits_term_passes_and_one_in_neither_fails(self):
        found, by_plaits = terms.emulator_terms_counted()
        self.assertNotIn(self.plaits_word, found)
        self.assertIn(self.other, found)
        self.assertEqual(by_plaits, 1)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("HIT docs/NOTES.md:2 term %s" % terms.h(self.other), out)
        self.assertNotIn("docs/NOTES.md:1", out)
        self.assertIn("took 1 of the emulator's terms off the list", out)
        self.assertNotIn(self.plaits_word, out)
        self.assertNotIn(self.other, out)

    def test_vendor_plaits_itself_is_not_scanned(self):
        self.assertIn("vendor/plaits/", terms.EXCLUDE)
        code, out = self.run_check()
        self.assertNotIn("vendor/plaits/", "".join(l for l in out.splitlines(True) if l.startswith("HIT")))

    def test_a_universal_constant_passes_and_an_emulator_only_number_fails(self):
        self.write("vendor/emulator/model.rs", "0x3f800000 0x7fffffff 0x1c7f0\n")
        self.write("docs/NOTES.md", "one is 0x3f800000, a mask 0x7fffffff\nand 0x1c7f0\n")
        subprocess.run(["git", "-C", self.dir, "add", "-A"], check=True)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertNotIn("docs/NOTES.md:1", out)
        self.assertIn("HIT docs/NOTES.md:2 term %s" % terms.h("0x1c7f0"), out)

    def test_our_own_notes_in_vendor_plaits_are_scanned(self):
        # SOURCE.md is ours, not upstream's: scanned (since SR-4)
        self.write("vendor/plaits/SOURCE.md", "%s\n" % self.other)
        subprocess.run(["git", "-C", self.dir, "add", "-A"], check=True)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("HIT vendor/plaits/SOURCE.md:1 term %s" % terms.h(self.other), out)

    def test_only_the_checksum_verified_tree_counts(self):
        # a changed file, or one SHA256SUMS doesn't list, fails the check
        self.write("vendor/plaits/eurorack/plaits/dsp/x.cc", "float %s; // changed\n" % self.plaits_word)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("does not match its SHA-256", out)
        self.sums()
        self.write("vendor/plaits/eurorack/plaits/dsp/extra.cc", "int %s;\n" % self.other)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("is not in SHA256SUMS", out)
        self.assertNotIn(self.other, out)


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
        self.saved = (terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts, terms.PLAITS)
        terms.ROOT, terms.EMU = self.dir, os.path.join(self.dir, "vendor", "emulator")
        terms.SDK = terms.REVIEWED = terms.PLAITS = os.path.join(self.dir, "none")
        terms.baseline_texts = lambda: iter(())
        self.env = dict(os.environ)

    def tearDown(self):
        terms.ROOT, terms.EMU, terms.SDK, terms.REVIEWED, terms.baseline_texts, terms.PLAITS = self.saved
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
