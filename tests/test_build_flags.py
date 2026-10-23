# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
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


if __name__ == "__main__":
    unittest.main()
