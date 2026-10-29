# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
import os
import re
import subprocess
import unittest

from tests.helpers import ROOT, load_tool

st = load_tool("store.py")
SCRIPT = os.path.join(ROOT, "tools", "store-region.pl")
# The package link's image ends at chip offset 0x11957 (build A's, give or
# take): 0x4000 + 0x0200D958 - 0x02000000, its data copied after its code.
IMAGE = {"__data_load": 0x0200D8D8, "__data_start": 0x01C27000, "__data_end": 0x01C27080}
AFTER = 0x12000


def nm(base, size, **image):
    syms = dict(IMAGE, **image)
    syms.update(sb_store_base=base, sb_store_size=size)
    return "".join("%08x %s %s\n" % (v, "A" if k.startswith("sb_store") else "T", k)
                   for k, v in sorted(syms.items()))


class StoreRegionTest(unittest.TestCase):
    """Requirements: R-STORE-12"""

    def check(self, base, size, **image):
        p = subprocess.run(["perl", SCRIPT, "app-pkg.elf"], input=nm(base, size, **image).encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, p.stdout.decode()

    def refused(self, base, size, *wants):
        rc, out = self.check(base, size)
        self.assertEqual(rc, 1, out)
        for w in wants:
            self.assertIn(w, out)
        self.assertRegex(out, r"(?m)^app-pkg\.elf: store region: where it would fit: ")
        return out

    def test_the_constants_are_the_stores(self):
        with open(SCRIPT) as f:
            pl = f.read()
        self.assertIn("my $MIN_SECTORS = %d;" % st.SECTORS_MIN, pl)
        self.assertIn("my $MAX_SECTORS = %d;" % st.SECTORS_MAX, pl)
        self.assertIn("[0x%X, 0x%X, \"the stock firmware's user patch region" % st.USER_REGION, pl)
        self.assertIn("my ($UNUSED, $UNUSED_END) = (0x%X, 0x%X);" % (st.BASE, st.REGION_END), pl)

    def test_takes_the_default_and_regions_after_the_image(self):
        for base, size in ((0xFC000, 0x3000), (0x20000, 0x5000), (0x20000, 0x10000), (AFTER, 0x3000),
                           (0x94000 - 0x10000, 0x10000), (AFTER, 128 * 0x1000)):
            rc, out = self.check(base, size)
            self.assertEqual(rc, 0, out)
            self.assertRegex(out, r"^app-pkg\.elf: store region 0x%X to 0x%X, %d sectors \(the image ends at 0x11957\)"
                             % (base, base + size - 1, size // 0x1000))
        for n, (base, sectors) in st.TEST_REGIONS.items():
            self.assertEqual(self.check(base, sectors * st.SECTOR)[0], 0, n)

    def test_refuses_a_region_over_the_image(self):
        out = self.refused(0x10000, 0x5000, "the region (0x10000 to 0x14FFF) overlaps the image, which ends at "
                           "chip offset 0x11957: start it at 0x12000 or later")
        self.assertIn("a region of 5 sectors fits in the app area after the image, from 0x12000 to 0x8F000 at the "
                      "latest", out)

    def test_refuses_a_region_across_the_app_areas_end(self):
        out = self.refused(0x90000, 0x10000, "the region (0x90000 to 0x9FFFF) crosses the end of the app area at "
                           "0x94000", "overlaps the stock firmware's VM region")
        self.assertIn("a region of 16 sectors fits in the app area after the image, from 0x12000 to 0x%X" % (0x94000 - 0x10000),
                      out)

    def test_refuses_the_stock_user_patch_region(self):
        # The wide region test build's until clean-store-region.
        out = self.refused(0xFA000, 0x5000, "overlaps the stock firmware's user patch region, which the base leaves "
                           "untouched, 0xEA000 to 0xFBFFF (HW-80)")
        self.assertIn("the unused region 0xFC000 to 0xFEFFF holds 3", out)
        self.refused(0xEA000, 0x12000, "user patch region")

    def test_refuses_what_isnt_whole_sectors(self):
        self.refused(0x20800, 0x5000, "STORE_BASE 0x20800 is not on a 4 KiB sector boundary: 0x20000 or 0x21000 "
                     "would be")
        self.refused(0x20000, 0x5800, "STORE_SIZE 0x5800 is not a whole number of 4 KiB sectors: 0x5000 or 0x6000 "
                     "would be")

    def test_refuses_too_small_and_too_large(self):
        out = self.refused(0x20000, 0x2000, "STORE_SIZE 0x2000 is 2 sectors; the store needs 3 at least (0x3000)")
        self.assertIn("a region of 3 sectors fits", out)
        self.refused(0xFC000, 0, "is 0 sectors; the store needs 3 at least")
        out = self.refused(AFTER, 129 * 0x1000, "is 129 sectors; the store keeps track of 128 at most (0x80000, "
                           "STORE_SECTORS_MAX)")
        self.assertIn("a region of 128 sectors fits in the app area after the image, from 0x12000 to 0x14000", out)

    def test_refuses_the_rest_of_the_stock_layout(self):
        self.refused(0x0, 0x3000, "begins in the boot area (0x0 to 0x3FFF)")
        self.refused(0xA0000, 0x5000, "overlaps the stock firmware's VM region")
        self.refused(0xE9000, 0x3000, "overlaps the Bluetooth sector, 0xE9000 to 0xE9FFF")
        self.refused(0xFD000, 0x3000, "overlaps the chip's last sector, the per-unit key that must never be erased")
        self.refused(0xFE000, 0x4000, "runs past the end of the 1 MiB chip")

    def test_says_when_the_app_area_has_no_room(self):
        # An image reaching past the app area's end leaves it none.
        rc, out = self.check(0x20000, 0x5000, __data_load=0x02092000)
        self.assertEqual(rc, 1)
        self.assertIn("overlaps the image", out)
        self.assertIn("the app area after the image (none) holds 0 sectors at most", out)

    def test_every_problem_is_listed(self):
        out = self.refused(0x10400, 0x2800)
        self.assertEqual(len(re.findall(r"(?m)^app-pkg\.elf: store region: ", out)), 5, out)


if __name__ == "__main__":
    unittest.main()
