# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import subprocess
import unittest

from tests.helpers import ROOT

# The toolchain's disassembly, as objdump -d prints it (tab before the
# instruction), with the forms tools/ownbase.pl must and must not flag.
SAMPLE = """
t.o:\tfile format ELF32-pi32v2

Disassembly of section .text:
f:
       0:    d9 e8 20 00       \t[--sp] = {rets, r5}
       4:    d0 ec 17 10       \t[++r1=4] = r1
       8:    a2 05             \t[r2++=4] = r2
       a:    dc ee 31 34       \tb[++r3=r4] = r3
       e:    dd 06             \th[r5++=-2] = r5
      10:    a3 05             \t[r2++=4] = r3
Disassembly of section .text.g:
g:
      20:    a3 05             \tr1 = [r1++=4]
      22:    a3 05             \t[r12+4] = r12
      24:    a3 05             \t[r1++=4] = r10 #
      26:    a3 05             \t[r1+r2] = r1
      28:    a3 05             \th[++r7=2] = r7 #
"""


class OwnBaseTest(unittest.TestCase):
    """Requirements: R-BUILD-3"""

    def run_check(self, text):
        p = subprocess.run(["perl", os.path.join(ROOT, "tools", "ownbase.pl"), "t.o"],
                           input=text.encode(), stdout=subprocess.PIPE)
        return p.returncode, p.stdout.decode().splitlines()

    def test_flags_each_store_into_its_own_base_register_with_its_place(self):
        rc, lines = self.run_check(SAMPLE)
        self.assertEqual(rc, 1)
        self.assertEqual(lines, [
            "t.o: f+0x4 (.text): [++r1=4] = r1",
            "t.o: f+0x8 (.text): [r2++=4] = r2",
            "t.o: f+0xa (.text): b[++r3=r4] = r3",
            "t.o: f+0xe (.text): h[r5++=-2] = r5",
            "t.o: g+0x8 (.text.g): h[++r7=2] = r7 #",
        ])

    def test_passes_code_without_one(self):
        rc, lines = self.run_check("Disassembly of section .text:\nf:\n   0:  a3 05  \t[r2++=4] = r3\n")
        self.assertEqual((rc, lines), (0, []))


if __name__ == "__main__":
    unittest.main()
