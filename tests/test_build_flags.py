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


if __name__ == "__main__":
    unittest.main()
