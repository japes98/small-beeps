# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
import subprocess
import unittest

from tests.helpers import ROOT


class BuildFlagsTest(unittest.TestCase):
    """Requirements: R-BUILD-1"""

    def setUp(self):
        with open(os.path.join(ROOT, "tools", "build.sh"), encoding="utf-8") as f:
            self.script = f.read()

    def test_the_chips_cpu_model_and_float_instructions(self):
        # HW-62: the SDK builds for this CPU model with fprev1.
        m = re.search(r'^\s*CPU="([^"]*)"', self.script, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).split(), ["-mcpu=r3", "-mfprev1"])

    def test_c_and_assembly_both_use_it(self):
        for name in ("CFLAGS", "ASFLAGS"):
            m = re.search(r'^\s*%s="-target pi32v2 \$CPU ' % name, self.script, re.M)
            self.assertIsNotNone(m, name)


class FolderCpuTest(unittest.TestCase):
    """Requirements: R-BUILD-5

    A --src folder's objects are built for the SDK's CPU and float
    (clean-pin-flags): tools/build.sh's cpu_effects, on readings as
    read_cpu makes them from clang's -### line (the build image's clang
    gives these for the flags named)."""

    def setUp(self):
        with open(os.path.join(ROOT, "tools", "build.sh"), encoding="utf-8") as f:
            m = re.search(r"^cpu_effects\(\) \{\n.*?^\}\n", f.read(), re.M | re.S)
        self.assertIsNotNone(m)
        self.func = m.group(0)

    def effects(self, reading):
        out = subprocess.run(["sh", "-c", self.func + 'cpu_effects "$1"', "sh", reading],
                             check=True, capture_output=True, text=True).stdout
        return out.splitlines()

    def test_the_sdks_set_and_none_pass(self):
        for reading in (" -mcpu=r3 -mattr=+fprev1",           # the base's flags, and -mfprev1 again
                        " -mcpu=r3",                          # -mcpu=r3 alone
                        " -mcpu=r3 -mattr=-fprev1",           # -mno-fprev1
                        " -mcpu=r3 -mattr=+fprev1,+fprev2,-fprev2"):
            self.assertEqual(self.effects(reading), [], reading)

    def test_another_cpu(self):
        self.assertEqual(self.effects(" -mcpu=r4 -mattr=+fprev1"), ["another CPU, r4 (the SDK's is r3)"])
        self.assertEqual(self.effects(" -mcpu=r3s -mattr=+fprev1"), ["another CPU, r3s (the SDK's is r3)"])
        self.assertEqual(self.effects(""), ["no particular CPU (clang read none from the flags; the SDK's is r3)"])

    def test_double_precision_simd_and_any_other_feature(self):
        # -mfprev2 and -Xclang -target-feature -Xclang +fprev2 read the same.
        self.assertEqual(self.effects(" -mcpu=r3 -mattr=+fprev1,+fprev2"), ["double-precision float (fprev2)"])
        self.assertEqual(self.effects(" -mcpu=r3 -mattr=+fprev1,+simd"), ["SIMD instructions (simd)"])
        self.assertEqual(self.effects(" -mcpu=r3 -mattr=+fprev1,+newfeature"), ["the target feature newfeature"])
        self.assertEqual(self.effects(" -mcpu=r4 -mattr=-fprev1,+simd,+fprev2"),
                         ["another CPU, r4 (the SDK's is r3)", "SIMD instructions (simd)",
                          "double-precision float (fprev2)"])


class FolderFlagsTest(unittest.TestCase):
    """Requirements: R-BUILD-5

    The families a folder may set (tools/build.sh's check_flags): -Xclang
    stays refused, and -mllvm, which passes options to the code generator
    past clang's reading of the CPU and float, is refused outright
    (clean-mllvm, the owner's answers)."""

    def setUp(self):
        with open(os.path.join(ROOT, "tools", "build.sh"), encoding="utf-8") as f:
            m = re.search(r"^check_flags\(\) \{\n.*?^\}\n", f.read(), re.M | re.S)
        self.assertIsNotNone(m)
        self.func = m.group(0)

    def check(self, flags):
        return subprocess.run(["sh", "-c", self.func + 'check_flags --cflags "$1"', "sh", flags],
                              capture_output=True, text=True)

    def test_m_flags_pass(self):
        for flags in ("-mfprev1 -O2", "-mcpu=r3", "-mno-fprev1"):
            r = self.check(flags)
            self.assertEqual((r.returncode, r.stderr), (0, ""), flags)

    def test_mllvm_is_refused(self):
        # -fast-isel would pass on its own (-f); -mllvm= is clang's joined spelling.
        for flags, word in (("-mllvm -fast-isel", "-mllvm"), ("-O2 -mllvm=-fast-isel", "-mllvm=-fast-isel")):
            r = self.check(flags)
            self.assertEqual(r.returncode, 2, flags)
            self.assertIn("build: --cflags '%s' is not one a folder may set: it passes options "
                          "straight to the code generator" % word, r.stderr)

    def test_xclang_stays_refused(self):
        r = self.check("-Xclang -target-feature -Xclang +fprev2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("'-Xclang' is not one a folder may set", r.stderr)


if __name__ == "__main__":
    unittest.main()
